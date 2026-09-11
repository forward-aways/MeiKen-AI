"""路由聚合：main.py 统一注册。"""
from backend.routes import (
    agents, auth, chat, convs, files, images, kb, misc, providers, skills,
)

all_routers = [
    auth.router,
    convs.router,
    chat.router,
    agents.router,
    skills.router,
    kb.router,
    providers.router,
    images.router,
    files.router,
    misc.router,
]
