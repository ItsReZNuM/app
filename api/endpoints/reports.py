from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from urllib.parse import quote
from datetime import date
import base64
import io

from app.database.db import get_db
from app.services.report_service import ReportService

router = APIRouter(
    prefix="/api/reports",
    tags=["Reports"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Not authenticated"},
        status.HTTP_403_FORBIDDEN: {"description": "Not authorized"},
        status.HTTP_404_NOT_FOUND: {"description": "Not found"},
    },
)


# --- Helpers -----------------------------------------------------------------

def _ascii_safe_filename(name: str) -> str:
    """Return an ASCII-only filename by replacing unsafe chars with '_'.
    Keeps letters, digits, space, dash, underscore, and dot. Removes Windows-forbidden chars.
    """
    bad = set('\/:*?"<>|')
    out = []
    for ch in name:
        if ch.isascii() and ch not in bad and (ch.isalnum() or ch in ("-", "_", ".", " ")):
            out.append(ch)
        else:
            out.append("_")
    cleaned = "".join(out).strip("_")
    return cleaned or "report.xlsx"


def _build_disposition(company_id: str, report_type: str) -> str:
    today = date.today().isoformat()
    utf8_name = f"report_{company_id}_{report_type}_{today}.xlsx"
    ascii_name = _ascii_safe_filename(utf8_name)
    # RFC 5987: ASCII-only header with UTF-8 filename*
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(utf8_name)}"


def _bytes_from(data) -> bytes:
    if isinstance(data, io.BytesIO):
        return data.getvalue()
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    raise TypeError("ReportService must return bytes or BytesIO")


# --- Schemas -----------------------------------------------------------------

class ReportRequest(BaseModel):
    company_id: str
    report_type: str


# --- Endpoints ---------------------------------------------------------------

@router.post("/base64", response_class=JSONResponse, status_code=status.HTTP_200_OK)
async def generate_report_base64(payload: ReportRequest, db: Session = Depends(get_db)):
    """Alternative method (no headers with non-ASCII):
    Returns the Excel file as base64 inside JSON. Frontend decodes and saves.
    Body: {"company_id": "...", "report_type": "..."}
    """
    try:
        content_bytes = _bytes_from(
            ReportService.generate_report(db, payload.company_id, payload.report_type)
        )
        today = date.today().isoformat()
        utf8_name = f"report_{payload.company_id}_{payload.report_type}_{today}.xlsx"
        ascii_name = _ascii_safe_filename(utf8_name)

        return {
            "filename": utf8_name,          # may contain Persian (OK in JSON)
            "filename_ascii": ascii_name,   # safe fallback
            "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "data_b64": base64.b64encode(content_bytes).decode("ascii"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در تولید گزارش: {e}")


@router.post("", response_class=StreamingResponse, status_code=status.HTTP_200_OK)
async def generate_report_post(payload: ReportRequest, db: Session = Depends(get_db)):
    """Original streaming method (kept for compatibility)."""
    try:
        content_bytes = _bytes_from(ReportService.generate_report(db, payload.company_id, payload.report_type))
        return StreamingResponse(
            content=content_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                # ASCII-only + RFC5987 UTF-8 filename* to avoid latin-1 errors
                "Content-Disposition": _build_disposition(payload.company_id, payload.report_type),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در تولید گزارش: {e}")


@router.get("", response_class=StreamingResponse, status_code=status.HTTP_200_OK)
async def generate_report_get(
    company_id: str = Query(...),
    report_type: str = Query(...),
    db: Session = Depends(get_db),
):
    """GET variant (query string)."""
    try:
        content_bytes = _bytes_from(ReportService.generate_report(db, company_id, report_type))
        return StreamingResponse(
            content=content_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": _build_disposition(company_id, report_type),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در تولید گزارش: {e}")


@router.get("/types")
async def list_report_types():
    """Optional: expose available report types for the UI dropdown."""
    try:
        types = getattr(ReportService, "REPORT_CONFIGS", None)
        if isinstance(types, dict):
            items = list(types.keys())
        else:
            items = [
                "مشخصات پروژه",
                "وضعیت مالی",
                "تضامین",
                "بیمه تأمین اجتماعی",
                "گزارش کلی",
            ]
        return {"items": items}
    except Exception:
        return {"items": []}
