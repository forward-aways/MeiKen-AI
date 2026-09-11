"""文件工作区测试：上传 → 列表 → 预览 → 下载 → 路径安全。"""
import random

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="module")
def auth():
    with TestClient(app) as c:
        suffix = random.randint(100000, 999999)
        r = c.post("/api/auth/register", json={
            "email": f"files{suffix}@t.com",
            "password": "pass1234",
            "nickname": f"files{suffix}",
        })
        assert r.status_code == 200, r.text
        yield c


def test_upload_then_list(auth):
    r = auth.post(
        "/api/kb/upload",
        files={"file": ("test_note.txt", "这是测试内容".encode("utf-8"), "text/plain")},
    )
    assert r.status_code == 200, r.text
    file_id = r.json()["file"]["id"]

    r = auth.get("/api/files", params={"scope": "uploads"})
    assert r.status_code == 200
    files = r.json()
    assert any(f["path"].startswith("uploads/") for f in files)

    # 清理：删除知识库文件
    r = auth.delete(f"/api/kb/files/{file_id}")
    assert r.status_code == 200


def test_read_preview(auth):
    r = auth.post(
        "/api/kb/upload",
        files={"file": ("preview_me.txt", "预览内容 ABC".encode("utf-8"), "text/plain")},
    )
    assert r.status_code == 200
    file_id = r.json()["file"]["id"]

    files = auth.get("/api/files", params={"scope": "uploads"}).json()
    path = next(f["path"] for f in files if f["name"].startswith("preview_me"))
    r = auth.get("/api/files/read", params={"path": path})
    assert r.status_code == 200, r.text
    assert "预览内容 ABC" in r.json()["content"]

    r = auth.delete(f"/api/kb/files/{file_id}")
    assert r.status_code == 200


def test_download(auth):
    r = auth.post(
        "/api/kb/upload",
        files={"file": ("dl_me.txt", "下载内容".encode("utf-8"), "text/plain")},
    )
    assert r.status_code == 200
    file_id = r.json()["file"]["id"]

    files = auth.get("/api/files", params={"scope": "uploads"}).json()
    path = next(f["path"] for f in files if f["name"].startswith("dl_me"))
    r = auth.get("/api/files/download", params={"path": path})
    assert r.status_code == 200
    assert "下载内容".encode("utf-8") in r.content

    auth.delete(f"/api/kb/files/{file_id}")


def test_path_traversal_blocked(auth):
    r = auth.get("/api/files/read", params={"path": "../../../Windows/win.ini"})
    assert r.status_code == 400

    r = auth.get("/api/files/download", params={"path": "../../chat.db"})
    assert r.status_code == 400


def test_missing_file_404(auth):
    r = auth.get("/api/files/read", params={"path": "uploads/not-exist.txt"})
    assert r.status_code == 404
