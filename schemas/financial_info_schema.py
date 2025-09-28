from typing import Optional, Literal, List, Dict, Any
from pydantic import BaseModel, Field, validator

# =========================================================
# Helpers: نرمال‌سازی متون فارسی/انگلیسی و نگاشت‌ها
# =========================================================

def _norm_fa(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    s = str(v)
    s = (
        # s = s.replace("\u200c", "")  # ❌ این خط را حذف کن: ZWNJ را پاک نکن
        s.replace("\u200f", "")   # RLM
         .replace("\u00a0", " ")  # NBSP → space
         .replace("\u202f", " ")  # NNBSP → space
         .replace("\u2009", " ")  # thin space → space
    )
    s = s.translate(str.maketrans({"ي": "ی", "ك": "ک"}))
    return s.strip()


# نگاشت‌های انگلیسی/فارسی → مقدار فارسی استاندارد
_INVOICE_TYPE_MAP = {
    # EN
    "advance": "پیش‌پرداخت",
    "prepayment": "پیش‌پرداخت",
    "partial": "علی‌الحساب",
    "ali_alhesab": "علی‌الحساب",
    "normal": "موقت",
    "temporary": "موقت",
    "final": "قطعی",
    "definitive": "قطعی",
    "adjust": "تعدیل",
    "adjustment": "تعدیل",
    # FA variants seen in DB
    "صورت وضعیت": "موقت",
}

_INVOICE_TYPE_MAP.update({
    "پیش پرداخت": "پیش‌پرداخت",
    "پیشپرداخت": "پیش‌پرداخت",
    "علی الحساب": "علی‌الحساب",
    "علیالحساب": "علی‌الحساب",
})


_REQUEST_RESULT_MAP = {
    # EN
    "approved": "تایید شده",
    "accepted": "تایید شده",
    "rejected": "تایید نشده",
    "denied": "تایید نشده",
    "pending": "درحال بررسی",
    "in_review": "درحال بررسی",
    # FA variants
    "تایید نهایی": "تایید شده",
}

_SETTLEMENT_METHOD_MAP = {
    # EN
    "cash": "نقد",
    "bond": "اسناد خزانه",
    "ebond": "اسناد خزانه",
    "treasury_bond": "اسناد خزانه",
    # FA variants
    "نقدی": "نقد",
}

# =========================================================
# Base Schema
# =========================================================

class FinancialInfoBase(BaseModel):
    # شناسه‌ها
    company_id: str = Field(..., description="شناسه ملی شرکت")
    record_number: int = Field(..., description="شماره ردیف صورت‌وضعیت (>=1)")
    stage: int = Field(..., description="شماره مرحله (>=1)")

    # داده‌های ثابت صورت‌وضعیت
    invoice_number: Optional[str] = Field(None, description="شماره صورت‌وضعیت")
    invoice_type: Literal["پیش‌پرداخت", "علی‌الحساب", "موقت", "قطعی", "تعدیل"] = Field(
        ..., description="نوع صورت‌وضعیت"
    )
    invoice_amount: float = Field(..., ge=0, description="مبلغ صورت‌وضعیت")
    allocation_amount: Optional[float] = Field(0, ge=0, description="مبلغ تخصیص‌یافته")

    # اطلاعات نامه/فرآیند
    request_number: Optional[str] = Field(None, description="شماره نامه درخواست")
    request_date: Optional[str] = Field(None, description="تاریخ نامه درخواست (مثلاً 1403/01/15)")
    request_result: Optional[Literal["تایید شده", "تایید نشده", "درحال بررسی"]] = Field(
        None, description="نتیجه درخواست"
    )
    settlement_method: Optional[Literal["نقد", "اسناد خزانه"]] = Field(
        None, description="روش تسویه"
    )

    # مقادیر مرحله‌ای
    paid_amount: float = Field(..., ge=0, description="مبلغ پرداخت‌شده در این مرحله")
    advance_amortization: Optional[float] = Field(0, ge=0, description="استهلاک پیش‌پرداخت در این مرحله")
    partial_amortization: Optional[float] = Field(0, ge=0, description="استهلاک علی‌الحساب در این مرحله")

    # اعتبارسنجی پایه
    @validator("record_number", "stage")
    def _pos_ints(cls, v):
        if v is None or v <= 0:
            raise ValueError("record_number و stage باید بزرگ‌تر از صفر باشند.")
        return v

    # نرمال‌سازی‌های کلیدی
    @validator("invoice_type", pre=True)
    def _normalize_invoice_type(cls, v):
        s = _norm_fa(v)
        if s in ("پیش‌پرداخت", "علی‌الحساب", "موقت", "قطعی", "تعدیل"):
            return s
        # تلاش برای نگاشت مستقیم یا بدون فاصله
        key = (s or "")
        return (_INVOICE_TYPE_MAP.get(key)
                or _INVOICE_TYPE_MAP.get(key.replace(" ", ""))
                or s)


    @validator("request_result", pre=True)
    def _normalize_request_result(cls, v):
        if v is None:
            return None
        s = _norm_fa(v)
        if s in ("تایید شده", "تایید نشده", "درحال بررسی"):
            return s
        return _REQUEST_RESULT_MAP.get((s or "").lower(), s)

    @validator("settlement_method", pre=True)
    def _normalize_settlement_method(cls, v):
        if v is None:
            return None
        s = _norm_fa(v)
        if s in ("نقد", "اسناد خزانه"):
            return s
        return _SETTLEMENT_METHOD_MAP.get((s or "").lower(), s)

# =========================================================
# Create / Update
# =========================================================

class FinancialInfoCreate(FinancialInfoBase):
    """ورودی ایجاد مرحله جدید از یک صورت‌وضعیت."""
    pass

class FinancialInfoUpdate(BaseModel):
    """
    ورودی ویرایش مرحله موجود (PUT/PATCH) — همه فیلدها اختیاری‌اند.
    """
    company_id: Optional[str]
    record_number: Optional[int]
    stage: Optional[int]

    invoice_number: Optional[str]
    invoice_type: Optional[str]
    invoice_amount: Optional[float]
    allocation_amount: Optional[float]

    request_number: Optional[str]
    request_date: Optional[str]
    request_result: Optional[str]
    settlement_method: Optional[str]

    paid_amount: Optional[float]
    advance_amortization: Optional[float]
    partial_amortization: Optional[float]

    @validator("record_number", "stage")
    def _pos_ints_optional(cls, v):
        if v is not None and v <= 0:
            raise ValueError("record_number و stage باید بزرگ‌تر از صفر باشند.")
        return v

    # اگر این سه فیلد در Update ارسال شوند، استانداردسازی شوند
    @validator("invoice_type", "request_result", "settlement_method", pre=True)
    def _normalize_optionals(cls, v, field):
        if v is None:
            return None
        if field.name == "invoice_type":
            return FinancialInfoBase._normalize_invoice_type(v)  # type: ignore
        if field.name == "request_result":
            return FinancialInfoBase._normalize_request_result(v)  # type: ignore
        if field.name == "settlement_method":
            return FinancialInfoBase._normalize_settlement_method(v)  # type: ignore
        return v

# =========================================================
# Computed / Response
# =========================================================

class FinancialInfoComputed(BaseModel):
    remaining_invoice: float
    remaining_advance: float
    remaining_partial: float
    remaining_allocation: float
    contractor_credit: float
    contractor_debit: float
    total_paid_invoices: float

class FinancialInfoResponse(FinancialInfoBase, FinancialInfoComputed):
    """
    خروجی یک رکورد + فیلد اختیاری project برای نمایش در فرانت.
    نکته: برای جلوگیری از خطای from_orm در Pydantic v1، هر مقدار غیر-دیکشنری به None تبدیل می‌شود.
    """
    project: Optional[Dict[str, Any]] = None

    # کلید: جلوگیری از ValidationError هنگام from_orm(info) اگر info.project یک ORM باشد
    @validator("project", pre=True, always=True)
    def _project_must_be_dict(cls, v):
        if v is None or isinstance(v, dict):
            return v
        # اگر ORM/مدل بود، فعلاً None برگردان؛ بعداً در endpoint خودمان dict ست می‌کنیم
        return None

    class Config:
        orm_mode = True

class FinancialInfoListResponse(BaseModel):
    items: List[FinancialInfoResponse]
    total: int

    class Config:
        orm_mode = True

# =========================================================
# سازگاری عقب‌رو
# =========================================================

class FinancialInfo(FinancialInfoResponse):
    """Alias برای سازگاری با کدهای قدیمی که از FinancialInfo استفاده می‌کردند."""
    pass
