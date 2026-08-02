"""add one shared mobile special-sale logical unit per floor

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-07-23
"""
from typing import Sequence, Union

from alembic import op


revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, Sequence[str], None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO business_units (
          floor_id,
          unit_code,
          status,
          contract_mode,
          manual_area,
          parent_unit_id
        )
        SELECT
          f.id,
          '流动特卖',
          'ACTIVE',
          'SHARED',
          NULL,
          NULL
        FROM floors f
        ON CONFLICT (floor_id, unit_code) DO UPDATE SET
          status = 'ACTIVE',
          contract_mode = 'SHARED',
          updated_at = NOW();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM business_units bu
        WHERE trim(bu.unit_code) = '流动特卖'
          AND NOT EXISTS (
            SELECT 1
            FROM business_unit_binding b
            WHERE b.shop_unit_id = bu.id
          )
          AND NOT EXISTS (
            SELECT 1
            FROM geo_elements ge
            WHERE ge.unit_id = bu.id
          );
        """
    )
