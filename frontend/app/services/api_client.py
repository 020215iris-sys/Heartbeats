"""
백엔드 API 호출 레이어.
FastAPI 백엔드(API_BASE_URL)와 HTTP로 통신.
주소가 바뀌면 .env의 API_BASE_URL만 수정하면 됨.
"""

import requests
import uuid
from flask import current_app, session as flask_session


class SignupError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _base_url() -> str:
    return current_app.config["API_BASE_URL"]


def login(email: str, password: str, role: str) -> dict | None:
    """로그인. 성공 시 세션 payload 반환, 실패(인증 오류·서버 오류) 시 None."""
    try:
        res = requests.post(
            f"{_base_url()}/auth/login",
            json={"email": email, "password": password, "role": role},
            timeout=5,
        )
    except requests.RequestException:
        return None

    if not res.ok:
        return None

    data = res.json()
    return {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token"),
        "id": data["id"],
        "email": data["email"],
        "nickname": data["nickname"],
        "role": data["role"],
    }


def signup(
    email: str,
    password: str,
    role: str,
    nickname: str,
    phone_number: str,
    gender: str | None = None,
    birth_date: str | None = None,
) -> dict:
    """
    가입 성공 시 payload 반환.
    실패 시 SignupError(code=...) raise:
      - "email_taken": 이메일 중복
      - "phone_taken": 휴대폰 번호 중복
      - "server_error": 네트워크·서버 오류
    """
    try:
        res = requests.post(
            f"{_base_url()}/auth/signup",
            json={
                "email": email,
                "password": password,
                "role": role,
                "nickname": nickname,
                "phone_number": phone_number,
                "gender": gender,
                "birth_date": birth_date,
            },
            timeout=5,
        )
    except requests.RequestException as exc:
        raise SignupError("server_error") from exc

    if res.status_code == 409:
        raise SignupError(res.json().get("detail", "server_error"))
    if not res.ok:
        raise SignupError("server_error")

    data = res.json()
    return {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token"),
        "id": data["id"],
        "email": data["email"],
        "nickname": data["nickname"],
        "role": data["role"],
        "needs_guardian_link": data.get("needs_guardian_link", False),
    }


def send_chat_message(user_message: str, history: list, user_id: str | None) -> str:
    """
    AI 채팅 메시지 전송. 백엔드 /chat 호출 후 응답 텍스트 반환.
    연결 실패 시 안내 문구 반환.
    """
    from flask import session as flask_session

    # JWT 토큰 꺼내기 — 없으면 로그인 안 된 상태
    access_token = flask_session.get("access_token")
    # session_id 꺼내기 — 없으면 새로 만들어서 세션에 저장
    if "chat_session_id" not in flask_session:
        flask_session["chat_session_id"] = str(uuid.uuid4())
    chat_session_id = flask_session["chat_session_id"]

    if not access_token:
        return "이야기해주셔서 감사해요. 체험 모드에서는 임시 응답이에요. 회원가입 후 실제 AI와 대화해보세요."

    try:
        res = requests.post(
            f"{_base_url()}/counseling/chat",
            json={
                "message": user_message,
                "session_id": chat_session_id,  # 백엔드 필수값
                "history": [{"role": h["role"], "content": h["content"]} for h in history],
            },
            headers={
                "Authorization": f"Bearer {access_token}"  # JWT 인증
            },
            timeout=15,
        )
        if res.ok:
            return res.json().get("reply", "응답을 받지 못했어요.")
        # 401이면 refresh 시도
        if res.status_code == 401:
            refresh_token = flask_session.get("refresh_token")
            if refresh_token:
                try:
                    r = requests.post(
                        f"{_base_url()}/auth/refresh",
                        json={"refresh_token": refresh_token},
                        timeout=5,
                    )
                    if r.ok:
                        # 새 access_token 저장 후 원래 요청 재시도
                        flask_session["access_token"] = r.json()["access_token"]
                        flask_session["chat_session_id"] = str(uuid.uuid4())
                        chat_session_id = flask_session["chat_session_id"]
                        retry = requests.post(
                            f"{_base_url()}/counseling/chat",
                            json={
                                "message": user_message,
                                "session_id": chat_session_id,
                                "history": history,
                            },
                            headers={"Authorization": f"Bearer {flask_session['access_token']}"},
                            timeout=15,
                        )
                        if retry.ok:
                            return retry.json().get("reply", "응답을 받지 못했어요.")
                except requests.RequestException:
                    pass
            # refresh도 실패 → 로그아웃 처리
            flask_session.clear()
            return "로그인이 만료됐어요. 다시 로그인해주세요."
    except requests.RequestException:
        pass
    return "현재 서버에 연결할 수 없어요. 잠시 후 다시 시도해주세요."


def get_active_survey() -> dict | None:
    """백엔드에서 활성 설문 정의 조회. GET /surveys/active"""
    try:
        res = requests.get(f"{_base_url()}/surveys/active", timeout=5)
        if res.ok:
            return res.json()
    except requests.RequestException:
        pass
    return None


def submit_survey(answers: list[int]) -> dict | None:
    """설문 답변 제출·채점·저장. POST /surveys/active/responses (로그인 필요)"""
    token = flask_session.get("access_token")
    if not token:
        return None
    try:
        res = requests.post(
            f"{_base_url()}/surveys/active/responses",
            json={"answers": answers},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if res.ok:
            return res.json()
    except requests.RequestException:
        pass
    return None

def logout(refresh_token: str, access_token: str) -> None:
    """
    백엔드에 로그아웃 요청. 요약 저장 + refresh_token 만료 처리.
    백엔드 실패해도 프론트 로그아웃은 진행되므로 예외 무시.
    """
    try:
        requests.post(
            f"{_base_url()}/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
    except requests.RequestException:
        pass

def get_sessions(limit: int | None = None) -> list:
    """내 상담 세션 목록. GET /counseling/sessions"""
    token = flask_session.get("access_token")
    if not token:
        return []
    try:
        res = requests.get(
            f"{_base_url()}/counseling/sessions",
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": limit} if limit else {},
            timeout=10,
        )
        if res.ok:
            return res.json().get("sessions", [])
    except requests.RequestException:
        pass
    return []

def get_session_messages(session_id: str) -> list:
    """세션 대화 조회. GET /counseling/sessions/{id}/messages (복호화 평문)"""
    token = flask_session.get("access_token")
    if not token:
        return []
    try:
        res = requests.get(
            f"{_base_url()}/counseling/sessions/{session_id}/messages",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if res.ok:
            return res.json().get("messages", [])
    except requests.RequestException:
        pass
    return []