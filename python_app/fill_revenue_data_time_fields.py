#!/usr/bin/env python3
"""
填充revenue_data表的时间分析字段
"""
from models.database import get_db
from sqlalchemy import text
from datetime import datetime, date
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fill_time_fields():
    """填充时间分析字段"""
    db = next(get_db())
    
    try:
        logger.info("开始填充revenue_data表的时间分析字段...")
        
        # 1. 填充年月日字段（从report_date提取）
        logger.info("1. 填充年月日字段...")
        update_query = """
        UPDATE revenue_data 
        SET 
            year = EXTRACT(YEAR FROM report_date),
            month = EXTRACT(MONTH FROM report_date),
            day = EXTRACT(DAY FROM report_date),
            date = report_date
        WHERE report_date IS NOT NULL
        """
        result = db.execute(text(update_query))
        db.commit()
        logger.info(f"更新了 {result.rowcount} 条记录的年月日字段")
        
        # 2. 为每个柜位计算同期数据（假设同期是去年同月同日）
        logger.info("2. 计算同期数据...")
        
        # 获取所有有数据的记录
        select_query = """
        SELECT counter_id, report_date, monthly_revenue 
        FROM revenue_data 
        WHERE report_date IS NOT NULL 
        ORDER BY counter_id, report_date
        """
        result = db.execute(text(select_query))
        records = result.fetchall()
        
        logger.info(f"找到 {len(records)} 条记录需要计算同期数据")
        
        # 为每条记录计算同期数据
        updated_count = 0
        for record in records:
            counter_id, report_date, monthly_revenue = record
            
            # 计算去年同期日期
            same_period_date = date(report_date.year - 1, report_date.month, report_date.day)
            
            # 查找去年同期的收益数据
            same_period_query = """
            SELECT monthly_revenue 
            FROM revenue_data 
            WHERE counter_id = :counter_id 
            AND report_date = :same_period_date
            """
            same_period_result = db.execute(text(same_period_query), {
                'counter_id': counter_id,
                'same_period_date': same_period_date
            })
            same_period_record = same_period_result.fetchone()
            
            if same_period_record:
                same_period_revenue = same_period_record[0]
                # 计算同比（百分比）
                if same_period_revenue and same_period_revenue > 0:
                    year_over_year = ((monthly_revenue - same_period_revenue) / same_period_revenue) * 100
                else:
                    year_over_year = None
            else:
                same_period_revenue = None
                year_over_year = None
            
            # 更新同期数据
            update_same_period_query = """
            UPDATE revenue_data 
            SET 
                same_period_date = :same_period_date,
                same_period_revenue = :same_period_revenue,
                year_over_year = :year_over_year
            WHERE counter_id = :counter_id 
            AND report_date = :report_date
            """
            db.execute(text(update_same_period_query), {
                'same_period_date': same_period_date,
                'same_period_revenue': same_period_revenue,
                'year_over_year': year_over_year,
                'counter_id': counter_id,
                'report_date': report_date
            })
            updated_count += 1
            
            if updated_count % 100 == 0:
                logger.info(f"已处理 {updated_count} 条记录...")
        
        db.commit()
        logger.info(f"成功更新了 {updated_count} 条记录的同期数据")
        
        # 3. 验证结果
        logger.info("3. 验证结果...")
        verify_query = """
        SELECT 
            COUNT(*) as total_records,
            COUNT(year) as year_filled,
            COUNT(month) as month_filled,
            COUNT(day) as day_filled,
            COUNT(date) as date_filled,
            COUNT(same_period_date) as same_period_date_filled,
            COUNT(same_period_revenue) as same_period_revenue_filled,
            COUNT(year_over_year) as year_over_year_filled
        FROM revenue_data
        """
        verify_result = db.execute(text(verify_query))
        stats = verify_result.fetchone()
        
        logger.info("字段填充统计:")
        logger.info(f"  总记录数: {stats[0]}")
        logger.info(f"  年份字段: {stats[1]}")
        logger.info(f"  月份字段: {stats[2]}")
        logger.info(f"  日期字段: {stats[3]}")
        logger.info(f"  完整日期字段: {stats[4]}")
        logger.info(f"  同期日期字段: {stats[5]}")
        logger.info(f"  同期收益字段: {stats[6]}")
        logger.info(f"  同比字段: {stats[7]}")
        
        # 4. 显示一些示例数据
        logger.info("4. 示例数据:")
        sample_query = """
        SELECT 
            counter_id, 
            report_date, 
            year, month, day, date,
            monthly_revenue,
            same_period_date,
            same_period_revenue,
            year_over_year
        FROM revenue_data 
        WHERE counter_id = 2199
        ORDER BY report_date DESC
        LIMIT 3
        """
        sample_result = db.execute(text(sample_query))
        sample_records = sample_result.fetchall()
        
        for record in sample_records:
            logger.info(f"  柜位 {record[0]}: {record[1]} -> 年{record[2]}月{record[3]}日{record[4]}, 收益{record[6]}, 同期{record[7]}({record[8]}), 同比{record[9]}%")
        
        logger.info("✅ 时间分析字段填充完成！")
        
    except Exception as e:
        logger.error(f"❌ 填充过程中出错: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    fill_time_fields()










