from pydantic import BaseModel, Field

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

class ConvDetail(ConvOut):
    messages: list[MsgOut] = []

class CreateConv(BaseModel):
    title: str = Field(default="New Chat", max_length=200)

class ChatReq(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    system_prompt: str = Field(default="", max_length=2000)
    enable_search: bool = Field(default=False)
    enable_thinking: bool = Field(default=False)
