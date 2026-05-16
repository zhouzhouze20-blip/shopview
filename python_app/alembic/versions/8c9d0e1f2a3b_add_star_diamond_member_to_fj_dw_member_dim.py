"""add star diamond member flag to fj_dw_member_dim

Revision ID: 8c9d0e1f2a3b
Revises: 7b8c9d0e1f2a
Create Date: 2026-05-13
"""
from typing import Sequence, Union

from alembic import op


revision: str = "8c9d0e1f2a3b"
down_revision: Union[str, Sequence[str], None] = "7b8c9d0e1f2a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE fj_dw_member_dim
        ADD COLUMN IF NOT EXISTS is_star_diamond_member VARCHAR(10);

        COMMENT ON COLUMN fj_dw_member_dim.is_star_diamond_member IS '是否星钻会员';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE fj_dw_member_dim
        DROP COLUMN IF EXISTS is_star_diamond_member;
        """
    )
