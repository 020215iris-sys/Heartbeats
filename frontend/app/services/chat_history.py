"""이전 채팅 목록 (백엔드 연동 전 임시 더미).
TODO: 백엔드 GET /counseling/sessions 연동 시 이 함수 본문만 교체.
"""

_MOCK_CHATS = [
    {"id": "sess-1", "persona": "다온", "emoji": "🌱", "date": "2026년 6월 3일",
     "preview": "무기력과 우울감이 한 달 넘게 이어지고 있어요.", "msg_count": 12},

    {"id": "sess-2", "persona": "다온", "emoji": "🌱", "date": "2026년 5월 28일",
     "preview": "시험 스트레스 때문에 잠을 잘 못 자고 있어요.", "msg_count": 6},

    {"id": "sess-3", "persona": "다온", "emoji": "🌱", "date": "2026년 5월 20일",
     "preview": "산책 이후 기분이 조금 나아진 경험을 이야기했어요.", "msg_count": 5},

    {"id": "sess-4", "persona": "다온", "emoji": "🌱", "date": "2026년 5월 12일",
     "preview": "친구와 다툰 이후 감정 정리가 안 되고 있어요.", "msg_count": 8},

    {"id": "sess-5", "persona": "다온", "emoji": "🌱", "date": "2026년 5월 5일",
     "preview": "미래에 대한 불안 때문에 집중이 안 돼요.", "msg_count": 7},

    {"id": "sess-6", "persona": "다온", "emoji": "🌱", "date": "2026년 4월 30일",
     "preview": "요즘은 그래도 조금 괜찮아진 것 같아요.", "msg_count": 4},
]


def get_recent_chats(limit: int | None = None) -> list[dict]:
    """최근순 채팅 목록. limit이 있으면 그 개수만."""
    return _MOCK_CHATS[:limit] if limit else _MOCK_CHATS

_MOCK_MESSAGES = {
    "sess-1": [
    {"role": "user", "content": "요즘 계속 무기력해요"},
    {"role": "assistant", "content": "무기력이 오래 지속되면 많이 지치셨을 것 같아요."},
    {"role": "assistant", "content": "언제부터 그런 느낌이 시작됐는지 기억나시나요?"},
    {"role": "user", "content": "한 달 정도 된 것 같아요"},
    {"role": "user", "content": "아무것도 하기 싫어요"},
    {"role": "assistant", "content": "그럴 때는 아주 작은 행동도 버겁게 느껴질 수 있어요."},
    {"role": "assistant", "content": "최근에 그나마 덜 힘들었던 순간은 있었을까요?"},
    {"role": "user", "content": "친구 만났을 때는 조금 괜찮았어요"},
    {"role": "assistant", "content": "그 경험이 중요한 단서일 수 있어요."},
    {"role": "assistant", "content": "이번 주에 짧게라도 사람을 만나는 계획을 세워볼까요?"},
    {"role": "user", "content": "가능할 것 같아요"},
    {"role": "assistant", "content": "좋아요. 너무 무리하지 않는 선에서 시도해보세요."},
    ],
    "sess-2": [
    {"role": "user", "content": "시험 때문에 잠을 못 자요"},
    {"role": "assistant", "content": "잠을 못 자면 더 불안해지기 쉽죠."},
    {"role": "assistant", "content": "잠들기 전에 어떤 생각이 가장 많이 떠오르나요?"},
    {"role": "user", "content": "망칠까 봐 계속 생각나요"},
    {"role": "assistant", "content": "그 생각이 반복되면 몸도 긴장 상태를 유지하게 됩니다."},
    {"role": "assistant", "content": "짧은 호흡 정리나 기록으로 생각을 밖으로 꺼내보는 건 도움이 될 수 있어요."},
    ],
    "sess-3": [
    {"role": "user", "content": "오늘 산책했는데 기분이 좀 나아졌어요"},
    {"role": "assistant", "content": "좋은 변화네요. 몸을 움직인 게 영향을 준 것 같아요."},
    {"role": "assistant", "content": "산책하면서 어떤 점이 가장 좋았나요?"},
    {"role": "user", "content": "생각이 좀 정리됐어요"},
    {"role": "assistant", "content": "그 경험을 반복할 수 있도록 루틴으로 만들어보는 것도 좋겠습니다."},
    ],
    "sess-4": [
    {"role": "user", "content": "친구랑 싸웠어요"},
    {"role": "assistant", "content": "마음이 많이 복잡하셨을 것 같아요."},
    {"role": "assistant", "content": "어떤 상황이었는지 조금 더 이야기해 주실 수 있을까요?"},
    {"role": "user", "content": "제가 너무 예민하게 반응했어요"},
    {"role": "assistant", "content": "그렇게 느끼셨군요."},
    {"role": "assistant", "content": "지금은 친구에게 어떤 마음이 드시나요?"},
    {"role": "user", "content": "미안한데 연락하기가 어려워요"},
    {"role": "assistant", "content": "짧은 메시지로 감정을 전달하는 것부터 시작해도 괜찮습니다."},
    ],
    "sess-5": [
    {"role": "user", "content": "앞으로가 너무 불안해요"},
    {"role": "assistant", "content": "미래에 대한 불안은 누구나 느낄 수 있는 감정입니다."},
    {"role": "assistant", "content": "특히 어떤 부분이 가장 걱정되나요?"},
    {"role": "user", "content": "취업이요"},
    {"role": "assistant", "content": "구체적인 걱정이네요."},
    {"role": "assistant", "content": "현재 준비하고 있는 것들을 한번 정리해볼까요?"},
    {"role": "user", "content": "정리하면 조금 나을 것 같아요"},
    ],
    "sess-6": [
    {"role": "user", "content": "요즘은 좀 괜찮아요"},
    {"role": "assistant", "content": "좋은 변화네요."},
    {"role": "assistant", "content": "어떤 점이 달라졌다고 느끼시나요?"},
    {"role": "user", "content": "생활이 좀 규칙적이 됐어요"},
    ],
}


def get_chat(chat_id: str) -> dict | None:
    """id로 채팅 메타(날짜·페르소나 등) 하나 반환."""
    return next((c for c in _MOCK_CHATS if c["id"] == chat_id), None)


def get_chat_messages(chat_id: str) -> list[dict]:
    """id로 그 대화 메시지 목록 반환(더미)."""
    return _MOCK_MESSAGES.get(chat_id, [
        {"role": "assistant", "content": "이 대화의 기록은 백엔드 연동 후 표시됩니다."},
    ])