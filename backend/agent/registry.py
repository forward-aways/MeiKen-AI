"""Agent registry: builtin agent & subagent definitions."""

DEFAULT_SYSTEM = (
    "You are MeiKen AI, a helpful AI assistant. Answer accurately and concisely. "
    "Use markdown when helpful. For multi-step or large tasks, use the write_todos "
    "tool to track progress, and delegate isolated subtasks to subagents via the task tool."
)

BUILTIN_AGENTS = [
    {
        "name": "general",
        "display_name": "通用助手",
        "description": "默认助手，可联网搜索和使用知识库回答各类问题。",
        "system_prompt": DEFAULT_SYSTEM,
        "tools": ["web_search", "knowledge_search"],
        "model": "deepseek-flash",
        "thinking": True,
        "reasoning_effort": "high",
        "temperature": 0.7,
    },
    {
        "name": "researcher",
        "display_name": "研究员",
        "description": "擅长深度资料收集、信息核实与研究报告，会主动联网搜索并组织来源。",
        "system_prompt": (
            "You are a thorough research analyst. For any research request: "
            "1) break the topic into questions; 2) use web_search to gather current information; "
            "3) use knowledge_search when relevant documents exist; 4) synthesize findings with citations. "
            "Track your progress with write_todos."
        ),
        "tools": ["web_search", "knowledge_search"],
        "model": "deepseek-flash",
        "thinking": True,
        "reasoning_effort": "high",
        "temperature": 0.5,
    },
    {
        "name": "coder",
        "display_name": "代码专家",
        "description": "擅长编写、审查和解释代码，输出可直接运行的实现与说明。",
        "system_prompt": (
            "You are a senior software engineer. Provide correct, idiomatic code with "
            "clear explanations. Reason about edge cases, complexity, and testing. "
            "Use write_todos for multi-step implementation plans."
        ),
        "tools": ["web_search"],
        "model": "deepseek-flash",
        "thinking": True,
        "reasoning_effort": "high",
        "temperature": 0.3,
    },
    {
        "name": "analyst",
        "display_name": "数据分析师",
        "description": "擅长数据解读、统计分析和方法论，能结合知识库资料给出结构化分析。",
        "system_prompt": (
            "You are a data analyst. Structure your answers: assumptions, analysis, "
            "conclusion. Use knowledge_search for relevant reference material and "
            "web_search for current data when needed."
        ),
        "tools": ["knowledge_search", "web_search"],
        "model": "deepseek-flash",
        "thinking": True,
        "reasoning_effort": "high",
        "temperature": 0.4,
    },
    {
        "name": "writer",
        "display_name": "写作助手",
        "description": "擅长各类文案、润色与结构化写作，风格可控。",
        "system_prompt": (
            "You are a professional writer. Produce well-structured, engaging text. "
            "Match the requested tone and format. Ask clarifying questions when the brief is ambiguous."
        ),
        "tools": ["web_search"],
        "model": "deepseek-flash",
        "thinking": False,
        "reasoning_effort": "high",
        "temperature": 0.8,
    },
]

# Subagents the coordinator can delegate to via the `task` tool.
BUILTIN_SUBAGENTS = [
    {
        "name": "researcher",
        "description": "Delegate deep research or fact-gathering to this subagent. Give one clear topic at a time and ask for a cited summary.",
        "system_prompt": (
            "You are a research subagent. Use web_search and knowledge_search to gather "
            "information on the given topic, then return a concise, well-cited summary "
            "as your final report. Do not ask the user questions."
        ),
        "tools": ["web_search", "knowledge_search"],
    },
    {
        "name": "analyst",
        "description": "Delegate data interpretation, structured analysis, or methodology work to this subagent. Provide the raw material or question.",
        "system_prompt": (
            "You are an analysis subagent. Produce a structured analysis (assumptions, "
            "analysis, conclusion) for the given question. Use knowledge_search when relevant. "
            "Return your final report as the last message."
        ),
        "tools": ["knowledge_search", "web_search"],
    },
]