"""add one multi-business logical unit per operating store

Revision ID: i7d8e9f0a1b2
Revises: h6c7d8e9f0a1
Create Date: 2026-07-24
"""
from typing import Sequence, Union

from alembic import op


revision: str = "i7d8e9f0a1b2"
down_revision: Union[str, Sequence[str], None] = "h6c7d8e9f0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


BACKOFFICE_FLOOR_CODE = "BO"
BACKOFFICE_FLOOR_NAME = "后台部门"
MULTI_BUSINESS_UNIT_CODE = "多经"


def upgrade() -> None:
    # 复用店级逻辑柜位楼层；只处理已有实际楼层的在用门店。
    op.execute(
        f"""
        INSERT INTO floors (
          store_code,
          building_code,
          floor_code,
          name,
          sort_no
        )
        SELECT
          s.store_code,
          s.store_code || '-BO',
          '{BACKOFFICE_FLOOR_CODE}',
          '{BACKOFFICE_FLOOR_NAME}',
          999
        FROM stores s
        WHERE COALESCE(s.is_active, TRUE)
          AND EXISTS (
            SELECT 1
            FROM floors existing_floor
            WHERE existing_floor.store_code = s.store_code
              AND NOT (
                existing_floor.floor_code = '{BACKOFFICE_FLOOR_CODE}'
                AND existing_floor.building_code = s.store_code || '-BO'
              )
          )
        ON CONFLICT (store_code, building_code, floor_code) DO UPDATE SET
          name = EXCLUDED.name,
          sort_no = EXCLUDED.sort_no;
        """
    )
    op.execute(
        f"""
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
          '{MULTI_BUSINESS_UNIT_CODE}',
          'ACTIVE',
          'SHARED',
          NULL,
          NULL
        FROM floors f
        WHERE f.floor_code = '{BACKOFFICE_FLOOR_CODE}'
          AND f.name = '{BACKOFFICE_FLOOR_NAME}'
          AND f.building_code = f.store_code || '-BO'
        ON CONFLICT (floor_id, unit_code) DO UPDATE SET
          status = 'ACTIVE',
          contract_mode = 'SHARED',
          updated_at = NOW();
        """
    )


def downgrade() -> None:
    op.execute(
        f"""
        DELETE FROM business_units bu
        USING floors f
        WHERE bu.floor_id = f.id
          AND trim(bu.unit_code) = '{MULTI_BUSINESS_UNIT_CODE}'
          AND f.floor_code = '{BACKOFFICE_FLOOR_CODE}'
          AND f.name = '{BACKOFFICE_FLOOR_NAME}'
          AND f.building_code = f.store_code || '-BO'
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
