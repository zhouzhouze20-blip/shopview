"""
收益数据管理API
Revenue Data Management API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_, or_
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal

from models.database import get_db
from models.models import RevenueData
from schemas.schemas import RevenueData as RevenueDataSchema, RevenueDataCreate, RevenueDataUpdate, RevenueAnalysis, TimeSeriesAnalysis

router = APIRouter(prefix="/api/revenue-data", tags=["收益数据"])


@router.get("/", response_model=List[RevenueDataSchema])
async def get_revenue_data(
    skip: int = 0,
    limit: int = Query(1000, ge=1, le=10000, description="限制记录数"),
    counter_id: Optional[int] = Query(None, description="柜位ID"),
    store_id: Optional[int] = Query(None, description="门店ID"),
    floor_id: Optional[int] = Query(None, description="楼层ID"),
    year: Optional[int] = Query(None, description="年份"),
    month: Optional[int] = Query(None, description="月份"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db: Session = Depends(get_db)
):
    """获取收益数据列表"""
    try:
        query = db.query(RevenueData)
        
        # 添加筛选条件
        if counter_id is not None:
            query = query.filter(RevenueData.counter_id == counter_id)
        if store_id is not None:
            query = query.filter(RevenueData.store_id == store_id)
        if floor_id is not None:
            query = query.filter(RevenueData.floor_id == floor_id)
        if year is not None:
            query = query.filter(RevenueData.year == year)
        if month is not None:
            query = query.filter(RevenueData.month == month)
        if start_date is not None:
            query = query.filter(RevenueData.date >= start_date)
        if end_date is not None:
            query = query.filter(RevenueData.date <= end_date)
        
        # 排序和分页
        query = query.order_by(RevenueData.report_date.desc(), RevenueData.counter_id)
        results = query.offset(skip).limit(limit).all()
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询收益数据失败: {str(e)}")


@router.get("/analysis", response_model=RevenueAnalysis)
async def get_revenue_analysis(
    store_id: Optional[int] = Query(None, description="门店ID"),
    floor_id: Optional[int] = Query(None, description="楼层ID"),
    year: Optional[int] = Query(None, description="年份"),
    month: Optional[int] = Query(None, description="月份"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db: Session = Depends(get_db)
):
    """获取收益数据分析"""
    try:
        query = db.query(RevenueData)
        
        # 添加筛选条件
        if store_id is not None:
            query = query.filter(RevenueData.store_id == store_id)
        if floor_id is not None:
            query = query.filter(RevenueData.floor_id == floor_id)
        if year is not None:
            query = query.filter(RevenueData.year == year)
        if month is not None:
            query = query.filter(RevenueData.month == month)
        if start_date is not None:
            query = query.filter(RevenueData.date >= start_date)
        if end_date is not None:
            query = query.filter(RevenueData.date <= end_date)
        
        # 计算统计数据
        stats = query.with_entities(
            func.sum(RevenueData.monthly_revenue).label('total_revenue'),
            func.avg(RevenueData.monthly_revenue).label('average_revenue'),
            func.count(RevenueData.id).label('record_count')
        ).first()
        
        # 获取同期数据对比
        same_period_query = query.filter(RevenueData.same_period_revenue.isnot(None))
        same_period_stats = same_period_query.with_entities(
            func.sum(RevenueData.same_period_revenue).label('same_period_total'),
            func.avg(RevenueData.year_over_year).label('avg_yoy')
        ).first()
        
        # 获取表现最好的柜位
        top_performers = query.order_by(RevenueData.monthly_revenue.desc()).limit(10).all()
        
        # 计算增长趋势
        revenue_trend = "stable"
        if same_period_stats and same_period_stats.avg_yoy:
            if same_period_stats.avg_yoy > 5:
                revenue_trend = "up"
            elif same_period_stats.avg_yoy < -5:
                revenue_trend = "down"
        
        return RevenueAnalysis(
            total_revenue=stats.total_revenue or Decimal('0'),
            average_revenue=stats.average_revenue or Decimal('0'),
            revenue_growth=same_period_stats.avg_yoy if same_period_stats else None,
            year_over_year_growth=same_period_stats.avg_yoy if same_period_stats else None,
            top_performers=top_performers,
            revenue_trend=revenue_trend,
            period=f"{year or '全部'}-{month or '全部'}" if year else "全部"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析收益数据失败: {str(e)}")


@router.get("/time-series", response_model=List[TimeSeriesAnalysis])
async def get_time_series_analysis(
    store_id: Optional[int] = Query(None, description="门店ID"),
    floor_id: Optional[int] = Query(None, description="楼层ID"),
    year: Optional[int] = Query(None, description="年份"),
    group_by: str = Query("month", description="分组方式: month, quarter, year"),
    db: Session = Depends(get_db)
):
    """获取时间序列分析"""
    try:
        # 构建基础查询
        base_query = db.query(RevenueData)
        
        if store_id is not None:
            base_query = base_query.filter(RevenueData.store_id == store_id)
        if floor_id is not None:
            base_query = base_query.filter(RevenueData.floor_id == floor_id)
        if year is not None:
            base_query = base_query.filter(RevenueData.year == year)
        
        # 根据分组方式构建查询
        if group_by == "month":
            group_expr = func.concat(RevenueData.year, '-', func.lpad(RevenueData.month, 2, '0'))
            order_expr = [RevenueData.year, RevenueData.month]
        elif group_by == "quarter":
            group_expr = func.concat(RevenueData.year, '-Q', func.ceil(RevenueData.month / 3.0))
            order_expr = [RevenueData.year, func.ceil(RevenueData.month / 3.0)]
        elif group_by == "year":
            group_expr = RevenueData.year
            order_expr = [RevenueData.year]
        else:
            raise HTTPException(status_code=400, detail="无效的分组方式")
        
        # 执行分组查询
        results = base_query.with_entities(
            group_expr.label('period'),
            func.sum(RevenueData.monthly_revenue).label('total_revenue'),
            func.count(RevenueData.id).label('record_count'),
            func.avg(RevenueData.monthly_revenue).label('average_revenue'),
            func.avg(RevenueData.year_over_year).label('avg_yoy'),
            func.sum(RevenueData.same_period_revenue).label('same_period_revenue')
        ).group_by(group_expr).order_by(*order_expr).all()
        
        # 转换为响应模型
        time_series = []
        for result in results:
            time_series.append(TimeSeriesAnalysis(
                period=str(result.period),
                total_revenue=result.total_revenue or Decimal('0'),
                record_count=result.record_count or 0,
                average_revenue=result.average_revenue or Decimal('0'),
                growth_rate=result.avg_yoy,
                same_period_revenue=result.same_period_revenue,
                year_over_year=result.avg_yoy
            ))
        
        return time_series
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"时间序列分析失败: {str(e)}")


@router.get("/counter/{counter_id}", response_model=List[RevenueDataSchema])
async def get_counter_revenue_history(
    counter_id: int,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    limit: int = Query(100, ge=1, le=1000, description="限制记录数"),
    db: Session = Depends(get_db)
):
    """获取指定柜位的收益历史"""
    try:
        query = db.query(RevenueData).filter(RevenueData.counter_id == counter_id)
        
        if start_date is not None:
            query = query.filter(RevenueData.date >= start_date)
        if end_date is not None:
            query = query.filter(RevenueData.date <= end_date)
        
        results = query.order_by(RevenueData.report_date.desc()).limit(limit).all()
        
        if not results:
            raise HTTPException(status_code=404, detail=f"未找到柜位 {counter_id} 的收益数据")
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询柜位收益历史失败: {str(e)}")


@router.post("/", response_model=RevenueDataSchema)
async def create_revenue_data(
    revenue_data: RevenueDataCreate,
    db: Session = Depends(get_db)
):
    """创建收益数据记录"""
    try:
        # 如果提供了年月日但没有提供完整日期，自动计算
        if revenue_data.year and revenue_data.month and revenue_data.day and not revenue_data.date:
            revenue_data.date = date(revenue_data.year, revenue_data.month, revenue_data.day)
        
        # 如果提供了完整日期但没有年月日，自动提取
        if revenue_data.date and not (revenue_data.year and revenue_data.month and revenue_data.day):
            revenue_data.year = revenue_data.date.year
            revenue_data.month = revenue_data.date.month
            revenue_data.day = revenue_data.date.day
        
        db_revenue = RevenueData(**revenue_data.dict())
        db.add(db_revenue)
        db.commit()
        db.refresh(db_revenue)
        
        return db_revenue
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建收益数据失败: {str(e)}")


@router.put("/{revenue_id}", response_model=RevenueDataSchema)
async def update_revenue_data(
    revenue_id: int,
    revenue_data: RevenueDataUpdate,
    db: Session = Depends(get_db)
):
    """更新收益数据记录"""
    try:
        db_revenue = db.query(RevenueData).filter(RevenueData.id == revenue_id).first()
        if not db_revenue:
            raise HTTPException(status_code=404, detail="收益数据记录不存在")
        
        # 更新字段
        update_data = revenue_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_revenue, field, value)
        
        # 如果更新了年月日，重新计算完整日期
        if any(field in update_data for field in ['year', 'month', 'day']):
            if db_revenue.year and db_revenue.month and db_revenue.day:
                db_revenue.date = date(db_revenue.year, db_revenue.month, db_revenue.day)
        
        # 如果更新了完整日期，重新计算年月日
        if 'date' in update_data and db_revenue.date:
            db_revenue.year = db_revenue.date.year
            db_revenue.month = db_revenue.date.month
            db_revenue.day = db_revenue.date.day
        
        db.commit()
        db.refresh(db_revenue)
        
        return db_revenue
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新收益数据失败: {str(e)}")


@router.delete("/{revenue_id}")
async def delete_revenue_data(
    revenue_id: int,
    db: Session = Depends(get_db)
):
    """删除收益数据记录"""
    try:
        db_revenue = db.query(RevenueData).filter(RevenueData.id == revenue_id).first()
        if not db_revenue:
            raise HTTPException(status_code=404, detail="收益数据记录不存在")
        
        db.delete(db_revenue)
        db.commit()
        
        return {"message": "收益数据记录删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除收益数据失败: {str(e)}")










