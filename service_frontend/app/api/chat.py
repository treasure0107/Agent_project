"""
聊天接口：POST /chat/send
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agent.chat import chat_with_user
from app.api.deps import get_current_user
from app.database.postgresql import get_postgres_db
from app.models.user import User
from app.schemas.chat import ChatSendRequest, ChatSendResponse

router = APIRouter(prefix="/chat", tags=["聊天"])


def _ensure_user_id(requested: str, current_user: User) -> str:
    canonical = f"user_{current_user.id}"
    if requested not in {canonical, str(current_user.id)}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权以其他用户身份聊天",
        )
    return canonical


@router.post("/send", response_model=ChatSendResponse)
def send_message(
    payload: ChatSendRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_postgres_db),
) -> ChatSendResponse:
    """处理用户发送的问题，返回助手回复"""
    user_id = _ensure_user_id(payload.user_id, current_user)
    try:
        reply = chat_with_user(
            user_id=user_id,
            message=payload.message,
            thread_id=payload.thread_id,
            db=db,
        )
        return ChatSendResponse(success=True, message=reply)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"聊天处理失败: {exc}",
        ) from exc
