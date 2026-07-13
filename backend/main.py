import json, traceback, os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Body, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.database import (
    conv_create, conv_list, conv_get, conv_delete, conv_rename,
    msg_add, msg_list, msg_delete, search_messages,
    user_create, user_get_by_email, user_get, user_get_by_nickname,
    user_update_password, user_update_profile, seed_admin,
    kb_add, kb_list, kb_get, kb_delete,
)
from backend.schemas import (
    ConvOut, ConvItem, ConvDetail, CreateConv, ChatReq,
    RegisterReq, LoginReq, AuthResp, ProfileReq, ForgotReq, ResetReq, ChangePasswordReq,
)
from backend.chat import stream_chat, stream_chat_with_search, stream_chat_with_thinking, stream_chat_with_search_and_thinking, stream_chat_with_rag
from fastapi.responses import JSONResponse as JsonResp

from backend.auth import (
    hash_password, verify_password, create_token, current_user,
    set_auth_cookie, clear_auth_cookie,
    create_reset_token, verify_reset_token, send_reset_email,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_admin(hash_password("admin123"))
    yield

app = FastAPI(title="MeiKen AI", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# -- auth --

@app.post("/api/auth/register")
def route_register(body: RegisterReq):
    if user_get_by_email(body.email):
        raise HTTPException(409, "Email already registered")
    u = user_create(body.email, hash_password(body.password), body.nickname)
    token = create_token(u["id"])
    resp = JsonResp({"token": token, "user": u})
    set_auth_cookie(resp, token)
    return resp

@app.post("/api/auth/login")
def route_login(body: LoginReq):
    u = user_get_by_email(body.email)
    if not u:
        u = user_get_by_nickname(body.email)
    if not u or not verify_password(body.password, u["password_hash"]):
        raise HTTPException(401, "Invalid username or password")
    token = create_token(u["id"])
    user_data = user_get(u["id"])
    resp = JsonResp({"token": token, "user": user_data})
    set_auth_cookie(resp, token)
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
    c["messages"] = msg_list(cid)
    return c

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
    if not c or c.get("user_id", 0) != uid: raise HTTPException(404, "Conversation not found")

    msgs = msg_list(cid)
    if not msgs:
        title = body.message[:80] + ("..." if len(body.message) > 80 else "")
        conv_rename(cid, title)

    msg_add(cid, "user", body.message)

    async def sse():
        collected = []
        total_tokens = 0
        try:
            if body.enable_rag:
                rag_uid = uid
                async for event in stream_chat_with_rag(body.message, msgs, body.system_prompt, rag_uid, body.rag_files):
                    if "token" in event:
                        collected.append(event["token"])
                    elif "tokens" in event:
                        total_tokens = event["tokens"]
                    yield f"data: {json.dumps(event)}\n\n"
            elif body.enable_thinking and body.enable_search:
                async for event in stream_chat_with_search_and_thinking(body.message, msgs, body.system_prompt):
                    if "token" in event:
                        collected.append(event["token"])
                    elif "tokens" in event:
                        total_tokens = event["tokens"]
                    yield f"data: {json.dumps(event)}\n\n"
            elif body.enable_thinking:
                async for event in stream_chat_with_thinking(body.message, msgs, body.system_prompt):
                    if "token" in event:
                        collected.append(event["token"])
                    elif "tokens" in event:
                        total_tokens = event["tokens"]
                    yield f"data: {json.dumps(event)}\n\n"
            elif body.enable_search:
                print(f"[SEARCH] enabled for conv {cid}, query: {body.message[:60]}...")
                async for event in stream_chat_with_search(body.message, msgs, body.system_prompt):
                    if "token" in event:
                        collected.append(event["token"])
                    elif "tokens" in event:
                        total_tokens = event["tokens"]
                    yield f"data: {json.dumps(event)}\n\n"
            else:
                async for token in stream_chat(body.message, msgs, body.system_prompt):
                    if isinstance(token, dict) and "tokens" in token:
                        total_tokens = token["tokens"]
                    else:
                        collected.append(token)
                        yield f"data: {json.dumps({'token': token})}\n\n"
            full = "".join(collected)
            saved = msg_add(cid, "assistant", full, total_tokens)
            yield f"data: {json.dumps({'done': True, 'id': saved['id'], 'tokens': total_tokens})}\n\n"
        except Exception as exc:
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(sse(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

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
    chunks = ingest_document(filepath, filename, file_id, scope=scope)
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

# -- serve frontend (production) --

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

_frontend_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
if os.path.isdir(_frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(_frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        return FileResponse(os.path.join(_frontend_dist, "index.html"))
