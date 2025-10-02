from sqlalchemy import Column, Integer, String, Float, ForeignKey
from database.db import Base

class Guarantee(Base):
    __tablename__ = "guarantees"

    company_id = Column(String, ForeignKey("projects.company_id"), primary_key=True, index=True)
    record_number = Column(String, primary_key=True)
    guarantee_type = Column(String, nullable=False)
    guarantee_category = Column(String, nullable=True)
    guarantee_number = Column(String, nullable=True)
    guarantee_date = Column(String, nullable=True)
    guarantee_amount = Column(Float, nullable=True)
    guarantee_bank = Column(String, nullable=True)
    guarantee_expiry = Column(String, nullable=True)
    deposit_type = Column(String, nullable=True)
    deposit_date = Column(String, nullable=True)
    deposit_amount = Column(Float, nullable=True)
    deposit_release_reason = Column(String, nullable=True)
    deposit_released_amount = Column(Float, nullable=True)
    deposit_release_date = Column(String, nullable=True)

    def __repr__(self) -> str:
        return f"<Guarantee(company_id='{self.company_id}', record_number='{self.record_number}')>"