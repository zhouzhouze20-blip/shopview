"""add permission for mobile C-coupon member follow-up

Revision ID: g6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-08-17
"""
from typing import Sequence, Union

from alembic import op


revision: str = "g6b7c8d9e0f1"
down_revision: Union[str, Sequence[str], None] = "f5a6b7c8d9e0"
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
          'mobile.coupon_followup.view',
          '查看手机端C券会员跟进',
          'mobile',
          'coupon_followup_view'
        )
        ON CONFLICT (permission_code) DO UPDATE SET
          permission_name = EXCLUDED.permission_name,
          module_code = EXCLUDED.module_code,
          action_code = EXCLUDED.action_code;

        INSERT INTO roles (
          role_code, role_name, role_level, is_system, is_active, created_at, updated_at
        )
        VALUES (
          'category_coupon_followup_manager', 'C券会员跟进品类主管', 610, TRUE, TRUE, NOW(), NOW()
        )
        ON CONFLICT (role_code) DO UPDATE SET
          role_name = EXCLUDED.role_name,
          role_level = EXCLUDED.role_level,
          is_system = TRUE,
          is_active = TRUE,
          updated_at = NOW();

        INSERT INTO role_permissions (role_id, permission_id, created_at)
        SELECT target_role.id, mobile_followup.id, NOW()
        FROM roles target_role
        CROSS JOIN permissions mobile_followup
        WHERE target_role.role_code = 'category_coupon_followup_manager'
          AND mobile_followup.permission_code = 'mobile.coupon_followup.view'
        ON CONFLICT DO NOTHING;

        INSERT INTO user_roles (user_id, role_id, store_id, created_at)
        SELECT DISTINCT
          assignment.manager_user_id,
          target_role.id,
          assignment.store_id,
          NOW()
        FROM category_manager_brand_assignments assignment
        JOIN stores store_row
          ON store_row.store_id = assignment.store_id
         AND TRIM(store_row.store_code) = '601'
        CROSS JOIN roles target_role
        WHERE assignment.is_active
          AND target_role.role_code = 'category_coupon_followup_manager'
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE role_id = (SELECT id FROM roles WHERE role_code = 'category_coupon_followup_manager');

        DELETE FROM user_roles
        WHERE role_id = (SELECT id FROM roles WHERE role_code = 'category_coupon_followup_manager');

        DELETE FROM roles
        WHERE role_code = 'category_coupon_followup_manager';

        DELETE FROM permissions
        WHERE permission_code = 'mobile.coupon_followup.view';
        """
    )
