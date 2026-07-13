from datetime import date
from decimal import Decimal

import pytest

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
    assert "trim(both from h.mkt) = s.sglmarket::text" in compact
    assert "select distinct h.billno" in compact
    assert "case when mt.billno is not null then coalesce(s.sglxssr, 0) else 0 end" in compact


def test_query_limits_member_identification_to_scoped_base_ticket_keys():
    sql, _ = build_report_query(START, END, TrustedScopeSql(""), {})
    compact = compact_sql(sql)

    assert "join base_sales s" in compact
    assert "0::bigint as unmatched_member_ticket_count" in compact


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

    assert "left join manaframe mf" in compact
    assert "left join manaframe dept" in compact
    assert "left join stores st" in compact
    assert "left join mana_brand_hierarchy h" in compact
    assert "mf.mfchr2" in compact and "h.level3_code" in compact
    assert "mfcname" not in compact.split("left join mana_brand_hierarchy h", 1)[1].split("where", 1)[0]
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
        "unmatched_organization_sales_amount": -25.0,
        "unmatched_hierarchy_group_count": 1,
        "unmatched_hierarchy_sales_amount": -25.0,
        "missing_grade_group_count": 1,
        "missing_grade_sales_amount": -25.0,
        "unmatched_member_ticket_count": 0,
    }


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
        "unmatched_organization_sales_amount": 0.0,
        "unmatched_hierarchy_group_count": 0,
        "unmatched_hierarchy_sales_amount": 0.0,
        "missing_grade_group_count": 0,
        "missing_grade_sales_amount": 0.0,
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
