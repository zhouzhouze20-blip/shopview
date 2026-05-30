"""make business_unit_binding shop_unit_id optional

Revision ID: e5f6a7b8c9d1
Revises: d3e4f5a6b7c8
Create Date: 2026-05-27

"""
from typing import Sequence, Union

from alembic import op


revision: str = "e5f6a7b8c9d1"
down_revision: Union[str, Sequence[str], None] = "d3e4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE business_unit_binding
          DROP CONSTRAINT IF EXISTS fk_bub_shop_unit;

        ALTER TABLE business_unit_binding
          ALTER COLUMN shop_unit_id DROP NOT NULL;

        ALTER TABLE business_unit_binding
          ADD CONSTRAINT fk_bub_shop_unit
          FOREIGN KEY (shop_unit_id)
          REFERENCES business_units(id)
          ON DELETE SET NULL;

        COMMENT ON COLUMN business_unit_binding.shop_unit_id
          IS '铺位ID，对应 business_units.id；图纸变更删除经营单元时可暂时为空，后续重新关联';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM business_unit_binding WHERE shop_unit_id IS NULL;

        ALTER TABLE business_unit_binding
          DROP CONSTRAINT IF EXISTS fk_bub_shop_unit;

        ALTER TABLE business_unit_binding
          ALTER COLUMN shop_unit_id SET NOT NULL;

        ALTER TABLE business_unit_binding
          ADD CONSTRAINT fk_bub_shop_unit
          FOREIGN KEY (shop_unit_id)
          REFERENCES business_units(id)
          ON DELETE RESTRICT;

        COMMENT ON COLUMN business_unit_binding.shop_unit_id
          IS '铺位ID，对应 business_units.id';
        """
    )
