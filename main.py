from fastapi import FastAPI, Depends, Request, Form, HTTPException, status, Body
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from app.database.db import Base, engine, get_db
from app.api.endpoints import projects, financial_info, guarantees, social_security, reminders
from app.database.models.password import Password
from app.database.models.financial_info_DB import FinancialInfo as FinancialInfoModel
from app.database.models.ProjectDB import Project
from app.database.models.guarantee import Guarantee
from app.database.models.social_security import SocialSecurity
from app.database.models.reminder import Reminder
from app.services.financial_service import calculate_financial_metrics
from app.schemas.financial_info_schema import FinancialInfo
from app.api.endpoints import reports
from app.schemas.project import Project as ProjectSchema
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
import traceback
import logging
from app.schemas.project import ProjectWithoutFinancials as ProjectLite
from app.schemas.financial_info_schema import FinancialInfo
from typing import Optional, Dict, List

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="سامانه مدیریت پروژه", description="مدیریت پروژه‌ها و اطلاعات مالی")

# Define base path for project files
BASE_DIR = Path(__file__).resolve().parent

# Set up Jinja2 for rendering HTML templates
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Mount static files
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key="x7k9m2p8q3a5w1r4t6y8u9i2o4p6a8s9d0f2g3h4j5k6l7",
    session_cookie="session_cookie",
    max_age=3600,
    same_site="lax",
    https_only=False
)

def _to_float(v: Optional[float]) -> float:
    try:
        return float(v or 0.0)
    except Exception:
        logging.warning(f"Invalid float conversion: {v}")
        return 0.0

def _as_record(model) -> Dict:
    """Convert ORM to structure for financial metrics service"""
    return {
        "company_id": model.company_id,
        "record_number": model.record_number,
        "stage": model.stage,
        "invoice_number": model.invoice_number or "",
        "invoice_type": model.invoice_type,
        "invoice_amount": _to_float(model.invoice_amount),
        "allocation_amount": _to_float(model.allocation_amount),
        "paid_amount": _to_float(model.paid_amount),
        "advance_amortization": _to_float(model.advance_amortization),
        "partial_amortization": _to_float(model.partial_amortization),
        # عبور دادن روش تسویه در صورت نیاز سرویس محاسباتی
        "settlement_method": getattr(model, "settlement_method", None),
    }

# Exception handler
@app.exception_handler(Exception)
async def unicorn_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception: {exc}")
    logging.error(traceback.format_exc())
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "خطای داخلی سرور رخ داده است. لطفاً بعداً دوباره امتحان کنید.",
            "error_message": str(exc),
            "traceback": traceback.format_exc().splitlines()
        },
    )

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    return await http_exception_handler(request, exc)

@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(request: Request, exc: RequestValidationError):
    return await request_validation_exception_handler(request, exc)

# Include API routers
app.include_router(projects.router, prefix="/api", tags=["Projects"])
app.include_router(financial_info.router, prefix="/api", tags=["Financial Info"])
app.include_router(guarantees.router, prefix="/api", tags=["Guarantees"])
app.include_router(social_security.router, prefix="/api", tags=["Social Security"])
app.include_router(reminders.router, prefix="/api", tags=["Reminders"])
app.include_router(reports.router)

def check_login(request: Request):
    if not request.session.get("logged_in"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="لطفاً ابتدا وارد شوید",
            headers={"Location": "/login"}
        )
    return True

# Start page
@app.get("/start", response_class=RedirectResponse)
async def start_app():
    return RedirectResponse(url="/login", status_code=303)

# Login page
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, password: str = Form(...), db: Session = Depends(get_db)):
    stored_password = db.query(Password).filter_by(id="main_password").first()
    if not stored_password:
        stored_password = Password(id="main_password", password="admin123")
        db.add(stored_password)
        db.commit()

    if password != stored_password.password:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "رمز عبور نادرست است"}
        )

    request.session["logged_in"] = True
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return response

@app.get("/api/check-login")
async def check_login_status(request: Request):
    if not request.session.get("logged_in"):
        raise HTTPException(status_code=401, detail="لطفاً ابتدا وارد شوید")
    return {"status": "authenticated"}

# Settings page
@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})


@app.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request, logged_in: bool = Depends(check_login)):
    return templates.TemplateResponse("reports.html", {"request": request})

# Change password
@app.post("/settings/change-password")
async def change_password(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    new_password = data.get("new_password")
    if not new_password or len(new_password) < 6:
        raise HTTPException(status_code=400, detail="رمز عبور باید حداقل ۶ کاراکتر باشد")
    stored_password = db.query(Password).filter_by(id="main_password").first()
    if not stored_password:
        stored_password = Password(id="main_password", password=new_password)
        db.add(stored_password)
    else:
        stored_password.password = new_password
    db.commit()
    return {"message": "رمز با موفقیت تغییر یافت"}

# Check password existence
@app.get("/api/check-password")
async def check_password_exists(db: Session = Depends(get_db)):
    stored_password = db.query(Password).filter_by(id="main_password").first()
    return {"has_password": stored_password is not None}

# Reset password
@app.post("/reset-password")
async def reset_password(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    secret_phrase = data.get("secret_phrase")
    DEFAULT_PASSWORD = "admin123"
    SECRET_PHRASE = "admin123"

    if secret_phrase != SECRET_PHRASE:
        raise HTTPException(status_code=401, detail="عبارت خاص نامعتبر است")

    stored_password = db.query(Password).filter_by(id="main_password").first()
    if not stored_password:
        stored_password = Password(id="main_password", password=DEFAULT_PASSWORD)
        db.add(stored_password)
    else:
        stored_password.password = DEFAULT_PASSWORD
    db.commit()
    return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "رمز عبور با موفقیت به 'admin123' ریست شد."})

# Logout
@app.get("/logout", response_class=RedirectResponse)
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

# Home page
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, logged_in: bool = Depends(check_login)):
    return templates.TemplateResponse("index.html", {"request": request})

# Add project page
@app.get("/add-project", response_class=HTMLResponse)
async def add_project_form(request: Request, db: Session = Depends(get_db), logged_in: bool = Depends(check_login)):
    return templates.TemplateResponse("add-project.html", {"request": request})

# Financial details page (fixed: add computed fields)
@app.get("/financial-details/{company_id}", response_class=HTMLResponse)
async def financial_details_form(request: Request, company_id: str, db: Session = Depends(get_db), logged_in: bool = Depends(check_login)):
    company = db.query(Project).filter_by(company_id=company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="شرکت یافت نشد")
    
    financial_infos = db.query(FinancialInfoModel).filter_by(company_id=company_id).order_by(FinancialInfoModel.stage).all()
    response_data = []

    # Convert DB records to dicts for calculate_financial_metrics
    records = [_as_record(info) for info in financial_infos]

    company_remaining_allocation = 0.0
    if records:
        # Calculate metrics for all records
        metrics_list = calculate_financial_metrics(records)

        # محاسبه مانده تخصیص سطح شرکت (سقف تخصیص کل - مصرف تخصیص کل)
        try:
            total_alloc = sum(float(r.get("allocation_amount") or 0) for r in records)
            total_usage = 0.0
            for r, m in zip(records, metrics_list):
                # اگر سرویس مقدار allocation_usage بدهد از آن استفاده می‌کنیم؛ وگرنه paid_amount را ملاک می‌گیریم
                usage = m.get("allocation_usage") if isinstance(m, dict) else None
                if usage is None:
                    usage = r.get("paid_amount") or 0.0
                total_usage += float(usage or 0.0)
            company_remaining_allocation = total_alloc - total_usage
        except Exception:
            company_remaining_allocation = 0.0

        for info, metrics in zip(financial_infos, metrics_list):
            pydantic_info = FinancialInfo.from_orm(info)
            # Add computed fields to pydantic model
            pydantic_info_dict = pydantic_info.dict()
            pydantic_info_dict.update({
                "remaining_invoice": metrics.get("remaining_invoice", 0.0),
                "remaining_advance": metrics.get("remaining_advance", 0.0),
                "remaining_partial": metrics.get("remaining_partial", 0.0),
                "remaining_allocation": metrics.get("remaining_allocation", 0.0),
                "contractor_credit": metrics.get("contractor_credit", 0.0),
                "contractor_debit": metrics.get("contractor_debit", 0.0),
                "total_paid_invoices": metrics.get("total_paid_invoices", 0.0),
            })
            if info.project:
                proj_model = ProjectLite.from_orm(info.project)
                pydantic_info_dict["project"] = proj_model.dict()
            response_data.append(pydantic_info_dict)
    
    return templates.TemplateResponse("financial_details.html", {
        "request": request,
        "company_id": company_id,
        "company_name": company.company_name,
        "financial_infos": response_data,
        "company_remaining_allocation": company_remaining_allocation,
    })

# Companies list page
@app.get("/companies", response_class=HTMLResponse)
async def list_companies(request: Request, db: Session = Depends(get_db), logged_in: bool = Depends(check_login)):
    projects = db.query(Project).all()
    return templates.TemplateResponse("companies.html", {
        "request": request,
        "projects": [ProjectLite.from_orm(p).dict() for p in projects]
    })

@app.get("/projects/{company_id}")
async def get_company(company_id: str, db: Session = Depends(get_db)):
    company = db.query(Project).filter(Project.company_id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="شرکت یافت نشد")
    proj_lite = ProjectLite.from_orm(company)
    return proj_lite

# Other pages
@app.get("/guarantees", response_class=HTMLResponse)
async def list_guarantees(request: Request, db: Session = Depends(get_db), logged_in: bool = Depends(check_login)):
    guarantees = db.query(Guarantee).all()
    return templates.TemplateResponse("guarantees.html", {"request": request, "guarantees": guarantees})

@app.get("/social-security", response_class=HTMLResponse)
async def list_social_security(request: Request, db: Session = Depends(get_db), logged_in: bool = Depends(check_login)):
    social_securities = db.query(SocialSecurity).all()
    return templates.TemplateResponse("social_security.html", {"request": request, "social_securities": social_securities})

@app.get("/reminders", response_class=HTMLResponse)
async def list_reminders(request: Request, db: Session = Depends(get_db), logged_in: bool = Depends(check_login)):
    reminders = db.query(Reminder).all()
    return templates.TemplateResponse("reminders.html", {"request": request, "reminders": reminders})

# Create financial info form
@app.get("/financial-info/{company_id}", response_class=HTMLResponse)
async def create_financial_info_form(request: Request, company_id: str, db: Session = Depends(get_db), logged_in: bool = Depends(check_login)):
    company = db.query(Project).filter_by(company_id=company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="شرکت یافت نشد")
    return templates.TemplateResponse("financial_details.html", {
        "request": request,
        "company_id": company_id,
        "company_name": company.company_name
    })

# Save/Update financial info
@app.post("/financial-info/{company_id}/{record_number}/{stage}", response_class=RedirectResponse)
async def create_financial_info(
    request: Request,
    company_id: str,
    record_number: int,
    stage: int,
    db: Session = Depends(get_db),
    logged_in: bool = Depends(check_login),
):
    try:
        # Read form data
        form = await request.form()
        data = {k: (v if v is not None else "") for k, v in form.items()}

        # Check if record exists (to decide create vs update)
        financial_info = db.query(FinancialInfoModel).filter_by(
            company_id=company_id, record_number=record_number, stage=stage
        ).first()

        # Build override for current stage from form input
        override_current: Dict = {
            "company_id": company_id,
            "record_number": record_number,
            "stage": stage,
            "invoice_number": data.get("invoice_number") or "",
            "invoice_type": data.get("invoice_type"),
            "invoice_amount": _to_float(data.get("invoice_amount")),
            "allocation_amount": _to_float(data.get("allocation_amount")),
            "paid_amount": _to_float(data.get("paid_amount")),
            "advance_amortization": _to_float(data.get("advance_amortization")),
            "partial_amortization": _to_float(data.get("partial_amortization")),
            # عبور دادن روش تسویه در صورت نیاز
            "settlement_method": data.get("settlement_method"),
        }

        # Get all stages for this record + inject current stage
        rows: List[FinancialInfoModel] = (
            db.query(FinancialInfoModel)
              .filter_by(company_id=company_id, record_number=record_number)
              .order_by(FinancialInfoModel.stage)
              .all()
        )
        records: List[Dict] = []
        has_current = False
        for r in rows:
            if r.stage == stage:
                records.append(override_current)
                has_current = True
            else:
                records.append(_as_record(r))
        if not has_current:
            records.append(override_current)

        # Call financial metrics service
        metrics_list = calculate_financial_metrics(records)
        current = next((m for m in metrics_list if m.get("stage") == stage), None)
        if current is None:
            raise HTTPException(status_code=500, detail="نتیجهٔ محاسبات مرحله جاری یافت نشد.")

        # Create or update
        if not financial_info:
            financial_info = FinancialInfoModel(
                company_id=company_id,
                record_number=record_number,
                stage=stage,
                invoice_number=data.get("invoice_number"),
                invoice_type=data.get("invoice_type"),
                invoice_amount=_to_float(data.get("invoice_amount")),
                allocation_amount=_to_float(data.get("allocation_amount")),
                request_number=data.get("request_number"),
                request_date=data.get("request_date"),
                request_result=data.get("request_result"),
                settlement_method=data.get("settlement_method"),
                paid_amount=_to_float(data.get("paid_amount")),
                advance_amortization=_to_float(data.get("advance_amortization")),
                partial_amortization=_to_float(data.get("partial_amortization")),
            )
            # ست متریک‌ها هنگام ایجاد
            financial_info.remaining_invoice = float(current.get("remaining_invoice", 0.0))
            financial_info.remaining_advance = float(current.get("remaining_advance", 0.0))
            financial_info.remaining_partial = float(current.get("remaining_partial", 0.0))
            financial_info.remaining_allocation = float(current.get("remaining_allocation", 0.0))
            financial_info.contractor_credit = float(current.get("contractor_credit", 0.0))
            financial_info.contractor_debit = float(current.get("contractor_debit", 0.0))
            financial_info.total_paid_invoices = float(current.get("total_paid_invoices", 0.0))
            db.add(financial_info)
        else:
            financial_info.invoice_number = data.get("invoice_number")
            financial_info.invoice_type = data.get("invoice_type")
            financial_info.invoice_amount = _to_float(data.get("invoice_amount"))
            financial_info.allocation_amount = _to_float(data.get("allocation_amount"))
            financial_info.request_number = data.get("request_number")
            financial_info.request_date = data.get("request_date")
            financial_info.request_result = data.get("request_result")
            financial_info.settlement_method = data.get("settlement_method")
            financial_info.paid_amount = _to_float(data.get("paid_amount"))
            financial_info.advance_amortization = _to_float(data.get("advance_amortization"))
            financial_info.partial_amortization = _to_float(data.get("partial_amortization"))
            # ست متریک‌ها هنگام ویرایش
            financial_info.remaining_invoice = float(current.get("remaining_invoice", 0.0))
            financial_info.remaining_advance = float(current.get("remaining_advance", 0.0))
            financial_info.remaining_partial = float(current.get("remaining_partial", 0.0))
            financial_info.remaining_allocation = float(current.get("remaining_allocation", 0.0))
            financial_info.contractor_credit = float(current.get("contractor_credit", 0.0))
            financial_info.contractor_debit = float(current.get("contractor_debit", 0.0))
            financial_info.total_paid_invoices = float(current.get("total_paid_invoices", 0.0))

        db.commit()
        return RedirectResponse(url=f"/financial-details/{company_id}", status_code=303)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.exception("Create/Update financial info (main.py) failed")
        raise HTTPException(status_code=500, detail=f"خطا در ثبت/به‌روزرسانی اطلاعات: {str(e)}")

# Financial details redirect
@app.get("/financial_details", response_class=HTMLResponse)
async def financial_details_redirect(request: Request):
    return RedirectResponse(url="/companies")
