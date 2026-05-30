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
                  g.id,
                  g.version_id,
                  g.unit_id,
                  bu.unit_code,
                  bu.floor_id,
                  bu.status AS unit_status,
                  bu.manual_area AS unit_manual_area,
                  bu.parent_unit_id AS unit_parent_unit_id,
                  g.svg_element_id,
                  g.path_data,
                  g.centroid_x,
                  g.centroid_y,
                  g.bbox_minx,
                  g.bbox_miny,
                  g.bbox_maxx,
                  g.bbox_maxy,
                  g.area_svg,
                  g.created_at
                FROM geo_elements g
                LEFT JOIN business_units bu ON bu.id = g.unit_id
                WHERE g.version_id = :version_id
                ORDER BY g.id ASC
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
                "unit_code": r.unit_code,
                "floor_id": r.floor_id,
                "unit_status": r.unit_status,
                "unit_manual_area": float(r.unit_manual_area) if r.unit_manual_area is not None else None,
                "unit_parent_unit_id": r.unit_parent_unit_id,
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
