"""技能路由：列表、创建、上传、更新、删除（含用户级启用覆盖）。"""
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend import runtime
from backend.auth import current_user
from backend.db import (
    skill_create, skill_delete, skill_get, skill_get_by_name, skill_list,
    skill_set_override, skill_update,
)
from backend.documents import SUPPORTED_EXTS
from backend.log import get_logger
from backend.schemas import SkillCreateReq, SkillUpdateReq
from backend.skills import (
    BUILTIN_SKILLS, SkillValidationError, build_skill_markdown,
    parse_skill_markdown, slugify,
)

log = get_logger("backend.routes.skills")
router = APIRouter(prefix="/api/skills", tags=["技能"])


async def _sync_user_skills(user_id: int) -> None:
    """把用户启用的技能（含内置）镜像到 langgraph store，供代理读取。"""
    from deepagents.backends.utils import create_file_data
    ns = ("skills", str(user_id))
    enabled = [r for r in skill_list(user_id) if r["enabled"]]
    names = {r["name"] for r in enabled}
    for r in enabled:
        full = skill_get(r["id"])
        if not full:
            continue
        await runtime.store.aput(ns, f"/skills/{r['name']}/SKILL.md", create_file_data(full["content"]))
    for item in await runtime.store.asearch(ns):
        parts = item.key.split("/")
        if len(parts) >= 3 and parts[2] not in names:
            await runtime.store.adelete(ns, item.key)


@router.get("")
def route_skill_list(uid: int = Depends(current_user)):
    return skill_list(uid)


@router.get("/{sid}")
def route_skill_get(sid: int, uid: int = Depends(current_user)):
    s = skill_get(sid)
    if not s or s.get("user_id") not in (0, uid):
        raise HTTPException(404, "技能不存在")
    return s


@router.post("", status_code=201)
async def route_skill_create(body: SkillCreateReq, uid: int = Depends(current_user)):
    if skill_get_by_name(uid, body.name):
        raise HTTPException(409, "技能名称已存在")
    content = build_skill_markdown(body.name, body.description, body.body)
    try:
        parsed = parse_skill_markdown(content, fallback_name=body.name)
    except SkillValidationError as exc:
        raise HTTPException(400, str(exc))
    s = skill_create(uid, parsed["name"], parsed["description"], content, parsed["meta"])
    await _sync_user_skills(uid)
    runtime.factory.invalidate_user(uid)
    log.info("创建技能 | name=%s", s["name"])
    return {"ok": True, "skill": {k: s[k] for k in s if k != "content"}}


@router.post("/upload", status_code=201)
async def route_skill_upload(file: UploadFile = File(...), uid: int = Depends(current_user)):
    filename = file.filename or "skill.md"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in SUPPORTED_EXTS:
        raise HTTPException(400, f"不支持的文件类型：{ext}")
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(400, "文件过大（限 2MB）")
    from backend.rag import cleanup_upload_file, extract_text, save_upload_file
    filepath, _file_id = save_upload_file(content, filename, uid)
    try:
        text = extract_text(filepath, filename)
    finally:
        cleanup_upload_file(filepath)
    if not text.strip():
        raise HTTPException(400, "文件内容为空")
    try:
        parsed = parse_skill_markdown(text, fallback_name=slugify(os.path.splitext(filename)[0]))
    except SkillValidationError as exc:
        raise HTTPException(400, str(exc))
    if skill_get_by_name(uid, parsed["name"]):
        raise HTTPException(409, "技能名称已存在")
    s = skill_create(uid, parsed["name"], parsed["description"], text.strip(), parsed["meta"], source="upload")
    await _sync_user_skills(uid)
    runtime.factory.invalidate_user(uid)
    log.info("上传技能 | name=%s file=%s", s["name"], filename)
    return {"ok": True, "skill": {k: s[k] for k in s if k != "content"}}


@router.patch("/{sid}")
async def route_skill_update(sid: int, body: SkillUpdateReq, uid: int = Depends(current_user)):
    s = skill_get(sid)
    if not s or s.get("user_id") not in (0, uid):
        raise HTTPException(404, "技能不存在")
    if s.get("user_id") == 0:
        # 内置技能共享：每用户状态存于 skill_overrides
        if body.enabled is not None:
            skill_set_override(uid, sid, body.enabled)
        elif body.description is not None or body.body is not None:
            raise HTTPException(403, "内置技能不可编辑，仅可启用或关闭")
        await _sync_user_skills(uid)
        runtime.factory.invalidate_user(uid)
        updated = skill_get(sid)
        if updated.get("user_id") == 0:
            updated["enabled"] = 1 if body.enabled is None else body.enabled
        return {"ok": True, "skill": {k: updated[k] for k in updated if k != "content"}}
    fields = {}
    if body.description is not None:
        fields["description"] = body.description
    if body.body is not None:
        content = build_skill_markdown(s["name"], body.description or s["description"], body.body)
        fields["content"] = content
        try:
            parsed = parse_skill_markdown(content, fallback_name=s["name"])
        except SkillValidationError as exc:
            raise HTTPException(400, str(exc))
        fields["description"] = parsed["description"]
        fields["meta"] = parsed["meta"]
    if body.enabled is not None:
        fields["enabled"] = body.enabled
    skill_update(sid, fields)
    await _sync_user_skills(uid)
    runtime.factory.invalidate_user(uid)
    updated = skill_get(sid)
    log.info("更新技能 | name=%s 字段=%s", s["name"], sorted(fields.keys()))
    return {"ok": True, "skill": {k: updated[k] for k in updated if k != "content"}}


@router.delete("/{sid}", status_code=204)
async def route_skill_delete(sid: int, uid: int = Depends(current_user)):
    s = skill_get(sid)
    if not s or s.get("user_id") != uid:
        raise HTTPException(404, "技能不存在")
    skill_delete(sid, uid)
    await _sync_user_skills(uid)
    runtime.factory.invalidate_user(uid)
    log.info("删除技能 | name=%s", s["name"])
