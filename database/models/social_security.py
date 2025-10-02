from sqlalchemy import Column, Integer, String, Float, ForeignKey
from database.db import Base

class SocialSecurity(Base):
    __tablename__ = "social_security"

    company_id = Column(String, ForeignKey("projects.company_id"), primary_key=True, index=True)
    record_number = Column(Integer, primary_key=True)
    insurance_amount = Column(Float, nullable=True)
    payment_method = Column(String, nullable=True)

    def __repr__(self) -> str:
        return f"<SocialSecurity(company_id='{self.company_id}', record_number={self.record_number})>"