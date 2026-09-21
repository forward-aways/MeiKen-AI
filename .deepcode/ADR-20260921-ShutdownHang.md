# ADR-20260921：Ctrl+C 无法终止（lifespan 关闭缺陷）

- 状态：待确认（Phase 1/2 完成）
- 日期：2026-09-21
- 影响面：`backend/main.py`（lifespan 关闭段）

---

## 1. 问题陈述

用户按 Ctrl+C 终止后端时**进程无法退出**，并打印：

```
INFO:     Finished server process [940]
INFO:     ASGI 'lifespan' protocol appears unsupported.
```

注意：应用本身运行正常（可正常对话），故障只出现在**关闭阶段**。

## 2. 根因分析

### 2.1 事实证据

| 事实 | 证据 |
|---|---|
| aiosqlite 每个连接启动一个**非 daemon** 工作线程 | `.venv/.../aiosqlite/core.py`：`self._thread = Thread(target=_connection_worker_thread, args=(self._tx,))`（**无 `daemon=True`**） |
| 该线程只在 `Connection.close()` 时收到 STOP 哨兵后退出 | `core.py:199` `async def close()` → `finally: self.stop()` |
| 项目创建了**两个** aiosqlite 连接 | `backend/main.py`：`runtime.saver = AsyncSqliteSaver(await aiosqlite.connect(checkpoints.db))`、`runtime.store = AsyncSqliteStore(await aiosqlite.connect(skills_store.db))` |
| 关闭时**只关闭了 saver** | `backend/main.py` 关闭段仅 `await runtime.saver.conn.close()`；**store 的连接从未关闭** |
| `AsyncSqliteStore` 的连接属性为 `.conn` | `langgraph/store/sqlite/aio.py:110` `self.conn = conn` |

### 2.2 机制

```
Ctrl+C
  └─ uvicorn 停止事件循环 → 执行 lifespan 关闭段
       ├─ saver.conn.close()   ✅ 该线程收到 STOP 并退出
       └─ store.conn           ❌ 从未 close() → 工作线程仍存活
  └─ 解释器退出前等待所有非 daemon 线程结束
       └─ 永久等待 → 进程卡死，Ctrl+C 无效
```

### 2.3 根因分层表

| 层级 | 内容 | 证据 |
|---|---|---|
| 症状 | Ctrl+C 无法终止；打印 "lifespan appears unsupported" | 用户反馈 |
| 直接原因 | lifespan 关闭段只关闭了一个 aiosqlite 连接，另一个工作线程存活 | `main.py` 关闭段 |
| **根因** | **资源获取与释放不对称**：lifespan 启动段创建了 2 个需显式关闭的异步连接，关闭段只释放 1 个；且关闭段无异常兜底，一旦抛出，uvicorn 会误判为"应用不支持 lifespan" | 同上 |

### 2.4 泛化判断

| 问题 | 一次性 / 一类 | 代表输入 | 反例 | 非适用场景 |
|---|---|---|---|---|
| 非 daemon 线程导致无法退出 | **一类**：任何"启动时创建、关闭时未释放"的资源（连接/线程/子进程） | aiosqlite 连接 | 已正确 `close()` 的连接（saver）不受影响 | 线程为 daemon 时不会阻塞退出 |

**规则**：lifespan 启动段创建的每个资源，必须在关闭段被显式释放；关闭段必须容错。

## 3. 设计方案

```python
    yield

    # 关闭所有 aiosqlite 连接：其工作线程为非 daemon 线程，
    # 未关闭会导致解释器退出前永久等待（Ctrl+C 卡死）。
    # 逐项容错：任一失败不得中断关闭流程，也不得让 uvicorn 误判 lifespan 不支持。
    for label, resource in (("store", runtime.store), ("saver", runtime.saver)):
        conn = getattr(resource, "conn", None) if resource is not None else None
        if conn is None:
            continue
        try:
            await conn.close()
        except Exception:
            log.exception("关闭 %s 连接失败", label)
    runtime.store = None
    runtime.saver = None
    log.info("MeiKen AI 已停止")
```

不变量：
- I1：启动段创建的每个 aiosqlite 连接，关闭段必须 `close()`。
- I2：关闭段逐项容错，绝不向上抛异常（避免 uvicorn 误判 lifespan 不支持）。
- I3：关闭后置空引用，防止重复关闭。

**复杂度**：O(1)。**为何不用强制退出兜底**（如 `os._exit`）：那是症状掩盖；根因是资源未释放。

## 4. 防复发机制

1. **守卫测试**（`tests/test_lifespan.py`）：用假资源（含 `conn.close()` 记录调用）验证
   - 启动段创建的所有连接在关闭段都被关闭；
   - 关闭段即使某个 `close()` 抛异常也不向外抛。
2. **注释**：在 lifespan 关闭段写明"非 daemon 线程 → 必须显式关闭"的原因。

## 5. 测试计划

| ID | 类型 | 场景 | 期望 |
|---|---|---|---|
| T1 | 单元 | 关闭段遍历 store/saver 两个假连接 | 两者的 `close()` 均被调用 |
| T2 | 单元 | 其中一个 `close()` 抛异常 | 另一个仍被关闭，且不向外抛异常 |
| T3 | 集成 | 真实运行 lifespan 后检查线程 | 无存活的 aiosqlite 工作线程 |
| T4 | 手工 | `uv run python main.py backend` 后 Ctrl+C | 进程立即退出，无 "lifespan appears unsupported" |
| T5 | 回归 | 现有后端用例 | 全通过 |
