import asyncio
import os
from datetime import date

import pytest
from sqlalchemy import create_engine, text

from python_app.services.od0002_report import (
    EXCLUDED_DEPARTMENT_CODES,
    FLOOR_NAMES,
    TrustedScopeSql,
    build_authorized_departments_query,
    build_authorized_stores_query,
    build_report_query,
    compare_period,
    metric_triplet,
    load_od0002_report,
    load_od0002_authorized_stores,
    load_od0002_authorized_departments,
    normalize_rows,
)


def test_authorized_department_query_is_scope_and_store_filtered():
    sql, params = build_authorized_departments_query(
        TrustedScopeSql(" AND dept.mfcode = ANY(:allowed_departments)"),
        {"allowed_departments": ["6030117"]},
        selected_store="603",
    )

    assert ":allowed_departments" in sql
    assert ":selected_store" in sql
    assert ":excluded_department_codes" in sql
    assert params["selected_store"] == "603"
    assert params["allowed_departments"] == ["6030117"]
    assert set(params["excluded_department_codes"]) == set(EXCLUDED_DEPARTMENT_CODES)


def test_load_authorized_departments_uses_sales_dashboard_order():
    db = FakeDb([
        {"store_code": "603", "department_code": "6030102", "department_name": "中心四部(男装)"},
        {"store_code": "603", "department_code": "6030117", "department_name": "中心三部(女装)"},
    ])

    rows = load_od0002_authorized_departments(db, TrustedScopeSql(" AND 1=1"), {})

    assert [row["department_code"] for row in rows] == ["6030117", "6030102"]


def test_report_query_binds_selected_department():
    sql, params = build_report_query(
        date(2026, 1, 1), date(2026, 1, 31),
        date(2025, 1, 1), date(2025, 1, 31),
        TrustedScopeSql(" AND 1=1"), {}, None, " 6030117 ",
    )

    assert ":selected_department" in sql
    assert params["selected_department"] == "6030117"


def test_authorized_store_query_uses_master_dimensions_without_sales_or_dates():
    sql, params = build_authorized_stores_query(
        TrustedScopeSql(" AND upper(trim(COALESCE((dept.mfcode)::varchar, ''))) = ANY(:stores_allow_department)"),
        {"stores_allow_department": ["60101"]},
    )
    compact = " ".join(sql.split()).lower()

    assert "salegoodslist" not in compact
    assert "start_date" not in compact and "end_date" not in compact
    assert "from stores st" in compact
    assert "join manaframe mf" in compact
    assert "left join manaframe dept" in compact
    assert "left join area_category" in compact
    assert "mf.mflc" in compact
    assert ":stores_allow_department" in sql
    assert params == {"stores_allow_department": ["60101"]}


def test_load_authorized_stores_returns_scoped_store_without_sales():
    db = FakeDb([{"store_id": 601, "store_code": "601", "store_name": "零销售授权店"}])

    rows = load_od0002_authorized_stores(
        db,
        TrustedScopeSql(" AND 1=1"),
        {},
    )

    assert rows == [{"store_id": 601, "store_code": "601", "store_name": "零销售授权店"}]
    assert "salegoodslist" not in db.calls[0][0].lower()


def test_od0002_stores_endpoint_requires_permission_and_scope_aliases(monkeypatch):
    from python_app.routers import sales
    from python_app.routers.authz import DataScope

    calls = {}
    monkeypatch.setattr(sales, "require_permission", lambda db, user, code: calls.setdefault("permission", code))
    monkeypatch.setattr(sales, "load_business_scope", lambda db, user, **kwargs: DataScope(allow={"department": {"60101"}}))
    monkeypatch.setattr(sales, "_business_scope_filter_sql", lambda scope, params, **kwargs: (calls.setdefault("filter_kwargs", kwargs), " AND 1=1")[1])
    monkeypatch.setattr(sales, "load_od0002_authorized_stores", lambda db, scope_sql, params: [{"store_id": 601, "store_code": "601", "store_name": "零销售授权店"}])

    result = asyncio.run(sales.od0002_stores(object(), object()))

    assert calls["permission"] == "sales.od0002.view"
    assert calls["filter_kwargs"]["department_code_expr"] == "dept.mfcode"
    assert calls["filter_kwargs"]["department_name_expr"] == "dept.mfcname"
    assert calls["filter_kwargs"]["group_expr"] == "mf.mfcode"
    assert calls["filter_kwargs"]["category_code_expr"] == "ac.category_code"
    assert calls["filter_kwargs"]["category_name_expr"] == "ac.category_name"
    assert calls["filter_kwargs"]["floor_expr"] == "mf.mflc"
    assert calls["filter_kwargs"]["store_expr"] == "st.store_id::text"
    assert result[0]["store_name"] == "零销售授权店"


def test_od0002_departments_endpoint_filters_by_store_and_permission(monkeypatch):
    from python_app.routers import sales
    from python_app.routers.authz import DataScope

    calls = {}
    monkeypatch.setattr(sales, "require_permission", lambda db, user, code: calls.setdefault("permission", code))
    monkeypatch.setattr(sales, "load_business_scope", lambda db, user, **kwargs: DataScope(allow={"department": {"6030117"}}))
    monkeypatch.setattr(sales, "_business_scope_filter_sql", lambda scope, params, **kwargs: " AND 1=1")
    monkeypatch.setattr(
        sales,
        "load_od0002_authorized_departments",
        lambda db, scope_sql, params, selected_store: calls.setdefault("load", selected_store) or [],
    )

    asyncio.run(sales.od0002_departments(" 603 ", object(), object()))

    assert calls == {"permission": "sales.od0002.view", "load": "603"}


def test_selected_store_code_is_resolved_to_active_store_id_with_bound_parameter():
    from python_app.routers import sales

    class Result:
        def first(self):
            return (1,)

    class Db:
        def __init__(self):
            self.call = None

        def execute(self, statement, params):
            self.call = (str(statement), params)
            return Result()

    db = Db()
    assert sales._od0002_store_id_for_code(db, "601") == "1"
    sql, params = db.call
    assert "st.is_active IS TRUE" in sql
    assert "= :store_code" in sql
    assert params == {"store_code": "601"}


def test_compare_period_uses_same_dates_in_previous_year():
    assert compare_period(date(2026, 5, 29), date(2026, 6, 28)) == (
        date(2025, 5, 29),
        date(2025, 6, 28),
    )


def test_compare_period_clamps_leap_day():
    assert compare_period(date(2024, 2, 29), date(2024, 3, 1)) == (
        date(2023, 2, 28),
        date(2023, 3, 1),
    )


def test_compare_period_rejects_end_before_start():
    with pytest.raises(ValueError):
        compare_period(date(2026, 6, 28), date(2026, 5, 29))


def test_metric_triplet_calculates_weighted_margin_and_yoy():
    assert metric_triplet(120, 24, 100, 15) == {
        "sales_current": 120.0,
        "sales_prior": 100.0,
        "sales_yoy": 0.2,
        "profit_current": 24.0,
        "profit_prior": 15.0,
        "profit_yoy": 0.6,
        "margin_current": 0.2,
        "margin_prior": 0.15,
        "margin_change": 0.05,
    }


def test_metric_triplet_returns_none_when_denominator_is_zero():
    result = metric_triplet(0, 0, 0, 0)

    assert result["sales_yoy"] is None
    assert result["profit_yoy"] is None
    assert result["margin_current"] is None
    assert result["margin_prior"] is None
    assert result["margin_change"] is None


def test_report_constants_match_the_design():
    assert EXCLUDED_DEPARTMENT_CODES == frozenset(
        {
            "6010115",
            "6010108",
            "6010109",
            "6010110",
            "6010202",
            "6010205",
            "6020105",
            "6020107",
            "6020109",
            "6020202",
            "6020205",
            "6030108",
            "6030109",
            "6030111",
            "6030202",
            "6030205",
        }
    )
    assert FLOOR_NAMES == {
        "01": "BF",
        "02": "1F",
        "03": "2F",
        "04": "3F",
        "05": "4F",
        "06": "5F",
        "07": "6F",
        "08": "7F",
        "09": "8F",
        "10": "9F",
        "11": "10F",
        "12": "11F",
        "13": "12F",
        "14": "13F",
        "15": "14F",
        "16": "特卖",
        "17": "微商城",
        "18": "15F",
        "19": "16F",
    }


def test_build_report_query_uses_od0002_sources_filters_and_bound_params():
    scope_sql = " AND NOT (st.store_id::text = ANY(:scope_deny_store))"
    sql, params = build_report_query(
        date(2026, 5, 29),
        date(2026, 6, 28),
        date(2025, 5, 29),
        date(2025, 6, 28),
        scope_sql,
        {"scope_deny_store": ["602"]},
        selected_store="601",
    )
    compact = " ".join(sql.split()).lower()

    assert "from salegoodslist s" in compact
    assert "sum(case when s.sglhsrq" in compact
    assert "s.sglxssr" in compact
    assert "s.sgln2" in compact
    assert "join manaframe mf" in compact
    assert "join manaframe dept" in compact
    assert "join area_category_dedup ac" in compact
    assert "join stores st" in compact
    assert "s.sglmfid" in compact and "mf.mfcode" in compact
    assert "mf.mfpcode" in compact and "dept.mfcode" in compact
    assert "mf.mfchr1" in compact and "ac.category_code" in compact
    assert "s.sglwmid <> '5'" in compact
    assert "trim(both from coalesce(mf.mflc, '')) <> '00'" in compact
    assert "trim(both from coalesce(ac.area_name, '')) <> '其他类别区域'" in compact
    assert "replace(coalesce(ac.area_name" not in compact
    assert scope_sql in sql
    assert "s.sglmarket::text = :selected_store" in sql
    assert "s.sglmarket::text as store_code" in compact
    assert "st.store_name as store_name" in compact
    assert "substring(trim(both from coalesce(mf.mfcode" not in compact
    assert set(EXCLUDED_DEPARTMENT_CODES).issubset(set(params["excluded_department_codes"]))
    assert params["scope_deny_store"] == ["602"]
    assert params["selected_store"] == "601"


def test_report_query_normalizes_erp_codes_before_output_filters_and_floor_mapping():
    sql, _ = build_report_query(
        date(2026, 1, 1), date(2026, 1, 31),
        date(2025, 1, 1), date(2025, 1, 31), TrustedScopeSql(""), {},
    )
    compact = " ".join(sql.split()).lower()

    assert "trim(both from coalesce(dept.mfcode, '')) as department_code" in compact
    assert "trim(both from coalesce(mf.mfcode, '')) as group_code" in compact
    assert "trim(both from coalesce(mf.mflc, '')) as floor_code" in compact
    assert "case trim(both from coalesce(mf.mflc, ''))" in compact
    assert "trim(both from coalesce(mf.mflc, '')) <> '00'" in compact
    assert "trim(both from coalesce(dept.mfcode, '')) <> all(:excluded_department_codes)" in compact


def test_build_report_query_deduplicates_area_category_deterministically():
    sql, _ = build_report_query(
        date(2026, 1, 1), date(2026, 1, 31),
        date(2025, 1, 1), date(2025, 1, 31), TrustedScopeSql(""), {},
    )
    compact = " ".join(sql.split()).lower()

    assert "area_category_dedup as" in compact
    assert "from area_category" in compact
    assert "distinct on (upper(trim(both from category_code)))" in compact
    assert "order by upper(trim(both from category_code)), area_code, area_name, category_name" in compact
    assert "min(" not in compact  # never synthesize a dictionary row from independent minima
    assert "join area_category_dedup ac" in compact


@pytest.mark.parametrize("unsafe", [" AND 1=1; DROP TABLE stores", " AND 1=1 -- x", "/*x*/ AND 1=1"])
def test_build_report_query_rejects_untrusted_scope_sql_markers(unsafe):
    with pytest.raises(ValueError, match="scope_filter_sql"):
        build_report_query(
            date(2026, 1, 1), date(2026, 1, 31),
            date(2025, 1, 1), date(2025, 1, 31), unsafe, {},
        )


def test_build_report_query_filters_sales_dates_before_dimension_joins():
    sql, _ = build_report_query(
        date(2026, 1, 1), date(2026, 1, 31),
        date(2025, 1, 1), date(2025, 1, 31), "", {},
    )
    compact = " ".join(sql.split()).lower()

    assert "filtered_sales as" in compact
    filtered_sales = compact.split("filtered_sales as", 1)[1].split("),", 1)[0]
    assert "from salegoodslist s" in filtered_sales
    assert "sglhsrq between :start_date and :end_date" in filtered_sales


def test_build_report_query_contains_six_dimensions_and_store_grouping():
    sql, _ = build_report_query(
        date(2026, 1, 1),
        date(2026, 1, 31),
        date(2025, 1, 1),
        date(2025, 1, 31),
        "",
        {},
    )

    for dimension in ("stores", "departments", "areas", "categories", "groups", "floors"):
        assert f"'{dimension}' AS dimension_type" in sql
    for cte in ("departments", "areas", "categories", "groups", "floors"):
        section = sql.split(f"{cte} AS (", 1)[1].split("),", 1)[0]
        assert "store_code" in section.split("GROUP BY", 1)[1]


def test_normalize_rows_keeps_same_department_separate_by_store_and_builds_metrics():
    rows = [
        {
            "dimension_type": "departments", "store_code": "601", "store_name": "一店",
            "dimension_code": "D01", "dimension_name": "女装", "sales_current": 120,
            "profit_current": 24, "sales_prior": 100, "profit_prior": 15,
        },
        FakeMapping({
            "dimension_type": "departments", "store_code": "602", "store_name": "二店",
            "dimension_code": "D01", "dimension_name": "女装", "sales_current": 80,
            "profit_current": 8, "sales_prior": 100, "profit_prior": 10,
        }),
    ]

    dimensions, quality = normalize_rows(rows)

    assert [(row["store_code"], row["dimension_name"]) for row in dimensions["departments"]] == [
        ("601", "女装"), ("602", "女装")
    ]
    assert dimensions["departments"][0]["metrics"] == metric_triplet(120, 24, 100, 15)
    assert quality == {
        "unmatched_area_category_group_count": 0,
        "unmatched_floor_group_count": 0,
        "unmatched_area_category_sales_current": 0.0,
        "unmatched_floor_sales_current": 0.0,
    }


def test_normalize_rows_uses_sales_dashboard_department_order_within_each_store():
    rows = [
        {
            "dimension_type": "departments", "store_code": "603", "store_name": "新世纪",
            "dimension_code": "6030102", "dimension_name": "中心四部(男装)",
            "sales_current": 1, "profit_current": 1, "sales_prior": 1, "profit_prior": 1,
        },
        {
            "dimension_type": "departments", "store_code": "603", "store_name": "新世纪",
            "dimension_code": "6030117", "dimension_name": "中心三部(女装)",
            "sales_current": 1, "profit_current": 1, "sales_prior": 1, "profit_prior": 1,
        },
        {
            "dimension_type": "departments", "store_code": "602", "store_name": "二店",
            "dimension_code": "6020002", "dimension_name": "二部",
            "sales_current": 1, "profit_current": 1, "sales_prior": 1, "profit_prior": 1,
        },
        {
            "dimension_type": "departments", "store_code": "602", "store_name": "二店",
            "dimension_code": "6020001", "dimension_name": "一部",
            "sales_current": 1, "profit_current": 1, "sales_prior": 1, "profit_prior": 1,
        },
    ]

    dimensions, _quality = normalize_rows(rows)

    assert [
        (row["store_code"], row["dimension_code"])
        for row in dimensions["departments"]
    ] == [
        ("602", "6020001"),
        ("602", "6020002"),
        ("603", "6030117"),
        ("603", "6030102"),
    ]


def test_normalize_rows_reports_unmatched_area_and_floor_counts():
    rows = [
        {"dimension_type": "quality", "store_code": None, "store_name": None,
         "dimension_code": "unmatched_area_category", "dimension_name": "未匹配区域品类",
         "sales_current": 31, "profit_current": 2, "sales_prior": 0, "profit_prior": 0},
        FakeMapping({"dimension_type": "quality", "store_code": None, "store_name": None,
         "dimension_code": "unmatched_floor", "dimension_name": "未匹配楼层",
         "sales_current": 17, "profit_current": 3, "sales_prior": 0, "profit_prior": 0}),
    ]

    dimensions, quality = normalize_rows(rows)

    assert all(not values for values in dimensions.values())
    assert quality == {
        "unmatched_area_category_group_count": 2,
        "unmatched_floor_group_count": 3,
        "unmatched_area_category_sales_current": 31.0,
        "unmatched_floor_sales_current": 17.0,
    }


@pytest.mark.skipif(
    not os.getenv("OD0002_TEST_DATABASE_URL"),
    reason="OD0002_TEST_DATABASE_URL is not configured",
)
def test_postgresql_query_deduplicates_dictionary_and_preserves_store_totals():
    engine = create_engine(os.environ["OD0002_TEST_DATABASE_URL"])
    with engine.connect() as connection, connection.begin():
        connection.execute(text("""
            CREATE TEMP TABLE salegoodslist (
              sglmarket integer, sglmfid text, sglhsrq date, sglxssr numeric,
              sgln2 numeric, sglwmid text
            ) ON COMMIT DROP;
            CREATE TEMP TABLE manaframe (
              mfcode text, mfcname text, mfpcode text, mfchr1 text, mflc text
            ) ON COMMIT DROP;
            CREATE TEMP TABLE area_category (
              area_code text, area_name text, category_code text, category_name text
            ) ON COMMIT DROP;
            CREATE TEMP TABLE stores (store_code text, store_name text) ON COMMIT DROP;
        """))
        connection.execute(text("""
            INSERT INTO stores VALUES ('601', '一店'), ('602', '二店');
            INSERT INTO manaframe VALUES
              ('D1', '部门一', '0', NULL, NULL), ('D2', '部门二', '0', NULL, NULL),
              ('G1', '柜组一', 'D1', 'C1', '02'), ('G2', '柜组二', 'D2', 'C1', '02');
            INSERT INTO area_category VALUES
              ('A1', 'Z区域', 'C1', 'Z品类'), ('A9', 'A区域', ' C1 ', 'A品类');
            INSERT INTO salegoodslist VALUES
              (601, 'G1', DATE '2026-01-10', 100, 20, '1'),
              (602, 'G2', DATE '2026-01-10', 200, 40, '1');
        """))
        sql, params = build_report_query(
            date(2026, 1, 1), date(2026, 1, 31),
            date(2025, 1, 1), date(2025, 1, 31),
            TrustedScopeSql(" AND s.sglmarket::text = ANY(:allowed_stores)"),
            {"allowed_stores": ["601", "602"]},
        )
        rows = connection.execute(text(sql), params).mappings().all()

    dimensions, _ = normalize_rows(rows)
    expected = {"601": 100.0, "602": 200.0}
    for dimension_type in ("stores", "departments", "areas", "categories", "groups", "floors"):
        totals = {}
        for row in dimensions[dimension_type]:
            totals[row["store_code"]] = totals.get(row["store_code"], 0) + row["metrics"]["sales_current"]
        assert totals == expected
    assert {
        (row["dimension_code"], row["dimension_name"])
        for row in dimensions["areas"]
    } == {("A1", "Z区域")}
    assert {
        (row["dimension_code"], row["dimension_name"])
        for row in dimensions["categories"]
    } == {("C1", "Z品类")}


class FakeMapping:
    """Minimal SQLAlchemy RowMapping-like object (Mapping protocol without dict type)."""

    def __init__(self, values):
        self._values = values

    def keys(self):
        return self._values.keys()

    def __getitem__(self, key):
        return self._values[key]


class FakeDbResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows


class FakeDb:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def execute(self, statement, params):
        self.calls.append((str(statement), params))
        return FakeDbResult(self.rows)


def test_load_od0002_report_executes_bound_query_and_builds_weighted_totals():
    rows = [
        {"dimension_type": "stores", "store_code": "601", "store_name": "一店",
         "dimension_code": "601", "dimension_name": "一店", "sales_current": 100,
         "profit_current": 10, "sales_prior": 80, "profit_prior": 8},
        {"dimension_type": "stores", "store_code": "602", "store_name": "二店",
         "dimension_code": "602", "dimension_name": "二店", "sales_current": 300,
         "profit_current": 60, "sales_prior": 120, "profit_prior": 12},
    ]
    db = FakeDb(rows)

    payload = load_od0002_report(
        db,
        TrustedScopeSql(" AND s.sglmarket::text = ANY(:scope_allow_store)"),
        {"scope_allow_store": ["601", "602"]},
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        prior_start_date=date(2025, 1, 1),
        prior_end_date=date(2025, 1, 31),
        selected_store=None,
    )

    assert len(db.calls) == 1
    sql, params = db.calls[0]
    assert ":start_date" in sql and ":scope_allow_store" in sql
    assert params["start_date"] == date(2026, 1, 1)
    assert params["scope_allow_store"] == ["601", "602"]
    assert payload["dates"] == {
        "start_date": date(2026, 1, 1), "end_date": date(2026, 1, 31),
        "prior_start_date": date(2025, 1, 1), "prior_end_date": date(2025, 1, 31),
    }
    assert set(payload["dimensions"]) == set(
        (
            "stores",
            "departments",
            "department_categories",
            "areas",
            "categories",
            "groups",
            "floors",
        )
    )
    assert payload["totals"]["stores"] == metric_triplet(400, 70, 200, 20)
    assert all(row["total"] == payload["totals"]["stores"] for row in payload["dimensions"]["stores"])
    assert payload["selected_store"] is None
    assert payload["quality"]["unmatched_floor_group_count"] == 0
    assert payload["generated_at"]


def test_report_query_adds_department_category_dimension_without_merging_departments():
    sql, _ = build_report_query(
        date(2026, 1, 1),
        date(2026, 1, 31),
        date(2025, 1, 1),
        date(2025, 1, 31),
        TrustedScopeSql(""),
        {},
    )
    compact = " ".join(sql.lower().split())

    assert "department_categories as" in compact
    block = compact.split("department_categories as", 1)[1].split("), areas as", 1)[0]
    assert "'department_categories' as dimension_type" in block
    assert "department_code" in block
    assert "area_code" in block
    assert "category_code" in block
    assert "group by store_code, store_name, department_code, department_name" in block
    assert "area_code, area_name, category_code, category_name" in block
    assert "union all select * from department_categories" in compact


def test_normalize_rows_builds_category_area_and_department_rows_in_order():
    rows = [
        {
            "dimension_type": "department_categories",
            "store_code": "603",
            "store_name": "商城",
            "department_code": "6030102",
            "department_name": "新世纪二部",
            "area_code": "A1",
            "area_name": "女装区",
            "category_code": "C2",
            "category_name": "中淑女装",
            "dimension_code": "C2",
            "dimension_name": "中淑女装",
            "sales_current": 50,
            "profit_current": 5,
            "sales_prior": 40,
            "profit_prior": 4,
        },
        {
            "dimension_type": "department_categories",
            "store_code": "603",
            "store_name": "商城",
            "department_code": "6030102",
            "department_name": "新世纪二部",
            "area_code": "A1",
            "area_name": "女装区",
            "category_code": "C1",
            "category_name": "中式女装",
            "dimension_code": "C1",
            "dimension_name": "中式女装",
            "sales_current": 30,
            "profit_current": 3,
            "sales_prior": 20,
            "profit_prior": 2,
        },
    ]

    dimensions, _ = normalize_rows(rows)
    hierarchy = dimensions["department_categories"]

    assert [row["row_type"] for row in hierarchy] == [
        "category",
        "category",
        "area_subtotal",
        "department_subtotal",
    ]
    assert [row["category_code"] for row in hierarchy[:2]] == ["C1", "C2"]
    assert hierarchy[2]["metrics"]["sales_current"] == 80
    assert hierarchy[3]["metrics"]["sales_current"] == 80


def test_load_report_total_counts_only_department_category_detail_rows():
    rows = [
        {
            "dimension_type": "department_categories",
            "store_code": "603",
            "store_name": "商城",
            "department_code": "D1",
            "department_name": "一部",
            "area_code": "A1",
            "area_name": "女装区",
            "category_code": "C1",
            "category_name": "女装",
            "dimension_code": "C1",
            "dimension_name": "女装",
            "sales_current": 100,
            "profit_current": 20,
            "sales_prior": 80,
            "profit_prior": 16,
        }
    ]
    payload = load_od0002_report(
        FakeDb(rows),
        TrustedScopeSql(""),
        {},
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        prior_start_date=date(2025, 1, 1),
        prior_end_date=date(2025, 1, 31),
    )

    assert payload["totals"]["department_categories"]["sales_current"] == 100


def test_department_category_reuses_base_permission_and_department_filter():
    scope = " AND s.sglmarket::text = ANY(:scope_allow_store)"
    sql, params = build_report_query(
        date(2026, 1, 1),
        date(2026, 1, 31),
        date(2025, 1, 1),
        date(2025, 1, 31),
        TrustedScopeSql(scope),
        {"scope_allow_store": ["603"]},
        selected_store="603",
        selected_department="6030102",
    )
    compact = " ".join(sql.split())
    base = compact.split("base AS", 1)[1].split("), stores AS", 1)[0]

    assert scope in base
    assert "s.sglmarket::text = :selected_store" in base
    assert "= UPPER(:selected_department)" in base
    assert params["scope_allow_store"] == ["603"]
    assert params["selected_department"] == "6030102"


def test_od0002_route_requires_permission_scope_and_builds_expected_alias_scope(monkeypatch):
    from python_app.routers import sales
    from python_app.routers.authz import DataScope

    calls = {}
    scope = DataScope(all_access=False, allow={"store": {"601"}})
    monkeypatch.setattr(sales, "require_permission", lambda db, user, code: calls.setdefault("permission", code))
    monkeypatch.setattr(sales, "load_business_scope", lambda db, user, **kwargs: (calls.setdefault("scope_kwargs", kwargs), scope)[1])
    monkeypatch.setattr(sales, "_business_scope_filter_sql", lambda scope, params, **kwargs: (calls.setdefault("filter_kwargs", kwargs), " AND 1=1")[1])
    monkeypatch.setattr(sales, "load_od0002_report", lambda db, scope_sql, params, **kwargs: {
        "scope_sql": scope_sql.value, "params": params, "kwargs": kwargs
    })

    result = asyncio.run(sales.od0002_report(date(2026, 1, 1), date(2026, 1, 31), None, object(), object()))

    assert calls["permission"] == "sales.od0002.view"
    assert calls["scope_kwargs"] == {"fallback_resource_code": "sales"}
    assert calls["filter_kwargs"] == {
        "prefix": "od0002", "store_expr": "st.store_id::text",
        "department_code_expr": "dept.mfcode", "department_name_expr": "dept.mfcname",
        "group_expr": "mf.mfcode", "category_code_expr": "ac.category_code",
        "category_name_expr": "ac.category_name", "floor_expr": "mf.mflc",
    }
    assert result["scope_sql"] == " AND 1=1"
    assert result["kwargs"]["prior_start_date"] == date(2025, 1, 1)


def test_od0002_route_rejects_end_before_start_with_422():
    from fastapi import HTTPException
    from python_app.routers import sales

    with pytest.raises(HTTPException) as exc:
        asyncio.run(sales.od0002_report(date(2026, 2, 1), date(2026, 1, 31), None, object(), object()))
    assert exc.value.status_code == 422


def test_od0002_route_rejects_selected_store_outside_scope(monkeypatch):
    from fastapi import HTTPException
    from python_app.routers import sales
    from python_app.routers.authz import DataScope

    monkeypatch.setattr(sales, "require_permission", lambda *args: None)
    monkeypatch.setattr(sales, "load_business_scope", lambda *args, **kwargs: DataScope(allow={"store": {"601"}}))
    monkeypatch.setattr(sales, "_od0002_store_id_for_code", lambda db, code: "2")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(sales.od0002_report(date(2026, 1, 1), date(2026, 1, 31), "602", object(), object()))
    assert exc.value.status_code == 403


def test_od0002_route_allows_selected_store_when_store_id_is_explicitly_allowed(monkeypatch):
    from python_app.routers import sales
    from python_app.routers.authz import DataScope

    monkeypatch.setattr(sales, "require_permission", lambda *args: None)
    monkeypatch.setattr(sales, "load_business_scope", lambda *args, **kwargs: DataScope(allow={"store": {"1"}}))
    monkeypatch.setattr(sales, "_od0002_store_id_for_code", lambda db, code: "1")
    monkeypatch.setattr(sales, "load_od0002_report", lambda *args, **kwargs: {"selected_store": kwargs["selected_store"]})

    result = asyncio.run(
        sales.od0002_report(date(2026, 1, 1), date(2026, 1, 31), "601", object(), object())
    )

    assert result == {"selected_store": "601"}


@pytest.mark.parametrize(
    ("dimension", "value"),
    [
        ("department", "D01"),
        ("group", "G01"),
        ("category", "C01"),
        ("floor", "02"),
    ],
)
def test_od0002_route_allows_store_selection_for_non_store_scopes(
    monkeypatch, dimension, value
):
    from python_app.routers import sales
    from python_app.routers.authz import DataScope

    monkeypatch.setattr(sales, "require_permission", lambda *args: None)
    monkeypatch.setattr(sales, "_od0002_store_id_for_code", lambda db, code: "1")
    monkeypatch.setattr(
        sales,
        "load_business_scope",
        lambda *args, **kwargs: DataScope(allow={dimension: {value}}),
    )
    monkeypatch.setattr(
        sales,
        "load_od0002_report",
        lambda *args, **kwargs: {"selected_store": kwargs["selected_store"]},
    )

    result = asyncio.run(
        sales.od0002_report(
            date(2026, 1, 1), date(2026, 1, 31), "601", object(), object()
        )
    )

    assert result == {"selected_store": "601"}


def test_od0002_route_rejects_explicitly_denied_store(monkeypatch):
    from fastapi import HTTPException
    from python_app.routers import sales
    from python_app.routers.authz import DataScope

    monkeypatch.setattr(sales, "require_permission", lambda *args: None)
    monkeypatch.setattr(
        sales,
        "load_business_scope",
        lambda *args, **kwargs: DataScope(all_access=True, deny={"store": {"1"}}),
    )
    monkeypatch.setattr(sales, "_od0002_store_id_for_code", lambda db, code: "1")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            sales.od0002_report(
                date(2026, 1, 1), date(2026, 1, 31), "601", object(), object()
            )
        )
    assert exc.value.status_code == 403


def test_od0002_route_preserves_union_semantics_for_mixed_store_and_department_allow(
    monkeypatch,
):
    from python_app.routers import sales
    from python_app.routers.authz import DataScope

    monkeypatch.setattr(sales, "require_permission", lambda *args: None)
    monkeypatch.setattr(sales, "_od0002_store_id_for_code", lambda db, code: "2")
    monkeypatch.setattr(
        sales,
        "load_business_scope",
        lambda *args, **kwargs: DataScope(
            allow={"store": {"1"}, "department": {"D01"}}
        ),
    )
    monkeypatch.setattr(
        sales,
        "load_od0002_report",
        lambda *args, **kwargs: {"selected_store": kwargs["selected_store"]},
    )

    result = asyncio.run(
        sales.od0002_report(
            date(2026, 1, 1), date(2026, 1, 31), "602", object(), object()
        )
    )

    assert result == {"selected_store": "602"}


def test_od0002_route_honors_all_access_despite_residual_store_allow(monkeypatch):
    from python_app.routers import sales
    from python_app.routers.authz import DataScope

    monkeypatch.setattr(sales, "require_permission", lambda *args: None)
    monkeypatch.setattr(
        sales,
        "load_business_scope",
        lambda *args, **kwargs: DataScope(
            all_access=True, allow={"store": {"601"}}
        ),
    )
    monkeypatch.setattr(
        sales,
        "load_od0002_report",
        lambda *args, **kwargs: {"selected_store": kwargs["selected_store"]},
    )

    result = asyncio.run(
        sales.od0002_report(
            date(2026, 1, 1), date(2026, 1, 31), "602", object(), object()
        )
    )

    assert result == {"selected_store": "602"}


@pytest.mark.parametrize(
    ("raw_store_id", "expected_store_id"),
    [(" 601 ", "601"), ("   ", None)],
)
def test_od0002_route_normalizes_selected_store(
    monkeypatch, raw_store_id, expected_store_id
):
    from python_app.routers import sales
    from python_app.routers.authz import DataScope

    monkeypatch.setattr(sales, "require_permission", lambda *args: None)
    monkeypatch.setattr(
        sales,
        "load_business_scope",
        lambda *args, **kwargs: DataScope(all_access=True),
    )
    monkeypatch.setattr(
        sales,
        "load_od0002_report",
        lambda *args, **kwargs: {"selected_store": kwargs["selected_store"]},
    )

    result = asyncio.run(
        sales.od0002_report(
            date(2026, 1, 1),
            date(2026, 1, 31),
            raw_store_id,
            object(),
            object(),
        )
    )

    assert result == {"selected_store": expected_store_id}


def test_load_od0002_report_returns_complete_empty_structure():
    payload = load_od0002_report(
        FakeDb([]), TrustedScopeSql(""), {}, start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31), prior_start_date=date(2025, 1, 1),
        prior_end_date=date(2025, 1, 31), selected_store="601",
    )

    assert payload["selected_store"] == "601"
    assert all(rows == [] for rows in payload["dimensions"].values())
    assert all(total == metric_triplet(0, 0, 0, 0) for total in payload["totals"].values())
