"""
백엔드 API 호출 레이어.
지금은 user_storage(CSV)를 백엔드처럼 다루는 MVP 구현.
나중에 송지현 님 FastAPI 붙으면 user_storage 호출을 requests.post(...)로 교체.
"""

import secrets
from . import user_storage


def _generate_token(role: str) -> str:
    """임시 세션 토큰. 진짜 백엔드 붙으면 JWT 발급은 백엔드가 함."""
    return f"local-{role}-{secrets.token_urlsafe(16)}"


def _build_session_payload(user: dict) -> dict:
    """라우트가 세션에 저장할 형태로 변환. ERD 필드명 그대로 사용."""
    return {
        "access_token": _generate_token(user["role"]),
        "id": user["id"],
        "email": user["email"],
        "nickname": user["nickname"],
        "role": user["role"],
    }


def login(email: str, password: str, role: str) -> dict | None:
    """
    로그인. 이메일·비번 검증 + 역할 일치 확인.
    성공 반환: {access_token, id, email, nickname, role}
    """
    # TODO: 백엔드 붙으면 아래 주석 풀고 위 로직 삭제
    # res = requests.post(f"{current_app.config['API_BASE_URL']}/auth/login",
    #                     json={...}, timeout=5)
    # return res.json() if res.status_code == 200 else None

    user = user_storage.verify_password(email, password)
    if user is None:
        return None
    # 가입 시 등록한 역할과 다르면 거부 (사용자 계정으로 보호자 로그인 차단)
    if user["role"] != role:
        return None
    return _build_session_payload(user)


def signup(
    email: str,
    password: str,
    role: str,
    nickname: str,
    phone_number: str,
) -> dict | None:
    """
    회원가입. 이메일 중복 체크 후 user_storage에 저장.
    실패 케이스: 이미 존재하는 이메일.
    """
    # TODO: 백엔드 붙으면 진짜 요청으로 교체

    if user_storage.email_exists(email):
        return None
    if user_storage.phone_exists(phone_number):
            return None
    user = user_storage.create_user(
        email=email,
        password=password,
        nickname=nickname,
        role=role,
        phone_number=phone_number,
    )

    payload = _build_session_payload(user)
    # 보호자는 가입 후 GUARDIAN_CONSENTS 연결 절차 필요
    payload["needs_guardian_link"] = (role == "guardian")
    return payload