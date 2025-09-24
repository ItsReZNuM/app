from pydantic import BaseModel
from typing import Optional

class InvoiceRecordBase(BaseModel):
    company_id: str
    record_number: int
    invoice_number: Optional[str] = None
    invoice_type: str
    invoice_amount: int

class InvoiceRecordCreate(InvoiceRecordBase):
    pass

class InvoiceRecordUpdate(InvoiceRecordBase):
    company_id: Optional[str] = None
    record_number: Optional[int] = None
    invoice_type: Optional[str] = None
    invoice_amount: Optional[int] = None

class InvoiceRecord(InvoiceRecordBase):
    class Config:
        orm_mode = True