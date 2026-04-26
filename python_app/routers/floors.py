"""
百货柜位管理系统 - 楼层字典 API（public.floors）
Department Store Counter Management System - Floor Dictionary API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional

from models.database import get_db
from models.models import Floor
from schemas.floor_dict_schemas import FloorDict, FloorDictCreate, FloorDictUpdate

router = APIRouter(
    prefix="/api/floors",
    tags=["floors"],
)

def _get_floors_columns(db: Session) -> set[str]:
    rows = db.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'floors'
            """
        )
    ).fetchall()
    return {r.column_name for r in rows}


def _ensure_building_area_column(db: Session) -> set[str]:
    """确保 floors 表存在建筑面积字段。"""
    cols = _get_floors_columns(db)
    if "building_area" not in cols:
        db.execute(text("ALTER TABLE floors ADD COLUMN building_area NUMERIC(12, 2)"))
        db.execute(text("COMMENT ON COLUMN floors.building_area IS '建筑面积（平方米）'"))
        db.commit()
        cols = _get_floors_columns(db)
    return cols


@router.get("/")
async def list_floors(
    store_id: Optional[str] = Query(None, description="按门店ID筛选"),
    skip: int = 0,
    limit: int = 500,
    db: Session = Depends(get_db),
):
    """获取楼层字典列表。

    说明：历史迁移里 floors 可能存在 store_id 或 store_code（或都不存在）。
    这里做自适应查询，保证接口稳定返回 store_id 字段给前端使用。
    """
    try:
        cols = _ensure_building_area_column(db)
        store_col = "store_id" if "store_id" in cols else ("store_code" if "store_code" in cols else None)

        select_store = f"{store_col} AS store_id," if store_col else "NULL::text AS store_id,"
        sql = f"""
            SELECT id, {select_store} building_code, floor_code, name, building_area, sort_no, created_at
            FROM floors
            WHERE 1=1
        """
        params = {"skip": skip, "limit": limit}
        if store_id is not None and store_col:
            sql += f" AND {store_col} = :store_id"
            params["store_id"] = store_id
        sql += " ORDER BY sort_no ASC, id ASC LIMIT :limit OFFSET :skip"
        result = db.execute(text(sql), params)
        rows = result.fetchall()
        return [
            {
                "id": r.id,
                "store_id": r.store_id,
                "building_code": r.building_code,
                "floor_code": r.floor_code,
                "name": r.name,
                "building_area": float(r.building_area) if r.building_area is not None else None,
                "sort_no": r.sort_no,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取楼层列表失败: {str(e)}",
        )


@router.get("/{floor_id}", response_model=FloorDict)
async def get_floor(
    floor_id: int,
    db: Session = Depends(get_db),
):
    """获取单条楼层字典"""
    _ensure_building_area_column(db)
    row = db.query(Floor).filter(Floor.id == floor_id).first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="楼层不存在",
        )
    return row


@router.post("/", response_model=FloorDict)
async def create_floor(
    body: FloorDictCreate,
    db: Session = Depends(get_db),
):
    """新增楼层字典"""
    try:
        cols = _ensure_building_area_column(db)
        store_col = "store_id" if "store_id" in cols else ("store_code" if "store_code" in cols else None)

        # 唯一性：优先使用库里现有的唯一约束逻辑
        exists = db.execute(
            text(
                """
                SELECT 1 FROM floors
                WHERE building_code = :building_code AND floor_code = :floor_code
                LIMIT 1
                """
            ),
            {"building_code": body.building_code, "floor_code": body.floor_code},
        ).fetchone()
        if exists:
            raise HTTPException(status_code=400, detail="楼栋编码+楼层编码已存在")

        params = {
            "building_code": body.building_code,
            "floor_code": body.floor_code,
            "name": body.name,
            "building_area": body.building_area,
            "sort_no": body.sort_no,
            "store_value": body.store_id,
        }
        if store_col:
            sql = f"""
                INSERT INTO floors ({store_col}, building_code, floor_code, name, building_area, sort_no)
                VALUES (:store_value, :building_code, :floor_code, :name, :building_area, :sort_no)
                RETURNING id, {store_col} AS store_id, building_code, floor_code, name, building_area, sort_no, created_at
            """
        else:
            sql = """
                INSERT INTO floors (building_code, floor_code, name, building_area, sort_no)
                VALUES (:building_code, :floor_code, :name, :building_area, :sort_no)
                RETURNING id, NULL::text AS store_id, building_code, floor_code, name, building_area, sort_no, created_at
            """

        row = db.execute(text(sql), params).fetchone()
        db.commit()
        return {
            "id": row.id,
            "store_id": row.store_id,
            "building_code": row.building_code,
            "floor_code": row.floor_code,
            "name": row.name,
            "building_area": float(row.building_area) if row.building_area is not None else None,
            "sort_no": row.sort_no,
            "created_at": row.created_at,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"新增楼层失败: {str(e)}")


@router.put("/{floor_id}", response_model=FloorDict)
async def update_floor(
    floor_id: int,
    body: FloorDictUpdate,
    db: Session = Depends(get_db),
):
    """更新楼层字典"""
    try:
        cols = _ensure_building_area_column(db)
        store_col = "store_id" if "store_id" in cols else ("store_code" if "store_code" in cols else None)

        exists = db.execute(text("SELECT 1 FROM floors WHERE id = :id"), {"id": floor_id}).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="楼层不存在")

        data = body.model_dump(exclude_unset=True)
        sets: list[str] = []
        params: dict = {"id": floor_id}
        if "building_code" in data and data["building_code"] is not None:
            sets.append("building_code = :building_code")
            params["building_code"] = data["building_code"]
        if "floor_code" in data and data["floor_code"] is not None:
            sets.append("floor_code = :floor_code")
            params["floor_code"] = data["floor_code"]
        if "name" in data and data["name"] is not None:
            sets.append("name = :name")
            params["name"] = data["name"]
        if "building_area" in data:
            sets.append("building_area = :building_area")
            params["building_area"] = data["building_area"]
        if "sort_no" in data and data["sort_no"] is not None:
            sets.append("sort_no = :sort_no")
            params["sort_no"] = data["sort_no"]
        if "store_id" in data and store_col:
            sets.append(f"{store_col} = :store_value")
            params["store_value"] = data["store_id"]

        if sets:
            db.execute(text(f"UPDATE floors SET {', '.join(sets)} WHERE id = :id"), params)

        select_store = f"{store_col} AS store_id," if store_col else "NULL::text AS store_id,"
        row = db.execute(
            text(
                f"""
                SELECT id, {select_store} building_code, floor_code, name, building_area, sort_no, created_at
                FROM floors WHERE id = :id
                """
            ),
            {"id": floor_id},
        ).fetchone()
        db.commit()
        return {
            "id": row.id,
            "store_id": row.store_id,
            "building_code": row.building_code,
            "floor_code": row.floor_code,
            "name": row.name,
            "building_area": float(row.building_area) if row.building_area is not None else None,
            "sort_no": row.sort_no,
            "created_at": row.created_at,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新楼层失败: {str(e)}")


@router.delete("/{floor_id}")
async def delete_floor(
    floor_id: int,
    db: Session = Depends(get_db),
):
    """删除楼层字典"""
    _ensure_building_area_column(db)
    row = db.query(Floor).filter(Floor.id == floor_id).first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="楼层不存在",
        )
    db.delete(row)
    db.commit()
    return {"message": "删除成功"}
