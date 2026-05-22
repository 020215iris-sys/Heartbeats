"""
백엔드 API 호출 레이어.
지금은 user_storage(CSV)를 백엔드처럼 다루는 MVP 구현.
나중에 송지현 님 FastAPI 붙으면 user_storage 호출을 requests.post(...)로 교체.
"""

import secrets
from . import user_storage
from . import diagnosis_storage

class SignupError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)

def _generate_token(role: str) -> str:
    """임시 세션 토큰. 진짜 백엔드 붙으면 JWT 발급은 백엔드가 함."""
    return f"local-{role}-{secrets.token_urlsafe(16)}"


def _build_session_payload(user: dict) -> dict:
    """라우트가 세션에 저장할 형태로 변환."""
    return {
        "access_token": _generate_token(user["role"]),
        "id": user["id"],
        "email": user["email"],
        "nickname": user["nickname"],
        "role": user["role"],
    }


def login(email: str, password: str, role: str) -> dict | None:
    """로그인. 이메일·비번·역할 검증."""
    user = user_storage.verify_password(email, password)
    if user is None:
        return None
    # 가입 시 역할과 로그인 시 역할 불일치 차단
    if user["role"] != role:
        return None
    return _build_session_payload(user)


def signup(
    email: str,
    password: str,
    role: str,
    nickname: str,
    phone_number: str,
) -> dict: 
    """
    가입 성공 시 payload 반환.
    실패 시 SignupError(code=...) 를 raise:
      - "email_taken": 이메일 중복
      - "phone_taken": 휴대폰 번호 중복
    """
    if user_storage.email_exists(email):
        raise SignupError("email_taken")
    if user_storage.phone_exists(phone_number):
        raise SignupError("phone_taken")

    user = user_storage.create_user(
        email=email,
        password=password,
        nickname=nickname,
        role=role,
        phone_number=phone_number,
    )

    payload = _build_session_payload(user)
    payload["needs_guardian_link"] = (role == "guardian")
    return payload

def save_diagnosis(
    user_id: str | None,
    instrument_code: str,
    scores: dict,
    severities: dict,
    follow_ups: list,
) -> dict:
    """
    진단 결과 저장.
    백엔드 붙으면 requests.post(...)로 교체. 호출하는 라우트는 손 안 댐.
    """
    # TODO: 백엔드 붙으면 아래로 교체
    # res = requests.post(
    #     f"{current_app.config['API_BASE_URL']}/diagnoses",
    #     json={
    #         "user_id": user_id,
    #         "instrument_code": instrument_code,
    #         "scores": scores,
    #         "severities": severities,
    #         "follow_ups": follow_ups,
    #     },
    #     headers={"Authorization": f"Bearer {session.get('access_token')}"},
    #     timeout=5,
    # )
    # return res.json()

    return diagnosis_storage.save(
        user_id=user_id,
        instrument_code=instrument_code,
        scores=scores,
        severities=severities,
        follow_ups=follow_ups,
    )


def get_latest_diagnosis(user_id: str) -> dict | None:
    """사용자의 가장 최근 진단 조회. 채팅 페이지에서 페르소나 결정 시 사용 예정."""
    # TODO: 백엔드 붙으면 requests.get(...)로 교체
    return diagnosis_storage.find_latest_by_user(user_id)