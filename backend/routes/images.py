"""图片路由：多模态消息附件的上传与读取。"""
import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.auth import current_user
from backend.db import image_add, image_get
from backend.log import get_logger

log = get_logger("backend.routes.images")
router = APIRouter(prefix="/api/images", tags=["图片"])

ALLOWED_MIMES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 单图 5MB


@router.post("", status_code=201)
async def route_image_upload(file: UploadFile = File(...), uid: int = Depends(current_user)):
    mime = (file.content_type or "").lower()
    ext = ALLOWED_MIMES.get(mime)
    if not ext:
        raise HTTPException(400, "仅支持 PNG / JPEG / WebP / GIF 图片")
    content = await file.read()
    if not content:
        raise HTTPException(400, "文件内容为空")
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(400, "图片过大（限 5MB）")
    image_id = uuid.uuid4().hex
    from backend.workspace import save_upload
    filepath = save_upload(uid, image_id, ext, content)
    rec = image_add(image_id, uid, file.filename or f"image{ext}", filepath, mime, len(content))
    log.info("上传图片 | user=%s id=%s mime=%s 大小=%d", uid, image_id, mime, len(content))
    return {
        "id": rec["id"],
        "url": f"/api/images/{rec['id']}",
        "filename": rec["filename"],
        "mime": rec["mime"],
        "size": rec["size"],
    }


@router.get("/{image_id}")
def route_image_get(image_id: str, uid: int = Depends(current_user)):
    rec = image_get(image_id)
    if not rec or rec.get("user_id") != uid:
        raise HTTPException(404, "图片不存在")
    if not os.path.exists(rec["filepath"]):
        raise HTTPException(404, "图片文件丢失")
    return FileResponse(rec["filepath"], media_type=rec["mime"], filename=rec["filename"])
