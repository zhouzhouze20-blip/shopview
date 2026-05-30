"""
百货柜位管理系统 - 柜位定义（MANAFRAME）API
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from models.database import get_db


router = APIRouter(
    prefix="/api/manaframe",
    tags=["manaframe"],
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


@router.get("/")
async def list_manaframe(
    keyword: Optional[str] = Query(None, description="按柜组编码/名称搜索"),
    status_filter: Optional[str] = Query(None, description="按状态筛选"),
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

        sql = """
            SELECT
              mfcode,
              mfcname,
              mfstatus,
              mfjyfs,
              mfjywz,
              mfjyqy,
              mfclass,
              mffcode,
              mfpcode,
              mfflag,
              mfcatcode,
              mfsubject,
              mfmemo
            FROM manaframe
            WHERE 1=1
        """
        params = {"skip": skip, "limit": limit}

        normalized_keyword = (keyword or "").strip()
        if normalized_keyword:
            sql += """
              AND (
                upper(trim(COALESCE(mfcode, ''))) LIKE upper(:keyword)
                OR upper(trim(COALESCE(mfcname, ''))) LIKE upper(:keyword)
              )
            """
            params["keyword"] = f"%{normalized_keyword}%"

        normalized_status = (status_filter or "").strip()
        if normalized_status:
            sql += " AND upper(trim(COALESCE(mfstatus, ''))) = upper(:status_filter)"
            params["status_filter"] = normalized_status

        sql += """
            ORDER BY mfcode ASC
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
