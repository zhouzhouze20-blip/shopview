from __future__ import annotations

from tempfile import SpooledTemporaryFile
from typing import Any

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


BLUE = "0B64A0"
LIGHT_BLUE = "D9EAF7"
LIGHT_GREEN = "E2F0D9"
WHITE = "FFFFFF"
RISE_RED = "FFC00000"
FALL_GREEN = "FF008000"
THIN = Side(style="thin", color="B7B7B7")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def _safe_text(value: Any) -> str:
    text = str(value or "")
    return "'" + text if text.startswith(("=", "+", "-", "@")) else text


def _style_header(cell, fill: str = BLUE) -> None:
    cell.fill = PatternFill("solid", fgColor=fill)
    cell.font = Font(name="微软雅黑", color=WHITE, bold=True, size=9)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = BORDER


def _metric_lookup(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(level.get("level_code")): level for level in row.get("levels", [])}


def _yoy_color(value: Any) -> str | None:
    if value is None:
        return None
    numeric = float(value)
    if numeric > 0:
        return RISE_RED
    if numeric < 0:
        return FALL_GREEN
    return None


def _add_yoy_conditional_formatting(sheet, cell_range: str) -> None:
    sheet.conditional_formatting.add(
        cell_range,
        CellIsRule(operator="greaterThan", formula=["0"], font=Font(color=RISE_RED)),
    )
    sheet.conditional_formatting.add(
        cell_range,
        CellIsRule(operator="lessThan", formula=["0"], font=Font(color=FALL_GREEN)),
    )


def _write_detail(workbook: Workbook, report: dict[str, Any]) -> None:
    sheet = workbook.active
    sheet.title = "明细"
    sheet.freeze_panes = "D4"
    sheet.sheet_view.showGridLines = False

    fixed_headers = ("品类主管", "柜组编码", "重点品牌")
    for col, label in enumerate(fixed_headers, 1):
        cell = sheet.cell(1, col, label)
        sheet.merge_cells(start_row=1, start_column=col, end_row=3, end_column=col)
        _style_header(cell)

    sheet.merge_cells("D1:O1")
    sheet["D1"] = "销售（元）"
    _style_header(sheet["D1"])
    sheet.merge_cells("P1:AA1")
    sheet["P1"] = "消费人数"
    _style_header(sheet["P1"], fill="70AD47")

    levels = report.get("levels", [])
    for section_start, fill in ((4, BLUE), (16, "70AD47")):
        for index, level in enumerate(levels):
            start = section_start + index * 3
            sheet.merge_cells(start_row=2, start_column=start, end_row=2, end_column=start + 2)
            cell = sheet.cell(2, start, level.get("level_label"))
            _style_header(cell, fill=fill)
            for offset, label in enumerate(("本期", "同期", "同比")):
                _style_header(sheet.cell(3, start + offset, label), fill=fill)

    widths = (14, 15, 25) + (14, 14, 11) * 8
    for index, width in enumerate(widths, 1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    for row_index in (1, 2, 3):
        sheet.row_dimensions[row_index].height = 24

    for row_index, source in enumerate(report.get("rows", []), 4):
        sheet.cell(row_index, 1, _safe_text(source.get("manager_name") or "未维护"))
        sheet.cell(row_index, 2, _safe_text(source.get("group_code")))
        sheet.cell(row_index, 2).number_format = "@"
        sheet.cell(row_index, 3, _safe_text(source.get("group_name")))
        lookup = _metric_lookup(source)
        for level_index, level in enumerate(levels):
            metric = lookup.get(str(level.get("level_code")), {})
            sales_col = 4 + level_index * 3
            buyer_col = 16 + level_index * 3
            sales_values = (
                metric.get("current_sales", 0),
                metric.get("prior_sales", 0),
                metric.get("sales_yoy"),
            )
            buyer_values = (
                metric.get("current_buyers", 0),
                metric.get("prior_buyers", 0),
                metric.get("buyer_yoy"),
            )
            for offset, value in enumerate(sales_values):
                cell = sheet.cell(row_index, sales_col + offset, value)
                cell.number_format = "0.00" if offset < 2 else "0.00%"
            for offset, value in enumerate(buyer_values):
                cell = sheet.cell(row_index, buyer_col + offset, value)
                cell.number_format = "0" if offset < 2 else "0.00%"
        for cell in sheet[row_index]:
            cell.border = BORDER
            cell.font = Font(name="微软雅黑", size=9)
            cell.alignment = Alignment(
                horizontal="left" if cell.column <= 3 else "right",
                vertical="center",
            )
        for level_index, level in enumerate(levels):
            metric = lookup.get(str(level.get("level_code")), {})
            for column, value in (
                (6 + level_index * 3, metric.get("sales_yoy")),
                (18 + level_index * 3, metric.get("buyer_yoy")),
            ):
                color = _yoy_color(value)
                if color is not None:
                    sheet.cell(row_index, column).font = Font(
                        name="微软雅黑", size=9, color=color
                    )

    last_row = max(4, 3 + len(report.get("rows", [])))
    sheet.auto_filter.ref = f"A3:AA{last_row}"
    if report.get("rows"):
        for column in ("F", "I", "L", "O", "R", "U", "X", "AA"):
            _add_yoy_conditional_formatting(sheet, f"{column}4:{column}{last_row}")


def _write_manager_summary(workbook: Workbook, report: dict[str, Any]) -> None:
    sheet = workbook.create_sheet("主管汇总")
    sheet.sheet_view.showGridLines = False
    sheet.freeze_panes = "A2"
    headers = ("品类主管", "重点品牌数", "本期黑金+黑钻销售", "同期黑金+黑钻销售", "同比")
    for col, label in enumerate(headers, 1):
        _style_header(sheet.cell(1, col, label))
    for col, width in enumerate((16, 14, 22, 22, 12), 1):
        sheet.column_dimensions[get_column_letter(col)].width = width

    detail_last_row = max(4, 3 + len(report.get("rows", [])))
    for row_index, summary in enumerate(report.get("manager_summary", []), 2):
        manager = _safe_text(summary.get("manager_name") or "未维护")
        sheet.cell(row_index, 1, manager)
        sheet.cell(row_index, 2, summary.get("key_brand_count", 0))
        sheet.cell(
            row_index,
            3,
            f'=SUMIF(\'明细\'!$A$4:$A${detail_last_row},A{row_index},\'明细\'!$D$4:$D${detail_last_row})+'
            f'SUMIF(\'明细\'!$A$4:$A${detail_last_row},A{row_index},\'明细\'!$G$4:$G${detail_last_row})',
        )
        sheet.cell(
            row_index,
            4,
            f'=SUMIF(\'明细\'!$A$4:$A${detail_last_row},A{row_index},\'明细\'!$E$4:$E${detail_last_row})+'
            f'SUMIF(\'明细\'!$A$4:$A${detail_last_row},A{row_index},\'明细\'!$H$4:$H${detail_last_row})',
        )
        sheet.cell(row_index, 5, f'=IFERROR(C{row_index}/D{row_index}-1,"")')
        for cell in sheet[row_index]:
            cell.border = BORDER
            cell.font = Font(name="微软雅黑", size=9)
            cell.alignment = Alignment(horizontal="right" if cell.column > 1 else "left")
        sheet.cell(row_index, 2).number_format = "0"
        sheet.cell(row_index, 3).number_format = "0.00"
        sheet.cell(row_index, 4).number_format = "0.00"
        sheet.cell(row_index, 5).number_format = "0.00%"
        color = _yoy_color(summary.get("premium_sales_yoy"))
        if color is not None:
            sheet.cell(row_index, 5).font = Font(
                name="微软雅黑", size=9, color=color
            )
    if report.get("manager_summary"):
        _add_yoy_conditional_formatting(
            sheet, f"E2:E{1 + len(report.get('manager_summary', []))}"
        )


def _write_notes(workbook: Workbook, report: dict[str, Any]) -> None:
    sheet = workbook.create_sheet("数据口径")
    sheet.sheet_view.showGridLines = False
    sheet.column_dimensions["A"].width = 22
    sheet.column_dimensions["B"].width = 110
    notes = [
        ("报表", "HY0001 重点品牌会员消费情况"),
        (
            "期间",
            f"本期 {report.get('dates', {}).get('current_start')} 至 {report.get('dates', {}).get('current_end')}；"
            f"同期 {report.get('dates', {}).get('prior_start')} 至 {report.get('dates', {}).get('prior_end')}",
        ),
        ("重点品牌", "取 manaframe_key_brand 中当前标记为重点品牌的柜组。"),
        ("品类主管", "取 category_manager_brand_assignments 当前有效的柜组—品类主管关系；未维护显示“未维护”。"),
        ("会员等级", "取 salehead.custtype：01银星、02金星、03黑金、04黑钻。"),
        ("销售", "按等级内、期间内至少有一笔正向购买的会员汇总销售收入净额 sglxssr；退货净额保留。"),
        ("人数", "按会员等级和柜组对非空会员卡号去重，仅计期间内至少有一笔正向购买的会员。"),
        ("同比", "本期÷同期－1；同期为0时留空，不强行显示为100%；上升显示红色，下跌显示绿色。"),
        ("权限范围", report.get("scope_description") or "以当前账号销售数据权限为准。"),
    ]
    for row_index, (label, value) in enumerate(notes, 1):
        sheet.cell(row_index, 1, label)
        sheet.cell(row_index, 2, value)
        sheet.cell(row_index, 1).fill = PatternFill("solid", fgColor=LIGHT_BLUE)
        sheet.cell(row_index, 1).font = Font(name="微软雅黑", bold=True)
        for cell in sheet[row_index]:
            cell.border = BORDER
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            if cell.font.name != "微软雅黑":
                cell.font = Font(name="微软雅黑", size=10)


def build_hy0001_workbook_file(report: dict[str, Any]):
    workbook = Workbook()
    _write_detail(workbook, report)
    _write_manager_summary(workbook, report)
    _write_notes(workbook, report)
    output = SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b")
    workbook.save(output)
    output.seek(0)
    return output
