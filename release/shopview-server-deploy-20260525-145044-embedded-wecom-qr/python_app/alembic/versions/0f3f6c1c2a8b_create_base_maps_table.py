"""create base_maps table

为楼层字典表 floors 增加静态底图表 base_maps，并添加“同一楼层仅一个 active 底图”的条件唯一索引。

Revision ID: 0f3f6c1c2a8b
Revises: add_store_code_floors
Create Date: 2026-03-11

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0f3f6c1c2a8b"
down_revision: Union[str, Sequence[str], None] = "add_store_code_floors"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("base_maps"):
        op.create_table(
            "base_maps",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("floor_id", sa.BigInteger(), nullable=False),
            sa.Column("base_map_code", sa.Text(), nullable=False),
            sa.Column("file_url", sa.Text(), nullable=False),
            sa.Column("svg_viewbox", sa.Text(), nullable=True),
            sa.Column("svg_width", sa.Numeric(12, 3), nullable=True),
            sa.Column("svg_height", sa.Numeric(12, 3), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["floor_id"], ["floors.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("base_map_code", name="base_maps_base_map_code_key"),
        )

    # 同一楼层仅一个 active 底图（PostgreSQL partial unique index）
    existing_indexes = {idx.get("name") for idx in inspector.get_indexes("base_maps")}
    if "ux_base_maps_active_per_floor" not in existing_indexes:
        op.create_index(
            "ux_base_maps_active_per_floor",
            "base_maps",
            ["floor_id"],
            unique=True,
            postgresql_where=sa.text("is_active = true"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("base_maps"):
        op.drop_index("ux_base_maps_active_per_floor", table_name="base_maps")
        op.drop_table("base_maps")

