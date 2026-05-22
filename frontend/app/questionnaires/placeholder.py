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

PLACEHOLDER = {
    "code": "placeholder_screening",
    "type": "screening",
    "title": "초기 선별 설문 (임시)",
    "instruction": "각 항목에 대해 가장 적절한 것을 선택해주세요.",

    # 1차에서 동시에 측정할 질환 목록 (실제 도구 정해지면 "depression", "anxiety" 등으로)
    "conditions": ["질환A", "질환B", "질환C"],

    # 각 문항: 텍스트 + 어느 질환의 점수에 들어가는지 명시
    # scores_for에 여러 개 적으면 한 답변이 여러 질환 점수에 동시 누적됨
    "questions": [
        {"text": "설문1",  "scores_for": ["질환A"]},
        {"text": "설문2",  "scores_for": ["질환B"]},
        {"text": "설문3",  "scores_for": ["질환A", "질환B"]},  # 두 질환에 동시 기여
        {"text": "설문4",  "scores_for": ["질환C"]},
        {"text": "설문5",  "scores_for": ["질환A"]},
        {"text": "설문6",  "scores_for": ["질환B", "질환C"]},  # 두 질환에 동시 기여
        {"text": "설문7",  "scores_for": ["질환A", "질환B", "질환C"]},  # 세 질환 모두
        {"text": "설문8",  "scores_for": ["질환C"]},
        {"text": "설문9",  "scores_for": ["질환B"]},
        {"text": "설문10", "scores_for": ["질환A"]},
    ],

    # 선택지 5개 (이전과 동일)
    "choices": [
        (1, "점수1"),
        (2, "점수2"),
        (3, "점수3"),
        (4, "점수4"),
        (5, "점수5"),
    ],

    # 질환별로 점수 누적되니까 최대 점수는 질환마다 다름:
    #   질환A: 설문 1,3,5,7,10 = 5문항 × 최대 5점 = 25점
    #   질환B: 설문 2,3,6,7,9  = 5문항 × 최대 5점 = 25점
    #   질환C: 설문 4,6,7,8    = 4문항 × 최대 5점 = 20점
    # 실제 도구 정해지면 각 질환의 진짜 절단점으로 교체
    "severity_by_condition": {
        "질환A": [
            ( 5, 11, "낮음", "low"),
            (12, 18, "중간", "medium"),
            (19, 25, "높음", "high"),
        ],
        "질환B": [
            ( 5, 11, "낮음", "low"),
            (12, 18, "중간", "medium"),
            (19, 25, "높음", "high"),
        ],
        "질환C": [
            ( 4,  9, "낮음", "low"),
            (10, 14, "중간", "medium"),
            (15, 20, "높음", "high"),
        ],
    },

    # 2차(표적) 설문이 필요한 심각도 임계치.
    # 1차 결과가 여기 명시된 코드와 일치하면 그 질환 전용 추가 설문 안내.
    # 예: 질환A가 "medium" 또는 "high"면 질환A 표적 설문으로 보냄
    "follow_up_when": {
        "질환A": ["medium", "high"],
        "질환B": ["medium", "high"],
        "질환C": ["high"],  # 질환C는 high일 때만 추가
    },
}