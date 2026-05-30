"""create system management acl tables

Revision ID: f2c1a6b7d9e0
Revises: e1b2c3d4f5a6
Create Date: 2026-04-23 18:30:00

"""
from typing import Sequence, Union

from alembic import op


revision: str = "f2c1a6b7d9e0"
down_revision: Union[str, Sequence[str], None] = "e1b2c3d4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_SQL = r"""
ALTER TABLE users ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'ACTIVE';
ALTER TABLE users ADD COLUMN IF NOT EXISTS default_store_id INTEGER;
ALTER TABLE users ADD COLUMN IF NOT EXISTS employee_no VARCHAR(50);

UPDATE users
SET status = CASE WHEN COALESCE(is_active, TRUE) THEN 'ACTIVE' ELSE 'DISABLED' END
WHERE status IS NULL;

CREATE TABLE IF NOT EXISTS user_identities (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    identity_type VARCHAR(20) NOT NULL,
    identifier VARCHAR(200) NOT NULL,
    credential_hash VARCHAR(255),
    corp_id VARCHAR(100),
    wecom_user_id VARCHAR(100),
    union_id VARCHAR(100),
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (identity_type, identifier)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_user_identities_wecom_user
    ON user_identities(corp_id, wecom_user_id)
    WHERE corp_id IS NOT NULL AND wecom_user_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS departments (
    id BIGSERIAL PRIMARY KEY,
    store_id INTEGER NOT NULL REFERENCES stores(store_id) ON DELETE RESTRICT,
    dept_code VARCHAR(50) NOT NULL,
    dept_name VARCHAR(100) NOT NULL,
    parent_id BIGINT REFERENCES departments(id) ON DELETE RESTRICT,
    manager_user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (store_id, dept_code)
);

CREATE TABLE IF NOT EXISTS posts (
    id BIGSERIAL PRIMARY KEY,
    post_code VARCHAR(50) NOT NULL UNIQUE,
    post_name VARCHAR(100) NOT NULL,
    level INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_department_posts (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    store_id INTEGER NOT NULL REFERENCES stores(store_id) ON DELETE RESTRICT,
    department_id BIGINT NOT NULL REFERENCES departments(id) ON DELETE RESTRICT,
    post_id BIGINT REFERENCES posts(id) ON DELETE RESTRICT,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_user_department_posts_user_id ON user_department_posts(user_id);
CREATE INDEX IF NOT EXISTS ix_user_department_posts_department_id ON user_department_posts(department_id);

CREATE TABLE IF NOT EXISTS roles (
    id BIGSERIAL PRIMARY KEY,
    role_code VARCHAR(50) NOT NULL UNIQUE,
    role_name VARCHAR(100) NOT NULL,
    role_level INTEGER NOT NULL DEFAULT 0,
    is_system BOOLEAN NOT NULL DEFAULT TRUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS permissions (
    id BIGSERIAL PRIMARY KEY,
    permission_code VARCHAR(100) NOT NULL UNIQUE,
    permission_name VARCHAR(100) NOT NULL,
    module_code VARCHAR(50) NOT NULL,
    action_code VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS role_permissions (
    id BIGSERIAL PRIMARY KEY,
    role_id BIGINT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id BIGINT NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS user_roles (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role_id BIGINT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    store_id INTEGER REFERENCES stores(store_id) ON DELETE RESTRICT,
    expires_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_user_roles_scope
    ON user_roles(user_id, role_id, COALESCE(store_id, 0));
CREATE INDEX IF NOT EXISTS ix_user_roles_user_id ON user_roles(user_id);

CREATE TABLE IF NOT EXISTS data_policies (
    id BIGSERIAL PRIMARY KEY,
    subject_type VARCHAR(20) NOT NULL,
    subject_id BIGINT NOT NULL,
    resource_code VARCHAR(50) NOT NULL,
    action_code VARCHAR(50) NOT NULL,
    scope_mode VARCHAR(20) NOT NULL DEFAULT 'CUSTOM',
    effect VARCHAR(20) NOT NULL DEFAULT 'ALLOW',
    priority INTEGER NOT NULL DEFAULT 100,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_data_policies_subject ON data_policies(subject_type, subject_id);
CREATE INDEX IF NOT EXISTS ix_data_policies_resource ON data_policies(resource_code, action_code);

CREATE TABLE IF NOT EXISTS data_policy_items (
    id BIGSERIAL PRIMARY KEY,
    policy_id BIGINT NOT NULL REFERENCES data_policies(id) ON DELETE CASCADE,
    dimension_type VARCHAR(20) NOT NULL,
    dimension_value VARCHAR(100) NOT NULL,
    include_children BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_data_policy_items_policy_id ON data_policy_items(policy_id);
CREATE INDEX IF NOT EXISTS ix_data_policy_items_dimension ON data_policy_items(dimension_type, dimension_value);

CREATE TABLE IF NOT EXISTS login_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    identity_type VARCHAR(20),
    identifier VARCHAR(200),
    login_result VARCHAR(20) NOT NULL,
    ip_address VARCHAR(64),
    user_agent TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS operation_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    action_code VARCHAR(100) NOT NULL,
    resource_code VARCHAR(50) NOT NULL,
    target_id VARCHAR(100),
    detail JSONB,
    ip_address VARCHAR(64),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

ALTER TABLE counter_groups ADD COLUMN IF NOT EXISTS department_id BIGINT;
CREATE UNIQUE INDEX IF NOT EXISTS ux_counter_groups_store_group_code ON counter_groups(store_id, group_code);

ALTER TABLE business_units ADD COLUMN IF NOT EXISTS store_id INTEGER;
ALTER TABLE business_units ADD COLUMN IF NOT EXISTS department_id BIGINT;
ALTER TABLE business_units ADD COLUMN IF NOT EXISTS group_code VARCHAR(20);

CREATE INDEX IF NOT EXISTS ix_business_units_store_id ON business_units(store_id);
CREATE INDEX IF NOT EXISTS ix_business_units_department_id ON business_units(department_id);
CREATE INDEX IF NOT EXISTS ix_business_units_group_code ON business_units(group_code);

INSERT INTO posts (post_code, post_name, level, is_active)
VALUES
    ('store_manager', '门店管理员', 800, TRUE),
    ('dept_manager', '部门主管', 700, TRUE),
    ('staff', '普通员工', 100, TRUE)
ON CONFLICT (post_code) DO NOTHING;

INSERT INTO roles (role_code, role_name, role_level, is_system, is_active)
VALUES
    ('super_admin', '超级管理员', 1000, TRUE, TRUE),
    ('system_admin', '系统管理员', 900, TRUE, TRUE),
    ('store_admin', '门店管理员', 800, TRUE, TRUE),
    ('dept_manager', '部门主管', 700, TRUE, TRUE),
    ('group_manager', '柜组负责人', 600, TRUE, TRUE),
    ('finance', '财务人员', 500, TRUE, TRUE),
    ('viewer', '只读用户', 100, TRUE, TRUE)
ON CONFLICT (role_code) DO NOTHING;

INSERT INTO permissions (permission_code, permission_name, module_code, action_code)
VALUES
    ('dashboard.view', '查看驾驶舱', 'dashboard', 'view'),
    ('store.view', '查看门店', 'store', 'view'),
    ('floor.view', '查看楼层', 'floor', 'view'),
    ('counter.view', '查看柜位', 'counter', 'view'),
    ('counter.create', '新增柜位', 'counter', 'create'),
    ('counter.edit', '编辑柜位', 'counter', 'edit'),
    ('counter.delete', '删除柜位', 'counter', 'delete'),
    ('hall.view', '查看厅房', 'hall', 'view'),
    ('hall.edit', '编辑厅房', 'hall', 'edit'),
    ('hall.bind_group', '绑定厅房柜组', 'hall', 'bind_group'),
    ('business_unit.view', '查看经营单元', 'business_unit', 'view'),
    ('business_unit.create', '新增经营单元', 'business_unit', 'create'),
    ('business_unit.edit', '编辑经营单元', 'business_unit', 'edit'),
    ('business_unit.delete', '删除经营单元', 'business_unit', 'delete'),
    ('tenant.view', '查看商户', 'tenant', 'view'),
    ('tenant.create', '新增商户', 'tenant', 'create'),
    ('tenant.edit', '编辑商户', 'tenant', 'edit'),
    ('tenant.delete', '删除商户', 'tenant', 'delete'),
    ('contract.view', '查看合同', 'contract', 'view'),
    ('contract.create', '新增合同', 'contract', 'create'),
    ('contract.edit', '编辑合同', 'contract', 'edit'),
    ('contract.delete', '删除合同', 'contract', 'delete'),
    ('contract.approve', '审批合同', 'contract', 'approve'),
    ('bill.view', '查看账单', 'bill', 'view'),
    ('bill.create', '新增账单', 'bill', 'create'),
    ('bill.edit', '编辑账单', 'bill', 'edit'),
    ('bill.approve', '审批账单', 'bill', 'approve'),
    ('revenue.view', '查看收益', 'revenue', 'view'),
    ('revenue.export', '导出收益', 'revenue', 'export'),
    ('system.user.manage', '管理用户', 'system', 'user_manage'),
    ('system.role.manage', '管理角色', 'system', 'role_manage'),
    ('system.permission.manage', '管理权限', 'system', 'permission_manage'),
    ('system.data_policy.manage', '管理数据权限', 'system', 'data_policy_manage'),
    ('system.audit_log.view', '查看审计日志', 'system', 'audit_log_view')
ON CONFLICT (permission_code) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.role_code = 'super_admin'
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.permission_code IN (
    'dashboard.view',
    'store.view',
    'floor.view',
    'system.user.manage',
    'system.role.manage',
    'system.permission.manage',
    'system.data_policy.manage',
    'system.audit_log.view'
)
WHERE r.role_code = 'system_admin'
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.permission_code IN (
    'dashboard.view',
    'store.view',
    'floor.view',
    'counter.view',
    'counter.create',
    'counter.edit',
    'hall.view',
    'hall.edit',
    'hall.bind_group',
    'business_unit.view',
    'business_unit.create',
    'business_unit.edit',
    'tenant.view',
    'tenant.create',
    'tenant.edit',
    'contract.view',
    'contract.create',
    'contract.edit',
    'bill.view',
    'bill.create',
    'bill.edit',
    'revenue.view',
    'revenue.export'
)
WHERE r.role_code = 'store_admin'
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.permission_code IN (
    'dashboard.view',
    'store.view',
    'floor.view',
    'counter.view',
    'counter.edit',
    'hall.view',
    'hall.edit',
    'business_unit.view',
    'business_unit.edit',
    'tenant.view',
    'tenant.edit',
    'contract.view',
    'contract.edit',
    'bill.view',
    'revenue.view'
)
WHERE r.role_code = 'dept_manager'
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.permission_code IN (
    'dashboard.view',
    'counter.view',
    'hall.view',
    'business_unit.view',
    'tenant.view',
    'contract.view',
    'bill.view',
    'revenue.view'
)
WHERE r.role_code = 'group_manager'
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.permission_code IN (
    'dashboard.view',
    'tenant.view',
    'contract.view',
    'bill.view',
    'bill.create',
    'bill.edit',
    'bill.approve',
    'revenue.view',
    'revenue.export'
)
WHERE r.role_code = 'finance'
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.permission_code IN (
    'dashboard.view',
    'store.view',
    'floor.view',
    'counter.view',
    'hall.view',
    'business_unit.view',
    'tenant.view',
    'contract.view',
    'bill.view',
    'revenue.view'
)
WHERE r.role_code = 'viewer'
ON CONFLICT DO NOTHING;

INSERT INTO user_identities (user_id, identity_type, identifier, credential_hash, is_primary, created_at, updated_at)
SELECT
    u.user_id,
    'password',
    u.username,
    u.password_hash,
    TRUE,
    COALESCE(u.created_at, NOW()),
    NOW()
FROM users u
WHERE NOT EXISTS (
    SELECT 1
    FROM user_identities ui
    WHERE ui.user_id = u.user_id
      AND ui.identity_type = 'password'
);

INSERT INTO user_roles (user_id, role_id, store_id, created_at)
SELECT
    u.user_id,
    r.id,
    NULL,
    NOW()
FROM users u
JOIN roles r ON r.role_code = CASE
    WHEN u.role = 'admin' THEN 'super_admin'
    WHEN u.role = 'viewer' THEN 'viewer'
    ELSE 'viewer'
END
WHERE NOT EXISTS (
    SELECT 1
    FROM user_roles ur
    WHERE ur.user_id = u.user_id
      AND ur.role_id = r.id
      AND ur.store_id IS NULL
);

INSERT INTO data_policies (
    subject_type, subject_id, resource_code, action_code, scope_mode, effect, priority, is_active, created_at, updated_at
)
SELECT 'ROLE', r.id, src.resource_code, src.action_code, 'ALL', 'ALLOW', 1, TRUE, NOW(), NOW()
FROM roles r
CROSS JOIN (
    VALUES
        ('counter', 'view'),
        ('counter', 'edit'),
        ('hall', 'view'),
        ('hall', 'edit'),
        ('tenant', 'view'),
        ('tenant', 'edit'),
        ('contract', 'view'),
        ('contract', 'edit'),
        ('contract', 'approve'),
        ('bill', 'view'),
        ('bill', 'edit'),
        ('bill', 'approve'),
        ('revenue', 'view'),
        ('revenue', 'export')
) AS src(resource_code, action_code)
WHERE r.role_code = 'super_admin'
  AND NOT EXISTS (
      SELECT 1
      FROM data_policies dp
      WHERE dp.subject_type = 'ROLE'
        AND dp.subject_id = r.id
        AND dp.resource_code = src.resource_code
        AND dp.action_code = src.action_code
  );
"""


DOWNGRADE_SQL = r"""
DROP TABLE IF EXISTS operation_logs;
DROP TABLE IF EXISTS login_logs;
DROP TABLE IF EXISTS data_policy_items;
DROP TABLE IF EXISTS data_policies;
DROP INDEX IF EXISTS ux_user_roles_scope;
DROP TABLE IF EXISTS user_roles;
DROP TABLE IF EXISTS role_permissions;
DROP TABLE IF EXISTS permissions;
DROP TABLE IF EXISTS roles;
DROP TABLE IF EXISTS user_department_posts;
DROP TABLE IF EXISTS posts;
DROP TABLE IF EXISTS departments;
DROP INDEX IF EXISTS ux_user_identities_wecom_user;
DROP TABLE IF EXISTS user_identities;
"""


def upgrade() -> None:
    op.get_bind().exec_driver_sql(UPGRADE_SQL)


def downgrade() -> None:
    op.get_bind().exec_driver_sql(DOWNGRADE_SQL)
