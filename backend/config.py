"""集中配置：环境变量、路径与默认值。

设计：全项目只在此处读取 .env / 环境变量，其他模块从这里导入，
避免 os.getenv 散落在各处。所有项均有安全的默认值。
"""
import os

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# 路径
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "chat.db")
SKILLS_STORE_DB = os.path.join(BASE_DIR, "skills_store.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")            # 旧上传目录（迁移后废弃）
WORKSPACE_DIR = os.path.join(BASE_DIR, "workspace")       # 用户文件工作区
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")
CONFIG_DIR = os.path.join(BASE_DIR, "config")


# ---------------------------------------------------------------------------
# 认证与用户
# ---------------------------------------------------------------------------
JWT_SECRET = os.getenv("JWT_SECRET", "meiken-secret-change-in-production")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:3000")


# ---------------------------------------------------------------------------
# 模型供应商（仅用于首次启动时种子内置 DeepSeek，之后以数据库为准）
# ---------------------------------------------------------------------------
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
BOCHA_API_KEY = os.getenv("BOCHA_API_KEY", "")

# 同时进行的代理运行数上限
MAX_CONCURRENT_RUNS = int(os.getenv("MAX_CONCURRENT_RUNS", "4"))


# ---------------------------------------------------------------------------
# 密码重置邮件（可选，留空则日志中打印重置链接）
# ---------------------------------------------------------------------------
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")


# ---------------------------------------------------------------------------
# 日志
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR = os.getenv("LOG_DIR") or os.path.join(BASE_DIR, "logs")
LOG_DAYS = int(os.getenv("LOG_DAYS", "14"))
