from fastapi import APIRouter, UploadFile, File, HTTPException
from app.core.config import settings
from app.services.storage import ensure_bucket_exists, upload_stream

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/ensure-bucket")
def ensure_bucket():
    try:
        ensure_bucket_exists(settings.s3_bucket)
        return {"ok": True, "bucket": settings.s3_bucket}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Простой upload: FastAPI принимает файл и кладёт в MinIO.
    """
    try:
        ensure_bucket_exists(settings.s3_bucket)

        object_key = upload_stream(
            fileobj=file.file,
            original_name=file.filename,
            content_type=file.content_type or "application/octet-stream",
        )
        return {
            "ok": True,
            "bucket": settings.s3_bucket,
            "object_key": object_key,
            "original_name": file.filename,
            "content_type": file.content_type,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
