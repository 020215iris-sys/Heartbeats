"""
회원 정보 CSV 저장소 (MVP 임시).
ERD의 USERS 테이블과 동일한 필드명을 사용해서, 백엔드 붙을 때 매핑 손실 없게 함.

향후 송지현 님 FastAPI + PostgreSQL로 옮겨갈 영역.
교체 시 이 파일의 공개 함수 시그니처는 그대로, 내부 구현만 requests.post(...)로 교체.

CSV 컬럼 (USERS 테이블과 1:1 매핑):
    id, email, nickname, hashed_password, phone_number, role,
    is_active, created_at, last_login_at, deleted_at
"""

import csv
import os
import uuid
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash


# CSV 파일 경로 (frontend/data/users.csv)
CSV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "users.csv",
)

# ERD의 USERS 컬럼 순서. 백엔드 마이그레이션 시 그대로 매핑됨
FIELDNAMES = [
    "id",
    "email",
    "nickname",
    "hashed_password",
    "phone_number",
    "role",
    "is_active",
    "created_at",
    "last_login_at",
    "deleted_at",
]


def _now() -> str:
    """현재 시각 UTC ISO 8601 문자열. PostgreSQL timestamp와 호환."""
    return datetime.now(timezone.utc).isoformat()


def _ensure_file_exists() -> None:
    """users.csv가 없으면 헤더만 있는 빈 파일을 만듦."""
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=FIELDNAMES).writeheader()


def _read_all() -> list[dict]:
    """CSV 전체를 dict 리스트로 읽어옴."""
    _ensure_file_exists()
    with open(CSV_PATH, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_all(rows: list[dict]) -> None:
    """
    CSV 전체를 덮어쓰기. last_login_at 같은 업데이트 작업에 사용.
    임시 파일 → rename 패턴으로 쓰면 더 안전하지만, MVP에선 단순화.
    """
    _ensure_file_exists()
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def _sanitize_user(user: dict) -> dict:
    """
    응답에서 password_hash 제거.
    세션·로그·HTTP 응답 등 어디에도 비번 해시가 노출 안 되게.
    """
    return {k: v for k, v in user.items() if k != "hashed_password"}


# ========== 공개 API (라우트/api_client에서 호출) ==========


def find_by_email(email: str) -> dict | None:
    """이메일로 사용자 1명 찾기. deleted_at이 있는 계정은 제외."""
    for row in _read_all():
        if row["email"] == email and not row.get("deleted_at"):
            return row
    return None


def email_exists(email: str) -> bool:
    """가입 시 중복 체크용."""
    return find_by_email(email) is not None


def create_user(
    email: str,
    password: str,
    nickname: str,
    role: str,
    phone_number: str,
) -> dict:
    """
    새 사용자 추가.
    - 비밀번호는 받자마자 해시. 평문은 절대 CSV에 안 들어감
    - id는 UUID로 생성 (ERD가 uuid 타입이라서)
    - 반환값에 hashed_password는 포함 안 됨 
    """
    new_user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "nickname": nickname,
        "hashed_password": generate_password_hash(password),
        # 빈 값은 빈 문자열로. CSV는 None을 저장 못 하니까
        "phone_number": phone_number,
        "role": role,
        # CSV는 boolean도 문자열로. "True"/"False"로 통일
        "is_active": "True",
        "created_at": _now(),
        "last_login_at": "",     # 가입 직후엔 비어있음
        "deleted_at": "",        # 활성 계정이므로 비어있음
    }

    _ensure_file_exists()
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=FIELDNAMES).writerow(new_user)

    return _sanitize_user(new_user)


def verify_password(email: str, password: str) -> dict | None:
    """
    로그인 검증. 성공 시 사용자 정보 반환 + last_login_at 갱신.
    실패 시 None.
    """
    user = find_by_email(email)
    if user is None:
        return None
    if user.get("is_active") != "True":
        return None  # 비활성 계정 로그인 차단
    if not check_password_hash(user["hashed_password"], password):
        return None

    # 로그인 성공 시 last_login_at 갱신
    rows = _read_all()
    for row in rows:
        if row["id"] == user["id"]:
            row["last_login_at"] = _now()
            break
    _write_all(rows)

    user["last_login_at"] = _now()
    return _sanitize_user(user)


def soft_delete(user_id: str) -> bool:
    """
    소프트 삭제: deleted_at에 시각 기록, is_active를 False로.
    실제 데이터는 남기되 find_by_email에서 제외됨.
    탈퇴 기능 만들 때 호출. 지금은 정의만.
    """
    rows = _read_all()
    for row in rows:
        if row["id"] == user_id:
            row["is_active"] = "False"
            row["deleted_at"] = _now()
            _write_all(rows)
            return True
    return False

def phone_exists(phone_number: str) -> bool:
    """같은 번호로 가입된 활성 계정 존재 여부."""
    for row in _read_all():
        if row["phone_number"] == phone_number and not row.get("deleted_at"):
            return True
    return False