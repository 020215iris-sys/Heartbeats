"""
보호자 대시보드 라우트.

접근 제어: 로그인 + role == "guardian"만. (role은 로그인 시 세션에 저장됨)
지금은 틀만 — 데이터는 더미. 백엔드 연동은 다음 단계.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, session, request

bp = Blueprint("guardian", __name__)


def _require_guardian():
    """로그인 + 보호자 권한 게이트. 못 통과하면 redirect 응답, 통과면 None."""
    if "access_token" not in session:
        flash("로그인이 필요합니다.", "info")
        return redirect(url_for("auth.login"))
    if session.get("role") != "guardian":
        flash("보호자 전용 페이지입니다.", "error")
        return redirect(url_for("main.landing"))
    return None


@bp.route("/")
def dashboard():
    guard = _require_guardian()
    if guard:
        return guard
    selected_ward_id = request.args.get("ward_id")   # 사이드바에서 클릭한 사용자
    wards = []  # 피보호자 목록 (추후 백엔드)
    return render_template(
        "guardian/dashboard.html",
        wards=wards,
        selected_ward_id=selected_ward_id,
    )

