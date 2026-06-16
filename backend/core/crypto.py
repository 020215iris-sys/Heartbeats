# backend/core/crypto.py
"""
대화·요약 본문 암호화 헬퍼 (W2: AES-256-GCM)

W2 단계 정책
- encrypt_content: 평문 str → AES-256-GCM 암호문 바이트 (nonce 12바이트 prepend)
- decrypt_content: 라벨(key_id)을 보고 분기
    - 'AES256GCM_V1' → 진짜 AES 복호화
    - 'DEV_PLAINTEXT_V1' → 옛 W1 행(UTF-8 평문) 호환 디코딩
- key_id: 'AES256GCM_V1' (현재). 키 로테이션 시 V2로 증가하며 두 버전 모두 지원.

암호화 키
- 환경변수 ENCRYPTION_KEY (32바이트를 base64로 인코딩한 문자열)
- 부팅 시점에 검증: 누락·길이 불일치면 RuntimeError로 즉시 중단

호환성
- W1 시기에 저장된 행(key_id='DEV_PLAINTEXT_V1')도 그대로 읽힘.
- 신규 저장은 모두 AES256GCM_V1.

⚠️ 이 모듈을 호출하지 않고 직접 DB에 평문/바이트를 쓰면 W2 전환 후 데이터 깨짐.
   반드시 encrypted_content / *_encrypted 컬럼 다루는 모든 경로는 이 함수를 통과해야 함.
"""
import os
import json
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# ──────────────────────────────────────────
# 키 로딩 (부팅 시 1회)
# ──────────────────────────────────────────
_KEY_B64 = os.getenv("ENCRYPTION_KEY")
if not _KEY_B64:
    raise RuntimeError(
        "ENCRYPTION_KEY 환경변수가 없습니다. "
        "32바이트 base64 문자열로 backend/.env 또는 docker-compose 환경변수에 설정하세요. "
        "예: python -c \"import os, base64; print(base64.b64encode(os.urandom(32)).decode())\""
    )

_KEY = base64.b64decode(_KEY_B64)
if len(_KEY) != 32:
    raise RuntimeError(
        f"ENCRYPTION_KEY는 32바이트(AES-256용)여야 합니다. "
        f"현재 디코딩된 길이: {len(_KEY)}바이트. "
        f"base64 인코딩이 올바른지 확인하세요."
    )

_AESGCM = AESGCM(_KEY)

# 라벨(key_id) — DB 행마다 어떤 키·알고리즘으로 잠갔는지 기록
_CURRENT_KEY_ID = "AES256GCM_V1"
_LEGACY_PLAINTEXT_KEY_IDS = {"DEV_PLAINTEXT_V1", "none"}
_NONCE_BYTES = 12                          # AES-GCM 권장 nonce 길이


# ──────────────────────────────────────────
# 공개 API
# ──────────────────────────────────────────
def encrypt_content(plaintext: str) -> tuple[bytes, str]:
    """
    평문 → AES-256-GCM 암호문 바이트로 변환.

    반환 형식: (nonce(12B) + ciphertext + tag(16B), 'AES256GCM_V1')
    nonce를 ciphertext 앞에 붙여 한 BYTEA 컬럼으로 저장 → 복호화 시 분리.

    Args:
        plaintext: 사용자 또는 AI의 메시지·요약 평문

    Returns:
        (ciphertext_bytes, key_id) — DB의 *_encrypted + *_key_id 컬럼에 같이 저장.
    """
    if not isinstance(plaintext, str):
        raise TypeError(f"plaintext는 str이어야 함, got {type(plaintext)}")

    nonce = os.urandom(_NONCE_BYTES)
    ct = _AESGCM.encrypt(nonce, plaintext.encode("utf-8"), None)
    return nonce + ct, _CURRENT_KEY_ID


def decrypt_content(ciphertext: bytes, key_id: str) -> str:
    """
    저장된 바이트 → 평문 str로 복원.

    key_id 라벨로 분기:
        - 'AES256GCM_V1' → AES 복호화
        - 'DEV_PLAINTEXT_V1' → 옛 W1 행 (UTF-8 디코딩만)
        - 그 외 → ValueError (알 수 없는 라벨)

    asyncpg 등이 BYTEA를 bytes/memoryview/bytearray로 줄 수 있어 셋 다 허용.
    옛 이주 호환: ciphertext가 str로 들어오면 그대로 반환.
    """
    if isinstance(ciphertext, str):
        return ciphertext  # 옛 TEXT 컬럼 행 호환

    if not isinstance(ciphertext, (bytes, memoryview, bytearray)):
        raise TypeError(f"ciphertext는 bytes여야 함, got {type(ciphertext)}")

    ciphertext = bytes(ciphertext)

    # 옛 W1 행 (W1 헬퍼 또는 default='none'): UTF-8 평문이 그대로 들어있음
    if key_id in _LEGACY_PLAINTEXT_KEY_IDS:
        return ciphertext.decode("utf-8")

    # 현재 W2 행: AES-256-GCM 복호화
    if key_id == _CURRENT_KEY_ID:
        if len(ciphertext) < _NONCE_BYTES + 16:  # nonce + 최소 tag
            raise ValueError("ciphertext가 너무 짧습니다 (nonce+tag 길이 부족)")
        nonce, ct = ciphertext[:_NONCE_BYTES], ciphertext[_NONCE_BYTES:]
        return _AESGCM.decrypt(nonce, ct, None).decode("utf-8")

    raise ValueError(
        f"알 수 없는 encryption_key_id: '{key_id}'. "
        f"지원: '{_CURRENT_KEY_ID}' (W2), {sorted(_LEGACY_PLAINTEXT_KEY_IDS)} (옛 평문)."
    )

# ──────────────────────────────────────────
# W3: JSONB 컬럼용 헬퍼
# 대상 컬럼:
#   summaries.core_topics, summaries.important_memory,
#   classifications.compound_flags, classification_results.responses
# ──────────────────────────────────────────
def encrypt_json(value) -> tuple[bytes | None, str | None]:
    """
    dict / list / None → AES-256-GCM 암호문.

    None → (None, None)  (nullable 컬럼에 그대로 NULL 저장 가능)
    []   → '[]' 평문을 정상 암호화
    {}   → '{}' 평문을 정상 암호화

    ensure_ascii=False — 한글이 \\uXXXX로 부풀지 않게 UTF-8 직렬화.
    반환: (ciphertext_bytes, key_id) — DB의 *_encrypted + *_key_id 컬럼 짝.
    """
    if value is None:
        return None, None
    payload = json.dumps(value, ensure_ascii=False)
    return encrypt_content(payload)


def decrypt_json(ciphertext, key_id):
    """
    BYTEA + key_id → dict / list / None.

    - ciphertext나 key_id가 None이면 None.
    - 복호화·JSON 파싱 실패 시 예외 안 던지고 None 반환
      → 호출부에서 옛 평문 컬럼으로 fallback 가능 (마이그레이션 중간 상태 안전).
    - asyncpg가 BYTEA를 bytes/memoryview/bytearray 어느 형태로 줘도 decrypt_content가 흡수.
    """
    if ciphertext is None or key_id is None:
        return None
    try:
        plaintext = decrypt_content(ciphertext, key_id)
        if not plaintext:
            return None
        return json.loads(plaintext)
    except Exception:
        return None