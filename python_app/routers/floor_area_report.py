"""
楼层在营及空置面积报表 API。

按门店、楼层汇总经营单元的在营/空置数量与人工确认面积。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from models.database import get_db
from routers.authz import require_permission_dependency


router = APIRouter(
    prefix="/api/reports",
    tags=["reports"],
)


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


def _table_columns(db: Session, table_name: str) -> set[str]:
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
    return {row.column_name for row in rows}


def _summary_sql(store_col: str | None, has_building_area: bool) -> str:
    """Build SQL only from allow-listed schema column names discovered above."""
    store_expression = f"f.{store_col}" if store_col else "NULL::text"
    building_area_expression = (
        "f.building_area" if has_building_area else "NULL::numeric"
    )
    store_filter = (
        f"""AND (
          :store_code = ''
          OR UPPER(TRIM((f.{store_col})::text)) = UPPER(TRIM(:store_code))
        )"""
        if store_col
        else ""
    )

    return f"""
        SELECT
          f.id AS floor_id,
          {store_expression} AS store_code,
          f.building_code,
          f.floor_code,
          f.name,
          {building_area_expression} AS building_area,
          COUNT(bu.id) FILTER (
            WHERE UPPER(TRIM(COALESCE(bu.status, ''))) = 'ACTIVE'
          )::bigint AS active_unit_count,
          COALESCE(SUM(bu.manual_area) FILTER (
            WHERE UPPER(TRIM(COALESCE(bu.status, ''))) = 'ACTIVE'
          ), 0)::numeric AS active_area_total,
          COUNT(bu.id) FILTER (
            WHERE UPPER(TRIM(COALESCE(bu.status, ''))) = 'ACTIVE'
              AND bu.manual_area IS NULL
          )::bigint AS active_area_missing_count,
          COUNT(bu.id) FILTER (
            WHERE UPPER(TRIM(COALESCE(bu.status, ''))) = 'VACANT'
          )::bigint AS vacant_unit_count,
          COALESCE(SUM(bu.manual_area) FILTER (
            WHERE UPPER(TRIM(COALESCE(bu.status, ''))) = 'VACANT'
          ), 0)::numeric AS vacant_area_total,
          COUNT(bu.id) FILTER (
            WHERE UPPER(TRIM(COALESCE(bu.status, ''))) = 'VACANT'
              AND bu.manual_area IS NULL
          )::bigint AS vacant_area_missing_count,
          COUNT(bu.id) FILTER (
            WHERE UPPER(TRIM(COALESCE(bu.status, ''))) NOT IN ('ACTIVE', 'VACANT')
          )::bigint AS other_unit_count
        FROM floors f
        LEFT JOIN business_units bu ON bu.floor_id = f.id
        WHERE 1 = 1
          {store_filter}
        GROUP BY
          f.id, {store_expression}, f.building_code, f.floor_code, f.name,
          {building_area_expression}, f.sort_no
        ORDER BY f.sort_no ASC, f.id ASC
    """


def _store_name_map(db: Session) -> dict[str, str]:
    if not _table_exists(db, "stores"):
        return {}

    store_columns = _table_columns(db, "stores")
    code_col = (
        "store_code"
        if "store_code" in store_columns
        else ("store_id" if "store_id" in store_columns else None)
    )
    name_col = (
        "store_name"
        if "store_name" in store_columns
        else ("name" if "name" in store_columns else None)
    )
    if not code_col or not name_col:
        return {}

    rows = db.execute(
        text(
            f"SELECT store_id, {code_col} AS code, {name_col} AS name FROM stores"
        )
    ).fetchall()
    result: dict[str, str] = {}
    for row in rows:
        if row.code is not None:
            result[str(row.code).strip()] = str(row.name or "")
        if row.store_id is not None:
            result[str(row.store_id).strip()] = str(row.name or "")
    return result


@router.get("/floor-area-summary")
async def floor_area_summary(
    store_code: str | None = Query(default=None, max_length=20),
    db: Session = Depends(get_db),
    _=Depends(require_permission_dependency("floor.view")),
):
    """按门店输出每个楼层的在营/空置柜位数量和人工确认面积。"""
    try:
        if not _table_exists(db, "floors") or not _table_exists(
            db, "business_units"
        ):
            return []

        floor_columns = _table_columns(db, "floors")
        store_col = (
            "store_code"
            if "store_code" in floor_columns
            else ("store_id" if "store_id" in floor_columns else None)
        )
        normalized_store_code = (store_code or "").strip()
        if normalized_store_code and not store_col:
            return []

        rows = db.execute(
            text(_summary_sql(store_col, "building_area" in floor_columns)),
            {"store_code": normalized_store_code},
        ).fetchall()
        store_names = _store_name_map(db)

        result = []
        for row in rows:
            row_store_code = (
                str(row.store_code).strip() if row.store_code is not None else ""
            )
            result.append(
                {
                    "floor_id": int(row.floor_id),
                    "store_code": row_store_code or None,
                    "store_name": store_names.get(row_store_code, ""),
                    "building_code": row.building_code,
                    "floor_code": row.floor_code,
                    "name": row.name,
                    "active_unit_count": int(row.active_unit_count or 0),
                    "active_area_total": float(row.active_area_total or 0),
                    "active_area_missing_count": int(
                        row.active_area_missing_count or 0
                    ),
                    "vacant_unit_count": int(row.vacant_unit_count or 0),
                    "vacant_area_total": float(row.vacant_area_total or 0),
                    "vacant_area_missing_count": int(
                        row.vacant_area_missing_count or 0
                    ),
                    "other_unit_count": int(row.other_unit_count or 0),
                    "building_area": (
                        float(row.building_area)
                        if row.building_area is not None
                        else 0
                    ),
                }
            )

        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取楼层面积报表失败: {str(exc)}",
        ) from exc
