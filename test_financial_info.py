# Tests for the main application
import pytest
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from project_management.app.database.db import Base, get_db
from project_management.app.main import app

# دیتابیس تست (اینجا SQLite در حافظه برای سرعت)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_financial_info.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override کردن get_db برای تست
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# ساخت جداول تست
Base.metadata.create_all(bind=engine)

@pytest.mark.asyncio
async def test_create_financial_info():
    """
    تست ایجاد رکورد مالی جدید با تمام فیلدهای لازم.
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {
            "company_id": "C123",
            "record_number": 1,
            "stage": 1,
            "invoice_amount": 1000,
            "paid_amount": 0,  # اینجا باید صفر ثبت بشه، تست باگ قبلی or
            "advance_amortization": 0,
            "partial_amortization": 0,
            "invoice_type": "normal"
        }
        response = await ac.post("/financial_info/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["company_id"] == "C123"
    assert data["paid_amount"] == 0  # این باید صفر بمونه، نه مقدار DB

@pytest.mark.asyncio
async def test_create_duplicate_financial_info():
    """
    تست ایجاد رکورد تکراری (باید ارور بده).
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {
            "company_id": "C123",
            "record_number": 1,
            "stage": 1,
            "invoice_amount": 500
        }
        response = await ac.post("/financial_info/", json=payload)

    assert response.status_code == 400 or response.status_code == 409  # بسته به هندل کدت
    assert "exists" in response.text.lower() or "duplicate" in response.text.lower()

@pytest.mark.asyncio
async def test_post_with_missing_fields():
    """
    تست ارسال حداقل فیلدهای لازم و بررسی پیش‌فرض‌ها.
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {
            "company_id": "C999",
            "record_number": 2,
            "stage": 1
        }
        response = await ac.post("/financial_info/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["invoice_amount"] == 0.0
    assert data["paid_amount"] == 0.0
