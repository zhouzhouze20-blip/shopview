"""add OD0004 monthly sales follow-up permission

Revision ID: r6f7a8b9c0d1
Revises: q5e6f7a8b9c0
Create Date: 2026-07-31
"""
from typing import Sequence, Union

from alembic import op


revision: str = "r6f7a8b9c0d1"
down_revision: Union[str, Sequence[str], None] = "q5e6f7a8b9c0"
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
          'sales.od0004.view',
          '查看OD0004销售逐月跟进表',
          'sales',
          'od0004_view'
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
        WHERE target.permission_code = 'sales.od0004.view'
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id = (
          SELECT id FROM permissions
          WHERE permission_code = 'sales.od0004.view'
        );
        DELETE FROM permissions
        WHERE permission_code = 'sales.od0004.view';
        """
    )
