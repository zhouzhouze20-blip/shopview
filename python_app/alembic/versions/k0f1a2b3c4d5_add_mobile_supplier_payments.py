"""add mobile supplier-payment module for category managers

Revision ID: k0f1a2b3c4d5
Revises: j9e0f1a2b3c4
Create Date: 2026-08-26
"""

from alembic import op


revision = "k0f1a2b3c4d5"
down_revision = "j9e0f1a2b3c4"
branch_labels = None
depends_on = None


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
          'mobile.supplier_payments.view',
          '查看手机端供应商付款单',
          'mobile',
          'supplier_payments_view'
        )
        ON CONFLICT (permission_code) DO UPDATE SET
          permission_name = EXCLUDED.permission_name,
          module_code = EXCLUDED.module_code,
          action_code = EXCLUDED.action_code;

        INSERT INTO roles (
          role_code, role_name, role_level, is_system, is_active, created_at, updated_at
        )
        VALUES (
          'category_supplier_payment_viewer',
          '供应商付款单品类主管',
          620,
          TRUE,
          TRUE,
          NOW(),
          NOW()
        )
        ON CONFLICT (role_code) DO UPDATE SET
          role_name = EXCLUDED.role_name,
          role_level = EXCLUDED.role_level,
          is_system = TRUE,
          is_active = TRUE,
          updated_at = NOW();

        INSERT INTO role_permissions (role_id, permission_id, created_at)
        SELECT target_role.id, mobile_payment.id, NOW()
        FROM roles target_role
        CROSS JOIN permissions mobile_payment
        WHERE target_role.role_code = 'category_supplier_payment_viewer'
          AND mobile_payment.permission_code = 'mobile.supplier_payments.view'
        ON CONFLICT DO NOTHING;

        INSERT INTO user_roles (user_id, role_id, store_id, created_at)
        SELECT DISTINCT
          assignment.manager_user_id,
          target_role.id,
          assignment.store_id,
          NOW()
        FROM category_manager_brand_assignments assignment
        CROSS JOIN roles target_role
        WHERE assignment.is_active
          AND target_role.role_code = 'category_supplier_payment_viewer'
        ON CONFLICT DO NOTHING;

        INSERT INTO role_permissions (role_id, permission_id, created_at)
        SELECT existing.role_id, mobile_payment.id, NOW()
        FROM role_permissions existing
        JOIN permissions desktop_payment
          ON desktop_payment.id = existing.permission_id
         AND desktop_payment.permission_code = 'settlement.joint_payment_confirmation.view'
        CROSS JOIN permissions mobile_payment
        WHERE mobile_payment.permission_code = 'mobile.supplier_payments.view'
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id = (
          SELECT id FROM permissions WHERE permission_code = 'mobile.supplier_payments.view'
        );

        DELETE FROM user_roles
        WHERE role_id = (
          SELECT id FROM roles WHERE role_code = 'category_supplier_payment_viewer'
        );

        DELETE FROM roles
        WHERE role_code = 'category_supplier_payment_viewer';

        DELETE FROM permissions
        WHERE permission_code = 'mobile.supplier_payments.view';
        """
    )
