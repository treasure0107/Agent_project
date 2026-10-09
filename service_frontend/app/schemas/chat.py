"""
聊天请求模型
"""
from pydantic import BaseModel, Field


class ChatSendRequest(BaseModel):
    """前端 /chat/send 请求体"""

    user_id: str = Field(..., min_length=1, max_length=64)
    message: str = Field(..., min_length=1, max_length=8000)
    thread_id: str = Field(..., min_length=1, max_length=64)


class ChatSendResponse(BaseModel):
    """前端期望的响应"""

    success: bool = True
    message: str
