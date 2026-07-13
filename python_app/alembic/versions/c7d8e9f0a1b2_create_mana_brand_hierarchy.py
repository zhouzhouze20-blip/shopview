"""create mana brand hierarchy

Revision ID: c7d8e9f0a1b2
Revises: b3c4d5e6f7a8
Create Date: 2026-07-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, Sequence[str], None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mana_brand_hierarchy",
        sa.Column("level1_code", sa.String(length=100), nullable=False),
        sa.Column("level1_name", sa.String(length=100), nullable=False),
        sa.Column("level2_code", sa.String(length=100), nullable=False),
        sa.Column("level2_name", sa.String(length=100), nullable=False),
        sa.Column("level3_code", sa.String(length=100), nullable=False, primary_key=True),
        sa.Column("level3_name", sa.String(length=100), nullable=False),
        sa.Column("grade_code", sa.String(length=10), nullable=True),
        sa.Column("grade_label", sa.String(length=1), nullable=True),
        sa.Column(
            "etl_loaded_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "grade_label IS NULL OR grade_label IN ('A', 'B', 'C', 'D')",
            name="ck_mana_brand_hierarchy_grade_label",
        ),
        comment="HDYY01 集团经营分析品牌层级维度，层级来源 BIBH.ODS_MANABRAND",
    )
    op.create_index(
        "ix_mana_brand_hierarchy_level1_code",
        "mana_brand_hierarchy",
        ["level1_code"],
    )
    op.create_index(
        "ix_mana_brand_hierarchy_level2_code",
        "mana_brand_hierarchy",
        ["level2_code"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_mana_brand_hierarchy_level2_code",
        table_name="mana_brand_hierarchy",
    )
    op.drop_index(
        "ix_mana_brand_hierarchy_level1_code",
        table_name="mana_brand_hierarchy",
    )
    op.drop_table("mana_brand_hierarchy")
