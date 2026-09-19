"""expand month-close fee type code for combined Fuji codes

Revision ID: c7e8f9a0b1c2
Revises: b6d7e8f9a0b1
Create Date: 2026-08-07
"""
from typing import Sequence, Union

from alembic import op


revision: str = "c7e8f9a0b1c2"
down_revision: Union[str, Sequence[str], None] = "b6d7e8f9a0b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE revenue_month_close_adjustments
          ALTER COLUMN fee_type_code TYPE VARCHAR(100);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE revenue_month_close_adjustments
          ALTER COLUMN fee_type_code TYPE VARCHAR(50);
        """
    )
