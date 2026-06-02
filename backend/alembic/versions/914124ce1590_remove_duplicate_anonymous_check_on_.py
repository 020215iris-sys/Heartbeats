"""remove duplicate anonymous CHECK on users.role

Revision ID: 914124ce1590
Revises: 543f6f4d60bf
Create Date: 2026-06-02 11:46:50.126847

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '914124ce1590'
down_revision: Union[str, Sequence[str], None] = '543f6f4d60bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('users_role_check', 'users', type_='check')
    pass


def downgrade() -> None:
    op.create_check_constraint(
        'users_role_check',                                    # 같은 이름으로 복원
        'users',
        "role IN ('user', 'guardian', 'admin')"
    )   
    pass
