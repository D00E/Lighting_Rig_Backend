from fastapi import APIRouter, Body, HTTPException, Query

from app.services.storage import upload_bytes


router = APIRouter(prefix="/storage", tags=["storage"])


@router.post("/upload")
def upload_asset(
    content: bytes = Body(...),
    callsign: str = Query(..., min_length=6, max_length=6),
    filename: str = Query(...),
    content_type: str = Query("application/octet-stream"),
) -> dict:
    storage_path = f"{callsign}/{filename}"
    try:
        result = upload_bytes(storage_path=storage_path, content=content, content_type=content_type)
    except RuntimeError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return result
