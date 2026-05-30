"""create wecom role scope rules

Revision ID: b6d4e8f0a2c1
Revises: a1b2c3d4e5f6
Create Date: 2026-05-30

"""
from typing import Sequence, Union

from alembic import op


revision: str = "b6d4e8f0a2c1"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_SQL = r"""
CREATE TABLE IF NOT EXISTS wecom_role_scope_rules (
    id BIGSERIAL PRIMARY KEY,
    rule_name VARCHAR(100) NOT NULL,
    corp_id VARCHAR(100),
    priority INTEGER NOT NULL DEFAULT 100,
    match_mode VARCHAR(10) NOT NULL DEFAULT 'ALL',
    wecom_userids JSONB NOT NULL DEFAULT '[]'::jsonb,
    name_keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
    department_keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
    position_keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
    role_codes JSONB NOT NULL DEFAULT '[]'::jsonb,
    scope_mode VARCHAR(20) NOT NULL DEFAULT 'CUSTOM',
    scope_dimensions JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    remark TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_wecom_role_scope_rules_match_mode CHECK (match_mode IN ('ALL', 'ANY')),
    CONSTRAINT ck_wecom_role_scope_rules_scope_mode CHECK (scope_mode IN ('ALL', 'CUSTOM', 'NONE'))
);

CREATE INDEX IF NOT EXISTS ix_wecom_role_scope_rules_active_priority
    ON wecom_role_scope_rules(is_active, priority, id);
CREATE INDEX IF NOT EXISTS ix_wecom_role_scope_rules_corp_id
    ON wecom_role_scope_rules(corp_id);

INSERT INTO wecom_role_scope_rules (
    rule_name,
    priority,
    match_mode,
    position_keywords,
    role_codes,
    scope_mode,
    scope_dimensions,
    remark
)
SELECT
    '默认-门店负责人',
    100,
    'ALL',
    '["店长", "总经理", "门店管理员"]'::jsonb,
    '["store_admin"]'::jsonb,
    'CUSTOM',
    '{"store": ["$store_id"]}'::jsonb,
    '系统预置，可在前台调整或停用'
WHERE NOT EXISTS (SELECT 1 FROM wecom_role_scope_rules WHERE rule_name = '默认-门店负责人');

INSERT INTO wecom_role_scope_rules (
    rule_name,
    priority,
    match_mode,
    position_keywords,
    role_codes,
    scope_mode,
    scope_dimensions,
    remark
)
SELECT
    '默认-部门主管',
    200,
    'ALL',
    '["部门主管", "部门经理", "主管", "经理"]'::jsonb,
    '["dept_manager"]'::jsonb,
    'CUSTOM',
    '{"department": ["$department"]}'::jsonb,
    '系统预置，可在前台调整或停用'
WHERE NOT EXISTS (SELECT 1 FROM wecom_role_scope_rules WHERE rule_name = '默认-部门主管');

INSERT INTO wecom_role_scope_rules (
    rule_name,
    priority,
    match_mode,
    position_keywords,
    role_codes,
    scope_mode,
    scope_dimensions,
    remark
)
SELECT
    '默认-柜组负责人',
    300,
    'ALL',
    '["柜组负责人", "柜组主管", "柜组长", "柜长", "组长"]'::jsonb,
    '["group_manager"]'::jsonb,
    'CUSTOM',
    '{"department": ["$department"]}'::jsonb,
    '系统预置，可在前台调整或停用'
WHERE NOT EXISTS (SELECT 1 FROM wecom_role_scope_rules WHERE rule_name = '默认-柜组负责人');

INSERT INTO wecom_role_scope_rules (
    rule_name,
    priority,
    match_mode,
    department_keywords,
    position_keywords,
    role_codes,
    scope_mode,
    scope_dimensions,
    remark
)
SELECT
    '默认-财务',
    400,
    'ANY',
    '["财务"]'::jsonb,
    '["财务"]'::jsonb,
    '["finance"]'::jsonb,
    'CUSTOM',
    '{"store": ["$store_id"]}'::jsonb,
    '系统预置，可在前台调整或停用'
WHERE NOT EXISTS (SELECT 1 FROM wecom_role_scope_rules WHERE rule_name = '默认-财务');
"""


DOWNGRADE_SQL = r"""
DROP TABLE IF EXISTS wecom_role_scope_rules;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
