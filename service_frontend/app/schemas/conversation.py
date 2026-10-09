"""
会话相关请求/响应模型
"""
from datetime import datetime

from pydantic import BaseModel, Field


class CreateConversationRequest(BaseModel):
    """创建会话请求体"""

    id: str = Field(..., min_length=1, max_length=64)
    title: str = Field(..., min_length=1, max_length=255)


class ConversationListItem(BaseModel):
    """列表项（字段名对齐前端）"""

    id: str
    title: str
    lastMessage: str
    lastActive: datetime
    created_at: datetime


class ConversationDetail(BaseModel):
    """创建成功返回的会话对象"""

    id: str
    title: str
    last_message: str
    last_active: datetime


class MessageOut(BaseModel):
    """消息"""

    role: str
    content: str
    timestamp: datetime
