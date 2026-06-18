"""rename unit revenue profit column

Revision ID: 2b3c4d5e6f7a
Revises: 1a2b3c4d5e6f
Create Date: 2026-06-05

"""
from typing import Sequence, Union

from alembic import op


revision: str = "2b3c4d5e6f7a"
down_revision: Union[str, Sequence[str], None] = "1a2b3c4d5e6f"
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
                  AND column_name = 'tax_excluded_gross_profit_amount'
            ) AND NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'unit_revenue_sales_detail'
                  AND column_name = 'tax_excluded_profit_amount'
            ) THEN
                ALTER TABLE unit_revenue_sales_detail
                RENAME COLUMN tax_excluded_gross_profit_amount TO tax_excluded_profit_amount;
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        COMMENT ON COLUMN unit_revenue_sales_detail.tax_excluded_profit_amount
        IS '不含税销售毛利，汇总时进入销售毛利收益'
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
                  AND column_name = 'tax_excluded_profit_amount'
            ) AND NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'unit_revenue_sales_detail'
                  AND column_name = 'tax_excluded_gross_profit_amount'
            ) THEN
                ALTER TABLE unit_revenue_sales_detail
                RENAME COLUMN tax_excluded_profit_amount TO tax_excluded_gross_profit_amount;
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        COMMENT ON COLUMN unit_revenue_sales_detail.tax_excluded_gross_profit_amount
        IS '不含税销售毛利，汇总时进入销售毛利收益'
        """
    )
