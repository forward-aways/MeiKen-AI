"""对话域：会话 CRUD、消息 CRUD 与全文搜索。"""
import json

from backend.db._core import _db, _ts

__all__ = [
    "conv_create", "conv_list", "conv_get", "conv_delete", "conv_rename",
    "msg_add", "msg_delete", "msg_list", "search_messages",
]


# -- 会话 --

def conv_create(user_id: int, title="New Chat"):
    now = _ts()
    with _db() as c:
        cur = c.execute("INSERT INTO conversations(user_id,title,created_at,updated_at) VALUES(?,?,?,?)",
                        (user_id, title, now, now))
        return dict(c.execute("SELECT * FROM conversations WHERE id=?", (cur.lastrowid,)).fetchone())


def conv_list(user_id: int):
    """用户会话列表（最近 100 条，含消息数）。"""
    with _db() as c:
        rows = c.execute(
            "SELECT c.*,(SELECT COUNT(*) FROM messages WHERE conversation_id=c.id) msg_count "
            "FROM conversations c WHERE c.user_id=? ORDER BY c.updated_at DESC LIMIT 100",
            (user_id,)).fetchall()
    return [dict(r) for r in rows]


def conv_get(cid):
    with _db() as c:
        r = c.execute("SELECT * FROM conversations WHERE id=?", (cid,)).fetchone()
    return dict(r) if r else None


def conv_delete(cid):
    with _db() as c:
        cur = c.execute("DELETE FROM conversations WHERE id=?", (cid,))
    return cur.rowcount > 0


def conv_rename(cid, title):
    with _db() as c:
        c.execute("UPDATE conversations SET title=?, updated_at=? WHERE id=?", (title, _ts(), cid))


# -- 消息 --

def msg_add(cid, role, content, tokens=0, images=None):
    """新增消息并刷新会话更新时间。images 为图片 id 列表。"""
    now = _ts()
    with _db() as c:
        cur = c.execute("INSERT INTO messages(conversation_id,role,content,created_at,tokens,images) VALUES(?,?,?,?,?,?)",
                        (cid, role, content, now, tokens, json.dumps(images or [], ensure_ascii=False)))
        c.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, cid))
        return dict(c.execute("SELECT * FROM messages WHERE id=?", (cur.lastrowid,)).fetchone())


def msg_delete(cid, mid):
    with _db() as c:
        cur = c.execute("DELETE FROM messages WHERE id=? AND conversation_id=?", (mid, cid))
    return cur.rowcount > 0


def msg_list(cid):
    with _db() as c:
        rows = c.execute("SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at ASC", (cid,)).fetchall()
    return [dict(r) for r in rows]


def search_messages(user_id: int, query: str):
    """跨会话全文搜索（LIKE 匹配，最多 30 条）。"""
    with _db() as c:
        rows = c.execute("""
            SELECT c.id cid, c.title, m.content snippet, m.role, m.created_at
            FROM messages m JOIN conversations c ON c.id=m.conversation_id
            WHERE c.user_id=? AND m.content LIKE ?
            ORDER BY m.created_at DESC LIMIT 30
        """, (user_id, f"%{query}%")).fetchall()
    return [dict(r) for r in rows]
