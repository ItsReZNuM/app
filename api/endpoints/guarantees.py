from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database.db import get_db
from schemas.guarantee import Guarantee, GuaranteeCreate, GuaranteeUpdate
from services.guarantee_service import (
    create_or_update_guarantee,
    get_guarantee_by_id,
    get_guarantees_by_company,
    delete_guarantee_record
)
from fastapi import status

router = APIRouter()

@router.post(
    "/guarantees/", 
    response_model=Guarantee,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Invalid input data"},
        404: {"description": "Company not found"},
        500: {"description": "Internal server error"}
    }
)
def create_guarantee(guarantee: GuaranteeCreate, db: Session = Depends(get_db)):
    """
    Create a new guarantee record.
    
    Args:
        guarantee: GuaranteeCreate schema containing guarantee data
        db: Database session
        
    Returns:
        Created guarantee record
    """
    try:
        result = create_or_update_guarantee(db, guarantee.dict())
        return result["guarantee"]
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در ایجاد تضمین: {str(e)}"
        )

@router.get(
    "/guarantees/{company_id}/{record_number}", 
    response_model=Guarantee,
    responses={
        404: {"description": "Guarantee not found"},
        500: {"description": "Internal server error"}
    }
)
def read_guarantee(company_id: str, record_number: int, db: Session = Depends(get_db)):
    """
    Get a specific guarantee record by company ID and record number.
    
    Args:
        company_id: Company national ID
        record_number: Guarantee record number
        db: Database session
        
    Returns:
        Guarantee record if found
    """
    try:
        guarantee = get_guarantee_by_id(db, company_id, record_number)
        return guarantee
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در دریافت اطلاعات تضمین: {str(e)}"
        )

@router.get(
    "/guarantees/{company_id}", 
    response_model=List[Guarantee],
    responses={
        404: {"description": "No guarantees found for company"},
        500: {"description": "Internal server error"}
    }
)
def read_guarantees_by_company(company_id: str, db: Session = Depends(get_db)):
    """
    Get all guarantees for a specific company.
    
    Args:
        company_id: Company national ID
        db: Database session
        
    Returns:
        List of guarantee records for the company
    """
    try:
        guarantees = get_guarantees_by_company(db, company_id)
        return guarantees
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در دریافت لیست تضامین: {str(e)}"
        )

@router.put(
    "/guarantees/{company_id}/{record_number}", 
    response_model=Guarantee,
    responses={
        400: {"description": "Invalid input data"},
        404: {"description": "Guarantee not found"},
        500: {"description": "Internal server error"}
    }
)
def update_guarantee(
    company_id: str,
    record_number: int,
    guarantee: GuaranteeUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing guarantee record.
    
    Args:
        company_id: Company national ID
        record_number: Guarantee record number
        guarantee: GuaranteeUpdate schema with updated fields
        db: Database session
        
    Returns:
        Updated guarantee record
    """
    try:
        # Check if guarantee exists
        existing = get_guarantee_by_id(db, company_id, record_number)
        
        # Prepare update data
        data = guarantee.dict(exclude_unset=True)
        data["company_id"] = company_id
        data["record_number"] = record_number
        
        # Update guarantee
        result = create_or_update_guarantee(db, data)
        return result["guarantee"]
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در به‌روزرسانی تضمین: {str(e)}"
        )

@router.delete(
    "/guarantees/{company_id}/{record_number}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"description": "Guarantee not found"},
        500: {"description": "Internal server error"}
    }
)
def delete_guarantee(company_id: str, record_number: int, db: Session = Depends(get_db)):
    """
    Delete a guarantee record.
    
    Args:
        company_id: Company national ID
        record_number: Guarantee record number
        db: Database session
    """
    try:
        delete_guarantee_record(db, company_id, record_number)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در حذف تضمین: {str(e)}"
        )