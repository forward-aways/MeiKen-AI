"""对话路由：会话 CRUD、消息删除与跨会话搜索。"""
import json

from fastapi import APIRouter, Depends, HTTPException

from backend.auth import current_user
from backend.db import (
    conv_create, conv_list, conv_get, conv_delete, conv_rename,
    msg_delete, msg_list, search_messages,
)
from backend.schemas import ConvOut, ConvItem, ConvDetail, CreateConv

router = APIRouter(prefix="/api", tags=["对话"])


def _msgs_out(rows: list[dict]) -> list[dict]:
    """解析消息中的 JSON 字段（images）供 API 层使用。"""
    out = []
    for m in rows:
        m["images"] = json.loads(m.get("images") or "[]")
        out.append(m)
    return out


def _require_conv(cid: int, uid: int) -> dict:
    """校验会话存在且属于当前用户，否则 404。"""
    c = conv_get(cid)
    if not c or c.get("user_id", 0) != uid:
        raise HTTPException(404, "会话不存在")
    return c


@router.get("/conversations", response_model=list[ConvItem])
def route_conv_list(uid: int = Depends(current_user)):
    return conv_list(uid)


@router.post("/conversations", response_model=ConvOut, status_code=201)
def route_conv_create(body: CreateConv, uid: int = Depends(current_user)):
    return conv_create(uid, body.title)


@router.get("/conversations/{cid}", response_model=ConvDetail)
def route_conv_get(cid: int, uid: int = Depends(current_user)):
    c = _require_conv(cid, uid)
    c["messages"] = _msgs_out(msg_list(cid))
    return c


@router.delete("/conversations/{cid}", status_code=204)
def route_conv_delete(cid: int, uid: int = Depends(current_user)):
    _require_conv(cid, uid)
    conv_delete(cid)


@router.patch("/conversations/{cid}")
def route_conv_rename(cid: int, body: CreateConv, uid: int = Depends(current_user)):
    _require_conv(cid, uid)
    conv_rename(cid, body.title)
    return {"ok": True}


@router.delete("/conversations/{cid}/messages/{mid}")
def route_msg_delete(cid: int, mid: int, uid: int = Depends(current_user)):
    _require_conv(cid, uid)
    if not msg_delete(cid, mid):
        raise HTTPException(404, "消息不存在")
    return {"ok": True}


@router.get("/search")
def route_search(q: str = "", uid: int = Depends(current_user)):
    if not q.strip():
        return []
    return search_messages(uid, q.strip())
