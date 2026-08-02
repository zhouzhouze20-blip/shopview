"""open baseline mobile modules and add mobile revenue dashboard

Revision ID: o3d4e5f6a7b8
Revises: n2c3d4e5f6a7
Create Date: 2026-07-28
"""
from typing import Sequence, Union

from alembic import op


revision: str = "o3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "n2c3d4e5f6a7"
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
          'mobile.revenue_dashboard.view',
          '查看手机端收益看板',
          'mobile',
          'revenue_dashboard_view'
        )
        ON CONFLICT (permission_code) DO UPDATE SET
          permission_name = EXCLUDED.permission_name,
          module_code = EXCLUDED.module_code,
          action_code = EXCLUDED.action_code;

        INSERT INTO role_permissions (role_id, permission_id, created_at)
        SELECT role_row.id, permission_row.id, NOW()
        FROM roles role_row
        CROSS JOIN permissions permission_row
        WHERE permission_row.permission_code IN (
          'mobile.sales.view',
          'mobile.contracts.view',
          'mobile.inventory.view'
        )
        ON CONFLICT DO NOTHING;

        INSERT INTO role_permissions (role_id, permission_id, created_at)
        SELECT existing.role_id, mobile_revenue.id, NOW()
        FROM role_permissions existing
        JOIN permissions desktop_revenue
          ON desktop_revenue.id = existing.permission_id
         AND desktop_revenue.permission_code = 'revenue.dashboard.view'
        CROSS JOIN permissions mobile_revenue
        WHERE mobile_revenue.permission_code = 'mobile.revenue_dashboard.view'
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
          WHERE permission_code = 'mobile.revenue_dashboard.view'
        );

        DELETE FROM permissions
        WHERE permission_code = 'mobile.revenue_dashboard.view';
        """
    )
