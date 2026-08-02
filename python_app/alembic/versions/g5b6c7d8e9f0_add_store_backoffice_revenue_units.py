"""add one backoffice revenue logical unit per operating store

Revision ID: g5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-07-23
"""
from typing import Sequence, Union

from alembic import op


revision: str = "g5b6c7d8e9f0"
down_revision: Union[str, Sequence[str], None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


BACKOFFICE_FLOOR_CODE = "BO"
BACKOFFICE_FLOOR_NAME = "后台部门"
BACKOFFICE_UNIT_CODE = "后台部门收益"


def upgrade() -> None:
    # 只处理已有实际楼层的在用门店，避免为 STORE001 等空白测试门店造数据。
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
          '{BACKOFFICE_UNIT_CODE}',
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
          AND trim(bu.unit_code) = '{BACKOFFICE_UNIT_CODE}'
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
    op.execute(
        f"""
        DELETE FROM floors f
        WHERE f.floor_code = '{BACKOFFICE_FLOOR_CODE}'
          AND f.name = '{BACKOFFICE_FLOOR_NAME}'
          AND f.building_code = f.store_code || '-BO'
          AND NOT EXISTS (
            SELECT 1 FROM business_units bu WHERE bu.floor_id = f.id
          )
          AND NOT EXISTS (
            SELECT 1 FROM base_maps bm WHERE bm.floor_id = f.id
          )
          AND NOT EXISTS (
            SELECT 1 FROM unit_map_versions umv WHERE umv.floor_id = f.id
          );
        """
    )
