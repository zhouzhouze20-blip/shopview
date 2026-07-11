"""add mall planning role

Revision ID: a2b3c4d5e6f7
Revises: f0a1b2c3d4e6
Create Date: 2026-07-09
"""
from typing import Sequence, Union

from alembic import op


revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "f0a1b2c3d4e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_SQL = r"""
INSERT INTO roles (role_code, role_name, role_level, is_system, is_active, created_at, updated_at)
VALUES ('mall_planning', '购物中心企划', 790, TRUE, TRUE, NOW(), NOW())
ON CONFLICT (role_code) DO UPDATE
SET role_name = EXCLUDED.role_name,
    role_level = EXCLUDED.role_level,
    is_system = TRUE,
    is_active = TRUE,
    updated_at = NOW();

INSERT INTO permissions (permission_code, permission_name, module_code, action_code)
VALUES
    ('dashboard.view', '查看驾驶舱', 'dashboard', 'view'),
    ('sales.view', '查看销售', 'sales', 'view'),
    ('activity_analysis.view', '查看活动分析', 'activity_analysis', 'view'),
    ('activity_analysis.points.view', '查看积分活动核对', 'activity_analysis', 'points_view'),
    ('activity_analysis.star_diamond.view', '查看中心星钻会员', 'activity_analysis', 'star_diamond_view')
ON CONFLICT (permission_code) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id, created_at)
SELECT r.id, p.id, NOW()
FROM roles r
JOIN permissions p ON p.permission_code IN (
    'dashboard.view',
    'sales.view',
    'activity_analysis.view',
    'activity_analysis.points.view',
    'activity_analysis.star_diamond.view'
)
WHERE r.role_code = 'mall_planning'
ON CONFLICT DO NOTHING;

WITH target_users AS (
    SELECT user_id
    FROM users
    WHERE real_name IN ('俞陈', '白海燕')
),
target_role AS (
    SELECT id AS role_id
    FROM roles
    WHERE role_code = 'mall_planning'
)
DELETE FROM user_roles ur
USING target_users tu
WHERE ur.user_id = tu.user_id;

WITH target_users AS (
    SELECT user_id
    FROM users
    WHERE real_name IN ('俞陈', '白海燕')
),
target_role AS (
    SELECT id AS role_id
    FROM roles
    WHERE role_code = 'mall_planning'
)
INSERT INTO user_roles (user_id, role_id, created_at)
SELECT tu.user_id, tr.role_id, NOW()
FROM target_users tu
CROSS JOIN target_role tr;

WITH target_users AS (
    SELECT user_id
    FROM users
    WHERE real_name IN ('俞陈', '白海燕')
)
UPDATE data_policies dp
SET is_active = FALSE,
    updated_at = NOW()
FROM target_users tu
WHERE dp.subject_type = 'USER'
  AND dp.subject_id = tu.user_id
  AND dp.resource_code = 'business_scope'
  AND dp.action_code = 'view'
  AND COALESCE(dp.external_scope_id, '') NOT IN (
      'mall_planning:yuchen:store:1',
      'mall_planning:baihaiyan:stores:1-4'
  );

WITH target_scopes(real_name, external_scope_id, external_scope_name) AS (
    VALUES
        ('俞陈', 'mall_planning:yuchen:store:1', '俞陈 购物中心全部权限'),
        ('白海燕', 'mall_planning:baihaiyan:stores:1-4', '白海燕 四门店全部权限')
)
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
    ts.external_scope_id,
    ts.external_scope_name,
    NOW(),
    NOW(),
    NOW()
FROM target_scopes ts
JOIN users u ON u.real_name = ts.real_name
WHERE NOT EXISTS (
    SELECT 1
    FROM data_policies existing
    WHERE existing.subject_type = 'USER'
      AND existing.subject_id = u.user_id
      AND existing.resource_code = 'business_scope'
      AND existing.action_code = 'view'
      AND existing.external_scope_id = ts.external_scope_id
);

WITH target_scopes(real_name, external_scope_id, external_scope_name) AS (
    VALUES
        ('俞陈', 'mall_planning:yuchen:store:1', '俞陈 购物中心全部权限'),
        ('白海燕', 'mall_planning:baihaiyan:stores:1-4', '白海燕 四门店全部权限')
)
UPDATE data_policies dp
SET scope_mode = 'CUSTOM',
    effect = 'ALLOW',
    priority = 100,
    is_active = TRUE,
    source_type = 'MANUAL',
    source_system = 'shopview',
    external_scope_name = ts.external_scope_name,
    synced_at = NOW(),
    updated_at = NOW()
FROM target_scopes ts
JOIN users u ON u.real_name = ts.real_name
WHERE dp.subject_type = 'USER'
  AND dp.subject_id = u.user_id
  AND dp.resource_code = 'business_scope'
  AND dp.action_code = 'view'
  AND dp.external_scope_id = ts.external_scope_id;

DELETE FROM data_policy_items dpi
USING data_policies dp
WHERE dpi.policy_id = dp.id
  AND dp.subject_type = 'USER'
  AND dp.resource_code = 'business_scope'
  AND dp.action_code = 'view'
  AND dp.external_scope_id IN (
      'mall_planning:yuchen:store:1',
      'mall_planning:baihaiyan:stores:1-4',
      'mall_planning:store:1'
  )
  AND dp.subject_id IN (
      SELECT user_id FROM users WHERE real_name IN ('俞陈', '白海燕')
  );

WITH target_items(real_name, external_scope_id, external_scope_name, store_id) AS (
    VALUES
        ('俞陈', 'mall_planning:yuchen:store:1', '俞陈 购物中心全部权限', '1'),
        ('白海燕', 'mall_planning:baihaiyan:stores:1-4', '白海燕 四门店全部权限', '1'),
        ('白海燕', 'mall_planning:baihaiyan:stores:1-4', '白海燕 四门店全部权限', '2'),
        ('白海燕', 'mall_planning:baihaiyan:stores:1-4', '白海燕 四门店全部权限', '3'),
        ('白海燕', 'mall_planning:baihaiyan:stores:1-4', '白海燕 四门店全部权限', '4')
)
INSERT INTO data_policy_items (policy_id, dimension_type, dimension_value, include_children, created_at)
SELECT dp.id, 'store', ti.store_id, FALSE, NOW()
FROM data_policies dp
JOIN users u ON u.user_id = dp.subject_id
JOIN target_items ti
  ON ti.real_name = u.real_name
 AND ti.external_scope_id = dp.external_scope_id
WHERE dp.subject_type = 'USER'
  AND dp.resource_code = 'business_scope'
  AND dp.action_code = 'view'
  AND dp.external_scope_id IN (
      'mall_planning:yuchen:store:1',
      'mall_planning:baihaiyan:stores:1-4'
  );
"""


DOWNGRADE_SQL = r"""
DELETE FROM data_policy_items dpi
USING data_policies dp
WHERE dpi.policy_id = dp.id
  AND dp.external_scope_id IN (
      'mall_planning:yuchen:store:1',
      'mall_planning:baihaiyan:stores:1-4',
      'mall_planning:store:1'
  );

DELETE FROM data_policies
WHERE external_scope_id IN (
    'mall_planning:yuchen:store:1',
    'mall_planning:baihaiyan:stores:1-4',
    'mall_planning:store:1'
);

DELETE FROM user_roles
WHERE role_id = (SELECT id FROM roles WHERE role_code = 'mall_planning')
  AND user_id IN (SELECT user_id FROM users WHERE real_name IN ('俞陈', '白海燕'));

DELETE FROM role_permissions
WHERE role_id = (SELECT id FROM roles WHERE role_code = 'mall_planning');

DELETE FROM roles
WHERE role_code = 'mall_planning';
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
