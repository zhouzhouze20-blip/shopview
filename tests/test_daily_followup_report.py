import asyncio
from datetime import date

import pytest

from python_app.services.daily_followup_report import (
    build_daily_followup_payload,
    build_daily_followup_query,
    financial_month_period,
)
from python_app.services.od0002_report import TrustedScopeSql


def test_financial_month_runs_from_previous_month_29_to_current_month_28():
    assert financial_month_period(2026, 8) == (
        date(2026, 7, 29),
        date(2026, 8, 28),
    )
    assert financial_month_period(2026, 1) == (
        date(2025, 12, 29),
        date(2026, 1, 28),
    )
    assert financial_month_period(2026, 3) == (
        date(2026, 3, 1),
        date(2026, 3, 28),
    )
    assert financial_month_period(2024, 3) == (
        date(2024, 2, 29),
        date(2024, 3, 28),
    )


def test_financial_month_rejects_invalid_values():
    with pytest.raises(ValueError, match="between 1 and 12"):
        financial_month_period(2026, 13)
    with pytest.raises(ValueError, match="greater than 1"):
        financial_month_period(1, 1)


def test_daily_followup_query_binds_filters_and_permission_scope():
    sql, params = build_daily_followup_query(
        date(2026, 7, 29),
        date(2026, 8, 28),
        date(2025, 7, 29),
        date(2025, 8, 28),
        "groups",
        TrustedScopeSql(" AND dept.mfcode = ANY(:allowed_departments)"),
        {"allowed_departments": ["6030117"]},
        selected_store="603",
        selected_department=" 6030117 ",
    )

    compact = " ".join(sql.split())
    assert "salegoodslist" in compact
    assert "s.sglhsrq::date AS sale_date" in compact
    assert "dept.mfcode = ANY(:allowed_departments)" in compact
    assert "s.sglmarket::text = :selected_store" in compact
    assert "= UPPER(:selected_department)" in compact
    assert "ac.area_name" in compact
    assert "ac.category_name" in compact
    assert "contmanaframe" in compact
    assert "contmain" in compact
    assert "contract.cmwmid" in compact
    assert "s.sglhsrq::date BETWEEN cm.cmeffdate::date AND cm.cmlapdate::date" in compact
    assert params["selected_store"] == "603"
    assert params["selected_department"] == "6030117"
    assert params["allowed_departments"] == ["6030117"]


def test_daily_followup_query_pushes_selected_store_into_sales_prefilter():
    sql, _params = build_daily_followup_query(
        date(2026, 1, 1),
        date(2026, 12, 31),
        date(2025, 1, 1),
        date(2025, 12, 31),
        "departments",
        TrustedScopeSql(""),
        {},
        selected_store="602",
    )

    filtered_sales_sql, enriched_sales_sql = sql.split("area_category_dedup AS", 1)
    store_predicate = "s.sglmarket::text = :selected_store"
    assert store_predicate in filtered_sales_sql
    assert store_predicate not in enriched_sales_sql


def test_monthly_query_can_use_sales_operation_method_without_contract_lateral():
    sql, _params = build_daily_followup_query(
        date(2026, 1, 1),
        date(2026, 12, 31),
        date(2025, 1, 1),
        date(2025, 12, 31),
        "departments",
        TrustedScopeSql(""),
        {},
        selected_store="601",
        operation_method_source="sales",
    )

    compact = " ".join(sql.split())
    assert "LEFT JOIN LATERAL" not in compact
    assert "TRIM(BOTH FROM COALESCE(s.sglwmid, '')) AS operation_method_code" in compact
    assert "s.sglwmid" in compact.split("area_category_dedup AS", 1)[0]


def test_daily_followup_special_sales_query_matches_od0002_group_brand_scope():
    sql, _params = build_daily_followup_query(
        date(2026, 6, 29),
        date(2026, 7, 28),
        date(2025, 6, 29),
        date(2025, 7, 28),
        "special_sales",
        TrustedScopeSql(""),
        {},
    )

    compact = " ".join(sql.split())
    assert "TRIM(BOTH FROM COALESCE(mf.mflc, '')) = '16'" in compact
    assert "LEFT JOIN codebrand cb" in compact
    assert "s.sglppcode" in compact
    assert "cb.cbcname" in compact


def test_daily_followup_query_rejects_untrusted_dimension():
    with pytest.raises(ValueError, match="unsupported"):
        build_daily_followup_query(
            date(2026, 7, 29),
            date(2026, 8, 28),
            date(2025, 7, 29),
            date(2025, 8, 28),
            "stores",  # type: ignore[arg-type]
            TrustedScopeSql(""),
            {},
        )


def test_daily_followup_payload_aligns_prior_days_and_totals():
    rows = [
        {
            "sale_date": date(2026, 7, 29),
            "store_code": "603",
            "store_name": "常州新世纪商城",
            "department_code": "6030117",
            "department_name": "中心三部(女装)",
            "area_name": "女装区",
            "category_name": "少淑女装",
            "operation_method_code": "4",
            "dimension_code": "6030117",
            "dimension_name": "中心三部(女装)",
            "sales": 120_000,
            "profit": 24_000,
        },
        {
            "sale_date": date(2025, 7, 29),
            "store_code": "603",
            "store_name": "常州新世纪商城",
            "department_code": "6030117",
            "department_name": "中心三部(女装)",
            "area_name": "女装区",
            "category_name": "少淑女装",
            "operation_method_code": "4",
            "dimension_code": "6030117",
            "dimension_name": "中心三部(女装)",
            "sales": 100_000,
            "profit": 15_000,
        },
        {
            "sale_date": date(2026, 7, 29),
            "store_code": "603",
            "store_name": "常州新世纪商城",
            "department_code": "6030102",
            "department_name": "中心四部(男装)",
            "dimension_code": "6030102",
            "dimension_name": "中心四部(男装)",
            "sales": 30_000,
            "profit": 3_000,
        },
    ]

    report = build_daily_followup_payload(
        rows,
        financial_year=2026,
        financial_month=8,
        dimension="departments",
    )

    assert report["dates"] == {
        "start_date": "2026-07-29",
        "end_date": "2026-08-28",
        "prior_start_date": "2025-07-29",
        "prior_end_date": "2025-08-28",
    }
    assert report["days"][0] == {
        "date": "2026-07-29",
        "prior_date": "2025-07-29",
        "label": "07-29",
    }
    assert [row["department_code"] for row in report["rows"]] == [
        "6030117",
        "6030102",
    ]
    first_day = report["rows"][0]["daily"][0]
    assert report["rows"][0]["area_name"] == "女装区"
    assert report["rows"][0]["category_name"] == "少淑女装"
    assert report["rows"][0]["operation_method"] == "联营"
    assert first_day["sales_current"] == 120_000
    assert first_day["sales_prior"] == 100_000
    assert first_day["sales_yoy"] == pytest.approx(0.2)
    assert first_day["margin_current"] == pytest.approx(0.2)
    assert report["totals"]["sales_current"] == 150_000
    assert report["totals"]["sales_prior"] == 100_000
    assert report["daily_totals"][0]["profit_current"] == 27_000


def test_daily_followup_cumulative_totals_stop_at_yesterday_for_od0001():
    rows = [
        {
            "sale_date": date(2026, 7, 29),
            "store_code": "601",
            "department_code": "60101",
            "dimension_code": "60101",
            "sales": 50_000,
            "profit": 5_000,
        },
        {
            "sale_date": date(2025, 7, 29),
            "store_code": "601",
            "department_code": "60101",
            "dimension_code": "60101",
            "sales": 40_000,
            "profit": 4_000,
        },
        {
            "sale_date": date(2026, 7, 31),
            "store_code": "601",
            "department_code": "60101",
            "dimension_code": "60101",
            "sales": 10_000,
            "profit": 1_000,
        },
        {
            "sale_date": date(2025, 7, 31),
            "store_code": "601",
            "department_code": "60101",
            "dimension_code": "60101",
            "sales": 20_000,
            "profit": 2_000,
        },
        {
            "sale_date": date(2026, 8, 1),
            "store_code": "601",
            "department_code": "60101",
            "dimension_code": "60101",
            "sales": 900_000,
            "profit": 90_000,
        },
        {
            "sale_date": date(2025, 8, 1),
            "store_code": "601",
            "department_code": "60101",
            "dimension_code": "60101",
            "sales": 800_000,
            "profit": 80_000,
        },
    ]

    report = build_daily_followup_payload(
        rows,
        financial_year=2026,
        financial_month=8,
        dimension="departments",
        as_of_date=date(2026, 8, 1),
        cutoff_at_yesterday=True,
    )

    assert report["cumulative_dates"] == {
        "start_date": "2026-07-29",
        "end_date": "2026-07-31",
        "prior_start_date": "2025-07-29",
        "prior_end_date": "2025-07-31",
    }
    assert report["rows"][0]["totals"]["sales_current"] == 60_000
    assert report["rows"][0]["totals"]["sales_prior"] == 60_000
    assert report["rows"][0]["totals"]["sales_yoy"] == pytest.approx(0)
    assert report["totals"]["sales_prior"] == 60_000
    assert report["daily_totals"][3]["sales_current"] == 900_000
    assert report["daily_totals"][3]["sales_prior"] == 800_000


def test_daily_followup_completed_month_keeps_full_financial_period_totals():
    rows = [
        {
            "sale_date": date(2025, 7, 28),
            "store_code": "601",
            "department_code": "60101",
            "dimension_code": "60101",
            "sales": 90_000,
            "profit": 9_000,
        }
    ]

    report = build_daily_followup_payload(
        rows,
        financial_year=2026,
        financial_month=7,
        dimension="departments",
        as_of_date=date(2026, 7, 30),
    )

    assert report["cumulative_dates"]["end_date"] == "2026-07-28"
    assert report["cumulative_dates"]["prior_end_date"] == "2025-07-28"
    assert report["totals"]["sales_prior"] == 90_000


def test_daily_followup_special_sales_keeps_group_brand_rows_separate():
    rows = [
        {
            "sale_date": date(2026, 6, 29),
            "store_code": "601",
            "store_name": "常州百货大楼",
            "department_code": "6010101",
            "department_name": "营运一部",
            "floor_code": "16",
            "operation_method_code": "4",
            "dimension_code": "6010101999",
            "dimension_name": "一楼特卖厅",
            "brand_code": "B1",
            "brand_name": "品牌一",
            "sales": 50_000,
            "profit": 5_000,
        },
        {
            "sale_date": date(2026, 6, 29),
            "store_code": "601",
            "store_name": "常州百货大楼",
            "department_code": "6010101",
            "department_name": "营运一部",
            "floor_code": "16",
            "operation_method_code": "4",
            "dimension_code": "6010101999",
            "dimension_name": "一楼特卖厅",
            "brand_code": "B2",
            "brand_name": "品牌二",
            "sales": 30_000,
            "profit": 3_000,
        },
    ]

    report = build_daily_followup_payload(
        rows,
        financial_year=2026,
        financial_month=7,
        dimension="special_sales",
    )

    assert [
        (row["dimension_code"], row["brand_code"], row["totals"]["sales_current"])
        for row in report["rows"]
    ] == [
        ("6010101999", "B1", 50_000),
        ("6010101999", "B2", 30_000),
    ]
    assert report["totals"]["sales_current"] == 80_000


def test_daily_followup_endpoint_uses_independent_report_permission_and_scope(monkeypatch):
    from python_app.routers import sales
    from python_app.routers.authz import DataScope

    calls = {}
    monkeypatch.setattr(
        sales,
        "require_permission",
        lambda db, user, code: calls.setdefault("permission", code),
    )
    monkeypatch.setattr(
        sales,
        "load_business_scope",
        lambda db, user, **kwargs: DataScope(allow={"department": {"6030117"}}),
    )
    monkeypatch.setattr(
        sales,
        "_business_scope_filter_sql",
        lambda scope, params, **kwargs: (
            calls.setdefault("scope_kwargs", kwargs),
            " AND 1=1",
        )[1],
    )
    def fake_load_daily_followup_report(db, scope_sql, params, **kwargs):
        calls["report_kwargs"] = kwargs
        return {
            "financial_month": "2026-08",
            "rows": [],
        }

    monkeypatch.setattr(
        sales,
        "load_daily_followup_report",
        fake_load_daily_followup_report,
    )

    result = asyncio.run(
        sales.daily_followup_report(
            financial_year=2026,
            financial_month=8,
            dimension="departments",
            store_id=None,
            department_id=None,
            db=object(),
            current_user=object(),
        )
    )

    assert calls["permission"] == "sales.od0001.view"
    assert calls["scope_kwargs"]["store_expr"] == "st.store_id::text"
    assert calls["scope_kwargs"]["department_code_expr"] == "dept.mfcode"
    assert calls["scope_kwargs"]["group_expr"] == "mf.mfcode"
    assert calls["report_kwargs"]["cutoff_at_yesterday"] is True
    assert result["financial_month"] == "2026-08"
    assert "当前用户权限范围" in result["scope_description"]


def test_daily_followup_filter_options_use_independent_permission(monkeypatch):
    from python_app.routers import sales

    calls = []
    monkeypatch.setattr(
        sales,
        "_load_report_store_options",
        lambda db, user, **kwargs: calls.append(("stores", kwargs)) or [],
    )
    monkeypatch.setattr(
        sales,
        "_load_report_department_options",
        lambda db, user, store_id, **kwargs: (
            calls.append(("departments", store_id, kwargs)) or []
        ),
    )

    asyncio.run(sales.daily_followup_stores(object(), object()))
    asyncio.run(sales.daily_followup_departments(" 603 ", object(), object()))

    assert calls == [
        (
            "stores",
            {
                "permission_code": "sales.od0001.view",
                "prefix": "daily_followup_stores",
            },
        ),
        (
            "departments",
            " 603 ",
            {
                "permission_code": "sales.od0001.view",
                "prefix": "daily_followup_departments",
            },
        ),
    ]
