from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import importlib

class ProjectBase(BaseModel):
    company_id: str
    company_name: str
    subject: Optional[str] = None
    project_code: Optional[str] = None
    contract_number: Optional[str] = None
    contract_date: Optional[str] = None
    initial_amount: Optional[float] = None
    change_amount: Optional[float] = None
    start_date: Optional[str] = None
    duration: Optional[int] = None
    extension_date: Optional[str] = None
    contact_numbers: Optional[str] = None
    archive_number: Optional[str] = None
    tax_clearance: int = 0
    contract_type: Optional[str] = None
    project_status: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(ProjectBase):
    company_id: Optional[str] = None
    company_name: Optional[str] = None

class ProjectWithoutFinancials(ProjectBase):
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        orm_mode = True

class Project(ProjectBase):
    financial_infos: Optional[List["FinancialInfo"]] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        orm_mode = True

# رفع forward reference با استفاده از lazy import
try:
    financial_info_module = importlib.import_module("schemas.financial_info_schema")
    Project.update_forward_refs(FinancialInfo=financial_info_module.FinancialInfo)
except ImportError as e:
    raise ImportError(f"خطا در بارگذاری ماژول FinancialInfo: {str(e)}")