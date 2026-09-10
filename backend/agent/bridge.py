"""Translate the deepagents/langgraph stream into the MeiKen SSE protocol.

Uses ``agent.astream(stream_mode=["messages", "updates", "values"])`` because
``astream_events`` (v1/v2) does not surface human-in-the-loop interrupts.

Event protocol (extended):
    {"agent":<name>,"type":"token","token":...}            live content
    {"agent":<name>,"type":"reasoning","reasoning":...}     thinking delta
    {"agent":<name>,"type":"todo","todos":[...]}            task list snapshot
    {"agent":<name>,"type":"tool_call","tool","args"}       tool call card
    {"agent":<name>,"type":"tool_result","tool","result"}   tool result
    {"agent":<name>,"status":"sub_started","subagent","task"}
    {"agent":<name>,"status":"sub_done","subagent"}
    {"agent":<name>,"type":"approval_request","action_id","tool","args","allowed"}
    {"agent":<name>,"status":"run_end","interrupted","run_id","tokens"}
"""
import base64
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from langgraph.errors import GraphInterrupt

from backend.database import approval_create

_COORDINATOR_NODE = "agent"


def _agent_from_meta(meta: dict, fallback: str) -> str:
    return (
        meta.get("lc_agent_name")
        or meta.get("ls_agent_name")
        or meta.get("agent_name")
        or meta.get("langgraph_node")
        or fallback
    )


def _clean_args(args) -> dict:
    if not isinstance(args, dict):
        return {"input": str(args)}
    return {k: v for k, v in args.items() if not k.startswith("__")}


class RunStatus:
    """Mutable holder so the route knows whether the run paused for approval."""

    def __init__(self):
        self.interrupted = False
        self.pending_actions = []


class RunCtx:
    """Per-run mutable context (tool_call_id -> tool name / subagent name)."""

    def __init__(self):
        self.tool_names: dict[str, str] = {}
        self.task_names: dict[str, str] = {}


async def _handle_message_chunk(chunk, meta: dict, agent_name: str, tokens_box: dict):
    agent = _agent_from_meta(meta, agent_name)
    content = chunk.content if hasattr(chunk, "content") else ""
    if content:
        yield {"agent": agent, "type": "token", "token": content}
    rc = ""
    try:
        rc = chunk.additional_kwargs.get("reasoning_content", "") or ""
    except Exception:
        rc = ""
    if rc:
        yield {"agent": agent, "type": "reasoning", "reasoning": rc}
    um = getattr(chunk, "usage_metadata", None)
    if um:
        tokens_box["tokens"] = um.get("total_tokens", 0)


def _handle_model_update(update: dict, ctx: RunCtx):
    msgs = update.get("messages") or []
    last = msgs[-1] if msgs else None
    if last is None or not getattr(last, "tool_calls", None):
        return
    for tc in last.tool_calls:
        tc_id = tc.get("id", "")
        name = tc.get("name", "")
        ctx.tool_names[tc_id] = name
        if name == "write_todos":
            continue
        if name == "task":
            args = tc.get("args", {})
            subagent = str(args.get("subagent_type") or args.get("name") or "")
            ctx.task_names[tc_id] = subagent
            yield {"status": "sub_started",
                   "subagent": subagent,
                   "task": str(args.get("task") or "")}
        else:
            yield {"type": "tool_call", "tool": name, "args": tc.get("args", {})}


def _handle_tools_update(update: dict, ctx: RunCtx):
    msgs = update.get("messages") or []
    for m in msgs:
        if getattr(m, "type", "") != "tool":
            continue
        tc_id = getattr(m, "tool_call_id", "") or ""
        name = ctx.tool_names.get(tc_id, "")
        if name == "write_todos":
            continue
        if name == "task":
            yield {"status": "sub_done", "subagent": ctx.task_names.get(tc_id, "")}
            continue
        if not name:
            continue
        output = m.content
        if isinstance(output, bytes):
            output = output.decode("utf-8", "ignore")
        yield {"type": "tool_result", "tool": name, "result": str(output or "")}


def _handle_interrupt(update, run_id: int, status: RunStatus, agent_name: str):
    status.interrupted = True
    for intr in update:
        value = intr.value if hasattr(intr, "value") else (intr.get("value") if isinstance(intr, dict) else None)
        if not isinstance(value, dict):
            continue
        actions = value.get("action_requests") or []
        reviews = {c.get("action_name"): c for c in value.get("review_configs") or []}
        for a in actions:
            action_id = a.get("id") or a.get("tool_call_id") or f"act-{a.get('index', 0)}"
            tool = a.get("name") or a.get("tool", "")
            args = a.get("args", {}) or {}
            allowed = (reviews.get(tool) or {}).get("allowed_decisions", ["approve", "reject"])
            approval_create(run_id, str(action_id), tool, args)
            status.pending_actions.append({"action_id": str(action_id), "tool": tool})
            yield {"agent": agent_name, "type": "approval_request",
                   "action_id": str(action_id), "tool": tool, "args": args,
                   "allowed": allowed}


async def _stream(
    agent,
    graph_input,
    thread_id: str,
    run_id: int,
    agent_name: str,
    status: RunStatus,
    tokens_box: dict,
):
    ctx = RunCtx()
    config = {"configurable": {"thread_id": thread_id}}
    try:
        async for mode, value in agent.astream(
            graph_input,
            config=config,
            stream_mode=["messages", "updates", "values"],
        ):
            if mode == "messages":
                chunk, meta = value
                async for out in _handle_message_chunk(chunk, meta, agent_name, tokens_box):
                    yield out
            elif mode == "updates":
                for node, update in value.items():
                    if node == "__interrupt__":
                        for out in _handle_interrupt(update, run_id, status, agent_name):
                            yield out
                    elif node == "model":
                        for out in _handle_model_update(update, ctx):
                            yield out
                    elif node == "tools":
                        for out in _handle_tools_update(update, ctx):
                            yield out
            elif mode == "values":
                todos = value.get("todos") if isinstance(value, dict) else None
                if todos:
                    yield {"agent": agent_name, "type": "todo", "todos": todos}
            if status.interrupted:
                break
    except GraphInterrupt:
        status.interrupted = True
    yield {"agent": agent_name, "status": "run_end", "interrupted": status.interrupted,
           "run_id": run_id, "tokens": tokens_box["tokens"]}


def build_human_content(text: str, images: list[dict] | None = None):
    """Build HumanMessage content for the model.

    Plain text when no images; otherwise OpenAI-style content blocks with each
    image inlined as a ``data:<mime>;base64,...`` URL (supported natively by
    DeepSeek V4.1 Flash / OpenAI-compatible multimodal endpoints). Unreadable
    image files are silently skipped.
    """
    if not images:
        return text
    blocks: list[dict] = []
    if text:
        blocks.append({"type": "text", "text": text})
    added = 0
    for img in images:
        try:
            with open(img["filepath"], "rb") as f:
                data = f.read()
        except (OSError, KeyError, TypeError):
            continue
        b64 = base64.b64encode(data).decode()
        blocks.append({
            "type": "image_url",
            "image_url": {"url": f"data:{img.get('mime', 'image/png')};base64,{b64}"},
        })
        added += 1
    # Fall back to plain text when no image could actually be attached, so
    # non-multimodal models never receive content blocks.
    return blocks if added else text


async def stream_agent_run(agent, user_message: str, thread_id: str, run_id: int, agent_name: str,
                           images: list[dict] | None = None):
    """Start (or continue) a run turn and stream SSE events.

    ``images`` are DB records (filepath/mime) attached to the user message;
    they are inlined as base64 data URLs for the multimodal model.
    """
    status = RunStatus()
    tokens_box = {"tokens": 0}
    inp = {"messages": [HumanMessage(content=build_human_content(user_message, images))]}
    async for out in _stream(agent, inp, thread_id, run_id, agent_name, status, tokens_box):
        yield out


async def stream_agent_resume(agent, decisions: list[dict], thread_id: str, run_id: int, agent_name: str):
    """Resume a run paused for approval with Command(resume=...) and stream events."""
    status = RunStatus()
    tokens_box = {"tokens": 0}
    cmd = Command(resume={"decisions": decisions})
    async for out in _stream(agent, cmd, thread_id, run_id, agent_name, status, tokens_box):
        yield out