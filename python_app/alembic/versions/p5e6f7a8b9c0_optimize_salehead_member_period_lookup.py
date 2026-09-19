"""optimize brand-member receipt lookup by member and period

Revision ID: p5e6f7a8b9c0
Revises: o4d5e6f7a8b9
Create Date: 2026-09-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "p5e6f7a8b9c0"
down_revision: Union[str, Sequence[str], None] = "o4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INDEX_NAME = "idx_salehead_mkt_member_no_rqsj_billno"


def upgrade() -> None:
    connection = op.get_bind()
    has_salehead = connection.execute(
        sa.text("SELECT to_regclass('public.salehead') IS NOT NULL")
    ).scalar()
    if not has_salehead:
        return

    # The member-analysis paths first reduce to a member set and then resolve
    # only those members' receipts in a bounded period. Build concurrently so
    # POS reads and writes are not blocked on this large fact table.
    with op.get_context().autocommit_block():
        op.execute(
            sa.text(
                f"""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS {INDEX_NAME}
                ON salehead (
                    mkt,
                    (NULLIF(UPPER(TRIM(BOTH FROM COALESCE(hykh, ''))), '')),
                    rqsj,
                    billno
                )
                WHERE NULLIF(TRIM(BOTH FROM COALESCE(hykh, '')), '') IS NOT NULL
                """
            )
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(sa.text(f"DROP INDEX CONCURRENTLY IF EXISTS {INDEX_NAME}"))
