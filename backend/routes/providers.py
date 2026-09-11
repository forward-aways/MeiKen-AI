"""模型供应商路由：CRUD 与连接测试。"""
import json
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException

from backend import runtime
from backend.auth import current_user
from backend.crypto import decrypt_secret, encrypt_secret
from backend.db import (
    model_name_exists, provider_create, provider_delete, provider_get,
    provider_list, provider_name_exists, provider_update,
)
from backend.log import get_logger
from backend.schemas import ProviderCreateReq, ProviderUpdateReq

log = get_logger("backend.routes.providers")
router = APIRouter(prefix="/api/providers", tags=["模型供应商"])


def _mask_key(enc: str) -> str:
    """脱敏展示 API Key（绝不泄露明文）。"""
    if not enc:
        return ""
    try:
        k = decrypt_secret(enc)
    except ValueError:
        return ""
    if not k:
        return ""
    if len(k) <= 8:
        return "*" * len(k)
    return k[:4] + "*" * 12 + k[-4:]


def _provider_out(p: dict) -> dict:
    return {
        "id": p["id"],
        "name": p["name"],
        "base_url": p["base_url"],
        "key_configured": bool(p["api_key_enc"]),
        "key_masked": _mask_key(p["api_key_enc"]),
        "deepseek_compat": bool(p["deepseek_compat"]),
        "models": json.loads(p.get("models") or "[]"),
        "is_builtin": bool(p["is_builtin"]),
        "enabled": bool(p["enabled"]),
    }


def _require_own_provider(pid: int, uid: int) -> dict:
    p = provider_get(pid)
    if not p or p.get("user_id") not in (0, uid):
        raise HTTPException(404, "供应商不存在")
    return p


@router.get("")
def route_providers(uid: int = Depends(current_user)):
    return [_provider_out(p) for p in provider_list(uid)]


@router.post("", status_code=201)
def route_provider_create(body: ProviderCreateReq, uid: int = Depends(current_user)):
    if provider_name_exists(uid, body.name):
        raise HTTPException(409, "供应商名称已存在")
    for m in body.models:
        if model_name_exists(uid, m.name):
            raise HTTPException(409, f"模型「{m.name}」已存在于其他供应商")
    enc = encrypt_secret(body.api_key) if body.api_key else ""
    p = provider_create(uid, body.name.strip(), body.base_url.strip(), enc,
                        body.deepseek_compat, [m.model_dump() for m in body.models])
    runtime.factory.invalidate_user(uid)
    log.info("创建供应商 | name=%s 模型数=%d 兼容模式=%s", p["name"], len(body.models), body.deepseek_compat)
    return _provider_out(p)


@router.patch("/{pid}")
def route_provider_update(pid: int, body: ProviderUpdateReq, uid: int = Depends(current_user)):
    p = _require_own_provider(pid, uid)
    data = body.model_dump(exclude_unset=True)
    if p.get("is_builtin"):
        # 内置 DeepSeek：仅允许修改 Key / Base URL / 启停
        data = {k: v for k, v in data.items() if k in {"api_key", "base_url", "enabled"}}
    if "api_key" in data:
        data["api_key_enc"] = encrypt_secret(data["api_key"]) if data["api_key"] else ""
        del data["api_key"]
    if "models" in data:
        for m in data["models"]:
            if model_name_exists(uid, m["name"], exclude_id=pid):
                raise HTTPException(409, f"模型「{m['name']}」已存在于其他供应商")
        data["models"] = [dict(m) for m in data["models"]]
    if "name" in data and provider_name_exists(uid, data["name"], exclude_id=pid):
        raise HTTPException(409, "供应商名称已存在")
    if not data:
        return _provider_out(p)
    provider_update(pid, data)
    runtime.factory.invalidate_user(uid)
    log.info("更新供应商 | id=%s name=%s 字段=%s", pid, p["name"], sorted(data.keys()))
    return _provider_out(provider_get(pid))


@router.delete("/{pid}", status_code=204)
def route_provider_delete(pid: int, uid: int = Depends(current_user)):
    p = _require_own_provider(pid, uid)
    if p.get("is_builtin"):
        raise HTTPException(403, "内置供应商不可删除")
    provider_delete(pid)
    runtime.factory.invalidate_user(uid)
    log.info("删除供应商 | id=%s name=%s", pid, p["name"])


@router.post("/{pid}/test")
def route_provider_test(pid: int, uid: int = Depends(current_user)):
    p = _require_own_provider(pid, uid)
    api_key = decrypt_secret(p["api_key_enc"]) if p.get("api_key_enc") else ""
    if not api_key:
        raise HTTPException(400, "尚未配置 API Key")
    models = json.loads(p.get("models") or "[]")
    if not models:
        raise HTTPException(400, "供应商没有可用模型")
    model = models[0]["name"]
    url = p["base_url"].rstrip("/") + "/chat/completions"
    t0 = time.perf_counter()
    try:
        r = httpx.post(
            url,
            json={"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15,
        )
        latency = int((time.perf_counter() - t0) * 1000)
        if r.status_code == 200:
            log.info("供应商测试通过 | id=%s model=%s | %dms", pid, model, latency)
            return {"ok": True, "latency_ms": latency}
        log.warning("供应商测试失败 | id=%s model=%s | HTTP %s", pid, model, r.status_code)
        return {"ok": False, "latency_ms": latency, "error": f"HTTP {r.status_code}: {r.text[:200]}"}
    except httpx.TimeoutException:
        log.warning("供应商测试超时 | id=%s model=%s", pid, model)
        return {"ok": False, "error": "连接超时（15s）"}
    except httpx.RequestError as exc:
        log.warning("供应商测试异常 | id=%s model=%s | %s", pid, model, exc)
        return {"ok": False, "error": str(exc)}
