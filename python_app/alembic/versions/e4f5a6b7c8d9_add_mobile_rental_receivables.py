"""add permission for mobile rental receivables

Revision ID: e4f5a6b7c8d9
Revises: d3f4a5b6c7d8
Create Date: 2026-08-15
"""
from typing import Sequence, Union

from alembic import op


revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "d3f4a5b6c7d8"
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
          'mobile.rental_receivables.view',
          '查看手机端租赁应收未收',
          'mobile',
          'rental_receivables_view'
        )
        ON CONFLICT (permission_code) DO UPDATE SET
          permission_name = EXCLUDED.permission_name,
          module_code = EXCLUDED.module_code,
          action_code = EXCLUDED.action_code;

        INSERT INTO role_permissions (role_id, permission_id, created_at)
        SELECT existing.role_id, mobile_receivables.id, NOW()
        FROM role_permissions existing
        JOIN permissions desktop_settlement
          ON desktop_settlement.id = existing.permission_id
         AND desktop_settlement.permission_code = 'settlement.view'
        CROSS JOIN permissions mobile_receivables
        WHERE mobile_receivables.permission_code = 'mobile.rental_receivables.view'
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
          WHERE permission_code = 'mobile.rental_receivables.view'
        );

        DELETE FROM permissions
        WHERE permission_code = 'mobile.rental_receivables.view';
        """
    )
