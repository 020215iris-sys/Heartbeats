"""
초기 설문 라우트.

흐름:
    GET  /survey/initial  → 폼 표시
    POST /survey/initial  → 검증 → 점수 계산 → 세션 저장 → /survey/result 로 redirect
    GET  /survey/result   → 마지막 결과 표시 (세션에서 꺼냄)

참고:
    지금은 결과를 세션에만 저장 (백엔드 미연동).
    송지현 님 FastAPI 붙으면 evaluate() 호출 후
    api_client.save_diagnosis(result)로 영구 저장 추가하면 됨.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, session
from ..forms.survey import build_survey_form
from ..questionnaires import ACTIVE_INSTRUMENT, evaluate
from ..services import api_client

bp = Blueprint("survey", __name__)


@bp.route("/initial", methods=["GET", "POST"])
def initial():
    """
    초기 설문 진행.

    GET: 빈 폼 표시
    POST: 검증 통과 시 점수 계산 후 결과 페이지로 이동
    검증 실패 시 같은 페이지가 다시 렌더링되며 에러 표시
    """

    # 활성 설문지(placeholder)로 폼 클래스를 동적으로 생성.
    # 매 요청마다 생성하지만 가벼운 연산이라 성능 부담 없음.
    SurveyForm = build_survey_form(ACTIVE_INSTRUMENT)
    form = SurveyForm()

    if form.validate_on_submit():
        # 답변 수집: q1, q2, ..., qN 순서대로.
        # ACTIVE_INSTRUMENT["questions"] 길이를 직접 보고 순회해서
        # 문항 수가 바뀌어도 이 코드는 그대로 동작
        answers = [
            form[f"q{i + 1}"].data
            for i in range(len(ACTIVE_INSTRUMENT["questions"]))
        ]
        # 결과: [3, 5, 2, ...] 같은 int 리스트 (coerce=int 덕분)

        # 한 번에 점수·심각도·follow-up 계산
        # 반환 dict 구조는 Step 2의 evaluate() 참고
        result = evaluate(answers)

        # ⬇️ 추가: 진단 결과를 CSV에 영구 저장
        # 로그인 안 한 사용자는 user_id가 None — 그래도 저장은 됨 (익명 진단)
        saved = api_client.save_diagnosis(
            user_id=session.get("user_id"),
            instrument_code=result["instrument_code"],
            scores=result["scores_by_condition"],
            severities=result["severities_by_condition"],
            follow_ups=result["follow_ups_needed"],
        )

        # 세션엔 결과 페이지 표시용으로만 임시 저장
        session["last_survey_result"] = result
        # 추후 채팅 페이지가 이 진단을 참조할 수 있게 ID도 보관
        session["last_diagnosis_id"] = saved["id"]

        # PRG 패턴 (Post → Redirect → Get):
        # 폼 제출 후 redirect하면 새로고침해도 중복 제출 안 됨
        return redirect(url_for("survey.result"))

    # GET 요청 또는 검증 실패 시 폼 다시 표시
    return render_template(
        "survey/initial.html",
        form=form,
        instrument=ACTIVE_INSTRUMENT,
    )


@bp.route("/result")
def result():
    """가장 최근 설문 결과 표시."""

    result_data = session.get("last_survey_result")

    # 결과가 세션에 없으면 (직접 URL 입력 등) 설문 페이지로 안내
    if not result_data:
        flash("먼저 설문을 진행해주세요.", "info")
        return redirect(url_for("survey.initial"))

    return render_template(
        "survey/result.html",
        result=result_data,
        instrument=ACTIVE_INSTRUMENT,
    )