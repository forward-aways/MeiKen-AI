"""Unified logging for MeiKen.

Two outputs share one text format:

- console (stdout) for local development / foreground servers;
- a daily rotating file at ``logs/meiken.log`` (rotated copies keep the date
  suffix, 14 days retained by default).

Every log line carries a request scope (``req=<8-hex> user=<id>``) taken from
contextvars, so all lines of one HTTP request can be correlated. The request
scope is installed by the HTTP middleware in ``backend.main`` and the user id
by the auth dependency in ``backend.auth``.

Configuration (all optional):
    LOG_LEVEL   DEBUG | INFO | WARNING | ERROR   (default INFO)
    LOG_DIR     directory for log files         (default <project>/logs)
    LOG_DAYS    rotated files to retain         (default 14)
"""

import logging
import os
import sys
from contextvars import ContextVar
from logging.handlers import TimedRotatingFileHandler

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

request_id_var: ContextVar[str] = ContextVar("mk_request_id", default="-")
user_id_var: ContextVar[str] = ContextVar("mk_user_id", default="-")

_FORMAT = "%(asctime)s [%(levelname)s] [req=%(req_id)s user=%(user_id)s] %(name)s: %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"

_NOISY_LOGGERS = (
    "httpx", "httpx2", "httpcore", "openai", "urllib3", "multipart",
    "chromadb", "langchain", "langchain_openai", "langchain_core",
    "langgraph", "deepagents", "aiosqlite", "asyncio",
)

_configured = False


def set_request_id(rid: str | None) -> None:
    request_id_var.set(rid or "-")


def set_user_id(uid: int | str | None) -> None:
    user_id_var.set(str(uid) if uid else "-")


def get_request_id() -> str:
    return request_id_var.get()


class _ContextFilter(logging.Filter):
    """Inject the current request scope into every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.req_id = request_id_var.get()
        record.user_id = user_id_var.get()
        return True


def setup_logging(level: str | None = None, log_dir: str | None = None) -> None:
    """Install console + rotating-file handlers on the root logger. Idempotent."""
    global _configured
    if _configured:
        return
    _configured = True

    level_name = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    level_value = getattr(logging, level_name, logging.INFO)
    try:
        retain_days = int(os.getenv("LOG_DAYS", "14"))
    except ValueError:
        retain_days = 14
    directory = log_dir or os.getenv("LOG_DIR") or os.path.join(_PROJECT_ROOT, "logs")
    os.makedirs(directory, exist_ok=True)

    formatter = logging.Formatter(_FORMAT, datefmt=_DATEFMT)
    ctx_filter = _ContextFilter()

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    console.addFilter(ctx_filter)

    file_handler = TimedRotatingFileHandler(
        os.path.join(directory, "meiken.log"),
        when="midnight", backupCount=retain_days, encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(ctx_filter)

    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    root.setLevel(level_value)
    root.addHandler(console)
    root.addHandler(file_handler)

    # Access lines are emitted by our own HTTP middleware (with latency and
    # request scope) — silence uvicorn's duplicate.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
