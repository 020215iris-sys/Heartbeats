"""
비회원(게스트) 체험 모드 헬퍼.
세션 쿠키로 게스트 상태와 메시지 카운트를 추적함.
브라우저 쿠키를 지우면 카운트가 리셋되지만, MVP에선 그 정도면 충분.
(완전한 차단이 목적이 아니라 "회원가입 유도" 깔때기가 목적)
"""

from flask import session, current_app


def start_guest_session() -> None:
    """게스트 모드 시작. 랜딩의 '익명으로 시작하기' 버튼 클릭 시 호출."""
    # 이미 게스트 상태면 카운트 유지 (체험 중 새로고침해도 리셋 안 됨)
    if not session.get("guest_active"):
        session["guest_active"] = True
        session["guest_message_count"] = 0


def end_guest_session() -> None:
    """게스트 모드 종료. 회원가입/로그인 성공 시 호출하면 됨."""
    session.pop("guest_active", None)
    session.pop("guest_message_count", None)


def is_guest() -> bool:
    """현재 요청이 비회원 체험 상태인지."""
    # access_token이 있으면 회원이므로 guest 아님
    if "access_token" in session:
        return False
    return session.get("guest_active") is True


def get_message_count() -> int:
    """현재까지 보낸 게스트 메시지 수."""
    return session.get("guest_message_count", 0)


def get_remaining_messages() -> int:
    """남은 게스트 메시지 수. 0 이하면 더 못 보냄."""
    limit = current_app.config["GUEST_MESSAGE_LIMIT"]
    return max(0, limit - get_message_count())


def can_send_message() -> bool:
    """게스트가 메시지를 더 보낼 수 있는지."""
    return get_remaining_messages() > 0


def increment_message_count() -> int:
    """
    메시지 하나 보냈음을 기록. 채팅 라우트에서 메시지 받을 때마다 호출.
    반환값은 증가 후의 카운트.
    """
    count = get_message_count() + 1
    session["guest_message_count"] = count
    return count