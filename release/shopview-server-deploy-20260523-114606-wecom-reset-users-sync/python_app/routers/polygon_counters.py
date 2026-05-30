#!/usr/bin/env python3
"""
多边形柜位管理API
Polygon Counter Management API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from models.database import get_db
from models.models import Counter
from models.geometry_models import CounterGeometry
from routers.authz import require_permission_dependency
from utils.polygon_utils import CounterShapeManager, PolygonUtils

router = APIRouter(
    prefix="/api/polygon-counters",
    tags=["polygon-counters"]
)


class PolygonCoordinates(BaseModel):
    """多边形坐标点"""
    x: float = Field(..., description="X坐标")
    y: float = Field(..., description="Y坐标")


class RectangleCounterCreate(BaseModel):
    """矩形柜位创建请求"""
    store_id: int = Field(..., description="门店ID")
    floor_id: int = Field(..., description="楼层ID")
    counter_code: str = Field(..., max_length=20, description="柜位编号")
    counter_name: str = Field(..., max_length=100, description="柜位名称")
    x: float = Field(..., description="X坐标")
    y: float = Field(..., description="Y坐标")
    width: float = Field(..., gt=0, description="宽度")
    height: float = Field(..., gt=0, description="高度")
    counter_type: str = Field(default="标准柜位", max_length=50, description="柜位类型")
    status: str = Field(default="vacant", description="状态")
    monthly_rent: float = Field(default=0.0, description="月租金")
    management_fee: float = Field(default=0.0, description="管理费")
    deposit: float = Field(default=0.0, description="押金")
    group_code: str = Field(None, max_length=20, description="柜组编码")


class PolygonCounterCreate(BaseModel):
    """多边形柜位创建请求"""
    store_id: int = Field(..., description="门店ID")
    floor_id: int = Field(..., description="楼层ID")
    counter_code: str = Field(..., max_length=20, description="柜位编号")
    counter_name: str = Field(..., max_length=100, description="柜位名称")
    coordinates: List[PolygonCoordinates] = Field(..., min_items=3, description="多边形坐标点")
    counter_type: str = Field(default="标准柜位", max_length=50, description="柜位类型")
    status: str = Field(default="vacant", description="状态")
    monthly_rent: float = Field(default=0.0, description="月租金")
    management_fee: float = Field(default=0.0, description="管理费")
    deposit: float = Field(default=0.0, description="押金")
    group_code: str = Field(None, max_length=20, description="柜组编码")


class CounterShapeUpdate(BaseModel):
    """柜位形状更新请求"""
    coordinates: List[PolygonCoordinates] = Field(..., min_items=3, description="新的多边形坐标点")


def _geometry_from_shape(counter_id: int, shape_data: Dict[str, Any]) -> CounterGeometry:
    return CounterGeometry(
        counter_id=counter_id,
        shape_type=shape_data["shape_type"],
        position_x=shape_data["position_x"],
        position_y=shape_data["position_y"],
        width=shape_data["width"],
        height=shape_data["height"],
        polygon_coordinates=shape_data["polygon_coordinates"],
        center_x=shape_data["center_x"],
        center_y=shape_data["center_y"],
        bounding_box_min_x=shape_data["bounding_box_min_x"],
        bounding_box_min_y=shape_data["bounding_box_min_y"],
        bounding_box_max_x=shape_data["bounding_box_max_x"],
        bounding_box_max_y=shape_data["bounding_box_max_y"],
    )


@router.post("/rectangle", response_model=Dict[str, Any])
async def create_rectangle_counter(
    counter_data: RectangleCounterCreate,
    db: Session = Depends(get_db),
    _=Depends(require_permission_dependency("counter.create")),
):
    """创建矩形柜位"""
    try:
        # 检查柜位编号是否已存在
        existing = db.query(Counter).filter(
            Counter.counter_code == counter_data.counter_code
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"柜位编号 {counter_data.counter_code} 已存在"
            )
        
        # 创建矩形柜位形状数据
        shape_data = CounterShapeManager.create_rectangle_counter(
            counter_data.x,
            counter_data.y,
            counter_data.width,
            counter_data.height
        )
        
        # 创建柜位记录
        counter = Counter(
            store_id=counter_data.store_id,
            floor_id=counter_data.floor_id,
            counter_code=counter_data.counter_code,
            counter_name=counter_data.counter_name,
            area=shape_data['area'],
            position_x=shape_data['position_x'],
            position_y=shape_data['position_y'],
            width=shape_data['width'],
            height=shape_data['height'],
            counter_type=counter_data.counter_type,
            status=counter_data.status,
            monthly_rent=counter_data.monthly_rent,
            management_fee=counter_data.management_fee,
            deposit=counter_data.deposit,
            group_code=counter_data.group_code,
            is_active=True
        )

        db.add(counter)
        db.flush()
        geometry = _geometry_from_shape(counter.counter_id, shape_data)
        db.add(geometry)
        db.commit()
        db.refresh(counter)
        db.refresh(geometry)
        
        return {
            "message": "矩形柜位创建成功",
            "counter_id": counter.counter_id,
            "counter_code": counter.counter_code,
            "shape_type": geometry.shape_type,
            "area": float(counter.area)
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建矩形柜位失败: {str(e)}")


@router.post("/polygon", response_model=Dict[str, Any])
async def create_polygon_counter(
    counter_data: PolygonCounterCreate,
    db: Session = Depends(get_db),
    _=Depends(require_permission_dependency("counter.create")),
):
    """创建多边形柜位"""
    try:
        # 检查柜位编号是否已存在
        existing = db.query(Counter).filter(
            Counter.counter_code == counter_data.counter_code
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"柜位编号 {counter_data.counter_code} 已存在"
            )
        
        # 转换坐标格式
        coordinates = [[coord.x, coord.y] for coord in counter_data.coordinates]
        
        # 创建多边形柜位形状数据
        shape_data = CounterShapeManager.create_polygon_counter(coordinates)
        
        # 创建柜位记录
        counter = Counter(
            store_id=counter_data.store_id,
            floor_id=counter_data.floor_id,
            counter_code=counter_data.counter_code,
            counter_name=counter_data.counter_name,
            area=shape_data['area'],
            position_x=shape_data['position_x'],
            position_y=shape_data['position_y'],
            width=shape_data['width'],
            height=shape_data['height'],
            counter_type=counter_data.counter_type,
            status=counter_data.status,
            monthly_rent=counter_data.monthly_rent,
            management_fee=counter_data.management_fee,
            deposit=counter_data.deposit,
            group_code=counter_data.group_code,
            is_active=True
        )

        db.add(counter)
        db.flush()
        geometry = _geometry_from_shape(counter.counter_id, shape_data)
        db.add(geometry)
        db.commit()
        db.refresh(counter)
        db.refresh(geometry)
        
        return {
            "message": "多边形柜位创建成功",
            "counter_id": counter.counter_id,
            "counter_code": counter.counter_code,
            "shape_type": geometry.shape_type,
            "area": float(counter.area)
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"无效的多边形数据: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建多边形柜位失败: {str(e)}")


@router.put("/{counter_id}/shape", response_model=Dict[str, Any])
async def update_counter_shape(
    counter_id: int,
    shape_update: CounterShapeUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_permission_dependency("counter.edit")),
):
    """更新柜位形状"""
    try:
        # 查找柜位
        counter = db.query(Counter).filter(Counter.counter_id == counter_id).first()
        if not counter:
            raise HTTPException(status_code=404, detail="柜位不存在")
        
        # 转换坐标格式
        coordinates = [[coord.x, coord.y] for coord in shape_update.coordinates]
        
        # 更新形状数据
        shape_data = CounterShapeManager.create_polygon_counter(coordinates)
        
        counter.area = shape_data['area']
        counter.position_x = shape_data['position_x']
        counter.position_y = shape_data['position_y']
        counter.width = shape_data['width']
        counter.height = shape_data['height']

        geometry = db.query(CounterGeometry).filter(CounterGeometry.counter_id == counter_id).first()
        if not geometry:
            geometry = _geometry_from_shape(counter_id, shape_data)
            db.add(geometry)
        else:
            geometry.shape_type = shape_data["shape_type"]
            geometry.position_x = shape_data["position_x"]
            geometry.position_y = shape_data["position_y"]
            geometry.width = shape_data["width"]
            geometry.height = shape_data["height"]
            geometry.polygon_coordinates = shape_data["polygon_coordinates"]
            geometry.center_x = shape_data["center_x"]
            geometry.center_y = shape_data["center_y"]
            geometry.bounding_box_min_x = shape_data["bounding_box_min_x"]
            geometry.bounding_box_min_y = shape_data["bounding_box_min_y"]
            geometry.bounding_box_max_x = shape_data["bounding_box_max_x"]
            geometry.bounding_box_max_y = shape_data["bounding_box_max_y"]

        db.commit()
        
        return {
            "message": "柜位形状更新成功",
            "counter_id": counter.counter_id,
            "counter_code": counter.counter_code,
            "shape_type": geometry.shape_type,
            "area": float(counter.area)
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"无效的多边形数据: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新柜位形状失败: {str(e)}")


@router.get("/{counter_id}/coordinates", response_model=Dict[str, Any])
async def get_counter_coordinates(
    counter_id: int,
    db: Session = Depends(get_db)
):
    """获取柜位坐标信息"""
    try:
        counter = db.query(Counter).filter(Counter.counter_id == counter_id).first()
        if not counter:
            raise HTTPException(status_code=404, detail="柜位不存在")
        
        geometry = db.query(CounterGeometry).filter(CounterGeometry.counter_id == counter_id).first()
        if not geometry:
            raise HTTPException(status_code=404, detail="柜位几何信息不存在")

        # 解析坐标数据
        coordinates = []
        if geometry.polygon_coordinates:
            coordinates = PolygonUtils.json_to_coordinates(geometry.polygon_coordinates)

        return {
            "counter_id": counter.counter_id,
            "counter_code": counter.counter_code,
            "shape_type": geometry.shape_type,
            "coordinates": coordinates,
            "center": {
                "x": float(geometry.center_x) if geometry.center_x else None,
                "y": float(geometry.center_y) if geometry.center_y else None
            },
            "bounding_box": {
                "min_x": float(geometry.bounding_box_min_x) if geometry.bounding_box_min_x else None,
                "min_y": float(geometry.bounding_box_min_y) if geometry.bounding_box_min_y else None,
                "max_x": float(geometry.bounding_box_max_x) if geometry.bounding_box_max_x else None,
                "max_y": float(geometry.bounding_box_max_y) if geometry.bounding_box_max_y else None
            },
            "area": float(counter.area) if counter.area else 0.0
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取柜位坐标失败: {str(e)}")


@router.post("/validate-polygon", response_model=Dict[str, Any])
async def validate_polygon(coordinates: List[PolygonCoordinates]):
    """验证多边形是否有效"""
    try:
        coords = [[coord.x, coord.y] for coord in coordinates]
        is_valid = PolygonUtils.validate_polygon(coords)
        area = PolygonUtils.calculate_polygon_area(coords) if is_valid else 0.0
        
        return {
            "is_valid": is_valid,
            "area": area,
            "coordinates": coords
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"验证多边形失败: {str(e)}")






