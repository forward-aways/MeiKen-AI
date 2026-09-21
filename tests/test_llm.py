"""LLM 构建测试：流式用量上报与 DeepSeek 专有参数注入。

回归目标（对应 ADR-20260921-CapsuleAndContextMeter 的根因 A）：
- langchain-openai 仅在 base_url 等参数全为 None 时才自动开启 stream_usage，
  而本项目始终传 base_url → 必须显式开启，否则 usage_metadata 恒为空，
  上下文用量恒为 0；
- 非 DeepSeek 兼容端点不得注入专有参数（泛化边界）。
"""
import backend.agent.llm as llm


def _provider(**overrides) -> dict:
    base = {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "api_key_enc": "encrypted-placeholder",
        "deepseek_compat": 1,
    }
    base.update(overrides)
    return base


def _build(monkeypatch, provider, **kwargs):
    # 避免依赖真实 Fernet 密钥
    monkeypatch.setattr(llm, "decrypt_secret", lambda _s: "fake-key")
    return llm.build_llm(provider, model="deepseek-flash", **kwargs)


def test_deepseek_compat_enables_stream_usage(monkeypatch):
    model = _build(monkeypatch, _provider())
    assert model.stream_usage is True, "必须显式开启流式用量，否则上下文用量恒为 0"


def test_deepseek_compat_injects_thinking_params(monkeypatch):
    model = _build(monkeypatch, _provider(), thinking=True, reasoning_effort="max")
    extra = model.extra_body
    assert extra["thinking"] == {"type": "enabled"}
    assert extra["reasoning_effort"] == "max"


def test_thinking_disabled_omits_reasoning_effort(monkeypatch):
    model = _build(monkeypatch, _provider(), thinking=False, reasoning_effort="high")
    extra = model.extra_body
    assert extra["thinking"] == {"type": "disabled"}
    assert "reasoning_effort" not in extra, "关闭思考时不应下发推理强度"


def test_standard_provider_gets_no_deepseek_params(monkeypatch):
    model = _build(monkeypatch, _provider(name="OpenAI", deepseek_compat=0))
    assert not model.extra_body, "标准 OpenAI 兼容端点不得注入 DeepSeek 专有参数"
    assert model.stream_usage is not True, "不支持的端点不应强制开启流式用量"


def test_missing_key_raises(monkeypatch):
    monkeypatch.setattr(llm, "decrypt_secret", lambda _s: "")
    try:
        llm.build_llm(_provider(), model="deepseek-flash")
    except llm.LLMConfigError:
        return
    raise AssertionError("未配置 Key 时应抛出 LLMConfigError")
