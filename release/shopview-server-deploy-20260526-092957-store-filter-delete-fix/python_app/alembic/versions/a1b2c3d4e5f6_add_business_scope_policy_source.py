"""add business scope policy source

Revision ID: a1b2c3d4e5f6
Revises: f4a7b8c9d0e1
Create Date: 2026-05-01

"""
from typing import Sequence, Union

from alembic import op


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f4a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_SQL = r"""
ALTER TABLE data_policies ADD COLUMN IF NOT EXISTS source_type VARCHAR(20) NOT NULL DEFAULT 'MANUAL';
ALTER TABLE data_policies ADD COLUMN IF NOT EXISTS source_system VARCHAR(50) NOT NULL DEFAULT 'shopview';
ALTER TABLE data_policies ADD COLUMN IF NOT EXISTS external_scope_id VARCHAR(100);
ALTER TABLE data_policies ADD COLUMN IF NOT EXISTS external_scope_name VARCHAR(200);
ALTER TABLE data_policies ADD COLUMN IF NOT EXISTS synced_at TIMESTAMP;

CREATE INDEX IF NOT EXISTS ix_data_policies_source
    ON data_policies(source_type, source_system, external_scope_id);

INSERT INTO permissions (permission_code, permission_name, module_code, action_code)
VALUES
    ('sales.view', '查看销售', 'sales', 'view'),
    ('settlement.view', '查看结算单', 'settlement', 'view')
ON CONFLICT (permission_code) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.permission_code IN ('sales.view', 'settlement.view')
WHERE r.role_code = 'super_admin'
ON CONFLICT DO NOTHING;

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
    synced_at,
    created_at,
    updated_at
)
SELECT
    old.subject_type,
    old.subject_id,
    'business_scope',
    'view',
    old.scope_mode,
    old.effect,
    old.priority,
    old.is_active,
    COALESCE(old.source_type, 'MANUAL'),
    COALESCE(old.source_system, 'shopview'),
    old.external_scope_id,
    old.external_scope_name,
    old.synced_at,
    NOW(),
    NOW()
FROM data_policies old
WHERE old.resource_code = 'contract'
  AND old.action_code = 'view'
  AND NOT EXISTS (
      SELECT 1
      FROM data_policies existing
      WHERE existing.subject_type = old.subject_type
        AND existing.subject_id = old.subject_id
        AND existing.resource_code = 'business_scope'
        AND existing.action_code = 'view'
        AND existing.effect = old.effect
        AND existing.scope_mode = old.scope_mode
        AND COALESCE(existing.source_type, 'MANUAL') = COALESCE(old.source_type, 'MANUAL')
        AND COALESCE(existing.source_system, 'shopview') = COALESCE(old.source_system, 'shopview')
        AND COALESCE(existing.external_scope_id, '') = COALESCE(old.external_scope_id, '')
  );

INSERT INTO data_policy_items (
    policy_id,
    dimension_type,
    dimension_value,
    include_children,
    created_at
)
SELECT
    new_policy.id,
    item.dimension_type,
    item.dimension_value,
    item.include_children,
    NOW()
FROM data_policies old_policy
JOIN data_policies new_policy
  ON new_policy.subject_type = old_policy.subject_type
 AND new_policy.subject_id = old_policy.subject_id
 AND new_policy.resource_code = 'business_scope'
 AND new_policy.action_code = 'view'
 AND new_policy.effect = old_policy.effect
 AND new_policy.scope_mode = old_policy.scope_mode
 AND COALESCE(new_policy.source_type, 'MANUAL') = COALESCE(old_policy.source_type, 'MANUAL')
 AND COALESCE(new_policy.source_system, 'shopview') = COALESCE(old_policy.source_system, 'shopview')
 AND COALESCE(new_policy.external_scope_id, '') = COALESCE(old_policy.external_scope_id, '')
JOIN data_policy_items item ON item.policy_id = old_policy.id
WHERE old_policy.resource_code = 'contract'
  AND old_policy.action_code = 'view'
  AND NOT EXISTS (
      SELECT 1
      FROM data_policy_items existing_item
      WHERE existing_item.policy_id = new_policy.id
        AND existing_item.dimension_type = item.dimension_type
        AND existing_item.dimension_value = item.dimension_value
  );
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute("DELETE FROM data_policies WHERE resource_code = 'business_scope' AND action_code = 'view'")
    op.execute("DELETE FROM permissions WHERE permission_code IN ('sales.view', 'settlement.view')")
    op.execute("DROP INDEX IF EXISTS ix_data_policies_source")
    op.execute("ALTER TABLE data_policies DROP COLUMN IF EXISTS synced_at")
    op.execute("ALTER TABLE data_policies DROP COLUMN IF EXISTS external_scope_name")
    op.execute("ALTER TABLE data_policies DROP COLUMN IF EXISTS external_scope_id")
    op.execute("ALTER TABLE data_policies DROP COLUMN IF EXISTS source_system")
    op.execute("ALTER TABLE data_policies DROP COLUMN IF EXISTS source_type")
