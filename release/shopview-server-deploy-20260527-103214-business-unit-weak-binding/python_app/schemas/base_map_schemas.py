"""
base_maps 静态底图表 - Pydantic 模型
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class BaseMapBase(BaseModel):
    floor_id: int
    base_map_code: str
    file_url: str
    svg_viewbox: Optional[str] = None
    svg_width: Optional[float] = None
    svg_height: Optional[float] = None
    is_active: bool = False


class BaseMapCreate(BaseMapBase):
    pass


class BaseMapUpdate(BaseModel):
    base_map_code: Optional[str] = None
    svg_viewbox: Optional[str] = None
    svg_width: Optional[float] = None
    svg_height: Optional[float] = None
    is_active: Optional[bool] = None


class BaseMap(BaseMapBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
