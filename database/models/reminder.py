from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database.db import Base # فرض بر این است که Base از این مسیر وارد می‌شود

class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String, nullable=False) # فیلد جدید: موضوع (اجباری)
    message = Column(String, nullable=True) # اکنون می‌تواند Null باشد
    gregorian_date = Column(String, nullable=True) # اکنون می‌تواند Null باشد
    jalali_date = Column(String, nullable=True) # اکنون می‌تواند Null باشد
    status = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        # تغییر در __repr__ برای نمایش subject
        return f"<Reminder(id={self.id}, subject='{self.subject[:20]}...', jalali_date='{self.jalali_date}')>"