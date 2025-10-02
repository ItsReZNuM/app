from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import List, Optional
from database.db import get_db
from schemas.project import Project as ProjectSchema, ProjectCreate, ProjectUpdate, ProjectWithoutFinancials
from database.models.ProjectDB import Project as ProjectDB

router = APIRouter()

@router.post("/projects/", response_model=ProjectSchema)
def create_project(
    project: ProjectCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    if not request.session.get("logged_in"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="لطفاً ابتدا وارد شوید"
        )

    existing_project = db.query(ProjectDB).filter(
        ProjectDB.company_id == project.company_id
    ).first()

    if existing_project:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="شرکت با این شناسه ملی قبلاً ثبت شده است"
        )

    try:
        db_project = ProjectDB(**project.dict())
        db.add(db_project)
        db.commit()
        db.refresh(db_project)
        return ProjectSchema.from_orm(db_project)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در ثبت پروژه: {str(e)}"
        )

@router.get("/projects/", response_model=List[ProjectWithoutFinancials])
def read_projects(
    request: Request,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    دریافت لیست تمام پروژه‌ها با امکان جستجو
    """
    if not request.session.get("logged_in"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="لطفاً ابتدا وارد شوید"
        )

    query = db.query(ProjectDB)

    if search:
        query = query.filter(
            (ProjectDB.company_id.contains(search)) |
            (ProjectDB.company_name.contains(search)) |
            (ProjectDB.contract_number.contains(search))
        )

    projects = query.order_by(ProjectDB.company_name).all()
    return [ProjectWithoutFinancials.from_orm(project) for project in projects]

@router.get("/projects/{company_id}", response_model=ProjectWithoutFinancials)
def read_project(
    request: Request,
    company_id: str,
    db: Session = Depends(get_db)
):
    """
    دریافت اطلاعات یک پروژه خاص بر اساس شناسه شرکت
    """
    if not request.session.get("logged_in"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="لطفاً ابتدا وارد شوید"
        )

    project = db.query(ProjectDB).filter(
        ProjectDB.company_id == company_id
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="پروژه یافت نشد"
        )

    return ProjectWithoutFinancials.from_orm(project)

@router.put("/projects/{company_id}", response_model=ProjectSchema)
def update_project(
    company_id: str,
    project: ProjectUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    به‌روزرسانی اطلاعات یک پروژه
    """
    if not request.session.get("logged_in"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="لطفاً ابتدا وارد شوید"
        )

    db_project = db.query(ProjectDB).filter(
        ProjectDB.company_id == company_id
    ).first()

    if not db_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="پروژه یافت نشد"
        )

    try:
        update_data = project.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_project, key, value)

        db.commit()
        db.refresh(db_project)
        return ProjectSchema.from_orm(db_project)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در به‌روزرسانی پروژه: {str(e)}"
        )

@router.delete("/projects/{company_id}")
def delete_project(
    company_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    حذف یک پروژه
    """
    if not request.session.get("logged_in"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="لطفاً ابتدا وارد شوید"
        )

    project = db.query(ProjectDB).filter(
        ProjectDB.company_id == company_id
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="پروژه یافت نشد"
        )

    try:
        db.delete(project)
        db.commit()
        return {
            "message": f"پروژه با شناسه {company_id} با موفقیت حذف شد",
            "status": "success"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در حذف پروژه: {str(e)}"
        )