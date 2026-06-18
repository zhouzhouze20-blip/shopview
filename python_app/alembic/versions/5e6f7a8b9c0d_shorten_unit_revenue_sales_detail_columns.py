"""shorten unit revenue sales detail columns

Revision ID: 5e6f7a8b9c0d
Revises: 4d5e6f7a8b9c
Create Date: 2026-06-05

"""
from typing import Sequence, Union

from alembic import op


revision: str = "5e6f7a8b9c0d"
down_revision: Union[str, Sequence[str], None] = "4d5e6f7a8b9c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


RENAMES = (
    (
        "tax_excluded_profit_adjustment",
        "tax_excl_profit_adjustment",
        "不含税毛利调整金额",
    ),
    (
        "guaranteed_adjustment_amount",
        "guaranteed_adjust_amount",
        "保底调整金额",
    ),
    (
        "original_deduction_profit_amount",
        "original_deduct_profit_amt",
        "原扣率毛利金额",
    ),
)


def _rename_if_needed(old_name: str, new_name: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'unit_revenue_sales_detail'
                  AND column_name = '{old_name}'
            ) AND NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'unit_revenue_sales_detail'
                  AND column_name = '{new_name}'
            ) THEN
                ALTER TABLE unit_revenue_sales_detail
                RENAME COLUMN {old_name} TO {new_name};
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    for old_name, new_name, comment in RENAMES:
        _rename_if_needed(old_name, new_name)
        op.execute(
            f"""
            COMMENT ON COLUMN unit_revenue_sales_detail.{new_name}
            IS '{comment}'
            """
        )


def downgrade() -> None:
    for old_name, new_name, comment in reversed(RENAMES):
        _rename_if_needed(new_name, old_name)
        op.execute(
            f"""
            COMMENT ON COLUMN unit_revenue_sales_detail.{old_name}
            IS '{comment}'
            """
        )
