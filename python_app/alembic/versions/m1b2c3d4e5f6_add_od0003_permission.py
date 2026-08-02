"""add OD0003 center sales follow-up permission

Revision ID: m1b2c3d4e5f6
Revises: l0a1b2c3d4e5
Create Date: 2026-07-27
"""
from typing import Sequence, Union

from alembic import op


revision: str = "m1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "l0a1b2c3d4e5"
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
          'sales.od0003.view',
          '查看OD0003中心销售跟进表',
          'sales',
          'od0003_view'
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
        JOIN permissions target
          ON target.permission_code = 'sales.od0003.view'
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id = (
          SELECT id FROM permissions
          WHERE permission_code = 'sales.od0003.view'
        );
        DELETE FROM permissions
        WHERE permission_code = 'sales.od0003.view';
        """
    )
