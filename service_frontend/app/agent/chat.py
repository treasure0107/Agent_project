"""
对话 Agent：处理用户提问，结合长/短期记忆生成回复
"""
from __future__ import annotations

from datetime import datetime, timezone

from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from sqlalchemy.orm import Session

from app.agent.memory import (
    build_thread_config,
    get_short_term_memory,
    get_user_long_memory,
)
from app.config.settings import settings
from app.models.conversation import Conversation, Message

_graph = None
_llm: ChatTongyi | None = None


def _get_llm() -> ChatTongyi:
    global _llm
    if _llm is None:
        if not settings.DASHSCOPE_API_KEY:
            raise ValueError("未配置 DASHSCOPE_API_KEY，无法调用大模型")
        _llm = ChatTongyi(
            model="qwen-turbo",
            dashscope_api_key=settings.DASHSCOPE_API_KEY,
            temperature=0.3,
        )
    return _llm


def _build_system_prompt(user_id: str) -> str:
    long_memory = ""
    try:
        long_memory = get_user_long_memory(user_id) or ""
    except Exception as exc:  # noqa: BLE001
        print(f"读取长期记忆失败: {exc}")

    base = (
        "你是一名专业、谨慎的智能医疗助手。"
        "请用清晰的中文回答用户关于健康、就医、报告解读等问题。"
        "你不能替代执业医师诊断；涉及紧急情况请建议及时就医。"
        "回答尽量使用 Markdown 结构化排版。"
    )
    if long_memory:
        return f"{base}\n\n以下是该用户的长期记忆，请在回答时参考：\n{long_memory}"
    return base


def get_chat_graph():
    """获取带短期记忆 checkpointer 的对话图（单例）"""
    global _graph
    if _graph is not None:
        return _graph

    llm = _get_llm()

    def call_model(state: MessagesState) -> dict:
        response = llm.invoke(state["messages"])
        return {"messages": [response]}

    builder = StateGraph(MessagesState)
    builder.add_node("model", call_model)
    builder.add_edge(START, "model")
    builder.add_edge("model", END)
    _graph = builder.compile(checkpointer=get_short_term_memory())
    return _graph


def _persist_messages(
    db: Session,
    conversation_id: str,
    user_text: str,
    assistant_text: str,
) -> None:
    """将本轮对话写入会话消息表，并更新会话摘要"""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    conversation = (
        db.query(Conversation).filter(Conversation.id == conversation_id).first()
    )
    if conversation is None:
        # 会话不存在时不阻断聊天，仅跳过持久化
        return

    db.add(
        Message(
            conversation_id=conversation_id,
            role="user",
            content=user_text,
            timestamp=now,
        )
    )
    db.add(
        Message(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_text,
            timestamp=now,
        )
    )
    conversation.last_message = (assistant_text or "")[:500]
    conversation.last_active = now
    if conversation.title == conversation.id or conversation.title.startswith("conv_"):
        conversation.title = (user_text or conversation.title)[:40]
    db.commit()


def chat_with_user(
    *,
    user_id: str,
    message: str,
    thread_id: str,
    db: Session,
) -> str:
    """
    处理用户一条消息，返回助手回复文本。

    Args:
        user_id: 前端传入，如 user_1
        message: 用户问题
        thread_id: 会话 ID（短期记忆 thread）
        db: smart_session 数据库会话
    """
    if not message or not message.strip():
        raise ValueError("消息内容不能为空")
    if not thread_id:
        raise ValueError("thread_id 不能为空")

    graph = get_chat_graph()
    config = build_thread_config(thread_id)
    system_prompt = _build_system_prompt(user_id)

    result = graph.invoke(
        {
            "messages": [
                SystemMessage(content=system_prompt),
                HumanMessage(content=message.strip()),
            ]
        },
        config=config,
    )

    assistant_text = ""
    messages = result.get("messages") or []
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) or getattr(msg, "type", "") == "ai":
            content = msg.content
            if isinstance(content, list):
                assistant_text = "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                )
            else:
                assistant_text = str(content)
            break

    if not assistant_text:
        assistant_text = "抱歉，我暂时无法生成回答，请稍后再试。"

    try:
        _persist_messages(db, thread_id, message.strip(), assistant_text)
    except Exception as exc:  # noqa: BLE001
        print(f"持久化会话消息失败: {exc}")
        db.rollback()

    return assistant_text
