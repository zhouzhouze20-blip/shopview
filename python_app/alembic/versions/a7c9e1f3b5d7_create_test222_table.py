"""create test222 table

Revision ID: a7c9e1f3b5d7
Revises: d8e9f0a1b2c3
Create Date: 2026-07-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a7c9e1f3b5d7"
down_revision: Union[str, Sequence[str], None] = "d8e9f0a1b2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "test222",
        sa.Column("SHORE_CODE", sa.String(length=255), nullable=True),
        sa.Column("STORE_NAME", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("test222")
