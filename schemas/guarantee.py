from pydantic import BaseModel
from typing import Optional

class GuaranteeBase(BaseModel):
    company_id: str
    record_number: str
    guarantee_type: str
    guarantee_category: Optional[str] = None
    guarantee_number: Optional[str] = None
    guarantee_date: Optional[str] = None
    guarantee_amount: Optional[int] = None
    guarantee_bank: Optional[str] = None
    guarantee_expiry: Optional[str] = None
    deposit_type: Optional[str] = None
    deposit_date: Optional[str] = None
    deposit_amount: Optional[int] = None
    deposit_release_reason: Optional[str] = None
    deposit_released_amount: Optional[int] = None
    deposit_release_date: Optional[str] = None

class GuaranteeCreate(GuaranteeBase):
    pass

class GuaranteeUpdate(GuaranteeBase):
    company_id: Optional[str] = None
    record_number: Optional[str] = None
    guarantee_type: Optional[str] = None

class Guarantee(GuaranteeBase):
    class Config:
        orm_mode = True