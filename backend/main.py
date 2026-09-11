"""MeiKen AI 应用装配。

职责边界：
- 日志初始化与生命周期（种子数据 / 检查点 / 技能存储 / 代理工厂）；
- 中间件与全局异常处理；
- 路由注册与前端静态资源托管。

业务逻辑位于 ``backend/routes``（HTTP 层）与 ``backend/services``（服务层）。
"""
import os
import threading
from contextlib import asynccontextmanager

import aiosqlite
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from backend import runtime
from backend.agent.factory import AgentFactory
from backend.agent.registry import BUILTIN_AGENTS
from backend.auth import hash_password
from backend.config import (
    ADMIN_PASSWORD, BASE_DIR, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL,
    LOG_LEVEL, MAX_CONCURRENT_RUNS, SKILLS_STORE_DB,
)
from backend.db import (
    seed_admin, seed_builtin_agents, seed_builtin_provider, seed_builtin_skills,
)
from backend.log import get_logger, setup_logging
from backend.middleware import RequestContextMiddleware
from backend.routes import all_routers
from backend.skills import BUILTIN_SKILLS
from backend.workspace import migrate_legacy_uploads

log = get_logger("backend.main")

APP_VERSION = "2.0.0"
_CHECKPOINTS_DB = os.path.join(BASE_DIR, "checkpoints.db")
_FRONTEND_DIST = os.path.join(BASE_DIR, "frontend", "dist")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    log.info("MeiKen AI 启动中（版本 %s，日志级别 %s）", APP_VERSION, LOG_LEVEL)

    # 幂等种子：管理员 / 内置智能体 / 内置技能 / 内置供应商
    seed_admin(hash_password(ADMIN_PASSWORD))
    seed_builtin_agents(BUILTIN_AGENTS)
    seed_builtin_skills(BUILTIN_SKILLS)
    seed_builtin_provider(DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL)
    log.info("种子数据就绪（管理员 / 智能体 / 技能 / 内置供应商）")

    # 旧上传目录 → 用户工作区（幂等）
    migrate_legacy_uploads()
    log.info("用户工作区就绪")

    # 对话检查点与技能文件存储
    runtime.saver = AsyncSqliteSaver(await aiosqlite.connect(_CHECKPOINTS_DB))
    await runtime.saver.setup()
    from langgraph.store.sqlite.aio import AsyncSqliteStore
    runtime.store = AsyncSqliteStore(await aiosqlite.connect(SKILLS_STORE_DB, isolation_level=None))
    await runtime.store.setup()

    runtime.factory = AgentFactory(runtime.saver, runtime.store)
    runtime.semaphore = threading.Semaphore(MAX_CONCURRENT_RUNS)
    log.info("检查点与技能存储就绪，最大并发运行数 = %d", MAX_CONCURRENT_RUNS)

    yield

    await runtime.saver.conn.close()
    log.info("MeiKen AI 已停止")


app = FastAPI(title="MeiKen AI", version=APP_VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.add_middleware(RequestContextMiddleware)

for _r in all_routers:
    app.include_router(_r)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """全局异常兜底：记录日志并返回统一错误体。"""
    log.exception("未处理异常 | %s %s", request.method, request.url.path)
    return JSONResponse({"detail": "服务器内部错误"}, status_code=500)


# -- 前端静态资源（生产构建存在时托管） --
if os.path.isdir(_FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(_FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        # index.html 绝不缓存：其引用哈希化资源，旧缓存会导致重建后界面不更新
        return FileResponse(
            os.path.join(_FRONTEND_DIST, "index.html"),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )
