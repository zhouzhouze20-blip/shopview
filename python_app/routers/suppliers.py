from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models.database import get_db
from routers.authz import require_permission_dependency
from schemas.supplier_schemas import SupplierCreate, SupplierDetail, SupplierListItem, SupplierUpdate


router = APIRouter(
    prefix="/api/suppliers",
    tags=["suppliers"],
)


MANAGED_COLUMNS = [
    "sbid",
    "sbcname",
    "sbsname",
    "sbstatus",
    "sbflag",
    "sbregcode",
    "sbcatcode",
    "sbtaxpayer",
    "sblxr",
    "sblxfs",
    "sbtel",
    "sbemail",
    "sbtaxno",
    "sbbank",
    "sbaccntno",
    "sbaddr",
    "sbfrdb",
    "sbyjcgy",
    "grade",
    "sbnbtype",
    "sbiftt",
    "sbcomname",
    "sbcomename",
    "sbyt",
    "sbxfdx",
    "sbyxmf",
    "sbyxrent",
    "sbyxmon",
    "sbyxmj",
    "sbopendesc",
    "sbppdesc",
    "sbjfyq",
    "sbmemo",
    "sbwmid1",
    "sbwmid2",
    "sbwmid3",
    "sbwmid4",
    "sbwmid5",
    "sbjszq",
    "sbdhzq",
    "sbdbsend",
    "sblry",
    "sbljsrq",
    "sblrrq",
    "sbxgr",
    "sbxgrq",
]

LIST_COLUMNS = """
    sbid,
    sbcname,
    sbaddr,
    sbstatus,
    sbflag,
    sbcatcode,
    sbregcode,
    sbfrdb,
    sbbank,
    sbaccntno,
    sbtaxno,
    sblrrq,
    sbxgrq
"""

DETAIL_COLUMNS = """
    sbid,
    sbcname,
    sbsname,
    sbstatus,
    sbflag,
    sbregcode,
    sbcatcode,
    sbtaxpayer,
    sblxr,
    sblxfs,
    sbtel,
    sbemail,
    sbtaxno,
    sbbank,
    sbaccntno,
    sbaddr,
    sbfrdb,
    sbyjcgy,
    grade,
    sbnbtype,
    sbiftt,
    sbcomname,
    sbcomename,
    sbyt,
    sbxfdx,
    sbyxmf,
    sbyxrent,
    sbyxmon,
    sbyxmj,
    sbopendesc,
    sbppdesc,
    sbjfyq,
    sbmemo,
    sbwmid1,
    sbwmid2,
    sbwmid3,
    sbwmid4,
    sbwmid5,
    sbjszq,
    sbdhzq,
    sbdbsend,
    sblry,
    sbljsrq,
    sblrrq,
    sbxgr,
    sbxgrq
"""


def _table_exists(db: Session, table_name: str = "supplierbase") -> bool:
    return bool(db.execute(text("SELECT to_regclass(:table_name)"), {"table_name": f"public.{table_name}"}).scalar())


def _ensure_table_ready(db: Session) -> None:
    if _table_exists(db):
        return
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="supplierbase 表不存在，请重新部署后确认容器启动时已执行 Alembic 迁移。",
    )


def _fetch_one(db: Session, sql: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    result = db.execute(text(sql), params).mappings().first()
    return dict(result) if result else None


@router.get("/", response_model=List[SupplierListItem])
async def list_suppliers(
    keyword: Optional[str] = Query(None, description="编码/名称/简称/联系人搜索"),
    store_id: Optional[str] = Query(None, description="门店编码"),
    supplier_code: Optional[str] = Query(None, description="供应商编码"),
    supplier_name: Optional[str] = Query(None, description="供应商名称"),
    status_filter: Optional[str] = Query(None, alias="status", description="状态"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    _ensure_table_ready(db)

    where_clauses = ["1=1"]
    params: Dict[str, Any] = {"skip": max(skip, 0), "limit": max(1, min(limit, 500))}

    supplier_code_value = (supplier_code or "").strip()
    if supplier_code_value:
        params["supplier_code"] = f"%{supplier_code_value}%"
        where_clauses.append("sbid ILIKE :supplier_code")

    supplier_name_value = (supplier_name or "").strip()
    if supplier_name_value:
        params["supplier_name"] = f"%{supplier_name_value}%"
        where_clauses.append("sbcname ILIKE :supplier_name")

    search_value = (keyword or "").strip()
    if search_value and not supplier_code_value and not supplier_name_value:
        params["keyword"] = f"%{search_value}%"
        where_clauses.append(
            "(sbid ILIKE :keyword OR sbcname ILIKE :keyword OR COALESCE(sbsname, '') ILIKE :keyword OR COALESCE(sblxr, '') ILIKE :keyword)"
        )

    status_value = (status_filter or "").strip()
    if status_value:
        params["status_filter"] = status_value
        where_clauses.append("sbstatus = :status_filter")

    store_value = (store_id or "").strip()
    if store_value and _table_exists(db, "contmain") and _table_exists(db, "contmanaframe"):
        params["store_id"] = store_value
        where_clauses.append(
            """
            EXISTS (
              SELECT 1
              FROM contmain cm
              LEFT JOIN contmanaframe cmf
                ON upper(trim(COALESCE(cmf.cmfcontno, ''))) = upper(trim(COALESCE(cm.cmcontno, '')))
              WHERE upper(trim(COALESCE(cm.cmsupid, ''))) = upper(trim(COALESCE(supplierbase.sbid, '')))
                AND (
                  SUBSTRING(TRIM(BOTH FROM COALESCE(cmf.cmfmfid, cm.cmmfid, cm.cmchar9, '')) FROM 1 FOR 3) = :store_id
                  OR upper(trim(COALESCE(cmf.cmfmarket, cm.cmjsmkt, ''))) = upper(trim(:store_id))
                )
            )
            """
        )

    sql = f"""
        SELECT {LIST_COLUMNS}
        FROM supplierbase
        WHERE {' AND '.join(where_clauses)}
        ORDER BY NULLIF(sbcname, '') NULLS LAST, sbid
        OFFSET :skip
        LIMIT :limit
    """
    rows = db.execute(text(sql), params).mappings().all()
    return [dict(row) for row in rows]


@router.get("/{supplier_id}", response_model=SupplierDetail)
async def get_supplier(
    supplier_id: str,
    db: Session = Depends(get_db),
):
    _ensure_table_ready(db)
    item = _fetch_one(
        db,
        f"SELECT {DETAIL_COLUMNS} FROM supplierbase WHERE sbid = :supplier_id",
        {"supplier_id": supplier_id},
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="供应商不存在")
    return item


@router.post("/", response_model=SupplierDetail)
async def create_supplier(
    supplier: SupplierCreate,
    db: Session = Depends(get_db),
    _=Depends(require_permission_dependency("supplier.create")),
):
    _ensure_table_ready(db)

    exists = db.execute(
        text("SELECT 1 FROM supplierbase WHERE sbid = :supplier_id"),
        {"supplier_id": supplier.sbid},
    ).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="供应商编码已存在")

    payload = supplier.model_dump()
    now = datetime.now()
    payload["sbljsrq"] = now
    payload["sblrrq"] = now
    payload["sbxgrq"] = now

    insert_columns = ", ".join(MANAGED_COLUMNS)
    insert_values = ", ".join(f":{column}" for column in MANAGED_COLUMNS)

    try:
        db.execute(
            text(f"INSERT INTO supplierbase ({insert_columns}) VALUES ({insert_values})"),
            payload,
        )
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return _fetch_one(
        db,
        f"SELECT {DETAIL_COLUMNS} FROM supplierbase WHERE sbid = :supplier_id",
        {"supplier_id": supplier.sbid},
    )


@router.put("/{supplier_id}", response_model=SupplierDetail)
async def update_supplier(
    supplier_id: str,
    supplier_update: SupplierUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_permission_dependency("supplier.edit")),
):
    _ensure_table_ready(db)

    if not db.execute(text("SELECT 1 FROM supplierbase WHERE sbid = :supplier_id"), {"supplier_id": supplier_id}).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="供应商不存在")

    update_data = supplier_update.model_dump(exclude_unset=True)
    if not update_data:
        return _fetch_one(
            db,
            f"SELECT {DETAIL_COLUMNS} FROM supplierbase WHERE sbid = :supplier_id",
            {"supplier_id": supplier_id},
        )

    update_data["sbxgrq"] = datetime.now()
    assignments = ", ".join(f"{field} = :{field}" for field in update_data.keys())
    update_data["supplier_id"] = supplier_id

    try:
        db.execute(
            text(f"UPDATE supplierbase SET {assignments} WHERE sbid = :supplier_id"),
            update_data,
        )
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return _fetch_one(
        db,
        f"SELECT {DETAIL_COLUMNS} FROM supplierbase WHERE sbid = :supplier_id",
        {"supplier_id": supplier_id},
    )


@router.delete("/{supplier_id}")
async def delete_supplier(
    supplier_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_permission_dependency("supplier.delete")),
):
    _ensure_table_ready(db)

    if not db.execute(text("SELECT 1 FROM supplierbase WHERE sbid = :supplier_id"), {"supplier_id": supplier_id}).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="供应商不存在")

    try:
        db.execute(text("DELETE FROM supplierbase WHERE sbid = :supplier_id"), {"supplier_id": supplier_id})
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {"message": "供应商删除成功", "id": supplier_id}
