import uuid
from datetime import datetime, timezone

from core.crypto import encrypt_content, encrypt_json, decrypt_json


# ──────────────────────────────────────────
# 위기 박제 정책
# - PRESERVE_BEFORE: 위기 발화 자체 포함 직전 N개
# - PRESERVE_AFTER : 세션 종료 후처리 시 위기 발화 이후 K개까지 추가
# - 90일 자동삭제와 무관하게 crisis_events 행에 박제(영구 보존)
# - 약관·개인정보처리방침에 별도 명시 필요
# ──────────────────────────────────────────
PRESERVE_BEFORE = 15
PRESERVE_AFTER  = 5



# -----------------------------------------------------------------------
# 안내 문구 정의
# severity에 따라 다른 문구 반환
# -----------------------------------------------------------------------
CRISIS_MESSAGES = {
    "critical": (
        "지금 많이 힘드신 것 같아서 걱정이 돼요. "
        "혼자 견디려고 하지 않아도 괜찮아요.\n\n"
        "📞 자살예방상담전화: 109 (24시간)\n"
        "📞 정신건강상담전화: 1577-0199 (24시간)\n"
        "📞 긴급신고: 119\n\n"
        "지금 안전한 곳에 계신가요?"
    ),

    "high": (
        "많이 힘드신 것 같아서 걱정돼요. "
        "혼자 감당하기 어렵다면 도움을 요청하는 것도 괜찮아요.\n\n"
        "📞 자살예방상담전화: 109 (24시간)\n"
        "📞 정신건강상담전화: 1577-0199 (24시간)\n\n"
        "지금 어떤 상황인지 조금 더 이야기해 주실 수 있나요?"
    ),

    "medium": (
        "요즘 정말 지치셨겠어요. "
        "그 감정을 조금 더 이야기해 주실 수 있나요?"
    ),

    "low": (
        "많이 힘드시군요. "
        "천천히, 편하게 이야기해 주셔도 괜찮아요."
    ),
}


def get_crisis_response_message(severity: str) -> str:
    return CRISIS_MESSAGES.get(severity, CRISIS_MESSAGES["low"])


# -----------------------------------------------------------------------
# crisis_events DB 저장
# DB 세션은 호출하는 쪽(라우터 or llm.py)에서 주입
# -----------------------------------------------------------------------

SEVERITY_SCORE_MAP = {
    "critical": 1.0,
    "high": 0.85,
    "medium": 0.6,
}

async def save_crisis_event(
    db,
    user_id: str,
    conversation_id: str,
    session_id: str,
    severity: str,
) -> None:
    """
    crisis_events 테이블에 위기 이벤트를 저장 + 위기 발화 앞 PRESERVE_BEFORE개 즉시 박제.

    뒤 PRESERVE_AFTER개는 세션 종료 시 finalize_crisis_preservation()이 append.

    호출 예시:
        await save_crisis_event(db, user_id, conv_id, session_id, severity)
    """
    from sqlalchemy import text
    from core.crypto import decrypt_content
    from models import Conversation
    from sqlalchemy.future import select
    import uuid as _uuid

    # W3: action_taken 듀얼 라이트 (변경 없음)
    action_taken_plain = "안내 문구 출력"
    at_bytes, at_kid = encrypt_content(action_taken_plain)

    # ── 즉시 박제: 위기 메시지 자체 포함 직전 PRESERVE_BEFORE개 ──
    # 동일 세션, 위기 메시지의 created_at 이하, soft delete 제외.
    trigger = (await db.execute(
        select(Conversation).where(Conversation.id == _uuid.UUID(conversation_id))
    )).scalar_one()

    rows = (await db.execute(
        select(Conversation)
        .where(
            Conversation.session_id == _uuid.UUID(session_id),
            Conversation.created_at <= trigger.created_at,
            Conversation.deleted_at.is_(None),
        )
        .order_by(Conversation.created_at.desc())
        .limit(PRESERVE_BEFORE)
    )).scalars().all()

    preserved = [
        {
            "message_id": str(m.id),
            "role": m.role,
            "content": decrypt_content(m.encrypted_content, m.encryption_key_id),
            "created_at": m.created_at.isoformat(),
            "is_trigger": str(m.id) == conversation_id,
        }
        for m in reversed(rows)  # 시간 오름차순으로 정렬
    ]
    pm_bytes, pm_kid = encrypt_json(preserved)

    query = text("""
        INSERT INTO crisis_events (
            id, user_id, conversation_id, crisis_score, severity,
            action_taken, action_taken_encrypted, action_taken_key_id,
            preserved_messages_encrypted, preserved_messages_key_id,
            guardian_notified, resolved, occurred_at
        ) VALUES (
            :id, :user_id, :conversation_id, :crisis_score, :severity,
            :action_taken, :action_taken_encrypted, :action_taken_key_id,
            :preserved_messages_encrypted, :preserved_messages_key_id,
            :guardian_notified, :resolved, :occurred_at
        )
    """)

    await db.execute(query, {
        "id":                            str(uuid.uuid4()),
        "user_id":                       user_id,
        "conversation_id":               conversation_id,
        "crisis_score":                  SEVERITY_SCORE_MAP.get(severity, 0.6),
        "severity":                      severity,
        "action_taken":                  action_taken_plain,
        "action_taken_encrypted":        at_bytes,
        "action_taken_key_id":           at_kid,
        "preserved_messages_encrypted":  pm_bytes,
        "preserved_messages_key_id":     pm_kid,
        "guardian_notified":             False,
        "resolved":                      False,
        "occurred_at":                   datetime.now(timezone.utc),
    })
    await db.commit()





# ──────────────────────────────────────────
# 세션 종료 후처리 — 위기 발화 이후 메시지 PRESERVE_AFTER개를 박제에 append
# - close_session_with_summary 끝부분에서 호출
# - 같은 세션의 모든 crisis_events 일괄 처리(idempotent: 항상 새로 박제하여 덮어쓰기)
# ──────────────────────────────────────────
async def finalize_crisis_preservation(session_id, db) -> None:
    """세션 내 모든 crisis_events에 대해 앞 PRESERVE_BEFORE + 뒤 PRESERVE_AFTER로 재박제."""
    from sqlalchemy import text, select
    from core.crypto import decrypt_content
    from models import CrisisEvent, Conversation
    import uuid as _uuid

    events = (await db.execute(
        select(CrisisEvent).where(CrisisEvent.conversation_id.in_(
            select(Conversation.id).where(
                Conversation.session_id == (
                    session_id if isinstance(session_id, _uuid.UUID)
                    else _uuid.UUID(str(session_id))
                )
            )
        ))
    )).scalars().all()

    for ev in events:
        trigger = (await db.execute(
            select(Conversation).where(Conversation.id == ev.conversation_id)
        )).scalar_one_or_none()
        if trigger is None:
            continue  # 트리거 conversation이 삭제됐다면 박제 그대로 유지

        # 앞 N개
        before_rows = (await db.execute(
            select(Conversation)
            .where(
                Conversation.session_id == trigger.session_id,
                Conversation.created_at <= trigger.created_at,
                Conversation.deleted_at.is_(None),
            )
            .order_by(Conversation.created_at.desc())
            .limit(PRESERVE_BEFORE)
        )).scalars().all()

        # 뒤 K개
        after_rows = (await db.execute(
            select(Conversation)
            .where(
                Conversation.session_id == trigger.session_id,
                Conversation.created_at > trigger.created_at,
                Conversation.deleted_at.is_(None),
            )
            .order_by(Conversation.created_at.asc())
            .limit(PRESERVE_AFTER)
        )).scalars().all()

        merged = list(reversed(before_rows)) + list(after_rows)
        preserved = [
            {
                "message_id": str(m.id),
                "role": m.role,
                "content": decrypt_content(m.encrypted_content, m.encryption_key_id),
                "created_at": m.created_at.isoformat(),
                "is_trigger": m.id == trigger.id,
            }
            for m in merged
        ]
        pm_bytes, pm_kid = encrypt_json(preserved)

        await db.execute(
            text("""
                UPDATE crisis_events
                   SET preserved_messages_encrypted = :pm_bytes,
                       preserved_messages_key_id    = :pm_kid
                 WHERE id = :id
            """),
            {"pm_bytes": pm_bytes, "pm_kid": pm_kid, "id": ev.id},
        )