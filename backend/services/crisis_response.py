import uuid
from datetime import datetime, timezone

from core.crypto import encrypt_content

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
    severity: str,
) -> None:
    """
    crisis_events 테이블에 위기 이벤트를 저장한다.

    호출 예시:
        await save_crisis_event(db, user_id, conversation_id, detection_result)
    """
    from sqlalchemy import text

    # W3: action_taken 듀얼 라이트
    # 현재는 "안내 문구 출력" 고정값이지만, 향후 보호자 번호·이름 등 PII가
    # 들어갈 예정이므로 미리 암호화 인프라를 깔아둔다.
    action_taken_plain = "안내 문구 출력"
    at_bytes, at_kid = encrypt_content(action_taken_plain)

    query = text("""
        INSERT INTO crisis_events (
            id,
            user_id,
            conversation_id,
            crisis_score,
            severity,
            action_taken,
            action_taken_encrypted,
            action_taken_key_id,
            guardian_notified,
            resolved,
            occurred_at
        ) VALUES (
            :id,
            :user_id,
            :conversation_id,
            :crisis_score,
            :severity,
            :action_taken,
            :action_taken_encrypted,
            :action_taken_key_id,
            :guardian_notified,
            :resolved,
            :occurred_at
        )
    """)

    await db.execute(query, {
        "id":                     str(uuid.uuid4()),
        "user_id":                user_id,
        "conversation_id":        conversation_id,
        "crisis_score":           SEVERITY_SCORE_MAP.get(severity, 0.6),
        "severity":                severity,
        "action_taken":            action_taken_plain,   # 옛 평문 (듀얼 라이트)
        "action_taken_encrypted":  at_bytes,             # W3
        "action_taken_key_id":     at_kid,               # W3
        "guardian_notified":       False,
        "resolved":                False,
        "occurred_at":             datetime.now(timezone.utc),
    })
    await db.commit()
