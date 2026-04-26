"""
百货柜位管理系统 - 柜位管理API
Department Store Counter Management System - Counter Management API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from models.database import get_db
from models.models import Counter, Store
try:
    from models.geometry_models import CounterGeometry, CounterGeometryProperty
except ImportError:
    # 如果geometry_models不存在，定义空的类
    CounterGeometry = None
    CounterGeometryProperty = None
from schemas.schemas import Counter as CounterSchema, CounterCreate, CounterUpdate, BaseResponse
from sqlalchemy import text
from utils.floor_table import resolve_floor_table

router = APIRouter(
    prefix="/api/counters",
    tags=["counters"]
)


@router.get("/", response_model=List[CounterSchema])
async def get_counters(
    skip: int = 0,
    limit: int = Query(100, ge=1, le=10000, description="限制记录数"),
    store_id: Optional[int] = Query(None, description="门店ID"),
    floor_id: Optional[int] = Query(None, description="楼层ID"),
    status: Optional[str] = Query(None, description="柜位状态"),
    is_active: Optional[bool] = None,
    include_geometry: bool = Query(False, description="是否包含几何信息"),
    shape_type: Optional[str] = Query(None, description="形状类型筛选"),
    db: Session = Depends(get_db)
):
    """获取柜位列表"""
    try:
        # 使用原始SQL查询，JOIN revenue_data表获取实际收益数据
        floor_table = resolve_floor_table(db)
        floor_join_key = "floor_id" if floor_table == "store_floors" else "id"
        floor_select = (
            "f.floor_name,\n"
            "            f.floor_number,\n"
            "            f.floor_display_name,\n"
            "            f.description as floor_description,\n"
            "            f.building_code,\n"
            "            f.building_name"
        ) if floor_table == "store_floors" else (
            "f.name as floor_name,\n"
            "            NULL::int as floor_number,\n"
            "            f.floor_code as floor_display_name,\n"
            "            NULL::text as floor_description,\n"
            "            f.building_code,\n"
            "            NULL::text as building_name"
        )

        sql_query = f"""
        SELECT DISTINCT
            c.counter_id,
            c.store_id,
            c.floor_id,
            c.counter_code,
            c.counter_name,
            c.area,
            c.position_x,
            c.position_y,
            c.width,
            c.height,
            c.counter_type,
            c.status,
            c.monthly_rent,
            c.management_fee,
            c.deposit,
            c.group_code,
            c.facade_image_url,
            c.is_active,
            c.created_at,
            c.updated_at,
            -- 从revenue_data表获取实际收益数据（只取2025年9月）
            COALESCE(r.monthly_revenue, c.monthly_revenue, 0) as monthly_revenue,
            r.daily_revenue,
            r.revenue_per_sqm,
            r.revenue_trend,
            r.revenue_change_percent,
            -- 楼层信息
            {floor_select}
        FROM counters c
        LEFT JOIN revenue_data r ON c.counter_id = r.counter_id 
            AND r.year = 2025 AND r.month = 9
        JOIN {floor_table} f ON c.floor_id = f.{floor_join_key}
        WHERE 1=1
        """
        
        # 构建参数字典
        params = {}
        
        # 添加筛选条件
        if store_id is not None:
            sql_query += " AND c.store_id = :store_id"
            params['store_id'] = store_id
        if floor_id is not None:
            sql_query += " AND c.floor_id = :floor_id"
            params['floor_id'] = floor_id
        if status is not None:
            sql_query += " AND c.status = :status"
            params['status'] = status
        if is_active is not None:
            sql_query += " AND c.is_active = :is_active"
            params['is_active'] = is_active
            
        sql_query += " ORDER BY c.counter_id LIMIT :limit OFFSET :offset"
        params['limit'] = limit
        params['offset'] = skip
        
        # 执行查询
        results = db.execute(text(sql_query), params).fetchall()
        
        # 构建返回结果
        result = []
        for row in results:
            counter_data = CounterSchema(
                counter_id=row.counter_id,
                store_id=row.store_id,
                floor_id=row.floor_id,
                counter_code=row.counter_code,
                counter_name=row.counter_name,
                area=row.area,
                position_x=row.position_x,
                position_y=row.position_y,
                width=row.width,
                height=row.height,
                counter_type=row.counter_type,
                status=row.status,
                monthly_rent=row.monthly_rent,
                management_fee=row.management_fee,
                deposit=row.deposit,
                group_code=row.group_code,
                facade_image_url=row.facade_image_url,
                monthly_revenue=row.monthly_revenue,  # 使用revenue_data表中的实际收益
                daily_revenue=row.daily_revenue,  # 使用revenue_data表中的日收益
                is_active=row.is_active,
                created_at=row.created_at,
                updated_at=row.updated_at,
                # 添加楼层信息
                floor_name=row.floor_name,
                floor_number=row.floor_number,
                floor_display_name=row.floor_display_name,
                floor_description=row.floor_description,
                building_code=row.building_code,
                building_name=row.building_name,
            )
            # 添加前端期望的字段映射
            counter_data_dict = counter_data.dict()
            counter_data_dict['x'] = float(row.position_x) if row.position_x else 0.0
            counter_data_dict['y'] = float(row.position_y) if row.position_y else 0.0
            # 确保daily_revenue字段被保留
            if hasattr(row, 'daily_revenue') and row.daily_revenue is not None:
                counter_data_dict['daily_revenue'] = row.daily_revenue
            counter_data = CounterSchema(**counter_data_dict)
            result.append(counter_data)
        
        return result
    except Exception as e:
        print(f"获取柜位列表时出错: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取柜位列表失败: {str(e)}")


@router.get("/{counter_id}", response_model=CounterSchema)
async def get_counter(
    counter_id: int, 
    include_geometry: bool = Query(False, description="是否包含几何信息"),
    db: Session = Depends(get_db)
):
    """获取单个柜位信息"""
    query = db.query(Counter)
    
    if include_geometry:
        query = query.options(joinedload(Counter.geometry))
    
    counter = query.filter(Counter.counter_id == counter_id).first()
    if not counter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="柜位不存在"
        )
    return counter


@router.get("/{counter_id}/geometry")
async def get_counter_geometry(counter_id: int, db: Session = Depends(get_db)):
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
                import json
                coordinates = json.loads(geometry.polygon_coordinates)
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
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取柜位几何信息失败: {str(e)}")


@router.get("/with-geometry/list")
async def get_counters_with_geometry(
    skip: int = 0,
    limit: int = 100,
    shape_type: Optional[str] = Query(None, description="形状类型筛选"),
    db: Session = Depends(get_db)
):
    """获取带几何信息的柜位列表"""
    try:
        query = db.query(Counter).options(
            joinedload(Counter.geometry)
        ).join(CounterGeometry, Counter.counter_id == CounterGeometry.counter_id)
        
        if shape_type:
            query = query.filter(CounterGeometry.shape_type == shape_type)
        
        counters = query.offset(skip).limit(limit).all()
        
        result = []
        for counter in counters:
            counter_data = {
                "counter_id": counter.counter_id,
                "counter_code": counter.counter_code,
                "counter_name": counter.counter_name,
                "area": float(counter.area) if counter.area else None,
                "status": counter.status,
                "geometry": None
            }
            
            if counter.geometry:
                counter_data["geometry"] = {
                    "geometry_id": counter.geometry.geometry_id,
                    "shape_type": counter.geometry.shape_type,
                    "bounding_box": {
                        "min_x": float(counter.geometry.bounding_box_min_x) if counter.geometry.bounding_box_min_x else None,
                        "min_y": float(counter.geometry.bounding_box_min_y) if counter.geometry.bounding_box_min_y else None,
                        "max_x": float(counter.geometry.bounding_box_max_x) if counter.geometry.bounding_box_max_x else None,
                        "max_y": float(counter.geometry.bounding_box_max_y) if counter.geometry.bounding_box_max_y else None
                    }
                }
            
            result.append(counter_data)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取柜位几何信息列表失败: {str(e)}")


@router.post("/", response_model=CounterSchema)
async def create_counter(counter: CounterCreate, db: Session = Depends(get_db)):
    """创建新柜位"""
    # 验证门店和楼层是否存在
    store = db.query(Store).filter(Store.store_id == counter.store_id).first()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="门店不存在"
        )
    
    floor_table = resolve_floor_table(db)
    floor_key = "floor_id" if floor_table == "store_floors" else "id"
    floor_row = db.execute(
        text(f"SELECT {floor_key} FROM {floor_table} WHERE {floor_key} = :floor_id"),
        {"floor_id": counter.floor_id},
    ).first()
    if not floor_row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="楼层不存在"
        )
    
    # 检查柜位编号是否已存在
    existing_counter = db.query(Counter).filter(
        Counter.counter_code == counter.counter_code,
        Counter.store_id == counter.store_id
    ).first()
    if existing_counter:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该门店中柜位编号已存在"
        )
    
    db_counter = Counter(**counter.dict())
    db.add(db_counter)
    db.commit()
    db.refresh(db_counter)
    return db_counter


@router.put("/{counter_id}", response_model=CounterSchema)
async def update_counter(
    counter_id: int,
    counter_update: CounterUpdate,
    db: Session = Depends(get_db)
):
    """更新柜位信息"""
    db_counter = db.query(Counter).filter(Counter.counter_id == counter_id).first()
    if not db_counter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="柜位不存在"
        )
    
    update_data = counter_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_counter, field, value)
    
    db.commit()
    db.refresh(db_counter)
    return db_counter


@router.delete("/{counter_id}", response_model=BaseResponse)
async def delete_counter(counter_id: int, db: Session = Depends(get_db)):
    """删除柜位（软删除）"""
    db_counter = db.query(Counter).filter(Counter.counter_id == counter_id).first()
    if not db_counter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="柜位不存在"
        )
    
    db_counter.is_active = False
    db.commit()
    return BaseResponse(message="柜位删除成功")


@router.get("/search/", response_model=List[CounterSchema])
async def search_counters(
    keyword: str = Query(..., description="搜索关键词"),
    db: Session = Depends(get_db)
):
    """搜索柜位"""
    counters = db.query(Counter).filter(
        (Counter.counter_code.ilike(f"%{keyword}%")) |
        (Counter.counter_name.ilike(f"%{keyword}%"))
    ).all()
    return counters


@router.put("/{counter_id}/position")
async def update_counter_position(
    counter_id: int,
    position_data: dict,
    db: Session = Depends(get_db)
):
    """更新柜位位置和尺寸"""
    try:
        # 查找柜位
        counter = db.query(Counter).filter(Counter.counter_id == counter_id).first()
        if not counter:
            raise HTTPException(status_code=404, detail="柜位不存在")
        
        # 更新位置和尺寸信息
        if 'x' in position_data:
            counter.position_x = position_data['x']
        if 'y' in position_data:
            counter.position_y = position_data['y']
        if 'width' in position_data:
            counter.width = position_data['width']
        if 'height' in position_data:
            counter.height = position_data['height']
        if 'area' in position_data:
            counter.area = position_data['area']
        
        db.commit()
        db.refresh(counter)
        
        return {
            "success": True,
            "message": "柜位位置更新成功",
            "data": {
                "counter_id": counter.counter_id,
                "position_x": float(counter.position_x) if counter.position_x else 0,
                "position_y": float(counter.position_y) if counter.position_y else 0,
                "width": float(counter.width) if counter.width else 0,
                "height": float(counter.height) if counter.height else 0,
                "area": float(counter.area) if counter.area else 0
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新柜位位置失败: {str(e)}")


@router.put("/batch/position")
async def update_counters_positions(
    positions_data: List[dict],
    db: Session = Depends(get_db)
):
    """批量更新柜位位置和尺寸"""
    try:
        updated_count = 0
        results = []
        
        for item in positions_data:
            counter_id = item.get('counter_id')
            if not counter_id:
                continue
                
            counter = db.query(Counter).filter(Counter.counter_id == counter_id).first()
            if not counter:
                continue
            
            # 更新位置和尺寸信息
            if 'x' in item:
                counter.position_x = item['x']
            if 'y' in item:
                counter.position_y = item['y']
            if 'width' in item:
                counter.width = item['width']
            if 'height' in item:
                counter.height = item['height']
            if 'area' in item:
                counter.area = item['area']
            
            updated_count += 1
            results.append({
                "counter_id": counter_id,
                "success": True
            })
        
        db.commit()
        
        return {
            "success": True,
            "message": f"批量更新成功，共更新 {updated_count} 个柜位",
            "updated_count": updated_count,
            "results": results
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"批量更新柜位位置失败: {str(e)}")
