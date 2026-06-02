"""
채팅 라우트.

흐름:
    GET  /chat/        → 메시지 리스트 + 입력 폼 표시
    POST /chat/        → 메시지 받기 → mock AI 응답 → redirect (PRG)
    POST /chat/clear   → 대화 초기화

접근 권한:
    - authenticated: 무제한
    - guest: GUEST_MESSAGE_LIMIT 까지
    - anonymous: 차단 (랜딩으로 안내)

⚠️ 메시지 영구 저장은 백엔드 영역.
   여기선 세션에만 임시 보관 — 새로고침은 살아남지만 로그아웃하면 사라짐.
   실제 운영에선 CONVERSATIONS 테이블(민감 DB)에 암호화 저장됨.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, session, request, jsonify
from datetime import datetime
from ..forms.chat import ChatMessageForm
from ..services import guest as guest_svc
from ..services.personas import get_persona
from ..services import api_client

bp = Blueprint("chat", __name__)


# 세션은 쿠키 기반이라 4KB 제한이 있음.
# 메시지가 너무 쌓이면 오래된 것부터 자름. 백엔드 붙으면 DB에 다 저장됨.
MAX_SESSION_MESSAGES = 20


def _get_messages() -> list[dict]:
    """세션에서 현재 대화의 메시지 리스트 꺼냄."""
    return session.get("chat_messages", [])


def _append_message(role: str, content: str, timestamp: str = None) -> None:
    """
    세션에 메시지 추가.
    role: "user" | "assistant"  (system은 아직 안 씀)
    """
    messages = _get_messages()
    messages.append({
        "role": role,
        "content": content,
        # timestamp 없으면 현재 시각 자동 생성
        "timestamp": timestamp or datetime.now().strftime("%H:%M")
    })
    session["chat_messages"] = messages[-MAX_SESSION_MESSAGES:]


def _mock_ai_reply(user_message: str) -> str:
    """
    임시 AI 응답. UI 흐름 검증 전용.
    실제 AI 응답 생성은 백엔드(송지현) + AI(다은) 영역.
    """
    return (
        "이야기해주셔서 감사해요. 지금은 임시 응답이라 깊이 있는 답변은 어려워요. "
        "실제 AI가 연결되면 천천히 이야기 나눠봐요."
    )


@bp.route("/", methods=["GET", "POST"])
def room():
    """채팅방 메인."""

    # ===== 1. 접근 권한 =====
    is_authenticated = "access_token" in session
    is_guest = guest_svc.is_guest()

    if not is_authenticated and not is_guest:
        # 익명 사용자는 랜딩으로 보내서 가입 또는 익명 체험 선택하게
        flash("채팅을 시작하려면 로그인하거나 익명 체험을 시작해주세요.", "info")
        return redirect(url_for("main.landing"))
    
    # 페르소나 결정.
    # 추후 사용자가 페르소나 선택 기능 만들면 session["persona_code"]로 분기.
    # 지금은 항상 기본 페르소나(empathy).
    persona = get_persona(session.get("persona_code"))

    # 첫 방문이면 캐릭터의 인사말을 자동 삽입.
    # 이걸 세션에 박아두면 새로고침해도 인사말이 유지되고,
    # 매번 _get_messages()를 부르는 곳에서 별도 처리 안 해도 됨.
    if not _get_messages():
        _append_message("assistant", persona["greeting"])

    form = ChatMessageForm()

    # ===== 2. POST: 메시지 전송 처리 =====
    if form.validate_on_submit():

        # 게스트 한도 다시 체크 — 누가 한도 다 쓴 상태로 직접 POST 보내는 경우 차단
        if is_guest and not guest_svc.can_send_message():
            # redirect 대신 팝업 플래그만 세팅 → GET에서 팝업 표시
            session["show_signup_modal"] = True
            return redirect(url_for("chat.room"))

        # 입력값 정제 (앞뒤 공백 제거)
        user_message = form.message.data.strip()
        # strip 후 빈 문자열이면 다시 폼으로 (Length validator가 잡았어야 하지만 안전망)
        if not user_message:
            flash("메시지를 입력해주세요.", "error")
            return redirect(url_for("chat.room"))

        # 사용자 메시지 저장
        now = datetime.now().strftime("%H:%M")
        _append_message("user", user_message, now)

        # 게스트면 카운트 증가 — 헤더의 X/5 표시가 다음 요청부터 자동 갱신됨
        if is_guest:
            guest_svc.increment_message_count()

        # ===== 3. AI 응답 (백엔드 /chat 호출) =====
        ai_reply = api_client.send_chat_message(
            user_message=user_message,
            history=_get_messages(),
            user_id=session.get("user_id"),
        )

        _append_message("assistant", ai_reply, now)

        # fetch 요청이면 JSON 반환, 일반 폼이면 redirect (하위 호환)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"reply": ai_reply, "timestamp": now})
        return redirect(url_for("chat.room"))

    # ===== 4. GET: 채팅 화면 렌더링 =====
    # 팝업 플래그 꺼내기 — pop으로 꺼내면 한 번 보여주고 자동 소멸
    show_signup_modal = session.pop("show_signup_modal", False)

    return render_template(
        "chat/room.html",
        form=form,
        messages=_get_messages(),
        persona=persona,
        show_signup_modal=show_signup_modal,
    )

@bp.route("/clear", methods=["POST"])
def clear():
    """대화 초기화. 새로 시작하고 싶을 때 사용자가 명시적으로 호출."""
    session.pop("chat_messages", None)
    flash("대화가 초기화되었어요.", "info")
    return redirect(url_for("chat.room"))