"""
合同柜位绑定 API（public.business_unit_binding）

用于补维护 ERP 合同未带柜位/经营单元字段时，ShopView 图纸柜位与合同号的关系。
"""

from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.database import get_db
from models.models import User
from routers.auth import get_current_user
from routers.authz import require_permission


router = APIRouter(
    prefix="/api/contract-unit-bindings",
    tags=["contract-unit-bindings"],
)


VALID_STATUS = {"ACTIVE", "INACTIVE", "HISTORY"}


def _json_value(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _table_exists(db: Session, table_name: str) -> bool:
    row = db.execute(
        text(
            """
            SELECT EXISTS (
              SELECT 1
              FROM information_schema.tables
              WHERE table_schema = 'public' AND table_name = :table_name
            ) AS ok
            """
        ),
        {"table_name": table_name},
    ).fetchone()
    return bool(row.ok) if row is not None else False


def _get_table_columns(db: Session, table_name: str) -> set[str]:
    rows = db.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = :table_name
            """
        ),
        {"table_name": table_name},
    ).fetchall()
    return {r.column_name for r in rows}


def _require_binding_table(db: Session) -> None:
    if not _table_exists(db, "business_unit_binding"):
        raise HTTPException(status_code=500, detail="business_unit_binding 表未创建")


def _parse_date(value: Any, field_name: str) -> Optional[date]:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except Exception:
        raise HTTPException(status_code=400, detail=f"{field_name} 日期格式应为 YYYY-MM-DD")


def _normalize_contract_no(value: Any) -> str:
    contract_no = str(value or "").strip()
    if not contract_no:
        raise HTTPException(status_code=400, detail="contract_id 不能为空")
    if contract_no.isdigit() and len(contract_no) < 8:
        return contract_no.zfill(8)
    return contract_no


def _require_business_unit(db: Session, unit_id: Any) -> int:
    try:
        normalized = int(unit_id)
    except Exception:
        raise HTTPException(status_code=400, detail="shop_unit_id 必须是有效数字")
    row = db.execute(text("SELECT id FROM business_units WHERE id = :id"), {"id": normalized}).fetchone()
    if not row:
        raise HTTPException(status_code=400, detail=f"经营单元不存在: {normalized}")
    return normalized


def _contract_exists(db: Session, contract_no: str) -> bool:
    checks = []
    if _table_exists(db, "contmain"):
        checks.append(("contmain", "cmcontno"))
    if _table_exists(db, "contmanaframe"):
        checks.append(("contmanaframe", "cmfcontno"))
    if not checks:
        return True
    for table_name, column_name in checks:
        row = db.execute(
            text(f"SELECT 1 FROM {table_name} WHERE upper(trim({column_name})) = upper(trim(:contract_no)) LIMIT 1"),
            {"contract_no": contract_no},
        ).fetchone()
        if row:
            return True
    return False


def _serialize(row) -> dict[str, Any]:
    return {key: _json_value(value) for key, value in dict(row).items()}


@router.get("/")
async def list_contract_unit_bindings(
    keyword: Optional[str] = Query(None, description="合同号/柜位号/主题/供应商搜索"),
    contract_id: Optional[str] = Query(None, description="合同号精确筛选"),
    unit_code: Optional[str] = Query(None, description="柜位号精确筛选"),
    status_filter: Optional[str] = Query(None, alias="status", description="绑定状态"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "contract.view")
    _require_binding_table(db)

    has_contmain = _table_exists(db, "contmain")
    has_supplierbase = _table_exists(db, "supplierbase")
    has_floors = _table_exists(db, "floors")
    supplier_join = (
        "LEFT JOIN supplierbase sb ON upper(trim(COALESCE(cm.cmsupid, ''))) = upper(trim(COALESCE(sb.sbid, '')))"
        if has_supplierbase
        else ""
    )
    contract_join = (
        f"""
        LEFT JOIN contmain cm
          ON upper(trim(COALESCE(cm.cmcontno, ''))) = upper(trim(COALESCE(b.contract_id, '')))
        {supplier_join}
        """
        if has_contmain
        else ""
    )
    contract_select = (
        """
        cm.cmtitle AS contract_title,
        cm.cmstatus AS contract_status,
        cm.cmeffdate::date AS contract_start_date,
        cm.cmlapdate::date AS contract_end_date,
        cm.cmsupid AS supplier_code,
        cm.cmppname AS brand_name,
        """
        if has_contmain
        else """
        NULL::varchar AS contract_title,
        NULL::varchar AS contract_status,
        NULL::date AS contract_start_date,
        NULL::date AS contract_end_date,
        NULL::varchar AS supplier_code,
        NULL::varchar AS brand_name,
        """
    )
    supplier_select = "sb.sbcname AS supplier_name," if has_supplierbase and has_contmain else "NULL::varchar AS supplier_name,"
    floor_join = "LEFT JOIN floors f ON f.id = bu.floor_id" if has_floors else ""
    floor_select = (
        """
        f.store_code,
        f.building_code,
        f.floor_code,
        f.name AS floor_name,
        """
        if has_floors
        else """
        NULL::varchar AS store_code,
        NULL::varchar AS building_code,
        NULL::varchar AS floor_code,
        NULL::varchar AS floor_name,
        """
    )

    sql = f"""
        SELECT
          b.id,
          b.shop_unit_id,
          bu.unit_code,
          bu.floor_id,
          {floor_select}
          b.contract_id,
          b.business_type,
          b.start_date,
          b.end_date,
          b.is_primary,
          b.status,
          b.remark,
          b.created_at,
          b.updated_at,
          {contract_select}
          {supplier_select}
          b.brand_id
        FROM business_unit_binding b
        LEFT JOIN business_units bu ON bu.id = b.shop_unit_id
        {floor_join}
        {contract_join}
        WHERE 1=1
    """
    params: dict[str, Any] = {"skip": skip, "limit": min(max(limit, 1), 500)}
    if keyword:
        sql += """
          AND (
            upper(trim(COALESCE(b.contract_id, ''))) LIKE upper(:kw)
            OR upper(trim(COALESCE(bu.unit_code, ''))) LIKE upper(:kw)
            OR upper(trim(COALESCE(b.remark, ''))) LIKE upper(:kw)
        """
        if has_contmain:
            sql += """
            OR upper(trim(COALESCE(cm.cmtitle, ''))) LIKE upper(:kw)
            OR upper(trim(COALESCE(cm.cmsupid, ''))) LIKE upper(:kw)
            OR upper(trim(COALESCE(cm.cmppname, ''))) LIKE upper(:kw)
            """
        if has_supplierbase:
            sql += " OR upper(trim(COALESCE(sb.sbcname, ''))) LIKE upper(:kw)"
        sql += ")"
        params["kw"] = f"%{keyword.strip()}%"
    if contract_id:
        params["contract_id"] = contract_id.strip()
        sql += " AND upper(trim(COALESCE(b.contract_id, ''))) = upper(trim(:contract_id))"
    if unit_code:
        params["unit_code"] = unit_code.strip()
        sql += " AND upper(trim(COALESCE(bu.unit_code, ''))) = upper(trim(:unit_code))"
    if status_filter and status_filter != "ALL":
        params["status"] = status_filter.strip().upper()
        sql += " AND upper(trim(COALESCE(b.status, ''))) = :status"

    count_sql = f"SELECT COUNT(*) AS cnt FROM ({sql}) t"
    total = db.execute(text(count_sql), params).fetchone()
    sql += " ORDER BY b.updated_at DESC NULLS LAST, b.id DESC LIMIT :limit OFFSET :skip"
    rows = db.execute(text(sql), params).mappings().all()
    return {
        "items": [_serialize(row) for row in rows],
        "count": int(total.cnt) if total else 0,
        "skip": skip,
        "limit": params["limit"],
    }


@router.post("/")
async def create_contract_unit_binding(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "contract.edit")
    _require_binding_table(db)
    shop_unit_id = _require_business_unit(db, body.get("shop_unit_id"))
    contract_no = _normalize_contract_no(body.get("contract_id"))
    if not _contract_exists(db, contract_no):
        raise HTTPException(status_code=400, detail=f"未找到 ERP 合同: {contract_no}")
    status_value = str(body.get("status") or "ACTIVE").strip().upper()
    if status_value not in VALID_STATUS:
        raise HTTPException(status_code=400, detail=f"status 非法，允许值: {', '.join(sorted(VALID_STATUS))}")
    start_date = _parse_date(body.get("start_date"), "start_date")
    end_date = _parse_date(body.get("end_date"), "end_date")
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date 不能晚于 end_date")

    dup = db.execute(
        text(
            """
            SELECT id FROM business_unit_binding
            WHERE shop_unit_id = :shop_unit_id
              AND upper(trim(contract_id)) = upper(trim(:contract_id))
              AND upper(trim(COALESCE(status, 'ACTIVE'))) = 'ACTIVE'
            LIMIT 1
            """
        ),
        {"shop_unit_id": shop_unit_id, "contract_id": contract_no},
    ).fetchone()
    if dup and status_value == "ACTIVE":
        raise HTTPException(status_code=400, detail="该柜位与合同已有有效绑定")

    try:
        row = db.execute(
            text(
                """
                INSERT INTO business_unit_binding (
                  shop_unit_id, contract_id, business_type, start_date, end_date,
                  is_primary, status, remark, created_at, updated_at
                )
                VALUES (
                  :shop_unit_id, :contract_id, :business_type, :start_date, :end_date,
                  :is_primary, :status, :remark, NOW(), NOW()
                )
                RETURNING id
                """
            ),
            {
                "shop_unit_id": shop_unit_id,
                "contract_id": contract_no,
                "business_type": (body.get("business_type") or "").strip() or None,
                "start_date": start_date,
                "end_date": end_date,
                "is_primary": bool(body.get("is_primary", True)),
                "status": status_value,
                "remark": (body.get("remark") or "").strip() or "前端手工补维护",
            },
        ).fetchone()
        db.commit()
        return {"message": "绑定创建成功", "id": row.id}
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"绑定创建失败: {str(e.orig)}")


@router.put("/{binding_id}")
async def update_contract_unit_binding(
    binding_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "contract.edit")
    _require_binding_table(db)
    exists = db.execute(text("SELECT id FROM business_unit_binding WHERE id = :id"), {"id": binding_id}).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail="绑定记录不存在")

    shop_unit_id = _require_business_unit(db, body.get("shop_unit_id")) if "shop_unit_id" in body else None
    contract_no = _normalize_contract_no(body.get("contract_id")) if "contract_id" in body else None
    if contract_no and not _contract_exists(db, contract_no):
        raise HTTPException(status_code=400, detail=f"未找到 ERP 合同: {contract_no}")
    status_value = str(body.get("status") or "ACTIVE").strip().upper() if "status" in body else None
    if status_value and status_value not in VALID_STATUS:
        raise HTTPException(status_code=400, detail=f"status 非法，允许值: {', '.join(sorted(VALID_STATUS))}")
    start_date = _parse_date(body.get("start_date"), "start_date") if "start_date" in body else None
    end_date = _parse_date(body.get("end_date"), "end_date") if "end_date" in body else None
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date 不能晚于 end_date")

    updates = ["updated_at = NOW()"]
    params: dict[str, Any] = {"id": binding_id}
    for column, value in (
        ("shop_unit_id", shop_unit_id),
        ("contract_id", contract_no),
        ("business_type", (body.get("business_type") or "").strip() or None if "business_type" in body else None),
        ("start_date", start_date),
        ("end_date", end_date),
        ("status", status_value),
        ("remark", (body.get("remark") or "").strip() or None if "remark" in body else None),
    ):
        if column in body or column in {"shop_unit_id", "contract_id", "start_date", "end_date", "status"} and value is not None:
            updates.append(f"{column} = :{column}")
            params[column] = value
    if "is_primary" in body:
        updates.append("is_primary = :is_primary")
        params["is_primary"] = bool(body.get("is_primary"))

    db.execute(text(f"UPDATE business_unit_binding SET {', '.join(updates)} WHERE id = :id"), params)
    db.commit()
    return {"message": "绑定更新成功", "id": binding_id}


@router.delete("/{binding_id}")
async def disable_contract_unit_binding(
    binding_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "contract.edit")
    _require_binding_table(db)
    result = db.execute(
        text(
            """
            UPDATE business_unit_binding
            SET status = 'INACTIVE', updated_at = NOW()
            WHERE id = :id
            """
        ),
        {"id": binding_id},
    )
    if not result.rowcount:
        raise HTTPException(status_code=404, detail="绑定记录不存在")
    db.commit()
    return {"message": "绑定已停用", "id": binding_id}
