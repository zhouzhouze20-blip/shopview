"""
收益仪表盘专用API
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from utils.floor_table import resolve_floor_table
from typing import List, Optional
from models.database import get_db
from pydantic import BaseModel
from decimal import Decimal
from fastapi import HTTPException

router = APIRouter(
    prefix="/api/revenue-dashboard",
    tags=["revenue-dashboard"]
)

class RevenueCounter(BaseModel):
    counter_id: int
    counter_code: str
    counter_name: Optional[str] = None
    area: Optional[Decimal] = None
    position_x: Optional[Decimal] = None
    position_y: Optional[Decimal] = None
    width: Optional[Decimal] = None
    height: Optional[Decimal] = None
    counter_type: Optional[str] = None
    status: str
    group_code: Optional[str] = None
    monthly_revenue: Optional[Decimal] = None
    daily_revenue: Optional[Decimal] = None
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    floor_name: Optional[str] = None
    floor_number: Optional[int] = None
    floor_display_name: Optional[str] = None
    floor_description: Optional[str] = None
    building_code: Optional[str] = None
    building_name: Optional[str] = None

@router.get("/counters", response_model=List[RevenueCounter])
async def get_revenue_counters(
    skip: int = 0,
    limit: int = Query(1000, ge=1, le=10000, description="限制记录数"),
    store_id: Optional[int] = Query(None, description="门店ID"),
    floor_id: Optional[int] = Query(None, description="楼层ID"),
    db: Session = Depends(get_db)
):
    """获取收益仪表盘柜位数据"""
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
            
        sql_query += " ORDER BY c.counter_id LIMIT :limit OFFSET :offset"
        params['limit'] = limit
        params['offset'] = skip
        
        # 执行查询
        results = db.execute(text(sql_query), params).fetchall()
        
        # 构建返回结果
        result = []
        for row in results:
            counter_data = RevenueCounter(
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
                group_code=row.group_code,
                monthly_revenue=row.monthly_revenue,
                daily_revenue=row.daily_revenue,  # 确保包含daily_revenue
                is_active=row.is_active,
                created_at=str(row.created_at) if row.created_at else None,
                updated_at=str(row.updated_at) if row.updated_at else None,
                floor_name=row.floor_name,
                floor_number=row.floor_number,
                floor_display_name=row.floor_display_name,
                floor_description=row.floor_description,
                building_code=row.building_code,
                building_name=row.building_name,
            )
            result.append(counter_data)
        
        return result
    except Exception as e:
        print(f"获取收益柜位数据时出错: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取收益柜位数据失败: {str(e)}")

# 收益分解数据模型
class RevenueBreakdown(BaseModel):
    total_revenue: Optional[Decimal] = None
    sales_profit: Optional[Decimal] = None
    fees: Optional[Decimal] = None
    sales_profit_percentage: Optional[Decimal] = None
    fees_percentage: Optional[Decimal] = None
    profit_margin: Optional[Decimal] = None
    fee_breakdown: Optional[List[dict]] = []
    sales_breakdown: Optional[List[dict]] = []

# 费用数据模型
class FeeDetail(BaseModel):
    fee_id: int
    fee_type: str
    amount: Decimal
    description: Optional[str] = None
    fee_date: str
    counter_id: int

# 订单数据模型
class OrderDetail(BaseModel):
    order_id: str
    order_date: str
    total_amount: Decimal
    counter_id: int
    status: str

# 订单明细数据模型
class OrderItem(BaseModel):
    item_id: int
    order_id: str
    product_name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal

@router.get("/counter/{counter_id}/breakdown", response_model=RevenueBreakdown)
async def get_counter_revenue_breakdown(
    counter_id: int,
    date_filter: str = Query("today", description="日期筛选"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    db: Session = Depends(get_db)
):
    """获取柜位收益分解数据"""
    try:
        # 构建日期条件
        date_condition = ""
        params = {"counter_id": counter_id}
        
        if date_filter == "today":
            date_condition = "AND DATE(r.created_at) = CURRENT_DATE"
        elif date_filter == "month":
            date_condition = "AND DATE_TRUNC('month', r.created_at) = DATE_TRUNC('month', CURRENT_DATE)"
        elif date_filter == "custom" and start_date and end_date:
            date_condition = "AND r.created_at >= :start_date AND r.created_at <= :end_date"
            params['start_date'] = start_date
            params['end_date'] = end_date
        
        # 查询收益分解数据
        sql_query = f"""
        SELECT 
            SUM(COALESCE(r.monthly_revenue, 0)) as total_revenue,
            SUM(COALESCE(r.monthly_revenue, 0)) as sales_profit,
            SUM(COALESCE(f.fee_amount, 0)) as fees
        FROM revenue_data r
        LEFT JOIN fees f ON r.counter_id = f.counter_id AND f.fee_date = r.date
        WHERE r.counter_id = :counter_id {date_condition}
        """
        
        result = db.execute(text(sql_query), params).fetchone()
        
        if result and result.total_revenue:
            total_revenue = result.total_revenue
            sales_profit = result.sales_profit or 0
            fees = result.fees or 0
            
            sales_profit_percentage = (sales_profit / total_revenue * 100) if total_revenue > 0 else 0
            fees_percentage = (fees / total_revenue * 100) if total_revenue > 0 else 0
            profit_margin = ((total_revenue - fees) / total_revenue * 100) if total_revenue > 0 else 0
            
            return RevenueBreakdown(
                total_revenue=total_revenue,
                sales_profit=sales_profit,
                fees=fees,
                sales_profit_percentage=sales_profit_percentage,
                fees_percentage=fees_percentage,
                profit_margin=profit_margin,
                fee_breakdown=[],
                sales_breakdown=[]
            )
        else:
            return RevenueBreakdown()
            
    except Exception as e:
        print(f"获取收益分解数据时出错: {e}")
        raise HTTPException(status_code=500, detail=f"获取收益分解数据失败: {str(e)}")

@router.get("/counter/{counter_id}/fees", response_model=List[FeeDetail])
async def get_counter_fees(
    counter_id: int,
    date_filter: str = Query("today", description="日期筛选"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    db: Session = Depends(get_db)
):
    """获取柜位费用列表"""
    try:
        # 构建日期条件
        date_condition = ""
        params = {"counter_id": counter_id}
        
        if date_filter == "today":
            date_condition = "AND DATE(f.fee_date) = CURRENT_DATE"
        elif date_filter == "month":
            date_condition = "AND DATE_TRUNC('month', f.fee_date) = DATE_TRUNC('month', CURRENT_DATE)"
        elif date_filter == "custom" and start_date and end_date:
            date_condition = "AND f.fee_date >= :start_date AND f.fee_date <= :end_date"
            params['start_date'] = start_date
            params['end_date'] = end_date
        
        # 查询费用数据 - 使用fees表
        sql_query = f"""
        SELECT 
            f.fee_id,
            f.fee_type,
            f.fee_amount as amount,
            f.fee_description as description,
            f.fee_date::text as fee_date,
            f.counter_id
        FROM fees f
        WHERE f.counter_id = :counter_id {date_condition}
        ORDER BY f.fee_date DESC
        """
        
        results = db.execute(text(sql_query), params).fetchall()
        
        fees = []
        for row in results:
            fee = FeeDetail(
                fee_id=row.fee_id,
                fee_type=row.fee_type,
                amount=row.amount,
                description=row.description,
                fee_date=row.fee_date,
                counter_id=row.counter_id
            )
            fees.append(fee)
        
        return fees
        
    except Exception as e:
        print(f"获取费用列表时出错: {e}")
        raise HTTPException(status_code=500, detail=f"获取费用列表失败: {str(e)}")

@router.get("/counter/{counter_id}/orders", response_model=List[OrderDetail])
async def get_counter_orders(
    counter_id: int,
    date_filter: str = Query("today", description="日期筛选"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    db: Session = Depends(get_db)
):
    """获取柜位订单列表"""
    try:
        # 构建日期条件
        date_condition = ""
        params = {"counter_id": counter_id}
        
        if date_filter == "today":
            date_condition = "AND DATE(o.order_date) = CURRENT_DATE"
        elif date_filter == "month":
            date_condition = "AND DATE_TRUNC('month', o.order_date) = DATE_TRUNC('month', CURRENT_DATE)"
        elif date_filter == "custom" and start_date and end_date:
            date_condition = "AND o.order_date >= :start_date AND o.order_date <= :end_date"
            params['start_date'] = start_date
            params['end_date'] = end_date
        
        # 查询订单数据 - 使用orders表
        sql_query = f"""
        SELECT 
            o.order_id,
            o.order_date::text as order_date,
            o.final_amount as total_amount,
            o.counter_id,
            o.order_status as status
        FROM orders o
        WHERE o.counter_id = :counter_id {date_condition}
        ORDER BY o.order_date DESC
        """
        
        results = db.execute(text(sql_query), params).fetchall()
        
        orders = []
        for row in results:
            order = OrderDetail(
                order_id=row.order_id,
                order_date=row.order_date,
                total_amount=row.total_amount,
                counter_id=row.counter_id,
                status=row.status
            )
            orders.append(order)
        
        return orders
        
    except Exception as e:
        print(f"获取订单列表时出错: {e}")
        raise HTTPException(status_code=500, detail=f"获取订单列表失败: {str(e)}")

@router.get("/order/{order_id}/items", response_model=List[OrderItem])
async def get_order_items(
    order_id: str,
    db: Session = Depends(get_db)
):
    """获取订单明细"""
    try:
        # 查询订单明细 - 使用order_items表
        sql_query = """
        SELECT 
            oi.item_id,
            oi.order_id,
            oi.product_name,
            oi.quantity,
            oi.unit_price,
            oi.total_price
        FROM order_items oi
        WHERE oi.order_id = :order_id
        """
        
        results = db.execute(text(sql_query), {
            "order_id": order_id
        }).fetchall()
        
        items = []
        for row in results:
            item = OrderItem(
                item_id=row.item_id,
                order_id=row.order_id,
                product_name=row.product_name,
                quantity=row.quantity,
                unit_price=row.unit_price,
                total_price=row.total_price
            )
            items.append(item)
        
        return items
        
    except Exception as e:
        print(f"获取订单明细时出错: {e}")
        raise HTTPException(status_code=500, detail=f"获取订单明细失败: {str(e)}")

@router.get("/test")
async def test_endpoint():
    """测试端点"""
    return {"message": "revenue-dashboard API is working"}

@router.get("/summary")
async def get_revenue_summary(
    date_filter: str = Query("today", description="日期筛选"),
    store_id: Optional[int] = Query(None, description="门店ID"),
    floor_id: Optional[int] = Query(None, description="楼层ID"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    db: Session = Depends(get_db)
):
    """获取收益汇总数据"""
    try:
        # 构建筛选条件
        where_conditions = []
        params = {}
        
        if store_id is not None:
            where_conditions.append("c.store_id = :store_id")
            params['store_id'] = store_id
        if floor_id is not None:
            where_conditions.append("c.floor_id = :floor_id")
            params['floor_id'] = floor_id
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # 构建日期条件
        date_condition = ""
        if date_filter == "today":
            date_condition = "AND DATE(r.created_at) = CURRENT_DATE"
        elif date_filter == "month":
            date_condition = "AND DATE_TRUNC('month', r.created_at) = DATE_TRUNC('month', CURRENT_DATE)"
        elif date_filter == "custom" and start_date and end_date:
            date_condition = "AND r.created_at >= :start_date AND r.created_at <= :end_date"
            params['start_date'] = start_date
            params['end_date'] = end_date
        
        # 查询收益汇总
        sql_query = f"""
        SELECT 
            SUM(COALESCE(r.daily_revenue, 0)) as total_daily_revenue,
            SUM(COALESCE(r.monthly_revenue, 0)) as total_monthly_revenue,
            AVG(COALESCE(r.revenue_per_sqm, 0)) as avg_revenue_per_sqm,
            COUNT(DISTINCT c.counter_id) as total_counters,
            COUNT(DISTINCT CASE WHEN c.status = 'occupied' THEN c.counter_id END) as occupied_counters,
            COUNT(DISTINCT CASE WHEN c.status = 'vacant' THEN c.counter_id END) as vacant_counters,
            COUNT(DISTINCT CASE WHEN c.status = 'maintenance' THEN c.counter_id END) as maintenance_counters
        FROM counters c
        LEFT JOIN revenue_data r ON c.counter_id = r.counter_id {date_condition}
        {where_clause}
        """
        
        result = db.execute(text(sql_query), params).fetchone()
        
        if result:
            return {
                "total_daily_revenue": result.total_daily_revenue or 0,
                "total_monthly_revenue": result.total_monthly_revenue or 0,
                "avg_revenue_per_sqm": result.avg_revenue_per_sqm or 0,
                "total_counters": result.total_counters or 0,
                "occupied_counters": result.occupied_counters or 0,
                "vacant_counters": result.vacant_counters or 0,
                "maintenance_counters": result.maintenance_counters or 0,
                "year_over_year_growth": 0  # 暂时设为0，需要历史数据计算
            }
        else:
            return {
                "total_daily_revenue": 0,
                "total_monthly_revenue": 0,
                "avg_revenue_per_sqm": 0,
                "total_counters": 0,
                "occupied_counters": 0,
                "vacant_counters": 0,
                "maintenance_counters": 0,
                "year_over_year_growth": 0
            }
            
    except Exception as e:
        print(f"获取收益汇总时出错: {e}")
        raise HTTPException(status_code=500, detail=f"获取收益汇总失败: {str(e)}")
