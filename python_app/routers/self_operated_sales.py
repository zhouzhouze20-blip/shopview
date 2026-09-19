"""Independent scope for self-operated clothing and bakery sales."""
from datetime import date
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, File, Form, UploadFile
from starlette.concurrency import run_in_threadpool
from tempfile import TemporaryDirectory
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile, BadZipFile
from sqlalchemy.orm import Session
from sqlalchemy import inspect, select
from models.database import get_db
from models.models import User
from routers.auth import get_current_user
from routers.authz import require_permission, load_data_scope, scope_allows_business
from services.self_operated_sales import RESOURCE_CODE, STORE_CODE, SECTIONS, read_summary, read_details, read_tickets, publish_export, imports
from services.fungkids_retail_import import parse_export
from services.self_operated_sales import read_discount_settlement

router = APIRouter(prefix="/api/self-operated-sales", tags=["self-operated-sales"])


def allowed_sections(db, user):
    require_permission(db, user, "sales.view")
    scope = load_data_scope(db, user, RESOURCE_CODE, "view")
    return [code for code in SECTIONS if scope_allows_business(
        scope, store_id=STORE_CODE, department_code=code)]


def validate_dates(start, end):
    if start > end or (end-start).days > 1095:
        raise HTTPException(422, "日期范围无效或超过三年")


def require_tables(db):
    inspector = inspect(db.get_bind())
    if not all(inspector.has_table(name) for name in (
        "self_operated_sales_imports", "self_operated_sales_lines", "self_operated_sales_coverage")):
        raise HTTPException(503, "自营公司数据表尚未初始化")


@router.get("/summary")
def summary(start_date: date, end_date: date, db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)):
    validate_dates(start_date, end_date)
    allowed = allowed_sections(db, current_user)
    if not allowed:
        return {"store_code": STORE_CODE, "store_name": "自营公司", "sections": [], "totals": {}}
    require_tables(db)
    return read_summary(db, allowed, start_date, end_date)


@router.get("/details")
def details(section: Literal["CLOTHING", "BAKERY"], start_date: date, end_date: date,
            offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
            db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    validate_dates(start_date, end_date)
    if section not in allowed_sections(db, current_user):
        raise HTTPException(403, "无该自营板块的数据权限")
    require_tables(db)
    return read_details(db, section, start_date, end_date, offset, limit)


@router.get("/discount-settlement")
def discount_settlement(start_date: date, end_date: date, channel: str | None = None,
                        db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    validate_dates(start_date, end_date)
    if "CLOTHING" not in allowed_sections(db, current_user):
        raise HTTPException(403, "无自营服装的数据权限")
    require_tables(db)
    return read_discount_settlement(db, start_date, end_date, channel)


def require_import_access(db, user):
    require_permission(db, user, "sales.self_operated.import")
    if "CLOTHING" not in allowed_sections(db, user):
        raise HTTPException(403, "无自营服装数据范围，请单独配置自营公司权限")


def process_upload(engine, content, filename, start, end, commit, expected_sha256, actor):
    try:
        with ZipFile(BytesIO(content)) as archive:
            if sum(info.file_size for info in archive.infolist()) > 100 * 1024 * 1024:
                raise ValueError("文件解压后超过100MB，请按更短日期区间导出")
        with TemporaryDirectory(prefix="self-operated-upload-") as directory:
            path = Path(directory) / "report.xlsx"
            path.write_bytes(content)
            parsed = parse_export(path, start=start, end=end)
            if not parsed.lines:
                raise ValueError("空报表不能覆盖已有数据")
            if commit:
                if not expected_sha256 or expected_sha256 != parsed.sha256:
                    raise ValueError("文件与预览不一致，请重新校验")
                result = publish_export(engine, path, start=start, end=end,
                                        source_file=filename, imported_by=actor)
                return {"status": "imported", **result}
            return {"status": "preview", "sha256": parsed.sha256, **parsed.summary()}
    except (ValueError, BadZipFile, KeyError) as exc:
        raise HTTPException(422, f"报表校验失败：{exc}") from None


@router.post("/upload")
async def upload(file: UploadFile = File(...), start_date: date = Form(...), end_date: date = Form(...),
                 commit: bool = Form(False), expected_sha256: str = Form(""),
                 db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_import_access(db, current_user)
    validate_dates(start_date, end_date)
    require_tables(db)
    filename = Path((file.filename or "").replace("\\", "/")).name
    if not filename.lower().endswith(".xlsx") or len(filename) > 255:
        raise HTTPException(422, "请选择名称不超过255字符的.xlsx报表")
    content = await file.read(15 * 1024 * 1024 + 1)
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(413, "文件超过15MB，请按更短日期区间导出")
    return await run_in_threadpool(process_upload, db.get_bind(), content, filename,
        start_date, end_date, commit, expected_sha256, current_user.username)


@router.get("/imports")
def import_history(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_import_access(db, current_user)
    require_tables(db)
    result = db.execute(select(imports).where(imports.c.section == "CLOTHING")
                        .order_by(imports.c.id.desc()).limit(30)).mappings().all()
    return [dict(row) for row in result]


@router.get("/tickets")
def tickets(section: Literal["CLOTHING", "BAKERY"], channel: str, start_date: date, end_date: date,
            offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=50),
            db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    validate_dates(start_date, end_date)
    if section not in allowed_sections(db, current_user):
        raise HTTPException(403, "无该自营板块的数据权限")
    require_tables(db)
    return read_tickets(db, section, channel, start_date, end_date, offset, limit)
