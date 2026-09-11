"""知识库域：上传文件记录 CRUD。"""
from backend.db._core import _db, _ts

__all__ = ["kb_add", "kb_list", "kb_get", "kb_delete", "kb_all", "kb_update_filepath"]


def kb_add(file_id: str, user_id: int, filename: str, filepath: str, chunks: int, scope: str = "kb"):
    now = _ts()
    with _db() as c:
        c.execute("INSERT INTO knowledge_files(id,user_id,filename,filepath,chunks,scope,created_at) VALUES(?,?,?,?,?,?,?)",
                  (file_id, user_id, filename, filepath, chunks, scope, now))
        return dict(c.execute("SELECT * FROM knowledge_files WHERE id=?", (file_id,)).fetchone())


def kb_list(user_id: int, scope: str = "kb"):
    with _db() as c:
        rows = c.execute("SELECT * FROM knowledge_files WHERE user_id=? AND scope=? ORDER BY created_at DESC",
                         (user_id, scope)).fetchall()
    return [dict(r) for r in rows]


def kb_get(file_id: str):
    with _db() as c:
        r = c.execute("SELECT * FROM knowledge_files WHERE id=?", (file_id,)).fetchone()
    return dict(r) if r else None


def kb_delete(file_id: str):
    with _db() as c:
        cur = c.execute("DELETE FROM knowledge_files WHERE id=?", (file_id,))
    return cur.rowcount > 0


def kb_all() -> list:
    """全部知识库记录（供工作区迁移使用）。"""
    with _db() as c:
        rows = c.execute("SELECT * FROM knowledge_files").fetchall()
    return [dict(r) for r in rows]


def kb_update_filepath(file_id: str, filepath: str) -> None:
    """更新文件磁盘路径（迁移后调用）。"""
    with _db() as c:
        c.execute("UPDATE knowledge_files SET filepath=? WHERE id=?", (filepath, file_id))
