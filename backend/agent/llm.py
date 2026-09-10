"""LLM construction for the agent harness.

Providers are resolved per user from the database (API keys stored encrypted).
A model name maps back to its provider at request-build time:

- ``deepseek_compat=True`` → ``DeepSeekChatOpenAI``: injects DeepSeek thinking
  params (``thinking`` + ``reasoning_effort``) via ``extra_body`` and captures
  ``reasoning_content`` from stream deltas;
- ``deepseek_compat=False`` → plain ``ChatOpenAI``: zero extra params ever sent,
  safe for any standard OpenAI-compatible endpoint (OpenAI, Ollama, GLM, ...).
"""

from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_openai import ChatOpenAI

from backend.crypto import decrypt_secret
from backend.database import provider_find_by_model
from backend.log import get_logger

log = get_logger("backend.llm")


class LLMConfigError(ValueError):
    """Raised when a model has no usable provider or the provider lacks a key."""


class DeepSeekChatOpenAI(ChatOpenAI):
    def __init__(
        self,
        *,
        thinking: bool = True,
        reasoning_effort: str = "high",
        **kwargs,
    ):
        extra = dict(kwargs.pop("extra_body", None) or {})
        # DeepSeek enables thinking by default; disable explicitly when off.
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
    """Map a model name to its enabled provider (user's own or built-in)."""
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
    """Build a chat model for ``model`` using the resolved provider config.

    Raises ``LLMConfigError`` when no provider owns the model or the provider
    has no API key configured.
    """
    if not provider:
        raise LLMConfigError(f"No provider configured for model '{model}'")
    api_key = decrypt_secret(provider.get("api_key_enc") or "") if provider.get("api_key_enc") else ""
    if not api_key:
        raise LLMConfigError(f"Provider '{provider['name']}' has no API key configured")
    base_url = provider.get("base_url")
    if provider.get("deepseek_compat"):
        log.debug("build llm | provider=%s model=%s style=deepseek thinking=%s effort=%s",
                  provider["name"], model, thinking, reasoning_effort)
        return DeepSeekChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            thinking=thinking,
            reasoning_effort=reasoning_effort,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
    log.debug("build llm | provider=%s model=%s style=standard", provider["name"], model)
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs,
    )