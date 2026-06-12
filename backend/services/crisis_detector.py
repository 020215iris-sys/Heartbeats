# 과거 파일 - 키워드 기반 감지

import json
import os
from dataclasses import dataclass
from typing import Optional

# keyword.json 경로: 프로젝트 루트 기준
KEYWORD_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "ai", "keyword.json")

with open(KEYWORD_PATH, encoding="utf-8") as f:
    KEYWORDS = json.load(f)

# 카테고리별 심각도 매핑
SEVERITY_MAP = {
    "self_harm":     "critical",
    "direct_high":   "high",
    "direct_medium": "medium",
    "panic":         "medium",
    "indirect":      "low",
}

# crisis_score 매핑
SCORE_MAP = {
    "critical": 1.0,
    "high":     0.85,
    "medium":   0.6,
    "low":      0.3,
}


@dataclass
class CrisisDetectionResult:
    detected: bool
    severity: Optional[str]        # critical / high / medium / low / None
    crisis_score: float            # 0.0 ~ 1.0
    matched_keyword: Optional[str] # 실제로 매칭된 키워드
    category: Optional[str]        # self_harm / direct_high / ...


def detect_crisis(user_message: str) -> CrisisDetectionResult:
    """
    사용자 발화에서 위험 키워드를 감지한다.
    심각도 우선순위: critical > high > medium > low
    """
    # 우선순위 순으로 카테고리 검사
    priority_order = ["self_harm", "direct_high", "direct_medium", "panic", "indirect"]

    for category in priority_order:
        keywords = KEYWORDS.get(category, [])
        for kw in keywords:
            if kw in user_message:
                severity = SEVERITY_MAP[category]
                return CrisisDetectionResult(
                    detected=True,
                    severity=severity,
                    crisis_score=SCORE_MAP[severity],
                    matched_keyword=kw,
                    category=category,
                )

    return CrisisDetectionResult(
        detected=False,
        severity=None,
        crisis_score=0.0,
        matched_keyword=None,
        category=None,
    )
