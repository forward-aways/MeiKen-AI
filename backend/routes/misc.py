"""杂项路由：健康检查。"""
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["杂项"])


@router.get("/health")
def health():
    return {"status": "ok"}
