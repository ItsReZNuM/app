# app/api/endpoints/invoice_records.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import logging

from database.db import get_db
from database.models.financial_info_DB import FinancialInfo as FinancialInfoModel
from schemas.financial_info_schema import (
    FinancialInfoResponse,
    FinancialInfoCreate,
    FinancialInfoUpdate,
)
# سرویس محاسباتی (همان ماژول موجود)
from services.financial_service import calculate_financial_metrics  # موجود است

router = APIRouter(prefix="/invoice-records", tags=["Invoice Records"])


def _to_float(v: Optional[float]) -> float:
    try:
        return float(v or 0.0)
    except Exception:
        return 0.0


def _as_record_like_payload(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    ورودی موردنیاز سرویس محاسباتی را از دیکشنری آماده می‌کند.
    """
    return {
        "company_id": d.get("company_id"),
        "record_number": d.get("record_number"),
        "stage": d.get("stage"),
        "invoice_number": d.get("invoice_number") or "",
        "invoice_type": d.get("invoice_type"),
        "invoice_amount": _to_float(d.get("invoice_amount")),
        "allocation_amount": _to_float(d.get("allocation_amount")),
        "paid_amount": _to_float(d.get("paid_amount")),
        "advance_amortization": _to_float(d.get("advance_amortization")),
        "partial_amortization": _to_float(d.get("partial_amortization")),
        # اگر صراحتاً مصرف تخصیص داده شده باشد، لحاظ می‌کنیم
        "allocation_usage": _to_float(d.get("allocation_usage")),
        "settlement_method": d.get("settlement_method"),
    }


def _apply_metrics_to_model(model: FinancialInfoModel, metrics: Dict[str, Any]) -> None:
    model.remaining_invoice = _to_float(metrics.get("remaining_invoice"))
    model.remaining_advance = _to_float(metrics.get("remaining_advance"))
    model.remaining_partial = _to_float(metrics.get("remaining_partial"))
    model.remaining_allocation = _to_float(metrics.get("remaining_allocation"))
    model.contractor_credit = _to_float(metrics.get("contractor_credit"))
    model.contractor_debit = _to_float(metrics.get("contractor_debit"))
    model.total_paid_invoices = _to_float(metrics.get("total_paid_invoices"))


@router.get("/{company_id}/next-record-number")
def next_record_number(company_id: str, db: Session = Depends(get_db)) -> Dict[str, int]:
    """
    بزرگ‌ترین record_number برای company_id را پیدا می‌کند و +1 می‌دهد.
    اگر چیزی نباشد، 1 برمی‌گرداند.
    """
    row = (
        db.query(FinancialInfoModel.record_number)
        .filter(FinancialInfoModel.company_id == company_id)
        .order_by(FinancialInfoModel.record_number.desc())
        .first()
    )
    nxt = (row[0] + 1) if row else 1
    return {"next_record_number": int(nxt)}


class FlexibleCreate(FinancialInfoCreate):
    """
    مشابه FinancialInfoCreate ولی اجازه می‌دهیم record_number اختیاری باشد.
    stage باید >=1 باشد (برای ایجاد مرحله 1 یا مراحل بعدی).
    """
    record_number: Optional[int] = None  # تفاوت اصلی


@router.post("/create-flexible", response_model=FinancialInfoResponse, status_code=status.HTTP_201_CREATED)
def create_flexible(payload: FlexibleCreate, db: Session = Depends(get_db)):
    """
    اگر record_number نیامده باشد:
      - آن را بر اساس بزرگترین ردیف شرکت + 1 تعیین می‌کنیم.
    سپس رکورد را با محاسبه متریک‌ها ذخیره می‌کنیم.
    """
    try:
        # اگر record_number نیامده، تعیین کن
        record_number = payload.record_number
        if not record_number:
            row = (
                db.query(FinancialInfoModel.record_number)
                .filter(FinancialInfoModel.company_id == payload.company_id)
                .order_by(FinancialInfoModel.record_number.desc())
                .first()
            )
            record_number = (row[0] + 1) if row else 1

        # جلوگیری از تکراری بودن (company_id, record_number, stage)
        exists = (
            db.query(FinancialInfoModel)
            .filter_by(
                company_id=payload.company_id,
                record_number=record_number,
                stage=payload.stage,
            )
            .first()
        )
        if exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="این مرحله از این ردیف قبلاً ثبت شده است."
            )

        # ساخت آبجکت ORM (بدون متریک‌ها)
        obj = FinancialInfoModel(
            company_id=payload.company_id,
            record_number=record_number,
            stage=payload.stage,
            invoice_number=payload.invoice_number,
            invoice_type=payload.invoice_type,
            invoice_amount=_to_float(payload.invoice_amount),
            allocation_amount=_to_float(payload.allocation_amount),
            request_number=payload.request_number,
            request_date=payload.request_date,
            request_result=payload.request_result,
            settlement_method=payload.settlement_method,
            paid_amount=_to_float(payload.paid_amount),
            allocation_usage=_to_float(getattr(payload, "allocation_usage", 0.0)),
            advance_amortization=_to_float(payload.advance_amortization),
            partial_amortization=_to_float(payload.partial_amortization),
        )

        # همه مراحل این ردیف را بگیر تا با مرحله فعلی، متریک‌ها را حساب کنیم
        rows = (
            db.query(FinancialInfoModel)
            .filter_by(company_id=payload.company_id, record_number=record_number)
            .order_by(FinancialInfoModel.stage)
            .all()
        )

        records = [_as_record_like_payload({
            "company_id": r.company_id,
            "record_number": r.record_number,
            "stage": r.stage,
            "invoice_number": r.invoice_number,
            "invoice_type": r.invoice_type,
            "invoice_amount": r.invoice_amount,
            "allocation_amount": r.allocation_amount,
            "paid_amount": r.paid_amount,
            "advance_amortization": r.advance_amortization,
            "partial_amortization": r.partial_amortization,
            "allocation_usage": getattr(r, "allocation_usage", 0.0),
            "settlement_method": r.settlement_method,
        }) for r in rows]

        # مرحله فعلی (که هنوز در DB نیست) را هم اضافه کن
        current_payload = payload.dict()
        current_payload["record_number"] = record_number
        records.append(_as_record_like_payload(current_payload))

        # محاسبه متریک‌ها
        metrics_list = calculate_financial_metrics(records)
        current_metrics = None
        for m in metrics_list:
            if int(m.get("stage") or 0) == int(payload.stage):
                current_metrics = m
                break
        if not current_metrics:
            raise HTTPException(status_code=500, detail="محاسبات مرحله جاری یافت نشد.")

        # اعمال متریک‌ها روی مدل
        _apply_metrics_to_model(obj, current_metrics)

        # ذخیره
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.exception("create_flexible failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در ایجاد اطلاعات مالی (انعطاف‌پذیر): {str(e)}"
        )
