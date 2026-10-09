"""
医疗文档处理：上传解析并写入长期记忆
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import UploadFile
from pypdf import PdfReader

from app.agent.memory import save_user_medical_record

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_STORE_CHARS = 4000
ALLOWED_SUFFIXES = {".pdf", ".txt", ".md"}


def _safe_filename(filename: str) -> str:
    name = Path(filename or "document").name
    name = re.sub(r"[^\w.\u4e00-\u9fff-]+", "_", name)
    return name[:120] or "document"


def extract_text_from_file(path: Path) -> str:
    """从本地文件提取文本"""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        parts: list[str] = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                parts.append(text.strip())
        return "\n\n".join(parts).strip()

    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore").strip()

    raise ValueError(f"暂不支持的文件类型: {suffix}")


async def process_medical_document(
    *,
    file: UploadFile,
    document_type: str,
    user_id: str,
) -> dict:
    """
    保存上传文件、提取文本，并写入用户长期医疗记忆。

    Returns:
        上传结果字典，供 /documents/upload 返回
    """
    if not user_id:
        raise ValueError("user_id 不能为空")

    original_name = file.filename or "document.pdf"
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ValueError("仅支持上传 PDF / TXT / MD 文件")

    safe_name = _safe_filename(original_name)
    stored_name = f"{uuid.uuid4().hex}_{safe_name}"
    dest = UPLOAD_DIR / stored_name

    content = await file.read()
    if not content:
        raise ValueError("上传文件为空")
    dest.write_bytes(content)

    try:
        text = extract_text_from_file(dest)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"文档解析失败: {exc}") from exc

    if not text:
        text = f"（未能从文件中提取到文本内容）文件名: {original_name}"

    preview = text[:MAX_STORE_CHARS]
    item_id = f"doc_{uuid.uuid4().hex[:12]}"
    category = (document_type or "医疗文档").strip()[:50]

    save_user_medical_record(
        user_id=user_id,
        category=category,
        content=f"【{original_name}】\n{preview}",
        item_id=item_id,
    )

    return {
        "success": True,
        "filename": original_name,
        "stored_as": stored_name,
        "document_type": category,
        "item_id": item_id,
        "text_preview": preview[:500],
        "char_count": len(text),
    }
