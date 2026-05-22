"""
설문 도구 공통 로직.

선별 설문(다질환)과 표적 설문(단일 질환) 둘 다 같은 함수로 처리됨.
질환이 N개면 점수·심각도 dict의 키도 N개일 뿐, 로직은 동일.
"""

from .placeholder import PLACEHOLDER


# ⬇️ 교체 포인트: 활성 도구를 바꾸려면 여기만 수정
ACTIVE_INSTRUMENT = PLACEHOLDER


# ========== 내부 헬퍼 ==========


def _severity_for_score(score: int, thresholds: list[tuple]) -> dict | None:
    """
    한 질환의 점수와 그 질환의 절단점 리스트를 받아 해당 구간 정보 반환.
    어느 구간에도 안 맞으면 None.

    thresholds 예: [(5, 11, "낮음", "low"), (12, 18, "중간", "medium"), ...]
    """
    for min_s, max_s, label, code in thresholds:
        if min_s <= score <= max_s:
            return {"score": score, "label": label, "code": code}
    return None


# ========== 공개 함수 ==========


def calculate_scores(
    answers: list[int],
    instrument: dict = ACTIVE_INSTRUMENT,
) -> dict[str, int]:
    """
    답변 리스트 → 질환별 점수 dict.

    핵심 로직:
        문항 i의 답변 점수가, 그 문항의 scores_for에 들어있는
        모든 질환의 점수에 동시 누적됨.

    예시 — answers = [3, 4, 2, ...], questions = [
        {"text": "설문1", "scores_for": ["질환A"]},
        {"text": "설문2", "scores_for": ["질환B"]},
        {"text": "설문3", "scores_for": ["질환A", "질환B"]},
        ...
    ]
        설문1의 3점 → 질환A에 +3
        설문2의 4점 → 질환B에 +4
        설문3의 2점 → 질환A에 +2, 질환B에도 +2  ← 동시 누적
    """
    # 모든 질환을 0으로 초기화. 한 문항도 기여 안 하는 질환이 있더라도 키는 존재하게.
    scores = {condition: 0 for condition in instrument["conditions"]}

    # zip으로 답변과 문항을 짝지어 순회.
    # answers 길이와 questions 길이가 같다고 가정 (라우트에서 보장)
    for answer, question in zip(answers, instrument["questions"]):
        for condition in question["scores_for"]:
            scores[condition] += answer

    return scores


def get_severity_per_condition(
    scores: dict[str, int],
    instrument: dict = ACTIVE_INSTRUMENT,
) -> dict[str, dict]:
    """
    질환별 점수 dict → 질환별 심각도 정보 dict.

    반환 예시:
        {
            "질환A": {"score": 15, "label": "중간", "code": "medium"},
            "질환B": {"score":  8, "label": "낮음", "code": "low"},
            "질환C": {"score": 18, "label": "높음", "code": "high"},
        }
    """
    result = {}
    for condition, score in scores.items():
        thresholds = instrument["severity_by_condition"][condition]
        severity = _severity_for_score(score, thresholds)
        if severity is None:
            # 절단점 표가 점수 범위를 다 커버하지 못한 설정 오류.
            # 운영 중엔 발생하면 안 되고, 개발 중 검증용 예외
            raise ValueError(
                f"{condition}의 점수 {score}가 어느 절단점 구간에도 안 들어가요. "
                f"placeholder.py의 severity_by_condition 설정 확인 필요."
            )
        result[condition] = severity

    return result


def get_follow_ups_needed(
    severities: dict[str, dict],
    instrument: dict = ACTIVE_INSTRUMENT,
) -> list[str]:
    """
    질환별 심각도 → 추가 설문이 필요한 질환 이름 리스트.

    follow_up_when 설정과 비교해서, 심각도 코드가 일치하면 follow-up 대상.

    예시 — follow_up_when = {"질환A": ["medium", "high"], "질환B": ["high"]}
        질환A 결과가 "medium" → 질환A는 follow-up 필요
        질환B 결과가 "medium" → 질환B는 follow-up 불필요 ("high"만 트리거)
        질환C는 follow_up_when에 없음 → 항상 불필요
    """
    follow_ups = []
    follow_up_rules = instrument.get("follow_up_when", {})

    for condition, severity in severities.items():
        triggers = follow_up_rules.get(condition, [])
        if severity["code"] in triggers:
            follow_ups.append(condition)

    return follow_ups


def evaluate(
    answers: list[int],
    instrument: dict = ACTIVE_INSTRUMENT,
) -> dict:
    """
    답변 한 방에 전체 평가. 라우트에서 이 함수만 호출하면 됨.

    반환:
        {
            "instrument_code": "placeholder_screening",
            "scores_by_condition": {"질환A": 15, "질환B": 8, ...},
            "severities_by_condition": {"질환A": {label, code, score}, ...},
            "follow_ups_needed": ["질환A", "질환C"],
        }
    """
    scores = calculate_scores(answers, instrument)
    severities = get_severity_per_condition(scores, instrument)
    follow_ups = get_follow_ups_needed(severities, instrument)

    return {
        "instrument_code": instrument["code"],
        "scores_by_condition": scores,
        "severities_by_condition": severities,
        "follow_ups_needed": follow_ups,
    }