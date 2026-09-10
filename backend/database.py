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
CREATE TABLE IF NOT EXISTS agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 0,
    name TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    system_prompt TEXT NOT NULL DEFAULT '',
    tools TEXT NOT NULL DEFAULT '[]',
    model TEXT NOT NULL DEFAULT 'deepseek-flash',
    thinking INTEGER NOT NULL DEFAULT 1,
    reasoning_effort TEXT NOT NULL DEFAULT 'high',
    temperature REAL NOT NULL DEFAULT 0.7,
    is_builtin INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conv_id INTEGER NOT NULL,
    agent_id INTEGER NOT NULL,
    thread_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    action_id TEXT NOT NULL,
    tool TEXT NOT NULL DEFAULT '',
    args TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 0,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    meta TEXT NOT NULL DEFAULT '{}',
    enabled INTEGER NOT NULL DEFAULT 1,
    source TEXT NOT NULL DEFAULT 'manual',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, name)
);
CREATE TABLE IF NOT EXISTS skill_overrides (
    user_id INTEGER NOT NULL,
    skill_id INTEGER NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (user_id, skill_id)
);
CREATE TABLE IF NOT EXISTS providers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 0,
    name TEXT NOT NULL,
    base_url TEXT NOT NULL,
    api_key_enc TEXT NOT NULL DEFAULT '',
    deepseek_compat INTEGER NOT NULL DEFAULT 0,
    models TEXT NOT NULL DEFAULT '[]',
    is_builtin INTEGER NOT NULL DEFAULT 0,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, name)
);
CREATE TABLE IF NOT EXISTS images (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    mime TEXT NOT NULL,
    size INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_provider_user ON providers(user_id, enabled);
CREATE INDEX IF NOT EXISTS idx_image_user ON images(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_msg ON messages(conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_kb_user ON knowledge_files(user_id, scope);
CREATE INDEX IF NOT EXISTS idx_agent_user ON agents(user_id);
CREATE INDEX IF NOT EXISTS idx_run_conv ON agent_runs(conv_id);
CREATE INDEX IF NOT EXISTS idx_approval_run ON approvals(run_id, status);
CREATE INDEX IF NOT EXISTS idx_skill_user ON skills(user_id, enabled);
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
    ("images", "TEXT NOT NULL DEFAULT '[]'"),
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

def msg_add(cid, role, content, tokens=0, images=None):
    import json
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

# -- agents --

AGENT_COLUMNS = "id,user_id,name,display_name,description,system_prompt,tools,model,thinking,reasoning_effort,temperature,is_builtin,created_at"


def agent_create(user_id: int, name: str, display_name: str, description: str,
                 system_prompt: str, tools: list, model: str = "deepseek-flash",
                 thinking: bool = True, reasoning_effort: str = "high",
                 temperature: float = 0.7, is_builtin: bool = False) -> dict:
    now = _ts()
    import json
    with _db() as c:
        cur = c.execute(
            f"INSERT INTO agents(user_id,name,display_name,description,system_prompt,tools,model,thinking,reasoning_effort,temperature,is_builtin,created_at)"
            f" VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (user_id, name, display_name, description, system_prompt,
             json.dumps(tools, ensure_ascii=False), model, 1 if thinking else 0,
             reasoning_effort, temperature, 1 if is_builtin else 0, now))
        return dict(c.execute(f"SELECT {AGENT_COLUMNS} FROM agents WHERE id=?", (cur.lastrowid,)).fetchone())


def agent_list(user_id: int) -> list:
    with _db() as c:
        rows = c.execute(
            f"SELECT {AGENT_COLUMNS} FROM agents WHERE user_id=? OR user_id=0 ORDER BY is_builtin DESC, id ASC",
            (user_id,)).fetchall()
    return [dict(r) for r in rows]


def agent_get(agent_id: int) -> dict | None:
    with _db() as c:
        r = c.execute(f"SELECT {AGENT_COLUMNS} FROM agents WHERE id=?", (agent_id,)).fetchone()
    return dict(r) if r else None


def agent_get_by_name(user_id: int, name: str) -> dict | None:
    with _db() as c:
        r = c.execute(
            f"SELECT {AGENT_COLUMNS} FROM agents WHERE (user_id=? OR user_id=0) AND name=?",
            (user_id, name)).fetchone()
    return dict(r) if r else None


def agent_update(agent_id: int, fields: dict) -> None:
    sets, vals = [], []
    import json
    for k, v in fields.items():
        if k == "tools":
            sets.append("tools=?")
            vals.append(json.dumps(v, ensure_ascii=False))
        elif k == "thinking":
            sets.append("thinking=?")
            vals.append(1 if v else 0)
        else:
            sets.append(f"{k}=?")
            vals.append(v)
    if not sets:
        return
    vals.append(agent_id)
    with _db() as c:
        c.execute(f"UPDATE agents SET {','.join(sets)} WHERE id=?", vals)


def agent_delete(agent_id: int) -> bool:
    with _db() as c:
        cur = c.execute("DELETE FROM agents WHERE id=? AND is_builtin=0", (agent_id,))
    return cur.rowcount > 0


def seed_builtin_agents(builtins: list[dict]) -> None:
    """Insert builtin agents (user_id=0) that do not exist yet. Idempotent."""
    with _db() as c:
        existing = {r["name"] for r in c.execute("SELECT name FROM agents WHERE user_id=0").fetchall()}
        now = _ts()
        import json
        for b in builtins:
            if b["name"] in existing:
                # Built-ins are platform-managed (not user-editable): migrate the
                # legacy default model name to its current canonical form.
                c.execute(
                    "UPDATE agents SET model=? WHERE user_id=0 AND name=? AND model='deepseek-v4-flash'",
                    (b.get("model", "deepseek-flash"), b["name"]))
                continue
            c.execute(
                "INSERT INTO agents(user_id,name,display_name,description,system_prompt,tools,model,thinking,reasoning_effort,temperature,is_builtin,created_at)"
                " VALUES(0,?,?,?,?,?,?,?,?,?,1,?)",
                (b["name"], b["display_name"], b["description"], b["system_prompt"],
                 json.dumps(b.get("tools", []), ensure_ascii=False),
                 b.get("model", "deepseek-flash"),
                 1 if b.get("thinking", True) else 0,
                 b.get("reasoning_effort", "high"),
                 b.get("temperature", 0.7), now))

# -- skills --

SKILL_COLUMNS = "id,user_id,name,description,content,meta,enabled,source,created_at,updated_at"
SKILL_LIST_COLUMNS = "id,user_id,name,description,enabled,source,created_at,updated_at"


def skill_create(user_id: int, name: str, description: str, content: str,
                 meta: dict, source: str = "manual", enabled: bool = True) -> dict:
    import json
    now = _ts()
    with _db() as c:
        cur = c.execute(
            "INSERT INTO skills(user_id,name,description,content,meta,enabled,source,created_at,updated_at)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (user_id, name, description, content, json.dumps(meta, ensure_ascii=False),
             1 if enabled else 0, source, now, now))
        return dict(c.execute(f"SELECT {SKILL_COLUMNS} FROM skills WHERE id=?", (cur.lastrowid,)).fetchone())


def skill_get(skill_id: int) -> dict | None:
    with _db() as c:
        r = c.execute(f"SELECT {SKILL_COLUMNS} FROM skills WHERE id=?", (skill_id,)).fetchone()
    return dict(r) if r else None


def skill_get_by_name(user_id: int, name: str) -> dict | None:
    with _db() as c:
        r = c.execute(
            f"SELECT {SKILL_COLUMNS} FROM skills WHERE (user_id=? OR user_id=0) AND name=?",
            (user_id, name)).fetchone()
    return dict(r) if r else None


def skill_list(user_id: int) -> list:
    with _db() as c:
        rows = c.execute(
            f"SELECT {SKILL_LIST_COLUMNS} FROM skills WHERE user_id=? OR user_id=0 "
            "ORDER BY user_id ASC, updated_at DESC",
            (user_id,)).fetchall()
        ov = {r["skill_id"]: r["enabled"]
              for r in c.execute("SELECT skill_id, enabled FROM skill_overrides WHERE user_id=?", (user_id,)).fetchall()}
    out = []
    for r in rows:
        d = dict(r)
        if d["user_id"] == 0 and d["id"] in ov:
            d["enabled"] = ov[d["id"]]
        out.append(d)
    return out


def skill_set_override(user_id: int, skill_id: int, enabled: bool) -> None:
    with _db() as c:
        c.execute(
            "INSERT INTO skill_overrides(user_id,skill_id,enabled) VALUES(?,?,?) "
            "ON CONFLICT(user_id,skill_id) DO UPDATE SET enabled=excluded.enabled",
            (user_id, skill_id, 1 if enabled else 0))


def skill_update(skill_id: int, fields: dict) -> None:
    sets, vals = [], []
    import json
    for k, v in fields.items():
        if k == "meta":
            sets.append("meta=?")
            vals.append(json.dumps(v, ensure_ascii=False))
        elif k == "enabled":
            sets.append("enabled=?")
            vals.append(1 if v else 0)
        else:
            sets.append(f"{k}=?")
            vals.append(v)
    if not sets:
        return
    sets.append("updated_at=?")
    vals.append(_ts())
    vals.append(skill_id)
    with _db() as c:
        c.execute(f"UPDATE skills SET {','.join(sets)} WHERE id=?", vals)


def skill_delete(skill_id: int, user_id: int) -> bool:
    with _db() as c:
        cur = c.execute("DELETE FROM skills WHERE id=? AND user_id=?", (skill_id, user_id))
    return cur.rowcount > 0


def seed_builtin_skills(skills: list[dict]) -> None:
    """Insert builtin skills (user_id=0) that do not exist yet. Idempotent."""
    import json
    now = _ts()
    with _db() as c:
        existing = {r["name"] for r in c.execute("SELECT name FROM skills WHERE user_id=0").fetchall()}
        for s in skills:
            if s["name"] in existing:
                continue
            c.execute(
                "INSERT INTO skills(user_id,name,description,content,meta,enabled,source,created_at,updated_at)"
                " VALUES(0,?,?,?,?,1,?,?,?)",
                (s["name"], s["description"], s["content"],
                 json.dumps(s.get("meta", {}), ensure_ascii=False),
                 s.get("source", "builtin"), now, now))


# -- providers --

PROVIDER_COLUMNS = ("id,user_id,name,base_url,api_key_enc,deepseek_compat,"
                    "models,is_builtin,enabled,created_at,updated_at")


def provider_create(user_id: int, name: str, base_url: str, api_key_enc: str,
                    deepseek_compat: bool, models: list, is_builtin: bool = False,
                    enabled: bool = True) -> dict:
    import json
    now = _ts()
    with _db() as c:
        cur = c.execute(
            "INSERT INTO providers(user_id,name,base_url,api_key_enc,deepseek_compat,"
            "models,is_builtin,enabled,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (user_id, name, base_url, api_key_enc, 1 if deepseek_compat else 0,
             json.dumps(models, ensure_ascii=False), 1 if is_builtin else 0,
             1 if enabled else 0, now, now))
        return dict(c.execute(f"SELECT {PROVIDER_COLUMNS} FROM providers WHERE id=?", (cur.lastrowid,)).fetchone())


def provider_get(pid: int) -> dict | None:
    with _db() as c:
        r = c.execute(f"SELECT {PROVIDER_COLUMNS} FROM providers WHERE id=?", (pid,)).fetchone()
    return dict(r) if r else None


def provider_list(user_id: int) -> list:
    """All providers visible to a user: their own plus built-ins (user_id=0)."""
    with _db() as c:
        rows = c.execute(
            f"SELECT {PROVIDER_COLUMNS} FROM providers WHERE user_id=? OR user_id=0 "
            "ORDER BY user_id ASC, is_builtin DESC, id ASC",
            (user_id,)).fetchall()
    return [dict(r) for r in rows]


def provider_update(pid: int, fields: dict) -> None:
    allowed = {"name", "base_url", "api_key_enc", "deepseek_compat", "models", "enabled"}
    sets, vals = [], []
    import json
    for k, v in fields.items():
        if k not in allowed:
            continue
        if k == "models":
            sets.append("models=?")
            vals.append(json.dumps(v, ensure_ascii=False))
        elif k == "deepseek_compat" or k == "enabled":
            sets.append(f"{k}=?")
            vals.append(1 if v else 0)
        else:
            sets.append(f"{k}=?")
            vals.append(v)
    if not sets:
        return
    sets.append("updated_at=?")
    vals.append(_ts())
    vals.append(pid)
    with _db() as c:
        c.execute(f"UPDATE providers SET {','.join(sets)} WHERE id=?", vals)


def provider_delete(pid: int) -> bool:
    with _db() as c:
        cur = c.execute("DELETE FROM providers WHERE id=?", (pid,))
    return cur.rowcount > 0


def provider_find_by_model(user_id: int, model: str) -> dict | None:
    """Return the first enabled provider whose models include ``model``."""
    import json
    for p in provider_list(user_id):
        if not p["enabled"]:
            continue
        for m in json.loads(p.get("models") or "[]"):
            if m.get("name") == model:
                return p
    return None


def provider_name_exists(user_id: int, name: str, exclude_id: int | None = None) -> bool:
    for p in provider_list(user_id):
        if p["id"] == exclude_id:
            continue
        if p["name"].lower() == name.lower():
            return True
    return False


def model_name_exists(user_id: int, model: str, exclude_id: int | None = None) -> bool:
    """Model names are globally unique across all providers (built-in included)."""
    import json
    for p in provider_list(user_id):
        if p["id"] == exclude_id:
            continue
        for m in json.loads(p.get("models") or "[]"):
            if m.get("name") == model:
                return True
    return False


# Built-in DeepSeek models. ``deepseek-flash`` is V4.1 Flash (native multimodal,
# current flagship); legacy names are kept because the API routes them to V4.1
# Flash for compatibility (deepseek-v4-pro routes there from 2026-09-14 too).
BUILTIN_PROVIDER_MODELS = [
    {"name": "deepseek-flash", "context_window": 1_000_000},
    {"name": "deepseek-v4-flash", "context_window": 1_000_000},
    {"name": "deepseek-v4-pro", "context_window": 1_000_000},
]


def seed_builtin_provider(deepseek_api_key: str = "", deepseek_base_url: str = "https://api.deepseek.com") -> None:
    """Seed the system-level DeepSeek provider (user_id=0). Idempotent.

    The key is read from .env only on first seed; afterwards the database is
    the single source of truth (editable via the UI). Already-seeded databases
    get newly launched models merged into their list.
    """
    import json
    from backend.crypto import encrypt_secret
    now = _ts()
    with _db() as c:
        r = c.execute(
            "SELECT id, api_key_enc, models FROM providers WHERE user_id=0 AND is_builtin=1"
        ).fetchone()
        if r is None:
            enc = encrypt_secret(deepseek_api_key) if deepseek_api_key else ""
            c.execute(
                "INSERT INTO providers(user_id,name,base_url,api_key_enc,deepseek_compat,"
                "models,is_builtin,enabled,created_at,updated_at) VALUES(0,?,?,?,1,?,1,1,?,?)",
                ("DeepSeek", deepseek_base_url, enc,
                 json.dumps(BUILTIN_PROVIDER_MODELS, ensure_ascii=False), now, now))
            return
        if not r["api_key_enc"] and deepseek_api_key:
            c.execute("UPDATE providers SET api_key_enc=?, updated_at=? WHERE id=?",
                      (encrypt_secret(deepseek_api_key), now, r["id"]))
        existing = json.loads(r["models"] or "[]")
        existing_names = {m.get("name") for m in existing}
        missing = [m for m in BUILTIN_PROVIDER_MODELS if m["name"] not in existing_names]
        if missing:
            merged = missing + existing
            c.execute("UPDATE providers SET models=?, updated_at=? WHERE id=?",
                      (json.dumps(merged, ensure_ascii=False), now, r["id"]))


# -- images (multimodal message attachments) --

IMAGE_COLUMNS = "id,user_id,filename,filepath,mime,size,created_at"


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


# -- agent runs / approvals --

def run_create(conv_id: int, agent_id: int, thread_id: str) -> dict:
    now = _ts()
    with _db() as c:
        cur = c.execute(
            "INSERT INTO agent_runs(conv_id,agent_id,thread_id,status,created_at,updated_at)"
            " VALUES(?,?,?,?,?,?)",
            (conv_id, agent_id, thread_id, "running", now, now))
        return dict(c.execute("SELECT * FROM agent_runs WHERE id=?", (cur.lastrowid,)).fetchone())


def run_get(run_id: int) -> dict | None:
    with _db() as c:
        r = c.execute("SELECT * FROM agent_runs WHERE id=?", (run_id,)).fetchone()
    return dict(r) if r else None


def run_get_by_conv(conv_id: int) -> dict | None:
    with _db() as c:
        r = c.execute("SELECT * FROM agent_runs WHERE conv_id=? ORDER BY id DESC LIMIT 1", (conv_id,)).fetchone()
    return dict(r) if r else None


def run_update_status(run_id: int, status: str) -> None:
    with _db() as c:
        c.execute("UPDATE agent_runs SET status=?, updated_at=? WHERE id=?", (status, _ts(), run_id))


def approval_create(run_id: int, action_id: str, tool: str, args: dict) -> dict:
    now = _ts()
    import json
    with _db() as c:
        cur = c.execute(
            "INSERT INTO approvals(run_id,action_id,tool,args,status,created_at) VALUES(?,?,?,?,?,?)",
            (run_id, action_id, tool, json.dumps(args, ensure_ascii=False), "pending", now))
        return dict(c.execute("SELECT * FROM approvals WHERE id=?", (cur.lastrowid,)).fetchone())


def approval_get(action_id: str) -> dict | None:
    with _db() as c:
        r = c.execute("SELECT * FROM approvals WHERE action_id=? ORDER BY id DESC LIMIT 1", (action_id,)).fetchone()
    return dict(r) if r else None


def approval_update_status(action_id: str, status: str) -> None:
    with _db() as c:
        c.execute("UPDATE approvals SET status=? WHERE action_id=?", (status, action_id))
