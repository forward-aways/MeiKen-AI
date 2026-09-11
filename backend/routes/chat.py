"""聊天路由：SSE 对话、人工审批恢复与停止运行。"""
from functools import partial

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend import runtime
from backend.agent.bridge import stream_agent_run, stream_agent_resume
from backend.agent.factory import build_decisions, thread_id_for
from backend.agent.llm import LLMConfigError
from backend.auth import current_user
from backend.db import (
    agent_get, agent_get_by_name, approval_get, approval_update_status,
    conv_get, conv_rename, image_get, msg_add, msg_delete, msg_list,
    run_create, run_get, run_get_by_conv, run_update_status,
)
from backend.log import get_logger
from backend.schemas import ApprovalReq, ChatReq
from backend.services.chat_stream import sse_response_stream

log = get_logger("backend.routes.chat")
router = APIRouter(prefix="/api", tags=["聊天"])

_SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


@router.post("/chat/{cid}")
async def route_chat(cid: int, body: ChatReq, uid: int = Depends(current_user)):
    c = conv_get(cid)
    if not c or c.get("user_id", 0) != uid:
        raise HTTPException(404, "会话不存在")

    # 解析附图：不属于当前用户的一律丢弃
    image_records = []
    for iid in body.image_ids:
        rec = image_get(iid)
        if rec and rec.get("user_id") == uid:
            image_records.append(rec)
    if not body.message.strip() and not image_records:
        raise HTTPException(400, "消息不能为空")

    agent_cfg = agent_get(body.agent_id) if body.agent_id else agent_get_by_name(uid, "general")
    if not agent_cfg or agent_cfg.get("user_id") not in (0, uid):
        raise HTTPException(404, "智能体不存在")

    # 首条消息时用其内容命名会话
    if not msg_list(cid):
        title = body.message[:80] + ("..." if len(body.message) > 80 else "")
        if not title.strip():
            title = "[图片]"
        conv_rename(cid, title)

    user_msg = msg_add(cid, "user", body.message, images=[r["id"] for r in image_records])

    run = run_get_by_conv(cid)
    if not run or run["status"] in ("completed", "failed"):
        run = run_create(cid, agent_cfg["id"], thread_id_for(cid))
    elif run["status"] == "waiting_approval":
        raise HTTPException(409, "该会话正在等待审批，请先处理审批请求")

    overrides = {}
    if body.model:
        overrides["model"] = body.model
    if body.thinking is not None:
        overrides["thinking"] = body.thinking
    if body.reasoning_effort:
        overrides["reasoning_effort"] = body.reasoning_effort
    try:
        agent = runtime.factory.build(agent_cfg, uid, overrides, body.mode or "general")
    except LLMConfigError as exc:
        msg_delete(cid, user_msg["id"])
        log.warning("对话被拒绝 | conv=%s agent=%s | %s", cid, agent_cfg["name"], exc)
        raise HTTPException(400, str(exc))

    effective_model = overrides.get("model") or agent_cfg.get("model", "")
    log_ctx = f"conv={cid} run={run['id']} agent={agent_cfg['name']} model={effective_model} 图片={len(image_records)}"
    log.info("对话运行开始 | %s", log_ctx)

    return StreamingResponse(
        sse_response_stream(
            partial(stream_agent_run, agent, body.message, run["thread_id"],
                    run["id"], agent_cfg["name"], images=image_records),
            cid, run["id"], log_ctx,
        ),
        media_type="text/event-stream", headers=_SSE_HEADERS,
    )


@router.post("/approvals/{action_id}")
async def route_approval(action_id: str, body: ApprovalReq, uid: int = Depends(current_user)):
    ap = approval_get(action_id)
    if not ap:
        raise HTTPException(404, "审批请求不存在")
    run = run_get(ap["run_id"])
    if not run:
        raise HTTPException(404, "运行记录不存在")
    c = conv_get(run["conv_id"])
    if not c or c.get("user_id", 0) != uid:
        raise HTTPException(404, "会话不存在")
    if ap["status"] != "pending":
        raise HTTPException(409, "该审批已处理")
    agent_cfg = agent_get(run["agent_id"])
    if not agent_cfg:
        raise HTTPException(404, "智能体不存在")
    try:
        agent = runtime.factory.build(agent_cfg, uid)
    except LLMConfigError as exc:
        raise HTTPException(400, str(exc))

    decisions = build_decisions([{
        "decision": body.decision,
        "edited_args": body.edited_args,
        "message": body.message,
        "tool": ap["tool"],
    }])
    approval_update_status(action_id, body.decision)

    log_ctx = f"conv={run['conv_id']} run={run['id']} 审批={body.decision} 工具={ap['tool']}"
    log.info("审批已处理，续跑运行 | %s", log_ctx)

    return StreamingResponse(
        sse_response_stream(
            partial(stream_agent_resume, agent, decisions, run["thread_id"],
                    run["id"], agent_cfg["name"]),
            run["conv_id"], run["id"], log_ctx,
        ),
        media_type="text/event-stream", headers=_SSE_HEADERS,
    )


@router.post("/runs/{run_id}/stop")
def route_run_stop(run_id: int, uid: int = Depends(current_user)):
    run = run_get(run_id)
    if not run:
        raise HTTPException(404, "运行记录不存在")
    c = conv_get(run["conv_id"])
    if not c or c.get("user_id", 0) != uid:
        raise HTTPException(404, "会话不存在")
    run_update_status(run_id, "stopped")
    log.info("运行已停止 | run=%s", run_id)
    return {"ok": True}
