"""
百货柜位管理系统 - 几何明细 API（public.geo_elements）

用于前端按版本拉取柜位几何（path_data）并渲染预览。
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional

from models.database import get_db


router = APIRouter(
    prefix="/api/geo-elements",
    tags=["geo-elements"],
)


@router.get("/")
async def list_geo_elements(
    version_id: int = Query(..., description="柜位图版本ID"),
    skip: int = 0,
    limit: int = 5000,
    db: Session = Depends(get_db),
):
    """按版本获取几何明细列表（用于前端渲染）。"""
    try:
        rows = db.execute(
            text(
                """
                SELECT
                  id, version_id, unit_id, svg_element_id, path_data,
                  centroid_x, centroid_y,
                  bbox_minx, bbox_miny, bbox_maxx, bbox_maxy,
                  area_svg, created_at
                FROM geo_elements
                WHERE version_id = :version_id
                ORDER BY id ASC
                LIMIT :limit OFFSET :skip
                """
            ),
            {"version_id": version_id, "skip": skip, "limit": limit},
        ).fetchall()

        return [
            {
                "id": r.id,
                "version_id": r.version_id,
                "unit_id": r.unit_id,
                "svg_element_id": r.svg_element_id,
                "path_data": r.path_data,
                "centroid_x": float(r.centroid_x) if r.centroid_x is not None else None,
                "centroid_y": float(r.centroid_y) if r.centroid_y is not None else None,
                "bbox_minx": float(r.bbox_minx) if r.bbox_minx is not None else None,
                "bbox_miny": float(r.bbox_miny) if r.bbox_miny is not None else None,
                "bbox_maxx": float(r.bbox_maxx) if r.bbox_maxx is not None else None,
                "bbox_maxy": float(r.bbox_maxy) if r.bbox_maxy is not None else None,
                "area_svg": float(r.area_svg) if r.area_svg is not None else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取几何明细失败: {str(e)}",
        )

