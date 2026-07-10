import os
import time
import json

import httpx
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

load_dotenv()

DEFAULT_SYSTEM = "You are MeiKen AI, a helpful assistant. Answer accurately and concisely. Use markdown when helpful."

SEARCH_SYSTEM_SUFFIX = (
    "\n\nYou have access to a web_search tool. "
    "Use it to find current information when the user's question requires real-time data, "
    "recent news, or facts beyond your knowledge cutoff. "
    "Always cite sources with markdown links when using search results."
)

BOCHA_KEY = os.getenv("BOCHA_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")


@tool
def web_search(query: str) -> str:
    """Search the web for current and real-time information. Use this tool when you need up-to-date facts, news, or anything beyond your knowledge cutoff."""
    return _search_formatted(query)


def _search_raw(query: str):
    if not BOCHA_KEY:
        return {"pages": [], "error": "Search API is not configured."}
    try:
        r = httpx.post(
            "https://api.bochaai.com/v1/web-search",
            headers={
                "Authorization": f"Bearer {BOCHA_KEY}",
                "Content-Type": "application/json",
            },
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


def _llm():
    return ChatOpenAI(
        model="deepseek-chat",
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=0.7,
        max_tokens=4096,
        streaming=True,
    )


def _llm_with_tools():
    return ChatOpenAI(
        model="deepseek-chat",
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=0.7,
        max_tokens=4096,
    ).bind_tools([web_search])


def _to_lc(msgs):
    out = []
    for m in msgs:
        if m["role"] == "user":
            out.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            out.append(AIMessage(content=m["content"]))
    return out


async def stream_chat(text, history, system_prompt=""):
    sys_msg = system_prompt.strip() if system_prompt.strip() else DEFAULT_SYSTEM
    prompt = ChatPromptTemplate.from_messages([
        ("system", sys_msg),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ])
    chain = prompt | _llm()
    async for chunk in chain.astream({"history": _to_lc(history), "input": text}):
        if hasattr(chunk, "content") and chunk.content:
            yield chunk.content


async def stream_chat_with_search(text, history, system_prompt=""):
    sys_msg = (system_prompt.strip() if system_prompt.strip() else DEFAULT_SYSTEM) + SEARCH_SYSTEM_SUFFIX
    messages = [SystemMessage(content=sys_msg)] + _to_lc(history) + [HumanMessage(content=text)]

    response = await _llm_with_tools().ainvoke(messages)

    if response.tool_calls:
        messages.append(response)
        for tc in response.tool_calls:
            name = tc.get("name", "")
            args = tc.get("args", {})
            query = args.get("query", "")
            if name == "web_search":
                yield {"status": "searching", "query": query}
                raw = _search_raw(query)
                result_text = _fmt_pages(raw["pages"]) if not raw.get("error") else f"Search failed: {raw['error']}"
                messages.append(ToolMessage(content=result_text, tool_call_id=tc["id"]))
                yield {"status": "searched", "query": query, "results": raw["pages"]}

        async for chunk in _llm().astream(messages):
            if hasattr(chunk, "content") and chunk.content:
                yield {"token": chunk.content}
    else:
        if response.content:
            yield {"token": response.content}


async def _stream_thinking(messages, tools=None):
    """Stream DeepSeek thinking mode via raw httpx SSE. Yields (reasoning, content) tuples."""
    body = {
        "model": "deepseek-chat",
        "messages": messages,
        "stream": True,
        "reasoning_effort": "high",
        "thinking": {"type": "enabled"},
    }
    if tools:
        body["tools"] = tools

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            DEEPSEEK_BASE_URL + "/chat/completions",
            headers=headers,
            json=body,
            timeout=120.0,
        ) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = chunk.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                reasoning = delta.get("reasoning_content", "")
                content = delta.get("content", "")
                tool_calls = delta.get("tool_calls")
                if reasoning:
                    yield ("reasoning", reasoning)
                if content:
                    yield ("content", content)
                if tool_calls:
                    yield ("tool_calls", tool_calls)


def _build_api_messages(text, history, system_prompt):
    sys_msg = system_prompt.strip() if system_prompt.strip() else DEFAULT_SYSTEM
    messages = [{"role": "system", "content": sys_msg}]
    for m in history:
        if m["role"] in ("user", "assistant"):
            messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": text})
    return messages


async def stream_chat_with_thinking(text, history, system_prompt=""):
    thinking_start = time.time()
    messages = _build_api_messages(text, history, system_prompt)

    async for kind, data in _stream_thinking(messages):
        if kind == "reasoning":
            yield {"reasoning": data}
        elif kind == "content":
            yield {"token": data}

    thinking_time = round(time.time() - thinking_start, 1)
    yield {"thinking_done": thinking_time}


async def stream_chat_with_search_and_thinking(text, history, system_prompt=""):
    sys_msg = (system_prompt.strip() if system_prompt.strip() else DEFAULT_SYSTEM) + SEARCH_SYSTEM_SUFFIX
    messages = _build_api_messages(text, history, sys_msg)

    tools = [{
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current and real-time information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"}
                },
                "required": ["query"]
            }
        }
    }]

    thinking_start = time.time()

    collected_reasoning = ""
    collected_content = ""
    tool_calls = None

    async for kind, data in _stream_thinking(messages, tools=tools):
        if kind == "reasoning":
            collected_reasoning += data
            yield {"reasoning": data}
        elif kind == "content":
            collected_content += data
            yield {"token": data}
        elif kind == "tool_calls":
            tool_calls = data

    if tool_calls:
        assistant_msg = {
            "role": "assistant",
            "content": collected_content,
            "reasoning_content": collected_reasoning,
            "tool_calls": _normalize_tool_calls(tool_calls),
        }
        messages.append(assistant_msg)

        for tc in assistant_msg["tool_calls"]:
            if tc["function"]["name"] == "web_search":
                args = json.loads(tc["function"]["arguments"])
                query = args.get("query", "")
                yield {"status": "searching", "query": query}
                raw = _search_raw(query)
                result_text = _fmt_pages(raw["pages"]) if not raw.get("error") else f"Search failed: {raw['error']}"
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result_text,
                })
                yield {"status": "searched", "query": query, "results": raw["pages"]}

        collected_reasoning2 = ""
        async for kind, data in _stream_thinking(messages, tools=tools):
            if kind == "reasoning":
                collected_reasoning2 += data
                yield {"reasoning": data}
            elif kind == "content":
                yield {"token": data}

    thinking_time = round(time.time() - thinking_start, 1)
    yield {"thinking_done": thinking_time}


def _normalize_tool_calls(raw_tool_calls):
    result = []
    for tc in raw_tool_calls:
        idx = tc.get("index", 0)
        fn = tc.get("function", {})
        result.append({
            "id": tc.get("id", f"call_{idx}"),
            "type": "function",
            "function": {
                "name": fn.get("name", ""),
                "arguments": fn.get("arguments", "{}"),
            }
        })
    return result
