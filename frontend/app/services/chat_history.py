"""이전 채팅 — 백엔드(/counseling) 연동."""
from datetime import datetime
from . import api_client
from .personas import get_persona




def _fmt_date(iso: str) -> str:
    try:
        dt = datetime.fromisoformat((iso or "").replace("Z", "+00:00"))
        return f"{dt.year}년 {dt.month}월 {dt.day}일"
    except Exception:
        return iso or ""


def _map_session(s: dict) -> dict:

    raw_persona = s.get("persona_type")

    if isinstance(raw_persona, dict):
        code = raw_persona.get("code")
        raw_name = raw_persona.get("name")
        raw_emoji = raw_persona.get("avatar_emoji")
    else:
        code = raw_persona
        raw_name = None
        raw_emoji = None

    persona_meta = get_persona(code)

    return {
        "id": s.get("session_id"),
        "persona": raw_name or persona_meta["name"],
        "emoji": raw_emoji or persona_meta["avatar_emoji"],
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
