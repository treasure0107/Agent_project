"""
偏好设置请求/响应模型
"""
from pydantic import BaseModel, Field


class PreferenceSaveRequest(BaseModel):
    """保存单条偏好"""

    user_id: str = Field(..., min_length=1, max_length=64)
    key: str = Field(..., min_length=1, max_length=100)
    value: str = Field(..., max_length=2000)


class PreferenceListResponse(BaseModel):
    """列表响应（文本格式对齐 PreferencesView 解析逻辑）"""

    preferences: str
