"""请求上下文中间件：注入请求 ID，响应头回传 X-Request-Id。

设计说明：
- 采用纯 ASGI 实现（而非 Starlette 的 BaseHTTPMiddleware），
  后者会派生子任务，导致 auth 依赖中设置的 user contextvar 丢失；
- HTTP 访问日志交由 uvicorn 原生输出（终端带高亮），此处不重复记录；
- 未处理异常仍在此兜底记录，便于定位。
"""
import time
import uuid

from starlette.datastructures import MutableHeaders

from backend.log import get_logger, set_request_id

log = get_logger("backend.middleware")


class RequestContextMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        rid = uuid.uuid4().hex[:8]
        set_request_id(rid)
        t0 = time.perf_counter()

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message).append("X-Request-Id", rid)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            log.exception("请求处理异常 | %s %s | %.0fms",
                          scope["method"], scope["path"], (time.perf_counter() - t0) * 1000)
            raise
