"""用户域：账户创建、查询、资料更新与管理员种子。"""
from backend.db._core import _db, _ts

# 对外返回的用户字段（不含密码散列）
USER_COLUMNS = (
    "id,email,nickname,role,created_at,"
    "real_name,gender,birthday,bio,ai_address,avatar,avatar_color"
)

# 允许通过资料接口更新的字段
PROFILE_FIELDS = {
    "nickname", "real_name", "gender", "birthday",
    "bio", "ai_address", "avatar", "avatar_color",
}

__all__ = [
    "USER_COLUMNS", "PROFILE_FIELDS",
    "user_create", "user_get", "user_get_by_email", "user_get_by_nickname",
    "user_update_nickname", "user_update_password", "user_update_profile",
    "seed_admin",
]


def user_create(email: str, password_hash: str, nickname: str = ""):
    now = _ts()
    with _db() as c:
        cur = c.execute("INSERT INTO users(email,nickname,password_hash,created_at) VALUES(?,?,?,?)",
                        (email, nickname, password_hash, now))
        return dict(c.execute(f"SELECT {USER_COLUMNS} FROM users WHERE id=?", (cur.lastrowid,)).fetchone())


def user_get_by_email(email: str):
    with _db() as c:
        r = c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    return dict(r) if r else None


def user_get(uid: int):
    with _db() as c:
        r = c.execute(f"SELECT {USER_COLUMNS} FROM users WHERE id=?", (uid,)).fetchone()
    return dict(r) if r else None


def user_get_by_nickname(nickname: str):
    with _db() as c:
        r = c.execute("SELECT * FROM users WHERE LOWER(nickname)=LOWER(?) AND nickname!=''", (nickname,)).fetchone()
    return dict(r) if r else None


def user_update_nickname(uid: int, nickname: str):
    with _db() as c:
        c.execute("UPDATE users SET nickname=? WHERE id=?", (nickname, uid))


def user_update_password(uid: int, password_hash: str):
    with _db() as c:
        c.execute("UPDATE users SET password_hash=? WHERE id=?", (password_hash, uid))


def user_update_profile(uid: int, fields: dict):
    """更新个人资料：仅写入 PROFILE_FIELDS 白名单内的字段。"""
    sets, vals = [], []
    for k, v in fields.items():
        if k in PROFILE_FIELDS and v is not None:
            sets.append(f"{k}=?")
            vals.append(v)
    if not sets:
        return
    vals.append(uid)
    with _db() as c:
        c.execute(f"UPDATE users SET {','.join(sets)} WHERE id=?", vals)


def seed_admin(hash_pw: str):
    """无任何用户时创建默认管理员账户（幂等）。"""
    with _db() as c:
        count = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count == 0:
            c.execute("INSERT INTO users(email,nickname,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                      ("admin@meiken.ai", "Admin", hash_pw, "admin", _ts()))
