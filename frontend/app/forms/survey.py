"""
설문 폼 동적 생성기.

설문지 dict의 questions 개수만큼 RadioField를 만들어
FlaskForm 서브클래스를 동적으로 생성한다.

이걸로 한 번 짜면 문항 수가 바뀌어도 코드 수정 불필요.
"""

from flask_wtf import FlaskForm
from wtforms import RadioField, IntegerRangeField
from wtforms.validators import InputRequired, NumberRange


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

    scales = instrument["scales"]
    for i, question in enumerate(instrument["questions"]):
        field_name = f"q{i + 1}"  # q1, q2, q3, ...
        scale = scales[question.get("scale", "likert4")]

        if scale["kind"] == "radio":
            fields[field_name] = RadioField(
                question["text"],
                choices=scale["choices"],
                validators=[InputRequired(message="응답을 선택해주세요")],
                coerce=int,
            )
        elif scale["kind"] == "nrs":
            # IntegerRangeField는 이미 int 반환 → coerce 불필요
            fields[field_name] = IntegerRangeField(
                question["text"],
                default=scale.get("default", scale["min"]),
                validators=[
                    InputRequired(message="응답을 선택해주세요"),
                    NumberRange(
                        min=scale["min"], max=scale["max"],
                        message=f"{scale['min']}~{scale['max']} 사이로 선택해주세요",
                    ),
                ],
            )
        else:
            raise ValueError(f"알 수 없는 척도 kind: {scale['kind']}")

    # type()로 클래스 동적 생성.
    # 매개변수: (클래스명, 부모클래스 튜플, 속성 dict)
    # 평소 class 키워드로 짜는 것과 결과 같음.
    return type("DynamicSurveyForm", (FlaskForm,), fields)