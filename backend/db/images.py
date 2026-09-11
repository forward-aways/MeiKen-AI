"""图片域：多模态消息附件的上传记录。"""
from backend.db._core import _db, _ts

IMAGE_COLUMNS = "id,user_id,filename,filepath,mime,size,created_at"

__all__ = ["IMAGE_COLUMNS", "image_add", "image_get", "image_delete", "image_all", "image_update_filepath"]


def image_add(image_id: str, user_id: int, filename: str, filepath: str,
              mime: str, size: int) -> dict:
    now = _ts()
    with _db() as c:
        c.execute(
            "INSERT INTO images(id,user_id,filename,filepath,mime,size,created_at)"
            " VALUES(?,?,?,?,?,?,?)",
            (image_id, user_id, filename, filepath, mime, size, now))
        return dict(c.execute(f"SELECT {IMAGE_COLUMNS} FROM images WHERE id=?", (image_id,)).fetchone())


def image_get(image_id: str) -> dict | None:
    with _db() as c:
        r = c.execute(f"SELECT {IMAGE_COLUMNS} FROM images WHERE id=?", (image_id,)).fetchone()
    return dict(r) if r else None


def image_delete(image_id: str) -> bool:
    with _db() as c:
        cur = c.execute("DELETE FROM images WHERE id=?", (image_id,))
    return cur.rowcount > 0


def image_all() -> list:
    """全部图片记录（供工作区迁移使用）。"""
    with _db() as c:
        rows = c.execute("SELECT * FROM images").fetchall()
    return [dict(r) for r in rows]


def image_update_filepath(image_id: str, filepath: str) -> None:
    """更新文件磁盘路径（迁移后调用）。"""
    with _db() as c:
        c.execute("UPDATE images SET filepath=? WHERE id=?", (filepath, image_id))
