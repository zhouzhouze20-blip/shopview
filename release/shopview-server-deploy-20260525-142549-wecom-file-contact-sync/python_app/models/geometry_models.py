#!/usr/bin/env python3
"""
几何信息模型
Geometry Models
"""
from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class CounterGeometry(Base):
    """柜位几何信息表"""
    __tablename__ = "counter_geometries"

    geometry_id = Column(Integer, primary_key=True, index=True)
    counter_id = Column(Integer, ForeignKey("counters.counter_id"), nullable=False, comment="柜位ID")
    shape_type = Column(String(20), nullable=False, comment="形状类型：rectangle-矩形, polygon-多边形, circle-圆形, ellipse-椭圆")
    
    # 矩形字段
    position_x = Column(Numeric(10, 2), comment="X坐标（矩形）")
    position_y = Column(Numeric(10, 2), comment="Y坐标（矩形）")
    width = Column(Numeric(10, 2), comment="宽度（矩形）")
    height = Column(Numeric(10, 2), comment="高度（矩形）")
    rotation = Column(Numeric(5, 2), default=0, comment="旋转角度")
    
    # 多边形字段
    polygon_coordinates = Column(Text, comment="多边形坐标点，JSON格式：[[x1,y1],[x2,y2],...]")
    
    # 圆形字段
    center_x = Column(Numeric(10, 2), comment="圆心X坐标")
    center_y = Column(Numeric(10, 2), comment="圆心Y坐标")
    radius = Column(Numeric(10, 2), comment="半径")
    
    # 椭圆字段
    ellipse_center_x = Column(Numeric(10, 2), comment="椭圆中心X坐标")
    ellipse_center_y = Column(Numeric(10, 2), comment="椭圆中心Y坐标")
    ellipse_radius_x = Column(Numeric(10, 2), comment="椭圆X轴半径")
    ellipse_radius_y = Column(Numeric(10, 2), comment="椭圆Y轴半径")
    ellipse_rotation = Column(Numeric(5, 2), comment="椭圆旋转角度")
    
    # 通用字段
    bounding_box_min_x = Column(Numeric(10, 2), comment="边界框最小X坐标")
    bounding_box_min_y = Column(Numeric(10, 2), comment="边界框最小Y坐标")
    bounding_box_max_x = Column(Numeric(10, 2), comment="边界框最大X坐标")
    bounding_box_max_y = Column(Numeric(10, 2), comment="边界框最大Y坐标")
    
    # 元数据
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    # 关联关系
    # counter = relationship("Counter", back_populates="geometry")
    properties = relationship("CounterGeometryProperty", back_populates="geometry", cascade="all, delete-orphan")


class CounterGeometryProperty(Base):
    """柜位几何属性表"""
    __tablename__ = "counter_geometry_properties"

    property_id = Column(Integer, primary_key=True, index=True)
    geometry_id = Column(Integer, ForeignKey("counter_geometries.geometry_id"), nullable=False, comment="几何信息ID")
    property_name = Column(String(50), nullable=False, comment="属性名")
    property_value = Column(Text, comment="属性值（JSON格式）")
    property_type = Column(String(20), comment="属性类型：string, number, boolean, json")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")

    # 关联关系
    geometry = relationship("CounterGeometry", back_populates="properties")

