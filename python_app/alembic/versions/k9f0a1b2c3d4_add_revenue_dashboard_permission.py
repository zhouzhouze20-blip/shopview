"""add revenue dashboard permission

Revision ID: k9f0a1b2c3d4
Revises: j8e9f0a1b2c3
Create Date: 2026-07-26
"""
from typing import Sequence, Union

from alembic import op


revision: str = "k9f0a1b2c3d4"
down_revision: Union[str, Sequence[str], None] = "j8e9f0a1b2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO permissions (permission_code, permission_name, module_code, action_code)
        VALUES (
          'revenue.dashboard.view',
          '查看收益看板',
          'revenue',
          'dashboard_view'
        )
        ON CONFLICT (permission_code) DO UPDATE SET
          permission_name = EXCLUDED.permission_name,
          module_code = EXCLUDED.module_code,
          action_code = EXCLUDED.action_code;

        INSERT INTO role_permissions (role_id, permission_id, created_at)
        SELECT existing.role_id, dashboard.id, NOW()
        FROM role_permissions existing
        JOIN permissions revenue_view
          ON revenue_view.id = existing.permission_id
         AND revenue_view.permission_code = 'revenue.view'
        CROSS JOIN permissions dashboard
        WHERE dashboard.permission_code = 'revenue.dashboard.view'
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id IN (
          SELECT id FROM permissions WHERE permission_code = 'revenue.dashboard.view'
        );
        DELETE FROM permissions WHERE permission_code = 'revenue.dashboard.view';
        """
    )
