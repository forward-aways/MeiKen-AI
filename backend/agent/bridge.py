"""把 deepagents/langgraph 事件流转换为 MeiKen 的 SSE 协议。

使用 ``agent.astream(stream_mode=["messages", "updates", "values"])``：
``astream_events``（v1/v2）无法暴露 human-in-the-loop 中断事件。

事件协议（扩展版）：
    {"agent":<name>,"type":"token","token":...}            实时正文
    {"agent":<name>,"type":"reasoning","reasoning":...}    思考增量
    {"agent":<name>,"type":"todo","todos":[...]}           任务清单快照
    {"agent":<name>,"type":"tool_call","id","tool","args"} 工具调用卡片
    {"agent":<name>,"type":"tool_result","id","tool","result","sources"?} 工具结果
    {"agent":<name>,"status":"sub_started","subagent","task"}  子代理开始
    {"agent":<name>,"status":"sub_done","subagent"}            子代理完成
    {"agent":<name>,"type":"approval_request","action_id","tool","args","allowed"}
    {"agent":<name>,"status":"run_end","interrupted","run_id","tokens","final_text"}
"""
import base64
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from langgraph.errors import GraphInterrupt

from backend.agent.tools import parse_kb_sources, parse_search_sources
from backend.db import approval_create

_COORDINATOR_NODE = "agent"


def _agent_from_meta(meta: dict, fallback: str) -> str:
    """从流元数据中识别事件所属代理（主代理或子代理）。"""
    return (
        meta.get("lc_agent_name")
        or meta.get("ls_agent_name")
        or meta.get("agent_name")
        or meta.get("langgraph_node")
        or fallback
    )


def _clean_args(args) -> dict:
    """清理工具参数：去掉内部字段（__ 前缀）。"""
    if not isinstance(args, dict):
        return {"input": str(args)}
    return {k: v for k, v in args.items() if not k.startswith("__")}


class RunStatus:
    """可变状态容器：让路由层知道本次运行是否因审批而中断。"""

    def __init__(self):
        self.interrupted = False
        self.pending_actions = []


class RunCtx:
    """单次运行的上下文：tool_call_id → 工具名 / 子代理名。"""

    def __init__(self):
        self.tool_names: dict[str, str] = {}
        self.task_names: dict[str, str] = {}


async def _handle_message_chunk(chunk, meta: dict, agent_name: str, tokens_box: dict):
    """处理流式消息增量：正文 / 思考 / 用量。"""
    agent = _agent_from_meta(meta, agent_name)
    content = chunk.content if hasattr(chunk, "content") else ""
    if content:
        # 累积当前回合文本；工具回合会将其重置，
        # 因此到 run_end 时保留下来的只有最终回答。
        tokens_box["turn_text"] = tokens_box.get("turn_text", "") + content
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
    """处理模型节点更新：发出工具调用卡片 / 子代理开始事件。"""
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
            yield {"type": "tool_call", "id": tc_id, "tool": name, "args": tc.get("args", {})}


def _handle_tools_update(update: dict, ctx: RunCtx):
    """处理工具节点更新：发出工具结果（含结构化来源）或子代理完成事件。"""
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
        out_text = str(output or "")
        ev = {"type": "tool_result", "id": tc_id, "tool": name, "result": out_text}
        # 附带结构化来源，让前端渲染专用来源卡片，而不是倾倒原始文本
        if name == "web_search":
            src = parse_search_sources(out_text)
            if src:
                ev["sources"] = src
        elif name == "knowledge_search":
            files = parse_kb_sources(out_text)
            if files:
                ev["sources"] = [{"title": f} for f in files]
        yield ev


def _handle_interrupt(update, run_id: int, status: RunStatus, agent_name: str):
    """处理人工审批中断：落库并发出审批请求事件。"""
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
                            # 本回合模型决定使用工具：此前输出的文本属于过程辞令，
                            # 从最终回答中剔除。
                            if out.get("type") == "tool_call" or out.get("status") == "sub_started":
                                tokens_box["turn_text"] = ""
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
           "run_id": run_id, "tokens": tokens_box["tokens"],
           "final_text": tokens_box.get("turn_text", "")}


def build_human_content(text: str, images: list[dict] | None = None):
    """构建 HumanMessage 内容。

    无图片时返回纯文本；有图片时返回 OpenAI 风格的内容块，
    每张图片以内联 ``data:<mime>;base64,...`` URL 形式提供
    （DeepSeek V4.1 Flash / OpenAI 兼容多模态端点原生支持）。
    无法读取的图片会被静默跳过。
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
    # 一张图都没能附上时回退为纯文本，确保非多模态模型不会收到内容块
    return blocks if added else text


async def stream_agent_run(agent, user_message: str, thread_id: str, run_id: int, agent_name: str,
                           images: list[dict] | None = None):
    """开始（或继续）一轮运行并流式输出 SSE 事件。

    ``images`` 是挂载在用户消息上的图片记录（filepath/mime），
    会以内联 base64 data URL 形式提供给多模态模型。
    """
    status = RunStatus()
    tokens_box = {"tokens": 0}
    inp = {"messages": [HumanMessage(content=build_human_content(user_message, images))]}
    async for out in _stream(agent, inp, thread_id, run_id, agent_name, status, tokens_box):
        yield out


async def stream_agent_resume(agent, decisions: list[dict], thread_id: str, run_id: int, agent_name: str):
    """用 Command(resume=...) 恢复因审批暂停的运行并流式输出事件。"""
    status = RunStatus()
    tokens_box = {"tokens": 0}
    cmd = Command(resume={"decisions": decisions})
    async for out in _stream(agent, cmd, thread_id, run_id, agent_name, status, tokens_box):
        yield out
