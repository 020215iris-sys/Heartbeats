from flask import Blueprint, render_template, redirect, url_for, flash
from ..services import guest as guest_svc
bp = Blueprint('main', __name__)

@bp.route('/')
def landing():
    return render_template('landing.html')

@bp.route("/guest/start")
def start_guest():
    """
    비회원 체험 시작.
    세션에 게스트 플래그 + 메시지 카운트(0) 초기화 후 채팅 페이지로 보냄.
    채팅 페이지는 아직 없으니까 임시로 랜딩으로 리다이렉트 (안내 메시지와 함께).
    """
    guest_svc.start_guest_session()
    flash(
        f"익명 체험 모드로 시작했어요. {guest_svc.get_remaining_messages()}개 메시지까지 보낼 수 있어요.",
        "info",
    )
    # TODO: chat 페이지 만들면 url_for("chat.room") 으로 교체
    return redirect(url_for("main.landing"))