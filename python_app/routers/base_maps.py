"""
百货柜位管理系统 - 静态底图 API（public.base_maps）

用于上传 SVG 底图后，在 base_maps 表登记元数据，并支持按楼层查询/设置激活底图。
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
import re

from models.database import get_db
from schemas.base_map_schemas import BaseMapCreate, BaseMapUpdate


router = APIRouter(
    prefix="/api/base-maps",
    tags=["base-maps"],
)


def _table_exists(db: Session, table_name: str) -> bool:
    """检查数据表是否存在（兼容不同阶段的表结构）。"""
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
    """读取指定表的列清单。"""
    if not _is_safe_identifier(table_name):
        return set()
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


def _is_safe_identifier(name: str) -> bool:
    """仅允许安全 SQL 标识符，避免动态表名注入风险。"""
    return bool(re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", name))


def _id_exists_in_table(db: Session, table_name: str, record_id: int) -> bool:
    """检查某张表中指定 id 是否存在。"""
    if not _is_safe_identifier(table_name):
        return False
    row = db.execute(
        text(f"SELECT 1 FROM {table_name} WHERE id = :id"),
        {"id": record_id},
    ).fetchone()
    return row is not None


def _get_base_maps_floor_fk_table(db: Session) -> Optional[str]:
    """
    获取 base_maps.floor_id 外键真实指向的表名。
    返回 None 表示当前库中未查到外键信息。
    """
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
              AND tc.table_name = 'base_maps'
              AND kcu.column_name = 'floor_id'
            LIMIT 1
            """
        )
    ).fetchone()
    return row.referenced_table if row and row.referenced_table else None


def _floor_exists(db: Session, floor_id: int) -> tuple[bool, str]:
    """
    校验楼层ID是否存在。
    优先按 base_maps.floor_id 的真实外键目标表校验，避免“查 A 表通过、插 B 表失败”。
    """
    fk_table = _get_base_maps_floor_fk_table(db)
    if fk_table and _table_exists(db, fk_table):
        return _id_exists_in_table(db, fk_table, floor_id), fk_table

    # 兼容：未取到外键时，按常见结构兜底
    for table_name in ("floors", "store_floors"):
        if _table_exists(db, table_name) and _id_exists_in_table(db, table_name, floor_id):
            return True, table_name

    return False, fk_table or "floors/store_floors"


def _resolve_base_maps_floor_id(db: Session, floor_id: int) -> tuple[int, str]:
    """
    将前端传入的 floor_id 解析为 base_maps 可写入的 floor_id。

    场景：
    - 若 base_maps 外键目标表就是 floors 且 id 存在：直接使用；
    - 若外键目标表是 store_floors，而 floor_id 仅存在于 floors：
      尝试按 building_code + floor_code 映射到 store_floors；
      若未命中则自动补建一条 store_floors，并返回新 id。
    """
    fk_table = _get_base_maps_floor_fk_table(db)
    if not fk_table or not _table_exists(db, fk_table):
        return floor_id, "raw"

    # 传入 id 在目标表中已存在，直接使用
    if _id_exists_in_table(db, fk_table, floor_id):
        return floor_id, "direct"

    # 非 store_floors 场景不做自动映射
    if fk_table != "store_floors":
        return floor_id, "raw"

    if not _table_exists(db, "floors"):
        return floor_id, "raw"

    floors_cols = _get_table_columns(db, "floors")
    if "id" not in floors_cols:
        return floor_id, "raw"

    floor_row = db.execute(
        text(
            """
            SELECT id, building_code, floor_code, name, sort_no
            FROM floors
            WHERE id = :id
            """
        ),
        {"id": floor_id},
    ).fetchone()
    if not floor_row:
        return floor_id, "raw"

    sf_cols = _get_table_columns(db, "store_floors")
    if "id" not in sf_cols:
        return floor_id, "raw"

    # 1) 优先按 building_code + floor_code 映射
    if "building_code" in sf_cols and "floor_code" in sf_cols:
        mapped = db.execute(
            text(
                """
                SELECT id
                FROM store_floors
                WHERE building_code = :building_code
                  AND floor_code = :floor_code
                ORDER BY id ASC
                LIMIT 1
                """
            ),
            {"building_code": floor_row.building_code, "floor_code": floor_row.floor_code},
        ).fetchone()
        if mapped:
            return int(mapped.id), "mapped"

    # 2) 未命中则自动补建 store_floors 记录
    insert_cols: list[str] = []
    insert_params: dict = {}
    if "building_code" in sf_cols:
        insert_cols.append("building_code")
        insert_params["building_code"] = floor_row.building_code
    if "floor_code" in sf_cols:
        insert_cols.append("floor_code")
        insert_params["floor_code"] = floor_row.floor_code
    if "name" in sf_cols:
        insert_cols.append("name")
        insert_params["name"] = floor_row.name
    if "sort_no" in sf_cols:
        insert_cols.append("sort_no")
        insert_params["sort_no"] = floor_row.sort_no

    # store_id/store_code 字段名兼容
    if "store_id" in sf_cols:
        insert_cols.append("store_id")
        if "store_id" in floors_cols:
            v = db.execute(text("SELECT store_id FROM floors WHERE id = :id"), {"id": floor_id}).fetchone()
            insert_params["store_id"] = v.store_id if v else None
        elif "store_code" in floors_cols:
            v = db.execute(text("SELECT store_code FROM floors WHERE id = :id"), {"id": floor_id}).fetchone()
            insert_params["store_id"] = v.store_code if v else None
        else:
            insert_params["store_id"] = None
    elif "store_code" in sf_cols:
        insert_cols.append("store_code")
        if "store_code" in floors_cols:
            v = db.execute(text("SELECT store_code FROM floors WHERE id = :id"), {"id": floor_id}).fetchone()
            insert_params["store_code"] = v.store_code if v else None
        elif "store_id" in floors_cols:
            v = db.execute(text("SELECT store_id FROM floors WHERE id = :id"), {"id": floor_id}).fetchone()
            insert_params["store_code"] = v.store_id if v else None
        else:
            insert_params["store_code"] = None

    if not insert_cols:
        return floor_id, "raw"

    col_sql = ", ".join(insert_cols)
    val_sql = ", ".join([f":{c}" for c in insert_cols])
    created = db.execute(
        text(f"INSERT INTO store_floors ({col_sql}) VALUES ({val_sql}) RETURNING id"),
        insert_params,
    ).fetchone()
    if created:
        return int(created.id), "created"
    return floor_id, "raw"


def _expand_floor_filter_ids(db: Session, floor_id: int) -> list[int]:
    """
    列表筛选时扩展可匹配的 floor_id：
    - 直接包含传入 id
    - 若存在 floors 与 store_floors 双表，按 building_code + floor_code 映射补充对应 id
    """
    ids = {int(floor_id)}
    if not (_table_exists(db, "floors") and _table_exists(db, "store_floors")):
        return list(ids)

    # floor_id 在 floors 中 -> 找 store_floors 对应项
    f = db.execute(
        text("SELECT building_code, floor_code FROM floors WHERE id = :id"),
        {"id": floor_id},
    ).fetchone()
    if f:
        r = db.execute(
            text(
                """
                SELECT id
                FROM store_floors
                WHERE building_code = :building_code
                  AND floor_code = :floor_code
                """
            ),
            {"building_code": f.building_code, "floor_code": f.floor_code},
        ).fetchall()
        for x in r:
            ids.add(int(x.id))

    # floor_id 在 store_floors 中 -> 找 floors 对应项
    sf = db.execute(
        text("SELECT building_code, floor_code FROM store_floors WHERE id = :id"),
        {"id": floor_id},
    ).fetchone()
    if sf:
        r2 = db.execute(
            text(
                """
                SELECT id
                FROM floors
                WHERE building_code = :building_code
                  AND floor_code = :floor_code
                """
            ),
            {"building_code": sf.building_code, "floor_code": sf.floor_code},
        ).fetchall()
        for x in r2:
            ids.add(int(x.id))

    return list(ids)


@router.get("/floor-options")
async def list_base_map_floor_options(
    skip: int = 0,
    limit: int = 500,
    db: Session = Depends(get_db),
):
    """
    获取“可用于 base_maps.floor_id”的楼层列表。

    关键点：
    1) 前端优先展示 floors 中维护的楼层，因为“楼层定义”页面写入的是 floors；
       创建底图时再由后端自动映射到 base_maps.floor_id 的真实外键目标表；
    2) 返回统一字段结构，便于前端复用楼层下拉组件；
    3) 兼容 floors / store_floors 历史差异。
    """
    try:
        candidate_table = "floors" if _table_exists(db, "floors") else ("store_floors" if _table_exists(db, "store_floors") else None)
        if not candidate_table:
            return []

        cols = _get_table_columns(db, candidate_table)
        if "id" not in cols:
            return []

        store_col = "store_id" if "store_id" in cols else ("store_code" if "store_code" in cols else None)
        building_col = "building_code" if "building_code" in cols else None
        floor_col = "floor_code" if "floor_code" in cols else None
        name_col = "name" if "name" in cols else None
        sort_col = "sort_no" if "sort_no" in cols else None
        created_col = "created_at" if "created_at" in cols else None

        select_store = f"{store_col} AS store_id" if store_col else "NULL::text AS store_id"
        select_building = f"{building_col} AS building_code" if building_col else f"'{candidate_table}'::text AS building_code"
        select_floor = f"{floor_col} AS floor_code" if floor_col else "id::text AS floor_code"
        select_name = f"{name_col} AS name" if name_col else "'未命名楼层'::text AS name"
        select_sort = f"{sort_col} AS sort_no" if sort_col else "0 AS sort_no"
        select_created = f"{created_col} AS created_at" if created_col else "NULL::timestamp AS created_at"

        sql = f"""
            SELECT
              id,
              {select_store},
              {select_building},
              {select_floor},
              {select_name},
              {select_sort},
              {select_created}
            FROM {candidate_table}
            ORDER BY sort_no ASC, id ASC
            LIMIT :limit OFFSET :skip
        """
        rows = db.execute(text(sql), {"skip": skip, "limit": limit}).fetchall()
        return [
            {
                "id": r.id,
                "store_id": r.store_id,
                "building_code": r.building_code,
                "floor_code": r.floor_code,
                "name": r.name,
                "sort_no": r.sort_no,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取可用楼层失败: {str(e)}",
        )


@router.get("/")
async def list_base_maps(
    floor_id: Optional[int] = Query(None, description="按楼层ID筛选"),
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    """获取底图列表（优先按楼层筛选）。使用原始 SQL 避免 ORM 与表结构不一致。"""
    try:
        fk_table = _get_base_maps_floor_fk_table(db)
        floor_table = fk_table if fk_table and _table_exists(db, fk_table) else None
        if not floor_table:
            floor_table = "floors" if _table_exists(db, "floors") else ("store_floors" if _table_exists(db, "store_floors") else None)

        floor_cols = _get_table_columns(db, floor_table) if floor_table else set()
        store_col = "store_id" if "store_id" in floor_cols else ("store_code" if "store_code" in floor_cols else None)
        building_col = "building_code" if "building_code" in floor_cols else None
        floor_code_col = "floor_code" if "floor_code" in floor_cols else None
        name_col = "name" if "name" in floor_cols else None

        select_store = f"f.{store_col} AS store_id" if store_col else "NULL::text AS store_id"
        select_building = f"f.{building_col} AS building_code" if building_col else "NULL::text AS building_code"
        select_floor_code = f"f.{floor_code_col} AS floor_code" if floor_code_col else "NULL::text AS floor_code"
        select_floor_name = f"f.{name_col} AS floor_name" if name_col else "NULL::text AS floor_name"
        join_floor = f"LEFT JOIN {floor_table} f ON bm.floor_id = f.id" if floor_table else ""

        sql = f"""
            SELECT
              bm.id, bm.floor_id, bm.base_map_code, bm.file_url,
              bm.svg_viewbox, bm.svg_width, bm.svg_height,
              bm.is_active, bm.created_at,
              {select_store},
              {select_building},
              {select_floor_code},
              {select_floor_name}
            FROM base_maps bm
            {join_floor}
            WHERE 1=1
        """
        params = {"skip": skip, "limit": limit}
        if floor_id is not None:
            filter_ids = _expand_floor_filter_ids(db, floor_id)
            sql += " AND bm.floor_id = ANY(:floor_ids)"
            params["floor_ids"] = filter_ids
        sql += " ORDER BY bm.created_at DESC NULLS LAST, bm.id DESC LIMIT :limit OFFSET :skip"
        rows = db.execute(text(sql), params).fetchall()
        return [
            {
                "id": r.id,
                "floor_id": r.floor_id,
                "base_map_code": r.base_map_code,
                "file_url": r.file_url,
                "svg_viewbox": r.svg_viewbox,
                "svg_width": float(r.svg_width) if r.svg_width is not None else None,
                "svg_height": float(r.svg_height) if r.svg_height is not None else None,
                "is_active": bool(r.is_active),
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "store_id": r.store_id,
                "building_code": r.building_code,
                "floor_code": r.floor_code,
                "floor_name": r.floor_name,
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取底图列表失败: {str(e)}",
        )


@router.post("/")
async def create_base_map(
    body: BaseMapCreate,
    db: Session = Depends(get_db),
):
    """创建底图记录。若 is_active=true，会先取消同楼层其它 active。"""
    try:
        # 1) 将 floor_id 解析为 base_maps 外键可用的 id（含 floors->store_floors 映射/补建）
        resolved_floor_id, _resolve_mode = _resolve_base_maps_floor_id(db, body.floor_id)

        # 2) 校验解析后的楼层存在
        floor_ok, expected_table = _floor_exists(db, resolved_floor_id)
        if not floor_ok:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"floor_id={body.floor_id} 不存在（base_maps.floor_id 期望关联表: {expected_table}），"
                    f"请先在该楼层表创建对应记录"
                ),
            )

        # 3) base_map_code 唯一（给友好提示）
        code_exists = db.execute(
            text("SELECT 1 FROM base_maps WHERE base_map_code = :code"),
            {"code": body.base_map_code},
        ).fetchone()
        if code_exists:
            raise HTTPException(status_code=400, detail="base_map_code 已存在")

        # 4) 若设为 active，先关闭同楼层其它 active
        if body.is_active:
            db.execute(
                text("UPDATE base_maps SET is_active = false WHERE floor_id = :floor_id AND is_active = true"),
                {"floor_id": resolved_floor_id},
            )

        # 5) 插入并返回
        row = db.execute(
            text(
                """
                INSERT INTO base_maps
                  (floor_id, base_map_code, file_url, svg_viewbox, svg_width, svg_height, is_active)
                VALUES
                  (:floor_id, :base_map_code, :file_url, :svg_viewbox, :svg_width, :svg_height, :is_active)
                RETURNING
                  id, floor_id, base_map_code, file_url,
                  svg_viewbox, svg_width, svg_height,
                  is_active, created_at
                """
            ),
            {
                "floor_id": resolved_floor_id,
                "base_map_code": body.base_map_code,
                "file_url": body.file_url,
                "svg_viewbox": body.svg_viewbox,
                "svg_width": body.svg_width,
                "svg_height": body.svg_height,
                "is_active": body.is_active,
            },
        ).fetchone()
        db.commit()

        return {
            "id": row.id,
            "floor_id": row.floor_id,
            "base_map_code": row.base_map_code,
            "file_url": row.file_url,
            "svg_viewbox": row.svg_viewbox,
            "svg_width": float(row.svg_width) if row.svg_width is not None else None,
            "svg_height": float(row.svg_height) if row.svg_height is not None else None,
            "is_active": bool(row.is_active),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建底图失败: {str(e)}",
        )


@router.post("/{base_map_id}/activate")
async def activate_base_map(
    base_map_id: int,
    db: Session = Depends(get_db),
):
    """将指定底图设为该楼层 active（同楼层其它 active 自动取消）。"""
    try:
        row = db.execute(
            text("SELECT id, floor_id FROM base_maps WHERE id = :id"),
            {"id": base_map_id},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="底图不存在")

        floor_id = row.floor_id
        db.execute(
            text("UPDATE base_maps SET is_active = false WHERE floor_id = :floor_id AND is_active = true"),
            {"floor_id": floor_id},
        )
        db.execute(
            text("UPDATE base_maps SET is_active = true WHERE id = :id"),
            {"id": base_map_id},
        )
        db.commit()
        return {"message": "已设为当前底图", "id": base_map_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"设置 active 失败: {str(e)}")


@router.put("/{base_map_id}")
async def update_base_map(
    base_map_id: int,
    body: BaseMapUpdate,
    db: Session = Depends(get_db),
):
    """更新底图元数据。"""
    try:
        existing = db.execute(
            text(
                """
                SELECT id, floor_id, base_map_code, svg_viewbox, svg_width, svg_height, is_active
                FROM base_maps
                WHERE id = :id
                """
            ),
            {"id": base_map_id},
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="底图不存在")

        updates = body.dict(exclude_unset=True)
        next_code = updates.get("base_map_code", existing.base_map_code)
        if next_code is not None:
            next_code = next_code.strip()
        if not next_code:
            raise HTTPException(status_code=400, detail="base_map_code 不能为空")

        code_exists = db.execute(
            text("SELECT 1 FROM base_maps WHERE base_map_code = :code AND id <> :id"),
            {"code": next_code, "id": base_map_id},
        ).fetchone()
        if code_exists:
            raise HTTPException(status_code=400, detail="base_map_code 已存在")

        next_is_active = updates.get("is_active", bool(existing.is_active))
        if next_is_active:
            db.execute(
                text("UPDATE base_maps SET is_active = false WHERE floor_id = :floor_id AND id <> :id"),
                {"floor_id": existing.floor_id, "id": base_map_id},
            )

        row = db.execute(
            text(
                """
                UPDATE base_maps
                SET
                  base_map_code = :base_map_code,
                  svg_viewbox = :svg_viewbox,
                  svg_width = :svg_width,
                  svg_height = :svg_height,
                  is_active = :is_active
                WHERE id = :id
                RETURNING
                  id, floor_id, base_map_code, file_url,
                  svg_viewbox, svg_width, svg_height,
                  is_active, created_at
                """
            ),
            {
                "id": base_map_id,
                "base_map_code": next_code,
                "svg_viewbox": updates.get("svg_viewbox", existing.svg_viewbox),
                "svg_width": updates.get("svg_width", existing.svg_width),
                "svg_height": updates.get("svg_height", existing.svg_height),
                "is_active": next_is_active,
            },
        ).fetchone()
        db.commit()

        return {
            "id": row.id,
            "floor_id": row.floor_id,
            "base_map_code": row.base_map_code,
            "file_url": row.file_url,
            "svg_viewbox": row.svg_viewbox,
            "svg_width": float(row.svg_width) if row.svg_width is not None else None,
            "svg_height": float(row.svg_height) if row.svg_height is not None else None,
            "is_active": bool(row.is_active),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新底图失败: {str(e)}")


@router.delete("/{base_map_id}")
async def delete_base_map(
    base_map_id: int,
    db: Session = Depends(get_db),
):
    """删除底图记录。若已有柜位图版本引用则拒绝删除。"""
    try:
        existing = db.execute(
            text("SELECT id FROM base_maps WHERE id = :id"),
            {"id": base_map_id},
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="底图不存在")

        version_ref = db.execute(
            text("SELECT 1 FROM unit_map_versions WHERE base_map_id = :id LIMIT 1"),
            {"id": base_map_id},
        ).fetchone()
        if version_ref:
            raise HTTPException(status_code=400, detail="该底图已被柜位图版本引用，无法删除")

        db.execute(text("DELETE FROM base_maps WHERE id = :id"), {"id": base_map_id})
        db.commit()
        return {"message": "底图已删除", "id": base_map_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除底图失败: {str(e)}")
