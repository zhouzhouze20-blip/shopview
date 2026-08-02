"""add non-rental monthly revenue report permission

Revision ID: p4e5f6a7b8c9
Revises: o3d4e5f6a7b8
Create Date: 2026-07-30
"""
from typing import Sequence, Union

from alembic import op


revision: str = "p4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "o3d4e5f6a7b8"
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
        VALUES (
          'sales.non_rental_monthly_revenue.view',
          '查看OD0005非租赁品牌月度收益表',
          'sales',
          'non_rental_monthly_revenue_view'
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
         AND source.permission_code = 'sales.od0002.view'
        CROSS JOIN permissions target
        WHERE target.permission_code = 'sales.non_rental_monthly_revenue.view'
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id = (
          SELECT id
          FROM permissions
          WHERE permission_code = 'sales.non_rental_monthly_revenue.view'
        );

        DELETE FROM permissions
        WHERE permission_code = 'sales.non_rental_monthly_revenue.view';
        """
    )
