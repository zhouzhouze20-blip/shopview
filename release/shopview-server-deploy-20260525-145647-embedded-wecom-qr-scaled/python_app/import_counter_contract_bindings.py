#!/usr/bin/env python3
"""
Import shop unit / counter group / contract bindings from the cabinet contract Excel.

Default mode is dry-run. Add --apply to write rows into business_unit_binding.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

try:
    import xlrd
except ImportError:
    print("Missing dependency: xlrd. Run `pip install -r python_requirements.txt` first.", file=sys.stderr)
    raise

from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parent))

from models.database import SessionLocal


SOURCE_PREFIX = "柜位合同1-5.xls"


@dataclass(frozen=True)
class BindingRow:
    sheet_name: str
    floor_text: str
    unit_code: str
    group_code: str
    group_name: str
    contract_id: str
    oa_contract_id: str
    area: Decimal | None
    unit_type: str
    drawing_area: Decimal | None


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _decimal(value: Any) -> Decimal | None:
    text_value = _text(value)
    if not text_value:
        return None
    try:
        return Decimal(text_value)
    except Exception:
        return None


def _contract_id(value: Any) -> str:
    text_value = _text(value)
    if not text_value:
        return ""
    if text_value.isdigit() and len(text_value) < 8:
        return text_value.zfill(8)
    return text_value


def _normalize_code(value: str) -> str:
    return "".join(value.upper().split())


def load_rows(path: str | Path) -> list[BindingRow]:
    workbook = xlrd.open_workbook(str(path))
    rows: list[BindingRow] = []
    for sheet in workbook.sheets():
        if sheet.nrows < 2:
            continue
        headers = [_text(sheet.cell_value(0, col)) for col in range(sheet.ncols)]
        header_index = {header: index for index, header in enumerate(headers) if header}

        def cell(row_index: int, header: str) -> Any:
            col_index = header_index.get(header)
            if col_index is None:
                return None
            return sheet.cell_value(row_index, col_index)

        for row_index in range(1, sheet.nrows):
            unit_code = _text(cell(row_index, "柜位编号"))
            group_code = _text(cell(row_index, "柜组"))
            contract_id = _contract_id(cell(row_index, "富基合同编号"))
            if not unit_code and not group_code and not contract_id:
                continue
            rows.append(
                BindingRow(
                    sheet_name=sheet.name,
                    floor_text=_text(cell(row_index, "楼层")),
                    unit_code=unit_code,
                    group_code=group_code,
                    group_name=_text(cell(row_index, "柜组名称")),
                    contract_id=contract_id,
                    oa_contract_id=_text(cell(row_index, "OA合同编号")),
                    area=_decimal(cell(row_index, "面积(㎡)")),
                    unit_type=_text(cell(row_index, "柜位性质")),
                    drawing_area=_decimal(cell(row_index, "图纸面积")),
                )
            )
    return rows


def _binding_remark(row: BindingRow) -> str:
    parts = [
        SOURCE_PREFIX,
        f"sheet={row.sheet_name}",
        f"floor={row.floor_text}",
        f"unit={row.unit_code}",
    ]
    if row.group_code:
        parts.append(f"group={row.group_code}")
    if row.group_name:
        parts.append(f"group_name={row.group_name}")
    if row.oa_contract_id:
        parts.append(f"oa={row.oa_contract_id}")
    if row.unit_type:
        parts.append(f"type={row.unit_type}")
    if row.area is not None:
        parts.append(f"area={row.area}")
    if row.drawing_area is not None:
        parts.append(f"drawing_area={row.drawing_area}")
    return "; ".join(parts)


def import_bindings(path: str | Path, apply: bool = False, replace_source: bool = False) -> int:
    source_rows = load_rows(path)
    stats = Counter()
    seen_keys: set[tuple[int, str]] = set()

    db = SessionLocal()
    try:
        unit_rows = db.execute(text("SELECT id, unit_code FROM business_units")).mappings().all()
        unit_by_code = {_normalize_code(row["unit_code"]): int(row["id"]) for row in unit_rows}

        group_rows = db.execute(text("SELECT group_id, group_code FROM counter_groups")).mappings().all()
        group_by_code = {_normalize_code(row["group_code"]): int(row["group_id"]) for row in group_rows}

        if apply and replace_source:
            deleted = db.execute(
                text("DELETE FROM business_unit_binding WHERE remark LIKE :source_prefix"),
                {"source_prefix": f"{SOURCE_PREFIX}%"},
            ).rowcount
            stats["deleted_source_rows"] = deleted or 0

        for row in source_rows:
            stats["excel_rows"] += 1
            if not row.unit_code:
                stats["missing_unit_code"] += 1
                continue
            if not row.contract_id:
                stats["missing_contract_id"] += 1
                continue

            shop_unit_id = unit_by_code.get(_normalize_code(row.unit_code))
            if not shop_unit_id:
                stats["unmatched_shop_unit"] += 1
                continue

            dedupe_key = (shop_unit_id, row.contract_id)
            if dedupe_key in seen_keys:
                stats["duplicate_excel_binding"] += 1
                continue
            seen_keys.add(dedupe_key)

            counter_group_id = group_by_code.get(_normalize_code(row.group_code)) if row.group_code else None
            if row.group_code and counter_group_id is None:
                stats["unmatched_counter_group"] += 1

            existing = db.execute(
                text(
                    """
                    SELECT id
                    FROM business_unit_binding
                    WHERE shop_unit_id = :shop_unit_id
                      AND upper(trim(contract_id)) = upper(trim(:contract_id))
                    LIMIT 1
                    """
                ),
                {"shop_unit_id": shop_unit_id, "contract_id": row.contract_id},
            ).fetchone()

            values = {
                "shop_unit_id": shop_unit_id,
                "counter_group_id": counter_group_id,
                "contract_id": row.contract_id,
                "brand_id": row.group_name or None,
                "business_type": row.unit_type or None,
                "remark": _binding_remark(row),
            }
            if existing:
                stats["would_update" if not apply else "updated"] += 1
                if apply:
                    db.execute(
                        text(
                            """
                            UPDATE business_unit_binding
                            SET counter_group_id = :counter_group_id,
                                brand_id = :brand_id,
                                business_type = :business_type,
                                status = 'ACTIVE',
                                remark = :remark,
                                updated_at = NOW()
                            WHERE id = :id
                            """
                        ),
                        {**values, "id": existing.id},
                    )
                continue

            stats["would_insert" if not apply else "inserted"] += 1
            if apply:
                db.execute(
                    text(
                        """
                        INSERT INTO business_unit_binding (
                            shop_unit_id,
                            counter_group_id,
                            brand_id,
                            contract_id,
                            business_type,
                            is_primary,
                            status,
                            remark,
                            created_at,
                            updated_at
                        )
                        VALUES (
                            :shop_unit_id,
                            :counter_group_id,
                            :brand_id,
                            :contract_id,
                            :business_type,
                            TRUE,
                            'ACTIVE',
                            :remark,
                            NOW(),
                            NOW()
                        )
                        """
                    ),
                    values,
                )

        if apply:
            db.commit()
        else:
            db.rollback()

        print("Import summary")
        for key, value in sorted(stats.items()):
            print(f"{key}: {value}")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Import shop unit / counter group / contract bindings from Excel.")
    parser.add_argument("excel_path", help="Path to .xls workbook")
    parser.add_argument("--apply", action="store_true", help="Write changes. Default is dry-run.")
    parser.add_argument(
        "--replace-source",
        action="store_true",
        help=f"Delete previous rows whose remark starts with {SOURCE_PREFIX!r} before importing.",
    )
    args = parser.parse_args()
    return import_bindings(args.excel_path, apply=args.apply, replace_source=args.replace_source)


if __name__ == "__main__":
    raise SystemExit(main())
