"""
상담사 페르소나 정의.

ERD의 COUNSELING_SESSIONS.persona_type ("empathy/coaching/neutral") 와 동기.
백엔드가 페르소나 코드로 LLM 프롬프트 전략을 분기할 때 같은 식별자 공유.

확장 시:
    - 새 페르소나 추가는 PERSONAS dict에 항목만 추가
    - 사용자 페르소나 선택 기능 만들 때는 session["persona_code"] 사용
    - 추후 일러스트 이미지가 생기면 avatar_image 필드 추가
"""

# 페르소나 데이터.
# avatar_emoji는 MVP용 임시. 추후 SVG/이미지로 교체.
PERSONAS = {
    "empathy": {
        "code": "empathy",
        "name": "다온",
        "tagline": "공감과 경청 중심",
        "greeting": "안녕하세요. 오늘은 어떤 이야기를 들려주실래요?",
        "avatar_emoji": "🌱",
        "accent_color": "brand",   # Tailwind 클래스 prefix
        "params": {"말수": 5, "공감도": 8, "따듯함": 9, "전문성": 6, "직접성": 3},
    },
    "coaching": {
        "code": "coaching",
        "name": "라온",
        "tagline": "실행 중심 코칭",
        "greeting": "반가워요. 무엇을 함께 정리해볼까요?",
        "avatar_emoji": "✨",
        "accent_color": "amber",
    },
    "neutral": {
        "code": "neutral",
        "name": "온유",
        "tagline": "중립적 안내",
        "greeting": "환영합니다. 편하게 말씀해주세요.",
        "avatar_emoji": "💧",
        "accent_color": "slate",
    },
}

DEFAULT_PERSONA_CODE = "empathy"


def get_persona(code: str | None = None) -> dict:
    """
    페르소나 dict 반환. code가 None이거나 없는 코드면 기본값.
    """
    if not code or code not in PERSONAS:
        code = DEFAULT_PERSONA_CODE
    return PERSONAS[code]

# ──────────────────────────────────────────────
# v2 커스텀 페르소나 (2026-06 개편)
# 백엔드 counseling_sessions.persona_type 스키마와 1:1 동기.
# 위의 PERSONAS dict는 v1 구형 데이터 변환용으로만 유지.
# ──────────────────────────────────────────────

# 신규 사용자(이전 세션 없음)의 기본 페르소나.
# ⚠️ 백엔드 DEFAULT_PERSONA 상수와 값을 맞출 것 (계약 문서 참고)
DEFAULT_PERSONA = {
    "name": "다온",
    "avatar_emoji": "🌱",
    "talk_type": "존댓말",
    "voice_type": "voice_1",
    "params": {"말수": 5, "공감도": 7, "따듯함": 7, "전문성": 5},
}

# 검증용 허용값 — 백엔드 검증 규칙과 동일하게 유지 (프론트는 1차 방어선일 뿐,
# 최종 검증은 백엔드 책임. 여기서 거르는 건 UX용)
ALLOWED_PARAM_KEYS = ("말수", "공감도", "따듯함", "전문성")
ALLOWED_TALK_TYPES = ("반말", "존댓말")
ALLOWED_VOICE_TYPES = ("voice_1", "voice_2")  # TTS 확정 시 갱신
ALLOWED_EMOJIS = ("🌱", "✨", "💧", "🌷", "🌙", "🍀", "🐰", "⭐")  # 팝업 프리셋과 동일하게
NAME_MAX_LEN = 20


def _has_batchim(word: str) -> bool:
    """마지막 글자 받침 유무 (조사 '야/이야', '예요/이에요' 선택용). 한글 아니면 False."""
    if not word:
        return False
    ch = word[-1]
    if not ("가" <= ch <= "힣"):
        return False
    return (ord(ch) - ord("가")) % 28 != 0


def normalize_persona(value) -> dict:
    """
    어떤 형태의 persona 값이 와도 완전한 v2 dict로 정규화.

    처리 케이스:
    1. None / dict 아님        → DEFAULT_PERSONA 복사본
    2. v1 구형 {"code": ...}   → 옛 프리셋에서 이름·이모지만 승계, 나머지 기본값
                                 (DB에 남아있는 옛 세션의 persona_type 읽을 때 발생)
    3. v2 dict                 → 필드별 검증 후 병합, 누락·이상값은 기본값으로

    호출부는 반환값이 항상 완전한 v2 dict임을 신뢰해도 됨.
    항상 새 dict를 반환하므로 수정해도 DEFAULT_PERSONA가 오염되지 않음.
    """
    # 깊은 복사 (params가 내부 dict라서 dict()만으론 공유됨)
    base = {k: (dict(v) if isinstance(v, dict) else v) for k, v in DEFAULT_PERSONA.items()}

    if not isinstance(value, dict):
        return base

    # ── v1 구형 변환 ──
    if "code" in value:
        old = get_persona(value.get("code"))
        base["name"] = old["name"]
        base["avatar_emoji"] = old["avatar_emoji"]
        return base

    # ── v2 필드별 검증 병합 ──
    name = str(value.get("name") or "").strip()
    if 0 < len(name) <= NAME_MAX_LEN:
        base["name"] = name

    if value.get("avatar_emoji") in ALLOWED_EMOJIS:
        base["avatar_emoji"] = value["avatar_emoji"]

    if value.get("talk_type") in ALLOWED_TALK_TYPES:
        base["talk_type"] = value["talk_type"]

    if value.get("voice_type") in ALLOWED_VOICE_TYPES:
        base["voice_type"] = value["voice_type"]

    params = value.get("params")
    if isinstance(params, dict):
        for key in ALLOWED_PARAM_KEYS:
            try:
                # 슬라이더 값은 문자열("7")로 올 수 있어 int 변환 → 1~10 클램프
                base["params"][key] = min(10, max(1, int(params[key])))
            except (KeyError, TypeError, ValueError):
                pass  # 누락·변환 실패 → 기본값 유지

    return base


def build_greeting(persona: dict) -> str:
    """
    페르소나 이름·말투에 맞는 첫 인사말 생성.
    v2 스키마엔 greeting 필드가 없으므로 템플릿 문구로 조립.
    받침에 따라 조사가 달라짐: '봄이야' vs '라온이야' → _has_batchim으로 분기.
    """
    name = persona.get("name", DEFAULT_PERSONA["name"])
    if persona.get("talk_type") == "반말":
        josa = "이야" if _has_batchim(name) else "야"
        return f"안녕, 나는 {name}{josa}. 오늘은 어떤 이야기를 하고 싶어?"
    josa = "이에요" if _has_batchim(name) else "예요"
    return f"안녕하세요, 저는 {name}{josa}. 오늘은 어떤 이야기를 들려주실래요?"