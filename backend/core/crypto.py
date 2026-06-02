# backend/core/crypto.py
"""
대화 본문 암호화 헬퍼 (W1: 투명 / W2: AES-256-GCM)

W1 단계 정책
- encrypt_content: 평문 str → UTF-8 바이트로 변환만 (실제 암호화 X)
- decrypt_content: UTF-8 바이트 → 평문 str로 변환
- key_id: 'DEV_PLAINTEXT_V1' 고정 (실제 키 없음을 명시)

W2 교체 시 변경할 것
- 본 모듈 내부만 진짜 AES-256-GCM 구현으로 교체
- 호출부(services/repositories) 코드는 한 줄도 안 바뀜
- key_id 정책: 'AES256GCM_V1' 같은 식으로 버전 관리

⚠️ 이 모듈을 호출하지 않고 직접 DB에 평문/바이트를 쓰면 W2 전환 시 데이터 깨짐.
   반드시 conversations.encrypted_content 다루는 모든 경로는 이 함수를 통과해야 함.
"""

# W1 단계 상수
_DEV_KEY_ID = "DEV_PLAINTEXT_V1"


def encrypt_content(plaintext: str) -> tuple[bytes, str]:
    """
    평문을 저장 가능한 바이트로 변환.

    Args:
        plaintext: 사용자 또는 AI의 메시지 평문

    Returns:
        (ciphertext_bytes, key_id) — DB의 encrypted_content + encryption_key_id 컬럼에 들어갈 값
    """
    if not isinstance(plaintext, str):
        raise TypeError(f"plaintext는 str이어야 함, got {type(plaintext)}")
    ciphertext = plaintext.encode("utf-8")
    return ciphertext, _DEV_KEY_ID


def decrypt_content(ciphertext: bytes, key_id: str) -> str:
    """
    저장된 바이트를 평문 str로 복원.

    Args:
        ciphertext: DB의 encrypted_content (BYTEA로 읽힌 bytes)
        key_id: DB의 encryption_key_id

    Returns:
        평문 문자열
    """
    if not isinstance(ciphertext, (bytes, memoryview, bytearray)):
        raise TypeError(f"ciphertext는 bytes여야 함, got {type(ciphertext)}")

    # W1: key_id 무시 (검증만 — 미래 키 회전 대비)
    if key_id != _DEV_KEY_ID:
        # 알 수 없는 key_id (W2 전환 후 옛 데이터일 수 있음)
        # 일단 UTF-8로 시도, 실패하면 에러
        pass

    return bytes(ciphertext).decode("utf-8")