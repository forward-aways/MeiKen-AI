"""JWT authentication — supports both Bearer header and httpOnly cookie."""

import os, smtplib
from email.mime.text import MIMEText

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse

SECRET = os.getenv("JWT_SECRET", "meiken-secret-change-in-production")
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
    """Set httpOnly cookie on login/register response."""
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=EXPIRE_HOURS * 3600,
        path="/",
    )


def clear_auth_cookie(response: JSONResponse):
    """Remove auth cookie on logout."""
    response.delete_cookie(key=COOKIE_NAME, path="/")


async def current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> int:
    """Extract user_id from cookie first, then fall back to Bearer header."""
    token = request.cookies.get(COOKIE_NAME)
    if not token and creds:
        token = creds.credentials
    if not token:
        raise HTTPException(401, "Not authenticated")
    uid = decode_token(token)
    if uid is None:
        raise HTTPException(401, "Invalid or expired token")
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
    frontend = os.getenv("FRONTEND_URL", "http://127.0.0.1:3000")
    link = f"{frontend}#reset?token={token}"

    smtp_host = os.getenv("SMTP_HOST", "")
    if not smtp_host:
        print(f"\n  [RESET PASSWORD] {link}\n")
        return link

    body = f"点击下方链接重置 MeiKen AI 密码（{RESET_EXPIRE_MINUTES} 分钟内有效）：\n\n{link}\n\n如非本人操作，请忽略。"
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = os.getenv("SMTP_USER", "")
    msg["To"] = to_email
    msg["Subject"] = "MeiKen AI — 重置密码"

    with smtplib.SMTP(smtp_host, int(os.getenv("SMTP_PORT", "587"))) as s:
        s.starttls()
        s.login(os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASSWORD", ""))
        s.sendmail(msg["From"], to_email, msg.as_string())
    return None
