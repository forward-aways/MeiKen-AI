from pydantic import BaseModel, Field
from typing import Literal

# -- auth --

class RegisterReq(BaseModel):
    email: str = Field(..., min_length=3, max_length=200, pattern=r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
    password: str = Field(..., min_length=6, max_length=100)
    nickname: str = Field(default="", max_length=50)

class LoginReq(BaseModel):
    email: str = Field(..., min_length=1, max_length=200)
    password: str

class AuthResp(BaseModel):
    token: str
    user: dict

class ProfileReq(BaseModel):
    nickname: str | None = Field(default=None, min_length=1, max_length=50)
    real_name: str | None = Field(default=None, max_length=50)
    gender: str | None = Field(default=None, pattern=r'^(male|female|other|private|)$')
    birthday: str | None = Field(default=None, max_length=10)
    bio: str | None = Field(default=None, max_length=100)
    ai_address: str | None = Field(default=None, max_length=30)
    avatar: str | None = Field(default=None, max_length=300000)
    avatar_color: str | None = Field(default=None, max_length=20)

class ForgotReq(BaseModel):
    email: str = Field(..., min_length=3, max_length=200)

class ResetReq(BaseModel):
    token: str
    password: str = Field(..., min_length=6, max_length=100)

class ChangePasswordReq(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=100)

# -- conversations --

class ConvOut(BaseModel):
    id: int; title: str; created_at: str; updated_at: str

class ConvItem(ConvOut):
    msg_count: int = 0

class MsgOut(BaseModel):
    id: int; conversation_id: int; role: str; content: str; created_at: str
    images: list[str] = []

class ConvDetail(ConvOut):
    messages: list[MsgOut] = []

class CreateConv(BaseModel):
    title: str = Field(default="New Chat", max_length=200)

class ChatReq(BaseModel):
    message: str = Field(default="", max_length=8000)
    image_ids: list[str] = Field(default=[], max_length=4)
    system_prompt: str = Field(default="", max_length=2000)
    enable_search: bool = Field(default=False)
    enable_thinking: bool = Field(default=False)
    enable_rag: bool = Field(default=False)
    rag_files: list[str] = Field(default=[])
    agent_id: int | None = Field(default=None)
    # per-session overrides on top of the agent's own config
    model: str | None = Field(default=None, max_length=128)
    thinking: bool | None = Field(default=None)
    reasoning_effort: str | None = Field(default=None, pattern=r'^(low|high|max)$')
    # UI mode: code / work / general — selects the soul block
    mode: Literal["code", "work", "general"] = "general"

# -- agents --

class AgentReq(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, pattern=r'^[a-zA-Z0-9\-_]+$')
    display_name: str = Field(default="", max_length=50)
    description: str = Field(default="", max_length=300)
    system_prompt: str = Field(default="", max_length=4000)
    tools: list[str] = Field(default=[])
    model: str = Field(default="deepseek-flash", max_length=128)
    thinking: bool = Field(default=True)
    reasoning_effort: str = Field(default="high", pattern=r'^(low|high|max)$')
    temperature: float = Field(default=0.7, ge=0, le=2)

class ApprovalReq(BaseModel):
    decision: str = Field(..., pattern=r'^(approve|reject|edit)$')
    edited_args: dict | None = Field(default=None)
    message: str | None = Field(default=None, max_length=500)

# -- skills --

class SkillCreateReq(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, pattern=r'^[a-z0-9\u4e00-\u9fff][a-z0-9\u4e00-\u9fff\-_]{0,63}$')
    description: str = Field(..., min_length=1, max_length=300)
    body: str = Field(..., min_length=1, max_length=10000)

class SkillUpdateReq(BaseModel):
    description: str | None = Field(default=None, min_length=1, max_length=300)
    body: str | None = Field(default=None, min_length=1, max_length=10000)
    enabled: bool | None = Field(default=None)

# -- providers --

MODEL_NAME_PATTERN = r'^[a-zA-Z0-9][a-zA-Z0-9._\-:/]{1,127}$'


class ProviderModelReq(BaseModel):
    name: str = Field(..., pattern=MODEL_NAME_PATTERN)
    context_window: int | None = Field(default=None, ge=1024, le=1_000_000_000)


class ProviderCreateReq(BaseModel):
    name: str = Field(..., min_length=1, max_length=40)
    base_url: str = Field(..., min_length=8, max_length=500, pattern=r'^https?://\S+$')
    api_key: str | None = Field(default=None, max_length=500)
    deepseek_compat: bool = Field(default=False)
    models: list[ProviderModelReq] = Field(..., min_length=1, max_length=50)


class ProviderUpdateReq(BaseModel):
    """api_key: None = keep existing; empty string = clear the key."""
    name: str | None = Field(default=None, min_length=1, max_length=40)
    base_url: str | None = Field(default=None, min_length=8, max_length=500, pattern=r'^https?://\S+$')
    api_key: str | None = Field(default=None, max_length=500)
    deepseek_compat: bool | None = Field(default=None)
    models: list[ProviderModelReq] | None = Field(default=None, min_length=1, max_length=50)
    enabled: bool | None = Field(default=None)
