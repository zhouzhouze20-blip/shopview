"""rename non-rental monthly revenue report to OD0005

Revision ID: s7a8b9c0d1e2
Revises: r6f7a8b9c0d1
Create Date: 2026-08-01
"""
from typing import Sequence, Union

from alembic import op


revision: str = "s7a8b9c0d1e2"
down_revision: Union[str, Sequence[str], None] = "r6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE permissions
        SET permission_name = '查看OD0005非租赁品牌月度收益表'
        WHERE permission_code = 'sales.non_rental_monthly_revenue.view';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE permissions
        SET permission_name = '查看非租赁品牌月度收益表'
        WHERE permission_code = 'sales.non_rental_monthly_revenue.view';
        """
    )
