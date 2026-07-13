import asyncio
import os
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text

from python_app.services.hdyy01_report import (
    TrustedScopeSql,
    build_report_payload,
    build_report_query,
    load_hdyy01_report,
    normalize_row,
)
from python_app.services.od0002_report import EXCLUDED_DEPARTMENT_CODES


START = date(2026, 7, 1)
END = date(2026, 7, 10)


def test_hdyy01_permission_is_registered_independently():
    from python_app.routers.authz import CORE_PERMISSION_DEFINITIONS

    assert (
        "sales.hdyy01.view",
        "查看HDYY01柜组经营分析表",
        "sales",
        "hdyy01_view",
    ) in CORE_PERMISSION_DEFINITIONS


def test_hdyy01_stores_endpoint_requires_permission_and_option_scope_aliases(monkeypatch):
    from python_app.routers import sales
    from python_app.routers.authz import DataScope

    calls = {}
    monkeypatch.setattr(sales, "require_permission", lambda db, user, code: calls.setdefault("permission", code))
    monkeypatch.setattr(sales, "load_business_scope", lambda db, user, **kwargs: (calls.setdefault("scope_kwargs", kwargs), DataScope(all_access=True))[1])
    monkeypatch.setattr(sales, "_business_scope_filter_sql", lambda scope, params, **kwargs: (calls.setdefault("filter_kwargs", kwargs), " AND 1=1")[1])
    monkeypatch.setattr(sales, "load_od0002_authorized_stores", lambda db, scope_sql, params: [{"store_code": "601"}])

    result = asyncio.run(sales.hdyy01_stores(object(), object()))

    assert result == [{"store_code": "601"}]
    assert calls["permission"] == "sales.hdyy01.view"
    assert calls["scope_kwargs"] == {"fallback_resource_code": "sales"}
    assert calls["filter_kwargs"] == {
        "prefix": "hdyy01_stores", "store_expr": "st.store_id::text",
        "department_code_expr": "dept.mfcode", "department_name_expr": "dept.mfcname",
        "group_expr": "mf.mfcode", "category_code_expr": "ac.category_code",
        "category_name_expr": "ac.category_name", "floor_expr": "mf.mflc",
    }


def test_hdyy01_departments_endpoint_trims_store_and_uses_option_scope_aliases(monkeypatch):
    from python_app.routers import sales
    from python_app.routers.authz import DataScope

    calls = {}
    monkeypatch.setattr(sales, "require_permission", lambda db, user, code: calls.setdefault("permission", code))
    monkeypatch.setattr(sales, "load_business_scope", lambda *args, **kwargs: DataScope(all_access=True))
    monkeypatch.setattr(sales, "_business_scope_filter_sql", lambda scope, params, **kwargs: (calls.setdefault("filter_kwargs", kwargs), " AND 1=1")[1])
    def fake_load_departments(db, scope_sql, params, store):
        calls["store"] = store
        return []

    monkeypatch.setattr(sales, "load_od0002_authorized_departments", fake_load_departments)

    result = asyncio.run(sales.hdyy01_departments(" 603 ", object(), object()))

    assert result == []
    assert calls["permission"] == "sales.hdyy01.view"
    assert calls["store"] == "603"
    assert calls["filter_kwargs"] == {
        "prefix": "hdyy01_departments", "store_expr": "st.store_id::text",
        "department_code_expr": "dept.mfcode", "department_name_expr": "dept.mfcname",
        "group_expr": "mf.mfcode", "category_code_expr": "ac.category_code",
        "category_name_expr": "ac.category_name", "floor_expr": "mf.mflc",
    }


def test_hdyy01_route_uses_independent_permission_main_aliases_and_loads_once(monkeypatch):
    from python_app.routers import sales
    from python_app.routers.authz import DataScope

    calls = {"loads": 0}
    monkeypatch.setattr(sales, "require_permission", lambda db, user, code: calls.setdefault("permission", code))
    monkeypatch.setattr(sales, "load_business_scope", lambda db, user, **kwargs: (calls.setdefault("scope_kwargs", kwargs), DataScope(all_access=True))[1])
    monkeypatch.setattr(sales, "_business_scope_filter_sql", lambda scope, params, **kwargs: (calls.setdefault("filter_kwargs", kwargs), " AND 1=1")[1])

    def fake_load(db, scope_sql, params, **kwargs):
        calls["loads"] += 1
        calls["load"] = (scope_sql, params, kwargs)
        return {"ok": True}

    monkeypatch.setattr(sales, "load_hdyy01_report", fake_load)

    result = asyncio.run(sales.hdyy01_report(START, END, " 603 ", object(), object(), " D01 "))

    assert result == {"ok": True}
    assert calls["permission"] == "sales.hdyy01.view"
    assert calls["scope_kwargs"] == {"fallback_resource_code": "sales"}
    assert calls["loads"] == 1
    assert calls["filter_kwargs"] == {
        "prefix": "hdyy01", "store_expr": "st.store_id::text",
        "department_code_expr": "dept.mfcode", "department_name_expr": "dept.mfcname",
        "group_expr": "s.sglmfid", "category_code_expr": "h.level2_code",
        "category_name_expr": "h.level2_name", "floor_expr": "mf.mflc",
    }
    assert calls["load"][0].value == " AND 1=1"
    assert calls["load"][2]["selected_store"] == "603"
    assert calls["load"][2]["selected_department"] == "D01"


def test_hdyy01_route_rejects_end_before_start_with_422():
    from fastapi import HTTPException
    from python_app.routers import sales

    with pytest.raises(HTTPException) as exc:
        asyncio.run(sales.hdyy01_report(date(2026, 7, 2), date(2026, 7, 1), None, object(), object()))
    assert exc.value.status_code == 422


def test_hdyy01_route_rejects_selected_store_outside_explicit_store_scope(monkeypatch):
    from fastapi import HTTPException
    from python_app.routers import sales
    from python_app.routers.authz import DataScope

    monkeypatch.setattr(sales, "require_permission", lambda *args: None)
    monkeypatch.setattr(sales, "load_business_scope", lambda *args, **kwargs: DataScope(allow={"store": {"1"}}))
    monkeypatch.setattr(sales, "_od0002_store_id_for_code", lambda db, code: "2")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(sales.hdyy01_report(START, END, "602", object(), object()))
    assert exc.value.status_code == 403


def test_hdyy01_route_allows_selected_store_explicitly_allowed(monkeypatch):
    from python_app.routers import sales
    from python_app.routers.authz import DataScope

    monkeypatch.setattr(sales, "require_permission", lambda *args: None)
    monkeypatch.setattr(sales, "load_business_scope", lambda *args, **kwargs: DataScope(allow={"store": {"1"}}))
    monkeypatch.setattr(sales, "_od0002_store_id_for_code", lambda db, code: "1")
    monkeypatch.setattr(sales, "load_hdyy01_report", lambda *args, **kwargs: {"store": kwargs["selected_store"]})

    assert asyncio.run(sales.hdyy01_report(START, END, "601", object(), object())) == {"store": "601"}


def test_hdyy01_route_preserves_mixed_scope_union_semantics(monkeypatch):
    from python_app.routers import sales
    from python_app.routers.authz import DataScope

    monkeypatch.setattr(sales, "require_permission", lambda *args: None)
    monkeypatch.setattr(sales, "load_business_scope", lambda *args, **kwargs: DataScope(allow={"store": {"1"}, "department": {"D01"}}))
    monkeypatch.setattr(sales, "_od0002_store_id_for_code", lambda db, code: "2")
    monkeypatch.setattr(sales, "load_hdyy01_report", lambda *args, **kwargs: {"store": kwargs["selected_store"]})

    assert asyncio.run(sales.hdyy01_report(START, END, "602", object(), object())) == {"store": "602"}


def test_hdyy01_route_honors_all_access_despite_residual_store_allow(monkeypatch):
    from python_app.routers import sales
    from python_app.routers.authz import DataScope

    monkeypatch.setattr(sales, "require_permission", lambda *args: None)
    monkeypatch.setattr(sales, "load_business_scope", lambda *args, **kwargs: DataScope(all_access=True, allow={"store": {"1"}}))
    monkeypatch.setattr(sales, "_od0002_store_id_for_code", lambda *args: pytest.fail("all_access must not resolve the selected store"))
    monkeypatch.setattr(sales, "load_hdyy01_report", lambda *args, **kwargs: {"store": kwargs["selected_store"]})

    assert asyncio.run(sales.hdyy01_report(START, END, "602", object(), object())) == {"store": "602"}


def test_hdyy01_route_applies_store_deny_before_all_access(monkeypatch):
    from fastapi import HTTPException
    from python_app.routers import sales
    from python_app.routers.authz import DataScope

    monkeypatch.setattr(sales, "require_permission", lambda *args: None)
    monkeypatch.setattr(sales, "load_business_scope", lambda *args, **kwargs: DataScope(all_access=True, deny={"store": {"1"}}))
    monkeypatch.setattr(sales, "_od0002_store_id_for_code", lambda db, code: "1")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(sales.hdyy01_report(START, END, "601", object(), object()))
    assert exc.value.status_code == 403


@pytest.mark.parametrize(
    ("dimension", "denied", "deny_expression", "resolution_guard"),
    [
        ("store", "1", "st.store_id::text", "st.store_id IS NOT NULL"),
        ("department", "D01", "dept.mfcode", "dept.normalized_mfcode IS NOT NULL"),
        ("group", "G01", "s.sglmfid", None),
        ("category", "C01", "h.level2_code", "h.normalized_level3_code IS NOT NULL"),
        (
            "floor",
            "02",
            "mf.mflc",
            "mf.normalized_mfcode IS NOT NULL AND NULLIF(TRIM(BOTH FROM COALESCE(mf.mflc, '')), '') IS NOT NULL",
        ),
    ],
)
def test_hdyy01_main_scope_denies_are_stable_when_dimensions_are_unresolved(
    monkeypatch, dimension, denied, deny_expression, resolution_guard
):
    from python_app.routers import sales
    from python_app.routers.authz import DataScope

    scope = DataScope(all_access=True, deny={dimension: {denied}})
    captured = {}
    monkeypatch.setattr(sales, "require_permission", lambda *args: None)
    monkeypatch.setattr(sales, "load_business_scope", lambda *args, **kwargs: scope)
    monkeypatch.setattr(
        sales,
        "load_hdyy01_report",
        lambda db, scope_sql, params, **kwargs: captured.update(
            scope_sql=scope_sql.value, params=params
        ) or {},
    )

    asyncio.run(sales.hdyy01_report(START, END, None, object(), object()))

    assert f"hdyy01_deny_{dimension}" in captured["params"]
    assert deny_expression in captured["scope_sql"]
    if resolution_guard is None:
        assert all(
            guard not in captured["scope_sql"]
            for guard in (
                "st.store_id IS NOT NULL",
                "dept.normalized_mfcode IS NOT NULL",
                "h.normalized_level3_code IS NOT NULL",
                "mf.normalized_mfcode IS NOT NULL",
            )
        )
    else:
        assert resolution_guard in captured["scope_sql"]


def test_hdyy01_all_deny_remains_unconditionally_closed():
    from python_app.routers import sales
    from python_app.routers.authz import DataScope

    scope = DataScope(all_access=True, deny={"__all__": {"*"}, "store": {"1"}})
    params = {}
    generated = sales._business_scope_filter_sql(
        scope,
        params,
        prefix="hdyy01",
        store_expr="st.store_id::text",
    )

    assert generated == " AND 1=0"
    assert sales._hdyy01_deny_resolution_guard_sql(scope) == ""


@pytest.mark.parametrize(
    ("raw_store", "raw_department", "expected_store", "expected_department"),
    [(" 601 ", " D01 ", "601", "D01"), ("   ", "  ", None, None)],
)
def test_hdyy01_route_trims_selected_filters(monkeypatch, raw_store, raw_department, expected_store, expected_department):
    from python_app.routers import sales
    from python_app.routers.authz import DataScope

    monkeypatch.setattr(sales, "require_permission", lambda *args: None)
    monkeypatch.setattr(sales, "load_business_scope", lambda *args, **kwargs: DataScope(all_access=True))
    monkeypatch.setattr(sales, "load_hdyy01_report", lambda *args, **kwargs: kwargs)

    result = asyncio.run(sales.hdyy01_report(START, END, raw_store, object(), object(), raw_department))
    assert result["selected_store"] == expected_store
    assert result["selected_department"] == expected_department


def test_hdyy01_export_route_is_not_registered_yet():
    from python_app.routers import sales

    assert not any(route.path == "/api/sales/reports/hdyy01/export" for route in sales.router.routes)


def compact_sql(sql):
    return " ".join(sql.lower().split())


def report_row(**overrides):
    row = {
        "store_code": "603",
        "store_name": "新世纪",
        "department_code": "6030117",
        "department_name": "中心三部",
        "group_code": "G01",
        "group_name": "A柜组",
        "area": Decimal("10.5"),
        "floor_code": "02",
        "level1_code": "10",
        "level1_name": "服装",
        "level2_code": "1001",
        "level2_name": "女装",
        "grade_label": "A",
        "quantity": Decimal("2"),
        "sales_amount": Decimal("100"),
        "tax_cost": Decimal("60"),
        "profit": Decimal("40"),
        "ticket_count": 1,
        "member_sales": Decimal("80"),
        "stored_card_sales": Decimal("30"),
        "unmatched_member_ticket_count": 0,
    }
    row.update(overrides)
    return row


def test_query_keeps_signed_returns_and_counts_only_positive_net_tickets():
    sql, params = build_report_query(
        START,
        END,
        TrustedScopeSql(" AND 1=1"),
        {},
        " 603 ",
        " 6030117 ",
    )
    compact = compact_sql(sql)
    base = compact.split("base_sales as", 1)[1].split("ticket_sales as", 1)[0]

    assert "sum(coalesce(s.sglsl, 0)) as quantity" in compact
    assert "sum(coalesce(s.sglxssr, 0)) as sales_amount" in compact
    assert "sum(coalesce(s.sgln13, 0) + coalesce(s.sgln14, 0) - coalesce(s.sglsupzk, 0)) as tax_cost" in compact
    assert "sum(coalesce(s.sgln2, 0)) as profit" in compact
    assert "sum(coalesce(s.sglfcard, 0)) as stored_card_sales" in compact
    assert "sum(coalesce(sglxssr, 0)) as ticket_sales" in compact
    assert "count(*) filter (where ticket_sales > 0)" in compact
    assert "sglxssr > 0" not in base
    assert params["selected_store"] == "603"
    assert params["selected_department"] == "6030117"


def test_query_preserves_store_department_group_grain_and_deterministic_order():
    sql, _ = build_report_query(START, END, TrustedScopeSql(""), {})
    compact = compact_sql(sql)

    assert "group by 1, 3, 5" in compact
    assert "group by sglmarket::text, group_code, sglhsrq, sglbillno" in compact
    assert "group by store_code, group_code" in compact
    assert "order by gm.store_code, gm.department_code, gm.group_code" in compact


def test_query_identifies_members_by_nonempty_card_and_both_ticket_keys():
    sql, _ = build_report_query(START, END, TrustedScopeSql(""), {})
    compact = compact_sql(sql)

    assert "from salehead h" in compact
    assert "nullif(trim(both from coalesce(h.hykh, '')), '') is not null" in compact
    assert "h.billno = s.sglbillno" in compact
    assert "trim(both from h.mkt) = s.store_code" in compact
    assert "select distinct h.billno" in compact
    assert "case when mt.billno is not null then coalesce(s.sglxssr, 0) else 0 end" in compact


def test_query_limits_member_identification_to_scoped_base_ticket_keys():
    sql, _ = build_report_query(START, END, TrustedScopeSql(""), {})
    compact = compact_sql(sql)

    assert "scoped_ticket_keys as" in compact
    assert "select distinct sglmarket::text as store_code, sglbillno" in compact
    assert "join scoped_ticket_keys s" in compact
    assert "0::bigint as unmatched_member_ticket_count" in compact


def test_query_uses_unique_normalized_dimensions_without_arbitrary_winners():
    sql, _ = build_report_query(START, END, TrustedScopeSql(""), {})
    compact = compact_sql(sql)

    assert "manaframe_normalized as" in compact
    assert "stores_normalized as" in compact
    assert "hierarchy_normalized as" in compact
    assert compact.count("count(*) over (") >= 3
    assert compact.count("partition by") >= 3
    assert "manaframe_unique as" in compact
    assert "stores_unique as" in compact
    assert "hierarchy_unique as" in compact
    assert compact.count("normalized_match_count = 1") >= 3
    assert "left join manaframe_unique mf" in compact
    assert "left join manaframe_unique dept" in compact
    assert "left join stores_unique st" in compact
    assert "left join hierarchy_unique h" in compact
    assert "distinct on" not in compact


def test_store_uniqueness_counts_only_active_store_mappings():
    sql, _ = build_report_query(START, END, TrustedScopeSql(""), {})
    compact = compact_sql(sql)
    stores = compact.split("stores_normalized as materialized", 1)[1].split(
        "stores_unique as materialized", 1
    )[0]

    assert "from stores source where source.is_active is true" in stores


def test_base_projects_used_columns_and_member_date_filter_is_sargable():
    sql, _ = build_report_query(START, END, TrustedScopeSql(""), {})
    compact = compact_sql(sql)
    base = compact.split("base_sales as materialized", 1)[1].split(") ,", 1)[0]

    assert "select s.*" not in compact
    assert "s.sglmarket" in base
    assert "s.sglbillno" in base
    assert "h.rqsj >= :start_date" in compact
    assert "h.rqsj < :end_date + interval '1 day'" in compact
    assert "h.rqsj::date" not in compact


def test_query_uses_left_organization_and_code_hierarchy_joins_and_filters():
    scope = " AND mf.mfcode = ANY(:scope_allow_group)"
    sql, params = build_report_query(
        START,
        END,
        TrustedScopeSql(scope),
        {"scope_allow_group": ["G01"]},
        selected_store="603",
        selected_department="6030117",
    )
    compact = compact_sql(sql)

    assert "left join manaframe_unique mf" in compact
    assert "left join manaframe_unique dept" in compact
    assert "left join stores_unique st" in compact
    assert "left join hierarchy_unique h" in compact
    assert "mf.mfchr2" in compact and "h.normalized_level3_code" in compact
    assert "mfcname" not in compact.split("left join hierarchy_unique h", 1)[1].split("where", 1)[0]
    assert "s.sglhsrq between :start_date and :end_date" in compact
    assert "s.sglwmid is null or s.sglwmid <> '5'" in compact
    assert ":excluded_department_codes" in compact
    assert scope in sql
    assert "s.sglmarket::text = :selected_store" in compact
    assert "upper(trim(both from coalesce(dept.mfcode, ''))) = upper(:selected_department)" in compact
    assert params["scope_allow_group"] == ["G01"]
    assert set(params["excluded_department_codes"]) == set(EXCLUDED_DEPARTMENT_CODES)


@pytest.mark.parametrize(
    "unsafe",
    [" AND 1=1; DROP TABLE stores", " AND 1=1 -- x", "/*x*/ AND 1=1"],
)
def test_query_rejects_scope_statement_and_comment_markers(unsafe):
    with pytest.raises(ValueError, match="scope_filter_sql"):
        build_report_query(START, END, unsafe, {})


def test_normalize_row_preserves_hierarchy_and_grade_values():
    row = normalize_row(report_row(grade_label="D"))

    assert row["level1_code"] == "10"
    assert row["level1_name"] == "服装"
    assert row["level2_code"] == "1001"
    assert row["level2_name"] == "女装"
    assert row["grade_label"] == "D"
    assert row["area"] == 10.5
    assert row["average_ticket"] == 100.0


def test_payload_keeps_same_group_separate_between_stores():
    payload = build_report_payload(
        [
            report_row(store_code="601", store_name="一店", group_code="G01"),
            report_row(store_code="602", store_name="二店", group_code="G01", sales_amount=200),
        ],
        start_date=START,
        end_date=END,
    )

    assert [(row["store_code"], row["group_code"]) for row in payload["rows"]] == [
        ("601", "G01"),
        ("602", "G01"),
    ]
    assert payload["total"]["sales_amount"] == 300.0


def test_return_row_reduces_signed_metrics_and_member_sales_without_ticket_count():
    payload = build_report_payload(
        [
            report_row(
                quantity=-1,
                sales_amount=-100,
                tax_cost=-60,
                profit=-40,
                ticket_count=0,
                member_sales=-100,
                stored_card_sales=-50,
            )
        ],
        start_date=START,
        end_date=END,
    )
    row = payload["rows"][0]

    assert {key: row[key] for key in (
        "quantity", "sales_amount", "tax_cost", "profit", "member_sales", "stored_card_sales"
    )} == {
        "quantity": -1.0,
        "sales_amount": -100.0,
        "tax_cost": -60.0,
        "profit": -40.0,
        "member_sales": -100.0,
        "stored_card_sales": -50.0,
    }
    assert row["ticket_count"] == 0
    assert row["average_ticket"] is None


def test_null_ticket_count_has_null_average_and_totals_are_weighted():
    payload = build_report_payload(
        [
            report_row(sales_amount=100, ticket_count=None),
            report_row(store_code="602", sales_amount=300, ticket_count=3),
        ],
        start_date=START,
        end_date=END,
    )

    assert payload["rows"][0]["average_ticket"] is None
    assert payload["rows"][1]["average_ticket"] == 100.0
    assert payload["total"]["sales_amount"] == 400.0
    assert payload["total"]["ticket_count"] == 3
    assert payload["total"]["average_ticket"] == pytest.approx(400 / 3)


def test_missing_dimensions_render_unmatched_and_feed_signed_quality_metrics():
    payload = build_report_payload(
        [
            report_row(
                store_name=None,
                department_code=None,
                department_name=" ",
                group_name=None,
                level1_code=None,
                level1_name=None,
                level2_code=None,
                level2_name=None,
                grade_label=None,
                sales_amount=-25,
                unmatched_member_ticket_count=0,
            ),
            report_row(store_code="602", grade_label="B", sales_amount=100),
        ],
        start_date=START,
        end_date=END,
    )
    missing = payload["rows"][0]

    assert missing["department_code"] is None
    assert missing["level2_code"] is None
    for key in ("store_name", "department_name", "group_name", "level1_name", "level2_name", "grade_label"):
        assert missing[key] == "未匹配"
    assert payload["quality"] == {
        "unmatched_organization_group_count": 1,
        "unmatched_organization_amount": -25.0,
        "unmatched_hierarchy_group_count": 1,
        "unmatched_hierarchy_amount": -25.0,
        "missing_grade_group_count": 1,
        "missing_grade_amount": -25.0,
        "unmatched_member_ticket_count": 0,
    }


@pytest.mark.parametrize(
    "missing_field",
    ["level1_code", "level1_name", "level2_code", "level2_name"],
)
def test_hierarchy_quality_requires_every_level_code_and_name(missing_field):
    payload = build_report_payload(
        [report_row(**{missing_field: None})],
        start_date=START,
        end_date=END,
    )

    assert payload["quality"]["unmatched_hierarchy_group_count"] == 1
    assert payload["quality"]["unmatched_hierarchy_amount"] == 100.0


def test_empty_payload_has_complete_zero_totals_and_quality():
    payload = build_report_payload([], start_date=START, end_date=END)

    assert payload["dates"] == {"start_date": START, "end_date": END}
    assert payload["selected_store"] is None
    assert payload["selected_department"] is None
    assert payload["rows"] == []
    assert payload["total"] == {
        "quantity": 0.0,
        "sales_amount": 0.0,
        "tax_cost": 0.0,
        "profit": 0.0,
        "ticket_count": 0,
        "member_sales": 0.0,
        "stored_card_sales": 0.0,
        "average_ticket": None,
    }
    assert payload["quality"] == {
        "unmatched_organization_group_count": 0,
        "unmatched_organization_amount": 0.0,
        "unmatched_hierarchy_group_count": 0,
        "unmatched_hierarchy_amount": 0.0,
        "missing_grade_group_count": 0,
        "missing_grade_amount": 0.0,
        "unmatched_member_ticket_count": 0,
    }
    assert payload["generated_at"].endswith("+00:00")


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def all(self):
        return self.rows


class FakeDb:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def execute(self, statement, params):
        self.calls.append((str(statement), params))
        return FakeResult(self.rows)


def test_load_report_executes_one_bound_statement_and_builds_payload():
    db = FakeDb([report_row()])

    payload = load_hdyy01_report(
        db,
        TrustedScopeSql(" AND mf.mfcode = ANY(:allowed_groups)"),
        {"allowed_groups": ["G01"]},
        start_date=START,
        end_date=END,
        selected_store=" 603 ",
        selected_department=" 6030117 ",
    )

    assert len(db.calls) == 1
    sql, params = db.calls[0]
    assert ":start_date" in sql and ":allowed_groups" in sql
    assert params["start_date"] == START
    assert params["allowed_groups"] == ["G01"]
    assert params["selected_store"] == "603"
    assert params["selected_department"] == "6030117"
    assert payload["selected_store"] == "603"
    assert payload["selected_department"] == "6030117"
    assert payload["rows"][0]["sales_amount"] == 100.0


@pytest.mark.skipif(
    not os.getenv("HDYY01_TEST_DATABASE_URL"),
    reason="HDYY01_TEST_DATABASE_URL is not configured",
)
def test_postgresql_query_preserves_signed_scoped_facts_without_dimension_amplification():
    engine = create_engine(os.environ["HDYY01_TEST_DATABASE_URL"])
    with engine.connect() as connection, connection.begin():
        connection.execute(text("""
            CREATE TEMP TABLE salegoodslist (
              sglmarket integer, sglmfid text, sglhsrq date, sglbillno text,
              sglsl numeric, sglxssr numeric, sgln13 numeric, sgln14 numeric,
              sglsupzk numeric, sgln2 numeric, sglfcard numeric, sglwmid text
            ) ON COMMIT DROP;
            CREATE TEMP TABLE salehead (
              billno text, mkt text, rqsj timestamp, hykh text
            ) ON COMMIT DROP;
            CREATE TEMP TABLE manaframe (
              mfcode text, mfcname text, mfpcode text, mfyymj numeric,
              mflc text, mfchr2 text
            ) ON COMMIT DROP;
            CREATE TEMP TABLE stores (
              store_code text, store_name text, is_active boolean
            ) ON COMMIT DROP;
            CREATE TEMP TABLE mana_brand_hierarchy (
              level1_code text, level1_name text, level2_code text,
              level2_name text, level3_code text, grade_label text
            ) ON COMMIT DROP;
        """))
        connection.execute(text("""
            INSERT INTO stores VALUES
              ('601', '一店', true), ('601', '已停用同码门店', false),
              ('602', '二店', true), ('603', '未授权店', true);
            INSERT INTO manaframe VALUES
              ('D1', '部门一', NULL, NULL, NULL, NULL),
              ('G1', '柜组一', 'D1', 10, '02', 'C1'),
              ('GC', '冲突柜组甲', 'D1', 20, '03', 'C1'),
              (' gc ', '冲突柜组乙', 'D1', 30, '04', 'C1');
            INSERT INTO mana_brand_hierarchy VALUES
              ('L1', '一级', 'L2', '二级', 'C1', 'A');
            INSERT INTO salegoodslist VALUES
              (601, 'G1', DATE '2026-07-01', 'B1', 1, 100, 60, 0, 0, 40, 20, '1'),
              (601, 'G1', DATE '2026-07-02', 'B2', -1, -30, -18, 0, 0, -12, -5, '1'),
              (601, 'G1', DATE '2026-07-03', 'B3', 1, 50, 30, 0, 0, 20, 0, '1'),
              (602, 'G1', DATE '2026-07-01', 'B1', 2, 200, 120, 0, 0, 80, 40, '1'),
              (601, 'GC', DATE '2026-07-04', 'BC', 1, 25, 15, 0, 0, 10, 0, '1'),
              (603, 'G1', DATE '2026-07-01', 'BX', 9, 999, 600, 0, 0, 399, 0, '1');
            INSERT INTO salehead VALUES
              ('B1', '601', TIMESTAMP '2026-07-01 10:00:00', 'M1'),
              ('B2', '601', TIMESTAMP '2026-07-02 10:00:00', 'M1'),
              ('B1', '602', TIMESTAMP '2026-07-01 11:00:00', 'M2'),
              ('BX', '603', TIMESTAMP '2026-07-01 12:00:00', 'M3');
        """))

        payload = load_hdyy01_report(
            connection,
            TrustedScopeSql(" AND s.sglmarket::text = ANY(:allowed_stores)"),
            {"allowed_stores": ["601", "602"]},
            start_date=START,
            end_date=END,
        )

    rows = {(row["store_code"], row["group_code"]): row for row in payload["rows"]}
    assert set(rows) == {("601", "G1"), ("602", "G1"), ("601", "GC")}
    assert rows[("601", "G1")]["sales_amount"] == 120.0
    assert rows[("601", "G1")]["store_name"] == "一店"
    assert rows[("601", "G1")]["quantity"] == 1.0
    assert rows[("601", "G1")]["tax_cost"] == 72.0
    assert rows[("601", "G1")]["profit"] == 48.0
    assert rows[("601", "G1")]["ticket_count"] == 2
    assert rows[("601", "G1")]["member_sales"] == 70.0
    assert rows[("602", "G1")]["sales_amount"] == 200.0
    assert rows[("602", "G1")]["member_sales"] == 200.0
    assert rows[("601", "GC")]["sales_amount"] == 25.0
    assert rows[("601", "GC")]["group_name"] == "未匹配"
    assert payload["total"]["sales_amount"] == 345.0
    assert payload["quality"]["unmatched_organization_group_count"] == 1
