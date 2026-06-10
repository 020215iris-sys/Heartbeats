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

def judge(
    scores: dict[str, int],
    rules: dict[str, dict],
) -> dict:
    """
    카테고리별 점수 + 카탈로그 severity_rule → 심각도 + follow-up.

    rules: category_catalog에서 읽은 {category_code: severity_rule}
           severity_rule = {"bands": [[min,max,label,code],...],
                            "follow_up_codes": [code,...]}
    반환: {"severities": {code: {score,label,code}}, "follow_ups": [code,...]}
    """
    severities = {}
    follow_ups = []
    for code, score in scores.items():
        rule = rules.get(code)
        if rule is None:
            raise ValueError(
                f"category_catalog에 '{code}' 규칙이 없습니다. seed_categories.py 실행을 확인하세요."
            )
        sev = _severity_for_score(score, rule["bands"])
        if sev is None:
            raise ValueError(
                f"'{code}' 점수 {score}가 어느 band에도 안 들어갑니다. severity_rule 범위를 확인하세요."
            )
        severities[code] = sev
        if sev["code"] in rule.get("follow_up_codes", []):
            follow_ups.append(code)
    return {"severities": severities, "follow_ups": follow_ups}


def responses_by_category(
    answers: list[int],
    instrument: dict = ACTIVE_INSTRUMENT,
) -> dict[str, dict]:
    """
    답변 리스트 → 카테고리별 부분 응답. 각 카테고리엔 그 카테고리(scores_for)에
    기여하는 문항의 답만 담김. 문항 키는 q1..qN(1부터).
    예: {"insomnia": {"q17": 0, "q18": 0, "q19": 0}, ...}
    """
    out = {code: {} for code in instrument["conditions"]}
    for idx, (answer, question) in enumerate(
        zip(answers, instrument["questions"]), start=1
    ):
        for code in question["scores_for"]:
            out[code][f"q{idx}"] = answer
    return out