"""
플레이스홀더 설문지.

⚠️ 실제 도구 확정되면 이 파일 통째로 교체.
구조만 유지하면 라우트·폼·템플릿은 손 안 대고 동작.

이 구조는 두 가지 모드를 모두 지원:
  1) 선별 설문(1차): conditions에 여러 질환, questions의 scores_for가 다양
  2) 표적 설문(2차): conditions에 한 질환만, 모든 questions가 그 질환에 기여

dict 키 설명:
    code        : 식별자 (DB 저장용)
    type        : "screening"(선별) / "focused"(표적)
    conditions  : 측정할 질환들. 1차는 여러 개, 2차는 1개
    questions   : 각 항목이 어느 질환에 점수 기여하는지 표시
    choices     : (점수값, 라벨)
    severity_by_condition : 질환별 독립 절단점
    follow_up_when        : 어떤 심각도면 추가 설문 필요한지
"""

# 문항별 척도 정의. 각 문항이 question["scale"]로 참조. 키 없으면 likert4로 간주.
SCALES = {
    "likert4": {
        "kind": "radio",
        "choices": [
            (0, "전혀 방해받지 않았다"),
            (1, "며칠 동안 방해 받았다"),
            (2, "7일 이상 방해 받았다"),
            (3, "거의 매일 방해 받았다"),
        ],
    },
    "nrs11": {
        "kind": "nrs",
        "min": 0, "max": 10, "step": 1, "default": 0,
        "min_label": "", "max_label": "",   # 문항별 라벨 우선, 없을 때만 이 값 사용
    },
}

PLACEHOLDER = {
    "code": "placeholder_screening",
    "type": "screening",
    "title": "초기 선별 설문 (임시)",
    "instruction": "각 항목에 대해 가장 적절한 것을 선택해주세요.",

    # 1차에서 동시에 측정할 질환 목록 (실제 도구 정해지면 "depression", "anxiety" 등으로)
    "conditions": ["depression", "anxiety", "insomnia"],

    # 각 문항: 텍스트 + 어느 질환의 점수에 들어가는지 명시
    # scores_for에 여러 개 적으면 한 답변이 여러 질환 점수에 동시 누적됨
    "questions": [
        {"text": "일 또는 여가 활동을 하는 데 흥미나 즐거움을 느끼지 못함.",  "scores_for": ["depression"]},
        {"text": "기분이 가라앉거나, 우울하거나, 희망이 없음.",  "scores_for": ["depression"]},
        {"text": "잠이 들거나 계속 잠을 자는 것이 어려움, 또는 잠을 너무 많이잠.", "scores_for": ["depression"]},
        {"text": "피곤하다고 느끼거나 기운이 거의 없음.", "scores_for": ["depression"]},
        {"text": "입맛이 없거나 과식을 함.", "scores_for": ["depression"]},
        {"text": "자신을 부정적으로 봄 혹은 자신이 실패자라고 느끼거나 자신또는 가족을 실망시킴.", "scores_for": ["depression"]},
        {"text": "신문을 읽거나 텔레비전 보는 것과 같은 일에 집중하는 것이 어려움.", "scores_for": ["depression"]},
        {"text": "다른 사람들이 주목할 정도로 너무 느리게 움직이거나 말을 함. 또는 반대로 평상시보다 많이 움직여서, 너무 안절부절 못하거나 들떠 있음.", "scores_for": ["depression"]},
        {"text": "자신이 죽는 것이 더 낫다고 생각하거나 어떤 식으로든 자신을 해칠 것이라고 생각함.", "scores_for": ["depression"]},

        {"text": "초조하거나 불안하거나 조마조마하게 느낀다.",  "scores_for": ["anxiety"]},
        {"text": "걱정하는 것을 멈추거나 조절할 수가 없다",  "scores_for": ["anxiety"]},
        {"text": "여러 가지 것들에 대해 걱정을 너무 많이 한다.",  "scores_for": ["anxiety"]},  
        {"text": "편하게 있기가 어렵다.",  "scores_for": ["anxiety"]},
        {"text": "너무 안절부절못해서 가만히 있기가 힘들다.",  "scores_for": ["anxiety"]},
        {"text": "쉽게 짜증이 나거나 쉽게 성을 내게 된다.",  "scores_for": ["anxiety"]},
        {"text": "마치 끔찍한 일이 생길 것처럼 두렵게 느껴진다.",  "scores_for": ["anxiety"]}, 

        {"text": "일어났을 때의 기분은 어떠십니까?", "scores_for": ["insomnia"], "scale": "nrs11", "min_label": "피곤하다", "max_label": "정신이 맑다"},
        {"text": "잠들기가 어떠십니까?", "scores_for": ["insomnia"], "scale": "nrs11", "min_label": "잠들기 힘들다", "max_label": "잠들기 쉽다"},
        {"text": "수면 상태는 어떠십니까?", "scores_for": ["insomnia"], "scale": "nrs11", "min_label": "선 잠을 잔다", "max_label": "푹 잔다"},
    ],

    # 선택지 5개 (이전과 동일)
    "choices": [
        (0, "전혀 방해받지 않았다"),
        (1, "며칠 동안 방해 받았다"),
        (2, "7일 이상 방해 받았다"),
        (3, "거의 매일 방해 받았다"),
    ],
    
    "scales": SCALES,
}