"""
百货柜位管理系统 - 经营单元 API（public.business_units）

提供经营单元的增删改查与状态维护：
- 列表查询（支持按楼层、状态、编码筛选）
- 新增经营单元
- 更新经营单元
- 删除经营单元
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional

from models.database import get_db


router = APIRouter(
    prefix="/api/business-units",
    tags=["business-units"],
)


VALID_STATUS = {"ACTIVE", "VACANT", "FITOUT", "INACTIVE"}


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


def _expand_floor_filter_ids(db: Session, floor_id: int) -> list[int]:
    """经营单元已统一使用 public.floors.id。"""
    return [int(floor_id)]


def _get_floor_fk_target_table(db: Session) -> Optional[str]:
    row = db.execute(
        text(
            """
            SELECT ccu.table_name AS referenced_table
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name = tc.constraint_name
             AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'public'
              AND tc.table_name = 'business_units'
              AND kcu.column_name = 'floor_id'
            LIMIT 1
            """
        )
    ).fetchone()
    return row.referenced_table if row and row.referenced_table else None


def _resolve_target_floor_id(db: Session, floor_id: int) -> int:
    """经营单元写入目标固定为 public.floors.id。"""
    return int(floor_id)


@router.get("/")
async def list_business_units(
    floor_id: Optional[int] = Query(None, description="按楼层筛选"),
    status_filter: Optional[str] = Query(None, alias="status", description="按状态筛选"),
    keyword: Optional[str] = Query(None, description="按经营单元编码模糊搜索"),
    skip: int = 0,
    limit: int = 500,
    db: Session = Depends(get_db),
):
    """查询经营单元列表。"""
    try:
        sql = """
            SELECT
              id, floor_id, unit_code, status, manual_area, parent_unit_id, created_at, updated_at
            FROM business_units
            WHERE 1=1
        """
        params: dict = {"skip": skip, "limit": limit}
        if floor_id is not None:
            sql += " AND floor_id = ANY(:floor_ids)"
            params["floor_ids"] = _expand_floor_filter_ids(db, floor_id)
        if status_filter:
            sql += " AND status = :status"
            params["status"] = status_filter.strip().upper()
        if keyword:
            sql += " AND unit_code ILIKE :kw"
            params["kw"] = f"%{keyword.strip()}%"
        sql += " ORDER BY created_at DESC NULLS LAST, id DESC LIMIT :limit OFFSET :skip"

        rows = db.execute(text(sql), params).fetchall()
        return [
            {
                "id": r.id,
                "floor_id": r.floor_id,
                "unit_code": r.unit_code,
                "status": r.status,
                "manual_area": float(r.manual_area) if r.manual_area is not None else None,
                "parent_unit_id": r.parent_unit_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取经营单元失败: {str(e)}",
        )


@router.post("/")
async def create_business_unit(
    body: dict,
    db: Session = Depends(get_db),
):
    """新增经营单元。"""
    try:
        floor_id_raw = int(body.get("floor_id"))
        unit_code = (body.get("unit_code") or "").strip()
        status_value = (body.get("status") or "ACTIVE").strip().upper()
        manual_area = body.get("manual_area")
        parent_unit_id = body.get("parent_unit_id")

        if not unit_code:
            raise HTTPException(status_code=400, detail="unit_code 不能为空")
        if status_value not in VALID_STATUS:
            raise HTTPException(status_code=400, detail=f"status 非法，允许值: {', '.join(sorted(VALID_STATUS))}")

        floor_id = _resolve_target_floor_id(db, floor_id_raw)
        floor_exists = db.execute(
            text("SELECT 1 FROM business_units WHERE floor_id = :floor_id LIMIT 1"),
            {"floor_id": floor_id},
        ).fetchone()
        # 仅通过已有数据无法判断楼层存在性，改为显式检查目标外键表
        target = _get_floor_fk_target_table(db) or "floors"
        if target != "floors":
            raise HTTPException(status_code=500, detail=f"不支持的楼层外键表: {target}")
        floor_row = db.execute(
            text(f"SELECT 1 FROM {target} WHERE id = :id"),
            {"id": floor_id},
        ).fetchone()
        if not floor_row and not floor_exists:
            raise HTTPException(status_code=400, detail=f"floor_id={floor_id_raw} 不存在")

        dup = db.execute(
            text("SELECT 1 FROM business_units WHERE floor_id = :floor_id AND unit_code = :unit_code"),
            {"floor_id": floor_id, "unit_code": unit_code},
        ).fetchone()
        if dup:
            raise HTTPException(status_code=400, detail="同楼层 unit_code 已存在")

        parent_id = int(parent_unit_id) if parent_unit_id not in (None, "") else None
        if parent_id is not None:
            p = db.execute(
                text("SELECT id, floor_id FROM business_units WHERE id = :id"),
                {"id": parent_id},
            ).fetchone()
            if not p:
                raise HTTPException(status_code=400, detail="parent_unit_id 不存在")
            if int(p.floor_id) != floor_id:
                raise HTTPException(status_code=400, detail="parent_unit_id 必须与当前 floor_id 同楼层")

        row = db.execute(
            text(
                """
                INSERT INTO business_units (floor_id, unit_code, status, manual_area, parent_unit_id)
                VALUES (:floor_id, :unit_code, :status, :manual_area, :parent_unit_id)
                RETURNING id, floor_id, unit_code, status, manual_area, parent_unit_id, created_at, updated_at
                """
            ),
            {
                "floor_id": floor_id,
                "unit_code": unit_code,
                "status": status_value,
                "manual_area": manual_area,
                "parent_unit_id": parent_id,
            },
        ).fetchone()
        db.commit()
        return {
            "id": row.id,
            "floor_id": row.floor_id,
            "unit_code": row.unit_code,
            "status": row.status,
            "manual_area": float(row.manual_area) if row.manual_area is not None else None,
            "parent_unit_id": row.parent_unit_id,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"新增经营单元失败: {str(e)}")


@router.put("/{unit_id}")
async def update_business_unit(
    unit_id: int,
    body: dict,
    db: Session = Depends(get_db),
):
    """更新经营单元。"""
    try:
        current = db.execute(
            text("SELECT id, floor_id, unit_code FROM business_units WHERE id = :id"),
            {"id": unit_id},
        ).fetchone()
        if not current:
            raise HTTPException(status_code=404, detail="经营单元不存在")

        floor_id = int(current.floor_id)
        unit_code = (body.get("unit_code") or current.unit_code).strip()
        status_value = (body.get("status") or "").strip().upper() if body.get("status") is not None else None
        manual_area = body.get("manual_area", "__KEEP__")
        parent_unit_id = body.get("parent_unit_id", "__KEEP__")

        if not unit_code:
            raise HTTPException(status_code=400, detail="unit_code 不能为空")
        if status_value is not None and status_value not in VALID_STATUS:
            raise HTTPException(status_code=400, detail=f"status 非法，允许值: {', '.join(sorted(VALID_STATUS))}")

        dup = db.execute(
            text(
                """
                SELECT 1
                FROM business_units
                WHERE floor_id = :floor_id AND unit_code = :unit_code AND id <> :id
                """
            ),
            {"floor_id": floor_id, "unit_code": unit_code, "id": unit_id},
        ).fetchone()
        if dup:
            raise HTTPException(status_code=400, detail="同楼层 unit_code 已存在")

        sets: list[str] = ["unit_code = :unit_code"]
        params: dict = {"id": unit_id, "unit_code": unit_code}

        if status_value is not None:
            sets.append("status = :status")
            params["status"] = status_value
        if manual_area != "__KEEP__":
            sets.append("manual_area = :manual_area")
            params["manual_area"] = manual_area if manual_area not in ("", None) else None
        if parent_unit_id != "__KEEP__":
            parent_id = int(parent_unit_id) if parent_unit_id not in ("", None) else None
            if parent_id is not None:
                if parent_id == unit_id:
                    raise HTTPException(status_code=400, detail="parent_unit_id 不能等于自身")
                p = db.execute(
                    text("SELECT id, floor_id FROM business_units WHERE id = :id"),
                    {"id": parent_id},
                ).fetchone()
                if not p:
                    raise HTTPException(status_code=400, detail="parent_unit_id 不存在")
                if int(p.floor_id) != floor_id:
                    raise HTTPException(status_code=400, detail="parent_unit_id 必须与当前 floor_id 同楼层")
            sets.append("parent_unit_id = :parent_unit_id")
            params["parent_unit_id"] = parent_id

        db.execute(
            text(f"UPDATE business_units SET {', '.join(sets)}, updated_at = NOW() WHERE id = :id"),
            params,
        )
        row = db.execute(
            text(
                """
                SELECT id, floor_id, unit_code, status, manual_area, parent_unit_id, created_at, updated_at
                FROM business_units
                WHERE id = :id
                """
            ),
            {"id": unit_id},
        ).fetchone()
        db.commit()
        return {
            "id": row.id,
            "floor_id": row.floor_id,
            "unit_code": row.unit_code,
            "status": row.status,
            "manual_area": float(row.manual_area) if row.manual_area is not None else None,
            "parent_unit_id": row.parent_unit_id,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新经营单元失败: {str(e)}")


@router.delete("/{unit_id}")
async def delete_business_unit(
    unit_id: int,
    db: Session = Depends(get_db),
):
    """删除经营单元。"""
    try:
        row = db.execute(
            text("SELECT id FROM business_units WHERE id = :id"),
            {"id": unit_id},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="经营单元不存在")

        db.execute(text("DELETE FROM business_units WHERE id = :id"), {"id": unit_id})
        db.commit()
        return {"message": "删除成功", "id": unit_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除经营单元失败: {str(e)}")
