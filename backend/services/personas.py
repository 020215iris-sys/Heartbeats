from typing import Any


# ── v1 구형 호환 (DB에 남아있는 옛 세션 데이터용) ──
# v2 전환 후 신규 세션엔 쓰이지 않음. 읽기 전용.
_V1_PERSONAS = {
    "empathy":  {"name": "다온", "avatar_emoji": "🌱"},
    "coaching": {"name": "라온", "avatar_emoji": "✨"},
    "neutral":  {"name": "온유", "avatar_emoji": "💧"},
}
DEFAULT_PERSONA_CODE = "empathy"  # v1 폴백용으로만 남김

# ──────────────────────────────────────────────
# v2 커스텀 페르소나 상수
# 프론트의 DEFAULT_PERSONA와 값을 맞출 것 (계약 문서 참고)
# ──────────────────────────────────────────────
DEFAULT_PERSONA: dict[str, Any] = {
    "name": "다온",
    "avatar_emoji": "🌱",
    "talk_type": "존댓말",
    "voice_type": "voice_1",
    "params": {"말수": 5, "공감도": 7, "따듯함": 7, "전문성": 5},
}

# 검증용 허용값 (프론트와 동기화 유지)
ALLOWED_PARAM_KEYS = frozenset({"말수", "공감도", "따듯함", "전문성"})
ALLOWED_TALK_TYPES = frozenset({"반말", "존댓말"})
ALLOWED_VOICE_TYPES = frozenset({"voice_1", "voice_2"})  # TTS 확정 시 갱신
ALLOWED_EMOJIS = frozenset({"🌱", "✨", "💧", "🌷", "🌙", "🍀", "🐰", "⭐"})
NAME_MAX_LEN = 20

def normalize_persona(value: Any) -> dict[str, Any]:
    """
    어떤 형태의 persona 값이 와도 완전한 v2 dict로 정규화.

    케이스:
    1. None / dict 아님        → DEFAULT_PERSONA 복사본
    2. v1 구형 {"code": ...}   → 이름·이모지만 승계, 나머지 기본값
    3. v2 dict                 → 필드별 검증 후 병합, 누락·이상값은 기본값

    항상 새 dict 반환 → DEFAULT_PERSONA 오염 없음.
    호출부는 반환값이 항상 완전한 v2임을 신뢰해도 됨.
    """
    # 깊은 복사 (params가 중첩 dict)
    base: dict[str, Any] = {
        k: (dict(v) if isinstance(v, dict) else v)
        for k, v in DEFAULT_PERSONA.items()
    }

    if not isinstance(value, dict):
        return base

    # ── v1 구형 변환 ──
    if "code" in value:
        old = _V1_PERSONAS.get(value["code"], _V1_PERSONAS[DEFAULT_PERSONA_CODE])
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
                # 문자열로 올 수 있으니 int 변환 → 1~10 클램프
                base["params"][key] = min(10, max(1, int(params[key])))
            except (KeyError, TypeError, ValueError):
                pass  # 누락·변환 실패 → 기본값 유지

    return base
