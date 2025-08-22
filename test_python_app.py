#!/usr/bin/env python3
"""
百货柜位管理系统 Python版本测试启动器
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 创建简化版测试应用
app = FastAPI(
    title="百货柜位管理系统",
    description="Department Store Counter Management System - Test Version",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "百货柜位管理系统 API (Python版)",
        "version": "1.0.0",
        "status": "running",
        "stores": [
            {"id": 1, "name": "常州购物中心", "code": "CZ001"},
            {"id": 2, "name": "常州新世纪", "code": "CZ002"}
        ],
        "features": [
            "门店管理",
            "柜位管理", 
            "租户管理",
            "合同管理",
            "财务管理"
        ]
    }

@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "百货柜位管理系统",
        "version": "1.0.0",
        "python": "3.11+"
    }

@app.get("/api/stores")
async def get_stores():
    """获取门店列表"""
    return [
        {
            "store_id": 1,
            "store_name": "常州购物中心",
            "store_code": "CZ001",
            "address": "江苏省常州市新北区中央商务区",
            "manager_name": "张经理",
            "contact_phone": "0519-12345678",
            "is_active": True
        },
        {
            "store_id": 2,
            "store_name": "常州新世纪",
            "store_code": "CZ002",
            "address": "江苏省常州市天宁区新世纪商业广场", 
            "manager_name": "李经理",
            "contact_phone": "0519-87654321",
            "is_active": True
        }
    ]

@app.get("/api/tenants")
async def get_tenants():
    """获取租户列表"""
    return [
        {
            "tenant_id": 1,
            "tenant_code": "T001",
            "company_name": "科技世界有限公司",
            "legal_representative": "张三",
            "contact_person": "李四",
            "contact_phone": "13800138001",
            "contact_email": "contact@techworld.com",
            "business_category": "电子产品",
            "is_active": True
        },
        {
            "tenant_id": 2,
            "tenant_code": "T002",
            "company_name": "时尚佳人服饰",
            "legal_representative": "王五",
            "contact_person": "赵六",
            "contact_phone": "13800138002",
            "contact_email": "info@styleplus.com",
            "business_category": "服装",
            "is_active": True
        }
    ]

@app.get("/api/counters")
async def get_counters():
    """获取柜位列表"""
    return [
        {
            "counter_id": 1,
            "store_id": 1,
            "counter_code": "A001",
            "counter_name": "一楼电子产品区A001",
            "area": 50.0,
            "status": "occupied",
            "monthly_rent": 8000.00,
            "is_active": True
        },
        {
            "counter_id": 2,
            "store_id": 1,
            "counter_code": "A002",
            "counter_name": "一楼服装区A002",
            "area": 60.0,
            "status": "occupied", 
            "monthly_rent": 9000.00,
            "is_active": True
        },
        {
            "counter_id": 3,
            "store_id": 2,
            "counter_code": "B001",
            "counter_name": "二楼美妆区B001",
            "area": 40.0,
            "status": "vacant",
            "monthly_rent": 7000.00,
            "is_active": True
        }
    ]

@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    """获取仪表板统计数据"""
    return {
        "total_stores": 2,
        "total_counters": 24,
        "occupied_counters": 20,
        "vacant_counters": 4,
        "total_tenants": 18,
        "active_contracts": 20,
        "monthly_revenue": 168000.00,
        "overdue_bills": 3
    }

if __name__ == "__main__":
    print("🏢 启动百货柜位管理系统 (Python版本)")
    print("📍 访问地址:")
    print("   - API文档: http://localhost:8001/docs")
    print("   - 主页: http://localhost:8001/")
    print("   - 健康检查: http://localhost:8001/api/health")
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8001)