"""Add department dimensions to the headquarters rental ODS.

Revision ID: b1d2e3f4a5b6
Revises: a0c1d2e3f4a5
"""

from typing import Sequence, Union

from alembic import op


revision: str = "b1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "a0c1d2e3f4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE ods.hq_supsettlehead ADD COLUMN department_code VARCHAR(20)")
    op.execute("ALTER TABLE ods.hq_supsettlehead ADD COLUMN department_name TEXT")
    op.execute(
        "CREATE INDEX ix_hq_supsettlehead_department "
        "ON ods.hq_supsettlehead (department_code)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ods.ix_hq_supsettlehead_department")
    op.execute("ALTER TABLE ods.hq_supsettlehead DROP COLUMN IF EXISTS department_name")
    op.execute("ALTER TABLE ods.hq_supsettlehead DROP COLUMN IF EXISTS department_code")
