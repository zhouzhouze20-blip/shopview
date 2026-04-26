#!/usr/bin/env python3
"""
更新 revenue_data 表，添加与新增表一致的测试数据
主要针对 store_id=1, floor_id=3 的柜位
"""

from models.database import SessionLocal
from models.models import Counter, RevenueData, SalesProfit, Fee
from datetime import date, datetime, timedelta
from decimal import Decimal
import random

def update_revenue_data():
    db = SessionLocal()
    try:
        # 获取 store_id=1, floor_id=3 的柜位
        counters = db.query(Counter).filter(Counter.store_id == 1, Counter.floor_id == 3).all()
        print(f"找到 {len(counters)} 个柜位")
        
        if not counters:
            print("没有找到符合条件的柜位")
            return
        
        # 为每个柜位更新 revenue_data
        for counter in counters[:10]:  # 只为前10个柜位更新数据
            print(f"更新柜位 {counter.counter_code} 的 revenue_data...")
            
            # 获取该柜位的销售毛利和收费数据
            sales_profits = db.query(SalesProfit).filter(SalesProfit.counter_id == counter.counter_id).all()
            fees = db.query(Fee).filter(Fee.counter_id == counter.counter_id).all()
            
            # 按日期分组计算收益
            revenue_by_date = {}
            
            # 处理销售毛利数据
            for sales in sales_profits:
                date_key = sales.order_date
                if date_key not in revenue_by_date:
                    revenue_by_date[date_key] = {'sales_profit': Decimal('0'), 'fees': Decimal('0')}
                revenue_by_date[date_key]['sales_profit'] += sales.gross_profit
            
            # 处理收费数据
            for fee in fees:
                date_key = fee.fee_date
                if date_key not in revenue_by_date:
                    revenue_by_date[date_key] = {'sales_profit': Decimal('0'), 'fees': Decimal('0')}
                revenue_by_date[date_key]['fees'] += fee.fee_amount
            
            # 更新或创建 revenue_data 记录
            for order_date, revenues in revenue_by_date.items():
                total_revenue = revenues['sales_profit'] + revenues['fees']
                
                # 检查是否已存在该日期的记录
                existing_revenue = db.query(RevenueData).filter(
                    RevenueData.counter_id == counter.counter_id,
                    RevenueData.date == order_date
                ).first()
                
                if existing_revenue:
                    # 更新现有记录
                    existing_revenue.daily_revenue = total_revenue
                    existing_revenue.monthly_revenue = total_revenue * Decimal('30')  # 估算月收益
                    existing_revenue.updated_at = datetime.now()
                else:
                    # 创建新记录
                    new_revenue = RevenueData(
                        counter_id=counter.counter_id,
                        counter_code=counter.counter_code,
                        counter_name=counter.counter_name,
                        store_id=counter.store_id,
                        store_name=counter.store.store_name if counter.store else "测试门店",
                        floor_id=counter.floor_id,
                        floor_name=counter.floor.floor_name if counter.floor else f"楼层{counter.floor_id}",
                        area=counter.area or Decimal('0'),
                        x=counter.position_x or 0,
                        y=counter.position_y or 0,
                        width=counter.width or 0,
                        height=counter.height or 0,
                        monthly_revenue=total_revenue * Decimal('30'),  # 估算月收益
                        daily_revenue=total_revenue,
                        revenue_per_sqm=total_revenue / (counter.area or Decimal('1')),
                        revenue_trend="stable",
                        revenue_change_percent=Decimal('0'),
                        report_date=order_date,
                        status="active",
                        tenant_name="测试租户",
                        brand_name="测试品牌",
                        year=order_date.year,
                        month=order_date.month,
                        day=order_date.day,
                        date=order_date,
                        same_period_sales=total_revenue * Decimal('0.9'),  # 模拟去年同期数据
                        same_period_date=order_date.replace(year=order_date.year - 1),
                        same_period_revenue=total_revenue * Decimal('0.9'),
                        year_over_year=Decimal('10.0')  # 模拟同比增长10%
                    )
                    db.add(new_revenue)
        
        # 提交所有更改
        db.commit()
        print(f"\\nrevenue_data 更新完成！")
        
        # 验证更新结果
        updated_count = db.query(RevenueData).filter(
            RevenueData.store_id == 1, 
            RevenueData.floor_id == 3
        ).count()
        print(f"store_id=1, floor_id=3 的 revenue_data 记录数: {updated_count}")
        
        # 显示一些示例数据
        sample_revenue = db.query(RevenueData).filter(
            RevenueData.store_id == 1, 
            RevenueData.floor_id == 3
        ).limit(3).all()
        
        print("\\n=== revenue_data 示例数据 ===")
        for revenue in sample_revenue:
            print(f"柜位: {revenue.counter_code}, 日期: {revenue.date}, 日收益: {revenue.daily_revenue}, 月收益: {revenue.monthly_revenue}")
        
    except Exception as e:
        print(f"更新 revenue_data 时出错: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_revenue_data()
