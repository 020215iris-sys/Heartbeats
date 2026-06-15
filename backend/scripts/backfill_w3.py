"""
W3 백필 스크립트 — 옛 평문(JSONB / VARCHAR) 행을 AES-256-GCM으로
재암호화해 신규 컬럼에 채운다.

대상:
  - summaries.core_topics / important_memory      (JSONB)
  - classifications.compound_flags                 (JSONB)
  - classification_results.responses               (JSONB)
  - crisis_events.action_taken                     (VARCHAR)

언제 돌리나:
  4·5단계(저장/조회 듀얼 라이트) 적용 + 컨테이너 재시작 후 1회.
  새 코드는 새 행은 듀얼 라이트로 양쪽 다 채우지만, 마이그레이션 적용 전에
  만들어진 옛 행은 새 컬럼이 NULL. 이 스크립트가 그 옛 행들의 새 컬럼만 채운다.

멱등성:
  WHERE (legacy IS NOT NULL AND new_enc IS NULL) 필터 → 이미 채워진 행은 건너뜀.
  여러 번 돌려도 안전.

배치:
  메모리 폭발 방지 — 한 번에 BATCH_SIZE개씩 처리.
  매 페이지 commit 후 다음 페이지 SELECT (조건이 enc IS NULL이라 자동 진행).

실행:
  docker compose exec api python scripts/backfill_w3.py

검증 (run 후):
  남은 행 수 SELECT (스크립트 아래 안내 참조). 전부 0이어야 함.

주의:
  audit 트리거가 UPDATE를 잡으므로 audit_logs_sensitive에 행 수만큼 INSERT 발생.
  베타 단계 데이터 양이라 무시 가능. 운영 단계에선 트리거 임시 비활성화 검토.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio

from sqlalchemy import or_, and_
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from database import engine_sensitive
from models import (
    Summary,
    Classification,
    ClassificationResult,
    CrisisEvent,
)
from core.crypto import encrypt_json, encrypt_content


BATCH_SIZE = 200


async def backfill_table(label, model, jobs):
    """
    jobs: [(legacy_attr, enc_attr, kid_attr, encryptor), ...]
      encryptor: callable(value) -> (bytes, key_id)
    """
    SessionMaker = async_sessionmaker(engine_sensitive, expire_on_commit=False)
    total_cells = 0
    pages = 0

    async with SessionMaker() as db:
        while True:
            # 옛 NOT NULL AND 새 NULL인 짝이 하나라도 있는 행만 가져옴
            row_filters = []
            for legacy_attr, enc_attr, _, _ in jobs:
                legacy_col = getattr(model, legacy_attr)
                enc_col = getattr(model, enc_attr)
                row_filters.append(and_(legacy_col.isnot(None), enc_col.is_(None)))

            stmt = (
                select(model)
                .where(or_(*row_filters))
                .order_by(model.id)
                .limit(BATCH_SIZE)
            )
            rows = (await db.execute(stmt)).scalars().all()
            if not rows:
                break

            updated_cells = 0
            for row in rows:
                for legacy_attr, enc_attr, kid_attr, encryptor in jobs:
                    legacy_val = getattr(row, legacy_attr)
                    enc_val = getattr(row, enc_attr)
                    if legacy_val is not None and enc_val is None:
                        ct, kid = encryptor(legacy_val)
                        setattr(row, enc_attr, ct)
                        setattr(row, kid_attr, kid)
                        updated_cells += 1

            await db.commit()
            pages += 1
            total_cells += updated_cells
            print(f"[{label}] page#{pages} rows={len(rows)} cells={updated_cells} 누적={total_cells}")

    print(f"[{label}] 완료 — 총 채운 셀: {total_cells}\n")


async def main():
    print("=== W3 백필 시작 ===\n")

    await backfill_table("summaries", Summary, [
        ("core_topics",      "core_topics_encrypted",      "core_topics_key_id",      encrypt_json),
        ("important_memory", "important_memory_encrypted", "important_memory_key_id", encrypt_json),
    ])

    await backfill_table("classifications", Classification, [
        ("compound_flags", "compound_flags_encrypted", "compound_flags_key_id", encrypt_json),
    ])

    await backfill_table("classification_results", ClassificationResult, [
        ("responses", "responses_encrypted", "responses_key_id", encrypt_json),
    ])

    await backfill_table("crisis_events", CrisisEvent, [
        ("action_taken", "action_taken_encrypted", "action_taken_key_id", encrypt_content),
    ])

    print("=== 전체 완료 ===")


if __name__ == "__main__":
    asyncio.run(main())