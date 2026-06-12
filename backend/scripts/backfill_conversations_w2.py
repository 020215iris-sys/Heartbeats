"""
일회성 백필 스크립트 — conversations 옛 W1 평문 행을 W2(AES-256-GCM)로 재암호화.

언제 돌리나:
    crypto.py가 W2로 교체된 직후 1회. 그 이후 새 메시지는 자동으로 W2로 저장됨.

멱등성:
    encryption_key_id == 'DEV_PLAINTEXT_V1'인 행만 골라서 처리하므로
    여러 번 실행해도 안전 (두 번째 실행은 0건 처리).

실행:
    docker compose exec api python scripts/backfill_conversations_w2.py

검증:
    docker compose exec db_sensitive psql -U heartbeat -d heartbeat_sensitive \\
      -c "SELECT encryption_key_id, count(*) FROM conversations GROUP BY 1;"

    => 'AES256GCM_V1'만 보이면 백필 완료. 'DEV_PLAINTEXT_V1'이 남아있으면 재실행.
"""
import asyncio

from sqlalchemy.future import select

from database import SessionLocalSensitive
from models import Conversation
from core.crypto import encrypt_content, decrypt_content


LEGACY_W1_KEY_ID = "DEV_PLAINTEXT_V1"

# 메모리 폭발 방지 — 한 번에 가져올 행 수
BATCH_SIZE = 500


async def backfill():
    total_processed = 0

    async with SessionLocalSensitive() as db:
        # 1. 옛 W1 행 갯수 먼저 확인
        count_result = await db.execute(
            select(Conversation).where(
                Conversation.encryption_key_id == LEGACY_W1_KEY_ID
            )
        )
        all_rows = count_result.scalars().all()
        total = len(all_rows)
        print(f"백필 대상: {total}건 (encryption_key_id='{LEGACY_W1_KEY_ID}')")

        if total == 0:
            print("처리할 W1 행 없음. 종료.")
            return

        # 2. 평문 복원 → AES 재암호화 → UPDATE
        for i, row in enumerate(all_rows, 1):
            try:
                plaintext = decrypt_content(row.encrypted_content, row.encryption_key_id)
                new_bytes, new_kid = encrypt_content(plaintext)
                row.encrypted_content = new_bytes
                row.encryption_key_id = new_kid
                total_processed += 1
            except Exception as e:
                print(f"  ⚠️ id={row.id} 처리 실패: {e}")
                continue

            # 배치 commit
            if i % BATCH_SIZE == 0:
                await db.commit()
                print(f"  진행: {i}/{total}")

        # 마지막 잔여 commit
        await db.commit()
        print(f"백필 완료: {total_processed}/{total}건 W2로 전환")


if __name__ == "__main__":
    asyncio.run(backfill())