"""认证路由：注册、登录、资料、密码与找回。"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse as JsonResp

from backend.auth import (
    hash_password, verify_password, create_token, current_user,
    set_auth_cookie, clear_auth_cookie,
    create_reset_token, verify_reset_token, send_reset_email,
)
from backend.db import (
    user_create, user_get_by_email, user_get, user_get_by_nickname,
    user_update_password, user_update_profile,
)
from backend.log import get_logger, set_user_id
from backend.schemas import RegisterReq, LoginReq, ProfileReq, ForgotReq, ResetReq, ChangePasswordReq

log = get_logger("backend.routes.auth")
router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register")
def route_register(body: RegisterReq):
    if user_get_by_email(body.email):
        raise HTTPException(409, "该邮箱已注册")
    u = user_create(body.email, hash_password(body.password), body.nickname)
    token = create_token(u["id"])
    resp = JsonResp({"token": token, "user": u})
    set_auth_cookie(resp, token)
    set_user_id(u["id"])
    log.info("用户注册 | user=%s", u["id"])
    return resp


@router.post("/login")
def route_login(body: LoginReq):
    u = user_get_by_email(body.email)
    if not u:
        u = user_get_by_nickname(body.email)
    if not u or not verify_password(body.password, u["password_hash"]):
        log.warning("登录失败 | account=%s", body.email[:60])
        raise HTTPException(401, "用户名或密码错误")
    token = create_token(u["id"])
    user_data = user_get(u["id"])
    resp = JsonResp({"token": token, "user": user_data})
    set_auth_cookie(resp, token)
    set_user_id(u["id"])
    log.info("登录成功 | user=%s", u["id"])
    return resp


@router.get("/me")
def route_me(uid: int = Depends(current_user)):
    u = user_get(uid)
    if not u:
        raise HTTPException(404, "用户不存在")
    return u


@router.put("/profile")
def route_profile(body: ProfileReq, uid: int = Depends(current_user)):
    data = body.model_dump(exclude_none=True)
    if "nickname" in data:
        existing = user_get_by_nickname(data["nickname"])
        if existing and existing["id"] != uid:
            raise HTTPException(409, "昵称已被占用")
    user_update_profile(uid, data)
    return {"ok": True, "user": user_get(uid)}


@router.put("/password")
def route_change_password(body: ChangePasswordReq, uid: int = Depends(current_user)):
    full = user_get_by_email(user_get(uid)["email"])
    if not full or not verify_password(body.old_password, full["password_hash"]):
        raise HTTPException(401, "原密码错误")
    user_update_password(uid, hash_password(body.new_password))
    log.info("修改密码 | user=%s", uid)
    return {"ok": True}


@router.post("/forgot-password")
def route_forgot(body: ForgotReq):
    u = user_get_by_email(body.email)
    if not u:
        return {"ok": True}  # 不暴露邮箱是否存在
    token = create_reset_token(body.email)
    link = send_reset_email(body.email, token)
    log.info("发送重置邮件 | user=%s", u["id"])
    return {"ok": True, "link": link}


@router.post("/reset-password")
def route_reset(body: ResetReq):
    email = verify_reset_token(body.token)
    if not email:
        raise HTTPException(401, "重置链接无效或已过期")
    u = user_get_by_email(email)
    if not u:
        raise HTTPException(404, "用户不存在")
    user_update_password(u["id"], hash_password(body.password))
    log.info("重置密码 | user=%s", u["id"])
    return {"ok": True}


@router.post("/logout")
def route_logout():
    resp = JsonResp({"ok": True})
    clear_auth_cookie(resp)
    return resp
