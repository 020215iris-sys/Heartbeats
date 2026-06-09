"""이전 채팅 — 백엔드(/counseling) 연동."""
from datetime import datetime
from . import api_client

_PERSONA = {"empathy": ("다온", "🌱")}


def _fmt_date(iso: str) -> str:
    try:
        dt = datetime.fromisoformat((iso or "").replace("Z", "+00:00"))
        return f"{dt.year}년 {dt.month}월 {dt.day}일"
    except Exception:
        return iso or ""


def _map_session(s: dict) -> dict:
    persona, emoji = _PERSONA.get(s.get("persona_type"), ("다온", "🌱"))
    return {
        "id": s.get("session_id"),
        "persona": persona,
        "emoji": emoji,
        "date": _fmt_date(s.get("started_at", "")),
        "preview": s.get("preview") or "(요약 없음)",
        "msg_count": s.get("message_count", 0),
    }


def get_recent_chats(limit: int | None = None) -> list[dict]:
    return [_map_session(s) for s in api_client.get_sessions(limit=limit)]


def get_chat(chat_id: str) -> dict | None:
    for s in api_client.get_sessions():
        if s.get("session_id") == chat_id:
            return _map_session(s)
    return None


def get_chat_messages(chat_id: str) -> list[dict]:
    msgs = api_client.get_session_messages(chat_id)
    return [{"role": m.get("role"), "content": m.get("content", "")} for m in msgs]
