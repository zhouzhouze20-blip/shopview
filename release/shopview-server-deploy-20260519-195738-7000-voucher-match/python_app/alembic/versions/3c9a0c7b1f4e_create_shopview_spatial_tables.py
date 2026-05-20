"""create shopview spatial tables

创建 ShopView 空间相关表：
- unit_map_versions
- business_units
- geo_elements
- spatial_evolution_log
- site_snapshots

说明：
- 采用“表不存在才创建”的方式，兼容已有库/重复执行。
- 依赖 floors/base_maps 已存在（base_maps 本分支已单独迁移创建）。

Revision ID: 3c9a0c7b1f4e
Revises: 0f3f6c1c2a8b
Create Date: 2026-03-11

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "3c9a0c7b1f4e"
down_revision: Union[str, Sequence[str], None] = "0f3f6c1c2a8b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1) unit_map_versions
    if not inspector.has_table("unit_map_versions"):
        op.create_table(
            "unit_map_versions",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("floor_id", sa.BigInteger(), nullable=False),
            sa.Column("base_map_id", sa.BigInteger(), nullable=False),
            sa.Column("version_code", sa.Text(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("change_note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["floor_id"], ["floors.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["base_map_id"], ["base_maps.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("version_code", name="unit_map_versions_version_code_key"),
        )

    # 同一楼层只能一个 active 柜位版本
    existing_indexes = {idx.get("name") for idx in inspector.get_indexes("unit_map_versions")}
    if "ux_unit_versions_active_per_floor" not in existing_indexes:
        op.create_index(
            "ux_unit_versions_active_per_floor",
            "unit_map_versions",
            ["floor_id"],
            unique=True,
            postgresql_where=sa.text("is_active = true"),
        )

    # 2) business_units
    if not inspector.has_table("business_units"):
        op.create_table(
            "business_units",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("floor_id", sa.BigInteger(), nullable=False),
            sa.Column("unit_code", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'ACTIVE'")),
            sa.Column("manual_area", sa.Numeric(12, 2), nullable=True),
            sa.Column("parent_unit_id", sa.BigInteger(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["floor_id"], ["floors.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["parent_unit_id"], ["business_units.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("floor_id", "unit_code", name="uq_business_units_floor_unit"),
            sa.CheckConstraint(
                "status IN ('ACTIVE','VACANT','FITOUT','INACTIVE')",
                name="ck_unit_status",
            ),
        )

    # 3) geo_elements
    if not inspector.has_table("geo_elements"):
        op.create_table(
            "geo_elements",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("version_id", sa.BigInteger(), nullable=False),
            sa.Column("unit_id", sa.BigInteger(), nullable=False),
            sa.Column("svg_element_id", sa.Text(), nullable=True),
            sa.Column("path_data", sa.Text(), nullable=False),
            sa.Column("centroid_x", sa.Numeric(14, 4), nullable=True),
            sa.Column("centroid_y", sa.Numeric(14, 4), nullable=True),
            sa.Column("bbox_minx", sa.Numeric(14, 4), nullable=True),
            sa.Column("bbox_miny", sa.Numeric(14, 4), nullable=True),
            sa.Column("bbox_maxx", sa.Numeric(14, 4), nullable=True),
            sa.Column("bbox_maxy", sa.Numeric(14, 4), nullable=True),
            sa.Column("area_svg", sa.Numeric(14, 2), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["version_id"], ["unit_map_versions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["unit_id"], ["business_units.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("version_id", "unit_id", name="uq_geo_elements_version_unit"),
        )

    # indexes for geo_elements
    geo_indexes = {idx.get("name") for idx in inspector.get_indexes("geo_elements")}
    if "ix_geo_elements_version" not in geo_indexes:
        op.create_index("ix_geo_elements_version", "geo_elements", ["version_id"], unique=False)
    if "ix_geo_elements_unit" not in geo_indexes:
        op.create_index("ix_geo_elements_unit", "geo_elements", ["unit_id"], unique=False)

    # 4) spatial_evolution_log
    if not inspector.has_table("spatial_evolution_log"):
        op.create_table(
            "spatial_evolution_log",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("from_version_id", sa.BigInteger(), nullable=False),
            sa.Column("to_version_id", sa.BigInteger(), nullable=False),
            sa.Column("change_type", sa.Text(), nullable=False),
            sa.Column("source_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("target_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("match_score", sa.Float(), nullable=True),
            sa.Column("confirmed_by", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["from_version_id"], ["unit_map_versions.id"]),
            sa.ForeignKeyConstraint(["to_version_id"], ["unit_map_versions.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.CheckConstraint(
                "change_type IN ('SPLIT','MERGE','REFORM')",
                name="ck_change_type",
            ),
        )

    evo_indexes = {idx.get("name") for idx in inspector.get_indexes("spatial_evolution_log")}
    if "ix_evolution_from_to" not in evo_indexes:
        op.create_index(
            "ix_evolution_from_to",
            "spatial_evolution_log",
            ["from_version_id", "to_version_id"],
            unique=False,
        )

    # 5) site_snapshots
    if not inspector.has_table("site_snapshots"):
        op.create_table(
            "site_snapshots",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("snapshot_code", sa.Text(), nullable=False),
            sa.Column("config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("snapshot_code", name="site_snapshots_snapshot_code_key"),
        )


def downgrade() -> None:
    # 逆序删除（仅当表存在）
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("site_snapshots"):
        op.drop_table("site_snapshots")

    if inspector.has_table("spatial_evolution_log"):
        op.drop_index("ix_evolution_from_to", table_name="spatial_evolution_log")
        op.drop_table("spatial_evolution_log")

    if inspector.has_table("geo_elements"):
        op.drop_index("ix_geo_elements_unit", table_name="geo_elements")
        op.drop_index("ix_geo_elements_version", table_name="geo_elements")
        op.drop_table("geo_elements")

    if inspector.has_table("business_units"):
        op.drop_table("business_units")

    if inspector.has_table("unit_map_versions"):
        op.drop_index("ux_unit_versions_active_per_floor", table_name="unit_map_versions")
        op.drop_table("unit_map_versions")

