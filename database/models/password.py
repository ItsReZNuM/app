from sqlalchemy import Column, String
from database.db import Base

class Password(Base):
    __tablename__ = "passwords"

    id = Column(String, primary_key=True, default="main_password")
    password = Column(String, nullable=False)

    def __repr__(self):
        return f"<Password(id='{self.id}')>"