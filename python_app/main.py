"""
百货柜位管理系统 - 主应用程序
Department Store Counter Management System - Main Application
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path
import uvicorn
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入模型和路由
from .models.database import engine, Base
from .routers import stores, counters, tenants, dashboard

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 创建FastAPI应用
app = FastAPI(
    title="百货柜位管理系统",
    description="Department Store Counter Management System",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含API路由
app.include_router(stores.router)
app.include_router(counters.router)
app.include_router(tenants.router)
app.include_router(dashboard.router)

# 静态文件服务（前端文件）
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 健康检查接口
@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "service": "百货柜位管理系统",
        "version": "1.0.0"
    }

# 根路径返回API信息
@app.get("/")
async def root():
    """根路径API信息"""
    return {
        "message": "百货柜位管理系统 API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "stores": ["常州购物中心", "常州新世纪"],
        "features": [
            "门店管理",
            "柜位管理",
            "租户管理",
            "合同管理",
            "财务管理",
            "数据统计"
        ]
    }

# 初始化数据
@app.on_event("startup")
async def startup_event():
    """应用启动时执行的初始化操作"""
    print("🏢 百货柜位管理系统启动中...")
    
    # 这里可以添加初始化数据的逻辑
    from .models.database import SessionLocal
    from .models.models import Store
    
    db = SessionLocal()
    try:
        # 检查是否需要创建默认门店
        existing_stores = db.query(Store).count()
        if existing_stores == 0:
            # 创建默认门店
            default_stores = [
                Store(
                    store_name="常州购物中心",
                    store_code="CZ001",
                    address="江苏省常州市新北区中央商务区",
                    manager_name="张经理",
                    contact_phone="0519-12345678"
                ),
                Store(
                    store_name="常州新世纪",
                    store_code="CZ002", 
                    address="江苏省常州市天宁区新世纪商业广场",
                    manager_name="李经理",
                    contact_phone="0519-87654321"
                )
            ]
            
            for store in default_stores:
                db.add(store)
            db.commit()
            print("✅ 默认门店数据创建完成")
            
    except Exception as e:
        print(f"❌ 初始化数据时出错: {e}")
    finally:
        db.close()
        
    print("🎉 百货柜位管理系统启动完成!")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True if os.getenv("DEBUG", "False").lower() == "true" else False
    )