"""사용자(피보호자) 대시보드 라우트."""

from flask import Blueprint, render_template, redirect, url_for, flash, session

bp = Blueprint("dashboard", __name__)


@bp.route("/")
def index():
    if "access_token" not in session:
        flash("로그인이 필요합니다.", "info")
        return redirect(url_for("auth.login"))
    # 보호자는 보호자 대시보드로 보냄
    if session.get("role") == "guardian":
        return redirect(url_for("guardian.dashboard"))
    return render_template("dashboard/index.html")