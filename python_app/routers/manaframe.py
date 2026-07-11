"""
百货柜位管理系统 - 柜位定义（MANAFRAME）API
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from models.database import get_db


router = APIRouter(
    prefix="/api/manaframe",
    tags=["manaframe"],
)


class ManaframeKeyBrandUpdate(BaseModel):
    is_key_brand: bool


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


def ensure_key_brand_table(db: Session) -> None:
    if _table_exists(db, "manaframe_key_brand"):
        return
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS manaframe_key_brand (
                mfcode VARCHAR(20) NOT NULL,
                is_key_brand BOOLEAN DEFAULT FALSE NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW() NOT NULL,
                updated_by VARCHAR(100),
                CONSTRAINT pk_manaframe_key_brand PRIMARY KEY (mfcode)
            )
            """
        )
    )
    db.commit()


@router.get("/")
async def list_manaframe(
    keyword: Optional[str] = Query(None, description="兼容旧参数：按柜组编码/名称搜索"),
    store_id: Optional[str] = Query(None, description="按门店筛选"),
    group_code: Optional[str] = Query(None, description="按柜组编码搜索"),
    group_name: Optional[str] = Query(None, description="按柜组名称搜索"),
    status_filter: Optional[str] = Query(None, description="兼容旧参数：按状态筛选"),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    try:
        if not _table_exists(db, "manaframe"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="manafame 表未创建",
            )
        ensure_key_brand_table(db)

        sql = """
            SELECT
              mf.mfcode,
              mf.mfcname,
              mf.mfstatus,
              mf.mfjyfs,
              mf.mfjywz,
              mf.mfjyqy,
              mf.mfclass,
              mf.mffcode,
              mf.mfpcode,
              mf.mfflag,
              mf.mfcatcode,
              mf.mfsubject,
              mf.mfmemo,
              COALESCE(kb.is_key_brand, FALSE) AS is_key_brand,
              mf.parsed_store_code AS store_code,
              mf.parsed_store_id AS store_id
            FROM (
              SELECT
                mf.*,
                SUBSTRING(TRIM(BOTH FROM COALESCE(mf.mfcode, '')) FROM 1 FOR 3) AS parsed_store_code,
                CASE
                  WHEN SUBSTRING(TRIM(BOTH FROM COALESCE(mf.mfcode, '')) FROM 1 FOR 3) ~ '^[0-9]+$'
                  THEN SUBSTRING(TRIM(BOTH FROM COALESCE(mf.mfcode, '')) FROM 1 FOR 3)::integer
                  ELSE NULL
                END AS parsed_store_id
              FROM manaframe mf
            ) mf
            LEFT JOIN manaframe_key_brand kb
              ON upper(trim(COALESCE(kb.mfcode, ''))) = upper(trim(COALESCE(mf.mfcode, '')))
            WHERE 1=1
        """
        params = {"skip": skip, "limit": limit}

        normalized_keyword = (keyword or "").strip()
        if normalized_keyword:
            sql += """
              AND (
                upper(trim(COALESCE(mf.mfcode, ''))) LIKE upper(:keyword)
                OR upper(trim(COALESCE(mf.mfcname, ''))) LIKE upper(:keyword)
              )
            """
            params["keyword"] = f"%{normalized_keyword}%"

        normalized_store_id = (store_id or "").strip()
        if normalized_store_id and normalized_store_id.upper() != "ALL":
            sql += """
              AND (
                mf.parsed_store_id::text = :store_id
                OR mf.parsed_store_code = :store_id
              )
            """
            params["store_id"] = normalized_store_id

        normalized_group_code = (group_code or "").strip()
        if normalized_group_code:
            sql += " AND upper(trim(COALESCE(mf.mfcode, ''))) LIKE upper(:group_code)"
            params["group_code"] = f"%{normalized_group_code}%"

        normalized_group_name = (group_name or "").strip()
        if normalized_group_name:
            sql += " AND upper(trim(COALESCE(mf.mfcname, ''))) LIKE upper(:group_name)"
            params["group_name"] = f"%{normalized_group_name}%"

        normalized_status = (status_filter or "").strip()
        if normalized_status:
            sql += " AND upper(trim(COALESCE(mf.mfstatus, ''))) = upper(:status_filter)"
            params["status_filter"] = normalized_status

        sql += """
            ORDER BY mf.mfcode ASC
            LIMIT :limit OFFSET :skip
        """

        rows = db.execute(text(sql), params).mappings().all()
        return [dict(row) for row in rows]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取柜位定义失败: {str(e)}",
        )


@router.put("/{group_code}/key-brand")
async def update_manaframe_key_brand(
    group_code: str,
    payload: ManaframeKeyBrandUpdate,
    db: Session = Depends(get_db),
):
    normalized_group_code = (group_code or "").strip()
    if not normalized_group_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="柜组编码不能为空")
    ensure_key_brand_table(db)
    existing = db.execute(
        text(
            """
            SELECT mfcode
            FROM manaframe
            WHERE upper(trim(COALESCE(mfcode, ''))) = upper(trim(:group_code))
            LIMIT 1
            """
        ),
        {"group_code": normalized_group_code},
    ).mappings().all()
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="柜组编码不存在")

    is_key_brand = bool(payload.is_key_brand)
    db.execute(
        text(
            """
            INSERT INTO manaframe_key_brand (mfcode, is_key_brand, updated_at)
            VALUES (:group_code, :is_key_brand, NOW())
            ON CONFLICT (mfcode) DO UPDATE
            SET is_key_brand = EXCLUDED.is_key_brand,
                updated_at = NOW()
            """
        ),
        {"group_code": normalized_group_code, "is_key_brand": is_key_brand},
    )
    db.commit()
    return {"group_code": normalized_group_code, "is_key_brand": is_key_brand}
