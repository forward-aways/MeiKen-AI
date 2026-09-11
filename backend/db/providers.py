"""供应商域：模型供应商 CRUD、模型唯一性校验与内置种子。"""
import json

from backend.crypto import encrypt_secret
from backend.db._core import _db, _ts

PROVIDER_COLUMNS = ("id,user_id,name,base_url,api_key_enc,deepseek_compat,"
                    "models,is_builtin,enabled,created_at,updated_at")

# 内置 DeepSeek 模型清单：
# deepseek-flash      —— V4.1 Flash（原生多模态，当前旗舰）
# deepseek-v4-flash   —— 兼容旧名，API 已路由至 V4.1 Flash
# deepseek-v4-pro     —— 过渡期模型，2026-09-14 起亦路由至 V4.1 Flash
BUILTIN_PROVIDER_MODELS = [
    {"name": "deepseek-flash", "context_window": 1_000_000},
    {"name": "deepseek-v4-flash", "context_window": 1_000_000},
    {"name": "deepseek-v4-pro", "context_window": 1_000_000},
]

__all__ = [
    "PROVIDER_COLUMNS", "BUILTIN_PROVIDER_MODELS",
    "provider_create", "provider_get", "provider_list", "provider_update",
    "provider_delete", "provider_find_by_model", "provider_name_exists",
    "model_name_exists", "seed_builtin_provider",
]


def provider_create(user_id: int, name: str, base_url: str, api_key_enc: str,
                    deepseek_compat: bool, models: list, is_builtin: bool = False,
                    enabled: bool = True) -> dict:
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
    """用户可见的供应商：自己的 + 内置（user_id=0）。"""
    with _db() as c:
        rows = c.execute(
            f"SELECT {PROVIDER_COLUMNS} FROM providers WHERE user_id=? OR user_id=0 "
            "ORDER BY user_id ASC, is_builtin DESC, id ASC",
            (user_id,)).fetchall()
    return [dict(r) for r in rows]


def provider_update(pid: int, fields: dict) -> None:
    """仅允许更新白名单字段。"""
    allowed = {"name", "base_url", "api_key_enc", "deepseek_compat", "models", "enabled"}
    sets, vals = [], []
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
    """按模型名找到第一个启用的供应商。"""
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
    """模型名在全部供应商中全局唯一（含内置）。"""
    for p in provider_list(user_id):
        if p["id"] == exclude_id:
            continue
        for m in json.loads(p.get("models") or "[]"):
            if m.get("name") == model:
                return True
    return False


def seed_builtin_provider(deepseek_api_key: str = "", deepseek_base_url: str = "https://api.deepseek.com") -> None:
    """种子内置 DeepSeek 供应商（user_id=0，幂等）。

    Key 仅首次种子时从 .env 读取，之后以数据库为唯一来源（可在界面修改）。
    已存在的库会把新上线的模型合并进模型列表。
    """
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
