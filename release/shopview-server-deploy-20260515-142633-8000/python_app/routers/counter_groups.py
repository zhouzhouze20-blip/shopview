"""
柜组查询 API

保留 /api/counter-groups 路径兼容旧前端，数据源改为 ERP MANAFRAME。
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from models.database import get_db


router = APIRouter(prefix="/api/counter-groups", tags=["counter-groups"])


@router.get("/")
async def get_counter_groups(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    store_id: Optional[int] = Query(None, description="门店ID"),
    db: Session = Depends(get_db),
):
    sql = """
        SELECT
          ROW_NUMBER() OVER (ORDER BY mf.mfcode) AS group_id,
          mf.mfcode AS group_code,
          mf.mfcname AS group_name,
          dept.mfcode AS department_code,
          dept.mfcname AS department_name,
          mf.mfjyfs AS operation_method,
          mf.mfzlgh AS brand_name,
          CASE WHEN upper(trim(COALESCE(mf.mfstatus, ''))) = 'Y' THEN TRUE ELSE FALSE END AS is_active,
          mf.mflast_modified AS erp_sync_time,
          COALESCE(mf.mflast_modified, NOW()) AS created_at,
          mf.mflast_modified AS updated_at
        FROM manaframe mf
        LEFT JOIN manaframe dept
          ON upper(trim(COALESCE(mf.mfpcode, ''))) = upper(trim(COALESCE(dept.mfcode, '')))
        WHERE 1=1
    """
    params = {"skip": skip, "limit": limit}

    if is_active is not None:
        sql += " AND upper(trim(COALESCE(mf.mfstatus, ''))) = :status_value"
        params["status_value"] = "Y" if is_active else "N"
    if store_id is not None:
        sql += """
          AND CASE
            WHEN SUBSTRING(TRIM(BOTH FROM COALESCE(mf.mfcode, '')) FROM 1 FOR 3) ~ '^[0-9]+$'
            THEN SUBSTRING(TRIM(BOTH FROM COALESCE(mf.mfcode, '')) FROM 1 FOR 3)::integer
            ELSE NULL
          END = :store_id
        """
        params["store_id"] = store_id
    if search:
        sql += """
          AND (
            upper(trim(COALESCE(mf.mfcname, ''))) LIKE upper(:search)
            OR upper(trim(COALESCE(mf.mfcode, ''))) LIKE upper(:search)
            OR upper(trim(COALESCE(mf.mfzlgh, ''))) LIKE upper(:search)
          )
        """
        params["search"] = f"%{search.strip()}%"

    sql += " ORDER BY mf.mfcode ASC LIMIT :limit OFFSET :skip"
    return [dict(row) for row in db.execute(text(sql), params).mappings().all()]


@router.post("/")
async def create_counter_group():
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="柜组主数据已改为 ERP MANAFRAME，请通过 ERP 同步维护",
    )
