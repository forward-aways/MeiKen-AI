"""代理域：代理配置 CRUD、运行记录与人工审批。"""
import json

from backend.db._core import _db, _ts

AGENT_COLUMNS = "id,user_id,name,display_name,description,system_prompt,tools,model,thinking,reasoning_effort,temperature,is_builtin,created_at"

__all__ = [
    "AGENT_COLUMNS",
    "agent_create", "agent_list", "agent_get", "agent_get_by_name",
    "agent_update", "agent_delete", "seed_builtin_agents",
    "run_create", "run_get", "run_get_by_conv", "run_update_status",
    "approval_create", "approval_get", "approval_update_status",
]


# -- 代理配置 --

def agent_create(user_id: int, name: str, display_name: str, description: str,
                 system_prompt: str, tools: list, model: str = "deepseek-flash",
                 thinking: bool = True, reasoning_effort: str = "high",
                 temperature: float = 0.7, is_builtin: bool = False) -> dict:
    now = _ts()
    with _db() as c:
        cur = c.execute(
            f"INSERT INTO agents(user_id,name,display_name,description,system_prompt,tools,model,thinking,reasoning_effort,temperature,is_builtin,created_at)"
            f" VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (user_id, name, display_name, description, system_prompt,
             json.dumps(tools, ensure_ascii=False), model, 1 if thinking else 0,
             reasoning_effort, temperature, 1 if is_builtin else 0, now))
        return dict(c.execute(f"SELECT {AGENT_COLUMNS} FROM agents WHERE id=?", (cur.lastrowid,)).fetchone())


def agent_list(user_id: int) -> list:
    """用户可见的代理：自己的 + 内置（user_id=0）。"""
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
    """仅允许删除用户自建代理（内置不可删）。"""
    with _db() as c:
        cur = c.execute("DELETE FROM agents WHERE id=? AND is_builtin=0", (agent_id,))
    return cur.rowcount > 0


def seed_builtin_agents(builtins: list[dict]) -> None:
    """插入缺失的内置代理（user_id=0，幂等）。

    内置代理由平台维护、不可编辑；已存在的会把历史默认模型名
    （deepseek-v4-flash）迁移到当前规范名。
    """
    with _db() as c:
        existing = {r["name"] for r in c.execute("SELECT name FROM agents WHERE user_id=0").fetchall()}
        now = _ts()
        for b in builtins:
            if b["name"] in existing:
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


# -- 运行记录 --

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
    """会话最近一次运行。"""
    with _db() as c:
        r = c.execute("SELECT * FROM agent_runs WHERE conv_id=? ORDER BY id DESC LIMIT 1", (conv_id,)).fetchone()
    return dict(r) if r else None


def run_update_status(run_id: int, status: str) -> None:
    with _db() as c:
        c.execute("UPDATE agent_runs SET status=?, updated_at=? WHERE id=?", (status, _ts(), run_id))


# -- 人工审批 --

def approval_create(run_id: int, action_id: str, tool: str, args: dict) -> dict:
    now = _ts()
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
