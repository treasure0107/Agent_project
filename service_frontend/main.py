"""
智能医疗助手 - FastAPI 入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router
from app.api.documents import router as documents_router
from app.api.preferences import router as preferences_router
from app.config.settings import settings
from app.database.postgresql import PostgresBase, postgres_engine
from app.models import conversation as conversation_models  # noqa: F401

app = FastAPI(
    title="智能医疗助手",
    version="0.1.0",
    description="用户认证与医疗助手后端服务",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(conversations_router)
app.include_router(preferences_router)
app.include_router(chat_router)
app.include_router(documents_router)


@app.on_event("startup")
def on_startup() -> None:
    """启动时尝试创建会话表与记忆表；数据库不可用时不阻断服务启动"""
    try:
        PostgresBase.metadata.create_all(bind=postgres_engine)
    except Exception as exc:  # noqa: BLE001
        print(f"[startup] 跳过会话表自动创建，PostgreSQL 暂不可用: {exc}")
    try:
        from app.agent.memory import setup_memories

        setup_memories()
    except Exception as exc:  # noqa: BLE001
        print(f"[startup] 跳过记忆表初始化: {exc}")


@app.get("/health")
def health() -> dict[str, str]:
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST or "0.0.0.0",
        port=settings.PORT or 8000,
        reload=True,
    )
