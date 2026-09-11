"""聊天流服务：把代理事件流转换为 SSE 并最终落库。

设计：
- ``/api/chat`` 与 ``/api/approvals`` 两个入口共用同一套编排（此前的重复实现已合并）；
- 并发信号量、异常兜底、运行状态更新、最终文本落库均在此处理；
- 事件协议对前端保持不变（逐字段兼容）。
"""
import json
import time
from typing import AsyncIterator, Callable

from backend import runtime
from backend.db import msg_add, run_update_status
from backend.log import get_logger

log = get_logger("backend.services.chat_stream")


async def _sse_core(events: AsyncIterator[dict], conv_id: int, run_id: int) -> AsyncIterator[str]:
    """把代理事件迭代器转成 SSE 文本，并把最终答案落库。

    ``final_text`` 只包含最后一个回合的文本（工具回合的过程辞令在
    bridge 层已被丢弃），因此入库的正文是干净的最终回答。
    """
    total_tokens = 0
    final_text = ""
    interrupted = False
    async for event in events:
        yield f"data: {json.dumps(event)}\n\n"
        if event.get("status") == "run_end":
            interrupted = bool(event.get("interrupted"))
            total_tokens = event.get("tokens", 0)
            final_text = event.get("final_text", "")
            run_update_status(run_id, "waiting_approval" if interrupted else "completed")
    if not interrupted and final_text:
        saved = msg_add(conv_id, "assistant", final_text, total_tokens)
        yield f"data: {json.dumps({'done': True, 'id': saved['id'], 'tokens': total_tokens})}\n\n"


def sse_response_stream(
    events_factory: Callable[[], AsyncIterator[dict]],
    conv_id: int,
    run_id: int,
    log_ctx: str,
) -> AsyncIterator[str]:
    """带并发闸门与异常兜底的 SSE 流。

    ``events_factory`` 返回异步事件迭代器（延迟创建，避免信号量未拿到时就发起调用）。
    """
    async def gen() -> AsyncIterator[str]:
        if not runtime.semaphore.acquire(blocking=False):
            log.warning("并发已达上限，拒绝请求 | %s", log_ctx)
            yield f"data: {json.dumps({'error': '并发任务数已达上限，请稍后重试'})}\n\n"
            return
        t0 = time.perf_counter()
        try:
            async for chunk in _sse_core(events_factory(), conv_id, run_id):
                yield chunk
            log.info("运行结束 | %s | %.1fs", log_ctx, time.perf_counter() - t0)
        except Exception as exc:
            log.exception("运行失败 | %s | %.1fs", log_ctx, time.perf_counter() - t0)
            run_update_status(run_id, "failed")
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        finally:
            runtime.semaphore.release()

    return gen()
