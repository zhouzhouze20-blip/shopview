"""remove legacy ERP business scope policies

Revision ID: 0b1c2d3e4f5a
Revises: f9a0b1c2d3e4
Create Date: 2026-06-04

"""
from typing import Sequence, Union

from alembic import op


revision: str = "0b1c2d3e4f5a"
down_revision: Union[str, Sequence[str], None] = "f9a0b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_SQL = r"""
WITH legacy_policies AS (
    SELECT id
    FROM data_policies
    WHERE action_code = 'view'
      AND resource_code IN ('business_scope', 'contract')
      AND NOT (
        source_type = 'WECOM'
        AND source_system = 'wecom'
      )
)
DELETE FROM data_policy_items
WHERE policy_id IN (SELECT id FROM legacy_policies);

DELETE FROM data_policies
WHERE action_code = 'view'
  AND resource_code IN ('business_scope', 'contract')
  AND NOT (
    source_type = 'WECOM'
    AND source_system = 'wecom'
  );
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    pass
