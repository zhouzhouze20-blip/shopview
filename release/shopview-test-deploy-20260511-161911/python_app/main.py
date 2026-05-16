"""
百货柜位管理系统 - 主应用程序
Department Store Counter Management System - Main Application
"""
from fastapi import FastAPI, Request, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path
import uvicorn
import os
import shutil
from dotenv import load_dotenv
from datetime import datetime
import uuid

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 加载环境变量
load_dotenv()

# 导入模型和路由
from models.database import engine, Base
from routers import (
    auth,
    erp_settlements,
    stores,
    counters,
    counter_groups,
    tenants,
    dashboard,
    polygon_counters,
    geometry_management,
    floors,
    base_maps,
    unit_map_versions,
    geo_elements,
    business_units,
    floor_area_report,
    contracts,
    sales,
    manaframe,
    suppliers,
    system_management,
    decorations,
)

# 创建FastAPI应用
app = FastAPI(
    title="百货柜位管理系统",
    description="Department Store Counter Management System",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# 配置CORS（本地 5173 直连 8000 时需放行；credentials=True 时不能使用 "*"）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://192.168.98.81:5173",
        "http://192.168.98.81:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 包含API路由
app.include_router(stores.router)
app.include_router(auth.router)
app.include_router(erp_settlements.router)
app.include_router(counters.router)
app.include_router(counter_groups.router)
app.include_router(tenants.router)
app.include_router(dashboard.router)
app.include_router(polygon_counters.router)
app.include_router(geometry_management.router)
app.include_router(floors.router)
app.include_router(base_maps.router)
app.include_router(unit_map_versions.router)
app.include_router(geo_elements.router)
app.include_router(business_units.router)
app.include_router(floor_area_report.router)
app.include_router(contracts.router)
app.include_router(sales.router)
app.include_router(manaframe.router)
app.include_router(suppliers.router)
app.include_router(system_management.router)
app.include_router(decorations.router)


@app.on_event("startup")
async def startup_event():
    from routers.auth import ensure_default_admin
    from routers.authz import ensure_core_permissions

    ensure_core_permissions()
    ensure_default_admin()
    _repair_base_map_upload_references(uploads_dir)

# 静态文件服务（前端文件）
# 尝试多个可能的静态文件路径
possible_static_dirs = [
    Path("/app/static"),  # Docker容器（优先）
    PROJECT_ROOT / "static",  # 本地开发
    Path("static"),  # 相对路径
]

static_dir = None
for dir_path in possible_static_dirs:
    if dir_path.exists():
        static_dir = dir_path
        print(f"找到静态文件目录: {static_dir}")
        # 列出目录内容用于调试
        try:
            files = list(dir_path.iterdir())
            print(f"静态目录内容: {[f.name for f in files]}")
        except Exception as e:
            print(f"无法列出静态目录内容: {e}")
        break

if static_dir:
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    print(f"静态文件服务已挂载: /static -> {static_dir}")
    
    # 添加一个调试接口来检查静态文件
    @app.get("/api/debug/static")
    async def debug_static():
        """调试静态文件"""
        try:
            files = list(static_dir.iterdir())
            return {
                "static_dir": str(static_dir),
                "files": [f.name for f in files if f.is_file()],
                "directories": [f.name for f in files if f.is_dir()]
            }
        except Exception as e:
            return {"error": str(e), "static_dir": str(static_dir)}
else:
    print("警告: 未找到静态文件目录，前端资源可能无法加载")

def _upload_dir_candidates():
    configured_path = (os.getenv("UPLOAD_PATH") or "").strip()
    candidates = []

    if configured_path:
        configured_dir = Path(configured_path).expanduser()
        if not configured_dir.is_absolute():
            configured_dir = PROJECT_ROOT / configured_dir
        candidates.append(configured_dir)

    candidates.append(PROJECT_ROOT / "uploads")

    unique_candidates = []
    seen = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique_candidates.append(candidate)
    return unique_candidates


def _legacy_upload_dir_candidates():
    return [
        PROJECT_ROOT / "python_app" / "uploads",
        Path("/tmp/shopview-uploads"),
    ]


def _sync_legacy_uploads(target_dir: Path) -> None:
    """将历史上传目录中的文件补齐到固定目录，避免重部署后资源失联。"""
    for legacy_dir in _legacy_upload_dir_candidates():
        if legacy_dir == target_dir or not legacy_dir.exists() or not legacy_dir.is_dir():
            continue

        copied = 0
        for child in legacy_dir.iterdir():
            if not child.is_file():
                continue
            target_file = target_dir / child.name
            if target_file.exists():
                continue
            shutil.copy2(child, target_file)
            copied += 1

        if copied:
            print(f"已从历史上传目录补齐文件: {legacy_dir} -> {target_dir} ({copied} 个)")


def _candidate_upload_dirs(target_dir: Path) -> list[Path]:
    dirs = [target_dir, *_legacy_upload_dir_candidates()]
    unique_dirs = []
    seen = set()
    for candidate in dirs:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique_dirs.append(candidate)
    return unique_dirs


def _original_upload_name(filename: str) -> str:
    """返回去掉 UUID 前缀后的原始上传文件名。"""
    parts = filename.split("_", 1)
    if len(parts) == 2 and len(parts[0]) >= 32:
        return parts[1]
    return filename


def _repair_base_map_upload_references(target_dir: Path) -> None:
    """
    修复 base_maps 指向的缺失上传文件。

    服务器换版本时，如果数据库仍指向旧 UUID 文件名，而持久化目录里只有同一原始
    SVG 的其它 UUID 版本，则复制一份到数据库期望的文件名，恢复底图访问。
    """
    try:
        from models.database import SessionLocal
        from sqlalchemy import text
    except Exception as exc:
        print(f"跳过底图上传文件修复，数据库模块不可用: {exc}")
        return

    db = SessionLocal()
    try:
        rows = db.execute(
            text(
                """
                SELECT id, file_url
                FROM base_maps
                WHERE file_url LIKE '/uploads/%'
                """
            )
        ).fetchall()

        repaired = 0
        for row in rows:
            filename = Path(row.file_url).name
            if not filename:
                continue

            expected_file = target_dir / filename
            if expected_file.exists():
                continue

            original_name = _original_upload_name(filename)
            source_file = None
            for candidate_dir in _candidate_upload_dirs(target_dir):
                if not candidate_dir.exists() or not candidate_dir.is_dir():
                    continue

                exact_candidate = candidate_dir / filename
                if exact_candidate.exists():
                    source_file = exact_candidate
                    break

                matches = sorted(
                    (
                        child
                        for child in candidate_dir.iterdir()
                        if child.is_file() and _original_upload_name(child.name) == original_name
                    ),
                    key=lambda child: child.stat().st_mtime,
                    reverse=True,
                )
                if matches:
                    source_file = matches[0]
                    break

            if not source_file:
                print(f"底图文件缺失且未找到同名历史文件: base_map_id={row.id}, file_url={row.file_url}")
                continue

            shutil.copy2(source_file, expected_file)
            repaired += 1
            print(f"已修复底图上传文件: {source_file} -> {expected_file}")

        if repaired:
            print(f"底图上传文件修复完成: {repaired} 个")
    except Exception as exc:
        print(f"底图上传文件修复失败: {exc}")
    finally:
        db.close()


def resolve_upload_dir() -> Path:
    """解析固定上传目录，默认使用项目根 uploads。"""
    errors = []
    candidates = _upload_dir_candidates()

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            if not os.access(candidate, os.W_OK | os.X_OK):
                raise PermissionError(f"目录不可写: {candidate}")
            _sync_legacy_uploads(candidate)
            print(f"上传目录已启用: {candidate}")
            return candidate
        except Exception as exc:
            errors.append(f"{candidate}: {exc}")
            print(f"上传目录不可用，尝试下一个: {candidate} ({exc})")

    raise RuntimeError("未找到可写的上传目录: " + " | ".join(errors))


# 上传文件服务
uploads_dir = resolve_upload_dir()
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

# 添加重定向来处理前端资源路径问题
@app.get("/assets/{file_path:path}")
async def redirect_assets(file_path: str):
    """重定向 /assets/ 到 /static/assets/"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"/static/assets/{file_path}", status_code=301)

@app.get("/favicon.ico")
async def favicon():
    """处理favicon请求"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/favicon.ico", status_code=301)

# 健康检查接口
@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    try:
        # 测试数据库连接
        from models.database import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        try:
            # 执行简单查询测试连接
            result = db.execute(text("SELECT 1"))
            db_status = "connected"
            db_message = "数据库连接正常"
        except Exception as e:
            db_status = "error"
            db_message = f"数据库连接失败: {str(e)}"
        finally:
            db.close()
        
        return {
            "status": "healthy" if db_status == "connected" else "degraded",
            "service": "百货柜位管理系统",
            "version": "1.0.0",
            "database": {
                "status": db_status,
                "message": db_message
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "百货柜位管理系统",
            "version": "1.0.0",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# 数据库连接测试接口
@app.get("/api/test-db")
async def test_database():
    """测试数据库连接接口"""
    try:
        from models.database import SessionLocal, engine
        from models.models import Store
        
        # 测试数据库引擎连接
        from sqlalchemy import text
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version()"))
            db_version = result.fetchone()[0]
        
        # 测试ORM查询
        db = SessionLocal()
        try:
            store_count = db.query(Store).count()
            stores = db.query(Store).limit(5).all()
            
            return {
                "status": "success",
                "message": "数据库连接测试成功",
                "database_info": {
                    "version": db_version,
                    "store_count": store_count,
                    "sample_stores": [
                        {
                            "id": store.store_id,
                            "name": store.store_name,
                            "code": store.store_code
                        } for store in stores
                    ]
                },
                "timestamp": datetime.now().isoformat()
            }
        finally:
            db.close()
            
    except Exception as e:
        return {
            "status": "error",
            "message": "数据库连接测试失败",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# 文件上传接口
@app.post("/api/objects/upload")
async def upload_file(request: Request):
    """获取文件上传URL"""
    try:
        # 生成一个唯一的文件名
        file_id = str(uuid.uuid4())
        # 这里返回一个模拟的上传URL，实际项目中应该配置真实的云存储
        upload_url = str(request.url_for("handle_file_upload", file_id=file_id))
        
        return {
            "uploadURL": upload_url,
            "fileId": file_id
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取上传地址失败: {str(e)}"
        )

@app.put("/api/objects/upload/{file_id}", name="handle_file_upload")
async def handle_file_upload(file_id: str, file: UploadFile = File(...)):
    """处理文件上传"""
    try:
        # 保存文件
        original_name = Path(file.filename or "upload.bin").name
        file_path = uploads_dir / f"{file_id}_{original_name}"
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 返回文件URL
        file_url = f"/uploads/{file_id}_{original_name}"
        return {"message": "文件上传成功", "fileUrl": file_url}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件上传失败: {str(e)}"
        )

def load_frontend_index() -> str:
    """加载前端入口文件。"""
    possible_paths = [
        Path("/app/static/index.html"),  # Docker容器（优先）
        Path(__file__).parent.parent / "static" / "index.html",  # 本地开发
        Path("static/index.html"),  # 相对路径
    ]

    for index_file in possible_paths:
        if index_file.exists():
            try:
                return index_file.read_text(encoding="utf-8")
            except Exception as e:
                print(f"读取前端文件失败 {index_file}: {e}")

    return ""

# 根路径返回前端页面
@app.get("/", response_class=HTMLResponse)
async def root():
    """根路径返回前端页面"""
    index_html = load_frontend_index()
    if index_html:
        return index_html

    # 如果所有前端文件都不存在，返回功能完整的HTML页面
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>百货柜位管理系统</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }
            .container { 
                max-width: 1200px; 
                margin: 0 auto; 
                padding: 20px;
            }
            .header { 
                text-align: center; 
                margin-bottom: 40px; 
                background: white;
                padding: 40px;
                border-radius: 16px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }
            .header h1 { 
                font-size: 2.5rem; 
                color: #2d3748; 
                margin-bottom: 10px;
            }
            .header p { 
                color: #718096; 
                font-size: 1.1rem;
            }
            .grid { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
                gap: 20px; 
                margin: 20px 0; 
            }
            .card { 
                background: white; 
                padding: 24px; 
                border-radius: 12px; 
                box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                transition: transform 0.2s;
            }
            .card:hover { 
                transform: translateY(-2px); 
            }
            .card h3 { 
                color: #2d3748; 
                margin-bottom: 16px; 
                font-size: 1.25rem;
            }
            .links { 
                display: flex; 
                flex-wrap: wrap; 
                gap: 12px; 
            }
            .links a { 
                display: inline-block; 
                padding: 12px 24px; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; 
                text-decoration: none; 
                border-radius: 8px; 
                font-weight: 500;
                transition: all 0.2s;
            }
            .links a:hover { 
                transform: translateY(-1px);
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            }
            .feature-list { 
                list-style: none; 
            }
            .feature-list li { 
                padding: 8px 0; 
                border-bottom: 1px solid #e2e8f0;
                position: relative;
                padding-left: 20px;
            }
            .feature-list li:before { 
                content: "✓"; 
                position: absolute; 
                left: 0; 
                color: #48bb78; 
                font-weight: bold;
            }
            .status { 
                display: inline-block; 
                padding: 4px 12px; 
                background: #48bb78; 
                color: white; 
                border-radius: 20px; 
                font-size: 0.875rem;
                font-weight: 500;
            }
            .api-info { 
                background: #f7fafc; 
                border-left: 4px solid #667eea;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏢 百货柜位管理系统</h1>
                <p>Department Store Counter Management System</p>
                <div style="margin-top: 20px;">
                    <span class="status">运行中</span>
                </div>
            </div>
            
            <div class="grid">
                <div class="card api-info">
                    <h3>📊 系统状态</h3>
                    <p><strong>版本:</strong> 1.0.0</p>
                    <p><strong>状态:</strong> <span class="status">运行中</span></p>
                    <p><strong>门店:</strong> 常州购物中心, 常州新世纪</p>
                    <p><strong>数据库:</strong> 已连接</p>
                </div>
                
                <div class="card">
                    <h3>🔗 快速链接</h3>
                    <div class="links">
                        <a href="/api/docs" target="_blank">API 文档</a>
                        <a href="/api/health" target="_blank">健康检查</a>
                        <a href="/api/stores" target="_blank">门店列表</a>
                        <a href="/api/counters" target="_blank">柜位列表</a>
                    </div>
                </div>
                
                <div class="card">
                    <h3>⚙️ 功能模块</h3>
                    <ul class="feature-list">
                        <li>门店管理</li>
                        <li>柜位管理</li>
                        <li>租户管理</li>
                        <li>合同管理</li>
                        <li>财务管理</li>
                        <li>数据统计</li>
                    </ul>
                </div>
                
            </div>
        </div>
    </body>
    </html>
    """

# 调试接口 - 检查文件结构
@app.get("/api/debug/files")
async def debug_files():
    """调试接口 - 检查文件结构"""
    import os
    result = {
        "current_working_directory": os.getcwd(),
        "python_app_path": str(Path(__file__).parent),
        "static_directories": {},
        "files_in_root": []
    }
    
    # 检查各个可能的静态目录
    possible_dirs = [
        ("/app/static", Path("/app/static")),
        ("../static", Path(__file__).parent.parent / "static"),
        ("static", Path("static")),
    ]
    
    for name, path in possible_dirs:
        if path.exists():
            try:
                files = list(path.iterdir())
                result["static_directories"][name] = {
                    "exists": True,
                    "path": str(path),
                    "files": [f.name for f in files if f.is_file()],
                    "directories": [f.name for f in files if f.is_dir()]
                }
            except Exception as e:
                result["static_directories"][name] = {
                    "exists": True,
                    "path": str(path),
                    "error": str(e)
                }
        else:
            result["static_directories"][name] = {
                "exists": False,
                "path": str(path)
            }
    
    # 检查根目录文件
    try:
        root_files = list(Path("/app").iterdir()) if Path("/app").exists() else []
        result["files_in_root"] = [f.name for f in root_files]
    except Exception as e:
        result["files_in_root"] = f"Error: {e}"
    
    return result

# API信息接口
@app.get("/api")
async def api_info():
    """API信息接口"""
    return {
        "message": "百货柜位管理系统 API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "debug": "/api/debug/files",
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

@app.get("/{full_path:path}", response_class=HTMLResponse)
async def spa_fallback(full_path: str):
    """为前端单页应用提供路由回退。"""
    excluded_prefixes = ("api/", "static/", "uploads/", "assets/")
    if full_path in {"favicon.ico", ""} or full_path.startswith(excluded_prefixes):
        raise HTTPException(status_code=404, detail="Not Found")

    index_html = load_frontend_index()
    if index_html:
        return index_html

    raise HTTPException(status_code=404, detail="Frontend not built")

# 初始化数据 - 暂时注释掉，避免关系配置错误
# @app.on_event("startup")
# async def startup_event():
#     """应用启动时执行的初始化操作"""
#     print("🏢 百货柜位管理系统启动中...")
#     
#     # 这里可以添加初始化数据的逻辑
#     from models.database import SessionLocal
#     from models.models import Store
#     
#     db = SessionLocal()
#     try:
#         # 检查是否需要创建默认门店
#         existing_stores = db.query(Store).count()
#         if existing_stores == 0:
#             # 创建默认门店
#             default_stores = [
#                 Store(
#                     store_name="常州购物中心",
#                     store_code="CZ001",
#                     address="江苏省常州市新北区中央商务区",
#                     manager_name="张经理",
#                     contact_phone="0519-12345678"
#                 ),
#                 Store(
#                     store_name="常州新世纪",
#                     store_code="CZ002", 
#                     address="江苏省常州市天宁区新世纪商业广场",
#                     manager_name="李经理",
#                     contact_phone="0519-87654321"
#                 )
#             ]
#             
#             for store in default_stores:
#                 db.add(store)
#             db.commit()
#             print("✅ 默认门店数据创建完成")
#             
#     except Exception as e:
#         print(f"❌ 初始化数据时出错: {e}")
#     finally:
#         db.close()
#     
#     print("🎉 百货柜位管理系统启动完成!")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True if os.getenv("DEBUG", "False").lower() == "true" else False
    )
