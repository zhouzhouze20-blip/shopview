"""add independent sales report permissions

Revision ID: l0a1b2c3d4e5
Revises: k9f0a1b2c3d4
Create Date: 2026-07-27
"""
from typing import Sequence, Union

from alembic import op


revision: str = "l0a1b2c3d4e5"
down_revision: Union[str, Sequence[str], None] = "k9f0a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO permissions (
          permission_code,
          permission_name,
          module_code,
          action_code
        )
        VALUES
          (
            'sales.commodity_detail.view',
            '查看商品销售明细',
            'sales',
            'commodity_detail_view'
          ),
          (
            'sales.settled_gross_profit.view',
            '查看结算后销售毛利排行表',
            'sales',
            'settled_gross_profit_view'
          ),
          (
            'sales.od0001.view',
            '查看OD0001销售逐日跟进表',
            'sales',
            'od0001_view'
          )
        ON CONFLICT (permission_code) DO UPDATE SET
          permission_name = EXCLUDED.permission_name,
          module_code = EXCLUDED.module_code,
          action_code = EXCLUDED.action_code;

        INSERT INTO role_permissions (role_id, permission_id, created_at)
        SELECT existing.role_id, target.id, NOW()
        FROM role_permissions existing
        JOIN permissions source
          ON source.id = existing.permission_id
        JOIN (
          VALUES
            ('sales.view', 'sales.commodity_detail.view'),
            ('sales.od0002.view', 'sales.settled_gross_profit.view'),
            ('sales.od0002.view', 'sales.od0001.view')
        ) AS mapping(source_code, target_code)
          ON mapping.source_code = source.permission_code
        JOIN permissions target
          ON target.permission_code = mapping.target_code
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id IN (
          SELECT id
          FROM permissions
          WHERE permission_code IN (
            'sales.commodity_detail.view',
            'sales.settled_gross_profit.view',
            'sales.od0001.view'
          )
        );

        DELETE FROM permissions
        WHERE permission_code IN (
          'sales.commodity_detail.view',
          'sales.settled_gross_profit.view',
          'sales.od0001.view'
        );
        """
    )
