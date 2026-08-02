from datetime import date
from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import load_workbook

from python_app.routers.authz import CORE_PERMISSION_DEFINITIONS
from python_app.services.od0002_report import TrustedScopeSql
from python_app.services.od0005_micro_mall_excel import build_od0005_workbook
from python_app.services.od0005_micro_mall_report import (
    assemble_od0005_report,
    build_od0005_query,
    micro_mall_cashier,
)


def test_three_store_cashier_mapping_matches_source_sql():
    assert micro_mall_cashier("601") == "300411"
    assert micro_mall_cashier("602") == "600518"
    assert micro_mall_cashier("603") == "500708"
    with pytest.raises(ValueError, match="unsupported OD0005 store"):
        micro_mall_cashier("604")


def test_query_keeps_source_columns_and_payment_groups():
    sql, params = build_od0005_query(
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 1),
        selected_store=" 601 ",
        selected_department=" 6010114 ",
        scope_filter_sql=TrustedScopeSql(" AND st.store_id::text = ANY(:allowed_stores)"),
        scope_params={"allowed_stores": ["1"]},
    )
    compact = " ".join(sql.lower().split())

    assert "s.sgldate::date between :start_date and :end_date" in compact
    assert "s.sglchecker" in compact
    assert "sum(coalesce(s.sglsl, 0))" in compact
    assert "sum(coalesce(s.sglsjje, 0))" in compact
    assert "coalesce(s.sglxssr, 0) + coalesce(s.sgltotzk, 0)" in compact
    assert "sum(coalesce(s.sgln2, 0))" in compact
    assert "spg.spgpmcode in ('2031', '1014', '3064')" in compact
    assert "spg.spgpmcode = '0511'" in compact
    assert "spg.spgpmtype = '5'" in compact
    assert "join sellpaygoods spg" in compact
    assert params["micro_mall_cashier"] == "300411"
    assert params["selected_department"] == "6010114"


def test_report_and_workbook_preserve_template_layout():
    report = assemble_od0005_report(
        [
            {
                "store_code": "601",
                "store_name": "常州购物中心",
                "department_code": "6010114",
                "department_name": "中心一部(化妆)",
                "group_code": "6010101005",
                "group_name": "SK-II厅",
                "sales_quantity": 4,
                "price_amount": 6800,
                "sales_before_discount": 6800,
                "sales_revenue": 5458.8,
                "gross_profit": 1200,
                "gross_margin": 0,
                "yzq_amount": 1661.2,
                "other_payment_amount": 5458.8,
                "nzd_amount": 0,
            }
        ],
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 1),
        selected_store="601",
        selected_department=None,
    )
    assert report["cashier_code"] == "300411"
    assert report["totals"]["gross_margin"] == pytest.approx(1200 / 5458.8)

    workbook = load_workbook(BytesIO(build_od0005_workbook(report)))
    sheet = workbook["微商城品牌销售统计"]
    assert sheet["A1"].value == "普灵仕集团百货事业部"
    assert sheet["A2"].value == "微商城品牌销售统计"
    assert sheet["A4"].value == "门店"
    assert sheet["D4"].value == "柜组名称"
    assert sheet["E4"].value == "销售数量"
    assert sheet["J4"].value == "毛利率"
    assert sheet["M4"].value == "NZD"
    assert sheet["D5"].value == "SK-II厅"
    assert sheet.freeze_panes == "A5"


def test_workbook_adds_department_sales_summary_sheet():
    report = assemble_od0005_report(
        [
            {
                "store_code": "601",
                "store_name": "常州购物中心",
                "department_code": "6010114",
                "department_name": "中心一部(化妆)",
                "group_code": "6010101005",
                "group_name": "SK-II厅",
                "sales_quantity": 4,
                "price_amount": 6800,
                "sales_before_discount": 5600,
                "sales_revenue": 5458.8,
                "gross_profit": 1200,
                "yzq_amount": 1661.2,
                "other_payment_amount": 3738.8,
                "nzd_amount": 58.8,
            },
            {
                "store_code": "601",
                "store_name": "常州购物中心",
                "department_code": "6010114",
                "department_name": "中心一部(化妆)",
                "group_code": "6010101006",
                "group_name": "兰蔻厅",
                "sales_quantity": 2,
                "price_amount": 3200,
                "sales_before_discount": 3000,
                "sales_revenue": 2800,
                "gross_profit": 600,
                "yzq_amount": 1000,
                "other_payment_amount": 1800,
                "nzd_amount": 0,
            },
            {
                "store_code": "601",
                "store_name": "常州购物中心",
                "department_code": "6010119",
                "department_name": "中心儿童游乐园",
                "group_code": "6010119001",
                "group_name": "游乐园",
                "sales_quantity": 1,
                "price_amount": 39.9,
                "sales_before_discount": 39.9,
                "sales_revenue": 39.9,
                "gross_profit": 39.9,
                "yzq_amount": 0,
                "other_payment_amount": 39.9,
                "nzd_amount": 0,
            },
        ],
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 1),
        selected_store="601",
        selected_department=None,
    )

    workbook = load_workbook(BytesIO(build_od0005_workbook(report)))
    assert workbook.sheetnames == ["微商城品牌销售统计", "部门销售统计"]

    sheet = workbook["部门销售统计"]
    assert sheet["A2"].value == "微商城部门销售统计"
    assert [sheet.cell(4, column).value for column in range(1, 11)] == [
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
    ]
    assert sheet["B5"].value == "6010114 中心一部(化妆)"
    assert sheet["C5"].value == pytest.approx(6)
    assert sheet["D5"].value == pytest.approx(10000)
    assert sheet["E5"].value == pytest.approx(2661.2)
    assert sheet["F5"].value == pytest.approx(5538.8)
    assert sheet["G5"].value == pytest.approx(8600)
    assert sheet["H5"].value == pytest.approx(8258.8)
    assert sheet["I5"].value == pytest.approx(1800)
    assert sheet["J5"].value == pytest.approx(1800 / 8258.8)
    assert sheet["A7"].value == "合计"
    assert sheet["D7"].value == pytest.approx(report["totals"]["price_amount"])
    assert sheet["J7"].value == pytest.approx(report["totals"]["gross_margin"])
    assert sheet.freeze_panes == "A5"


def test_permission_is_registered_and_migration_preserves_report_access():
    registered = {permission[0] for permission in CORE_PERMISSION_DEFINITIONS}
    assert "sales.od0005.view" in registered
    migration = Path(
        "python_app/alembic/versions/u9c0d1e2f3a4_add_od0005_micro_mall_permission.py"
    ).read_text(encoding="utf-8")
    assert "'sales.od0005.view'" in migration
    assert "source.permission_code = 'sales.od0001.view'" in migration
    assert "查看非租赁品牌月度收益表" in migration
