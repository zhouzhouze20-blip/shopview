"""optimize OD0005 micro-mall cashier lookup

Revision ID: o4d5e6f7a8b9
Revises: n3c4d5e6f7a8
Create Date: 2026-09-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "o4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "n3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INDEX_NAME = "idx_sgl_micro_cashier_market_date"


def upgrade() -> None:
    connection = op.get_bind()
    has_salegoodslist = connection.execute(
        sa.text("SELECT to_regclass('public.salegoodslist') IS NOT NULL")
    ).scalar()
    if not has_salegoodslist:
        return

    # salegoodslist is a large, continuously updated fact table. Keep the index
    # limited to the three dedicated micro-mall cashiers and build it without
    # blocking POS writes. The expressions exactly match the report predicates.
    with op.get_context().autocommit_block():
        op.execute(
            sa.text(
                f"""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS {INDEX_NAME}
                ON salegoodslist (
                    (TRIM(BOTH FROM COALESCE(sglchecker, ''))),
                    (TRIM(BOTH FROM sglmarket::text)),
                    sgldate,
                    (TRIM(BOTH FROM sglmfid)),
                    sglbillno
                )
                INCLUDE (sglsl, sglsjje, sglxssr, sgltotzk, sgln2)
                WHERE TRIM(BOTH FROM COALESCE(sglchecker, ''))
                    IN ('300411', '600518', '500708')
                """
            )
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(sa.text(f"DROP INDEX CONCURRENTLY IF EXISTS {INDEX_NAME}"))
