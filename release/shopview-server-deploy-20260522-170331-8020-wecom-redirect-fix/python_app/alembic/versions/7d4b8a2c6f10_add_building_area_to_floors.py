"""add building_area to floors

Revision ID: 7d4b8a2c6f10
Revises: 3c9a0c7b1f4e
Create Date: 2026-04-15
"""

from typing import Sequence, Union

from alembic import op


revision: str = "7d4b8a2c6f10"
down_revision: Union[str, Sequence[str], None] = "3c9a0c7b1f4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE floors ADD COLUMN IF NOT EXISTS building_area NUMERIC(12, 2)")
    op.execute("COMMENT ON COLUMN floors.building_area IS '建筑面积（平方米）'")


def downgrade() -> None:
    op.execute("ALTER TABLE floors DROP COLUMN IF EXISTS building_area")
