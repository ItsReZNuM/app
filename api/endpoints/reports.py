from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.services.report_service import ReportService
from fastapi import status, Body

router = APIRouter(
    prefix="/api/reports",
    tags=["Reports"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Not authenticated"},
        status.HTTP_403_FORBIDDEN: {"description": "Not authorized"},
        status.HTTP_404_NOT_FOUND: {"description": "Not found"}
    }
)

@router.post(
    "",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "description": "Excel report file",
            "content": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}}
        },
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid input data"},
        status.HTTP_404_NOT_FOUND: {"description": "Company or data not found"}
    }
)
async def generate_report(
    company_id: str = Body(..., embed=True),
    report_type: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Generate an Excel report for a company.
    
    Args:
        company_id: National ID of the company
        report_type: Type of report to generate
        db: Database session
        
    Returns:
        StreamingResponse: Excel file with the report data
        
    Raises:
        HTTPException: If input validation fails or data not found
    """
    try:
        report_data = ReportService.generate_report(db, company_id, report_type)
        
        return StreamingResponse(
            content=report_data,
            headers={
                "Content-Disposition": f'attachment; filename="report_{report_type}_{company_id}.xlsx"',
                "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            },
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در تولید گزارش: {str(e)}"
        )