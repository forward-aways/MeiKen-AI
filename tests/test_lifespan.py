"""lifespan 关闭测试：资源获取与释放必须对称。

回归目标（对应 ADR-20260921-ShutdownHang）：
aiosqlite 为每个连接启动**非 daemon** 工作线程，只有 close() 会让它退出。
启动段创建了两个连接（checkpoints / skills store），关闭段若遗漏任一，
解释器会在退出前永久等待 → Ctrl+C 卡死。
"""
import asyncio
import os
import tempfile
import threading

import backend.main as main_mod
from backend.main import _close_aiosqlite_conns, app, lifespan


class FakeConn:
    def __init__(self, fail: bool = False):
        self.closed = False
        self.fail = fail

    async def close(self):
        self.closed = True
        if self.fail:
            raise RuntimeError("close 失败")


class FakeResource:
    def __init__(self, fail: bool = False):
        self.conn = FakeConn(fail=fail)


def test_closes_every_connection():
    """T1：启动段创建的每个连接都必须在关闭段被关闭。"""
    store, saver = FakeResource(), FakeResource()
    asyncio.run(_close_aiosqlite_conns([("store", store), ("saver", saver)]))
    assert store.conn.closed, "store 连接未关闭 → 进程无法退出"
    assert saver.conn.closed, "saver 连接未关闭"


def test_tolerates_close_failure_and_keeps_closing():
    """T2：单个 close() 失败不得中断流程，也不得向上抛异常。"""
    store, saver = FakeResource(fail=True), FakeResource()
    asyncio.run(_close_aiosqlite_conns([("store", store), ("saver", saver)]))
    assert store.conn.closed
    assert saver.conn.closed, "前一个失败后仍应继续关闭其余连接"


def test_handles_missing_resources():
    """边界：资源为 None 或没有 conn 属性时不得抛异常。"""
    asyncio.run(_close_aiosqlite_conns([("none", None), ("bare", object())]))


def test_shutdown_leaves_no_aiosqlite_thread(monkeypatch):
    """T3：真实运行 lifespan 后不得残留存活的 aiosqlite 工作线程。"""
    tmp = tempfile.gettempdir()
    monkeypatch.setattr(main_mod, "_CHECKPOINTS_DB", os.path.join(tmp, "mk-test-checkpoints.db"))
    monkeypatch.setattr(main_mod, "SKILLS_STORE_DB", os.path.join(tmp, "mk-test-skills.db"))

    before = {t.ident for t in threading.enumerate()}

    async def run():
        async with lifespan(app):
            pass
        await asyncio.sleep(0.2)

    asyncio.run(run())

    leaked = [t for t in threading.enumerate() if t.ident not in before and t.is_alive()]
    assert leaked == [], f"关闭后仍有存活线程（会导致 Ctrl+C 卡死）：{leaked}"
