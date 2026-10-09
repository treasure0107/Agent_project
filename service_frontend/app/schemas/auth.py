"""
认证相关请求/响应模型
"""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """注册请求"""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=72)


class LoginRequest(BaseModel):
    """登录请求：account 可为用户名或邮箱"""

    account: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=72)


class UserOut(BaseModel):
    """对外返回的用户信息（不含密码）"""

    id: int
    username: str
    email: EmailStr
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """登录成功返回"""

    access_token: str
    token_type: str = "bearer"
    user: UserOut
