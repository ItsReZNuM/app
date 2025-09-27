from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database.db import get_db
from app.schemas.reminder import Reminder, ReminderCreate, ReminderUpdate
from app.services.reminder_service import ReminderService

router = APIRouter(
    prefix="/reminders",
    tags=["Reminders"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Not authenticated"},
        status.HTTP_403_FORBIDDEN: {"description": "Not authorized"},
        status.HTTP_404_NOT_FOUND: {"description": "Not found"}
    }
)

@router.post(
    "/",
    response_model=Reminder,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"description": "Reminder created successfully"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid input data"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"}
    }
)
def create_reminder(reminder: ReminderCreate, db: Session = Depends(get_db)):
    """Create a new reminder with optional jalali and gregorian dates."""
    return ReminderService.create_reminder(db, reminder)


@router.get(
    "/",
    response_model=List[Reminder],
    responses={
        status.HTTP_200_OK: {"description": "List of all reminders"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"}
    }
)
def read_reminders(db: Session = Depends(get_db)):
    """Get all reminders ordered by created_at descending."""
    return ReminderService.get_reminders(db)


@router.get(
    "/today",
    response_model=List[Reminder],
    responses={
        status.HTTP_200_OK: {"description": "List of today's reminders"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"}
    }
)
def read_today_reminders(db: Session = Depends(get_db)):
    """Get all reminders for today (regardless of status)."""
    return ReminderService.get_today_reminders(db)


@router.get(
    "/pending",
    response_model=List[Reminder],
    responses={
        status.HTTP_200_OK: {"description": "List of pending reminders"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"}
    }
)
def read_pending_reminders(db: Session = Depends(get_db)):
    """Get pending reminders for today."""
    return ReminderService.get_pending_reminders(db)


@router.put(
    "/{reminder_id}/read",
    response_model=Reminder,
    responses={
        status.HTTP_200_OK: {"description": "Reminder marked as read"},
        status.HTTP_404_NOT_FOUND: {"description": "Reminder not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"}
    }
)
def mark_as_read(reminder_id: int, db: Session = Depends(get_db)):
    """Mark a reminder as read."""
    reminder = ReminderService.mark_reminder_as_read(db, reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return reminder


@router.delete(
    "/{reminder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_204_NO_CONTENT: {"description": "Reminder deleted successfully"},
        status.HTTP_404_NOT_FOUND: {"description": "Reminder not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"}
    }
)
def delete_reminder(reminder_id: int, db: Session = Depends(get_db)):
    """Delete a reminder."""
    ReminderService.delete_reminder(db, reminder_id)
    return None