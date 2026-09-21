"""bridge 事件契约测试：thinking_done 结算与事件判别符不变量。

回归目标（对应 ADR-20260921 RC3）：
- 引擎迁移后前端依赖的 ``thinking_done`` 事件必须由 bridge 产出；
- 无思考的回合不得产出该事件（避免空事件污染 UI）；
- 每个事件恰好有一个判别符（status 或 type）。
"""
import asyncio

from backend.agent.bridge import _handle_message_chunk, _thinking_done_event


class FakeChunk:
    """最小化模拟 LangChain 消息 chunk。"""

    def __init__(self, content: str = "", reasoning: str = "", usage: dict | None = None):
        self.content = content
        self.additional_kwargs = {"reasoning_content": reasoning} if reasoning else {}
        self.usage_metadata = usage


def collect(agen) -> list:
    """同步收集异步生成器的全部事件。"""

    async def _run():
        return [ev async for ev in agen]

    return asyncio.run(_run())


def _chunk_events(chunk, tokens_box) -> list:
    return collect(_handle_message_chunk(chunk, {}, "main", tokens_box))


def _new_box() -> dict:
    return {"tokens": 0, "think_t0": None, "think_closed": True}


def test_thinking_then_answer_emits_thinking_done_before_token():
    """T1：reasoning → token 必须产出 thinking_done，且先于正文。"""
    box = _new_box()
    events = _chunk_events(FakeChunk(reasoning="let me think"), box)
    assert [e["type"] for e in events] == ["reasoning"]
    assert box["think_closed"] is False

    events = _chunk_events(FakeChunk(content="答案是 42"), box)
    types = [e["type"] for e in events]
    assert types == ["thinking_done", "token"], types
    done = events[0]
    assert isinstance(done["seconds"], float) and done["seconds"] >= 0


def test_no_thinking_means_no_thinking_done():
    """T7：无思考的回合不得产出 thinking_done。"""
    box = _new_box()
    events = _chunk_events(FakeChunk(content="plain answer"), box)
    assert [e["type"] for e in events] == ["token"]
    assert box.get("think_t0") is None


def test_thinking_done_is_emitted_at_most_once():
    """不变量：每个 run 只结算一次（后续思考回合不再重复产出）。"""
    box = _new_box()
    _chunk_events(FakeChunk(reasoning="a"), box)
    first = _chunk_events(FakeChunk(content="x"), box)
    second = _chunk_events(FakeChunk(reasoning="b"), box)
    third = _chunk_events(FakeChunk(content="y"), box)

    assert [e["type"] for e in first] == ["thinking_done", "token"]
    assert [e["type"] for e in second] == ["reasoning"]
    assert [e["type"] for e in third] == ["token"], "思考已结算，不得再次产出 thinking_done"


def test_late_thinking_done_helper_returns_none_when_closed():
    """T7 边界：未思考或已结算时结算函数返回 None（幂等）。"""
    box = _new_box()
    assert _thinking_done_event("main", box) is None

    box["think_t0"] = 0.0
    box["think_closed"] = False
    ev = _thinking_done_event("main", box)
    assert ev and ev["type"] == "thinking_done"
    assert _thinking_done_event("main", box) is None


def test_every_event_has_exactly_one_discriminator():
    """不变量 I1：每个事件恰好一个判别符（status 或 type）。"""
    box = _new_box()
    events = []
    events += _chunk_events(FakeChunk(reasoning="r"), box)
    events += _chunk_events(FakeChunk(content="c"), box)

    for ev in events:
        discriminators = [k for k in ("status", "type") if k in ev]
        assert len(discriminators) == 1, (ev, discriminators)


def test_turn_text_accumulates_and_resets_by_caller():
    """既有行为保持：正文累积在 turn_text，供 run_end 回传 final_text。"""
    box = _new_box()
    _chunk_events(FakeChunk(content="hello "), box)
    _chunk_events(FakeChunk(content="world"), box)
    assert box["turn_text"] == "hello world"
