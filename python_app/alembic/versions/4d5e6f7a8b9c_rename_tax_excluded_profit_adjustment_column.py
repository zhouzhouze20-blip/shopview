"""rename tax excluded profit adjustment column

Revision ID: 4d5e6f7a8b9c
Revises: 3c4d5e6f7a8b
Create Date: 2026-06-05

"""
from typing import Sequence, Union

from alembic import op


revision: str = "4d5e6f7a8b9c"
down_revision: Union[str, Sequence[str], None] = "3c4d5e6f7a8b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'unit_revenue_sales_detail'
                  AND column_name = 'tax_excluded_gross_profit_adjustment'
            ) AND NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'unit_revenue_sales_detail'
                  AND column_name = 'tax_excluded_profit_adjustment'
            ) THEN
                ALTER TABLE unit_revenue_sales_detail
                RENAME COLUMN tax_excluded_gross_profit_adjustment TO tax_excluded_profit_adjustment;
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        COMMENT ON COLUMN unit_revenue_sales_detail.tax_excluded_profit_adjustment
        IS '不含税毛利调整金额'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'unit_revenue_sales_detail'
                  AND column_name = 'tax_excluded_profit_adjustment'
            ) AND NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'unit_revenue_sales_detail'
                  AND column_name = 'tax_excluded_gross_profit_adjustment'
            ) THEN
                ALTER TABLE unit_revenue_sales_detail
                RENAME COLUMN tax_excluded_profit_adjustment TO tax_excluded_gross_profit_adjustment;
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        COMMENT ON COLUMN unit_revenue_sales_detail.tax_excluded_gross_profit_adjustment
        IS '不含税毛利调整金额'
        """
    )
