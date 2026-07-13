import sqlite3, os
from contextlib import contextmanager
from datetime import datetime, timezone

DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chat.db")

def _ts():
    return datetime.now(timezone.utc).isoformat()

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    nickname TEXT NOT NULL DEFAULT '',
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    created_at TEXT NOT NULL,
    real_name TEXT NOT NULL DEFAULT '',
    gender TEXT NOT NULL DEFAULT '',
    birthday TEXT NOT NULL DEFAULT '',
    bio TEXT NOT NULL DEFAULT '',
    ai_address TEXT NOT NULL DEFAULT '',
    avatar TEXT NOT NULL DEFAULT '',
    avatar_color TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 0,
    title TEXT NOT NULL DEFAULT 'New Chat',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user','assistant')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    tokens INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS knowledge_files (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    chunks INTEGER NOT NULL DEFAULT 0,
    scope TEXT NOT NULL DEFAULT 'kb',
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_msg ON messages(conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_kb_user ON knowledge_files(user_id, scope);
"""

# Columns added after initial release; added via ALTER TABLE for existing DBs.
_MIGRATE_COLUMNS = [
    ("real_name", "TEXT NOT NULL DEFAULT ''"),
    ("gender", "TEXT NOT NULL DEFAULT ''"),
    ("birthday", "TEXT NOT NULL DEFAULT ''"),
    ("bio", "TEXT NOT NULL DEFAULT ''"),
    ("ai_address", "TEXT NOT NULL DEFAULT ''"),
    ("avatar", "TEXT NOT NULL DEFAULT ''"),
    ("avatar_color", "TEXT NOT NULL DEFAULT ''"),
]

_MSG_MIGRATE_COLUMNS = [
    ("tokens", "INTEGER NOT NULL DEFAULT 0"),
]

# Public user fields (excludes password_hash).
USER_COLUMNS = (
    "id,email,nickname,role,created_at,"
    "real_name,gender,birthday,bio,ai_address,avatar,avatar_color"
)

# Fields allowed to be updated via the profile endpoint.
PROFILE_FIELDS = {
    "nickname", "real_name", "gender", "birthday",
    "bio", "ai_address", "avatar", "avatar_color",
}

_tables_ready = False

def _migrate(conn):
    """Add new columns to legacy tables (idempotent)."""
    existing = {r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
    for col, ddl in _MIGRATE_COLUMNS:
        if col not in existing:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col} {ddl}")
    msg_existing = {r["name"] for r in conn.execute("PRAGMA table_info(messages)").fetchall()}
    for col, ddl in _MSG_MIGRATE_COLUMNS:
        if col not in msg_existing:
            conn.execute(f"ALTER TABLE messages ADD COLUMN {col} {ddl}")


@contextmanager
def _db():
    global _tables_ready
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    if not _tables_ready:
        conn.executescript(_INIT_SQL)
        _migrate(conn)
        _tables_ready = True
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# -- users --

def user_create(email: str, password_hash: str, nickname: str = ""):
    now = _ts()
    with _db() as c:
        cur = c.execute("INSERT INTO users(email,nickname,password_hash,created_at) VALUES(?,?,?,?)",
                        (email, nickname, password_hash, now))
        return dict(c.execute(f"SELECT {USER_COLUMNS} FROM users WHERE id=?", (cur.lastrowid,)).fetchone())

def user_get_by_email(email: str):
    with _db() as c:
        r = c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    return dict(r) if r else None

def user_get(uid: int):
    with _db() as c:
        r = c.execute(f"SELECT {USER_COLUMNS} FROM users WHERE id=?", (uid,)).fetchone()
    return dict(r) if r else None

def user_get_by_nickname(nickname: str):
    with _db() as c:
        r = c.execute("SELECT * FROM users WHERE LOWER(nickname)=LOWER(?) AND nickname!=''", (nickname,)).fetchone()
    return dict(r) if r else None

def user_update_nickname(uid: int, nickname: str):
    with _db() as c:
        c.execute("UPDATE users SET nickname=? WHERE id=?", (nickname, uid))

def user_update_password(uid: int, password_hash: str):
    with _db() as c:
        c.execute("UPDATE users SET password_hash=? WHERE id=?", (password_hash, uid))

def user_update_profile(uid: int, fields: dict):
    """Update allowed profile fields. Only keys in PROFILE_FIELDS are written."""
    sets, vals = [], []
    for k, v in fields.items():
        if k in PROFILE_FIELDS and v is not None:
            sets.append(f"{k}=?")
            vals.append(v)
    if not sets:
        return
    vals.append(uid)
    with _db() as c:
        c.execute(f"UPDATE users SET {','.join(sets)} WHERE id=?", vals)

# -- conversations --

def conv_create(user_id: int, title="New Chat"):
    now = _ts()
    with _db() as c:
        cur = c.execute("INSERT INTO conversations(user_id,title,created_at,updated_at) VALUES(?,?,?,?)",
                        (user_id, title, now, now))
        return dict(c.execute("SELECT * FROM conversations WHERE id=?", (cur.lastrowid,)).fetchone())

def conv_list(user_id: int):
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

def seed_admin(hash_pw: str):
    """Create default admin account if no users exist."""
    with _db() as c:
        count = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count == 0:
            c.execute("INSERT INTO users(email,nickname,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                      ("admin@meiken.ai", "Admin", hash_pw, "admin", _ts()))

# -- messages --

def msg_add(cid, role, content, tokens=0):
    now = _ts()
    with _db() as c:
        cur = c.execute("INSERT INTO messages(conversation_id,role,content,created_at,tokens) VALUES(?,?,?,?,?)",
                        (cid, role, content, now, tokens))
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
    with _db() as c:
        rows = c.execute("""
            SELECT c.id cid, c.title, m.content snippet, m.role, m.created_at
            FROM messages m JOIN conversations c ON c.id=m.conversation_id
            WHERE c.user_id=? AND m.content LIKE ?
            ORDER BY m.created_at DESC LIMIT 30
        """, (user_id, f"%{query}%")).fetchall()
    return [dict(r) for r in rows]

# -- knowledge files --

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
