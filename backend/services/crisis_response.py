import uuid
from datetime import datetime, timezone

# -----------------------------------------------------------------------
# 안내 문구 정의
# severity에 따라 다른 문구 반환
# -----------------------------------------------------------------------
CRISIS_MESSAGES = {
    "critical": (
        "지금 많이 힘드신 것 같아서 걱정이 돼요. "
        "지금 바로 도움을 받으실 수 있어요.\n\n"
        "📞 자살예방상담전화: 1393 (24시간)\n"
        "📞 정신건강위기상담전화: 1577-0199\n"
        "📞 긴급신고: 119\n\n"
        "지금 안전한가요?"
    ),
    "high": (
        "많이 힘드신 것 같아서 걱정돼요. "
        "혼자 감당하기 어려우실 때는 전문가의 도움을 받는 것도 방법이에요.\n\n"
        "📞 자살예방상담전화: 1393 (24시간)\n\n"
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

    query = text("""
        INSERT INTO crisis_events (
            id,
            user_id,
            conversation_id,
            crisis_score,
            severity,
            action_taken,
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
            :guardian_notified,
            :resolved,
            :occurred_at
        )
    """)

    await db.execute(query, {
        "id":                str(uuid.uuid4()),
        "user_id":           user_id,
        "conversation_id":   conversation_id,
        "crisis_score":      1.0,
        "severity":          severity,
        "action_taken":      "안내 문구 출력",
        "guardian_notified": False,   # 추후 보호자 알림 연동 시 변경
        "resolved":          False,
        "occurred_at":       datetime.now(timezone.utc),
    })
    await db.commit()
