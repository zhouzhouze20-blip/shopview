"""
百货柜位管理系统 - 仪表板API
Department Store Counter Management System - Dashboard API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.database import get_db
from models.models import Store, Counter, Tenant, Contract, Bill
from schemas.schemas import DashboardStats, StoreStats
from typing import List
from decimal import Decimal

router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"]
)


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """获取仪表板统计数据"""
    
    # 统计门店数量
    total_stores = db.query(Store).filter(Store.is_active == True).count()
    
    # 统计柜位数量
    total_counters = db.query(Counter).filter(Counter.is_active == True).count()
    occupied_counters = db.query(Counter).filter(
        Counter.is_active == True,
        Counter.status == "occupied"
    ).count()
    vacant_counters = total_counters - occupied_counters
    
    # 统计租户数量
    total_tenants = db.query(Tenant).filter(Tenant.is_active == True).count()
    
    # 统计活跃合同数量
    active_contracts = db.query(Contract).filter(Contract.status == "active").count()
    
    # 统计月度收入
    monthly_revenue = db.query(func.sum(Contract.monthly_rent)).filter(
        Contract.status == "active"
    ).scalar() or Decimal("0")
    
    # 统计逾期账单
    overdue_bills = db.query(Bill).filter(Bill.payment_status == "overdue").count()
    
    return DashboardStats(
        total_stores=total_stores,
        total_counters=total_counters,
        occupied_counters=occupied_counters,
        vacant_counters=vacant_counters,
        total_tenants=total_tenants,
        active_contracts=active_contracts,
        monthly_revenue=monthly_revenue,
        overdue_bills=overdue_bills
    )


@router.get("/stores-stats", response_model=List[StoreStats])
async def get_stores_stats(db: Session = Depends(get_db)):
    """获取各门店统计数据"""
    stores = db.query(Store).filter(Store.is_active == True).all()
    stats = []
    
    for store in stores:
        # 统计该门店的柜位信息
        total_counters = db.query(Counter).filter(
            Counter.store_id == store.store_id,
            Counter.is_active == True
        ).count()
        
        occupied_counters = db.query(Counter).filter(
            Counter.store_id == store.store_id,
            Counter.is_active == True,
            Counter.status == "occupied"
        ).count()
        
        vacancy_rate = ((total_counters - occupied_counters) / total_counters * 100) if total_counters > 0 else 0
        
        # 统计该门店的月收入
        monthly_revenue = db.query(func.sum(Contract.monthly_rent)).join(
            Counter, Contract.counter_id == Counter.counter_id
        ).filter(
            Counter.store_id == store.store_id,
            Contract.status == "active"
        ).scalar() or Decimal("0")
        
        stats.append(StoreStats(
            store_id=store.store_id,
            store_name=store.store_name,
            total_counters=total_counters,
            occupied_counters=occupied_counters,
            vacancy_rate=round(vacancy_rate, 2),
            monthly_revenue=monthly_revenue
        ))
    
    return stats