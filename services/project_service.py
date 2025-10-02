from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from database.models.ProjectDB import Project
from sqlalchemy import or_
import locale

# تنظیم locale برای فرمت‌بندی اعداد
try:
    locale.setlocale(locale.LC_ALL, 'fa_IR.UTF-8')  # برای نمایش اعداد به فارسی
except locale.Error:
    locale.setlocale(locale.LC_ALL, '')  # استفاده از تنظیمات پیش‌فرض سیستم

def get_companies(db: Session, search: str = None):
    """
    دریافت لیست شرکت‌ها با امکان جستجو
    :param db: جلسه دیتابیس
    :param search: عبارت جستجو (اختیاری)
    :return: لیست شرکت‌ها
    """
    try:
        query = db.query(Project)
        if search:
            search = search.strip().lower()
            query = query.filter(or_(
                Project.company_id.ilike(f"%{search}%"),
                Project.company_name.ilike(f"%{search}%"),
                Project.contract_number.ilike(f"%{search}%")
            ))
        return query.order_by(Project.company_name.asc()).all()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در دریافت لیست شرکت‌ها: {str(e)}"
        )

def get_company_by_id(db: Session, company_id: str):
    """
    دریافت اطلاعات یک شرکت بر اساس شناسه ملی
    :param db: جلسه دیتابیس
    :param company_id: شناسه ملی شرکت
    :return: اطلاعات شرکت و مقادیر فرمت‌شده
    """
    try:
        # Find the first project associated with this company_id
        company = db.query(Project).filter(
            Project.company_id == company_id
        ).first()
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="شرکت با این شناسه یافت نشد"
            )

        # محاسبه مجموع مبالغ و سایر اطلاعات مالی مربوط به این شرکت
        # اینجا فقط پروژه اول را برمی‌گردانیم. اگر نیاز به تجمیع اطلاعات تمام پروژه‌های یک شرکت باشد،
        # باید کوئری را تغییر داد.
        return company

    except HTTPException as e:
        raise e # Re-raise HTTPExceptions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در دریافت اطلاعات شرکت: {str(e)}"
        )

def create_or_update_project(db: Session, project_data: dict):
    """
    ایجاد یا به‌روزرسانی پروژه
    :param db: جلسه دیتابیس
    :param project_data: داده‌های پروژه
    :return: پروژه ایجاد/به‌روزرسانی شده و مقادیر فرمت‌شده
    """
    try:
        # اعتبارسنجی فیلدهای اجباری
        if not project_data.get("company_id") or not project_data.get("company_name"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="شناسه ملی و نام شرکت اجباری هستند"
            )

        # اعتبارسنجی و تبدیل فیلدهای عددی
        numeric_fields = ["initial_amount", "change_amount", "duration"]
        for field in numeric_fields:
            if field in project_data and project_data[field]:
                try:
                    if field == "duration":
                        project_data[field] = int(project_data[field])
                    else:
                        project_data[field] = int(float(project_data[field]))
                except (ValueError, TypeError):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"مقدار {field} باید عدد معتبر باشد"
                    )
            else:
                project_data[field] = None if field != "duration" else 0

        # بررسی وجود پروژه
        existing_project = db.query(Project).filter(
            Project.company_id == project_data["company_id"]
        ).first()

        if existing_project:
            # به‌روزرسانی پروژه موجود
            for key, value in project_data.items():
                setattr(existing_project, key, value)
            db.commit()
            db.refresh(existing_project)
            project = existing_project
        else:
            # ایجاد پروژه جدید
            project = Project(**project_data)
            db.add(project)
            db.commit()
            db.refresh(project)

        # فرمت‌بندی اعداد برای نمایش
        formatted = {
            "initial_amount": locale.format_string("%d", project.initial_amount, grouping=True) 
                            if project.initial_amount else "۰",
            "change_amount": locale.format_string("%d", project.change_amount, grouping=True) 
                          if project.change_amount else "۰",
            "duration": str(project.duration) if project.duration else "۰"
        }

        return {"project": project, "formatted": formatted}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در ذخیره اطلاعات پروژه: {str(e)}"
        )