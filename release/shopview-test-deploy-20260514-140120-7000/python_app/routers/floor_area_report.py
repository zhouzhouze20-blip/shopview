"""
楼层面积报表 API

统计每个楼层的经营单元数量与面积汇总。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from models.database import get_db


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


@router.get("/floor-area-summary")
async def floor_area_summary(db: Session = Depends(get_db)):
    """
    按楼层输出经营单元面积汇总。
    - unit_count: 经营单元数量
    - manual_area_total: 人工面积合计
    - building_area: 楼层建筑面积
    """
    try:
        if not _table_exists(db, "floors"):
            return []

        floor_cols = db.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'floors'
                """
            )
        ).fetchall()
        floor_col_set = {c.column_name for c in floor_cols}
        store_col = "store_id" if "store_id" in floor_col_set else ("store_code" if "store_code" in floor_col_set else None)
        select_store = f"{store_col} AS store_code," if store_col else "NULL::text AS store_code,"
        select_building_area = "building_area," if "building_area" in floor_col_set else "NULL::numeric AS building_area,"

        floors = db.execute(
            text(
                f"""
                SELECT id, {select_store} building_code, floor_code, name, {select_building_area} sort_no
                FROM floors
                ORDER BY sort_no ASC, id ASC
                """
            )
        ).fetchall()

        store_name_map: dict[str, str] = {}
        if _table_exists(db, "stores"):
            # stores 表通常存在 store_id/store_code/store_name，做兼容读取
            store_cols = db.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'stores'
                    """
                )
            ).fetchall()
            store_col_set = {c.column_name for c in store_cols}
            code_col = "store_code" if "store_code" in store_col_set else ("store_id" if "store_id" in store_col_set else None)
            name_col = "store_name" if "store_name" in store_col_set else ("name" if "name" in store_col_set else None)
            if code_col and name_col:
                stores = db.execute(
                    text(f"SELECT store_id, {code_col} AS code, {name_col} AS name FROM stores")
                ).fetchall()
                for s in stores:
                    if s.code is not None:
                        store_name_map[str(s.code)] = str(s.name or "")
                    if s.store_id is not None:
                        store_name_map[str(s.store_id)] = str(s.name or "")

        result = []
        for f in floors:
            agg = db.execute(
                text(
                    """
                    SELECT
                      COUNT(*)::bigint AS unit_count,
                      COALESCE(SUM(manual_area), 0)::numeric AS manual_area_total
                    FROM business_units
                    WHERE floor_id = :floor_id
                    """
                ),
                {"floor_id": int(f.id)},
            ).fetchone()

            result.append(
                {
                    "floor_id": int(f.id),
                    "store_code": f.store_code,
                    "store_name": store_name_map.get(str(f.store_code), "") if f.store_code is not None else "",
                    "building_code": f.building_code,
                    "floor_code": f.floor_code,
                    "name": f.name,
                    "unit_count": int(agg.unit_count or 0),
                    "manual_area_total": float(agg.manual_area_total or 0),
                    "building_area": float(f.building_area) if f.building_area is not None else 0,
                }
            )

        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取楼层面积报表失败: {str(e)}",
        )
