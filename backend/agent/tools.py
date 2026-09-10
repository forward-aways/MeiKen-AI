"""Tools exposed to agents in the harness."""
import os

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
            {"title": p.get("name", ""), "snippet": p.get("snippet", "") or "", "url": p.get("url", "") or p.get("displayUrl", "")}
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