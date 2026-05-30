"""
楼层字典表（floors）Pydantic 模型：building_code + floor_code 唯一，用于全局楼层定义界面。
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class FloorDictBase(BaseModel):
    store_id: Optional[str] = None  # 门店ID（字符串）
    building_code: str = "DEFAULT"
    floor_code: str  # 如 B1 / 1F / 2F
    name: str  # 楼层显示名称
    building_area: Optional[float] = None  # 建筑面积（平方米）
    sort_no: int = 0


class FloorDictCreate(FloorDictBase):
    pass


class FloorDictUpdate(BaseModel):
    store_id: Optional[str] = None
    building_code: Optional[str] = None
    floor_code: Optional[str] = None
    name: Optional[str] = None
    building_area: Optional[float] = None
    sort_no: Optional[int] = None


class FloorDict(FloorDictBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
