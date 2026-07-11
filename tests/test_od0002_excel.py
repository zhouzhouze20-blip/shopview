import asyncio
from datetime import date
from io import BytesIO
from tempfile import SpooledTemporaryFile

from openpyxl import load_workbook


def sample_report(*, empty=False):
    metrics = {
        "sales_current": 120000.0,
        "sales_prior": 100000.0,
        "sales_yoy": 0.2,
        "profit_current": 24000.0,
        "profit_prior": 15000.0,
        "profit_yoy": 0.6,
        "margin_current": 0.2,
        "margin_prior": 0.15,
        "margin_change": 0.05,
    }
    dimensions = {}
    totals = {}
    for key in ("stores", "departments", "areas", "categories", "groups", "floors"):
        dimensions[key] = [] if empty else [{
            "store_code": "601",
            "store_name": "一店",
            "dimension_code": "D01" if key != "stores" else "601",
            "dimension_name": "女装" if key != "stores" else "一店",
            "metrics": dict(metrics),
        }]
        totals[key] = dict(metrics)
    if not empty:
        dimensions["departments"].append({
            "store_code": "602", "store_name": "二店",
            "dimension_code": "D02", "dimension_name": "男装",
            "metrics": dict(metrics),
        })
    return {
        "dates": {
            "start_date": date(2026, 1, 1), "end_date": date(2026, 1, 31),
            "prior_start_date": date(2025, 1, 1), "prior_end_date": date(2025, 1, 31),
        },
        "selected_store": None,
        "dimensions": dimensions,
        "totals": totals,
        "scope_description": "当前用户权限范围：门店 601、602",
    }


def test_workbook_has_required_sheets_headers_formats_totals_and_notes():
    from python_app.services.od0002_excel import build_od0002_workbook
    from python_app.services.od0002_report import EXCLUDED_DEPARTMENT_CODES

    payload = build_od0002_workbook(sample_report())
    assert isinstance(payload, bytes)
    workbook = load_workbook(BytesIO(payload))
    assert workbook.sheetnames == ["分店", "部门", "区域", "品类", "柜组", "楼层", "报表说明"]

    sheet = workbook["部门"]
    assert sheet["A1"].value == "OD0002 门店销售毛利汇总表（部门）"
    assert "2026-01-01" in sheet["A2"].value and "2026-01-31" in sheet["A2"].value
    assert "2025-01-01" in sheet["A3"].value and "2025-01-31" in sheet["A3"].value
    assert sheet.freeze_panes == "A8"
    assert sheet["A5"].fill.fgColor.rgb.endswith("4472C4")
    assert sheet["A5"].font.color.type == "rgb" and sheet["A5"].font.color.rgb.endswith("FFFFFF")
    assert sheet["E8"].value == 12
    assert sheet["E8"].number_format == "0.00"
    assert sheet["G8"].number_format == "0.00%"
    assert sheet["A10"].value == "合计"
    assert sheet["E10"].value == 12
    assert sheet["G10"].value == 0.2
    assert sheet["A10"].border.bottom.style is not None

    notes = workbook["报表说明"]["B2"].value
    for text in ("sglhsrq", "sglxssr", "sgln2", "sglwmid=5", "楼层00", "16部门", "当前用户权限范围", "大类暂不提供"):
        assert text in notes
    sorted_codes = sorted(EXCLUDED_DEPARTMENT_CODES)
    assert sorted_codes[0] in notes and sorted_codes[-1] in notes
    assert all(code in notes for code in sorted_codes)
    assert "合计仅包含当前用户权限范围" in notes


def test_workbook_keeps_store_columns_for_multiple_store_rows():
    from python_app.services.od0002_excel import build_od0002_workbook

    workbook = load_workbook(BytesIO(build_od0002_workbook(sample_report())))
    sheet = workbook["部门"]
    assert [sheet.cell(8, column).value for column in range(1, 5)] == ["601", "一店", "D01", "女装"]
    assert [sheet.cell(9, column).value for column in range(1, 5)] == ["602", "二店", "D02", "男装"]


def test_group_sheet_uses_roomier_data_rows_without_changing_other_sheets():
    from python_app.services.od0002_excel import GROUP_DATA_ROW_HEIGHT, build_od0002_workbook

    workbook = load_workbook(BytesIO(build_od0002_workbook(sample_report())))
    group_sheet = workbook["柜组"]
    assert group_sheet.row_dimensions[8].height == GROUP_DATA_ROW_HEIGHT
    assert group_sheet.row_dimensions[9].height == GROUP_DATA_ROW_HEIGHT
    assert workbook["部门"].row_dimensions[8].height is None


def test_workbook_escapes_formula_like_dimension_text_and_has_no_invalid_filter():
    from python_app.services.od0002_excel import build_od0002_workbook

    report = sample_report()
    report["dimensions"]["departments"][0].update({
        "store_code": "=1+1",
        "store_name": "+SUM(A1:A2)",
        "dimension_code": "-2+3",
        "dimension_name": "@cmd",
    })
    workbook = load_workbook(BytesIO(build_od0002_workbook(report)), data_only=False)
    sheet = workbook["部门"]
    for column in range(1, 5):
        cell = sheet.cell(8, column)
        assert cell.data_type == "s"
        assert cell.value.startswith("'")
    assert sheet.auto_filter.ref is None


def test_empty_report_still_has_valid_headers_and_notes():
    from python_app.services.od0002_excel import build_od0002_workbook

    workbook = load_workbook(BytesIO(build_od0002_workbook(sample_report(empty=True))))
    assert workbook["部门"]["A5"].value == "维度"
    assert workbook["部门"]["A8"].value == "合计"
    assert "大类暂不提供" in workbook["报表说明"]["B2"].value


def test_workbook_file_api_returns_seeked_temporary_file():
    from python_app.services.od0002_excel import build_od0002_workbook_file

    export_file = build_od0002_workbook_file(sample_report())
    try:
        assert isinstance(export_file, SpooledTemporaryFile)
        assert export_file.tell() == 0
        assert load_workbook(export_file).sheetnames[0] == "分店"
    finally:
        export_file.close()


def test_export_route_reuses_permission_scope_loader_and_sets_disposition(monkeypatch):
    from python_app.routers import sales
    from python_app.routers.authz import DataScope

    calls = {"load": 0}
    monkeypatch.setattr(sales, "require_permission", lambda db, user, code: calls.setdefault("permission", code))
    monkeypatch.setattr(sales, "load_business_scope", lambda *args, **kwargs: DataScope(allow={"store": {"601"}}))
    monkeypatch.setattr(sales, "_od0002_store_id_for_code", lambda db, code: "601")
    monkeypatch.setattr(sales, "_business_scope_filter_sql", lambda scope, params, **kwargs: " AND 1=1")
    def fake_load(*args, **kwargs):
        calls["load"] += 1
        calls["selected_store"] = kwargs["selected_store"]
        calls["selected_department"] = kwargs["selected_department"]
        return sample_report()
    monkeypatch.setattr(sales, "load_od0002_report", fake_load)
    export_file = SpooledTemporaryFile()
    export_file.write(b"xlsx")
    export_file.seek(0)
    monkeypatch.setattr(sales, "build_od0002_workbook_file", lambda report: export_file)
    threadpool_calls = []
    async def fake_threadpool(function, *args, **kwargs):
        threadpool_calls.append((function, args, kwargs))
        return function(*args, **kwargs)
    monkeypatch.setattr(sales, "run_in_threadpool", fake_threadpool)

    response = asyncio.run(sales.od0002_export(
        date(2026, 1, 1), date(2026, 1, 31), " 601 ", object(), object(), " 6030117 "
    ))

    assert calls == {
        "load": 1,
        "permission": "sales.od0002.view",
        "selected_store": "601",
        "selected_department": "6030117",
    }
    assert len(threadpool_calls) == 1
    assert threadpool_calls[0][0] is sales.build_od0002_workbook_file
    assert response.background is not None
    assert response.media_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    disposition = response.headers["content-disposition"]
    assert "filename*=UTF-8''" in disposition
    assert "OD0002_%E9%97%A8%E5%BA%97%E9%94%80%E5%94%AE%E6%AF%9B%E5%88%A9%E6%B1%87%E6%80%BB%E8%A1%A8_2026-01-01_2026-01-31.xlsx" in disposition

    async def consume_and_close():
        chunks = [chunk async for chunk in response.body_iterator]
        await response.background()
        return chunks

    chunks = asyncio.run(consume_and_close())
    assert b"".join(chunks) == b"xlsx"
    assert all(len(chunk) <= 64 * 1024 for chunk in chunks)
    assert export_file.closed


def test_query_and_export_each_load_report_once(monkeypatch):
    from python_app.routers import sales
    from python_app.routers.authz import DataScope

    calls = []
    monkeypatch.setattr(sales, "require_permission", lambda *args: None)
    monkeypatch.setattr(sales, "load_business_scope", lambda *args, **kwargs: DataScope(all_access=True))
    monkeypatch.setattr(sales, "_business_scope_filter_sql", lambda *args, **kwargs: "")
    monkeypatch.setattr(sales, "load_od0002_report", lambda *args, **kwargs: calls.append(kwargs) or sample_report())
    monkeypatch.setattr(sales, "build_od0002_workbook_file", lambda report: SpooledTemporaryFile())
    async def fake_threadpool(function, *args, **kwargs):
        return function(*args, **kwargs)
    monkeypatch.setattr(sales, "run_in_threadpool", fake_threadpool)

    asyncio.run(sales.od0002_report(date(2026, 1, 1), date(2026, 1, 31), None, object(), object()))
    assert len(calls) == 1
    calls.clear()
    asyncio.run(sales.od0002_export(date(2026, 1, 1), date(2026, 1, 31), None, object(), object()))
    assert len(calls) == 1
