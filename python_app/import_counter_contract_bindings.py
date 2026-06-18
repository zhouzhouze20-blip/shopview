#!/usr/bin/env python3
"""
Import shop unit / counter group / contract bindings from the cabinet contract Excel.

Default mode is dry-run. Add --apply to write rows into business_unit_binding.
"""

from __future__ import annotations

import argparse
import sys
import re
from collections import defaultdict
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any
from zipfile import ZipFile
from xml.etree import ElementTree as ET

xlrd = None

from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parent))

from models.database import SessionLocal


DEFAULT_SOURCE_PREFIX = "柜位合同1-5.xls"

SHEET_STORE_KEYWORDS = {
    "购物中心": "601",
    "百货大楼": "602",
    "新世纪": "603",
}

XML_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "office_rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


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


def _store_code_from_sheet(sheet_name: str) -> str:
    for keyword, store_code in SHEET_STORE_KEYWORDS.items():
        if keyword in sheet_name:
            return store_code
    return ""


def _unit_code_candidates(value: str) -> list[str]:
    normalized = _normalize_code(value)
    if not normalized:
        return []
    candidates = [normalized]
    for part in re.split(r"[/、,，]+", normalized):
        if part and part not in candidates:
            candidates.append(part)
    return candidates


def _load_shared_strings(workbook: ZipFile) -> list[str]:
    try:
        root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
    except KeyError:
        return []

    strings: list[str] = []
    for item in root.findall("main:si", XML_NS):
        pieces = [node.text or "" for node in item.findall(".//main:t", XML_NS)]
        strings.append("".join(pieces))
    return strings


def _load_xlsx_sheets(path: Path) -> list[tuple[str, list[list[Any]]]]:
    with ZipFile(path) as workbook:
        shared_strings = _load_shared_strings(workbook)

        relationships_root = ET.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
        relationship_targets = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in relationships_root.findall("rel:Relationship", XML_NS)
        }

        workbook_root = ET.fromstring(workbook.read("xl/workbook.xml"))
        sheets: list[tuple[str, list[list[Any]]]] = []
        for sheet in workbook_root.findall("main:sheets/main:sheet", XML_NS):
            sheet_name = sheet.attrib["name"]
            relationship_id = sheet.attrib[f"{{{XML_NS['office_rel']}}}id"]
            target = relationship_targets[relationship_id]
            sheet_path = f"xl/{target}" if not target.startswith("/") else target.lstrip("/")
            sheet_root = ET.fromstring(workbook.read(sheet_path))

            rows: list[list[Any]] = []
            for row in sheet_root.findall(".//main:sheetData/main:row", XML_NS):
                values: list[Any] = []
                for cell in row.findall("main:c", XML_NS):
                    ref = cell.attrib.get("r", "")
                    col_letters = re.sub(r"\d+", "", ref)
                    if col_letters:
                        col_index = 0
                        for letter in col_letters:
                            col_index = col_index * 26 + ord(letter.upper()) - ord("A") + 1
                        while len(values) < col_index - 1:
                            values.append(None)

                    value_node = cell.find("main:v", XML_NS)
                    if value_node is None:
                        values.append("")
                        continue

                    raw_value = value_node.text or ""
                    if cell.attrib.get("t") == "s":
                        values.append(shared_strings[int(raw_value)] if raw_value else "")
                    else:
                        values.append(raw_value)
                rows.append(values)
            sheets.append((sheet_name, rows))
        return sheets


def _first_cell(header_index: dict[str, int], row: list[Any], *headers: str) -> Any:
    for header in headers:
        col_index = header_index.get(header)
        if col_index is not None and col_index < len(row):
            return row[col_index]
    return None


def _row_from_values(sheet_name: str, header_index: dict[str, int], row: list[Any]) -> BindingRow | None:
    unit_code = _text(_first_cell(header_index, row, "柜位编号"))
    group_code = _text(_first_cell(header_index, row, "柜组", "柜组编码"))
    contract_id = _contract_id(_first_cell(header_index, row, "富基合同编号"))
    if not unit_code and not group_code and not contract_id:
        return None
    return BindingRow(
        sheet_name=sheet_name,
        floor_text=_text(_first_cell(header_index, row, "楼层")),
        unit_code=unit_code,
        group_code=group_code,
        group_name=_text(_first_cell(header_index, row, "柜组名称")),
        contract_id=contract_id,
        oa_contract_id=_text(_first_cell(header_index, row, "OA合同编号")),
        area=_decimal(_first_cell(header_index, row, "面积(㎡)")),
        unit_type=_text(_first_cell(header_index, row, "柜位性质")),
        drawing_area=_decimal(_first_cell(header_index, row, "图纸面积")),
    )


def load_rows(path: str | Path) -> list[BindingRow]:
    path = Path(path)
    rows: list[BindingRow] = []
    if path.suffix.lower() == ".xlsx":
        for sheet_name, values in _load_xlsx_sheets(path):
            if len(values) < 2:
                continue
            headers = [_text(value) for value in values[0]]
            header_index = {header: index for index, header in enumerate(headers) if header}
            for row in values[1:]:
                binding_row = _row_from_values(sheet_name, header_index, row)
                if binding_row is not None:
                    rows.append(binding_row)
        return rows

    global xlrd
    if xlrd is None:
        try:
            import xlrd as _xlrd
        except ImportError:
            print("Missing dependency: xlrd. Run `pip install -r python_requirements.txt` first.", file=sys.stderr)
            raise
        xlrd = _xlrd

    workbook = xlrd.open_workbook(str(path))
    for sheet in workbook.sheets():
        if sheet.nrows < 2:
            continue
        headers = [_text(sheet.cell_value(0, col)) for col in range(sheet.ncols)]
        header_index = {header: index for index, header in enumerate(headers) if header}
        for row_index in range(1, sheet.nrows):
            row = [sheet.cell_value(row_index, col) for col in range(sheet.ncols)]
            binding_row = _row_from_values(sheet.name, header_index, row)
            if binding_row is not None:
                rows.append(binding_row)
    return rows


def _binding_remark(row: BindingRow, source_prefix: str = DEFAULT_SOURCE_PREFIX) -> str:
    parts = [
        source_prefix,
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


def import_bindings(
    path: str | Path,
    apply: bool = False,
    replace_all: bool = False,
    replace_source: bool = False,
    skip_existing: bool = False,
) -> int:
    path = Path(path)
    source_prefix = path.name or DEFAULT_SOURCE_PREFIX
    source_rows = load_rows(path)
    stats = Counter()
    seen_keys: set[tuple[int, str]] = set()

    db = SessionLocal()
    try:
        unit_rows = db.execute(
            text(
                """
                SELECT
                    bu.id,
                    bu.unit_code,
                    COALESCE(s.store_code, f.store_code) AS store_code
                FROM business_units bu
                LEFT JOIN stores s ON s.store_id = bu.store_id
                LEFT JOIN floors f ON f.id = bu.floor_id
                """
            )
        ).mappings().all()
        unit_by_store_and_code: dict[tuple[str, str], list[int]] = defaultdict(list)
        for unit in unit_rows:
            store_code = _text(unit["store_code"])
            unit_code = _normalize_code(unit["unit_code"])
            if store_code and unit_code:
                unit_by_store_and_code[(store_code, unit_code)].append(int(unit["id"]))

        group_rows = db.execute(text("SELECT group_id, group_code FROM counter_groups")).mappings().all()
        group_by_code = {_normalize_code(row["group_code"]): int(row["group_id"]) for row in group_rows}

        if apply and replace_all:
            deleted = db.execute(text("DELETE FROM business_unit_binding")).rowcount
            stats["deleted_all_rows"] = deleted or 0
        elif apply and replace_source:
            deleted = db.execute(
                text("DELETE FROM business_unit_binding WHERE remark LIKE :source_prefix"),
                {"source_prefix": f"{source_prefix}%"},
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

            store_code = _store_code_from_sheet(row.sheet_name)
            if not store_code:
                stats["missing_sheet_store"] += 1
                continue

            shop_unit_ids: list[int] = []
            for unit_code in _unit_code_candidates(row.unit_code):
                matches = unit_by_store_and_code.get((store_code, unit_code), [])
                if len(matches) == 1:
                    if matches[0] not in shop_unit_ids:
                        shop_unit_ids.append(matches[0])
                elif len(matches) > 1:
                    stats["ambiguous_shop_unit"] += 1

            if not shop_unit_ids:
                stats["unmatched_shop_unit"] += 1
                continue

            counter_group_id = group_by_code.get(_normalize_code(row.group_code)) if row.group_code else None
            if row.group_code and counter_group_id is None:
                stats["unmatched_counter_group"] += 1

            for shop_unit_id in shop_unit_ids:
                dedupe_key = (shop_unit_id, row.contract_id)
                if dedupe_key in seen_keys:
                    stats["duplicate_excel_binding"] += 1
                    continue
                seen_keys.add(dedupe_key)

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
                    "remark": _binding_remark(row, source_prefix),
                }
                if existing:
                    if skip_existing:
                        stats["skipped_existing"] += 1
                        continue
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
        "--replace-all",
        action="store_true",
        help="Delete all existing rows in business_unit_binding before importing.",
    )
    parser.add_argument(
        "--replace-source",
        action="store_true",
        help="Delete previous rows whose remark starts with the source filename before importing.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip existing shop unit + contract bindings instead of updating them.",
    )
    args = parser.parse_args()
    return import_bindings(
        args.excel_path,
        apply=args.apply,
        replace_all=args.replace_all,
        replace_source=args.replace_source,
        skip_existing=args.skip_existing,
    )


if __name__ == "__main__":
    raise SystemExit(main())
