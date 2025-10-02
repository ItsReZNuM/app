from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from database.db import Base

class FinancialInfo(Base):
    __tablename__ = "financial_info"

    company_id = Column(String, ForeignKey("projects.company_id"), primary_key=True, index=True)
    record_number = Column(Integer, primary_key=True, index=True)
    stage = Column(Integer, primary_key=True, nullable=False, default=1)
    request_number = Column(String, nullable=True)
    request_date = Column(String, nullable=True)
    invoice_number = Column(String, nullable=True)
    invoice_type = Column(String, nullable=True)
    invoice_amount = Column(Float, default=0.0)
    allocation_amount = Column(Float, default=0.0)
    request_result = Column(String, nullable=True)
    settlement_method = Column(String, nullable=True)
    advance_amortization = Column(Float, default=0.0)
    partial_amortization = Column(Float, default=0.0)
    allocation_usage = Column(Float, default=0.0)
    paid_amount = Column(Float, default=0.0)
    remaining_invoice = Column(Float, default=0.0)
    remaining_advance = Column(Float, default=0.0)
    remaining_partial = Column(Float, default=0.0)
    remaining_allocation = Column(Float, nullable=True, default=0.0)
    contractor_credit = Column(Float, default=0.0)
    contractor_debit = Column(Float, default=0.0)
    total_paid_invoices = Column(Float, default=0.0)

    project = relationship("Project", back_populates="financial_infos")

    def __repr__(self) -> str:
        return f"<FinancialInfo(company_id='{self.company_id}', record_number={self.record_number}, stage={self.stage})>"