"""add Zhao Jia manual sports department scope

Revision ID: j8e9f0a1b2c3
Revises: i7d8e9f0a1b2
Create Date: 2026-07-24
"""
from typing import Sequence, Union

from alembic import op


revision: str = "j8e9f0a1b2c3"
down_revision: Union[str, Sequence[str], None] = "i7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


USERNAME = "1708"
REAL_NAME = "赵佳"
DEPARTMENT_CODE = "6030114"
EXTERNAL_SCOPE_PREFIX = "manual-business-scope"


def upgrade() -> None:
    op.execute(
        f"""
        INSERT INTO data_policies (
          subject_type,
          subject_id,
          resource_code,
          action_code,
          scope_mode,
          effect,
          priority,
          is_active,
          source_type,
          source_system,
          external_scope_id,
          external_scope_name,
          created_at,
          updated_at
        )
        SELECT
          'USER',
          u.user_id,
          'business_scope',
          'view',
          'CUSTOM',
          'ALLOW',
          100,
          TRUE,
          'MANUAL',
          'shopview',
          '{EXTERNAL_SCOPE_PREFIX}:' || u.user_id,
          u.real_name || ' 手工业务范围',
          NOW(),
          NOW()
        FROM users u
        WHERE u.username = '{USERNAME}'
          AND u.real_name = '{REAL_NAME}'
          AND COALESCE(u.is_active, TRUE)
          AND NOT EXISTS (
            SELECT 1
            FROM data_policies existing
            WHERE existing.subject_type = 'USER'
              AND existing.subject_id = u.user_id
              AND existing.resource_code = 'business_scope'
              AND existing.action_code = 'view'
              AND existing.source_type = 'MANUAL'
              AND existing.source_system = 'shopview'
              AND existing.external_scope_id = '{EXTERNAL_SCOPE_PREFIX}:' || u.user_id
          );
        """
    )
    op.execute(
        f"""
        INSERT INTO data_policy_items (
          policy_id,
          dimension_type,
          dimension_value,
          include_children,
          created_at
        )
        SELECT
          policy.id,
          'department',
          '{DEPARTMENT_CODE}',
          FALSE,
          NOW()
        FROM data_policies policy
        JOIN users u
          ON u.user_id = policy.subject_id
        WHERE u.username = '{USERNAME}'
          AND u.real_name = '{REAL_NAME}'
          AND policy.subject_type = 'USER'
          AND policy.resource_code = 'business_scope'
          AND policy.action_code = 'view'
          AND policy.source_type = 'MANUAL'
          AND policy.source_system = 'shopview'
          AND policy.external_scope_id = '{EXTERNAL_SCOPE_PREFIX}:' || u.user_id
          AND NOT EXISTS (
            SELECT 1
            FROM data_policy_items existing_item
            WHERE existing_item.policy_id = policy.id
              AND existing_item.dimension_type = 'department'
              AND existing_item.dimension_value = '{DEPARTMENT_CODE}'
          );
        """
    )


def downgrade() -> None:
    op.execute(
        f"""
        DELETE FROM data_policy_items item
        USING data_policies policy, users u
        WHERE item.policy_id = policy.id
          AND policy.subject_id = u.user_id
          AND u.username = '{USERNAME}'
          AND u.real_name = '{REAL_NAME}'
          AND policy.source_type = 'MANUAL'
          AND policy.source_system = 'shopview'
          AND policy.external_scope_id = '{EXTERNAL_SCOPE_PREFIX}:' || u.user_id
          AND item.dimension_type = 'department'
          AND item.dimension_value = '{DEPARTMENT_CODE}';
        """
    )
    op.execute(
        f"""
        DELETE FROM data_policies policy
        USING users u
        WHERE policy.subject_id = u.user_id
          AND u.username = '{USERNAME}'
          AND u.real_name = '{REAL_NAME}'
          AND policy.source_type = 'MANUAL'
          AND policy.source_system = 'shopview'
          AND policy.external_scope_id = '{EXTERNAL_SCOPE_PREFIX}:' || u.user_id
          AND NOT EXISTS (
            SELECT 1
            FROM data_policy_items item
            WHERE item.policy_id = policy.id
          );
        """
    )
