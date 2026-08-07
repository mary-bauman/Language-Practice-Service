from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from app.db.models import User
from app.db.session import get_session
from app.deps import get_current_user
from app.utils.import_export import export_items, import_items

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/export.csv")
def export_csv(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    content = export_items(session, current_user)
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="language-practice.csv"'
        },
    )


@router.post("/import.csv")
async def import_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if file.content_type not in {"text/csv", "application/csv", "text/plain"}:
        raise HTTPException(status_code=415, detail="Upload a CSV file")
    content = (await file.read()).decode("utf-8-sig")
    try:
        return import_items(session, current_user, content)
    except (UnicodeDecodeError, ValueError) as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
