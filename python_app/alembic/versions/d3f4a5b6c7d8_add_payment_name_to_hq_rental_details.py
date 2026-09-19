"""Add payment-mode name for rental settlement deduction detail lines.

Revision ID: d3f4a5b6c7d8
Revises: c2e3f4a5b6c7
"""

from typing import Sequence, Union

from alembic import op


revision: str = "d3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "c2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE ods.hq_supsettledettot ADD COLUMN payment_name_raw TEXT"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE ods.hq_supsettledettot DROP COLUMN IF EXISTS payment_name_raw"
    )
