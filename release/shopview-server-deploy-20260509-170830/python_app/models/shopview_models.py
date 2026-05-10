"""
ShopView 新 schema：楼层字典、底图、柜位图版本、经营单元、几何明细、空间演进、快照。
从零建表用，与旧 stores/counters 等表无依赖。
"""
from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    Boolean,
    String,
    Text,
    Numeric,
    ForeignKey,
    DateTime,
    UniqueConstraint,
    CheckConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class Floor(Base):
    """楼层字典表：统一管理楼层编码、名称与排序"""
    __tablename__ = "floors"
    __table_args__ = (
        UniqueConstraint("store_code", "building_code", "floor_code", name="uq_floors_store_building_floor"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="楼层ID，系统主键")
    store_id = Column(String(20), nullable=True, comment="门店ID")
    store_code = Column(String(10), nullable=True, comment="门店编码：601/602/603/604")
    building_code = Column(Text, nullable=False, server_default="DEFAULT", comment="建筑/项目编码（如百货名称，预留多项目）")
    floor_code = Column(Text, nullable=False, comment="楼层编码，如 B1 / 1F / 2F")
    name = Column(Text, nullable=False, comment="楼层显示名称")
    sort_no = Column(Integer, nullable=False, server_default="0", comment="楼层排序号，用于前端展示排序")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")

    base_maps = relationship("BaseMap", back_populates="floor", passive_deletes=True)
    unit_map_versions = relationship("UnitMapVersion", back_populates="floor", passive_deletes=True)
    business_units = relationship("BusinessUnit", back_populates="floor")


class BaseMap(Base):
    """静态底图表：存储不常变动的建筑底图（柱子、楼梯、消防等）"""
    __tablename__ = "base_maps"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="底图ID，系统主键")
    floor_id = Column(BigInteger, ForeignKey("floors.id", ondelete="CASCADE"), nullable=False, comment="所属楼层ID")
    base_map_code = Column(Text, nullable=False, unique=True, comment="底图业务编码，如 BASE_1F_2026_V1")
    file_url = Column(Text, nullable=False, comment="SVG 底图文件存储路径")
    svg_viewbox = Column(Text, comment="SVG viewBox 参数，用于前端缩放定位")
    svg_width = Column(Numeric(12, 3), comment="SVG 原始宽度")
    svg_height = Column(Numeric(12, 3), comment="SVG 原始高度")
    is_active = Column(Boolean, nullable=False, server_default="false", comment="是否为当前楼层正在使用的底图")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="底图上传时间")

    floor = relationship("Floor", back_populates="base_maps")
    unit_map_versions = relationship("UnitMapVersion", back_populates="base_map")


class UnitMapVersion(Base):
    """柜位图版本表：管理柜位拆分、合并等变更版本"""
    __tablename__ = "unit_map_versions"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="柜位图版本ID，系统主键")
    floor_id = Column(BigInteger, ForeignKey("floors.id", ondelete="CASCADE"), nullable=False, comment="所属楼层ID")
    base_map_id = Column(BigInteger, ForeignKey("base_maps.id"), nullable=False, comment="引用的底图ID（基于哪张底图绘制）")
    version_code = Column(Text, nullable=False, unique=True, comment="柜位图版本编码，如 UNIT_1F_20260125")
    is_active = Column(Boolean, nullable=False, server_default="false", comment="是否为当前生效的柜位版本")
    change_note = Column(Text, comment="版本变更说明（如 A01 拆分为两柜）")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="版本创建时间")

    floor = relationship("Floor", back_populates="unit_map_versions")
    base_map = relationship("BaseMap", back_populates="unit_map_versions")
    geo_elements = relationship("GeoElement", back_populates="version", passive_deletes=True)
    evolution_from = relationship(
        "SpatialEvolutionLog",
        foreign_keys="SpatialEvolutionLog.from_version_id",
        back_populates="from_version",
    )
    evolution_to = relationship(
        "SpatialEvolutionLog",
        foreign_keys="SpatialEvolutionLog.to_version_id",
        back_populates="to_version",
    )


class BusinessUnit(Base):
    """经营单元主表：柜位业务身份证，不随图纸变化"""
    __tablename__ = "business_units"
    __table_args__ = (
        UniqueConstraint("floor_id", "unit_code", name="uq_business_units_floor_unit"),
        CheckConstraint(
            "status IN ('ACTIVE','VACANT','FITOUT','INACTIVE')",
            name="ck_unit_status",
        ),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="经营单元ID，系统主键")
    floor_id = Column(BigInteger, ForeignKey("floors.id", ondelete="RESTRICT"), nullable=False, comment="所属楼层ID")
    unit_code = Column(Text, nullable=False, comment="柜位业务编号，如 A118 / B101")
    status = Column(Text, nullable=False, server_default="ACTIVE", comment="经营状态：ACTIVE经营中 / VACANT空置 / FITOUT装修中 / INACTIVE失效")
    manual_area = Column(Numeric(12, 2), comment="人工确认的计租面积（合同面积）")
    parent_unit_id = Column(BigInteger, ForeignKey("business_units.id"), comment="父柜位ID（用于拆分/合并溯源）")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    floor = relationship("Floor", back_populates="business_units")
    parent_unit = relationship("BusinessUnit", remote_side="BusinessUnit.id")
    geo_elements = relationship("GeoElement", back_populates="unit")


class GeoElement(Base):
    """空间几何明细表：存储每个柜位在某版本下的 SVG 矢量信息"""
    __tablename__ = "geo_elements"
    __table_args__ = (
        UniqueConstraint("version_id", "unit_id", name="uq_geo_elements_version_unit"),
        Index("ix_geo_elements_version", "version_id"),
        Index("ix_geo_elements_unit", "unit_id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="几何元素ID，系统主键")
    version_id = Column(BigInteger, ForeignKey("unit_map_versions.id", ondelete="CASCADE"), nullable=False, comment="所属柜位图版本ID")
    unit_id = Column(BigInteger, ForeignKey("business_units.id", ondelete="RESTRICT"), nullable=False, comment="对应的经营单元ID")
    svg_element_id = Column(Text, comment="SVG 中的元素ID（如 booth-A118）")
    path_data = Column(Text, nullable=False, comment="SVG path 的 d 属性原始数据")
    centroid_x = Column(Numeric(14, 4), comment="柜位中心点 X 坐标（SVG 坐标系）")
    centroid_y = Column(Numeric(14, 4), comment="柜位中心点 Y 坐标（SVG 坐标系）")
    bbox_minx = Column(Numeric(14, 4), comment="包围盒最小 X 值")
    bbox_miny = Column(Numeric(14, 4), comment="包围盒最小 Y 值")
    bbox_maxx = Column(Numeric(14, 4), comment="包围盒最大 X 值")
    bbox_maxy = Column(Numeric(14, 4), comment="包围盒最大 Y 值")
    area_svg = Column(Numeric(14, 2), comment="系统根据 SVG 路径计算的面积（非合同面积）")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="几何记录创建时间")

    version = relationship("UnitMapVersion", back_populates="geo_elements")
    unit = relationship("BusinessUnit", back_populates="geo_elements")


class SpatialEvolutionLog(Base):
    """空间演进日志表：记录柜位拆分、合并、重构的历史过程"""
    __tablename__ = "spatial_evolution_log"
    __table_args__ = (
        CheckConstraint(
            "change_type IN ('SPLIT','MERGE','REFORM')",
            name="ck_change_type",
        ),
        Index("ix_evolution_from_to", "from_version_id", "to_version_id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="演进日志ID，系统主键")
    from_version_id = Column(BigInteger, ForeignKey("unit_map_versions.id"), nullable=False, comment="变更前的柜位图版本ID")
    to_version_id = Column(BigInteger, ForeignKey("unit_map_versions.id"), nullable=False, comment="变更后的柜位图版本ID")
    change_type = Column(Text, nullable=False, comment="变更类型：SPLIT拆分 / MERGE合并 / REFORM重构")
    source_data = Column(JSONB, nullable=False, comment="变更前涉及的柜位编号数组")
    target_data = Column(JSONB, nullable=False, comment="变更后生成的柜位编号数组")
    match_score = Column(Numeric(5, 4), comment="系统自动匹配置信度（0-1）")
    confirmed_by = Column(Text, comment="人工确认人（项目经理/文员）")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="变更记录创建时间")

    from_version = relationship("UnitMapVersion", foreign_keys=[from_version_id], back_populates="evolution_from")
    to_version = relationship("UnitMapVersion", foreign_keys=[to_version_id], back_populates="evolution_to")


class SiteSnapshot(Base):
    """全场快照表：记录某一时间点全商场楼层与图纸组合状态"""
    __tablename__ = "site_snapshots"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="快照ID，系统主键")
    snapshot_code = Column(Text, nullable=False, unique=True, comment="快照业务编码，如 SNAP_2026_Q1")
    config_json = Column(JSONB, nullable=False, comment="楼层与图纸版本组合配置 JSON")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="快照生成时间")
