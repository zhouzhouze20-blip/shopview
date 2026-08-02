"""add HY0001 key-brand member consumption permission

Revision ID: t8b9c0d1e2f3
Revises: s7a8b9c0d1e2
Create Date: 2026-08-02
"""
from typing import Sequence, Union

from alembic import op


revision: str = "t8b9c0d1e2f3"
down_revision: Union[str, Sequence[str], None] = "s7a8b9c0d1e2"
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
          'sales.hy0001.view',
          '查看HY0001重点品牌会员消费情况',
          'sales',
          'hy0001_view'
        )
        ON CONFLICT (permission_code) DO UPDATE SET
          permission_name = EXCLUDED.permission_name,
          module_code = EXCLUDED.module_code,
          action_code = EXCLUDED.action_code;

        INSERT INTO role_permissions (role_id, permission_id, created_at)
        SELECT DISTINCT existing.role_id, target.id, NOW()
        FROM role_permissions existing
        JOIN permissions source
          ON source.id = existing.permission_id
         AND source.permission_code IN (
           'sales.category_performance.view',
           'sales.brand_member_analysis.view'
         )
        CROSS JOIN permissions target
        WHERE target.permission_code = 'sales.hy0001.view'
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id = (
          SELECT id FROM permissions
          WHERE permission_code = 'sales.hy0001.view'
        );
        DELETE FROM permissions
        WHERE permission_code = 'sales.hy0001.view';
        """
    )
