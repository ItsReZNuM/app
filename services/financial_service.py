import locale
from typing import List, Dict, TypedDict

# تنظیم locale برای نمایش درست اعداد با جداکننده‌ها
try:
    locale.setlocale(locale.LC_ALL, "fa_IR.UTF-8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        pass

# فلگ برای کنترل استهلاک خودکار
AUTO_AMORTIZATION_ENABLED = False


class FinancialRecord(TypedDict):
    company_id: str
    record_number: int
    stage: int
    invoice_number: str
    invoice_type: str  # پیش‌پرداخت، علی‌الحساب، موقت، قطعی، تعدیل
    invoice_amount: float
    allocation_amount: float
    paid_amount: float
    advance_amortization: float
    partial_amortization: float


class FinancialResult(FinancialRecord):
    remaining_invoice: float
    remaining_advance: float
    remaining_partial: float
    contractor_credit: float
    contractor_debit: float
    total_paid_invoices: float


def calculate_financial_metrics(records: List[FinancialRecord]) -> List[FinancialResult]:
    """
    محاسبه وضعیت مالی برای لیستی از رکوردهای مالی.
    منطق:
      - مانده صورت‌وضعیت = مبلغ صورت‌وضعیت - مجموع پرداختی‌های آن ردیف
      - مانده پیش‌پرداخت = مجموع پیش‌پرداخت‌ها - مجموع استهلاک پیش‌پرداخت‌ها
      - مانده علی‌الحساب = مجموع علی‌الحساب‌ها - مجموع استهلاک علی‌الحساب‌ها
      - بستانکاری پیمانکار = اگر پرداخت‌ها بیشتر از مبلغ صورت‌وضعیت باشد
      - بدهکاری پیمانکار = اگر پرداخت‌ها کمتر از مبلغ صورت‌وضعیت باشد
      - مجموع مبالغ پرداخت‌شده = مجموع پرداخت‌های همان ردیف
    """
    results: List[FinancialResult] = []

    # گروه‌بندی رکوردها بر اساس company_id و record_number
    grouped: Dict[tuple, List[FinancialRecord]] = {}
    for rec in records:
        key = (rec["company_id"], rec["record_number"])
        grouped.setdefault(key, []).append(rec)

    for (company_id, record_number), recs in grouped.items():
        total_paid = 0.0
        total_advance = sum(r["invoice_amount"] for r in recs if r["invoice_type"] == "پیش‌پرداخت" and r["stage"] == 1)
        total_partial = sum(r["invoice_amount"] for r in recs if r["invoice_type"] == "علی‌الحساب" and r["stage"] == 1)

        total_advance_amort = 0.0
        total_partial_amort = 0.0

        for rec in sorted(recs, key=lambda r: r["stage"]):
            paid_amount = rec["paid_amount"]
            total_paid += paid_amount

            if AUTO_AMORTIZATION_ENABLED:
                # اگر استهلاک خودکار فعال باشد می‌توان منطق خاصی را اینجا پیاده کرد
                total_advance_amort += rec["paid_amount"] if rec["invoice_type"] == "پیش‌پرداخت" else rec["advance_amortization"]
                total_partial_amort += rec["paid_amount"] if rec["invoice_type"] == "علی‌الحساب" else rec["partial_amortization"]
            else:
                total_advance_amort += rec["advance_amortization"]
                total_partial_amort += rec["partial_amortization"]

            invoice_amount = rec["invoice_amount"]

            # مانده صورت وضعیت
            remaining_invoice = max(invoice_amount - total_paid, 0)

            # مانده پیش‌پرداخت و علی‌الحساب
            remaining_advance = max(total_advance - total_advance_amort, 0)
            remaining_partial = max(total_partial - total_partial_amort, 0)

            # بستانکاری / بدهکاری
            balance = invoice_amount - total_paid
            contractor_credit = 0.0
            contractor_debit = 0.0
            if balance < 0:
                contractor_credit = abs(balance)
            else:
                contractor_debit = balance

            result: FinancialResult = {
                **rec,
                "remaining_invoice": remaining_invoice,
                "remaining_advance": remaining_advance,
                "remaining_partial": remaining_partial,
                "contractor_credit": contractor_credit,
                "contractor_debit": contractor_debit,
                "total_paid_invoices": total_paid,
            }
            results.append(result)

    return results
