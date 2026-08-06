"""add store other business income report permission

Revision ID: z4b5c6d7e8f9
Revises: y3a4b5c6d7e8
Create Date: 2026-08-04
"""
from typing import Sequence, Union

from alembic import op


revision: str = "z4b5c6d7e8f9"
down_revision: Union[str, Sequence[str], None] = "y3a4b5c6d7e8"
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
          'sales.store_other_business_income.view',
          '查看门店其他业务收入',
          'sales',
          'store_other_business_income_view'
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
        WHERE target.permission_code = 'sales.store_other_business_income.view'
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id = (
          SELECT id FROM permissions
          WHERE permission_code = 'sales.store_other_business_income.view'
        );
        DELETE FROM permissions
        WHERE permission_code = 'sales.store_other_business_income.view';
        """
    )
