"""
医疗文档上传接口：POST /documents/upload
"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.agent.documents import process_medical_document
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/documents", tags=["医疗文档"])


def _ensure_user_id(requested: str, current_user: User) -> str:
    canonical = f"user_{current_user.id}"
    if requested not in {canonical, str(current_user.id)}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权上传到其他用户空间",
        )
    return canonical


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(default="病历本"),
    user_id: str = Form(...),
    current_user: User = Depends(get_current_user),
) -> dict:
    """上传医疗文档，解析文本并写入长期记忆"""
    memory_user_id = _ensure_user_id(user_id, current_user)
    try:
        return await process_medical_document(
            file=file,
            document_type=document_type,
            user_id=memory_user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文档上传失败: {exc}",
        ) from exc
