"""统一日志系统。

两个输出共用同一种文本格式：

- 控制台（stdout）：带 ANSI 颜色高亮，方便本地开发/前台运行查看；
- 每日轮转文件 ``logs/meiken.log``（保留 LOG_DAYS 天，默认 14）。

每条日志携带请求上下文（``req=<8位十六进制> user=<id>``），
由 contextvars 提供，同一 HTTP 请求的所有日志可关联。
请求 ID 由 ``backend.middleware`` 注入，用户 ID 由 ``backend.auth`` 注入。

说明：HTTP 访问日志由 uvicorn 原生输出（终端带高亮），
本模块不重复记录访问行。

配置项（均可选）：
    LOG_LEVEL   DEBUG | INFO | WARNING | ERROR（默认 INFO）
    LOG_DIR     日志目录（默认 <项目根>/logs）
    LOG_DAYS    轮转文件保留天数（默认 14）
"""
import logging
import os
import sys
from contextvars import ContextVar
from logging.handlers import TimedRotatingFileHandler

from backend.config import LOG_DAYS, LOG_DIR, LOG_LEVEL

request_id_var: ContextVar[str] = ContextVar("mk_request_id", default="-")
user_id_var: ContextVar[str] = ContextVar("mk_user_id", default="-")

_FORMAT = "%(asctime)s [%(levelname)s] [req=%(req_id)s user=%(user_id)s] %(name)s: %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"

# ANSI 颜色：级别配色 + 辅助色
_RESET = "\033[0m"
_DIM = "\033[90m"
_MODULE = "\033[36m"
_LEVEL_COLORS = {
    logging.DEBUG: "\033[90m",
    logging.INFO: "\033[32m",
    logging.WARNING: "\033[33m",
    logging.ERROR: "\033[31m",
    logging.CRITICAL: "\033[1;41m",
}

# 这些第三方库的日志过于嘈杂，统一降到 WARNING
_NOISY_LOGGERS = (
    "httpx", "httpx2", "httpcore", "openai", "urllib3", "multipart",
    "chromadb", "langchain", "langchain_openai", "langchain_core",
    "langgraph", "deepagents", "aiosqlite", "asyncio",
)

_configured = False


def set_request_id(rid: str | None) -> None:
    """写入当前请求 ID（由中间件调用）。"""
    request_id_var.set(rid or "-")


def set_user_id(uid: int | str | None) -> None:
    """写入当前用户 ID（由认证依赖调用）。"""
    user_id_var.set(str(uid) if uid else "-")


def get_request_id() -> str:
    return request_id_var.get()


class _ContextFilter(logging.Filter):
    """把当前请求上下文注入每条日志记录。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.req_id = request_id_var.get()
        record.user_id = user_id_var.get()
        return True


class _ColorFormatter(logging.Formatter):
    """控制台彩色格式化：时间与上下文灰、级别按等级着色、模块名青色。"""

    def __init__(self, use_color: bool = True):
        super().__init__(_FORMAT, datefmt=_DATEFMT)
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        if not self.use_color:
            return super().format(record)
        color = _LEVEL_COLORS.get(record.levelno, "")
        ts = self.formatTime(record, self.datefmt)
        ctx = f"[req={record.req_id} user={record.user_id}]"
        line = (f"{_DIM}{ts}{_RESET} {color}[{record.levelname}]{_RESET} "
                f"{_DIM}{ctx}{_RESET} {_MODULE}{record.name}{_RESET}: {record.getMessage()}")
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


def setup_logging(level: str | None = None, log_dir: str | None = None) -> None:
    """安装控制台 + 轮转文件 handler（幂等，重复调用无效）。"""
    global _configured
    if _configured:
        return
    _configured = True

    level_value = getattr(logging, (level or LOG_LEVEL).upper(), logging.INFO)
    directory = log_dir or LOG_DIR
    os.makedirs(directory, exist_ok=True)

    # Windows 传统控制台默认 GBK，会导致中文日志乱码；尽量切到 UTF-8
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    ctx_filter = _ContextFilter()

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(_ColorFormatter(use_color=sys.stdout.isatty()))
    console.addFilter(ctx_filter)

    file_handler = TimedRotatingFileHandler(
        os.path.join(directory, "meiken.log"),
        when="midnight", backupCount=LOG_DAYS, encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATEFMT))
    file_handler.addFilter(ctx_filter)

    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    root.setLevel(level_value)
    root.addHandler(console)
    root.addHandler(file_handler)

    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
