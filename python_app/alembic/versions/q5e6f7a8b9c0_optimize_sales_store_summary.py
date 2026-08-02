"""optimize long-range sales store summary

Revision ID: q5e6f7a8b9c0
Revises: p4e5f6a7b8c9
Create Date: 2026-07-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "q5e6f7a8b9c0"
down_revision: Union[str, Sequence[str], None] = "p4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INDEX_NAME = "idx_salegoodslist_hsrq_market_mfid_billno"


def upgrade() -> None:
    connection = op.get_bind()
    has_salegoodslist = connection.execute(
        sa.text("SELECT to_regclass('public.salegoodslist') IS NOT NULL")
    ).scalar()
    if not has_salegoodslist:
        return

    with op.get_context().autocommit_block():
        op.execute(
            sa.text(
                f"""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS {INDEX_NAME}
                ON salegoodslist (sglhsrq, sglmarket, sglmfid, sglbillno)
                INCLUDE (sglsl, sglxssr, sgln2)
                """
            )
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(sa.text(f"DROP INDEX CONCURRENTLY IF EXISTS {INDEX_NAME}"))
