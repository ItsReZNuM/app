"""
Service: Financial Calculations
--------------------------------
این ماژول تمام محاسبات مالیِ موردنیاز UI و لایهٔ صفحات را به‌صورت «پیوِر» (بدون وابستگی به DB) انجام می‌دهد.

تابع‌های اصلی:
- calculate_financial_metrics(records): برای هر رکورد ورودی (هر مرحله) یک نتیجهٔ محاسباتی هم‌مرتبه برمی‌گرداند.
- calculate_company_remaining_allocation(records): ماندهٔ تخصیص سطح شرکت را از روی همهٔ ردیف‌ها محاسبه می‌کند.

سیاست‌ها:
- ماندهٔ تخصیص (ردیف): remaining_allocation = allocation_amount(stage1) - Σ(allocation_usage)
- allocation_usage هر مرحله اگر صراحتاً داده نشده باشد، به‌صورت پیش‌فرض از paid_amount فقط وقتی settlement_method == 'نقد' استفاده می‌شود (برای
  روش‌های دیگر مثل «اسناد خزانه» مقدار 0 در نظر گرفته می‌شود). در صورت نیاز، این سیاست را تغییر دهید.
- ماندهٔ صورت‌وضعیت (ردیف): remaining_invoice = invoice_amount(stage1) - Σ(paid_amount)
- ماندهٔ پیش‌پرداخت: اگر invoice_type در stage1 == 'پیش‌پرداخت' باشد، remaining_advance = invoice_amount(stage1) - Σ(advance_amortization)
- ماندهٔ علی‌الحساب: اگر invoice_type در stage1 == 'علی‌الحساب' باشد، remaining_partial = invoice_amount(stage1) - Σ(partial_amortization)
- بستانکاری/بدهکاری پیمانکار (ردیف): cash_balance = invoice_amount(stage1) - Σ(paid_amount)
  contractor_credit = max(cash_balance, 0)
  contractor_debit  = max(-cash_balance, 0)
- total_paid_invoices: مجموع paid_amountهای همان ردیف

توجه: خروجیِ calculate_financial_metrics به همان ترتیب ورودی records بازگردانده می‌شود و برای هر آیتم ورودی کلید stage حفظ می‌شود.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple, TypedDict
from collections import defaultdict

__all__ = [
    "calculate_financial_metrics",
    "calculate_company_remaining_allocation",
]


# ----- Types -----
class FinancialRecord(TypedDict, total=False):
    company_id: str
    record_number: int
    stage: int
    invoice_number: str
    invoice_type: str  # یکی از: 'پیش‌پرداخت'، 'علی‌الحساب'، 'موقت'، 'قطعی'، 'تعدیل'
    invoice_amount: float
    allocation_amount: float
    paid_amount: float
    advance_amortization: float
    partial_amortization: float
    settlement_method: Optional[str]  # 'نقد' | 'اسناد خزانه' | ...
    allocation_usage: Optional[float]


class FinancialResult(TypedDict, total=False):
    stage: int
    remaining_invoice: float
    remaining_advance: float
    remaining_partial: float
    remaining_allocation: float
    contractor_credit: float
    contractor_debit: float
    total_paid_invoices: float
    # برای اشکال‌زدایی/گزارش‌گیری
    allocation_usage: Optional[float]


# ----- Helpers -----
def _to_float(v: Any) -> float:
    try:
        if v is None:
            return 0.0
        if isinstance(v, (int, float)):
            return float(v)
        # تلاش برای تبدیل رشته‌هایی که جداکننده دارند
        if isinstance(v, str):
            # نگاشت ارقام فارسی/عربی → انگلیسی
            table = str.maketrans({
                "۰":"0","۱":"1","۲":"2","۳":"3","۴":"4","۵":"5","۶":"6","۷":"7","۸":"8","۹":"9",
                "٠":"0","١":"1","٢":"2","٣":"3","٤":"4","٥":"5","٦":"6","٧":"7","٨":"8","٩":"9",
            })
            s = v.translate(table)
            s = s.replace(",", "").replace("\u066C", "").replace("\u060C", "").replace("\u202F", "").replace("\u00A0", "").strip()
            
            if s == "":
                return 0.0
            return float(s)
        return float(v)
    except Exception:
        return 0.0


def _group_by_record(records: Iterable[FinancialRecord]) -> Dict[Tuple[str, int], List[FinancialRecord]]:
    groups: Dict[Tuple[str, int], List[FinancialRecord]] = defaultdict(list)
    for r in records:
        cid = r.get("company_id", "") or ""
        rn = int(r.get("record_number") or 0)
        groups[(cid, rn)].append(r)
    # مرتب‌سازی مراحل هر ردیف بر اساس stage
    for k in groups:
        groups[k].sort(key=lambda x: int(x.get("stage") or 0))
    return groups


def _find_stage1(rec_list: List[FinancialRecord]) -> Optional[FinancialRecord]:
    for r in rec_list:
        if int(r.get("stage") or 0) == 1:
            return r
    return None


def _resolve_allocation_usage(r: FinancialRecord) -> float:
    """
    سیاست جدید و هم‌سو با فرانت: اگر allocation_usage داده شده باشد همان؛
    در غیر این‌صورت «مصرف تخصیص = مبلغ پرداختی همان مرحله» (صرف‌نظر از روش تسویه).
    """
    explicit = r.get("allocation_usage")
    if explicit is not None:
        return _to_float(explicit)
    return _to_float(r.get("paid_amount"))


# ----- Core calculations -----
def calculate_financial_metrics(records: List[FinancialRecord]) -> List[FinancialResult]:
    """
    برای هر آیتم ورودی در records یک دیکشنری نتیجه با همان ترتیب بازمی‌گرداند.
    این تابع خروجی‌هایی سازگار با انتظارات UI و main.py تولید می‌کند.
    """
    # گروه‌بندی بر اساس (company_id, record_number)
    groups = _group_by_record(records)

    # برای دسترسی سریع به جمع‌ها در هر ردیف
    per_record_cache: Dict[Tuple[str, int], Dict[str, float]] = {}

    def compute_per_record(key: Tuple[str, int], recs: List[FinancialRecord]) -> Dict[str, float]:
        if key in per_record_cache:
            return per_record_cache[key]

        s1 = _find_stage1(recs)
        inv_amount_s1 = _to_float(s1.get("invoice_amount") if s1 else 0.0)
        alloc_amount_s1 = _to_float(s1.get("allocation_amount") if s1 else 0.0)
        inv_type_s1 = (s1.get("invoice_type") if s1 else "") or ""

        # Σ پرداخت‌ها، Σ استهلاک‌ها، Σ مصرف تخصیص برای همان ردیف
        total_paid = sum(_to_float(r.get("paid_amount")) for r in recs)
        total_adv_amort = sum(_to_float(r.get("advance_amortization")) for r in recs)
        total_par_amort = sum(_to_float(r.get("partial_amortization")) for r in recs)
        total_alloc_usage = sum(_resolve_allocation_usage(r) for r in recs)

        remaining_invoice = inv_amount_s1 - total_paid
        remaining_allocation = alloc_amount_s1 - total_alloc_usage

        remaining_advance = 0.0
        remaining_partial = 0.0
        if inv_type_s1 == "پیش‌پرداخت":
            remaining_advance = inv_amount_s1 - total_adv_amort
        elif inv_type_s1 == "علی‌الحساب":
            remaining_partial = inv_amount_s1 - total_par_amort

        cash_balance = inv_amount_s1 - total_paid
        contractor_credit = max(cash_balance, 0.0)
        contractor_debit = max(-cash_balance, 0.0)

        per_record_cache[key] = {
            "inv_amount_s1": inv_amount_s1,
            "alloc_amount_s1": alloc_amount_s1,
            "total_paid": total_paid,
            "total_adv_amort": total_adv_amort,
            "total_par_amort": total_par_amort,
            "total_alloc_usage": total_alloc_usage,
            "remaining_invoice": remaining_invoice,
            "remaining_allocation": remaining_allocation,
            "remaining_advance": remaining_advance,
            "remaining_partial": remaining_partial,
            "contractor_credit": contractor_credit,
            "contractor_debit": contractor_debit,
        }
        return per_record_cache[key]

    # خروجی به ترتیب ورودی‌ها
    results: List[FinancialResult] = []
    for rec in records:
        key = ((rec.get("company_id") or ""), int(rec.get("record_number") or 0))
        recs = groups.get(key, [rec])
        agg = compute_per_record(key, recs)

        results.append(
            FinancialResult(
                stage=int(rec.get("stage") or 0),
                remaining_invoice=float(agg["remaining_invoice"]),
                remaining_advance=float(agg["remaining_advance"]),
                remaining_partial=float(agg["remaining_partial"]),
                remaining_allocation=float(agg["remaining_allocation"]),
                contractor_credit=float(agg["contractor_credit"]),
                contractor_debit=float(agg["contractor_debit"]),
                total_paid_invoices=float(agg["total_paid"]),
                allocation_usage=_resolve_allocation_usage(rec),
            )
        )

    return results


def calculate_company_remaining_allocation(records: List[FinancialRecord]) -> float:
    """
    ماندهٔ تخصیص سطح شرکت = Σ allocation_amount (stage1 همهٔ ردیف‌ها) - Σ allocation_usage (همهٔ مراحل، با سیاست بالا)
    """
    groups = _group_by_record(records)

    total_alloc = 0.0
    for key, recs in groups.items():
        s1 = _find_stage1(recs)
        total_alloc += _to_float(s1.get("allocation_amount") if s1 else 0.0)

    total_usage = sum(_resolve_allocation_usage(r) for r in records)
    return total_alloc - total_usage
