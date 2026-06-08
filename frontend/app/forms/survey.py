"""
설문 폼 동적 생성기.

설문지 dict의 questions 개수만큼 RadioField를 만들어
FlaskForm 서브클래스를 동적으로 생성한다.

이걸로 한 번 짜면 문항 수가 바뀌어도 코드 수정 불필요.
"""

from flask_wtf import FlaskForm
from wtforms import RadioField
from wtforms.validators import InputRequired


def build_survey_form(instrument: dict) -> type[FlaskForm]:
    """
    설문지 dict를 받아서 FlaskForm 서브클래스를 동적으로 생성.

    매개변수:
        instrument: placeholder.py의 PLACEHOLDER 같은 dict
                    (questions, choices 키 필요)

    반환:
        FlaskForm 서브클래스 (인스턴스 아님!). 라우트에서 form = SurveyForm() 로
        실제 인스턴스 생성.

    필드명 규칙:
        문항 순서대로 q1, q2, q3, ... 식.
        템플릿에서 form.q1, form.q2 로 접근 가능
        (동적 인덱스로 접근하려면 form["q" ~ i])
    """
    # 클래스의 attribute로 들어갈 필드들을 dict에 모음
    fields = {}

    for i, question in enumerate(instrument["questions"]):
        field_name = f"q{i + 1}"  # q1, q2, q3, ...

        fields[field_name] = RadioField(
            # 라벨로 문항 텍스트 사용.
            # 사실 우리 템플릿에선 instrument["questions"][i]["text"]를
            # 직접 쓰니까 field.label은 거의 안 쓰임. 그래도 접근성·디버깅에 유용
            question["text"],

            # 선택지는 instrument의 choices를 그대로 사용.
            # [(1, "점수1"), (2, "점수2"), ...] 형태
            choices=instrument["choices"],

            # 응답 누락 시 에러 메시지
            validators=[InputRequired(message="응답을 선택해주세요")],

            # ⚠️ 중요: 폼 제출 시 문자열로 오는 값을 int로 변환.
            # 이게 없으면 sum() 할 때 문자열을 더하려 해서 TypeError.
            # (또는 "1"+"2"="12" 식으로 잘못 합쳐짐)
            coerce=int,
        )

    # type()로 클래스 동적 생성.
    # 매개변수: (클래스명, 부모클래스 튜플, 속성 dict)
    # 평소 class 키워드로 짜는 것과 결과 같음.
    return type("DynamicSurveyForm", (FlaskForm,), fields)