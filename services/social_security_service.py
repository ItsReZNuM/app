from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.database.models.social_security import SocialSecurity
from app.database.models.ProjectDB import Project
import locale
from typing import Dict, Any, Optional, List
from sqlalchemy.exc import SQLAlchemyError

locale.setlocale(locale.LC_ALL, '')

class SocialSecurityService:
    """
    Service class for managing social security records.
    Handles creation, retrieval, updating and deletion of social security records.
    """
    
    @staticmethod
    def create_or_update_social_security(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create or update a social security record.
        
        Args:
            db: Database session
            data: Social security data
            
        Returns:
            Dict: Dictionary containing the record and formatted values
            
        Raises:
            HTTPException: If validation fails or database error occurs
        """
        try:
            # Validate company exists
            SocialSecurityService._validate_company(db, data["company_id"])
            
            # Validate and process numeric fields
            processed_data = SocialSecurityService._process_input_data(data)
            
            # Check if record exists
            existing = db.query(SocialSecurity).filter_by(
                company_id=processed_data["company_id"],
                record_number=processed_data["record_number"]
            ).first()
            
            if existing:
                # Update existing record
                for key, value in processed_data.items():
                    setattr(existing, key, value)
                db.commit()
                db.refresh(existing)
                record = existing
            else:
                # Create new record
                record = SocialSecurity(**processed_data)
                db.add(record)
                db.commit()
                db.refresh(record)
            
            # Format numeric fields for display
            formatted = SocialSecurityService._format_numeric_fields(record)
            
            return {
                "social_security": record,
                "formatted": formatted
            }
            
        except HTTPException:
            raise
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"خطای پایگاه داده: {str(e)}"
            )
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"خطای ناشناخته در پردازش اطلاعات بیمه: {str(e)}"
            )

    @staticmethod
    def get_social_security(db: Session, company_id: str, record_number: int) -> SocialSecurity:
        """
        Get a specific social security record.
        
        Args:
            db: Database session
            company_id: Company national ID
            record_number: Record number
            
        Returns:
            SocialSecurity: The requested record
            
        Raises:
            HTTPException: If record not found or database error occurs
        """
        try:
            record = db.query(SocialSecurity).filter_by(
                company_id=company_id,
                record_number=record_number
            ).first()
            
            if not record:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="اطلاعات بیمه یافت نشد"
                )
                
            return record
            
        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"خطای پایگاه داده در دریافت اطلاعات بیمه: {str(e)}"
            )

    @staticmethod
    def get_social_securities_by_company(db: Session, company_id: str) -> List[SocialSecurity]:
        """
        Get all social security records for a company.
        
        Args:
            db: Database session
            company_id: Company national ID
            
        Returns:
            List[SocialSecurity]: List of records
            
        Raises:
            HTTPException: If no records found or database error occurs
        """
        try:
            records = db.query(SocialSecurity).filter_by(company_id=company_id).all()
            
            if not records:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="هیچ اطلاعات بیمه‌ای برای این شرکت یافت نشد"
                )
                
            return records
            
        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"خطای پایگاه داده در دریافت لیست بیمه: {str(e)}"
            )

    @staticmethod
    def delete_social_security(db: Session, company_id: str, record_number: int) -> None:
        """
        Delete a social security record.
        
        Args:
            db: Database session
            company_id: Company national ID
            record_number: Record number
            
        Raises:
            HTTPException: If record not found or database error occurs
        """
        try:
            record = db.query(SocialSecurity).filter_by(
                company_id=company_id,
                record_number=record_number
            ).first()
            
            if not record:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="اطلاعات بیمه یافت نشد"
                )
                
            db.delete(record)
            db.commit()
            
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"خطای پایگاه داده در حذف اطلاعات بیمه: {str(e)}"
            )

    @staticmethod
    def _validate_company(db: Session, company_id: str) -> None:
        """
        Validate that company exists.
        
        Args:
            db: Database session
            company_id: Company national ID
            
        Raises:
            HTTPException: If company not found
        """
        company = db.query(Project).filter_by(company_id=company_id).first()
        if not company:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="شناسه ملی شرکت معتبر نیست!"
            )

    @staticmethod
    def _process_input_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and validate input data.
        
        Args:
            data: Input data dictionary
            
        Returns:
            Dict: Processed data dictionary
            
        Raises:
            HTTPException: If validation fails
        """
        processed = data.copy()
        
        # Validate and process record_number
        if "record_number" in processed:
            try:
                processed["record_number"] = int(processed["record_number"])
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="شماره ردیف باید عدد معتبر باشد!"
                )
        
        # Validate and process insurance_amount
        if "insurance_amount" in processed and processed["insurance_amount"]:
            try:
                processed["insurance_amount"] = int(float(processed["insurance_amount"]))
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="مبلغ بیمه باید عدد معتبر باشد!"
                )
        else:
            processed["insurance_amount"] = None
        
        return processed

    @staticmethod
    def _format_numeric_fields(record: SocialSecurity) -> Dict[str, str]:
        """
        Format numeric fields for display.
        
        Args:
            record: SocialSecurity record
            
        Returns:
            Dict: Dictionary with formatted values
        """
        formatted = {}
        
        if record.insurance_amount is not None:
            formatted["insurance_amount"] = locale.format_string("%d", record.insurance_amount, grouping=True)
        else:
            formatted["insurance_amount"] = ""
            
        return formatted