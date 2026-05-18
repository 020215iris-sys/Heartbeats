from flask import current_app
import requests


# ========== MOCK: 백엔드 붙기 전 임시 응답 ==========
# 진짜 백엔드 연결되면 _mock_* 호출 부분만 갈아끼우면 됨


def _mock_login(email: str, password: str, role: str) -> dict | None:
    """이메일/비번/역할이 정상 형식이면 가짜 토큰 발급"""
    if email and password and len(password) >= 8:
        return {
            "access_token": f"mock-{role}-token-for-{email}",
            "role": role,
        }
    return None


def _mock_signup(email: str, password: str, role: str) -> dict | None:
    """가짜 회원가입. 'taken@test.com'은 이미 가입된 것처럼 처리"""
    if email == "taken@test.com":
        return None
    return {
        "access_token": f"mock-{role}-token-for-{email}",
        "role": role,
        # 보호자는 가입 후 사용자 연결 필요 (Step 14에서 활용)
        "needs_guardian_link": role == "guardian",
    }


# ========== 공개 함수 (라우트에서 이걸 호출) ==========


def login(email: str, password: str, role: str) -> dict | None:
    """
    로그인 시도.
    성공 시 {"access_token": "...", "role": "..."} 반환, 실패 시 None.
    """
    # TODO: 백엔드 붙으면 아래 주석 풀고 mock 호출 삭제
    # res = requests.post(
    #     f"{current_app.config['API_BASE_URL']}/auth/login",
    #     json={"email": email, "password": password, "role": role},
    #     timeout=5,
    # )
    # if res.status_code == 200:
    #     return res.json()
    # return None
    return _mock_login(email, password, role)


def signup(email: str, password: str, role: str) -> dict | None:
    """회원가입. 성공 시 토큰+역할 반환, 실패 시 None."""
    # TODO: 백엔드 붙으면 진짜 요청으로 교체
    return _mock_signup(email, password, role)