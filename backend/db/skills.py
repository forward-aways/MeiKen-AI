"""技能域：技能 CRUD、用户启用覆盖与内置种子。"""
import json

from backend.db._core import _db, _ts

SKILL_COLUMNS = "id,user_id,name,description,content,meta,enabled,source,created_at,updated_at"
SKILL_LIST_COLUMNS = "id,user_id,name,description,enabled,source,created_at,updated_at"

__all__ = [
    "SKILL_COLUMNS", "SKILL_LIST_COLUMNS",
    "skill_create", "skill_get", "skill_get_by_name", "skill_list",
    "skill_set_override", "skill_update", "skill_delete", "seed_builtin_skills",
]


def skill_create(user_id: int, name: str, description: str, content: str,
                 meta: dict, source: str = "manual", enabled: bool = True) -> dict:
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
    """用户可见的技能，并叠加用户级启用覆盖（skill_overrides）。"""
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
    """插入缺失的内置技能（user_id=0，幂等）。"""
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
