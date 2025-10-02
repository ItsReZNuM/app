from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database.db import get_db
from schemas.social_security import SocialSecurity, SocialSecurityCreate, SocialSecurityUpdate
from services.social_security_service import SocialSecurityService
from fastapi.responses import JSONResponse

router = APIRouter(
    prefix="/api/social-security",
    tags=["Social Security"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Not authenticated"},
        status.HTTP_403_FORBIDDEN: {"description": "Not authorized"},
        status.HTTP_404_NOT_FOUND: {"description": "Not found"}
    }
)

@router.post(
    "/",
    response_model=SocialSecurity,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"description": "Social security record created successfully"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid input data"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"}
    }
)
def create_social_security(social_security: SocialSecurityCreate, db: Session = Depends(get_db)):
    """
    Create a new social security record.
    
    Args:
        social_security: Social security data to create
        db: Database session
        
    Returns:
        SocialSecurity: The created social security record
        
    Raises:
        HTTPException: If input validation fails or server error occurs
    """
    try:
        result = SocialSecurityService.create_or_update_social_security(db, social_security.dict())
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "social_security": result["social_security"],
                "formatted": result["formatted"]
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در ایجاد رکورد بیمه تأمین اجتماعی: {str(e)}"
        )

@router.get(
    "/{company_id}/{record_number}",
    response_model=SocialSecurity,
    responses={
        status.HTTP_200_OK: {"description": "Social security record found"},
        status.HTTP_404_NOT_FOUND: {"description": "Social security record not found"}
    }
)
def read_social_security(company_id: str, record_number: int, db: Session = Depends(get_db)):
    """
    Get a specific social security record.
    
    Args:
        company_id: Company national ID
        record_number: Record number
        db: Database session
        
    Returns:
        SocialSecurity: The requested social security record
        
    Raises:
        HTTPException: If record not found
    """
    try:
        social_security = SocialSecurityService.get_social_security(db, company_id, record_number)
        return social_security
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در دریافت اطلاعات بیمه تأمین اجتماعی: {str(e)}"
        )

@router.get(
    "/{company_id}",
    response_model=List[SocialSecurity],
    responses={
        status.HTTP_200_OK: {"description": "List of social security records"},
        status.HTTP_404_NOT_FOUND: {"description": "No records found for this company"}
    }
)
def read_social_securities_by_company(company_id: str, db: Session = Depends(get_db)):
    """
    Get all social security records for a company.
    
    Args:
        company_id: Company national ID
        db: Database session
        
    Returns:
        List[SocialSecurity]: List of social security records
        
    Raises:
        HTTPException: If no records found or server error occurs
    """
    try:
        return SocialSecurityService.get_social_securities_by_company(db, company_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در دریافت لیست بیمه تأمین اجتماعی: {str(e)}"
        )

@router.put(
    "/{company_id}/{record_number}",
    response_model=SocialSecurity,
    responses={
        status.HTTP_200_OK: {"description": "Social security record updated successfully"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid input data"},
        status.HTTP_404_NOT_FOUND: {"description": "Record not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"}
    }
)
def update_social_security(
    company_id: str,
    record_number: int,
    social_security: SocialSecurityUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a social security record.
    
    Args:
        company_id: Company national ID
        record_number: Record number
        social_security: Social security data to update
        db: Database session
        
    Returns:
        SocialSecurity: The updated social security record
        
    Raises:
        HTTPException: If input validation fails, record not found or server error occurs
    """
    try:
        data = social_security.dict(exclude_unset=True)
        data["company_id"] = company_id
        data["record_number"] = record_number
        result = SocialSecurityService.create_or_update_social_security(db, data)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "social_security": result["social_security"],
                "formatted": result["formatted"]
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در به‌روزرسانی رکورد بیمه تأمین اجتماعی: {str(e)}"
        )

@router.delete(
    "/{company_id}/{record_number}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_204_NO_CONTENT: {"description": "Record deleted successfully"},
        status.HTTP_404_NOT_FOUND: {"description": "Record not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"}
    }
)
def delete_social_security(company_id: str, record_number: int, db: Session = Depends(get_db)):
    """
    Delete a social security record.
    
    Args:
        company_id: Company national ID
        record_number: Record number
        db: Database session
        
    Raises:
        HTTPException: If record not found or server error occurs
    """
    try:
        SocialSecurityService.delete_social_security(db, company_id, record_number)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در حذف رکورد بیمه تأمین اجتماعی: {str(e)}"
        )