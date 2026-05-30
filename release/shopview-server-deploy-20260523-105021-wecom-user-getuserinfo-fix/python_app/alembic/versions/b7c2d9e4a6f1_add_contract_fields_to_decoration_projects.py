"""add contract fields to decoration projects

Revision ID: b7c2d9e4a6f1
Revises: 9f2b7c6d4e1a
Create Date: 2026-04-26 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7c2d9e4a6f1"
down_revision: Union[str, Sequence[str], None] = "9f2b7c6d4e1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("decoration_projects", sa.Column("contract_no", sa.String(length=100), nullable=True))
    op.add_column("decoration_projects", sa.Column("contract_status", sa.String(length=30), nullable=True))
    op.add_column("decoration_projects", sa.Column("contract_start_date", sa.Date(), nullable=True))
    op.add_column("decoration_projects", sa.Column("contract_end_date", sa.Date(), nullable=True))
    op.create_index("ix_decoration_projects_contract_no", "decoration_projects", ["contract_no"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_decoration_projects_contract_no", table_name="decoration_projects")
    op.drop_column("decoration_projects", "contract_end_date")
    op.drop_column("decoration_projects", "contract_start_date")
    op.drop_column("decoration_projects", "contract_status")
    op.drop_column("decoration_projects", "contract_no")
