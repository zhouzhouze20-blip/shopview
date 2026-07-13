from __future__ import annotations

from tempfile import SpooledTemporaryFile
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .od0002_report import EXCLUDED_DEPARTMENT_CODES


BLUE = "4472C4"
WHITE = "FFFFFF"
TOTAL_FILL = "D9EAF7"
THIN = Side(style="thin", color="B7B7B7")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

DETAIL_COLUMNS = (
    ("机构", "store_name", "text"),
    ("部门", "department_name", "text"),
    ("柜组编码", "group_code", "text"),
    ("柜组名称", "group_name", "text"),
    ("面积", "area", "decimal"),
    ("楼层", "floor_code", "text"),
    ("一级编码", "level1_code", "classification"),
    ("一级名称", "level1_name", "classification"),
    ("二级编码", "level2_code", "classification"),
    ("二级名称", "level2_name", "classification"),
    ("等级", "grade_label", "classification"),
    ("数量", "quantity", "quantity"),
    ("销售收入", "sales_amount", "money"),
    ("含税成本", "tax_cost", "money"),
    ("毛利", "profit", "money"),
    ("消费次数", "ticket_count", "integer"),
    ("客单价", "average_ticket", "money"),
    ("会员销售", "member_sales", "money"),
    ("储值卡销售", "stored_card_sales", "money"),
)


def _date_text(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _safe_excel_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def _cell_value(row: dict[str, Any], key: str, kind: str) -> Any:
    value = row.get(key)
    if kind == "classification" and (value is None or not str(value).strip()):
        value = "未匹配"
    if kind in ("text", "classification"):
        return _safe_excel_text(value)
    if value is None:
        return None
    if kind == "integer":
        return int(value)
    return float(value)


def _number_format(kind: str) -> str | None:
    if kind in ("decimal", "money"):
        return "0.00"
    if kind == "quantity":
        return "0.####"
    if kind == "integer":
        return "0"
    return None


def _style_header(cell) -> None:
    cell.fill = PatternFill("solid", fgColor=BLUE)
    cell.font = Font(color=WHITE, bold=True)
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = BORDER


def _write_detail_sheet(sheet, report: dict[str, Any]) -> None:
    final_column = get_column_letter(len(DETAIL_COLUMNS))
    dates = report.get("dates", {})

    sheet.merge_cells(f"A1:{final_column}1")
    sheet["A1"] = "HDYY01柜组经营分析表"
    sheet["A1"].font = Font(size=16, bold=True)
    sheet["A1"].alignment = Alignment(horizontal="center", vertical="center")

    sheet.merge_cells(f"A2:{final_column}2")
    sheet["A2"] = (
        f"日期：{_date_text(dates.get('start_date'))} 至 "
        f"{_date_text(dates.get('end_date'))}；金额单位：元；面积单位：平方米"
    )
    sheet["A2"].alignment = Alignment(horizontal="center")

    selected_store = report.get("selected_store") or "全部"
    selected_department = report.get("selected_department") or "全部"
    sheet.merge_cells(f"A3:{final_column}3")
    sheet["A3"] = f"筛选：机构 {selected_store}；部门 {selected_department}"

    for column, (label, _key, _kind) in enumerate(DETAIL_COLUMNS, 1):
        cell = sheet.cell(4, column, label)
        _style_header(cell)

    row_number = 5
    for row in report.get("rows", []):
        for column, (_label, key, kind) in enumerate(DETAIL_COLUMNS, 1):
            cell = sheet.cell(row_number, column, _cell_value(row, key, kind))
            cell.border = BORDER
            number_format = _number_format(kind)
            if number_format is not None:
                cell.number_format = number_format
        row_number += 1

    total = report.get("total", {})
    total_values = {
        "quantity": total.get("quantity", 0),
        "sales_amount": total.get("sales_amount", 0),
        "tax_cost": total.get("tax_cost", 0),
        "profit": total.get("profit", 0),
        "ticket_count": total.get("ticket_count", 0),
        "average_ticket": total.get("average_ticket"),
        "member_sales": total.get("member_sales", 0),
        "stored_card_sales": total.get("stored_card_sales", 0),
    }
    for column, (_label, key, kind) in enumerate(DETAIL_COLUMNS, 1):
        value = "合计" if column == 1 else total_values.get(key)
        if key in total_values and value is not None:
            value = _cell_value(total_values, key, kind)
        cell = sheet.cell(row_number, column, value)
        cell.border = BORDER
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor=TOTAL_FILL)
        number_format = _number_format(kind)
        if number_format is not None:
            cell.number_format = number_format

    last_data_row = max(4, row_number - 1)
    sheet.auto_filter.ref = f"A4:{final_column}{last_data_row}"
    sheet.freeze_panes = "A5"
    sheet.row_dimensions[1].height = 26
    sheet.row_dimensions[4].height = 28

    widths = (18, 20, 15, 22, 12, 10, 13, 16, 13, 16, 10, 13, 15, 15, 15, 13, 15, 15, 16)
    for index, width in enumerate(widths, 1):
        sheet.column_dimensions[get_column_letter(index)].width = width


def _write_notes_sheet(sheet, report: dict[str, Any]) -> None:
    sheet["A1"] = "项目"
    sheet["B1"] = "说明"
    for cell in sheet[1]:
        _style_header(cell)

    excluded = "、".join(sorted(EXCLUDED_DEPARTMENT_CODES))
    scope = report.get("scope_description") or "当前用户权限范围：以系统数据权限为准"
    sheet["A2"] = "HDYY01 口径"
    sheet["B2"] = (
        "销售日期取 sglhsrq；销售收入取 sglxssr，金额单位为元；"
        "含税成本取 sgln13+sgln14-sglsupzk；毛利取 sgln2；"
        "储值卡销售取 sglfcard；会员销售以 salehead.hykh 非空识别；"
        "退货按带符号金额计入；仅小票净销售额 > 0 时计入消费次数；"
        "客单价 = 带符号销售额 / 正向消费次数；排除 sglwmid=5；"
        f"排除部门编码：{excluded}；{scope}；"
        "分类层级使用 manaframe.mfchr2 关联 mana_brand_hierarchy，按编码层级关联；"
        "分类缺失显示未匹配。"
    )
    sheet["A2"].border = BORDER
    sheet["B2"].border = BORDER
    sheet["A2"].alignment = Alignment(vertical="top")
    sheet["B2"].alignment = Alignment(wrap_text=True, vertical="top")
    sheet.column_dimensions["A"].width = 20
    sheet.column_dimensions["B"].width = 120
    sheet.row_dimensions[2].height = 100


def _build_hdyy01_workbook(report: dict[str, Any]) -> Workbook:
    workbook = Workbook()
    detail = workbook.active
    detail.title = "明细"
    _write_detail_sheet(detail, report)
    _write_notes_sheet(workbook.create_sheet("报表说明"), report)
    return workbook


def build_hdyy01_workbook_file(report: dict[str, Any]) -> SpooledTemporaryFile:
    """Build a seeked temporary XLSX file suitable for chunked streaming."""
    output = SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b")
    try:
        _build_hdyy01_workbook(report).save(output)
        output.seek(0)
        return output
    except Exception:
        output.close()
        raise


def build_hdyy01_workbook(report: dict[str, Any]) -> bytes:
    """Build the HDYY01 workbook as bytes for compatibility and tests."""
    output = build_hdyy01_workbook_file(report)
    try:
        return output.read()
    finally:
        output.close()
