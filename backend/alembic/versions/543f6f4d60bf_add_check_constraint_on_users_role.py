"""add CHECK constraint on users.role

Revision ID: 543f6f4d60bf
Revises: 8a8788af5a2c
Create Date: 2026-06-02 02:21:53.573138

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '543f6f4d60bf'
down_revision: Union[str, Sequence[str], None] = '8a8788af5a2c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        constraint_name='ck_users_role_valid',
        table_name='users',
        condition="role IN ('user', 'guardian', 'admin')"
    )


def downgrade() -> None:
    op.drop_constraint(
        constraint_name='ck_users_role_valid',
        table_name='users',
        type_='check'
    )
    pass
