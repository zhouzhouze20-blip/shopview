"""initial shopview tables (floors, base_maps, unit_map_versions, business_units, geo_elements, spatial_evolution_log, site_snapshots)

从零建表：仅创建新 schema 的 7 张表，不依赖旧表。
用于重新搭建数据库时执行。down_revision = None 表示可作为首条迁移。

Revision ID: initial_shopview
Revises: None
Create Date: 2026-02-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "initial_shopview"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    managed_tables = {
        "floors",
        "base_maps",
        "unit_map_versions",
        "business_units",
        "geo_elements",
        "spatial_evolution_log",
        "site_snapshots",
    }
    existing_tables = {name for name in managed_tables if inspector.has_table(name)}

    # 该初始迁移曾用于“从零建库”，但线上重复执行时不能破坏已有业务数据。
    # 一旦检测到任一目标表已存在，就直接跳过本迁移，其余结构应交给后续增量迁移处理。
    if existing_tables:
        return

    # 0) 楼层表
    op.create_table(
        "floors",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("building_code", sa.Text(), nullable=False, server_default="DEFAULT"),
        sa.Column("floor_code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("sort_no", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("building_code", "floor_code", name="uq_floors_building_floor"),
    )
    op.execute("COMMENT ON TABLE floors IS '楼层字典表：统一管理楼层编码、名称与排序'")
    op.execute("COMMENT ON COLUMN floors.id IS '楼层ID，系统主键'")
    op.execute("COMMENT ON COLUMN floors.building_code IS '建筑/项目编码（如百货名称，预留多项目）'")
    op.execute("COMMENT ON COLUMN floors.floor_code IS '楼层编码，如 B1 / 1F / 2F'")
    op.execute("COMMENT ON COLUMN floors.name IS '楼层显示名称'")
    op.execute("COMMENT ON COLUMN floors.sort_no IS '楼层排序号，用于前端展示排序'")
    op.execute("COMMENT ON COLUMN floors.created_at IS '创建时间'")

    # 1) 静态底图
    op.create_table(
        "base_maps",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("floor_id", sa.BigInteger(), nullable=False),
        sa.Column("base_map_code", sa.Text(), nullable=False),
        sa.Column("file_url", sa.Text(), nullable=False),
        sa.Column("svg_viewbox", sa.Text(), nullable=True),
        sa.Column("svg_width", sa.Numeric(12, 3), nullable=True),
        sa.Column("svg_height", sa.Numeric(12, 3), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["floor_id"], ["floors.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("base_map_code", name="base_maps_base_map_code_key"),
    )
    op.execute("COMMENT ON TABLE base_maps IS '静态底图表：存储不常变动的建筑底图（柱子、楼梯、消防等）'")
    op.execute("COMMENT ON COLUMN base_maps.id IS '底图ID，系统主键'")
    op.execute("COMMENT ON COLUMN base_maps.floor_id IS '所属楼层ID'")
    op.execute("COMMENT ON COLUMN base_maps.base_map_code IS '底图业务编码，如 BASE_1F_2026_V1'")
    op.execute("COMMENT ON COLUMN base_maps.file_url IS 'SVG 底图文件存储路径'")
    op.execute("COMMENT ON COLUMN base_maps.svg_viewbox IS 'SVG viewBox 参数，用于前端缩放定位'")
    op.execute("COMMENT ON COLUMN base_maps.svg_width IS 'SVG 原始宽度'")
    op.execute("COMMENT ON COLUMN base_maps.svg_height IS 'SVG 原始高度'")
    op.execute("COMMENT ON COLUMN base_maps.is_active IS '是否为当前楼层正在使用的底图'")
    op.execute("COMMENT ON COLUMN base_maps.created_at IS '底图上传时间'")
    op.execute("CREATE UNIQUE INDEX ux_base_maps_active_per_floor ON base_maps (floor_id) WHERE is_active = true")

    # 2) 柜位图版本
    op.create_table(
        "unit_map_versions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("floor_id", sa.BigInteger(), nullable=False),
        sa.Column("base_map_id", sa.BigInteger(), nullable=False),
        sa.Column("version_code", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("change_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["floor_id"], ["floors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["base_map_id"], ["base_maps.id"]),
        sa.UniqueConstraint("version_code", name="unit_map_versions_version_code_key"),
    )
    op.execute("COMMENT ON TABLE unit_map_versions IS '柜位图版本表：管理柜位拆分、合并等变更版本'")
    op.execute("COMMENT ON COLUMN unit_map_versions.id IS '柜位图版本ID，系统主键'")
    op.execute("COMMENT ON COLUMN unit_map_versions.floor_id IS '所属楼层ID'")
    op.execute("COMMENT ON COLUMN unit_map_versions.base_map_id IS '引用的底图ID（基于哪张底图绘制）'")
    op.execute("COMMENT ON COLUMN unit_map_versions.version_code IS '柜位图版本编码，如 UNIT_1F_20260125'")
    op.execute("COMMENT ON COLUMN unit_map_versions.is_active IS '是否为当前生效的柜位版本'")
    op.execute("COMMENT ON COLUMN unit_map_versions.change_note IS '版本变更说明（如 A01 拆分为两柜）'")
    op.execute("COMMENT ON COLUMN unit_map_versions.created_at IS '版本创建时间'")
    op.execute("CREATE UNIQUE INDEX ux_unit_versions_active_per_floor ON unit_map_versions (floor_id) WHERE is_active = true")

    # 3) 经营单元
    op.create_table(
        "business_units",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("floor_id", sa.BigInteger(), nullable=False),
        sa.Column("unit_code", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="ACTIVE"),
        sa.Column("manual_area", sa.Numeric(12, 2), nullable=True),
        sa.Column("parent_unit_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["floor_id"], ["floors.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["parent_unit_id"], ["business_units.id"]),
        sa.UniqueConstraint("floor_id", "unit_code", name="uq_business_units_floor_unit"),
        sa.CheckConstraint("status IN ('ACTIVE','VACANT','FITOUT','INACTIVE')", name="ck_unit_status"),
    )
    op.execute("COMMENT ON TABLE business_units IS '经营单元主表：柜位业务身份证，不随图纸变化'")
    op.execute("COMMENT ON COLUMN business_units.id IS '经营单元ID，系统主键'")
    op.execute("COMMENT ON COLUMN business_units.floor_id IS '所属楼层ID'")
    op.execute("COMMENT ON COLUMN business_units.unit_code IS '柜位业务编号，如 A118 / B101'")
    op.execute("COMMENT ON COLUMN business_units.status IS '经营状态：ACTIVE经营中 / VACANT空置 / FITOUT装修中 / INACTIVE失效'")
    op.execute("COMMENT ON COLUMN business_units.manual_area IS '人工确认的计租面积（合同面积）'")
    op.execute("COMMENT ON COLUMN business_units.parent_unit_id IS '父柜位ID（用于拆分/合并溯源）'")
    op.execute("COMMENT ON COLUMN business_units.created_at IS '创建时间'")
    op.execute("COMMENT ON COLUMN business_units.updated_at IS '更新时间'")

    # 4) 几何明细
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
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["version_id"], ["unit_map_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["unit_id"], ["business_units.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("version_id", "unit_id", name="uq_geo_elements_version_unit"),
    )
    op.create_index("ix_geo_elements_version", "geo_elements", ["version_id"], unique=False)
    op.create_index("ix_geo_elements_unit", "geo_elements", ["unit_id"], unique=False)
    op.execute("COMMENT ON TABLE geo_elements IS '空间几何明细表：存储每个柜位在某版本下的 SVG 矢量信息'")
    op.execute("COMMENT ON COLUMN geo_elements.id IS '几何元素ID，系统主键'")
    op.execute("COMMENT ON COLUMN geo_elements.version_id IS '所属柜位图版本ID'")
    op.execute("COMMENT ON COLUMN geo_elements.unit_id IS '对应的经营单元ID'")
    op.execute("COMMENT ON COLUMN geo_elements.svg_element_id IS 'SVG 中的元素ID（如 booth-A118）'")
    op.execute("COMMENT ON COLUMN geo_elements.path_data IS 'SVG path 的 d 属性原始数据'")
    op.execute("COMMENT ON COLUMN geo_elements.centroid_x IS '柜位中心点 X 坐标（SVG 坐标系）'")
    op.execute("COMMENT ON COLUMN geo_elements.centroid_y IS '柜位中心点 Y 坐标（SVG 坐标系）'")
    op.execute("COMMENT ON COLUMN geo_elements.bbox_minx IS '包围盒最小 X 值'")
    op.execute("COMMENT ON COLUMN geo_elements.bbox_miny IS '包围盒最小 Y 值'")
    op.execute("COMMENT ON COLUMN geo_elements.bbox_maxx IS '包围盒最大 X 值'")
    op.execute("COMMENT ON COLUMN geo_elements.bbox_maxy IS '包围盒最大 Y 值'")
    op.execute("COMMENT ON COLUMN geo_elements.area_svg IS '系统根据 SVG 路径计算的面积（非合同面积）'")
    op.execute("COMMENT ON COLUMN geo_elements.created_at IS '几何记录创建时间'")

    # 5) 空间演进日志
    op.create_table(
        "spatial_evolution_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("from_version_id", sa.BigInteger(), nullable=False),
        sa.Column("to_version_id", sa.BigInteger(), nullable=False),
        sa.Column("change_type", sa.Text(), nullable=False),
        sa.Column("source_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("target_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("match_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("confirmed_by", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["from_version_id"], ["unit_map_versions.id"]),
        sa.ForeignKeyConstraint(["to_version_id"], ["unit_map_versions.id"]),
        sa.CheckConstraint("change_type IN ('SPLIT','MERGE','REFORM')", name="ck_change_type"),
    )
    op.create_index("ix_evolution_from_to", "spatial_evolution_log", ["from_version_id", "to_version_id"], unique=False)
    op.execute("COMMENT ON TABLE spatial_evolution_log IS '空间演进日志表：记录柜位拆分、合并、重构的历史过程'")
    op.execute("COMMENT ON COLUMN spatial_evolution_log.id IS '演进日志ID，系统主键'")
    op.execute("COMMENT ON COLUMN spatial_evolution_log.from_version_id IS '变更前的柜位图版本ID'")
    op.execute("COMMENT ON COLUMN spatial_evolution_log.to_version_id IS '变更后的柜位图版本ID'")
    op.execute("COMMENT ON COLUMN spatial_evolution_log.change_type IS '变更类型：SPLIT拆分 / MERGE合并 / REFORM重构'")
    op.execute("COMMENT ON COLUMN spatial_evolution_log.source_data IS '变更前涉及的柜位编号数组'")
    op.execute("COMMENT ON COLUMN spatial_evolution_log.target_data IS '变更后生成的柜位编号数组'")
    op.execute("COMMENT ON COLUMN spatial_evolution_log.match_score IS '系统自动匹配置信度（0-1）'")
    op.execute("COMMENT ON COLUMN spatial_evolution_log.confirmed_by IS '人工确认人（项目经理/文员）'")
    op.execute("COMMENT ON COLUMN spatial_evolution_log.created_at IS '变更记录创建时间'")

    # 6) 全场快照
    op.create_table(
        "site_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("snapshot_code", sa.Text(), nullable=False),
        sa.Column("config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_code", name="site_snapshots_snapshot_code_key"),
    )
    op.execute("COMMENT ON TABLE site_snapshots IS '全场快照表：记录某一时间点全商场楼层与图纸组合状态'")
    op.execute("COMMENT ON COLUMN site_snapshots.id IS '快照ID，系统主键'")
    op.execute("COMMENT ON COLUMN site_snapshots.snapshot_code IS '快照业务编码，如 SNAP_2026_Q1'")
    op.execute("COMMENT ON COLUMN site_snapshots.config_json IS '楼层与图纸版本组合配置 JSON'")
    op.execute("COMMENT ON COLUMN site_snapshots.created_at IS '快照生成时间'")


def downgrade() -> None:
    op.drop_table("site_snapshots")
    op.drop_table("spatial_evolution_log")
    op.drop_table("geo_elements")
    op.drop_table("business_units")
    op.drop_table("unit_map_versions")
    op.drop_table("base_maps")
    op.drop_table("floors")
