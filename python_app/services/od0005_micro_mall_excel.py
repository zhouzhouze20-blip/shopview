from __future__ import annotations

from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


HEADERS = (
    "门店",
    "部门",
    "柜组",
    "柜组名称",
    "销售数量",
    "售价金额",
    "销售收入+总折扣(A)",
    "销售收入",
    "毛利",
    "毛利率",
    "YZQ",
    "其他支付",
    "NZD",
)

DEPARTMENT_HEADERS = (
    "门店",
    "部门",
    "销售数量",
    "应收金额",
    "有赞卡券",
    "礼券",
    "销售收入",
    "销售收入(内转)",
    "毛利额",
    "毛利率",
)

DEPARTMENT_AMOUNT_KEYS = (
    "sales_quantity",
    "price_amount",
    "yzq_amount",
    "other_payment_amount",
    "sales_before_discount",
    "sales_revenue",
    "gross_profit",
)


def _display_department(row: dict[str, Any]) -> str:
    code = str(row.get("department_code") or "").strip()
    name = str(row.get("department_name") or "").strip()
    return " ".join(value for value in (code, name) if value)


def _department_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    departments: dict[tuple[str, str], dict[str, Any]] = {}
    for source in rows:
        department_code = str(source.get("department_code") or "").strip()
        department_name = str(source.get("department_name") or "未匹配").strip()
        key = (department_code, department_name)
        row = departments.setdefault(
            key,
            {
                "store_code": source.get("store_code", ""),
                "department_code": department_code,
                "department_name": department_name,
                **{amount_key: 0.0 for amount_key in DEPARTMENT_AMOUNT_KEYS},
            },
        )
        for amount_key in DEPARTMENT_AMOUNT_KEYS:
            row[amount_key] += float(source.get(amount_key) or 0)

    for row in departments.values():
        sales_revenue = row["sales_revenue"]
        row["gross_margin"] = (
            row["gross_profit"] / sales_revenue if sales_revenue else None
        )
    return list(departments.values())


def _prepare_sheet(
    sheet: Any,
    *,
    report: dict[str, Any],
    title: str,
    headers: tuple[str, ...],
) -> tuple[str, PatternFill, PatternFill, Border]:
    sheet.sheet_view.showGridLines = False
    sheet.freeze_panes = "A5"

    last_column = get_column_letter(len(headers))
    sheet.merge_cells(f"A1:{last_column}1")
    sheet["A1"] = "普灵仕集团百货事业部"
    sheet["A1"].font = Font(name="宋体", size=24, bold=True)
    sheet["A1"].alignment = Alignment(horizontal="center", vertical="center")
    sheet.row_dimensions[1].height = 38

    sheet.merge_cells(f"A2:{last_column}2")
    sheet["A2"] = title
    sheet["A2"].font = Font(name="宋体", size=18, bold=True)
    sheet["A2"].alignment = Alignment(horizontal="center", vertical="center")
    sheet.row_dimensions[2].height = 30

    metadata_split = min(6, len(headers) - 1)
    sheet.merge_cells(start_row=3, start_column=1, end_row=3, end_column=metadata_split)
    sheet["A3"] = f"日期：{report['start_date']}  至  {report['end_date']}"
    store_column = metadata_split + 1
    sheet.merge_cells(
        start_row=3,
        start_column=store_column,
        end_row=3,
        end_column=len(headers),
    )
    store_cell = sheet.cell(3, store_column)
    store_cell.value = f"门店：{report['store_code']} {report['store_name']}"
    for cell in (sheet["A3"], store_cell):
        cell.font = Font(name="宋体", size=11, bold=True)
        cell.alignment = Alignment(horizontal="left", vertical="center")
    sheet.row_dimensions[3].height = 24

    header_fill = PatternFill("solid", fgColor="E2F0D9")
    total_fill = PatternFill("solid", fgColor="D9EAF7")
    thin = Side(style="thin", color="B7B7B7")
    border = Border(bottom=thin)
    for column, label in enumerate(headers, start=1):
        cell = sheet.cell(4, column, label)
        cell.font = Font(name="宋体", size=10, bold=True)
        cell.fill = header_fill
        cell.border = border
        cell.alignment = Alignment(horizontal="center", vertical="center")
    sheet.row_dimensions[4].height = 24
    return last_column, header_fill, total_fill, border


def _add_department_sheet(workbook: Workbook, report: dict[str, Any]) -> None:
    sheet = workbook.create_sheet("部门销售统计")
    last_column, _, total_fill, border = _prepare_sheet(
        sheet,
        report=report,
        title="微商城部门销售统计",
        headers=DEPARTMENT_HEADERS,
    )

    rows = _department_rows(list(report.get("rows", [])))
    for row_index, row in enumerate(rows, start=5):
        values = (
            row.get("store_code", ""),
            _display_department(row),
            row.get("sales_quantity", 0),
            row.get("price_amount", 0),
            row.get("yzq_amount", 0),
            row.get("other_payment_amount", 0),
            row.get("sales_before_discount", 0),
            row.get("sales_revenue", 0),
            row.get("gross_profit", 0),
            row.get("gross_margin"),
        )
        for column, value in enumerate(values, start=1):
            cell = sheet.cell(row_index, column, value)
            cell.font = Font(name="宋体", size=10)
            cell.border = border
            cell.alignment = Alignment(
                horizontal="left" if column == 2 else "right" if column >= 3 else "center",
                vertical="center",
            )

    total_row = 5 + len(rows)
    totals = report.get("totals", {})
    total_values = (
        "合计",
        "",
        totals.get("sales_quantity", 0),
        totals.get("price_amount", 0),
        totals.get("yzq_amount", 0),
        totals.get("other_payment_amount", 0),
        totals.get("sales_before_discount", 0),
        totals.get("sales_revenue", 0),
        totals.get("gross_profit", 0),
        totals.get("gross_margin"),
    )
    sheet.merge_cells(start_row=total_row, start_column=1, end_row=total_row, end_column=2)
    for column, value in enumerate(total_values, start=1):
        if column == 2:
            continue
        sheet.cell(total_row, column, value)
    for cell in sheet[total_row]:
        cell.fill = total_fill
        cell.font = Font(name="宋体", size=10, bold=True)
        cell.border = border
        cell.alignment = Alignment(horizontal="right", vertical="center")

    for row_index in range(5, total_row + 1):
        sheet.cell(row_index, 3).number_format = "#,##0.####"
        for column in range(4, 10):
            sheet.cell(row_index, column).number_format = "#,##0.00;[Red]-#,##0.00"
        sheet.cell(row_index, 10).number_format = "0.00%"

    widths = (9, 28, 12, 15, 15, 15, 15, 18, 15, 11)
    for column, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(column)].width = width

    sheet.auto_filter.ref = f"A4:{last_column}{max(total_row - 1, 4)}"
    sheet.print_title_rows = "1:4"
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.print_area = f"A1:{last_column}{total_row}"


def build_od0005_workbook(report: dict[str, Any]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "微商城品牌销售统计"
    last_column, _, total_fill, border = _prepare_sheet(
        sheet,
        report=report,
        title="微商城品牌销售统计",
        headers=HEADERS,
    )

    rows = report.get("rows", [])
    for row_index, row in enumerate(rows, start=5):
        values = (
            row.get("store_code", ""),
            _display_department(row),
            row.get("group_code", ""),
            row.get("group_name", ""),
            row.get("sales_quantity", 0),
            row.get("price_amount", 0),
            row.get("sales_before_discount", 0),
            row.get("sales_revenue", 0),
            row.get("gross_profit", 0),
            row.get("gross_margin"),
            row.get("yzq_amount", 0),
            row.get("other_payment_amount", 0),
            row.get("nzd_amount", 0),
        )
        for column, value in enumerate(values, start=1):
            cell = sheet.cell(row_index, column, value)
            cell.font = Font(name="宋体", size=10)
            cell.border = border
            cell.alignment = Alignment(
                horizontal="left" if column in (2, 4) else "right" if column >= 5 else "center",
                vertical="center",
            )

    total_row = 5 + len(rows)
    totals = report.get("totals", {})
    sheet.merge_cells(start_row=total_row, start_column=1, end_row=total_row, end_column=4)
    total_values = (
        "合计",
        totals.get("sales_quantity", 0),
        totals.get("price_amount", 0),
        totals.get("sales_before_discount", 0),
        totals.get("sales_revenue", 0),
        totals.get("gross_profit", 0),
        totals.get("gross_margin"),
        totals.get("yzq_amount", 0),
        totals.get("other_payment_amount", 0),
        totals.get("nzd_amount", 0),
    )
    sheet.cell(total_row, 1, total_values[0])
    for offset, value in enumerate(total_values[1:], start=5):
        sheet.cell(total_row, offset, value)
    for cell in sheet[total_row]:
        cell.fill = total_fill
        cell.font = Font(name="宋体", size=10, bold=True)
        cell.border = border
        cell.alignment = Alignment(horizontal="right", vertical="center")

    for row_index in range(5, total_row + 1):
        sheet.cell(row_index, 5).number_format = "#,##0.####"
        for column in range(6, 10):
            sheet.cell(row_index, column).number_format = "#,##0.00;[Red]-#,##0.00"
        sheet.cell(row_index, 10).number_format = "0.00%"
        for column in range(11, 14):
            sheet.cell(row_index, column).number_format = "#,##0.00;[Red]-#,##0.00"

    widths = (9, 25, 15, 30, 12, 15, 20, 15, 15, 11, 15, 15, 15)
    for column, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(column)].width = width

    sheet.auto_filter.ref = f"A4:{last_column}{max(total_row - 1, 4)}"
    sheet.print_title_rows = "1:4"
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.print_area = f"A1:{last_column}{total_row}"

    _add_department_sheet(workbook, report)

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def build_od0005_workbook_file(report: dict[str, Any]) -> BytesIO:
    output = BytesIO(build_od0005_workbook(report))
    output.seek(0)
    return output
