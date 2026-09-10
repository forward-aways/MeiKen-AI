"""API-key secret management.

Keys are stored in SQLite as Fernet-encrypted blobs (never plaintext). The
Fernet key lives in ``config/fernet.key`` and is auto-generated on first use,
so deploying to a fresh server requires zero manual setup.

Note: hashing was deliberately NOT chosen — hashes are one-way and cannot be
decrypted back into the plaintext key needed for upstream API calls.
"""

import os

from cryptography.fernet import Fernet, InvalidToken

_KEY_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config", "fernet.key",
)


def get_or_create_fernet_key() -> bytes:
    """Load the Fernet key, generating it on first run (idempotent)."""
    os.makedirs(os.path.dirname(_KEY_FILE), exist_ok=True)
    if not os.path.exists(_KEY_FILE):
        key = Fernet.generate_key()
        fd = os.open(_KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(key)
    with open(_KEY_FILE, "rb") as f:
        return f.read().strip()


def encrypt_secret(plain: str) -> str:
    """Encrypt a plaintext API key for storage."""
    return Fernet(get_or_create_fernet_key()).encrypt(plain.encode()).decode()


def decrypt_secret(token: str) -> str:
    """Decrypt a stored API key back to plaintext."""
    try:
        return Fernet(get_or_create_fernet_key()).decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError(
            "Unable to decrypt provider key: fernet.key mismatch or corrupted value"
        ) from exc