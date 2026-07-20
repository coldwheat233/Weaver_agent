"""资产上传路由"""

from fastapi import APIRouter, UploadFile, File
from uuid import uuid4
from src.storage.file_store import FileStore

router = APIRouter(prefix="/api/assets", tags=["assets"])
file_store = FileStore()


@router.post("/upload")
async def upload_asset(file: UploadFile = File(...)):
    """上传图片/音频文件"""
    data = await file.read()
    if file.content_type and file.content_type.startswith("image"):
        path = file_store.save_image(data, f"{uuid4()}_{file.filename or 'image.png'}")
    elif file.content_type and file.content_type.startswith("audio"):
        path = file_store.save_audio(data, f"{uuid4()}_{file.filename or 'audio.webm'}")
    else:
        path = file_store.save_image(data, f"{uuid4()}_{file.filename or 'file.bin'}")

    return {"path": path, "content_type": file.content_type, "size": len(data)}
