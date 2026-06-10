"""
초기 설문 라우트 (백엔드 연동판).

흐름:
    GET  /survey/initial  → 백엔드에서 설문 정의 받아 폼 표시 (로그인 필수)
    POST /survey/initial  → 답변을 백엔드로 제출(채점·저장) → /survey/result
    GET  /survey/result   → 세션에 임시 보관된 결과 표시

채점·절단점·저장은 모두 백엔드(FastAPI + DB) 담당.
프론트는 정의를 받아 그리고, 답변을 보내고, 결과를 보여주기만 함.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, session
from ..forms.survey import build_survey_form
from ..services import api_client

bp = Blueprint("survey", __name__)


@bp.route("/initial", methods=["GET", "POST"])
def initial():
    # 결과는 로그인 사용자만 저장 → 비로그인 차단
    if "access_token" not in session:
        flash("설문은 로그인 후 이용할 수 있어요.", "info")
        return redirect(url_for("auth.login"))

    # 백엔드에서 설문 정의 받아오기
    instrument = api_client.get_active_survey()
    if instrument is None:
        flash("설문을 불러오지 못했어요. 잠시 후 다시 시도해주세요.", "error")
        return redirect(url_for("main.landing"))

    SurveyForm = build_survey_form(instrument)
    form = SurveyForm()

    if form.validate_on_submit():
        # q1..qN 순서대로 답변 수집
        answers = [
            form[f"q{i + 1}"].data
            for i in range(len(instrument["questions"]))
        ]
        result = api_client.submit_survey(answers)
        if result is None:
            flash("결과 저장에 실패했어요. 다시 로그인했는지 확인 후 시도해주세요.", "error")
            return render_template("survey/initial.html", form=form, instrument=instrument)

        # 결과 페이지 표시용으로만 세션에 임시 보관 (영구 저장은 백엔드 DB)
        session["last_survey_result"] = result
        session["last_classification_id"] = result["classification_id"]
        return redirect(url_for("survey.result"))

    return render_template("survey/initial.html", form=form, instrument=instrument)


@bp.route("/result")
def result():
    """가장 최근 설문 결과 표시."""
    if "access_token" not in session:
        return redirect(url_for("auth.login"))

    result_data = session.get("last_survey_result")
    if not result_data:
        flash("먼저 설문을 진행해주세요.", "info")
        return redirect(url_for("survey.initial"))

    return render_template("survey/result.html", result=result_data)