"""JWT 认证：同时支持 Bearer 请求头与 httpOnly Cookie。"""
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

import bcrypt
from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from backend.config import (
    FRONTEND_URL, JWT_SECRET, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER,
)
from backend.log import get_logger, set_user_id

log = get_logger("backend.auth")

SECRET = JWT_SECRET
ALGORITHM = "HS256"
EXPIRE_HOURS = 72
RESET_EXPIRE_MINUTES = 10
COOKIE_NAME = "meiken_token"

bearer = HTTPBearer(auto_error=False)


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_token(user_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=EXPIRE_HOURS)
    return jwt.encode({"sub": str(user_id), "exp": exp}, SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        return int(payload.get("sub"))
    except JWTError:
        return None


def set_auth_cookie(response: JSONResponse, token: str):
    """登录 / 注册成功后写入 httpOnly Cookie。"""
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=EXPIRE_HOURS * 3600,
        path="/",
    )


def clear_auth_cookie(response: JSONResponse):
    """退出登录时清除 Cookie。"""
    response.delete_cookie(key=COOKIE_NAME, path="/")


async def current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> int:
    """获取当前用户 ID：优先 Cookie，其次 Bearer 请求头。

    同时把用户 ID 写入日志上下文，使同一请求的所有日志可关联。
    """
    token = request.cookies.get(COOKIE_NAME)
    if not token and creds:
        token = creds.credentials
    if not token:
        raise HTTPException(401, "未登录")
    uid = decode_token(token)
    if uid is None:
        raise HTTPException(401, "登录已过期，请重新登录")
    set_user_id(uid)
    return uid


def create_reset_token(email: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=RESET_EXPIRE_MINUTES)
    return jwt.encode({"email": email, "exp": exp, "type": "reset"}, SECRET, algorithm=ALGORITHM)


def verify_reset_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        if payload.get("type") != "reset":
            return None
        return payload.get("email")
    except JWTError:
        return None


def send_reset_email(to_email: str, token: str) -> str | None:
    """发送密码重置邮件；未配置 SMTP 时把重置链接写入日志。"""
    link = f"{FRONTEND_URL}#reset?token={token}"

    if not SMTP_HOST:
        log.info("未配置 SMTP，重置链接 | %s", link)
        return link

    body = f"点击下方链接重置 MeiKen AI 密码（{RESET_EXPIRE_MINUTES} 分钟内有效）：\n\n{link}\n\n如非本人操作，请忽略。"
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = "MeiKen AI — 重置密码"

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASSWORD)
        s.sendmail(msg["From"], to_email, msg.as_string())
    return None
