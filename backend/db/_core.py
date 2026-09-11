"""数据库核心：连接管理与建表迁移。

设计：所有域模块通过 ``_db()`` 上下文管理器获取连接；
建表 SQL 与列迁移在此集中处理（幂等，可重复执行）。
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from backend.config import DB_PATH

DB = DB_PATH


def _ts():
    """统一时间戳：UTC ISO 格式字符串。"""
    return datetime.now(timezone.utc).isoformat()


# 全部表结构（首次启动时执行；已存在则跳过）
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

# 初版发布后新增的列：对已有数据库用 ALTER TABLE 补齐
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

_tables_ready = False


def _migrate(conn):
    """为旧库补列（幂等）。"""
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
    """获取数据库连接（自动提交 / 回滚 / 关闭）。

    首次调用时执行建表与迁移；WAL 模式提升并发读性能。
    """
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
