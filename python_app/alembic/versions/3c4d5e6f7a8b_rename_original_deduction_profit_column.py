"""rename original deduction profit column

Revision ID: 3c4d5e6f7a8b
Revises: 2b3c4d5e6f7a
Create Date: 2026-06-05

"""
from typing import Sequence, Union

from alembic import op


revision: str = "3c4d5e6f7a8b"
down_revision: Union[str, Sequence[str], None] = "2b3c4d5e6f7a"
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
                  AND column_name = 'original_deduction_gross_profit_amount'
            ) AND NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'unit_revenue_sales_detail'
                  AND column_name = 'original_deduction_profit_amount'
            ) THEN
                ALTER TABLE unit_revenue_sales_detail
                RENAME COLUMN original_deduction_gross_profit_amount TO original_deduction_profit_amount;
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        COMMENT ON COLUMN unit_revenue_sales_detail.original_deduction_profit_amount
        IS '原扣率毛利金额'
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
                  AND column_name = 'original_deduction_profit_amount'
            ) AND NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'unit_revenue_sales_detail'
                  AND column_name = 'original_deduction_gross_profit_amount'
            ) THEN
                ALTER TABLE unit_revenue_sales_detail
                RENAME COLUMN original_deduction_profit_amount TO original_deduction_gross_profit_amount;
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        COMMENT ON COLUMN unit_revenue_sales_detail.original_deduction_gross_profit_amount
        IS '原扣率毛利金额'
        """
    )
