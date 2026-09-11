"""用户文件路由：工作区文件列表、预览读取与下载。"""
import os

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from backend.auth import current_user
from backend.documents import UnsupportedFormatError, extract_document, get_parser
from backend.log import get_logger
from backend.workspace import list_files, safe_path

log = get_logger("backend.routes.files")
router = APIRouter(prefix="/api/files", tags=["文件"])

MAX_PREVIEW_SIZE = 1024 * 1024  # 在线预览读取上限 1MB

# 纯文本类扩展名：直接读取原文预览
_TEXT_EXTS = {
    ".txt", ".md", ".markdown", ".csv", ".tsv", ".json", ".yaml", ".yml",
    ".log", ".ini", ".cfg", ".toml", ".xml", ".sql",
    ".py", ".js", ".ts", ".jsx", ".tsx", ".vue", ".java", ".go", ".rs", ".c", ".cpp", ".h", ".sh",
}


@router.get("")
def route_file_list(
    scope: str = Query("all", pattern="^(all|uploads|generated|exports)$"),
    uid: int = Depends(current_user),
):
    """列出当前用户工作区文件。"""
    return list_files(uid, scope)


@router.get("/read")
def route_file_read(path: str, uid: int = Depends(current_user)):
    """预览读取：文本类返回原文；文档类由解析器转为 Markdown。"""
    try:
        full = safe_path(uid, path)
    except ValueError:
        raise HTTPException(400, "非法路径")
    if not os.path.isfile(full):
        raise HTTPException(404, "文件不存在")
    if os.path.getsize(full) > MAX_PREVIEW_SIZE:
        raise HTTPException(400, "文件过大，无法在线预览（限 1MB）")

    ext = os.path.splitext(full)[1].lower()
    if ext in _TEXT_EXTS:
        with open(full, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return {"path": path, "content": content, "parsed": False}

    if not get_parser(path):
        raise HTTPException(400, "该格式暂不支持在线预览，请下载查看")
    try:
        doc = extract_document(full, os.path.basename(full))
    except UnsupportedFormatError:
        raise HTTPException(400, "该格式暂不支持在线预览，请下载查看")
    except Exception as exc:
        log.warning("文件解析失败 | user=%s path=%s | %s", uid, path, exc)
        raise HTTPException(400, f"文件解析失败：{exc}")
    return {"path": path, "content": doc.text, "parsed": True, "meta": doc.meta}


@router.get("/download")
def route_file_download(path: str, uid: int = Depends(current_user)):
    """下载文件（保持原文件名）。"""
    try:
        full = safe_path(uid, path)
    except ValueError:
        raise HTTPException(400, "非法路径")
    if not os.path.isfile(full):
        raise HTTPException(404, "文件不存在")
    log.info("下载文件 | user=%s path=%s", uid, path)
    return FileResponse(full, filename=os.path.basename(full))
