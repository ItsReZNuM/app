from pydantic import BaseModel
from typing import Optional

class SocialSecurityBase(BaseModel):
    company_id: str
    record_number: int
    insurance_amount: Optional[int] = None
    payment_method: Optional[str] = None

class SocialSecurityCreate(SocialSecurityBase):
    pass

class SocialSecurityUpdate(SocialSecurityBase):
    company_id: Optional[str] = None
    record_number: Optional[int] = None

class SocialSecurity(SocialSecurityBase):
    class Config:
        orm_mode = True