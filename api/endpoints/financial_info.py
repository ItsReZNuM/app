# app/api/endpoints/financial_info.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import logging

from database.db import get_db
from database.models.financial_info_DB import FinancialInfo as FinancialInfoModel
from schemas.financial_info_schema import (
    FinancialInfoResponse,
    FinancialInfoCreate,
    FinancialInfoUpdate,
    FinancialInfoListResponse,  # اگر در اسکیما نبود می‌توانید حذفش کنید
)
# --- dynamic import for calc fn to avoid ImportError ---
try:
    import services.financial_service as _fin_svc  # type: ignore
except Exception:
    _fin_svc = None


def _resolve_calc_fn():
    if _fin_svc:
        for _name in ("calculate_financial_metrics", "compute_financial_metrics", "calculate_metrics"):
            _fn = getattr(_fin_svc, _name, None)
            if callable(_fn):
                return _fn
    raise ImportError(
        "services.financial_service must expose one of: calculate_financial_metrics / compute_financial_metrics / calculate_metrics"
    )

_calc_financial_metrics = _resolve_calc_fn()  # use this instead of direct import

# تغییر ضروری برای هم‌راست شدن با فرانت: مسیرها زیر /api/financial قرار بگیرند
router = APIRouter(prefix="/financial", tags=["financial"])  # قبلاً: "/financial_info"

# ----------------------------
# Helpers
# ----------------------------

def _to_float(v: Optional[float]) -> float:
    try:
        return float(v or 0.0)
    except Exception:
        return 0.0

def _as_record(model: FinancialInfoModel) -> Dict:
    """تبدیل ORM به ساختار ورودی سرویس محاسباتی"""
    return {
        "company_id": model.company_id,
        "record_number": model.record_number,
        "stage": model.stage,
        "invoice_number": model.invoice_number or "",
        "invoice_type": model.invoice_type,
        "invoice_amount": _to_float(model.invoice_amount),
        "allocation_amount": _to_float(model.allocation_amount),
        "paid_amount": _to_float(model.paid_amount),
        # 🔧 استفاده از فیلد allocation_usage اگر موجود باشد
        "allocation_usage": _to_float(getattr(model, "allocation_usage", 0.0)),
        "settlement_method": model.settlement_method or None,
        "advance_amortization": _to_float(model.advance_amortization),
        "partial_amortization": _to_float(model.partial_amortization),
    }

def _calc_for_current_stage(
    db: Session,
    company_id: str,
    record_number: int,
    current_stage: int,
    override_current: Optional[Dict] = None,
) -> Dict:
    """
    همهٔ مراحل مربوط به یک record_number را می‌خواند،
    در صورت نیاز مرحلهٔ جاری را با override جایگزین می‌کند،
    سپس calculate_financial_metrics را روی لیست اجرا می‌کند
    و خروجی مرحلهٔ جاری را برمی‌گرداند.
    """
    rows: List[FinancialInfoModel] = (
        db.query(FinancialInfoModel)
        .filter_by(company_id=company_id, record_number=record_number)
        .order_by(FinancialInfoModel.stage)
        .all()
    )

    records: List[Dict] = []
    has_current = False
    for r in rows:
        if r.stage == current_stage and override_current is not None:
            records.append(override_current)
            has_current = True
        else:
            records.append(_as_record(r))

    # اگر مرحلهٔ جاری هنوز در DB وجود ندارد (سناریوی POST)
    if not has_current and override_current is not None:
        records.append(override_current)

    # اجرای سرویس محاسباتی
    logging.debug("Calculating metrics for records: %s", records)
    results = _calc_financial_metrics(records)
    logging.debug("Calculation results: %s", results)

    # انتخاب نتیجه مربوط به stage جاری
    for res in results:
        if res.get("stage") == current_stage:
            return res

    # اگر پیدا نشد، یعنی ورودی درست نبوده
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="نتیجهٔ محاسبات برای مرحلهٔ جاری یافت نشد.",
    )

def _apply_metrics_to_model(model: FinancialInfoModel, metrics: Dict) -> None:
    """ریختن خروجی سرویس به فیلدهای مدل DB"""
    model.remaining_invoice = _to_float(metrics.get("remaining_invoice"))
    model.remaining_advance = _to_float(metrics.get("remaining_advance"))
    model.remaining_partial = _to_float(metrics.get("remaining_partial"))
    model.remaining_allocation = _to_float(metrics.get("remaining_allocation"))
    model.contractor_credit = _to_float(metrics.get("contractor_credit"))
    model.contractor_debit = _to_float(metrics.get("contractor_debit"))
    model.total_paid_invoices = _to_float(metrics.get("total_paid_invoices"))


# کمک‌تابع برای غنی‌سازی پاسخ مراحل >۱ با داده‌های مرحله ۱
def _enrich_with_stage1_if_needed(db: Session, obj: FinancialInfoModel) -> Dict:
    data = {
        "company_id": obj.company_id,
        "record_number": obj.record_number,
        "stage": obj.stage,
        "invoice_number": obj.invoice_number,
        "invoice_type": obj.invoice_type,
        "invoice_amount": obj.invoice_amount,
        "allocation_amount": obj.allocation_amount,
        "request_number": obj.request_number,
        "request_date": obj.request_date,
        "request_result": obj.request_result,
        "settlement_method": obj.settlement_method,
        "paid_amount": obj.paid_amount,
        "allocation_usage": getattr(obj, "allocation_usage", 0.0),
        "advance_amortization": obj.advance_amortization,
        "partial_amortization": obj.partial_amortization,
        "remaining_invoice": obj.remaining_invoice,
        "remaining_advance": obj.remaining_advance,
        "remaining_partial": obj.remaining_partial,
        "remaining_allocation": obj.remaining_allocation,
        "contractor_credit": obj.contractor_credit,
        "contractor_debit": obj.contractor_debit,
        "total_paid_invoices": obj.total_paid_invoices,
        "project": None,
    }
    if obj.stage > 1:
        s1 = (
            db.query(FinancialInfoModel)
              .filter_by(company_id=obj.company_id, record_number=obj.record_number, stage=1)
              .first()
        )
        if s1:
            # در مراحل >۱ همیشه فیلدهای «ثابت» از مرحله ۱ روی پاسخ override شوند
            data["invoice_number"]    = s1.invoice_number
            data["invoice_type"]      = s1.invoice_type
            data["invoice_amount"]    = s1.invoice_amount
            data["allocation_amount"] = s1.allocation_amount
            data["request_number"]    = s1.request_number
            data["request_date"]      = s1.request_date
            data["request_result"]    = s1.request_result
            data["settlement_method"] = s1.settlement_method
        else:
            # اگر مرحله ۱ موجود نیست ولی stage>1 است، بهتر است خطا بدهیم
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="برای این ردیف مرحله ۱ وجود ندارد؛ امکان بازگردانی مرحله‌های بعدی نیست.")

    return data


# ----------------------------
# Endpoints
# ----------------------------

@router.get(
    "/{company_id}/{record_number}/{stage}",
    response_model=FinancialInfoResponse,
)
def get_financial_info(
    company_id: str,
    record_number: int,
    stage: int,
    db: Session = Depends(get_db),
):
    obj = (
        db.query(FinancialInfoModel)
        .filter_by(company_id=company_id, record_number=record_number, stage=stage)
        .first()
    )
    if not obj:
        raise HTTPException(status_code=404, detail="رکورد مالی یافت نشد.")
    return _enrich_with_stage1_if_needed(db, obj)


@router.get(
    "/{company_id}/{record_number}",
    response_model=FinancialInfoListResponse,  # اگر در اسکیما ندارید، می‌توانید لیست ساده برگردانید
)
def list_financial_infos(
    company_id: str,
    record_number: int,
    db: Session = Depends(get_db),
):
    items = (
        db.query(FinancialInfoModel)
        .filter_by(company_id=company_id, record_number=record_number)
        .order_by(FinancialInfoModel.stage)
        .all()
    )
    enriched = [_enrich_with_stage1_if_needed(db, it) for it in items]
    return {"items": enriched, "total": len(enriched)}


@router.get(
    "/{company_id}",
    response_model=FinancialInfoListResponse
)
def get_financial_info_by_company(
    company_id: str,
    db: Session = Depends(get_db)
):
    try:
        financial_infos = (
            db.query(FinancialInfoModel)
              .filter_by(company_id=company_id)
              .order_by(FinancialInfoModel.record_number, FinancialInfoModel.stage)
              .all()
        )
        enriched = [_enrich_with_stage1_if_needed(db, it) for it in financial_infos]
        return {"items": enriched, "total": len(enriched)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در دریافت اطلاعات مالی شرکت: {str(e)}"
        )


@router.post(
    "/",
    response_model=FinancialInfoResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_financial_info(
    financial_info: FinancialInfoCreate,
    db: Session = Depends(get_db),
):
    try:
        # جلوگیری از ساخت رکورد تکراری
        exists = (
            db.query(FinancialInfoModel)
            .filter_by(
                company_id=financial_info.company_id,
                record_number=financial_info.record_number,
                stage=financial_info.stage,
            )
            .first()
        )
        if exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="رکورد مالی با این مشخصات از قبل وجود دارد.",
            )
        
        if financial_info.stage > 1:
            s1_exists = db.query(FinancialInfoModel).filter_by(
                company_id=financial_info.company_id,
                record_number=financial_info.record_number,
                stage=1
            ).first()
            if not s1_exists:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                    detail="برای ایجاد مرحله جدید، مرحله ۱ این ردیف باید قبلاً ثبت شده باشد.")


        # ساخت آبجکت ORM (فعلاً بدون متریک‌ها)
        if financial_info.stage == 1:
            obj = FinancialInfoModel(
                company_id=financial_info.company_id,
                record_number=financial_info.record_number,
                stage=financial_info.stage,
                invoice_number=financial_info.invoice_number,
                invoice_type=financial_info.invoice_type,
                invoice_amount=_to_float(financial_info.invoice_amount),
                allocation_amount=_to_float(financial_info.allocation_amount),
                request_number=financial_info.request_number,
                request_date=financial_info.request_date,
                request_result=financial_info.request_result,
                settlement_method=financial_info.settlement_method,
                paid_amount=_to_float(financial_info.paid_amount),
                allocation_usage=_to_float(getattr(financial_info, "allocation_usage", 0.0)),
                advance_amortization=_to_float(financial_info.advance_amortization),
                partial_amortization=_to_float(financial_info.partial_amortization),
            )
        else:
            obj = FinancialInfoModel(
                company_id=financial_info.company_id,
                record_number=financial_info.record_number,
                stage=financial_info.stage,
                # فیلدهای ثابت در مراحل بعد ثبت/تغییر داده نمی‌شوند
                paid_amount=_to_float(financial_info.paid_amount),
                allocation_usage=_to_float(getattr(financial_info, "allocation_usage", 0.0)),
                advance_amortization=_to_float(financial_info.advance_amortization or 0.0),
                partial_amortization=_to_float(financial_info.partial_amortization or 0.0),
                settlement_method=financial_info.settlement_method,
            )

        # آماده‌سازی override برای مرحلهٔ جاری
        override_current = {
            "company_id": obj.company_id,
            "record_number": obj.record_number,
            "stage": obj.stage,
            **(
            {
                "invoice_number": obj.invoice_number or "",
                "invoice_type": obj.invoice_type,
                "invoice_amount": _to_float(obj.invoice_amount),
                "allocation_amount": _to_float(obj.allocation_amount),
            } if obj.stage == 1 else {}
            ),
            "paid_amount": _to_float(obj.paid_amount),
            # 🔧 لحاظ‌کردن مصرف تخصیص در محاسبات
            "allocation_usage": _to_float(getattr(obj, "allocation_usage", 0.0)),
            "advance_amortization": _to_float(obj.advance_amortization),
            "partial_amortization": _to_float(obj.partial_amortization),
        }

        # محاسبهٔ متریک‌ها با امضای درست (لیست رکوردها)
        current_metrics = _calc_for_current_stage(
            db=db,
            company_id=obj.company_id,
            record_number=obj.record_number,
            current_stage=obj.stage,
            override_current=override_current,
        )
        _apply_metrics_to_model(obj, current_metrics)

        # ذخیره
        db.add(obj)
        db.commit()
        db.refresh(obj)
        # پاسخ را با داده‌های stage1 غنی کن تا فیلدهای ثابت None نباشند
        return _enrich_with_stage1_if_needed(db, obj)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.exception("Create financial info failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در ایجاد اطلاعات مالی: {str(e)}",
        )


@router.put(
    "/{company_id}/{record_number}/{stage}",
    response_model=FinancialInfoResponse,
)
def update_financial_info(
    company_id: str,
    record_number: int,
    stage: int,
    financial_info: FinancialInfoUpdate,
    db: Session = Depends(get_db),
):
    try:
        obj: Optional[FinancialInfoModel] = (
            db.query(FinancialInfoModel)
            .filter_by(company_id=company_id, record_number=record_number, stage=stage)
            .first()
        )
        if not obj:
            raise HTTPException(status_code=404, detail="رکورد مالی برای ویرایش یافت نشد.")

        # بروزرسانی فیلدهای قابل ویرایش
        # فیلدهای ثابت فقط اگر stage==1 بروز شوند
        if obj.stage == 1:
            if financial_info.invoice_number is not None:
                obj.invoice_number = financial_info.invoice_number
            if financial_info.invoice_type is not None:
                obj.invoice_type = financial_info.invoice_type
            if financial_info.invoice_amount is not None:
                obj.invoice_amount = _to_float(financial_info.invoice_amount)
            if financial_info.allocation_amount is not None:
                obj.allocation_amount = _to_float(financial_info.allocation_amount)
        if financial_info.paid_amount is not None:
            obj.paid_amount = _to_float(financial_info.paid_amount)
        if financial_info.advance_amortization is not None:
            obj.advance_amortization = _to_float(financial_info.advance_amortization)
        if financial_info.partial_amortization is not None:
            obj.partial_amortization = _to_float(financial_info.partial_amortization)
        if financial_info.allocation_usage is not None:
            obj.allocation_usage = _to_float(financial_info.allocation_usage)
        if financial_info.request_number is not None:
            obj.request_number = financial_info.request_number
        if financial_info.request_date is not None:
            obj.request_date = financial_info.request_date
        if financial_info.request_result is not None:
            obj.request_result = financial_info.request_result
        if financial_info.settlement_method is not None:
            obj.settlement_method = financial_info.settlement_method

        # ساخت override از مقادیر جدید مرحلهٔ جاری
        override_current = {
            "company_id": obj.company_id,
            "record_number": obj.record_number,
            "stage": obj.stage,
            **(
                {
                    "invoice_number": obj.invoice_number or "",
                    "invoice_type": obj.invoice_type,
                    "invoice_amount": _to_float(obj.invoice_amount),
                    "allocation_amount": _to_float(obj.allocation_amount),
                } if obj.stage == 1 else {}
            ),
            "paid_amount": _to_float(obj.paid_amount),
            # 🔧 لحاظ‌کردن مصرف تخصیص در محاسبات
            "allocation_usage": _to_float(getattr(obj, "allocation_usage", 0.0)),
            "advance_amortization": _to_float(obj.advance_amortization),
            "partial_amortization": _to_float(obj.partial_amortization),
        }

        # محاسبهٔ متریک‌ها با امضای درست (لیست رکوردها)
        current_metrics = _calc_for_current_stage(
            db=db,
            company_id=obj.company_id,
            record_number=obj.record_number,
            current_stage=obj.stage,
            override_current=override_current,
        )
        _apply_metrics_to_model(obj, current_metrics)

        db.add(obj)
        db.commit()
        db.refresh(obj)
        # مثل بالا: پاسخ غنی‌شده بده
        return _enrich_with_stage1_if_needed(db, obj)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.exception("Update financial info failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در به‌روزرسانی اطلاعات مالی: {str(e)}",
        )


@router.delete("/{company_id}/{record_number}/{stage}", status_code=status.HTTP_204_NO_CONTENT)
def delete_financial_info(
    company_id: str,
    record_number: int,
    stage: int,
    db: Session = Depends(get_db),
):
    try:
        obj = (
            db.query(FinancialInfoModel)
            .filter_by(company_id=company_id, record_number=record_number, stage=stage)
            .first()
        )
        if not obj:
            raise HTTPException(status_code=404, detail="رکورد مالی برای حذف یافت نشد.")

        db.delete(obj)
        db.commit()
        return

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.exception("Delete financial info failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در حذف اطلاعات مالی: {str(e)}",
        )


# app/api/endpoints/financial_info.py
@router.delete("/{company_id}/{record_number}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(company_id: str, record_number: int, db: Session = Depends(get_db)):
    rows = (db.query(FinancialInfoModel)
              .filter_by(company_id=company_id, record_number=record_number)
              .all())
    if not rows:
        raise HTTPException(status_code=404, detail="ردیف یافت نشد.")
    for r in rows:
        db.delete(r)
    db.commit()
    return
