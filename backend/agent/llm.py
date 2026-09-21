"""代理引擎的 LLM 构建。

供应商按用户从数据库解析（API Key 加密存储）。
模型名在构建请求时反向映射到供应商：

- ``deepseek_compat=True`` → ``DeepSeekChatOpenAI``：通过 ``extra_body`` 注入
  DeepSeek 思考参数（``thinking`` + ``reasoning_effort``），
  并从流式增量中捕获 ``reasoning_content``；
- ``deepseek_compat=False`` → 原生 ``ChatOpenAI``：绝不发送额外参数，
  兼容任意标准 OpenAI 协议端点（OpenAI、Ollama、GLM 等）。
"""
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_openai import ChatOpenAI

from backend.crypto import decrypt_secret
from backend.db import provider_find_by_model
from backend.log import get_logger

log = get_logger("backend.llm")


class LLMConfigError(ValueError):
    """模型没有可用供应商，或供应商未配置 API Key 时抛出。"""


class DeepSeekChatOpenAI(ChatOpenAI):
    def __init__(
        self,
        *,
        thinking: bool = True,
        reasoning_effort: str = "high",
        **kwargs,
    ):
        extra = dict(kwargs.pop("extra_body", None) or {})
        # DeepSeek 默认开启思考；关闭时需显式声明 disabled
        extra["thinking"] = {"type": "enabled" if thinking else "disabled"}
        if thinking:
            extra["reasoning_effort"] = reasoning_effort
        kwargs["extra_body"] = extra
        super().__init__(**kwargs)

    def _convert_chunk_to_generation_chunk(
        self, chunk, default_chunk_class, base_generation_info
    ):
        gen = super()._convert_chunk_to_generation_chunk(
            chunk, default_chunk_class, base_generation_info
        )
        if gen is None or not isinstance(gen.message, AIMessageChunk):
            return gen
        choices = chunk.get("choices") or chunk.get("chunk", {}).get("choices", [])
        if not choices:
            return gen
        rc = choices[0].get("delta", {}).get("reasoning_content")
        if rc:
            prev = gen.message.additional_kwargs.get("reasoning_content", "")
            gen.message.additional_kwargs["reasoning_content"] = prev + rc
        return gen

    def _get_request_payload(self, input_, *, stop=None, **kwargs):
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        msgs = payload.get("messages")
        if not msgs:
            return payload
        for idx, m in enumerate(self._convert_input(input_).to_messages()):
            if isinstance(m, AIMessage):
                rc = m.additional_kwargs.get("reasoning_content")
                if rc and idx < len(msgs):
                    msgs[idx]["reasoning_content"] = rc
        return payload


def resolve_provider(user_id: int, model: str) -> dict | None:
    """把模型名映射到对应供应商（用户自建或内置）。"""
    return provider_find_by_model(user_id, model)


def build_llm(
    provider: dict | None,
    *,
    model: str,
    thinking: bool = True,
    reasoning_effort: str = "high",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    **kwargs,
):
    """按供应商配置为 ``model`` 构建聊天模型。

    当模型没有供应商、或供应商未配置 API Key 时抛出 ``LLMConfigError``。
    """
    if not provider:
        raise LLMConfigError(f"模型「{model}」没有可用的供应商")
    api_key = decrypt_secret(provider.get("api_key_enc") or "") if provider.get("api_key_enc") else ""
    if not api_key:
        raise LLMConfigError(f"供应商「{provider['name']}」尚未配置 API Key")
    base_url = provider.get("base_url")
    if provider.get("deepseek_compat"):
        log.debug("构建 LLM | provider=%s model=%s 风格=deepseek thinking=%s effort=%s",
                  provider["name"], model, thinking, reasoning_effort)
        return DeepSeekChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            thinking=thinking,
            reasoning_effort=reasoning_effort,
            temperature=temperature,
            max_tokens=max_tokens,
            # 显式开启流式用量上报：langchain-openai 仅在 base_url 等参数全为 None 时
            # 才自动开启，而本项目始终传 base_url，故必须显式声明，否则
            # usage_metadata 恒为空 → 上下文用量恒为 0（见 ADR-20260921-CapsuleAndContextMeter）
            stream_usage=True,
            **kwargs,
        )
    log.debug("构建 LLM | provider=%s model=%s 风格=标准", provider["name"], model)
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        # 标准 OpenAI 兼容端点不显式开启：部分第三方实现不支持
        # stream_options.include_usage，开启会导致请求被拒（泛化边界）
        **kwargs,
    )
