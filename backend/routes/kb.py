"""知识库路由：文件上传、列表与删除。"""
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.auth import current_user
from backend.db import kb_add, kb_delete, kb_get, kb_list
from backend.documents import SUPPORTED_EXTS
from backend.log import get_logger

log = get_logger("backend.routes.kb")
router = APIRouter(prefix="/api/kb", tags=["知识库"])

ALLOWED_EXTS = SUPPORTED_EXTS
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/upload")
async def route_kb_upload(file: UploadFile = File(...), scope: str = "kb", uid: int = Depends(current_user)):
    filename = file.filename or "unknown.txt"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(400, f"不支持的文件类型：{ext}（允许：{', '.join(sorted(ALLOWED_EXTS))}）")
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "文件过大（限 10MB）")
    from backend.rag import ingest_document, save_upload_file
    filepath, file_id = save_upload_file(content, filename, uid)
    chunks = ingest_document(filepath, filename, file_id, scope=scope, user_id=uid)
    kb_add(file_id, uid, filename, filepath, chunks, scope)
    log.info("上传知识库文件 | user=%s file=%s chunks=%d", uid, filename, chunks)
    return {"ok": True, "file": {"id": file_id, "filename": filename, "chunks": chunks}}


@router.get("/files")
def route_kb_list(uid: int = Depends(current_user)):
    return kb_list(uid, "kb")


@router.delete("/files/{file_id}")
def route_kb_delete(file_id: str, uid: int = Depends(current_user)):
    rec = kb_get(file_id)
    if not rec or rec.get("user_id") != uid:
        raise HTTPException(404, "文件不存在")
    from backend.rag import cleanup_upload_file, delete_document
    delete_document(file_id)
    cleanup_upload_file(rec["filepath"])
    kb_delete(file_id)
    log.info("删除知识库文件 | user=%s file=%s", uid, rec["filename"])
    return {"ok": True}
