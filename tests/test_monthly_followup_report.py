import asyncio
from datetime import date

import pytest

from python_app.services.monthly_followup_report import (
    build_monthly_followup_payload,
    financial_month_period,
    financial_year_period,
)


def test_financial_year_contains_twelve_financial_months():
    assert financial_year_period(2026) == (
        date(2026, 1, 1),
        date(2026, 12, 31),
    )
    assert financial_month_period(2026, 1) == (
        date(2026, 1, 1),
        date(2026, 1, 28),
    )
    assert financial_month_period(2026, 12) == (
        date(2026, 11, 29),
        date(2026, 12, 31),
    )


def test_march_financial_month_metadata_handles_leap_years_without_overlap():
    report = build_monthly_followup_payload(
        [],
        financial_year=2024,
        dimension="departments",
        as_of_date=date(2024, 2, 29),
    )

    march = report["months"][2]
    assert march["start_date"] == "2024-02-29"
    assert march["prior_start_date"] == "2023-03-01"
    assert march["comparison_end"] == "2024-02-29"
    assert march["prior_comparison_end"] is None


def test_monthly_payload_splits_financial_months_and_aligns_prior_year():
    rows = [
        {
            "sale_date": date(2026, 1, 1),
            "store_code": "603",
            "department_code": "60301",
            "department_name": "中心一部",
            "dimension_code": "60301",
            "dimension_name": "中心一部",
            "sales": 120_000,
            "profit": 24_000,
        },
        {
            "sale_date": date(2025, 1, 1),
            "store_code": "603",
            "department_code": "60301",
            "department_name": "中心一部",
            "dimension_code": "60301",
            "dimension_name": "中心一部",
            "sales": 100_000,
            "profit": 15_000,
        },
        {
            "sale_date": date(2026, 1, 29),
            "store_code": "603",
            "department_code": "60301",
            "department_name": "中心一部",
            "dimension_code": "60301",
            "dimension_name": "中心一部",
            "sales": 80_000,
            "profit": 16_000,
        },
        {
            "sale_date": date(2026, 12, 31),
            "store_code": "603",
            "department_code": "60301",
            "department_name": "中心一部",
            "dimension_code": "60301",
            "dimension_name": "中心一部",
            "sales": 30_000,
            "profit": 6_000,
        },
        {
            "sale_date": date(2025, 12, 31),
            "store_code": "603",
            "department_code": "60301",
            "department_name": "中心一部",
            "dimension_code": "60301",
            "dimension_name": "中心一部",
            "sales": 20_000,
            "profit": 4_000,
        },
    ]

    report = build_monthly_followup_payload(
        rows,
        financial_year=2026,
        dimension="departments",
        as_of_date=date(2026, 12, 31),
    )

    assert report["dates"] == {
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "prior_start_date": "2025-01-01",
        "prior_end_date": "2025-12-31",
    }
    assert len(report["months"]) == 12
    january = report["rows"][0]["monthly"][0]
    february = report["rows"][0]["monthly"][1]
    assert january["sales_current"] == 120_000
    assert january["sales_prior"] == 100_000
    assert january["sales_yoy"] == pytest.approx(0.2)
    assert february["sales_current"] == 80_000
    december = report["rows"][0]["monthly"][11]
    assert december["sales_current"] == 30_000
    assert december["sales_prior"] == 20_000
    assert report["months"][11]["end_date"] == "2026-12-31"
    assert report["totals"]["sales_current"] == 230_000


def test_current_financial_month_and_prior_are_both_cut_off_at_same_day():
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
            "sale_date": date(2025, 8, 10),
            "store_code": "601",
            "department_code": "60101",
            "dimension_code": "60101",
            "sales": 900_000,
            "profit": 90_000,
        },
        {
            "sale_date": date(2025, 9, 1),
            "store_code": "601",
            "department_code": "60101",
            "dimension_code": "60101",
            "sales": 700_000,
            "profit": 70_000,
        },
    ]

    report = build_monthly_followup_payload(
        rows,
        financial_year=2026,
        dimension="departments",
        as_of_date=date(2026, 7, 30),
    )

    august = report["rows"][0]["monthly"][7]
    september = report["rows"][0]["monthly"][8]
    assert august["sales_current"] == 50_000
    assert august["sales_prior"] == 40_000
    assert august["sales_yoy"] == pytest.approx(0.25)
    assert september["sales_current"] == 0
    assert september["sales_prior"] == 0
    assert report["months"][7]["comparison_end"] == "2026-07-30"
    assert report["months"][7]["prior_comparison_end"] == "2025-07-30"
    assert report["months"][8]["comparison_end"] is None


def test_od0004_endpoint_uses_independent_permission_and_scope(monkeypatch):
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
    monkeypatch.setattr(
        sales,
        "load_monthly_followup_report",
        lambda db, scope_sql, params, **kwargs: {
            "financial_year": kwargs["financial_year"],
            "rows": [],
        },
    )

    result = asyncio.run(
        sales.od0004_report(
            financial_year=2026,
            dimension="departments",
            store_id=None,
            department_id=None,
            db=object(),
            current_user=object(),
        )
    )

    assert calls["permission"] == "sales.od0004.view"
    assert calls["scope_kwargs"]["store_expr"] == "st.store_id::text"
    assert calls["scope_kwargs"]["department_code_expr"] == "dept.mfcode"
    assert calls["scope_kwargs"]["group_expr"] == "mf.mfcode"
    assert result["financial_year"] == 2026
    assert "当前用户权限范围" in result["scope_description"]


def test_od0004_filter_options_use_independent_permission(monkeypatch):
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

    asyncio.run(sales.od0004_stores(object(), object()))
    asyncio.run(sales.od0004_departments(" 603 ", object(), object()))

    assert calls == [
        (
            "stores",
            {
                "permission_code": "sales.od0004.view",
                "prefix": "od0004_stores",
            },
        ),
        (
            "departments",
            " 603 ",
            {
                "permission_code": "sales.od0004.view",
                "prefix": "od0004_departments",
            },
        ),
    ]
