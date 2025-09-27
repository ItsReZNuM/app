from datetime import datetime
from sqlalchemy.orm import Session
from app.database.models.reminder import Reminder as ReminderDB
from app.schemas.reminder import ReminderCreate, ReminderUpdate


class ReminderService:
    @staticmethod
    def create_reminder(db: Session, reminder: ReminderCreate):
        """
        Create a new reminder.
        Since gregorian_date is stored as String, we store it directly.
        """
        new_reminder = ReminderDB(
            subject=reminder.subject,
            message=reminder.message,
            jalali_date=reminder.jalali_date,
            gregorian_date=reminder.gregorian_date,  # ذخیره مستقیم به عنوان رشته
            status=reminder.status
        )

        db.add(new_reminder)
        db.commit()
        db.refresh(new_reminder)
        return new_reminder

    @staticmethod
    def get_reminders(db: Session):
        """
        Return all reminders ordered by created_at descending.
        """
        return db.query(ReminderDB).order_by(ReminderDB.created_at.desc()).all()

    @staticmethod
    def get_today_reminders(db: Session):
        """
        Return all reminders for today (regardless of status).
        Since gregorian_date is stored as String, we compare as strings.
        """
        today_str = datetime.now().strftime('%Y-%m-%d')
        
        return (
            db.query(ReminderDB)
            .filter(ReminderDB.gregorian_date != None)
            .filter(ReminderDB.gregorian_date == today_str)
            .order_by(ReminderDB.created_at.desc())
            .all()
        )

    @staticmethod
    def get_pending_reminders(db: Session):
        """
        Return reminders that have a gregorian_date == today and status == 0.
        Since gregorian_date is stored as String, we compare as strings.
        """
        today_str = datetime.now().strftime('%Y-%m-%d')
        
        return (
            db.query(ReminderDB)
            .filter(ReminderDB.gregorian_date != None)
            .filter(ReminderDB.gregorian_date == today_str)
            .filter(ReminderDB.status == 0)
            .all()
        )

    @staticmethod
    def mark_reminder_as_read(db: Session, reminder_id: int):
        """
        Mark a reminder as read (status = 1).
        """
        reminder = db.query(ReminderDB).filter(ReminderDB.id == reminder_id).first()
        if not reminder:
            return None
        reminder.status = 1
        db.commit()
        db.refresh(reminder)
        return reminder

    @staticmethod
    def delete_reminder(db: Session, reminder_id: int):
        """
        Delete a reminder by ID.
        """
        reminder = db.query(ReminderDB).filter(ReminderDB.id == reminder_id).first()
        if reminder:
            db.delete(reminder)
            db.commit()