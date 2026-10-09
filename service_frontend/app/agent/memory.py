"""
会话短期记忆（LangGraph Checkpoint）与长期记忆（LangGraph Store）
- 短期：POSTGRES_SHORT_TERM_URL / smart_short —— 按 thread_id 保存对话检查点
- 长期：POSTGRES_LONG_TERM_URL / smart_long —— 用户偏好、医疗历史等跨会话信息
"""
from __future__ import annotations

import threading
from typing import Any

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config.settings import settings

# 命名空间约定
NS_USER_PREFERENCES = "user_preferences"
NS_USER_MEDICAL_HISTORY = "user_medical_history"

_lock = threading.Lock()
_short_pool: ConnectionPool | None = None
_long_pool: ConnectionPool | None = None
_short_term_memory: PostgresSaver | None = None
_long_term_memory: PostgresStore | None = None


def _make_pool(conninfo: str) -> ConnectionPool:
    if not conninfo:
        raise ValueError("PostgreSQL 连接串为空，请检查 .env 配置")
    return ConnectionPool(
        conninfo=conninfo,
        min_size=1,
        max_size=5,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
        },
    )


def get_short_term_memory() -> PostgresSaver:
    """获取短期记忆 checkpointer（对话线程级）"""
    global _short_pool, _short_term_memory
    if _short_term_memory is not None:
        return _short_term_memory

    with _lock:
        if _short_term_memory is not None:
            return _short_term_memory
        _short_pool = _make_pool(settings.POSTGRES_SHORT_TERM_URL)
        _short_term_memory = PostgresSaver(_short_pool)
        _short_term_memory.setup()
        return _short_term_memory


def get_long_term_memory() -> PostgresStore:
    """获取长期记忆 store（用户级）"""
    global _long_pool, _long_term_memory
    if _long_term_memory is not None:
        return _long_term_memory

    with _lock:
        if _long_term_memory is not None:
            return _long_term_memory
        _long_pool = _make_pool(settings.POSTGRES_LONG_TERM_URL)
        _long_term_memory = PostgresStore(_long_pool)
        _long_term_memory.setup()
        return _long_term_memory


# 兼容用户提供的命名
get_long_term_memory_store = get_long_term_memory


def build_thread_config(thread_id: str) -> dict[str, Any]:
    """构造 LangGraph 短期记忆配置（thread_id 通常为会话 ID）"""
    return {"configurable": {"thread_id": thread_id}}


def get_user_long_memory(user_id: str, store: PostgresStore | None = None) -> str:
    """获取用户的长期记忆（个人信息、医疗记录等），格式化为提示词文本"""
    if store is None:
        store = get_long_term_memory()

    user_info: list[str] = []

    try:
        # 获取用户个人信息（基本信息）- 按字段去重，每个字段只保留最新
        preferences = store.search(("user_preferences", user_id), limit=100)
        if preferences:
            pref_dict: dict[str, Any] = {}
            for item in preferences:
                # 从 key 中提取 item_id (格式: namespace|user_id|item_id 或纯 item_id)
                key_parts = item.key.split("|") if "|" in item.key else [item.key]
                item_id = key_parts[-1] if key_parts else item.key
                pref_dict[item_id] = item.value

            pref_text = "\n".join(
                [
                    f"{value.get('key')}: {value.get('value')}"
                    for value in pref_dict.values()
                    if isinstance(value, dict)
                ]
            )
            if pref_text:
                user_info.append("【用户基本信息】\n" + pref_text)

        # 获取用户医疗历史 - 全部追加显示，不删除
        medical_history = store.search(("user_medical_history", user_id), limit=200)
        if medical_history:
            medical_by_category: dict[str, list[str]] = {}
            for item in medical_history:
                value = item.value if isinstance(item.value, dict) else {}
                category = value.get("category", "unknown")
                content = value.get("content", "")
                if not content:
                    continue
                medical_by_category.setdefault(category, []).append(content)

            history_lines: list[str] = []
            for category, contents in medical_by_category.items():
                if len(contents) == 1:
                    history_lines.append(f"{category}: {contents[0]}")
                else:
                    items_text = "\n".join(
                        [f"  {i + 1}. {c}" for i, c in enumerate(contents)]
                    )
                    history_lines.append(f"{category}:\n{items_text}")

            if history_lines:
                user_info.append("【医疗历史】\n" + "\n".join(history_lines))

    except Exception as exc:  # noqa: BLE001
        print(f"获取用户长期记忆时出错: {exc}")

    return "\n\n".join(user_info) if user_info else ""


def save_user_long_memory(
    store: PostgresStore | None,
    user_id: str,
    namespace: tuple,
    item_id: str,
    data: dict,
) -> None:
    """保存用户数据到长期记忆

    Args:
        store: PostgresStore，传 None 时自动获取
        user_id: 用户 ID（写入 data 元数据，便于排查）
        namespace: 如 ("user_preferences", user_id) 或 ("user_medical_history", user_id)
        item_id: 条目唯一键（偏好字段名，或医疗记录 UUID）
        data: 存储内容字典
    """
    if store is None:
        store = get_long_term_memory()
    try:
        payload = dict(data)
        payload.setdefault("user_id", user_id)
        store.put(namespace, item_id, payload)
    except Exception as exc:  # noqa: BLE001
        print(f"保存用户长期记忆时出错: {exc}")


def save_user_preference(
    user_id: str,
    key: str,
    value: str,
    store: PostgresStore | None = None,
) -> None:
    """保存/覆盖用户偏好字段（如 preferred_style、allergies）"""
    save_user_long_memory(
        store,
        user_id,
        (NS_USER_PREFERENCES, user_id),
        key,
        {"key": key, "value": value},
    )


def save_user_medical_record(
    user_id: str,
    category: str,
    content: str,
    item_id: str,
    store: PostgresStore | None = None,
) -> None:
    """追加一条医疗历史记录（不覆盖同类其它条目）"""
    save_user_long_memory(
        store,
        user_id,
        (NS_USER_MEDICAL_HISTORY, user_id),
        item_id,
        {"category": category, "content": content},
    )


def setup_memories() -> None:
    """初始化短/长期记忆表结构（可在应用启动时调用）"""
    get_short_term_memory()
    get_long_term_memory()
