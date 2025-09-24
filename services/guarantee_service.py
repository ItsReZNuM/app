from sqlalchemy.orm import Session
from fastapi import HTTPException
from fastapi import status
from app.database.models.guarantee import Guarantee
from app.database.models.ProjectDB import Project
import locale
from typing import Dict, Any, List

locale.setlocale(locale.LC_ALL, '')

def validate_company(db: Session, company_id: str) -> Project:
    """Validate that company exists in database."""
    project = db.query(Project).filter_by(company_id=company_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="شناسه ملی شرکت معتبر نیست!"
        )
    return project

def validate_numeric_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and convert numeric fields to integers."""
    numeric_fields = ["guarantee_amount", "deposit_amount", "deposit_released_amount"]
    for field in numeric_fields:
        if field in data and data[field]:
            try:
                # Remove any formatting (like commas) before conversion
                value = str(data[field]).replace(',', '')
                data[field] = int(float(value))
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"مقدار {field} باید عدد معتبر باشد!"
                )
        else:
            data[field] = None
    return data

def validate_guarantee_type(data: Dict[str, Any]) -> None:
    """Validate guarantee type is one of allowed values."""
    guarantee_type = data.get("guarantee_type", "")
    if guarantee_type not in ["", "ضمانت‌نامه", "سپرده"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="نوع تضمین نامعتبر است!"
        )

def format_numeric_values(data: Dict[str, Any]) -> Dict[str, str]:
    """Format numeric values for display with locale formatting."""
    numeric_fields = ["guarantee_amount", "deposit_amount", "deposit_released_amount"]
    formatted = {}
    for field in numeric_fields:
        if data.get(field) is not None:
            formatted[field] = locale.format_string("%d", data[field], grouping=True)
        else:
            formatted[field] = ""
    return formatted

def get_guarantee_by_id(db: Session, company_id: str, record_number: int) -> Guarantee:
    """Get a guarantee record by company ID and record number."""
    guarantee = db.query(Guarantee).filter_by(
        company_id=company_id, 
        record_number=record_number
    ).first()
    if not guarantee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="تضمین یافت نشد"
        )
    return guarantee

def get_guarantees_by_company(db: Session, company_id: str) -> List[Guarantee]:
    """Get all guarantees for a specific company."""
    guarantees = db.query(Guarantee).filter_by(company_id=company_id).all()
    if not guarantees:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="هیچ تضمینی برای این شرکت یافت نشد"
        )
    return guarantees

def delete_guarantee_record(db: Session, company_id: str, record_number: int) -> None:
    """Delete a guarantee record from database."""
    guarantee = get_guarantee_by_id(db, company_id, record_number)
    db.delete(guarantee)
    db.commit()

def create_or_update_guarantee(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create or update a guarantee record with proper validation and formatting.
    
    Args:
        db: Database session
        data: Dictionary containing guarantee data
        
    Returns:
        Dictionary containing:
            - guarantee: Created/updated guarantee record
            - formatted: Formatted numeric values for display
    """
    try:
        # Validate input data
        validate_company(db, data["company_id"])
        validate_guarantee_type(data)
        data = validate_numeric_fields(data)
        
        # Format numeric values for display
        formatted = format_numeric_values(data)
        
        # Check for existing guarantee
        existing = db.query(Guarantee).filter_by(
            company_id=data["company_id"], 
            record_number=data["record_number"]
        ).first()
        
        if existing:
            # Update existing record
            for key, value in data.items():
                setattr(existing, key, value)
        else:
            # Create new record
            existing = Guarantee(**data)
            db.add(existing)
        
        db.commit()
        db.refresh(existing)
        
        return {"guarantee": existing, "formatted": formatted}
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در پردازش تضمین: {str(e)}"
        )