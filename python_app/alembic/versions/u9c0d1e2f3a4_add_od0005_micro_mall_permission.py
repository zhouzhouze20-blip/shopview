"""add OD0005 micro-mall brand sales permission

Revision ID: u9c0d1e2f3a4
Revises: t8b9c0d1e2f3
Create Date: 2026-08-02
"""
from typing import Sequence, Union

from alembic import op


revision: str = "u9c0d1e2f3a4"
down_revision: Union[str, Sequence[str], None] = "t8b9c0d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE permissions
        SET permission_name = '查看非租赁品牌月度收益表'
        WHERE permission_code = 'sales.non_rental_monthly_revenue.view';

        INSERT INTO permissions (
          permission_code,
          permission_name,
          module_code,
          action_code
        )
        VALUES (
          'sales.od0005.view',
          '查看OD0005微商城品牌销售统计',
          'sales',
          'od0005_view'
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
         AND source.permission_code = 'sales.od0001.view'
        CROSS JOIN permissions target
        WHERE target.permission_code = 'sales.od0005.view'
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id = (
          SELECT id FROM permissions
          WHERE permission_code = 'sales.od0005.view'
        );
        DELETE FROM permissions
        WHERE permission_code = 'sales.od0005.view';

        UPDATE permissions
        SET permission_name = '查看OD0005非租赁品牌月度收益表'
        WHERE permission_code = 'sales.non_rental_monthly_revenue.view';
        """
    )
