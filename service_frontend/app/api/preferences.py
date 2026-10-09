"""
用户偏好 API（读写长期记忆 user_preferences）
路径与 frontend PreferencesView 对齐
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.agent.memory import (
    NS_USER_PREFERENCES,
    get_long_term_memory,
    save_user_preference,
)
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.preferences import PreferenceListResponse, PreferenceSaveRequest

router = APIRouter(prefix="/preferences", tags=["偏好设置"])


def _canonical_user_id(user: User) -> str:
    """与前端 HomeView 一致：user_{数字id}"""
    return f"user_{user.id}"


def _ensure_user_id(requested: str, current_user: User) -> str:
    canonical = _canonical_user_id(current_user)
    if requested not in {canonical, str(current_user.id)}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问其他用户的偏好",
        )
    return canonical


def _list_preferences_text(user_id: str) -> str:
    store = get_long_term_memory()
    items = store.search((NS_USER_PREFERENCES, user_id), limit=100)
    if not items:
        return ""

    pref_dict: dict[str, str] = {}
    for item in items:
        value = item.value if isinstance(item.value, dict) else {}
        key = value.get("key") or item.key
        val = value.get("value")
        if key is None or val is None:
            continue
        pref_dict[str(key)] = str(val)

    return "\n".join(f"{k}: {v}" for k, v in pref_dict.items())


@router.get("/list", response_model=PreferenceListResponse)
def list_preferences(
    user_id: str = Query(...),
    current_user: User = Depends(get_current_user),
) -> PreferenceListResponse:
    """获取用户偏好文本：preferred_style: xxx\\nallergies: yyy"""
    memory_user_id = _ensure_user_id(user_id, current_user)
    try:
        text = _list_preferences_text(memory_user_id)
        return PreferenceListResponse(preferences=text)
    except (OperationalError, SQLAlchemyError, Exception) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"读取偏好失败: {exc}",
        ) from exc


@router.post("/save")
def save_preference(
    payload: PreferenceSaveRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """保存单条偏好到长期记忆"""
    memory_user_id = _ensure_user_id(payload.user_id, current_user)
    allowed_keys = {"preferred_style", "allergies"}
    if payload.key not in allowed_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的偏好键，仅允许: {', '.join(sorted(allowed_keys))}",
        )
    try:
        save_user_preference(memory_user_id, payload.key, payload.value)
        return {"success": True, "key": payload.key, "value": payload.value}
    except (OperationalError, SQLAlchemyError, Exception) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"保存偏好失败: {exc}",
        ) from exc
