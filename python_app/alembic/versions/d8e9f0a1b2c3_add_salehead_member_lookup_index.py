"""add brand member analysis lookup indexes

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
Create Date: 2026-07-14
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d8e9f0a1b2c3"
down_revision: Union[str, Sequence[str], None] = "c7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INDEX_NAME = "idx_salehead_mkt_member_no_billno"
GROUP_HISTORY_INDEX_NAME = "idx_sgl_market_mfid_hsrq_billno"


def upgrade() -> None:
    # salehead is a large fact table. Build concurrently so deployment does not
    # block ongoing POS data reads and writes while the index is being created.
    with op.get_context().autocommit_block():
        op.execute(
            sa.text(
                f"""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS {INDEX_NAME}
                ON salehead (
                    mkt,
                    (NULLIF(UPPER(TRIM(BOTH FROM COALESCE(hykh, ''))), '')),
                    billno
                )
                WHERE NULLIF(TRIM(BOTH FROM COALESCE(hykh, '')), '') IS NOT NULL
                """
            )
        )
        op.execute(
            sa.text(
                f"""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS {GROUP_HISTORY_INDEX_NAME}
                ON salegoodslist (sglmarket, sglmfid, sglhsrq, sglbillno)
                INCLUDE (sglxssr)
                """
            )
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(sa.text(f"DROP INDEX CONCURRENTLY IF EXISTS {GROUP_HISTORY_INDEX_NAME}"))
        op.execute(sa.text(f"DROP INDEX CONCURRENTLY IF EXISTS {INDEX_NAME}"))
