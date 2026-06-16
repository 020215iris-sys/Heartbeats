"""사용자(피보호자) 대시보드 라우트."""

from flask import Blueprint, render_template, redirect, url_for, flash, session, jsonify, request
from ..services import api_client

bp = Blueprint("dashboard", __name__)

@bp.route("/")
def index():
    if "access_token" not in session:
        flash("로그인이 필요합니다.", "info")
        return redirect(url_for("auth.login"))
    # 보호자는 보호자 대시보드로
    if session.get("role") == "guardian":
        return redirect(url_for("guardian.dashboard"))
    return render_template("dashboard/index.html")


@bp.route("/invite", methods=["POST"])
def invite():
    if "access_token" not in session:
        return jsonify({"error": "unauthorized"}), 401
    result = api_client.create_guardian_invite()
    if result is None:
        return jsonify({"error": "발급 실패"}), 502
    return jsonify(result)

@bp.route("/calendar")
def calendar():
    """브라우저 JS → 여기(토큰 포함) → 백엔드 호출. 달력 레벨 데이터 반환."""
    if "access_token" not in session:
        return jsonify({"error": "unauthorized"}), 401
    month = request.args.get("month", "")
    data = api_client.get_calendar(month, request.args.get("ward_id"))
    return jsonify(data or {"month": month, "days": {}})

@bp.route("/day")
def day():
    if "access_token" not in session:
        return jsonify({"error": "unauthorized"}), 401
    date = request.args.get("date", "")
    data = api_client.get_day(date, request.args.get("ward_id"))
    return jsonify(data or {"date": date, "items": []})