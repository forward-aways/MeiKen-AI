"""代理可用的工具集。

说明：``@tool`` 装饰函数的 docstring 是给模型看的工具描述，
保持英文以获得稳定的模型表现；代码注释为中文。
"""
import os
import re

import httpx
from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv()

BOCHA_KEY = os.getenv("BOCHA_API_KEY", "")


@tool
def web_search(query: str) -> str:
    """Search the web for current and real-time information. Use this tool when you need up-to-date facts, news, or anything beyond your knowledge cutoff. Returns formatted results with titles, snippets and source URLs."""
    return _search_formatted(query)


@tool
def knowledge_search(query: str) -> str:
    """Search the user's private knowledge base for relevant document excerpts. Use this tool when the question relates to uploaded documents or the user's knowledge base. Returns matching chunks with source filenames."""
    try:
        from backend.rag import search_relevant
        results = search_relevant(query, scope="kb", k=4)
        if not results:
            return "知识库中没有找到相关内容。"
        parts = []
        for i, r in enumerate(results):
            parts.append(f"[Source {i + 1}: {r['filename']}]\n{r['content']}")
        return "\n\n---\n\n".join(parts)
    except Exception as e:
        return f"知识库检索失败: {e}"


def _clip(s, n=180):
    """压缩摘要文本：单行化并硬截断，控制工具输出体积。"""
    s = (s or "").strip().replace("\n", " ")
    return s[:n] + ("…" if len(s) > n else "")


def _search_raw(query: str):
    if not BOCHA_KEY:
        return {"pages": [], "error": "Search API is not configured."}
    try:
        r = httpx.post(
            "https://api.bochaai.com/v1/web-search",
            headers={"Authorization": f"Bearer {BOCHA_KEY}", "Content-Type": "application/json"},
            json={"query": query, "count": 5},
            timeout=10.0,
        )
        r.raise_for_status()
        data = r.json()
        pages = data.get("data", {}).get("webPages", {}).get("value", [])
        return {"pages": [
            {"title": _clip(p.get("name", ""), 120), "snippet": _clip(p.get("snippet")), "url": p.get("url", "") or p.get("displayUrl", "")}
            for p in pages
        ]}
    except Exception as e:
        return {"pages": [], "error": str(e)}


def _search_formatted(query: str) -> str:
    raw = _search_raw(query)
    if raw.get("error"):
        return f"Search request failed: {raw['error']}"
    pages = raw["pages"]
    if not pages:
        return f"No search results found for query: {query}"
    return _fmt_pages(pages)


def _fmt_pages(pages):
    if not pages:
        return "No results."
    parts = []
    for p in pages:
        parts.append(f"### {p['title']}\n{p['snippet']}\nSource: {p['url']}")
    return "\n\n---\n\n".join(parts)


def parse_search_sources(text: str) -> list[dict]:
    """从 web_search 的格式化输出中解析 {title, snippet, url} 列表。"""
    out = []
    for block in (text or "").split("\n\n---\n\n"):
        lines = block.strip().split("\n")
        if len(lines) >= 3 and lines[0].startswith("### ") and lines[-1].startswith("Source: "):
            out.append({
                "title": lines[0][4:].strip(),
                "snippet": "\n".join(lines[1:-1]).strip(),
                "url": lines[-1][8:].strip(),
            })
    return out


def parse_kb_sources(text: str) -> list[str]:
    """从 knowledge_search 输出中解析来源文件名（去重）。"""
    seen, out = set(), []
    for m in re.finditer(r"\[Source \d+: (.+?)\]", text or ""):
        name = m.group(1).strip()
        if name and name not in seen:
            seen.add(name)
            out.append(name)
    return out


TOOL_REGISTRY = {
    "web_search": web_search,
    "knowledge_search": knowledge_search,
}


def resolve_tools(names: list[str]):
    out = []
    for n in names or []:
        t = TOOL_REGISTRY.get(n)
        if t:
            out.append(t)
    return out