"""按代理配置构建 deepagents 实例。"""
import json

from langchain.agents.middleware import TodoListMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from deepagents import create_deep_agent
from deepagents.middleware import FilesystemMiddleware
from deepagents.backends import CompositeBackend, FilesystemBackend, StoreBackend

from backend.agent.llm import build_llm, resolve_provider
from backend.agent.identity import compose_system_prompt, SUBAGENT_IDENTITY
from backend.agent.registry import BUILTIN_SUBAGENTS
from backend.agent.tools import resolve_tools
from backend.log import get_logger
from backend.workspace import ensure_workspace, workspace_dir

log = get_logger("backend.factory")

# 技能存放在 langgraph store 的用户命名空间下。主代理与通用子代理通过
# 虚拟文件系统 /skills/ 读取（deepagents 官方的渐进式加载机制）。
_FS_TOOLS = ["read_file", "write_file", "edit_file", "delete", "ls", "glob", "grep"]

# 文件写入类操作需要人工审批（批准 / 修改 / 拒绝）
INTERRUPT_ON = {
    "write_file": {"allowed_decisions": ["approve", "edit", "reject"]},
    "edit_file": {"allowed_decisions": ["approve", "edit", "reject"]},
    "delete": {"allowed_decisions": ["approve", "reject"]},
}


def _build_subagents():
    subs = []
    for s in BUILTIN_SUBAGENTS:
        subs.append({
            "name": s["name"],
            "description": s["description"],
            "system_prompt": SUBAGENT_IDENTITY + "\n\n" + s["system_prompt"],
            "tools": resolve_tools(s.get("tools", [])),
        })
    return subs


def _fs_middleware(user_id: int) -> FilesystemMiddleware:
    """按用户隔离的文件系统中间件。

    - 默认根目录：用户工作区（真实磁盘落盘，virtual_mode 限制在目录内）
      → AI 生成的文件可被用户预览 / 下载 / 编辑；
      - /skills/ 路由到该用户的 langgraph store 命名空间。
    """
    ensure_workspace(user_id)
    backend = CompositeBackend(
        default=FilesystemBackend(root_dir=workspace_dir(user_id), virtual_mode=True),
        routes={
            "/skills/": StoreBackend(namespace=lambda rt: ("skills", str(user_id))),
        },
    )
    return FilesystemMiddleware(backend=backend, tools=_FS_TOOLS)


class AgentFactory:
    """按 (代理, 用户, 覆盖参数) 构建并缓存编译后的 deep agent。"""

    def __init__(self, checkpointer: AsyncSqliteSaver, store=None):
        self._checkpointer = checkpointer
        self._store = store
        self._cache: dict[tuple, object] = {}

    def build(self, agent_cfg: dict, user_id: int, overrides: dict | None = None, mode: str = "general"):
        overrides = overrides or {}
        model = overrides.get("model") or agent_cfg.get("model", "deepseek-flash")
        thinking = (
            bool(overrides["thinking"])
            if overrides.get("thinking") is not None
            else bool(agent_cfg.get("thinking", True))
        )
        effort = overrides.get("reasoning_effort") or agent_cfg.get("reasoning_effort", "high")
        temperature = float(agent_cfg.get("temperature", 0.7))

        provider = resolve_provider(user_id, model)
        provider_id = provider["id"] if provider else None
        key = (agent_cfg["id"], user_id, model, thinking, effort, mode, provider_id)
        if key in self._cache:
            log.debug("代理缓存命中 | agent=%s user=%s model=%s", agent_cfg.get("name"), user_id, model)
            return self._cache[key]

        raw_tools = agent_cfg.get("tools") or []
        if isinstance(raw_tools, str):
            try:
                raw_tools = json.loads(raw_tools) or []
            except (ValueError, TypeError):
                raw_tools = []
        tools = resolve_tools(raw_tools)

        llm = build_llm(
            provider,
            model=model,
            thinking=thinking,
            reasoning_effort=effort,
            temperature=temperature,
        )

        agent = create_deep_agent(
            model=llm,
            tools=tools,
            system_prompt=compose_system_prompt(agent_cfg, mode),
            middleware=[TodoListMiddleware(), _fs_middleware(user_id)],
            subagents=_build_subagents(),
            interrupt_on=INTERRUPT_ON,
            checkpointer=self._checkpointer,
            store=self._store,
            skills=["/skills/"],
            name=agent_cfg.get("name", "general"),
        )
        self._cache[key] = agent
        log.debug("构建代理 | agent=%s user=%s model=%s provider=%s mode=%s",
                  agent_cfg.get("name"), user_id, model, provider_id, mode)
        return agent

    def invalidate(self, agent_id: int, user_id: int) -> None:
        """使某代理的缓存失效（配置更新后调用）。"""
        self._cache = {
            k: v for k, v in self._cache.items()
            if not (k[0] == agent_id and k[1] == user_id)
        }

    def invalidate_user(self, user_id: int) -> None:
        """使某用户的全部代理缓存失效（供应商/技能变更后调用）。"""
        self._cache = {k: v for k, v in self._cache.items() if k[1] != user_id}

    def invalidate_provider(self, user_id: int) -> None:
        """供应商变更：丢弃该用户的所有代理缓存。"""
        self.invalidate_user(user_id)


def thread_id_for(conv_id: int) -> str:
    return f"conv-{conv_id}"


def resolve_interrupt_value(data: dict) -> dict | None:
    """从中断值中提取 {action_requests, review_configs}。"""
    if isinstance(data, dict):
        if "action_requests" in data:
            return data
        if "interrupts" in data and data["interrupts"]:
            v = data["interrupts"][0]
            if isinstance(v, dict) and "value" in v:
                val = v["value"]
                return val if isinstance(val, dict) else None
    return None


def serialize_interrupt_value(value: dict) -> list[dict]:
    """构造审批行：[{action_id, tool, args}]。"""
    actions = value.get("action_requests") or []
    reviews = {c.get("action_name"): c for c in value.get("review_configs") or []}
    out = []
    for a in actions:
        out.append({
            "action_id": a.get("id", a.get("tool_call_id") or ""),
            "tool": a.get("name", a.get("tool", "")),
            "args": a.get("args", {}) or {},
            "allowed": (reviews.get(a.get("name"), {}) or {}).get("allowed_decisions", ["approve", "reject"]),
        })
    return out


def build_decisions(decisions: list[dict]) -> list[dict]:
    """把 SSE 决策对象转换为 langgraph Command(resume) 所需的决策列表。"""
    out = []
    for d in decisions:
        if d["decision"] == "approve":
            out.append({"type": "approve"})
        elif d["decision"] == "reject":
            out.append({"type": "reject", "message": d.get("message") or "用户拒绝了这个操作。"})
        elif d["decision"] == "edit":
            out.append({
                "type": "edit",
                "edited_action": {"name": d.get("tool", ""), "args": d.get("edited_args", {})},
            })
    return out
