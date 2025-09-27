from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ReminderBase(BaseModel):
    subject: str # فیلد جدید: موضوع (اجباری)
    message: Optional[str] = None # اکنون اختیاری است
    jalali_date: Optional[str] = None # اکنون اختیاری است
    gregorian_date: Optional[str] = None # اکنون اختیاری است (زیرا وابسته به jalali_date است)
    status: int = 0

class ReminderCreate(ReminderBase):
    pass

class ReminderUpdate(BaseModel):
    subject: Optional[str] = None # موضوع نیز می‌تواند در به‌روزرسانی اختیاری باشد
    message: Optional[str] = None
    gregorian_date: Optional[str] = None
    jalali_date: Optional[str] = None
    status: Optional[int] = None

class Reminder(ReminderBase):
    id: int
    created_at: datetime
    
    class Config:
        orm_mode = True