"""后端冒烟测试：覆盖认证、会话、代理、供应商、技能、知识库等核心接口。

运行方式：
    uv run --with pytest pytest tests/ -v
"""
import random

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth(client):
    """注册一个随机测试用户并保持登录态。"""
    suffix = random.randint(100000, 999999)
    r = client.post("/api/auth/register", json={
        "email": f"pytest{suffix}@t.com",
        "password": "pass1234",
        "nickname": f"pytest{suffix}",
    })
    assert r.status_code == 200, r.text
    return client


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_register_sets_request_id(auth):
    # 注册时响应头应带请求 ID（由中间件注入）
    r = auth.post("/api/auth/login", json={"email": "nobody@t.com", "password": "x"})
    assert "X-Request-Id" in r.headers


def test_me(auth):
    r = auth.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["email"].startswith("pytest")


def test_conversation_flow(auth):
    r = auth.post("/api/conversations", json={"title": "冒烟会话"})
    assert r.status_code == 201
    cid = r.json()["id"]

    r = auth.get("/api/conversations")
    assert r.status_code == 200
    assert any(x["id"] == cid for x in r.json())

    r = auth.get(f"/api/conversations/{cid}")
    assert r.status_code == 200
    assert r.json()["messages"] == []

    r = auth.delete(f"/api/conversations/{cid}")
    assert r.status_code == 204


def test_agents_crud(auth):
    r = auth.get("/api/agents")
    assert r.status_code == 200
    assert len(r.json()) >= 1  # 至少有内置代理

    name = f"pytest-agent-{random.randint(100, 999)}"
    r = auth.post("/api/agents", json={
        "name": name, "display_name": "冒烟代理", "description": "",
        "system_prompt": "", "tools": [], "model": "deepseek-flash",
        "thinking": True, "reasoning_effort": "high", "temperature": 0.7,
    })
    assert r.status_code == 200, r.text
    aid = r.json()["agent"]["id"]

    r = auth.delete(f"/api/agents/{aid}")
    assert r.status_code == 204


def test_providers_include_builtin(auth):
    r = auth.get("/api/providers")
    assert r.status_code == 200
    assert any(p["is_builtin"] for p in r.json())


def test_skills_list(auth):
    r = auth.get("/api/skills")
    assert r.status_code == 200


def test_kb_list(auth):
    r = auth.get("/api/kb/files")
    assert r.status_code == 200


def test_search_empty(auth):
    r = auth.get("/api/search", params={"q": "不存在的内容xyz"})
    assert r.status_code == 200
    assert r.json() == []


def test_protected_requires_auth(client):
    # 独立的匿名客户端（不共享已登录 Cookie）
    with TestClient(app) as anon:
        r = anon.get("/api/conversations")
        assert r.status_code == 401
