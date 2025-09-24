from sqlalchemy import Column, String, Float, Integer
from sqlalchemy.orm import relationship
from app.database.db import Base

class Project(Base):
    __tablename__ = "projects"

    company_id = Column(String, primary_key=True, index=True)
    company_name = Column(String, nullable=False)
    subject = Column(String, nullable=True)
    project_code = Column(String, nullable=True)
    contract_number = Column(String, nullable=True)
    contract_date = Column(String, nullable=True)
    initial_amount = Column(Float, nullable=True)
    change_amount = Column(Float, nullable=True)
    start_date = Column(String, nullable=True)
    duration = Column(Integer, nullable=True)
    extension_date = Column(String, nullable=True)
    contact_numbers = Column(String, nullable=True)
    archive_number = Column(String, nullable=True)
    tax_clearance = Column(Integer, default=0, nullable=False)
    contract_type = Column(String, nullable=True)
    project_status = Column(String, nullable=True)

    financial_infos = relationship("FinancialInfo", order_by="FinancialInfo.stage", back_populates="project")

    def __repr__(self) -> str:
        return f"<Project(company_id='{self.company_id}', company_name='{self.company_name}')>"