#!/usr/bin/env python3
"""
几何信息管理API
Geometry Management API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from models.database import get_db
from models.models import Counter
from routers.authz import require_permission_dependency
try:
    from models.geometry_models import CounterGeometry, CounterGeometryProperty
except ImportError:
    # 如果geometry_models不存在，定义空的类
    CounterGeometry = None
    CounterGeometryProperty = None
from utils.polygon_utils import CounterShapeManager, PolygonUtils

router = APIRouter(
    prefix="/api/geometry",
    tags=["geometry-management"]
)


class GeometryCoordinates(BaseModel):
    """几何坐标点"""
    x: float = Field(..., description="X坐标")
    y: float = Field(..., description="Y坐标")


class RectangleGeometryCreate(BaseModel):
    """矩形几何创建请求"""
    counter_id: int = Field(..., description="柜位ID")
    position_x: float = Field(..., description="X坐标")
    position_y: float = Field(..., description="Y坐标")
    width: float = Field(..., gt=0, description="宽度")
    height: float = Field(..., gt=0, description="高度")
    rotation: float = Field(default=0, description="旋转角度")


class PolygonGeometryCreate(BaseModel):
    """多边形几何创建请求"""
    counter_id: int = Field(..., description="柜位ID")
    coordinates: List[GeometryCoordinates] = Field(..., min_items=3, description="多边形坐标点")


class CircleGeometryCreate(BaseModel):
    """圆形几何创建请求"""
    counter_id: int = Field(..., description="柜位ID")
    center_x: float = Field(..., description="圆心X坐标")
    center_y: float = Field(..., description="圆心Y坐标")
    radius: float = Field(..., gt=0, description="半径")


class GeometryPropertyCreate(BaseModel):
    """几何属性创建请求"""
    property_name: str = Field(..., max_length=50, description="属性名")
    property_value: str = Field(..., description="属性值")
    property_type: str = Field(default="string", description="属性类型")


@router.post("/rectangle", response_model=Dict[str, Any])
async def create_rectangle_geometry(
    geometry_data: RectangleGeometryCreate,
    db: Session = Depends(get_db),
    _=Depends(require_permission_dependency("counter.edit")),
):
    """创建矩形几何信息"""
    try:
        # 检查柜位是否存在
        counter = db.query(Counter).filter(Counter.counter_id == geometry_data.counter_id).first()
        if not counter:
            raise HTTPException(status_code=404, detail="柜位不存在")
        
        # 检查是否已有几何信息
        existing = db.query(CounterGeometry).filter(
            CounterGeometry.counter_id == geometry_data.counter_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="该柜位已有几何信息")
        
        # 创建矩形几何数据
        shape_data = CounterShapeManager.create_rectangle_counter(
            geometry_data.position_x,
            geometry_data.position_y,
            geometry_data.width,
            geometry_data.height
        )
        
        # 创建几何记录
        geometry = CounterGeometry(
            counter_id=geometry_data.counter_id,
            shape_type="rectangle",
            position_x=geometry_data.position_x,
            position_y=geometry_data.position_y,
            width=geometry_data.width,
            height=geometry_data.height,
            rotation=geometry_data.rotation,
            bounding_box_min_x=shape_data['bounding_box_min_x'],
            bounding_box_min_y=shape_data['bounding_box_min_y'],
            bounding_box_max_x=shape_data['bounding_box_max_x'],
            bounding_box_max_y=shape_data['bounding_box_max_y']
        )
        
        db.add(geometry)
        db.commit()
        db.refresh(geometry)
        
        return {
            "message": "矩形几何信息创建成功",
            "geometry_id": geometry.geometry_id,
            "counter_id": geometry.counter_id,
            "shape_type": geometry.shape_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建矩形几何信息失败: {str(e)}")


@router.post("/polygon", response_model=Dict[str, Any])
async def create_polygon_geometry(
    geometry_data: PolygonGeometryCreate,
    db: Session = Depends(get_db),
    _=Depends(require_permission_dependency("counter.edit")),
):
    """创建多边形几何信息"""
    try:
        # 检查柜位是否存在
        counter = db.query(Counter).filter(Counter.counter_id == geometry_data.counter_id).first()
        if not counter:
            raise HTTPException(status_code=404, detail="柜位不存在")
        
        # 检查是否已有几何信息
        existing = db.query(CounterGeometry).filter(
            CounterGeometry.counter_id == geometry_data.counter_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="该柜位已有几何信息")
        
        # 转换坐标格式
        coordinates = [[coord.x, coord.y] for coord in geometry_data.coordinates]
        
        # 创建多边形几何数据
        shape_data = CounterShapeManager.create_polygon_counter(coordinates)
        
        # 创建几何记录
        geometry = CounterGeometry(
            counter_id=geometry_data.counter_id,
            shape_type="polygon",
            polygon_coordinates=shape_data['polygon_coordinates'],
            bounding_box_min_x=shape_data['bounding_box_min_x'],
            bounding_box_min_y=shape_data['bounding_box_min_y'],
            bounding_box_max_x=shape_data['bounding_box_max_x'],
            bounding_box_max_y=shape_data['bounding_box_max_y']
        )
        
        db.add(geometry)
        db.commit()
        db.refresh(geometry)
        
        return {
            "message": "多边形几何信息创建成功",
            "geometry_id": geometry.geometry_id,
            "counter_id": geometry.counter_id,
            "shape_type": geometry.shape_type
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"无效的多边形数据: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建多边形几何信息失败: {str(e)}")


@router.post("/circle", response_model=Dict[str, Any])
async def create_circle_geometry(
    geometry_data: CircleGeometryCreate,
    db: Session = Depends(get_db),
    _=Depends(require_permission_dependency("counter.edit")),
):
    """创建圆形几何信息"""
    try:
        # 检查柜位是否存在
        counter = db.query(Counter).filter(Counter.counter_id == geometry_data.counter_id).first()
        if not counter:
            raise HTTPException(status_code=404, detail="柜位不存在")
        
        # 检查是否已有几何信息
        existing = db.query(CounterGeometry).filter(
            CounterGeometry.counter_id == geometry_data.counter_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="该柜位已有几何信息")
        
        # 计算边界框
        min_x = geometry_data.center_x - geometry_data.radius
        min_y = geometry_data.center_y - geometry_data.radius
        max_x = geometry_data.center_x + geometry_data.radius
        max_y = geometry_data.center_y + geometry_data.radius
        
        # 创建几何记录
        geometry = CounterGeometry(
            counter_id=geometry_data.counter_id,
            shape_type="circle",
            center_x=geometry_data.center_x,
            center_y=geometry_data.center_y,
            radius=geometry_data.radius,
            bounding_box_min_x=min_x,
            bounding_box_min_y=min_y,
            bounding_box_max_x=max_x,
            bounding_box_max_y=max_y
        )
        
        db.add(geometry)
        db.commit()
        db.refresh(geometry)
        
        return {
            "message": "圆形几何信息创建成功",
            "geometry_id": geometry.geometry_id,
            "counter_id": geometry.counter_id,
            "shape_type": geometry.shape_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建圆形几何信息失败: {str(e)}")


@router.get("/counter/{counter_id}", response_model=Dict[str, Any])
async def get_counter_geometry(
    counter_id: int,
    db: Session = Depends(get_db)
):
    """获取柜位几何信息"""
    try:
        geometry = db.query(CounterGeometry).options(
            joinedload(CounterGeometry.properties)
        ).filter(CounterGeometry.counter_id == counter_id).first()
        
        if not geometry:
            raise HTTPException(status_code=404, detail="柜位几何信息不存在")
        
        # 构建响应数据
        result = {
            "geometry_id": geometry.geometry_id,
            "counter_id": geometry.counter_id,
            "shape_type": geometry.shape_type,
            "bounding_box": {
                "min_x": float(geometry.bounding_box_min_x) if geometry.bounding_box_min_x else None,
                "min_y": float(geometry.bounding_box_min_y) if geometry.bounding_box_min_y else None,
                "max_x": float(geometry.bounding_box_max_x) if geometry.bounding_box_max_x else None,
                "max_y": float(geometry.bounding_box_max_y) if geometry.bounding_box_max_y else None
            },
            "properties": []
        }
        
        # 根据形状类型添加特定字段
        if geometry.shape_type == "rectangle":
            result.update({
                "position_x": float(geometry.position_x) if geometry.position_x else None,
                "position_y": float(geometry.position_y) if geometry.position_y else None,
                "width": float(geometry.width) if geometry.width else None,
                "height": float(geometry.height) if geometry.height else None,
                "rotation": float(geometry.rotation) if geometry.rotation else 0
            })
        elif geometry.shape_type == "polygon":
            coordinates = []
            if geometry.polygon_coordinates:
                coordinates = PolygonUtils.json_to_coordinates(geometry.polygon_coordinates)
            result["coordinates"] = coordinates
        elif geometry.shape_type == "circle":
            result.update({
                "center_x": float(geometry.center_x) if geometry.center_x else None,
                "center_y": float(geometry.center_y) if geometry.center_y else None,
                "radius": float(geometry.radius) if geometry.radius else None
            })
        
        # 添加属性
        for prop in geometry.properties:
            result["properties"].append({
                "property_name": prop.property_name,
                "property_value": prop.property_value,
                "property_type": prop.property_type
            })
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取柜位几何信息失败: {str(e)}")


@router.post("/{geometry_id}/properties", response_model=Dict[str, Any])
async def add_geometry_property(
    geometry_id: int,
    property_data: GeometryPropertyCreate,
    db: Session = Depends(get_db),
    _=Depends(require_permission_dependency("counter.edit")),
):
    """为几何信息添加属性"""
    try:
        # 检查几何信息是否存在
        geometry = db.query(CounterGeometry).filter(
            CounterGeometry.geometry_id == geometry_id
        ).first()
        if not geometry:
            raise HTTPException(status_code=404, detail="几何信息不存在")
        
        # 创建属性记录
        property_obj = CounterGeometryProperty(
            geometry_id=geometry_id,
            property_name=property_data.property_name,
            property_value=property_data.property_value,
            property_type=property_data.property_type
        )
        
        db.add(property_obj)
        db.commit()
        db.refresh(property_obj)
        
        return {
            "message": "几何属性添加成功",
            "property_id": property_obj.property_id,
            "geometry_id": geometry_id,
            "property_name": property_obj.property_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"添加几何属性失败: {str(e)}")


@router.get("/counters/with-geometry", response_model=List[Dict[str, Any]])
async def get_counters_with_geometry(
    skip: int = 0,
    limit: int = 100,
    shape_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取带几何信息的柜位列表"""
    try:
        query = db.query(Counter, CounterGeometry).join(
            CounterGeometry,
            Counter.counter_id == CounterGeometry.counter_id,
        )
        
        if shape_type:
            query = query.filter(CounterGeometry.shape_type == shape_type)
        
        rows = query.offset(skip).limit(limit).all()
        
        result = []
        for counter, geometry in rows:
            counter_data = {
                "counter_id": counter.counter_id,
                "counter_code": counter.counter_code,
                "counter_name": counter.counter_name,
                "area": float(counter.area) if counter.area else None,
                "status": counter.status,
                "geometry": {
                    "geometry_id": geometry.geometry_id,
                    "shape_type": geometry.shape_type,
                    "bounding_box": {
                        "min_x": float(geometry.bounding_box_min_x) if geometry.bounding_box_min_x else None,
                        "min_y": float(geometry.bounding_box_min_y) if geometry.bounding_box_min_y else None,
                        "max_x": float(geometry.bounding_box_max_x) if geometry.bounding_box_max_x else None,
                        "max_y": float(geometry.bounding_box_max_y) if geometry.bounding_box_max_y else None,
                    },
                },
            }
            result.append(counter_data)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取柜位几何信息列表失败: {str(e)}")



