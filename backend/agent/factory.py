"""Build deepagents harness instances from agent configs."""
import json

from langchain.agents.middleware import TodoListMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from deepagents import create_deep_agent
from deepagents.middleware import FilesystemMiddleware
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

from backend.agent.llm import build_llm, resolve_provider
from backend.agent.identity import compose_system_prompt, SUBAGENT_IDENTITY
from backend.agent.registry import BUILTIN_SUBAGENTS
from backend.agent.tools import resolve_tools
from backend.log import get_logger

log = get_logger("backend.factory")

# Skills live in the langgraph store under the user's namespace. The main agent
# and the general-purpose subagent read them through the virtual filesystem at
# /skills/ (official deepagents progressive-disclosure loading).
_FS_TOOLS = ["read_file", "write_file", "edit_file", "delete", "ls", "glob", "grep"]

# Filesystem writes require human approval (approve / edit / reject).
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
    """Per-user filesystem middleware routing /skills/ to the user's store namespace."""
    backend = CompositeBackend(
        default=StateBackend(),
        routes={
            "/skills/": StoreBackend(namespace=lambda rt: ("skills", str(user_id))),
        },
    )
    return FilesystemMiddleware(backend=backend, tools=_FS_TOOLS)


class AgentFactory:
    """Builds and caches compiled deep agents per (agent_id, user_id, overrides)."""

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
            log.debug("agent cache hit | agent=%s user=%s model=%s", agent_cfg.get("name"), user_id, model)
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
        log.debug("agent built | agent=%s user=%s model=%s provider=%s mode=%s",
                  agent_cfg.get("name"), user_id, model, provider_id, mode)
        return agent

    def invalidate(self, agent_id: int, user_id: int) -> None:
        self._cache = {
            k: v for k, v in self._cache.items()
            if not (k[0] == agent_id and k[1] == user_id)
        }

    def invalidate_user(self, user_id: int) -> None:
        self._cache = {k: v for k, v in self._cache.items() if k[1] != user_id}

    def invalidate_provider(self, user_id: int) -> None:
        """Provider CRUD changed — drop every cached agent of this user."""
        self.invalidate_user(user_id)


def thread_id_for(conv_id: int) -> str:
    return f"conv-{conv_id}"


def resolve_interrupt_value(data: dict) -> dict | None:
    """Extract {action_requests, review_configs} from an interrupt value."""
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
    """Build approval rows: [{action_id, tool, args}]."""
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
    """Convert our SSE decision objects into langgraph Command(resume) decisions."""
    out = []
    for d in decisions:
        if d["decision"] == "approve":
            out.append({"type": "approve"})
        elif d["decision"] == "reject":
            out.append({"type": "reject", "message": d.get("message") or "User rejected this action."})
        elif d["decision"] == "edit":
            out.append({
                "type": "edit",
                "edited_action": {"name": d.get("tool", ""), "args": d.get("edited_args", {})},
            })
    return out