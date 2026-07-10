from __future__ import annotations

from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .od0002_report import EXCLUDED_DEPARTMENT_CODES


SHEETS = (
    ("分店", "stores"),
    ("部门", "departments"),
    ("区域", "areas"),
    ("品类", "categories"),
    ("柜组", "groups"),
    ("楼层", "floors"),
)
BLUE = "4472C4"
WHITE = "FFFFFF"
THIN = Side(style="thin", color="B7B7B7")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def _date_text(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _write_headers(sheet, dimension_name: str) -> None:
    sheet.merge_cells("A5:D5")
    sheet["A5"] = "维度"
    for start, end, label in ((5, 7, "销售收入"), (8, 10, "毛利额"), (11, 13, "毛利率")):
        sheet.merge_cells(start_row=5, start_column=start, end_row=5, end_column=end)
        sheet.cell(5, start).value = label

    identifiers = ("门店编码", "门店名称", f"{dimension_name}编码", f"{dimension_name}名称")
    for column, label in enumerate(identifiers, 1):
        sheet.merge_cells(start_row=6, start_column=column, end_row=7, end_column=column)
        sheet.cell(6, column).value = label
    for group_start in (5, 8, 11):
        for offset, label in enumerate(("本期", "同期", "同比")):
            sheet.cell(6, group_start + offset).value = label
            sheet.cell(7, group_start + offset).value = "万元" if group_start < 11 and offset < 2 else "%"

    for row in range(5, 8):
        for column in range(1, 14):
            cell = sheet.cell(row, column)
            cell.fill = PatternFill("solid", fgColor=BLUE)
            cell.font = Font(color=WHITE, bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = BORDER


def _metric_values(metrics: dict[str, Any]) -> list[Any]:
    return [
        float(metrics.get("sales_current") or 0) / 10000,
        float(metrics.get("sales_prior") or 0) / 10000,
        metrics.get("sales_yoy"),
        float(metrics.get("profit_current") or 0) / 10000,
        float(metrics.get("profit_prior") or 0) / 10000,
        metrics.get("profit_yoy"),
        metrics.get("margin_current"),
        metrics.get("margin_prior"),
        metrics.get("margin_change"),
    ]


def _write_data_row(sheet, row_number: int, values: list[Any], *, total: bool = False) -> None:
    for column, value in enumerate(values, 1):
        cell = sheet.cell(row_number, column, value)
        cell.border = BORDER
        if column in (5, 6, 8, 9):
            cell.number_format = "0.00"
        elif column >= 7:
            cell.number_format = "0.00%"
        if total:
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor="D9EAF7")


def _write_report_sheet(sheet, report: dict[str, Any], label: str, dimension_key: str) -> None:
    dates = report["dates"]
    sheet.merge_cells("A1:M1")
    sheet["A1"] = f"OD0002 门店销售毛利汇总表（{label}）"
    sheet["A1"].font = Font(size=16, bold=True)
    sheet["A1"].alignment = Alignment(horizontal="center")
    sheet.merge_cells("A2:M2")
    sheet["A2"] = f"本期：{_date_text(dates['start_date'])} 至 {_date_text(dates['end_date'])}"
    sheet.merge_cells("A3:M3")
    sheet["A3"] = f"同期：{_date_text(dates['prior_start_date'])} 至 {_date_text(dates['prior_end_date'])}"
    _write_headers(sheet, label)

    row_number = 8
    for row in report.get("dimensions", {}).get(dimension_key, []):
        identifiers = [
            row.get("store_code"), row.get("store_name"),
            row.get("dimension_code"), row.get("dimension_name"),
        ]
        _write_data_row(sheet, row_number, identifiers + _metric_values(row.get("metrics", {})))
        row_number += 1
    total = report.get("totals", {}).get(dimension_key, {})
    _write_data_row(sheet, row_number, ["合计", None, None, None] + _metric_values(total), total=True)

    sheet.freeze_panes = "A8"
    widths = (14, 18, 16, 24) + (14,) * 9
    for index, width in enumerate(widths, 1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.auto_filter.ref = f"A7:M{row_number}"


def _write_notes(sheet, report: dict[str, Any]) -> None:
    sheet["A1"] = "项目"
    sheet["B1"] = "说明"
    sheet["A2"] = "OD0002 口径"
    scope = report.get("scope_description") or "当前用户权限范围：以系统数据权限为准"
    excluded_departments = "、".join(sorted(EXCLUDED_DEPARTMENT_CODES))
    sheet["B2"] = (
        "销售日期取 sglhsrq；销售收入取 sglxssr；毛利额取 sgln2；"
        "排除租赁 sglwmid=5；排除楼层00；排除16部门；"
        f"排除部门编码：{excluded_departments}；{scope}；"
        "合计仅包含当前用户权限范围；大类暂不提供。"
    )
    for cell in sheet[1]:
        cell.fill = PatternFill("solid", fgColor=BLUE)
        cell.font = Font(color=WHITE, bold=True)
        cell.border = BORDER
    sheet["A2"].border = BORDER
    sheet["B2"].border = BORDER
    sheet["B2"].alignment = Alignment(wrap_text=True, vertical="top")
    sheet.column_dimensions["A"].width = 20
    sheet.column_dimensions["B"].width = 110
    sheet.row_dimensions[2].height = 60


def build_od0002_workbook(report: dict[str, Any]) -> bytes:
    """Build the OD0002 multi-sheet workbook entirely in memory."""
    workbook = Workbook()
    workbook.remove(workbook.active)
    for label, dimension_key in SHEETS:
        _write_report_sheet(workbook.create_sheet(label), report, label, dimension_key)
    _write_notes(workbook.create_sheet("报表说明"), report)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
