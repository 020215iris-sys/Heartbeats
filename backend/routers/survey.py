import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db_sensitive
from core.security import get_current_user
from models import CategoryCatalog, Classification, ClassificationResult
from core.crypto import encrypt_json, decrypt_json
from questionnaires import (
    ACTIVE_INSTRUMENT,
    calculate_scores,
    judge,
    responses_by_category,
)

router = APIRouter(prefix="/surveys", tags=["Survey"])


def _render_view(instrument: dict) -> dict:
    """채점 내부값(scores_for·severity·follow_up)은 빼고
    화면 렌더링에 필요한 것만 추려서 반환. 점수 기준은 서버만 안다."""
    questions = [
        {
            "text": q["text"],
            "scale": q.get("scale", "likert4"),
            "min_label": q.get("min_label", ""),
            "max_label": q.get("max_label", ""),
        }
        for q in instrument["questions"]
    ]
    return {
        "code": instrument["code"],
        "type": instrument.get("type"),
        "title": instrument.get("title"),
        "instruction": instrument.get("instruction"),
        "questions": questions,
        "scales": instrument["scales"],
    }


@router.get("/active")
def get_active_survey():
    """현재 활성 설문지의 렌더링용 정의 반환."""
    return _render_view(ACTIVE_INSTRUMENT)

class SurveyAnswers(BaseModel):
    answers: list[int]


def _validate_answers(answers: list[int], instrument: dict) -> None:
    """답변 개수·각 값 범위를 서버에서 검증. 클라이언트 값을 믿지 않는다."""
    questions = instrument["questions"]
    if len(answers) != len(questions):
        raise HTTPException(
            status_code=422,
            detail=f"답변 수({len(answers)})가 문항 수({len(questions)})와 다릅니다.",
        )
    scales = instrument["scales"]
    for idx, (ans, q) in enumerate(zip(answers, questions), start=1):
        scale = scales[q.get("scale", "likert4")]
        if scale["kind"] == "radio":
            allowed = {c[0] for c in scale["choices"]}
            if ans not in allowed:
                raise HTTPException(422, f"{idx}번 문항 값 {ans}은(는) 허용 선택지가 아닙니다.")
        elif scale["kind"] == "nrs":
            if not (scale["min"] <= ans <= scale["max"]):
                raise HTTPException(
                    422,
                    f"{idx}번 문항 값 {ans}이(가) {scale['min']}~{scale['max']} 범위를 벗어났습니다.",
                )


@router.post("/active/responses")
async def submit_active_survey(
    body: SurveyAnswers,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_sensitive),
):
    """검증 → 채점(코드) → 심각도 판정(카탈로그) → classifications + results 저장."""
    _validate_answers(body.answers, ACTIVE_INSTRUMENT)
    user_uuid = uuid.UUID(current_user["user_id"])

    # 1) 카테고리별 점수·부분응답 — 코드 로직
    scores = calculate_scores(body.answers)
    resp_by_cat = responses_by_category(body.answers)

    # 2) 카탈로그 절단점으로 심각도·follow-up 판정 — DB
    catalog = {
        r.category_code: r
        for r in (await db.execute(select(CategoryCatalog))).scalars().all()
    }
    rules = {code: row.severity_rule for code, row in catalog.items()}
    verdict = judge(scores, rules)
    severities = verdict["severities"]
    follow_ups = verdict["follow_ups"]

    # 3) score_delta용 직전 점수 — 행 추가 전에 미리 조회
    deltas = {}
    for code, score in scores.items():
        prev = (await db.execute(
            select(ClassificationResult.total_score)
            .join(Classification,
                  Classification.id == ClassificationResult.classification_id)
            .where(
                Classification.user_id == user_uuid,
                ClassificationResult.category_code == code,
                Classification.deleted_at.is_(None),
                ClassificationResult.deleted_at.is_(None),
            )
            .order_by(ClassificationResult.created_at.desc())
            .limit(1)
        )).scalar_one_or_none()
        deltas[code] = (score - prev) if prev is not None else None

    # 4) classifications 1행
    # W3: compound_flags 듀얼 라이트
    cf_value = {"follow_ups": follow_ups}
    cf_bytes, cf_kid = encrypt_json(cf_value)

    classification = Classification(
        user_id=user_uuid,
        compound_flags=cf_value,                       # 옛 평문 (듀얼 라이트)
        compound_flags_encrypted=cf_bytes,             # W3
        compound_flags_key_id=cf_kid,                  # W3
        selected_prompt_key=None,                       # 상담 라우터가 이후 결정
    )
    db.add(classification)
    await db.flush()                # classification.id 확보

    # 5) classification_results 카테고리당 1행
    for code, score in scores.items():
        cat = catalog[code]
        # W3: responses 듀얼 라이트
        resp_value = resp_by_cat[code]
        resp_bytes, resp_kid = encrypt_json(resp_value)
        db.add(ClassificationResult(
            classification_id=classification.id,
            category_code=code,
            instrument=cat.instrument,
            instrument_ver=cat.instrument_ver,
            responses=resp_value,                       # 옛 평문 (듀얼 라이트)
            responses_encrypted=resp_bytes,             # W3
            responses_key_id=resp_kid,                  # W3
            total_score=score,
            severity=severities[code]["code"],
            score_delta=deltas[code],
        ))

    await db.commit()

    return {
        "classification_id": str(classification.id),
        "scores": scores,
        "severities": severities,
        "follow_ups": follow_ups,
        "display_names": {code: catalog[code].display_name for code in scores},
    }


@router.get("/classifications/{classification_id}")
async def get_classification(
    classification_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_sensitive),
):
    """저장된 분류 1건 + 결과 행 조회 (본인 것만). 저장 검증·결과 페이지용."""
    try:
        cid = uuid.UUID(classification_id)
    except ValueError:
        raise HTTPException(422, "classification_id가 올바른 UUID가 아닙니다.")
    cls = await db.get(Classification, cid)
    if cls is None or cls.user_id != uuid.UUID(current_user["user_id"]) or cls.deleted_at is not None:
        raise HTTPException(404, "해당 분류 결과를 찾을 수 없습니다.")
    rows = (await db.execute(
        select(ClassificationResult)
        .where(
            ClassificationResult.classification_id == cid,
            ClassificationResult.deleted_at.is_(None),
        )
    )).scalars().all()
    def _w3_or_legacy(enc_blob, key_id, legacy):
        """W3 우선 → 실패/없으면 옛 평문 JSONB."""
        if enc_blob is not None:
            decoded = decrypt_json(enc_blob, key_id)
            if decoded is not None:
                return decoded
        return legacy

    return {
        "classification_id": str(cls.id),
        "compound_flags": _w3_or_legacy(
            cls.compound_flags_encrypted, cls.compound_flags_key_id, cls.compound_flags
        ),
        "created_at": cls.created_at.isoformat(),
        "results": [
            {
                "category_code": r.category_code,
                "instrument": r.instrument,
                "instrument_ver": r.instrument_ver,
                "total_score": r.total_score,
                "severity": r.severity,
                "score_delta": r.score_delta,
                "responses": _w3_or_legacy(
                    r.responses_encrypted, r.responses_key_id, r.responses
                ),
            }
            for r in rows
        ],
    }

@router.get("/categories")
async def list_categories(db: AsyncSession = Depends(get_db_sensitive)):
    """category_catalog 전체 조회 (시드 확인·절단점 점검용)."""
    rows = (await db.execute(select(CategoryCatalog))).scalars().all()
    return [
        {
            "category_code": r.category_code,
            "display_name": r.display_name,
            "instrument": r.instrument,
            "instrument_ver": r.instrument_ver,
            "item_count": r.item_count,
            "max_score": r.max_score,
            "severity_rule": r.severity_rule,
            "is_active": r.is_active,
        }
        for r in rows
    ]