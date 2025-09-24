from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.database.models.reminder import Reminder
import jdatetime
import datetime
from typing import Optional
from decimal import Decimal
from sqlalchemy.exc import SQLAlchemyError

class ReminderService:
    """Service class for managing reminders with jalali and gregorian dates."""
    
    @staticmethod
    def create_reminder(db: Session, message: str, jalali_date: str) -> Reminder:
        """Create a new reminder with jalali and gregorian dates."""
        try:
            # Validate jalali date format
            j_date = ReminderService._validate_jalali_date(jalali_date)
            g_date = j_date.togregorian()
            today_gregorian = datetime.date.today()

            # Check if date is in the past
            if g_date < today_gregorian:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="تاریخ یادآوری نمی‌تواند گذشته باشد!"
                )

            # Create and save reminder
            reminder = Reminder(
                message=message,
                jalali_date=jalali_date,
                gregorian_date=g_date.strftime("%Y-%m-%d"),
                status=0
            )
            
            db.add(reminder)
            db.commit()
            db.refresh(reminder)
            return reminder
            
        except HTTPException:
            raise
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="فرمت تاریخ نامعتبر است. لطفاً به‌صورت yyyy-mm-dd وارد کنید."
            )
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"خطا در ذخیره یادآوری در پایگاه داده: {str(e)}"
            )
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"خطای ناشناخته در ایجاد یادآوری: {str(e)}"
            )

    @staticmethod
    def get_reminders(db: Session) -> list[Reminder]:
        """Get all reminders ordered by created_at descending."""
        try:
            return db.query(Reminder).order_by(Reminder.created_at.desc()).all()
        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"خطا در بارگذاری یادآوری‌ها از پایگاه داده: {str(e)}"
            )

    @staticmethod
    def get_pending_reminders(db: Session) -> list[Reminder]:
        """Get pending reminders for today."""
        try:
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            return db.query(Reminder).filter(
                Reminder.gregorian_date == today_str,
                Reminder.status == 0
            ).all()
        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"خطا در بررسی یادآوری‌های امروز: {str(e)}"
            )

    @staticmethod
    def mark_reminder_as_read(db: Session, reminder_id: int) -> Reminder:
        """Mark a reminder as read."""
        try:
            reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
            if not reminder:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="یادآوری یافت نشد"
                )
                
            reminder.status = 1
            db.commit()
            db.refresh(reminder)
            return reminder
            
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"خطا در به‌روزرسانی وضعیت یادآوری: {str(e)}"
            )

    @staticmethod
    def delete_reminder(db: Session, reminder_id: int) -> None:
        """Delete a reminder."""
        try:
            reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
            if not reminder:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="یادآوری یافت نشد"
                )
                
            db.delete(reminder)
            db.commit()
            
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"خطا در حذف یادآوری: {str(e)}"
            )

    @staticmethod
    def _validate_jalali_date(jalali_date: str) -> jdatetime.date:
        """Validate jalali date format and return jdatetime.date object."""
        try:
            return jdatetime.date.fromisoformat(jalali_date)
        except ValueError:
            raise ValueError("فرمت تاریخ نامعتبر است. لطفاً به‌صورت yyyy-mm-dd وارد کنید.")