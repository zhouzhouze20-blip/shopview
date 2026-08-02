"""add independent mobile module permissions

Revision ID: n2c3d4e5f6a7
Revises: m1b2c3d4e5f6
Create Date: 2026-07-28
"""
from typing import Sequence, Union

from alembic import op


revision: str = "n2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "m1b2c3d4e5f6"
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
            'mobile.sales.view',
            '查看手机端销售看板',
            'mobile',
            'sales_view'
          ),
          (
            'mobile.contracts.view',
            '查看手机端合同台账',
            'mobile',
            'contracts_view'
          ),
          (
            'mobile.inventory.view',
            '查看手机端实时库存查询',
            'mobile',
            'inventory_view'
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
            ('sales.view', 'mobile.sales.view'),
            ('contract.view', 'mobile.contracts.view'),
            ('sales.inventory.view', 'mobile.inventory.view')
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
            'mobile.sales.view',
            'mobile.contracts.view',
            'mobile.inventory.view'
          )
        );

        DELETE FROM permissions
        WHERE permission_code IN (
          'mobile.sales.view',
          'mobile.contracts.view',
          'mobile.inventory.view'
        );
        """
    )
