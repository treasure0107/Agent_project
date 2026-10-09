"""
会话管理接口：列表 / 创建 / 详情 / 删除
路径与 frontend HomeView 对齐（/conversations/...）
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.postgresql import get_postgres_db
from app.models.conversation import Conversation, Message
from app.models.user import User
from app.schemas.conversation import (
    ConversationDetail,
    ConversationListItem,
    CreateConversationRequest,
    MessageOut,
)

router = APIRouter(prefix="/conversations", tags=["会话"])

WELCOME_MESSAGE = "您好！我是智能医疗助手，请问有什么可以帮您？"
DB_UNAVAILABLE_DETAIL = (
    "PostgreSQL 会话库不可用。请先开 SSH 隧道："
    "ssh -L 5432:127.0.0.1:5432 root@120.26.72.29，"
    "并确认库 smart_session 已建表（scripts/init_conversations.sql）"
)


def _ensure_owner(conversation: Conversation | None, user_id: int) -> Conversation:
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    if conversation.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该会话")
    return conversation


def _raise_db_error(exc: Exception) -> None:
    if isinstance(exc, OperationalError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=DB_UNAVAILABLE_DETAIL,
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"会话数据库错误: {exc}",
    ) from exc


@router.get("/list")
def list_conversations(
    user_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_postgres_db),
) -> dict:
    """获取当前用户的会话列表"""
    if user_id is not None and user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看他人会话")

    try:
        rows = (
            db.query(Conversation)
            .filter(Conversation.user_id == current_user.id)
            .order_by(Conversation.last_active.desc())
            .all()
        )
        conversations = [
            ConversationListItem(
                id=row.id,
                title=row.title,
                lastMessage=row.last_message or "",
                lastActive=row.last_active,
                created_at=row.created_at,
            ).model_dump(mode="json")
            for row in rows
        ]
        return {"conversations": conversations}
    except (OperationalError, SQLAlchemyError) as exc:
        _raise_db_error(exc)


@router.post("/create")
def create_conversation(
    payload: CreateConversationRequest,
    user_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_postgres_db),
) -> dict:
    """创建新会话，并写入欢迎消息"""
    if user_id is not None and user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权为他人创建会话")

    try:
        existing = db.query(Conversation).filter(Conversation.id == payload.id).first()
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="会话 ID 已存在")

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        conversation = Conversation(
            id=payload.id,
            user_id=current_user.id,
            title=payload.title,
            last_message=WELCOME_MESSAGE,
            last_active=now,
            created_at=now,
        )
        db.add(conversation)
        db.add(
            Message(
                conversation_id=payload.id,
                role="assistant",
                content=WELCOME_MESSAGE,
                timestamp=now,
            )
        )
        db.commit()
        db.refresh(conversation)

        detail = ConversationDetail(
            id=conversation.id,
            title=conversation.title,
            last_message=conversation.last_message,
            last_active=conversation.last_active,
        )
        return {"conversation": detail.model_dump(mode="json")}
    except HTTPException:
        raise
    except (OperationalError, SQLAlchemyError) as exc:
        db.rollback()
        _raise_db_error(exc)


@router.get("/get")
def get_conversation(
    conversation_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_postgres_db),
) -> dict:
    """获取会话消息列表（选择会话时调用）"""
    try:
        conversation = (
            db.query(Conversation).filter(Conversation.id == conversation_id).first()
        )
        conversation = _ensure_owner(conversation, current_user.id)

        messages = [
            MessageOut(
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp,
            ).model_dump(mode="json")
            for msg in conversation.messages
        ]
        return {
            "conversation": {
                "id": conversation.id,
                "title": conversation.title,
                "last_message": conversation.last_message,
                "last_active": conversation.last_active.isoformat()
                if conversation.last_active
                else None,
            },
            "messages": messages,
        }
    except HTTPException:
        raise
    except (OperationalError, SQLAlchemyError) as exc:
        _raise_db_error(exc)


@router.delete("/delete")
def delete_conversation(
    conversation_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_postgres_db),
) -> dict:
    """删除会话及其消息"""
    try:
        conversation = (
            db.query(Conversation).filter(Conversation.id == conversation_id).first()
        )
        conversation = _ensure_owner(conversation, current_user.id)
        db.delete(conversation)
        db.commit()
        return {"success": True, "message": "会话已删除"}
    except HTTPException:
        raise
    except (OperationalError, SQLAlchemyError) as exc:
        db.rollback()
        _raise_db_error(exc)
