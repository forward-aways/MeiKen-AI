import threading
import json, os, time, uuid
from contextlib import asynccontextmanager

import aiosqlite
import httpx
from starlette.datastructures import MutableHeaders
from fastapi import FastAPI, HTTPException, Depends, Body, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from backend.database import (
    conv_create, conv_list, conv_get, conv_delete, conv_rename,
    msg_add, msg_list, msg_delete, search_messages,
    user_create, user_get_by_email, user_get, user_get_by_nickname,
    user_update_password, user_update_profile, seed_admin,
    kb_add, kb_list, kb_get, kb_delete,
    agent_list, agent_get, agent_get_by_name, agent_create, agent_update,
    agent_delete, seed_builtin_agents,
    skill_get, skill_list, skill_create, skill_update, skill_delete,
    skill_get_by_name, skill_set_override, seed_builtin_skills,
    provider_list, provider_get, provider_create, provider_update,
    provider_delete, provider_name_exists, model_name_exists,
    seed_builtin_provider,
    image_add, image_get,
    run_create, run_get, run_get_by_conv, run_update_status,
    approval_get, approval_update_status,
)
from backend.schemas import (
    ConvOut, ConvItem, ConvDetail, CreateConv, ChatReq, AgentReq, ApprovalReq,
    RegisterReq, LoginReq, AuthResp, ProfileReq, ForgotReq, ResetReq, ChangePasswordReq,
    SkillCreateReq, SkillUpdateReq,
    ProviderCreateReq, ProviderUpdateReq,
)
from backend.crypto import encrypt_secret, decrypt_secret
from backend.agent.llm import LLMConfigError
from backend.log import setup_logging, get_logger, set_request_id, set_user_id

log = get_logger("backend.main")
from backend.agent.factory import AgentFactory, thread_id_for, build_decisions
from backend.agent.bridge import stream_agent_run, stream_agent_resume
from backend.agent.registry import BUILTIN_AGENTS
from backend.skills import (
    parse_skill_markdown, build_skill_markdown, slugify,
    SkillValidationError, BUILTIN_SKILLS,
)
from fastapi.responses import JSONResponse as JsonResp

from backend.auth import (
    hash_password, verify_password, create_token, current_user,
    set_auth_cookie, clear_auth_cookie,
    create_reset_token, verify_reset_token, send_reset_email,
)

_factory: AgentFactory | None = None
_saver: AsyncSqliteSaver | None = None
_store = None
_semaphore: threading.Semaphore | None = None

_MAX_CONCURRENT_RUNS = int(os.getenv("MAX_CONCURRENT_RUNS", "4"))
_CHECKPOINTS_DB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "checkpoints.db")
_SKILLS_STORE_DB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills_store.db")
_UPLOADS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
_ALLOWED_IMAGE_MIMES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
_MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB per image


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _factory, _saver, _store, _semaphore
    setup_logging()
    log.info("MeiKen AI starting (version 2.0.0, level=%s)", os.getenv("LOG_LEVEL", "INFO").upper())
    seed_admin(hash_password(os.getenv("ADMIN_PASSWORD", "admin123")))
    seed_builtin_agents(BUILTIN_AGENTS)
    seed_builtin_skills(BUILTIN_SKILLS)
    seed_builtin_provider(os.getenv("DEEPSEEK_API_KEY", ""), os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    log.info("seeds ready (admin / agents / skills / builtin provider)")
    _saver = AsyncSqliteSaver(await aiosqlite.connect(_CHECKPOINTS_DB))
    await _saver.setup()
    from langgraph.store.sqlite.aio import AsyncSqliteStore
    _store = AsyncSqliteStore(await aiosqlite.connect(_SKILLS_STORE_DB, isolation_level=None))
    await _store.setup()
    _factory = AgentFactory(_saver, _store)
    _semaphore = threading.Semaphore(_MAX_CONCURRENT_RUNS)
    log.info("checkpointer + skills store ready, max concurrent runs = %d", _MAX_CONCURRENT_RUNS)
    yield
    await _saver.conn.close()
    log.info("MeiKen AI stopped")


app = FastAPI(title="MeiKen AI", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


class RequestLogMiddleware:
    """Pure ASGI middleware.

    Unlike Starlette's BaseHTTPMiddleware this does not spawn a child task, so
    contextvar updates made in the auth dependency (user id) are still visible
    when the access line is emitted — every log of one request correlates.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        rid = uuid.uuid4().hex[:8]
        set_request_id(rid)
        t0 = time.perf_counter()
        status = {"code": None}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
                headers = MutableHeaders(scope=message)
                headers.append("X-Request-Id", rid)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            log.exception("HTTP %s %s -> unhandled error after %.0fms",
                          scope["method"], scope["path"], (time.perf_counter() - t0) * 1000)
            raise
        path = scope["path"]
        if not path.startswith("/assets"):  # static bundles would flood the log
            log.info("HTTP %s %s -> %s (%.0fms)", scope["method"], path,
                     status["code"], (time.perf_counter() - t0) * 1000)


app.add_middleware(RequestLogMiddleware)

# -- auth --

@app.post("/api/auth/register")
def route_register(body: RegisterReq):
    if user_get_by_email(body.email):
        raise HTTPException(409, "Email already registered")
    u = user_create(body.email, hash_password(body.password), body.nickname)
    token = create_token(u["id"])
    resp = JsonResp({"token": token, "user": u})
    set_auth_cookie(resp, token)
    set_user_id(u["id"])
    log.info("register ok | user=%s", u["id"])
    return resp

@app.post("/api/auth/login")
def route_login(body: LoginReq):
    u = user_get_by_email(body.email)
    if not u:
        u = user_get_by_nickname(body.email)
    if not u or not verify_password(body.password, u["password_hash"]):
        log.warning("login failed | account=%s", body.email[:60])
        raise HTTPException(401, "Invalid username or password")
    token = create_token(u["id"])
    user_data = user_get(u["id"])
    resp = JsonResp({"token": token, "user": user_data})
    set_auth_cookie(resp, token)
    set_user_id(u["id"])
    log.info("login ok | user=%s", u["id"])
    return resp

@app.get("/api/auth/me")
def route_me(uid: int = Depends(current_user)):
    u = user_get(uid)
    if not u: raise HTTPException(404, "User not found")
    return u

@app.put("/api/auth/profile")
def route_profile(body: ProfileReq, uid: int = Depends(current_user)):
    data = body.model_dump(exclude_none=True)
    if "nickname" in data:
        existing = user_get_by_nickname(data["nickname"])
        if existing and existing["id"] != uid:
            raise HTTPException(409, "Nickname already taken")
    user_update_profile(uid, data)
    return {"ok": True, "user": user_get(uid)}

@app.put("/api/auth/password")
def route_change_password(body: ChangePasswordReq, uid: int = Depends(current_user)):
    full = user_get_by_email(user_get(uid)["email"])
    if not full or not verify_password(body.old_password, full["password_hash"]):
        raise HTTPException(401, "Incorrect old password")
    user_update_password(uid, hash_password(body.new_password))
    return {"ok": True}

@app.post("/api/auth/forgot-password")
def route_forgot(body: ForgotReq):
    u = user_get_by_email(body.email)
    if not u:
        return {"ok": True}  # don't reveal if email exists
    token = create_reset_token(body.email)
    link = send_reset_email(body.email, token)
    return {"ok": True, "link": link}

@app.post("/api/auth/reset-password")
def route_reset(body: ResetReq):
    email = verify_reset_token(body.token)
    if not email:
        raise HTTPException(401, "Invalid or expired reset link")
    u = user_get_by_email(email)
    if not u:
        raise HTTPException(404, "User not found")
    user_update_password(u["id"], hash_password(body.password))
    return {"ok": True}

@app.post("/api/auth/logout")
def route_logout():
    resp = JsonResp({"ok": True})
    clear_auth_cookie(resp)
    return resp

# -- conversations (protected) --

@app.get("/api/conversations", response_model=list[ConvItem])
def route_conv_list(uid: int = Depends(current_user)):
    return conv_list(uid)

@app.post("/api/conversations", response_model=ConvOut, status_code=201)
def route_conv_create(body: CreateConv, uid: int = Depends(current_user)):
    return conv_create(uid, body.title)

@app.get("/api/conversations/{cid}", response_model=ConvDetail)
def route_conv_get(cid: int, uid: int = Depends(current_user)):
    c = conv_get(cid)
    if not c or c.get("user_id", 0) != uid: raise HTTPException(404, "Not found")
    c["messages"] = _msgs_out(msg_list(cid))
    return c


def _msgs_out(rows: list[dict]) -> list[dict]:
    """Parse JSON-encoded message fields for the API layer."""
    out = []
    for m in rows:
        m["images"] = json.loads(m.get("images") or "[]")
        out.append(m)
    return out

@app.delete("/api/conversations/{cid}", status_code=204)
def route_conv_delete(cid: int, uid: int = Depends(current_user)):
    c = conv_get(cid)
    if not c or c.get("user_id", 0) != uid: raise HTTPException(404, "Not found")
    conv_delete(cid)

@app.patch("/api/conversations/{cid}")
def route_conv_rename(cid: int, body: CreateConv, uid: int = Depends(current_user)):
    c = conv_get(cid)
    if not c or c.get("user_id", 0) != uid: raise HTTPException(404, "Not found")
    conv_rename(cid, body.title)
    return {"ok": True}

# -- chat (protected) --

@app.post("/api/chat/{cid}")
async def route_chat(cid: int, body: ChatReq, uid: int = Depends(current_user)):
    c = conv_get(cid)
    if not c or c.get("user_id", 0) != uid:
        raise HTTPException(404, "Conversation not found")

    # Resolve attached images with ownership check (foreign ids are dropped).
    image_records = []
    for iid in body.image_ids:
        rec = image_get(iid)
        if rec and rec.get("user_id") == uid:
            image_records.append(rec)
    if not body.message.strip() and not image_records:
        raise HTTPException(400, "Message is empty")

    agent_cfg = None
    if body.agent_id:
        agent_cfg = agent_get(body.agent_id)
    else:
        agent_cfg = agent_get_by_name(uid, "general")
    if not agent_cfg or agent_cfg.get("user_id") not in (0, uid):
        raise HTTPException(404, "Agent not found")

    msgs = msg_list(cid)
    if not msgs:
        title = body.message[:80] + ("..." if len(body.message) > 80 else "")
        if not title.strip():
            title = "[图片]"
        conv_rename(cid, title)

    user_msg = msg_add(cid, "user", body.message, images=[r["id"] for r in image_records])

    run = run_get_by_conv(cid)
    if not run or run["status"] in ("completed", "failed"):
        run = run_create(cid, agent_cfg["id"], thread_id_for(cid))
    elif run["status"] == "waiting_approval":
        raise HTTPException(409, "Conversation is waiting for approval decisions")

    overrides = {}
    if body.model:
        overrides["model"] = body.model
    if body.thinking is not None:
        overrides["thinking"] = body.thinking
    if body.reasoning_effort:
        overrides["reasoning_effort"] = body.reasoning_effort
    try:
        agent = _factory.build(agent_cfg, uid, overrides, body.mode or "general")
    except LLMConfigError as exc:
        msg_delete(cid, user_msg["id"])
        log.warning("chat rejected | conv=%s agent=%s | %s", cid, agent_cfg["name"], exc)
        raise HTTPException(400, str(exc))

    effective_model = overrides.get("model") or agent_cfg.get("model", "")
    log.info("chat run start | conv=%s agent=%s model=%s mode=%s images=%d",
             cid, agent_cfg["name"], effective_model, body.mode or "general", len(image_records))

    async def sse():
        if not _semaphore.acquire(blocking=False):
            log.warning("chat rejected | conv=%s | concurrency limit reached", cid)
            yield f"data: {json.dumps({'error': '并发任务数已达上限，请稍后重试'})}\n\n"
            return
        collected = []
        total_tokens = 0
        run_interrupted = False
        t0 = time.perf_counter()
        try:
            async for event in stream_agent_run(
                agent, body.message, run["thread_id"], run["id"], agent_cfg["name"],
                images=image_records
            ):
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") == "token":
                    collected.append(event["token"])
                if event.get("status") == "run_end":
                    run_interrupted = bool(event.get("interrupted"))
                    total_tokens = event.get("tokens", 0)
                    run_update_status(run["id"], "waiting_approval" if run_interrupted else "completed")
            if not run_interrupted and collected:
                saved = msg_add(cid, "assistant", "".join(collected), total_tokens)
                yield f"data: {json.dumps({'done': True, 'id': saved['id'], 'tokens': total_tokens})}\n\n"
            log.info("chat run end | conv=%s run=%s status=%s | %.1fs | %d tokens",
                     cid, run["id"], "interrupted" if run_interrupted else "completed",
                     time.perf_counter() - t0, total_tokens)
        except Exception as exc:
            log.exception("chat run failed | conv=%s run=%s agent=%s | %.1fs",
                          cid, run["id"], agent_cfg["name"], time.perf_counter() - t0)
            run_update_status(run["id"], "failed")
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        finally:
            _semaphore.release()

    return StreamingResponse(sse(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/approvals/{action_id}")
async def route_approval(action_id: str, body: ApprovalReq, uid: int = Depends(current_user)):
    ap = approval_get(action_id)
    if not ap:
        raise HTTPException(404, "Approval not found")
    run = run_get(ap["run_id"])
    if not run:
        raise HTTPException(404, "Run not found")
    c = conv_get(run["conv_id"])
    if not c or c.get("user_id", 0) != uid:
        raise HTTPException(404, "Conversation not found")
    if ap["status"] != "pending":
        raise HTTPException(409, "Approval already resolved")

    agent_cfg = agent_get(run["agent_id"])
    if not agent_cfg:
        raise HTTPException(404, "Agent not found")
    try:
        agent = _factory.build(agent_cfg, uid)
    except LLMConfigError as exc:
        raise HTTPException(400, str(exc))

    decisions = build_decisions([{
        "decision": body.decision,
        "edited_args": body.edited_args,
        "message": body.message,
        "tool": ap["tool"],
    }])
    approval_update_status(action_id, body.decision)

    async def sse():
        if not _semaphore.acquire(blocking=False):
            yield f"data: {json.dumps({'error': '并发任务数已达上限，请稍后重试'})}\n\n"
            return
        collected = []
        total_tokens = 0
        try:
            async for event in stream_agent_resume(
                agent, decisions, run["thread_id"], run["id"], agent_cfg["name"]
            ):
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") == "token":
                    collected.append(event["token"])
                if event.get("status") == "run_end":
                    total_tokens = event.get("tokens", 0)
                    run_update_status(run["id"], "waiting_approval" if event.get("interrupted") else "completed")
            if collected:
                saved = msg_add(run["conv_id"], "assistant", "".join(collected), total_tokens)
                yield f"data: {json.dumps({'done': True, 'id': saved['id'], 'tokens': total_tokens})}\n\n"
        except Exception as exc:
            log.exception("approval resume failed | run=%s action=%s", run["id"], action_id)
            run_update_status(run["id"], "failed")
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        finally:
            _semaphore.release()

    return StreamingResponse(sse(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/runs/{run_id}/stop")
def route_run_stop(run_id: int, uid: int = Depends(current_user)):
    run = run_get(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    c = conv_get(run["conv_id"])
    if not c or c.get("user_id", 0) != uid:
        raise HTTPException(404, "Conversation not found")
    run_update_status(run_id, "stopped")
    return {"ok": True}


# -- agents (protected) --

@app.get("/api/agents")
def route_agents(uid: int = Depends(current_user)):
    return agent_list(uid)


@app.post("/api/agents")
def route_agent_create(body: AgentReq, uid: int = Depends(current_user)):
    if agent_get_by_name(uid, body.name):
        raise HTTPException(409, "Agent name already exists")
    a = agent_create(uid, body.name, body.display_name or body.name, body.description,
                     body.system_prompt, body.tools, body.model, body.thinking,
                     body.reasoning_effort, body.temperature)
    log.info("agent created | name=%s model=%s", a["name"], a["model"])
    return {"ok": True, "agent": a}


@app.patch("/api/agents/{aid}")
def route_agent_update(aid: int, body: AgentReq, uid: int = Depends(current_user)):
    a = agent_get(aid)
    if not a or a.get("user_id", 0) != uid or a.get("is_builtin"):
        raise HTTPException(404, "Agent not found")
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
    _factory.invalidate(aid, uid)
    log.info("agent updated | id=%s name=%s model=%s", aid, a.get("name"), body.model)
    return {"ok": True, "agent": agent_get(aid)}


@app.delete("/api/agents/{aid}", status_code=204)
def route_agent_delete(aid: int, uid: int = Depends(current_user)):
    a = agent_get(aid)
    if not a or a.get("user_id", 0) != uid or a.get("is_builtin"):
        raise HTTPException(404, "Agent not found")
    agent_delete(aid)
    _factory.invalidate(aid, uid)
    log.info("agent deleted | id=%s name=%s", aid, a.get("name"))

@app.delete("/api/conversations/{cid}/messages/{mid}")
def route_msg_delete(cid: int, mid: int, uid: int = Depends(current_user)):
    c = conv_get(cid)
    if not c or c.get("user_id", 0) != uid:
        raise HTTPException(404, "Conversation not found")
    if not msg_delete(cid, mid):
        raise HTTPException(404, "Message not found")
    return {"ok": True}

@app.get("/api/health")
def health():
    return {"status": "ok"}

# -- knowledge base (protected) --

ALLOWED_EXTS = {".txt", ".md", ".pdf", ".docx"}

@app.post("/api/kb/upload")
async def route_kb_upload(file: UploadFile = File(...), scope: str = "kb", uid: int = Depends(current_user)):
    filename = file.filename or "unknown.txt"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(400, f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTS)}")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 10MB)")
    from backend.rag import save_upload_file, ingest_document
    filepath, file_id = save_upload_file(content, filename)
    chunks = ingest_document(filepath, filename, file_id, scope=scope, user_id=uid)
    rec = kb_add(file_id, uid, filename, filepath, chunks, scope)
    return {"ok": True, "file": {"id": file_id, "filename": filename, "chunks": chunks}}

@app.get("/api/kb/files")
def route_kb_list(uid: int = Depends(current_user)):
    return kb_list(uid, "kb")

@app.delete("/api/kb/files/{file_id}")
def route_kb_delete(file_id: str, uid: int = Depends(current_user)):
    rec = kb_get(file_id)
    if not rec or rec.get("user_id") != uid:
        raise HTTPException(404, "File not found")
    from backend.rag import delete_document, cleanup_upload_file
    delete_document(file_id)
    cleanup_upload_file(rec["filepath"])
    kb_delete(file_id)
    return {"ok": True}

@app.get("/api/search")
def route_search(q: str = "", uid: int = Depends(current_user)):
    if not q.strip(): return []
    return search_messages(uid, q.strip())

# -- skills (protected) --

async def _sync_user_skills(user_id: int) -> None:
    """Mirror the user's enabled skills (incl. builtins) into the langgraph store."""
    from deepagents.backends.utils import create_file_data
    ns = ("skills", str(user_id))
    enabled = [r for r in skill_list(user_id) if r["enabled"]]
    names = {r["name"] for r in enabled}
    for r in enabled:
        full = skill_get(r["id"])
        if not full:
            continue
        await _store.aput(ns, f"/skills/{r['name']}/SKILL.md", create_file_data(full["content"]))
    for item in await _store.asearch(ns):
        parts = item.key.split("/")
        if len(parts) >= 3 and parts[2] not in names:
            await _store.adelete(ns, item.key)


@app.get("/api/skills")
def route_skill_list(uid: int = Depends(current_user)):
    return skill_list(uid)


@app.get("/api/skills/{sid}")
def route_skill_get(sid: int, uid: int = Depends(current_user)):
    s = skill_get(sid)
    if not s or s.get("user_id") not in (0, uid):
        raise HTTPException(404, "Skill not found")
    return s


@app.post("/api/skills", status_code=201)
async def route_skill_create(body: SkillCreateReq, uid: int = Depends(current_user)):
    if skill_get_by_name(uid, body.name):
        raise HTTPException(409, "Skill name already exists")
    content = build_skill_markdown(body.name, body.description, body.body)
    try:
        parsed = parse_skill_markdown(content, fallback_name=body.name)
    except SkillValidationError as exc:
        raise HTTPException(400, str(exc))
    s = skill_create(uid, parsed["name"], parsed["description"], content, parsed["meta"])
    await _sync_user_skills(uid)
    _factory.invalidate_user(uid)
    log.info("skill created | name=%s", s["name"])
    return {"ok": True, "skill": {k: s[k] for k in s if k != "content"}}


@app.post("/api/skills/upload", status_code=201)
async def route_skill_upload(file: UploadFile = File(...), uid: int = Depends(current_user)):
    filename = file.filename or "skill.md"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in {".md", ".txt", ".docx"}:
        raise HTTPException(400, "仅支持 .md / .txt / .docx 文件")
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 2MB)")
    from backend.rag import extract_text, save_upload_file, cleanup_upload_file
    filepath, _file_id = save_upload_file(content, filename)
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
        raise HTTPException(409, "Skill name already exists")
    s = skill_create(uid, parsed["name"], parsed["description"], text.strip(), parsed["meta"], source="upload")
    await _sync_user_skills(uid)
    _factory.invalidate_user(uid)
    log.info("skill uploaded | name=%s file=%s", s["name"], filename)
    return {"ok": True, "skill": {k: s[k] for k in s if k != "content"}}


@app.patch("/api/skills/{sid}")
async def route_skill_update(sid: int, body: SkillUpdateReq, uid: int = Depends(current_user)):
    s = skill_get(sid)
    if not s or s.get("user_id") not in (0, uid):
        raise HTTPException(404, "Skill not found")
    if s.get("user_id") == 0:
        # Builtin skills are shared; per-user state lives in the overrides table.
        if body.enabled is not None:
            skill_set_override(uid, sid, body.enabled)
        elif body.description is not None or body.body is not None:
            raise HTTPException(403, "内置技能不可编辑，仅可启用或关闭")
        await _sync_user_skills(uid)
        _factory.invalidate_user(uid)
        updated = skill_get(sid)
        if updated.get("user_id") == 0:
            # reflect the user's effective state
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
    _factory.invalidate_user(uid)
    updated = skill_get(sid)
    log.info("skill updated | name=%s fields=%s", s["name"], sorted(fields.keys()))
    return {"ok": True, "skill": {k: updated[k] for k in updated if k != "content"}}


@app.delete("/api/skills/{sid}", status_code=204)
async def route_skill_delete(sid: int, uid: int = Depends(current_user)):
    s = skill_get(sid)
    if not s or s.get("user_id") != uid:
        raise HTTPException(404, "Skill not found")
    skill_delete(sid, uid)
    await _sync_user_skills(uid)
    _factory.invalidate_user(uid)
    log.info("skill deleted | name=%s", s["name"])

# -- providers (protected) --

def _mask_key(enc: str) -> str:
    """Mask an encrypted API key for UI display (never leaks plaintext)."""
    if not enc:
        return ""
    try:
        k = decrypt_secret(enc)
    except ValueError:
        return ""
    if not k:
        return ""
    if len(k) <= 8:
        return "*" * len(k)
    return k[:4] + "*" * 12 + k[-4:]


def _provider_out(p: dict) -> dict:
    return {
        "id": p["id"],
        "name": p["name"],
        "base_url": p["base_url"],
        "key_configured": bool(p["api_key_enc"]),
        "key_masked": _mask_key(p["api_key_enc"]),
        "deepseek_compat": bool(p["deepseek_compat"]),
        "models": json.loads(p.get("models") or "[]"),
        "is_builtin": bool(p["is_builtin"]),
        "enabled": bool(p["enabled"]),
    }


def _require_own_provider(pid: int, uid: int) -> dict:
    p = provider_get(pid)
    if not p or p.get("user_id") not in (0, uid):
        raise HTTPException(404, "Provider not found")
    return p


@app.get("/api/providers")
def route_providers(uid: int = Depends(current_user)):
    return [_provider_out(p) for p in provider_list(uid)]


@app.post("/api/providers", status_code=201)
def route_provider_create(body: ProviderCreateReq, uid: int = Depends(current_user)):
    if provider_name_exists(uid, body.name):
        raise HTTPException(409, "Provider name already exists")
    for m in body.models:
        if model_name_exists(uid, m.name):
            raise HTTPException(409, f"Model '{m.name}' already exists in another provider")
    enc = encrypt_secret(body.api_key) if body.api_key else ""
    p = provider_create(uid, body.name.strip(), body.base_url.strip(), enc,
                        body.deepseek_compat, [m.model_dump() for m in body.models])
    _factory.invalidate_user(uid)
    log.info("provider created | name=%s models=%d compat=%s",
             p["name"], len(body.models), body.deepseek_compat)
    return _provider_out(p)


@app.patch("/api/providers/{pid}")
def route_provider_update(pid: int, body: ProviderUpdateReq, uid: int = Depends(current_user)):
    p = _require_own_provider(pid, uid)
    data = body.model_dump(exclude_unset=True)
    if p.get("is_builtin"):
        # Built-in DeepSeek: only the key, base_url and enabled flag are editable.
        data = {k: v for k, v in data.items() if k in {"api_key", "base_url", "enabled"}}
    if "api_key" in data:
        data["api_key_enc"] = encrypt_secret(data["api_key"]) if data["api_key"] else ""
        del data["api_key"]
    if "models" in data:
        for m in data["models"]:
            if model_name_exists(uid, m["name"], exclude_id=pid):
                raise HTTPException(409, f"Model '{m['name']}' already exists in another provider")
        data["models"] = [dict(m) for m in data["models"]]
    if "name" in data and provider_name_exists(uid, data["name"], exclude_id=pid):
        raise HTTPException(409, "Provider name already exists")
    if not data:
        return _provider_out(p)
    provider_update(pid, data)
    _factory.invalidate_user(uid)
    log.info("provider updated | id=%s name=%s fields=%s", pid, p["name"], sorted(data.keys()))
    return _provider_out(provider_get(pid))


@app.delete("/api/providers/{pid}", status_code=204)
def route_provider_delete(pid: int, uid: int = Depends(current_user)):
    p = _require_own_provider(pid, uid)
    if p.get("is_builtin"):
        raise HTTPException(403, "内置供应商不可删除")
    provider_delete(pid)
    _factory.invalidate_user(uid)
    log.info("provider deleted | id=%s name=%s", pid, p["name"])


@app.post("/api/providers/{pid}/test")
def route_provider_test(pid: int, uid: int = Depends(current_user)):
    p = _require_own_provider(pid, uid)
    api_key = decrypt_secret(p["api_key_enc"]) if p.get("api_key_enc") else ""
    if not api_key:
        raise HTTPException(400, "API key not configured")
    models = json.loads(p.get("models") or "[]")
    if not models:
        raise HTTPException(400, "Provider has no models")
    model = models[0]["name"]
    url = p["base_url"].rstrip("/") + "/chat/completions"
    t0 = time.perf_counter()
    try:
        r = httpx.post(
            url,
            json={"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15,
        )
        latency = int((time.perf_counter() - t0) * 1000)
        if r.status_code == 200:
            log.info("provider test ok | id=%s model=%s | %dms", pid, model, latency)
            return {"ok": True, "latency_ms": latency}
        log.warning("provider test failed | id=%s model=%s | HTTP %s", pid, model, r.status_code)
        return {"ok": False, "latency_ms": latency, "error": f"HTTP {r.status_code}: {r.text[:200]}"}
    except httpx.TimeoutException:
        log.warning("provider test timeout | id=%s model=%s", pid, model)
        return {"ok": False, "error": "连接超时（15s）"}
    except httpx.RequestError as exc:
        log.warning("provider test error | id=%s model=%s | %s", pid, model, exc)
        return {"ok": False, "error": str(exc)}


# -- images (multimodal attachments) --

@app.post("/api/images", status_code=201)
async def route_image_upload(file: UploadFile = File(...), uid: int = Depends(current_user)):
    mime = (file.content_type or "").lower()
    ext = _ALLOWED_IMAGE_MIMES.get(mime)
    if not ext:
        raise HTTPException(400, "仅支持 PNG / JPEG / WebP / GIF 图片")
    content = await file.read()
    if not content:
        raise HTTPException(400, "文件内容为空")
    if len(content) > _MAX_IMAGE_SIZE:
        raise HTTPException(400, "图片过大（限 5MB）")
    image_id = uuid.uuid4().hex
    dirpath = os.path.join(_UPLOADS_DIR, str(uid))
    os.makedirs(dirpath, exist_ok=True)
    filepath = os.path.join(dirpath, image_id + ext)
    with open(filepath, "wb") as f:
        f.write(content)
    rec = image_add(image_id, uid, file.filename or f"image{ext}", filepath, mime, len(content))
    log.info("image uploaded | id=%s mime=%s size=%d", image_id, mime, len(content))
    return {
        "id": rec["id"],
        "url": f"/api/images/{rec['id']}",
        "filename": rec["filename"],
        "mime": rec["mime"],
        "size": rec["size"],
    }


@app.get("/api/images/{image_id}")
def route_image_get(image_id: str, uid: int = Depends(current_user)):
    rec = image_get(image_id)
    if not rec or rec.get("user_id") != uid:
        raise HTTPException(404, "Image not found")
    if not os.path.exists(rec["filepath"]):
        raise HTTPException(404, "Image file missing")
    return FileResponse(rec["filepath"], media_type=rec["mime"], filename=rec["filename"])


# -- serve frontend (production) --

from fastapi.staticfiles import StaticFiles

_frontend_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
if os.path.isdir(_frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(_frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        # Never cache index.html: it references hashed asset bundles, so a stale
        # index would keep serving the previous UI after a rebuild.
        return FileResponse(
            os.path.join(_frontend_dist, "index.html"),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )

