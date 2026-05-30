"""Add store_id to floors table

Revision ID: add_store_id_to_floors
Revises: initial_shopview
Create Date: 2026-02-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_store_id_to_floors"
down_revision = "initial_shopview"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "floors",
        sa.Column("store_id", sa.String(20), nullable=True, comment="门店ID"),
    )


def downgrade():
    op.drop_column("floors", "store_id")
