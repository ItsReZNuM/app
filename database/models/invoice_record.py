from sqlalchemy import Column, Integer, String, Float, ForeignKey
from app.database.db import Base

class InvoiceRecord(Base):
    __tablename__ = "invoice_records"

    company_id = Column(String, ForeignKey("projects.company_id"), primary_key=True, index=True)
    record_number = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, nullable=True)
    invoice_type = Column(String, nullable=False)
    invoice_amount = Column(Float, nullable=False)

    def __repr__(self) -> str:
        return f"<InvoiceRecord(company_id='{self.company_id}', record_number={self.record_number})>"