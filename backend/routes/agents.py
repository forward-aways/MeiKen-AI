"""智能体路由：配置 CRUD。"""
from fastapi import APIRouter, Depends, HTTPException

from backend import runtime
from backend.auth import current_user
from backend.db import agent_create, agent_delete, agent_get, agent_get_by_name, agent_list, agent_update
from backend.log import get_logger
from backend.schemas import AgentReq

log = get_logger("backend.routes.agents")
router = APIRouter(prefix="/api/agents", tags=["智能体"])


@router.get("")
def route_agents(uid: int = Depends(current_user)):
    return agent_list(uid)


@router.post("")
def route_agent_create(body: AgentReq, uid: int = Depends(current_user)):
    if agent_get_by_name(uid, body.name):
        raise HTTPException(409, "智能体标识名已存在")
    a = agent_create(uid, body.name, body.display_name or body.name, body.description,
                     body.system_prompt, body.tools, body.model, body.thinking,
                     body.reasoning_effort, body.temperature)
    log.info("创建智能体 | name=%s model=%s", a["name"], a["model"])
    return {"ok": True, "agent": a}


@router.patch("/{aid}")
def route_agent_update(aid: int, body: AgentReq, uid: int = Depends(current_user)):
    a = agent_get(aid)
    if not a or a.get("user_id", 0) != uid or a.get("is_builtin"):
        raise HTTPException(404, "智能体不存在")
    agent_update(aid, {
        "display_name": body.display_name or body.name,
        "description": body.description,
        "system_prompt": body.system_prompt,
        "tools": body.tools,
        "model": body.model,
        "thinking": body.thinking,
        "reasoning_effort": body.reasoning_effort,
        "temperature": body.temperature,
    })
    runtime.factory.invalidate(aid, uid)
    log.info("更新智能体 | id=%s name=%s model=%s", aid, a.get("name"), body.model)
    return {"ok": True, "agent": agent_get(aid)}


@router.delete("/{aid}", status_code=204)
def route_agent_delete(aid: int, uid: int = Depends(current_user)):
    a = agent_get(aid)
    if not a or a.get("user_id", 0) != uid or a.get("is_builtin"):
        raise HTTPException(404, "智能体不存在")
    agent_delete(aid)
    runtime.factory.invalidate(aid, uid)
    log.info("删除智能体 | id=%s name=%s", aid, a.get("name"))
