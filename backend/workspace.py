"""用户文件工作区：物理隔离的存储布局、路径安全校验与旧目录迁移。

目录结构（每用户独立根目录）：
    workspace/{user_id}/
    ├── uploads/                 用户上传文件（知识库 / 图片 / 附件）
    ├── generated/{conv_id}/     AI 生成文件（按会话归档）
    └── exports/                 用户导出文件

安全约定：所有用户文件路径必须由本模块解析；
``safe_path`` 做前缀校验，防止 ``../`` 目录穿越。
"""
import os
import shutil

from backend.config import BASE_DIR, WORKSPACE_DIR

# 旧上传目录（迁移来源）
_LEGACY_UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")


def workspace_dir(user_id: int) -> str:
    """用户工作区根目录。"""
    return os.path.join(WORKSPACE_DIR, str(user_id))


def uploads_dir(user_id: int) -> str:
    return os.path.join(workspace_dir(user_id), "uploads")


def generated_dir(user_id: int, conv_id: int | None = None) -> str:
    base = os.path.join(workspace_dir(user_id), "generated")
    return os.path.join(base, str(conv_id)) if conv_id is not None else base


def exports_dir(user_id: int) -> str:
    return os.path.join(workspace_dir(user_id), "exports")


def ensure_workspace(user_id: int) -> str:
    """确保用户工作区目录存在（幂等）。"""
    for d in (uploads_dir(user_id), generated_dir(user_id), exports_dir(user_id)):
        os.makedirs(d, exist_ok=True)
    return workspace_dir(user_id)


def save_upload(user_id: int, file_id: str, ext: str, content: bytes) -> str:
    """保存上传文件到用户工作区，返回绝对路径。"""
    ensure_workspace(user_id)
    path = os.path.join(uploads_dir(user_id), file_id + ext)
    with open(path, "wb") as f:
        f.write(content)
    return path


def safe_path(user_id: int, rel_path: str) -> str:
    """把工作区内的相对路径解析为绝对路径；越界抛 ValueError。"""
    root = os.path.abspath(workspace_dir(user_id))
    target = os.path.abspath(os.path.join(root, rel_path.replace("\\", "/")))
    if target != root and not target.startswith(root + os.sep):
        raise ValueError("路径越界")
    return target


def list_files(user_id: int, scope: str = "all") -> list[dict]:
    """列出工作区文件（相对路径 / 大小 / 修改时间）。"""
    ensure_workspace(user_id)
    bases: list[tuple[str, str]] = []
    if scope in ("all", "uploads"):
        bases.append((uploads_dir(user_id), "uploads"))
    if scope in ("all", "generated"):
        bases.append((generated_dir(user_id), "generated"))
    if scope in ("all", "exports"):
        bases.append((exports_dir(user_id), "exports"))
    out: list[dict] = []
    for base, prefix in bases:
        for dirpath, _, filenames in os.walk(base):
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                try:
                    st = os.stat(full)
                except OSError:
                    continue
                rel = os.path.relpath(full, workspace_dir(user_id)).replace("\\", "/")
                out.append({
                    "path": rel,
                    "name": fn,
                    "scope": prefix,
                    "size": st.st_size,
                    "modified": int(st.st_mtime),
                })
    out.sort(key=lambda x: x["modified"], reverse=True)
    return out


def migrate_legacy_uploads() -> None:
    """把旧 uploads/ 布局迁移进用户工作区（幂等，启动时调用）。

    旧布局：
      - uploads/{file_id}{ext}          知识库文件（无用户目录，需查库归属）
      - uploads/{user_id}/{image_id}{ext}  图片
    """
    from backend.db import (
        image_all, image_update_filepath, kb_all, kb_update_filepath,
    )

    ws_root = os.path.abspath(WORKSPACE_DIR)
    moved = 0

    for rec in kb_all():
        old = os.path.abspath(rec.get("filepath") or "")
        if not old or old.startswith(ws_root):
            continue  # 已在新布局
        uid = rec.get("user_id") or 0
        new = os.path.join(uploads_dir(uid), os.path.basename(old))
        ensure_workspace(uid)
        try:
            if os.path.exists(old):
                shutil.move(old, new)
                moved += 1
        except OSError:
            continue
        kb_update_filepath(rec["id"], new)

    for rec in image_all():
        old = os.path.abspath(rec.get("filepath") or "")
        if not old or old.startswith(ws_root):
            continue
        uid = rec.get("user_id") or 0
        new = os.path.join(uploads_dir(uid), os.path.basename(old))
        ensure_workspace(uid)
        try:
            if os.path.exists(old):
                shutil.move(old, new)
                moved += 1
        except OSError:
            continue
        image_update_filepath(rec["id"], new)

    # 尽力清理空的旧目录（只删空目录，不动任何文件）
    if os.path.isdir(_LEGACY_UPLOAD_DIR) and moved:
        for dirpath, dirnames, filenames in os.walk(_LEGACY_UPLOAD_DIR, topdown=False):
            if not dirnames and not filenames:
                try:
                    os.rmdir(dirpath)
                except OSError:
                    pass
