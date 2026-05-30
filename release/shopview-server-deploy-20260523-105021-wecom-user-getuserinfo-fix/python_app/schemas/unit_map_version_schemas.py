"""
unit_map_versions 柜位图版本表 - Pydantic 模型
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UnitMapVersionBase(BaseModel):
  floor_id: int
  base_map_id: int
  version_code: str
  is_active: bool = False
  change_note: Optional[str] = None


class UnitMapVersionCreate(UnitMapVersionBase):
  pass


class UnitMapVersionUpdate(BaseModel):
  base_map_id: Optional[int] = None
  version_code: Optional[str] = None
  is_active: Optional[bool] = None
  change_note: Optional[str] = None


class UnitMapVersion(UnitMapVersionBase):
  id: int
  created_at: Optional[datetime] = None

  class Config:
    from_attributes = True
