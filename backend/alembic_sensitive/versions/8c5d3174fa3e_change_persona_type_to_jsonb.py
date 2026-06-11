"""change persona_type to jsonb

Revision ID: 8c5d3174fa3e
Revises: 6700a48b527b
Create Date: 2026-06-11 06:00:08.983033

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql



# revision identifiers, used by Alembic.
revision: str = '8c5d3174fa3e'
down_revision: Union[str, Sequence[str], None] = '6700a48b527b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    counseling_sessions.persona_type: VARCHAR(30) → JSONB.
    
    JSONB로 가는 이유:
      - 페르소나 코드뿐 아니라 메타데이터(name, version, params)를 함께 저장 가능
      - personas.py가 향후 변경되어도 과거 세션이 깨지지 않음 (스냅샷 보존)
      - 사용자 커스텀 파라미터 수용 여지 확보
    
    데이터 변환 규칙:
      'empathy'  → {"code": "empathy"}
      'coaching' → {"code": "coaching"}
      'neutral'  → {"code": "neutral"}
      NULL       → {"code": "empathy"}  (COALESCE로 안전 디폴트 채움)
      기타 값(예: 시드의 'warm_listener') → {"code": "warm_listener"} 그대로 변환
        ※ 데이터 손실 방지를 위해 유효하지 않은 코드도 보존. 정리는 별도 작업으로.
    
    순서 (이 순서 안 지키면 실패):
      1) DEFAULT 'empathy' (text) 제거 — 안 떼면 ALTER TYPE이 DEFAULT를 jsonb로 캐스트하다 실패
      2) ALTER COLUMN ... TYPE jsonb USING ...
      3) 새 JSONB DEFAULT 부착
      4) NOT NULL 잠금 (페르소나는 항상 존재해야 정합성 보장)
    """
    # 1) 기존 VARCHAR DEFAULT 제거
    op.execute("""
        ALTER TABLE counseling_sessions
            ALTER COLUMN persona_type DROP DEFAULT
    """)

    # 2) 타입 변환 + 데이터 변환
    #    jsonb_build_object('code', val) → {"code": val} 형태의 jsonb 생성
    #    COALESCE: NULL을 'empathy'로 안전하게 보정
    op.execute("""
        ALTER TABLE counseling_sessions
            ALTER COLUMN persona_type TYPE jsonb
            USING jsonb_build_object(
                'code', COALESCE(persona_type, 'empathy')
            )
    """)

    # 3) 새 JSONB DEFAULT
    op.execute("""
        ALTER TABLE counseling_sessions
            ALTER COLUMN persona_type SET DEFAULT '{"code": "empathy"}'::jsonb
    """)

    # 4) NOT NULL 잠금
    op.execute("""
        ALTER TABLE counseling_sessions
            ALTER COLUMN persona_type SET NOT NULL
    """)


def downgrade() -> None:
    """
    JSONB → VARCHAR(30) 복원.
    
    ->> 연산자: jsonb에서 text 추출 (-> 는 jsonb 반환, ->> 는 text 반환)
    여기선 varchar로 되돌려야 하므로 ->> 사용.
    """
    op.execute("""
        ALTER TABLE counseling_sessions
            ALTER COLUMN persona_type DROP NOT NULL
    """)
    op.execute("""
        ALTER TABLE counseling_sessions
            ALTER COLUMN persona_type DROP DEFAULT
    """)
    op.execute("""
        ALTER TABLE counseling_sessions
            ALTER COLUMN persona_type TYPE varchar(30)
            USING (persona_type->>'code')
    """)
    op.execute("""
        ALTER TABLE counseling_sessions
            ALTER COLUMN persona_type SET DEFAULT 'empathy'
    """)