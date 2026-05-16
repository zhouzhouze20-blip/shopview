"""
百货柜位管理系统 - 柜位图版本 API（public.unit_map_versions）

围绕 unit_map_versions 表提供：
- 列表查询（按楼层/底图过滤）
- 创建版本（若 is_active=true，会自动保证同楼层唯一 active）
- 单独激活某个版本
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
import xml.etree.ElementTree as ET
import re

from models.database import get_db
from routers.authz import require_permission_dependency
from schemas.unit_map_version_schemas import UnitMapVersionCreate, UnitMapVersionUpdate


router = APIRouter(
  prefix="/api/unit-map-versions",
  tags=["unit-map-versions"],
)


_NUM_RE = re.compile(r"[-+]?(?:\d+\.\d+|\d+|\.\d+)(?:[eE][-+]?\d+)?")
_TRANSFORM_RE = re.compile(r"([a-zA-Z]+)\s*\(([^)]*)\)")


def _matrix_multiply(m1: tuple[float, float, float, float, float, float], m2: tuple[float, float, float, float, float, float]) -> tuple[float, float, float, float, float, float]:
  """2D 仿射矩阵相乘（SVG matrix(a b c d e f) 形式）。"""
  a1, b1, c1, d1, e1, f1 = m1
  a2, b2, c2, d2, e2, f2 = m2
  return (
    a1 * a2 + c1 * b2,
    b1 * a2 + d1 * b2,
    a1 * c2 + c1 * d2,
    b1 * c2 + d1 * d2,
    a1 * e2 + c1 * f2 + e1,
    b1 * e2 + d1 * f2 + f1,
  )


def _parse_transform(transform_text: str) -> tuple[float, float, float, float, float, float]:
  """
  解析 transform 字符串，支持：
  - matrix(a,b,c,d,e,f)
  - translate(tx[,ty])
  - scale(sx[,sy])
  """
  m = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
  for fn, raw_args in _TRANSFORM_RE.findall(transform_text or ""):
    vals = [float(x) for x in _NUM_RE.findall(raw_args)]
    fn_l = fn.lower()
    if fn_l == "matrix" and len(vals) >= 6:
      cur = (vals[0], vals[1], vals[2], vals[3], vals[4], vals[5])
    elif fn_l == "translate" and len(vals) >= 1:
      tx = vals[0]
      ty = vals[1] if len(vals) >= 2 else 0.0
      cur = (1.0, 0.0, 0.0, 1.0, tx, ty)
    elif fn_l == "scale" and len(vals) >= 1:
      sx = vals[0]
      sy = vals[1] if len(vals) >= 2 else sx
      cur = (sx, 0.0, 0.0, sy, 0.0, 0.0)
    else:
      # 暂不支持 rotate/skew，遇到则忽略（保持现有兼容行为）
      continue
    m = _matrix_multiply(m, cur)
  return m


def _fmt_num(n: float) -> str:
  """紧凑数字格式，避免导出 path 过长。"""
  s = f"{n:.6f}".rstrip("0").rstrip(".")
  return "0" if s in {"", "-0"} else s


def _transform_xy(x: float, y: float, sx: float, sy: float, tx: float, ty: float, relative: bool) -> tuple[float, float]:
  if relative:
    return x * sx, y * sy
  return x * sx + tx, y * sy + ty


def _transform_path_d(d: str, matrix: tuple[float, float, float, float, float, float]) -> str:
  """
  将 path d 按仿射变换转换后返回。
  当前支持 scale/translate/matrix 且要求无旋转/错切（b=c=0）；
  对于不支持的矩阵，返回原始 d。
  """
  a, b, c, dd, e, f = matrix
  # 仅处理无旋转/错切：x'=sx*x+tx, y'=sy*y+ty
  if abs(b) > 1e-12 or abs(c) > 1e-12:
    return d
  sx, sy, tx, ty = a, dd, e, f
  if abs(sx - 1.0) < 1e-12 and abs(sy - 1.0) < 1e-12 and abs(tx) < 1e-12 and abs(ty) < 1e-12:
    return d

  tokens = re.findall(r"[A-Za-z]|[-+]?(?:\d+\.\d+|\d+|\.\d+)(?:[eE][-+]?\d+)?", d)
  out: list[str] = []
  i = 0
  cmd = ""

  def take_num() -> float:
    nonlocal i
    if i >= len(tokens):
      raise ValueError("path token 越界")
    v = float(tokens[i])
    i += 1
    return v

  while i < len(tokens):
    t = tokens[i]
    if re.fullmatch(r"[A-Za-z]", t):
      cmd = t
      out.append(cmd)
      i += 1
      if cmd in "Zz":
        continue
    elif not cmd:
      # 非法 path，保留原文
      return d

    rel = cmd.islower()
    u = cmd.upper()

    # 根据命令参数组长度循环消费，直到下一个命令字符
    while i < len(tokens) and not re.fullmatch(r"[A-Za-z]", tokens[i]):
      if u in ("M", "L", "T"):
        x, y = take_num(), take_num()
        x, y = _transform_xy(x, y, sx, sy, tx, ty, rel)
        out.extend([_fmt_num(x), _fmt_num(y)])
      elif u == "H":
        x = take_num()
        x = x * sx if rel else x * sx + tx
        out.append(_fmt_num(x))
      elif u == "V":
        y = take_num()
        y = y * sy if rel else y * sy + ty
        out.append(_fmt_num(y))
      elif u in ("S", "Q"):
        x1, y1, x, y = take_num(), take_num(), take_num(), take_num()
        x1, y1 = _transform_xy(x1, y1, sx, sy, tx, ty, rel)
        x, y = _transform_xy(x, y, sx, sy, tx, ty, rel)
        out.extend([_fmt_num(x1), _fmt_num(y1), _fmt_num(x), _fmt_num(y)])
      elif u == "C":
        x1, y1 = take_num(), take_num()
        x2, y2 = take_num(), take_num()
        x, y = take_num(), take_num()
        x1, y1 = _transform_xy(x1, y1, sx, sy, tx, ty, rel)
        x2, y2 = _transform_xy(x2, y2, sx, sy, tx, ty, rel)
        x, y = _transform_xy(x, y, sx, sy, tx, ty, rel)
        out.extend([_fmt_num(x1), _fmt_num(y1), _fmt_num(x2), _fmt_num(y2), _fmt_num(x), _fmt_num(y)])
      elif u == "A":
        rx, ry = take_num(), take_num()
        rot = take_num()
        laf = int(round(take_num()))
        sf = int(round(take_num()))
        x, y = take_num(), take_num()
        # 简化：缩放时同步放大半径；若镜像缩放，flag 仍按原值保留
        rx = abs(rx * sx)
        ry = abs(ry * sy)
        x, y = _transform_xy(x, y, sx, sy, tx, ty, rel)
        out.extend([_fmt_num(rx), _fmt_num(ry), _fmt_num(rot), str(laf), str(sf), _fmt_num(x), _fmt_num(y)])
      else:
        # 未覆盖命令，返回原文避免误改
        return d

      # M/m 后续隐式按 L/l 处理（SVG 规范）
      if u == "M":
        cmd = "l" if rel else "L"
        u = cmd.upper()
        out.append(cmd)
    # 删除可能多余的命令拼接
    if out and out[-1] in {"L", "l"} and (i >= len(tokens) or re.fullmatch(r"[A-Za-z]", tokens[i])):
      out.pop()

  return " ".join(out)


def _collect_paths_with_transform(el: ET.Element, inherited_matrix: tuple[float, float, float, float, float, float], result: list[tuple[str, str]]) -> None:
  """递归收集 path，并将父级 transform 累积到 d 上。"""
  own_transform = _parse_transform((el.attrib.get("transform") or "").strip())
  matrix = _matrix_multiply(inherited_matrix, own_transform)

  if el.tag.endswith("path"):
    el_id = (el.attrib.get("id") or "").strip()
    d = (el.attrib.get("d") or "").strip()
    if el_id and d:
      result.append((el_id, _transform_path_d(d, matrix)))

  for child in list(el):
    _collect_paths_with_transform(child, matrix, result)


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
  """柜位图版本已统一使用 public.floors.id。"""
  return [int(floor_id)]


def _ensure_alignment_table(db: Session) -> None:
  """确保版本对齐参数表存在。"""
  db.execute(
    text(
      """
      CREATE TABLE IF NOT EXISTS unit_map_alignments (
        version_id BIGINT PRIMARY KEY REFERENCES unit_map_versions(id) ON DELETE CASCADE,
        dx NUMERIC(14, 4) NOT NULL DEFAULT 0,
        dy NUMERIC(14, 4) NOT NULL DEFAULT 0,
        sx NUMERIC(14, 6) NOT NULL DEFAULT 1,
        sy NUMERIC(14, 6) NOT NULL DEFAULT 1,
        rotate NUMERIC(14, 6) NOT NULL DEFAULT 0,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      )
      """
    )
  )
  db.commit()


@router.get("")
@router.get("/")
async def list_unit_map_versions(
  floor_id: Optional[int] = Query(None, description="按楼层ID筛选"),
  base_map_id: Optional[int] = Query(None, description="按底图ID筛选"),
  skip: int = 0,
  limit: int = 200,
  db: Session = Depends(get_db),
):
  """
  获取柜位图版本列表。

  - 支持按 floor_id / base_map_id 过滤
  - 默认按创建时间倒序
  """
  try:
    sql = """
      SELECT
        id, floor_id, base_map_id, version_code,
        is_active, change_note, created_at
      FROM unit_map_versions
      WHERE 1=1
    """
    params: dict = {"skip": skip, "limit": limit}
    if floor_id is not None:
      sql += " AND floor_id = ANY(:floor_ids)"
      params["floor_ids"] = _expand_floor_filter_ids(db, floor_id)
    if base_map_id is not None:
      sql += " AND base_map_id = :base_map_id"
      params["base_map_id"] = base_map_id
    sql += " ORDER BY created_at DESC NULLS LAST, id DESC LIMIT :limit OFFSET :skip"

    rows = db.execute(text(sql), params).fetchall()
    return [
      {
        "id": r.id,
        "floor_id": r.floor_id,
        "base_map_id": r.base_map_id,
        "version_code": r.version_code,
        "is_active": bool(r.is_active),
        "change_note": r.change_note,
        "created_at": r.created_at.isoformat() if r.created_at else None,
      }
      for r in rows
    ]
  except Exception as e:
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=f"获取柜位图版本失败: {str(e)}",
    )


@router.post("")
@router.post("/")
async def create_unit_map_version(
  body: UnitMapVersionCreate,
  db: Session = Depends(get_db),
  _=Depends(require_permission_dependency("unit_map_version.create")),
):
  """
  创建柜位图版本记录。

  - 校验 floor_id / base_map_id 存在
  - version_code 全局唯一
  - 若 is_active=true，同楼层其它版本自动置为非 active
  """
  try:
    # 检查底图，并读取其 floor_id（以底图所属楼层为准，避免 floors/store_floors 双表 ID 不一致）
    base_map_row = db.execute(
      text("SELECT id, floor_id FROM base_maps WHERE id = :id"),
      {"id": body.base_map_id},
    ).fetchone()
    if not base_map_row:
      raise HTTPException(status_code=400, detail="base_map_id 不存在")
    resolved_floor_id = int(base_map_row.floor_id)

    # 检查版本编码唯一
    exists = db.execute(
      text("SELECT 1 FROM unit_map_versions WHERE version_code = :code"),
      {"code": body.version_code},
    ).fetchone()
    if exists:
      raise HTTPException(status_code=400, detail="version_code 已存在")

    # 若设为 active，先关闭同楼层其它 active
    if body.is_active:
      db.execute(
        text("UPDATE unit_map_versions SET is_active = false WHERE floor_id = :floor_id AND is_active = true"),
        {"floor_id": resolved_floor_id},
      )

    row = db.execute(
      text(
        """
        INSERT INTO unit_map_versions
          (floor_id, base_map_id, version_code, is_active, change_note)
        VALUES
          (:floor_id, :base_map_id, :version_code, :is_active, :change_note)
        RETURNING
          id, floor_id, base_map_id, version_code,
          is_active, change_note, created_at
        """
      ),
      {
        "floor_id": resolved_floor_id,
        "base_map_id": body.base_map_id,
        "version_code": body.version_code,
        "is_active": body.is_active,
        "change_note": body.change_note,
      },
    ).fetchone()
    db.commit()

    return {
      "id": row.id,
      "floor_id": row.floor_id,
      "base_map_id": row.base_map_id,
      "version_code": row.version_code,
      "is_active": bool(row.is_active),
      "change_note": row.change_note,
      "created_at": row.created_at.isoformat() if row.created_at else None,
    }
  except HTTPException:
    raise
  except Exception as e:
    db.rollback()
    raise HTTPException(status_code=500, detail=f"创建柜位图版本失败: {str(e)}")


@router.post("/{version_id}/activate")
async def activate_unit_map_version(
  version_id: int,
  db: Session = Depends(get_db),
  _=Depends(require_permission_dependency("unit_map_version.edit")),
):
  """将指定版本设为该楼层当前版本（同楼层其它版本自动取消 active）。"""
  try:
    row = db.execute(
      text("SELECT id, floor_id FROM unit_map_versions WHERE id = :id"),
      {"id": version_id},
    ).fetchone()
    if not row:
      raise HTTPException(status_code=404, detail="版本不存在")

    floor_id = row.floor_id
    db.execute(
      text("UPDATE unit_map_versions SET is_active = false WHERE floor_id = :floor_id AND is_active = true"),
      {"floor_id": floor_id},
    )
    db.execute(
      text("UPDATE unit_map_versions SET is_active = true WHERE id = :id"),
      {"id": version_id},
    )
    db.commit()
    return {"message": "已设为当前柜位图版本", "id": version_id}
  except HTTPException:
    raise
  except Exception as e:
    db.rollback()
    raise HTTPException(status_code=500, detail=f"设置 active 失败: {str(e)}")


@router.put("/{version_id}")
async def update_unit_map_version(
  version_id: int,
  body: UnitMapVersionUpdate,
  db: Session = Depends(get_db),
  _=Depends(require_permission_dependency("unit_map_version.edit")),
):
  """更新柜位图版本元数据。"""
  try:
    existing = db.execute(
      text(
        """
        SELECT id, floor_id, base_map_id, version_code, is_active, change_note
        FROM unit_map_versions
        WHERE id = :id
        """
      ),
      {"id": version_id},
    ).fetchone()
    if not existing:
      raise HTTPException(status_code=404, detail="版本不存在")

    updates = body.dict(exclude_unset=True)
    target_base_map_id = updates.get("base_map_id", existing.base_map_id)
    base_map_row = db.execute(
      text("SELECT id, floor_id FROM base_maps WHERE id = :id"),
      {"id": target_base_map_id},
    ).fetchone()
    if not base_map_row:
      raise HTTPException(status_code=400, detail="base_map_id 不存在")

    next_floor_id = int(base_map_row.floor_id)
    next_version_code = updates.get("version_code", existing.version_code)
    if next_version_code is not None:
      next_version_code = next_version_code.strip()
    if not next_version_code:
      raise HTTPException(status_code=400, detail="version_code 不能为空")

    version_exists = db.execute(
      text("SELECT 1 FROM unit_map_versions WHERE version_code = :code AND id <> :id"),
      {"code": next_version_code, "id": version_id},
    ).fetchone()
    if version_exists:
      raise HTTPException(status_code=400, detail="version_code 已存在")

    next_is_active = updates.get("is_active", bool(existing.is_active))
    if next_is_active:
      db.execute(
        text("UPDATE unit_map_versions SET is_active = false WHERE floor_id = :floor_id AND id <> :id"),
        {"floor_id": next_floor_id, "id": version_id},
      )

    row = db.execute(
      text(
        """
        UPDATE unit_map_versions
        SET
          floor_id = :floor_id,
          base_map_id = :base_map_id,
          version_code = :version_code,
          is_active = :is_active,
          change_note = :change_note
        WHERE id = :id
        RETURNING
          id, floor_id, base_map_id, version_code,
          is_active, change_note, created_at
        """
      ),
      {
        "id": version_id,
        "floor_id": next_floor_id,
        "base_map_id": target_base_map_id,
        "version_code": next_version_code,
        "is_active": next_is_active,
        "change_note": updates.get("change_note", existing.change_note),
      },
    ).fetchone()
    db.commit()

    return {
      "id": row.id,
      "floor_id": row.floor_id,
      "base_map_id": row.base_map_id,
      "version_code": row.version_code,
      "is_active": bool(row.is_active),
      "change_note": row.change_note,
      "created_at": row.created_at.isoformat() if row.created_at else None,
    }
  except HTTPException:
    raise
  except Exception as e:
    db.rollback()
    raise HTTPException(status_code=500, detail=f"更新柜位图版本失败: {str(e)}")


@router.delete("/{version_id}")
async def delete_unit_map_version(
  version_id: int,
  db: Session = Depends(get_db),
  _=Depends(require_permission_dependency("unit_map_version.delete")),
):
  """删除柜位图版本，并清理关联几何数据。"""
  try:
    existing = db.execute(
      text("SELECT id FROM unit_map_versions WHERE id = :id"),
      {"id": version_id},
    ).fetchone()
    if not existing:
      raise HTTPException(status_code=404, detail="版本不存在")

    _ensure_alignment_table(db)
    db.execute(text("DELETE FROM geo_elements WHERE version_id = :id"), {"id": version_id})
    db.execute(text("DELETE FROM unit_map_alignments WHERE version_id = :id"), {"id": version_id})
    if _table_exists(db, "spatial_evolution_log"):
      db.execute(
        text("DELETE FROM spatial_evolution_log WHERE from_version_id = :id OR to_version_id = :id"),
        {"id": version_id},
      )
    db.execute(text("DELETE FROM unit_map_versions WHERE id = :id"), {"id": version_id})
    db.commit()
    return {"message": "柜位图版本已删除", "id": version_id}
  except HTTPException:
    raise
  except Exception as e:
    db.rollback()
    raise HTTPException(status_code=500, detail=f"删除柜位图版本失败: {str(e)}")


@router.put("/{version_id}/import-svg")
async def import_svg_to_version(
  version_id: int,
  file: UploadFile = File(...),
  db: Session = Depends(get_db),
  _=Depends(require_permission_dependency("unit_map_version.edit")),
):
  """
  导入柜位版本 SVG（批量版）：
  - 解析 SVG 中所有带 id 与 d 的 <path>
  - 临时规则：unit_code = path 的 id（如 path42）
  - 自动 upsert business_units + geo_elements
  """
  try:
    # 1) 获取版本信息
    ver = db.execute(
      text("SELECT id, floor_id FROM unit_map_versions WHERE id = :id"),
      {"id": version_id},
    ).fetchone()
    if not ver:
      raise HTTPException(status_code=404, detail="版本不存在")

    floor_id = ver.floor_id

    # 2) 读取并解析 SVG
    raw = await file.read()
    try:
      root = ET.fromstring(raw)
    except Exception as e:
      raise HTTPException(status_code=400, detail=f"SVG 解析失败: {str(e)}")

    # 3) 收集所有 path（兼容 SVG namespace + 父级 transform）
    paths: list[tuple[str, str]] = []
    _collect_paths_with_transform(root, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0), paths)
    skipped = 0

    if not paths:
      raise HTTPException(status_code=400, detail="SVG 中未找到可导入的 path（需要同时具备 id 与 d）")

    created_units = 0
    created_geos = 0
    updated_geos = 0

    # 4) 逐个 upsert（简单可靠；后续需要性能可再批量化）
    for (svg_id, d) in paths:
      unit_code = svg_id  # 临时规则：unit_code = path id

      bu = db.execute(
        text("SELECT id FROM business_units WHERE floor_id = :floor_id AND unit_code = :unit_code"),
        {"floor_id": floor_id, "unit_code": unit_code},
      ).fetchone()
      if bu:
        unit_id = bu.id
      else:
        bu_row = db.execute(
          text(
            """
            INSERT INTO business_units (floor_id, unit_code)
            VALUES (:floor_id, :unit_code)
            RETURNING id
            """
          ),
          {"floor_id": floor_id, "unit_code": unit_code},
        ).fetchone()
        unit_id = bu_row.id
        created_units += 1

      existing_geo = db.execute(
        text("SELECT id FROM geo_elements WHERE version_id = :version_id AND unit_id = :unit_id"),
        {"version_id": version_id, "unit_id": unit_id},
      ).fetchone()
      if existing_geo:
        db.execute(
          text(
            """
            UPDATE geo_elements
            SET svg_element_id = :svg_element_id, path_data = :path_data
            WHERE id = :id
            """
          ),
          {"svg_element_id": svg_id, "path_data": d, "id": existing_geo.id},
        )
        updated_geos += 1
      else:
        db.execute(
          text(
            """
            INSERT INTO geo_elements (version_id, unit_id, svg_element_id, path_data)
            VALUES (:version_id, :unit_id, :svg_element_id, :path_data)
            """
          ),
          {"version_id": version_id, "unit_id": unit_id, "svg_element_id": svg_id, "path_data": d},
        )
        created_geos += 1

    db.commit()
    return {
      "message": "导入成功",
      "rule": "unit_code = path.id（临时规则）",
      "version_id": version_id,
      "floor_id": floor_id,
      "paths_total": len(paths),
      "paths_skipped": skipped,
      "business_units_created": created_units,
      "geo_elements_created": created_geos,
      "geo_elements_updated": updated_geos,
    }
  except HTTPException:
    raise
  except Exception as e:
    db.rollback()
    raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.get("/{version_id}/align-transform")
async def get_align_transform(
  version_id: int,
  db: Session = Depends(get_db),
):
  """
  获取柜位图版本的微调参数（平移/缩放/旋转）。
  若未设置，返回默认值。
  """
  try:
    ver = db.execute(
      text("SELECT id FROM unit_map_versions WHERE id = :id"),
      {"id": version_id},
    ).fetchone()
    if not ver:
      raise HTTPException(status_code=404, detail="版本不存在")

    _ensure_alignment_table(db)
    row = db.execute(
      text(
        """
        SELECT version_id, dx, dy, sx, sy, rotate, updated_at
        FROM unit_map_alignments
        WHERE version_id = :version_id
        """
      ),
      {"version_id": version_id},
    ).fetchone()
    if not row:
      return {
        "version_id": version_id,
        "dx": 0.0,
        "dy": 0.0,
        "sx": 1.0,
        "sy": 1.0,
        "rotate": 0.0,
        "updated_at": None,
      }
    return {
      "version_id": row.version_id,
      "dx": float(row.dx),
      "dy": float(row.dy),
      "sx": float(row.sx),
      "sy": float(row.sy),
      "rotate": float(row.rotate),
      "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"获取对齐参数失败: {str(e)}")


@router.put("/{version_id}/align-transform")
async def save_align_transform(
  version_id: int,
  body: dict,
  db: Session = Depends(get_db),
  _=Depends(require_permission_dependency("unit_map_version.edit")),
):
  """
  保存柜位图版本微调参数。
  body 支持字段：dx, dy, sx, sy, rotate
  """
  try:
    ver = db.execute(
      text("SELECT id FROM unit_map_versions WHERE id = :id"),
      {"id": version_id},
    ).fetchone()
    if not ver:
      raise HTTPException(status_code=404, detail="版本不存在")

    dx = float(body.get("dx", 0))
    dy = float(body.get("dy", 0))
    sx = float(body.get("sx", 1))
    sy = float(body.get("sy", 1))
    rotate = float(body.get("rotate", 0))
    if sx <= 0 or sy <= 0:
      raise HTTPException(status_code=400, detail="sx/sy 必须大于 0")

    _ensure_alignment_table(db)
    row = db.execute(
      text(
        """
        INSERT INTO unit_map_alignments (version_id, dx, dy, sx, sy, rotate, updated_at)
        VALUES (:version_id, :dx, :dy, :sx, :sy, :rotate, NOW())
        ON CONFLICT (version_id)
        DO UPDATE SET
          dx = EXCLUDED.dx,
          dy = EXCLUDED.dy,
          sx = EXCLUDED.sx,
          sy = EXCLUDED.sy,
          rotate = EXCLUDED.rotate,
          updated_at = NOW()
        RETURNING version_id, dx, dy, sx, sy, rotate, updated_at
        """
      ),
      {
        "version_id": version_id,
        "dx": dx,
        "dy": dy,
        "sx": sx,
        "sy": sy,
        "rotate": rotate,
      },
    ).fetchone()
    db.commit()
    return {
      "version_id": row.version_id,
      "dx": float(row.dx),
      "dy": float(row.dy),
      "sx": float(row.sx),
      "sy": float(row.sy),
      "rotate": float(row.rotate),
      "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
  except HTTPException:
    raise
  except Exception as e:
    db.rollback()
    raise HTTPException(status_code=500, detail=f"保存对齐参数失败: {str(e)}")
