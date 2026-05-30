"""add contract mode to business_units

Revision ID: c9d0e1f2a3b4
Revises: f6a7b8c9d0e2
Create Date: 2026-05-30

"""
from typing import Sequence, Union

from alembic import op


revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE business_units
          ADD COLUMN IF NOT EXISTS contract_mode TEXT NOT NULL DEFAULT 'EXCLUSIVE';

        UPDATE business_units
        SET contract_mode = 'EXCLUSIVE'
        WHERE contract_mode IS NULL
           OR trim(contract_mode) = ''
           OR contract_mode = 'MASTER_SUB';

        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname = 'ck_business_units_contract_mode'
          ) THEN
            ALTER TABLE business_units
              ADD CONSTRAINT ck_business_units_contract_mode
              CHECK (contract_mode IN ('EXCLUSIVE', 'SHARED'));
          END IF;
        END $$;

        COMMENT ON COLUMN business_units.contract_mode
          IS '合同签约模式：EXCLUSIVE 独占同期间只允许一份有效合同；SHARED 共享同期间允许多份合同';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE business_units
          DROP CONSTRAINT IF EXISTS ck_business_units_contract_mode;

        ALTER TABLE business_units
          DROP COLUMN IF EXISTS contract_mode;
        """
    )
