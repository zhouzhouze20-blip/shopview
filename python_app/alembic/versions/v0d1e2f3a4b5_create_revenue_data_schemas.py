"""create revenue data-layer schemas

Revision ID: v0d1e2f3a4b5
Revises: u9c0d1e2f3a4
Create Date: 2026-08-03
"""
from typing import Sequence, Union

from alembic import op


revision: str = "v0d1e2f3a4b5"
down_revision: Union[str, Sequence[str], None] = "u9c0d1e2f3a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ods")
    op.execute("CREATE SCHEMA IF NOT EXISTS dw")
    op.execute("CREATE SCHEMA IF NOT EXISTS mart")

    op.execute("COMMENT ON SCHEMA ods IS 'ERP and NC source data landing layer'")
    op.execute("COMMENT ON SCHEMA dw IS 'Standardized revenue detail and mapping layer'")
    op.execute("COMMENT ON SCHEMA mart IS 'Revenue aggregate and period snapshot layer'")


def downgrade() -> None:
    # Only empty schemas can be removed. Once business tables are created,
    # downgrading must stop instead of deleting data through CASCADE.
    op.execute("DROP SCHEMA IF EXISTS mart RESTRICT")
    op.execute("DROP SCHEMA IF EXISTS dw RESTRICT")
    op.execute("DROP SCHEMA IF EXISTS ods RESTRICT")
