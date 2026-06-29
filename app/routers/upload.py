import os
import uuid

from fastapi import APIRouter, HTTPException, UploadFile, File

from ..config import UPLOAD_DIR

router = APIRouter(tags=["文件上传"])


@router.post("/api/upload")
def upload_photo(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        raise HTTPException(status_code=400, detail="仅支持 jpg、png、gif、webp 格式的图片")

    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(file.file.read())
    return {"code": 200, "data": f"/uploads/{filename}"}
