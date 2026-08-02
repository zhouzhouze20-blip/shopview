"""add contract unit-binding edit permission

Revision ID: e3f4a5b6c7d8
Revises: d1b3c5e7f9a2
Create Date: 2026-07-21
"""
from typing import Sequence, Union

from alembic import op


revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "d1b3c5e7f9a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO permissions (permission_code, permission_name, module_code, action_code)
        VALUES (
          'contract.unit_binding.edit',
          '编辑合同柜位号',
          'contract',
          'unit_binding_edit'
        )
        ON CONFLICT (permission_code) DO UPDATE SET
          permission_name = EXCLUDED.permission_name,
          module_code = EXCLUDED.module_code,
          action_code = EXCLUDED.action_code;

        INSERT INTO role_permissions (role_id, permission_id, created_at)
        SELECT r.id, p.id, NOW()
        FROM roles r
        JOIN permissions p ON p.permission_code = 'contract.unit_binding.edit'
        WHERE r.role_code IN ('super_admin', 'system_admin')
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id IN (
          SELECT id FROM permissions WHERE permission_code = 'contract.unit_binding.edit'
        );
        DELETE FROM permissions WHERE permission_code = 'contract.unit_binding.edit';
        """
    )
