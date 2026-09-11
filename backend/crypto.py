"""API Key 密钥管理。

Key 以 Fernet 加密形式存储在 SQLite 中（绝不保存明文）。
加密密钥位于 ``config/fernet.key``，首次使用时自动生成，
部署到全新服务器无需手工配置。

说明：这里刻意不使用哈希——哈希不可逆，无法还原出调用上游 API
所需的明文 Key。
"""
import os

from cryptography.fernet import Fernet, InvalidToken

from backend.config import CONFIG_DIR

_KEY_FILE = os.path.join(CONFIG_DIR, "fernet.key")


def get_or_create_fernet_key() -> bytes:
    """读取 Fernet 密钥；不存在时生成（幂等）。"""
    os.makedirs(os.path.dirname(_KEY_FILE), exist_ok=True)
    if not os.path.exists(_KEY_FILE):
        key = Fernet.generate_key()
        fd = os.open(_KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(key)
    with open(_KEY_FILE, "rb") as f:
        return f.read().strip()


def encrypt_secret(plain: str) -> str:
    """加密明文 API Key，用于入库存储。"""
    return Fernet(get_or_create_fernet_key()).encrypt(plain.encode()).decode()


def decrypt_secret(token: str) -> str:
    """还原存储的 API Key 明文。"""
    try:
        return Fernet(get_or_create_fernet_key()).decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("无法解密供应商密钥：fernet.key 不匹配或密文已损坏") from exc
