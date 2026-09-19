from decimal import Decimal
from pathlib import Path
import sys

from fastapi import HTTPException
from sqlalchemy.exc import OperationalError


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_app"))

from routers import activity_analysis


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows


class _Db:
    def __init__(self, rows=()):
        self.rows = rows
        self.calls = []
        self.rolled_back = False

    def execute(self, statement, params=None):
        self.calls.append((str(statement), params or {}))
        return _Result(self.rows)

    def rollback(self):
        self.rolled_back = True


def test_star_member_predicate_keeps_explicit_null_filter_for_planner_statistics():
    sql = activity_analysis._star_diamond_member_where("m")

    assert "m.is_star_diamond_member IS NOT NULL" in sql
    assert "COALESCE(m.is_star_diamond_member" not in sql
    assert "NOT IN ('0', 'N', 'NO', 'FALSE', '否', '不是', '非')" in sql


def test_ticket_loader_uses_member_array_and_sargable_half_open_date_range():
    db = _Db(
        [
            {
                "billno": Decimal("123"),
                "member_no": "M001",
                "sale_time": "2026-08-01 12:00:00",
            }
        ]
    )

    rows = activity_analysis._load_star_diamond_tickets(
        db,
        ["M001"],
        "2026-07-23",
        "2026-08-22",
    )

    sql, params = db.calls[0]
    assert rows[0]["member_no"] == "M001"
    assert "= ANY(CAST(:member_nos AS text[]))" in sql
    assert "h.rqsj >= CAST(:start_date AS date)" in sql
    assert "h.rqsj < CAST(:end_date AS date) + INTERVAL '1 day'" in sql
    assert "h.rqsj::date" not in sql
    assert params["member_nos"] == ["M001"]


def test_overview_builder_preserves_counts_amounts_and_service_segments():
    members = [
        {"member_no": "M001"},
        {"member_no": "M002"},
        {"member_no": "M003"},
    ]
    sales_rows = [
        {
            "member_no": "M001",
            "overview_ticket_count": 2,
            "sales_amount": Decimal("12000"),
            "overview_net_profit": Decimal("1200"),
        },
        {
            "member_no": "M002",
            "overview_ticket_count": 1,
            "sales_amount": Decimal("500"),
            "overview_net_profit": Decimal("50"),
        },
    ]
    categories = [{"category_code": "01", "sales_amount": Decimal("12500")}]

    result = activity_analysis._build_star_diamond_overview(members, sales_rows, categories)

    assert result["summary"] == {
        "star_member_count": 3,
        "active_member_count": 2,
        "ticket_count": 3,
        "sales_amount": 12500.0,
        "net_profit": 1250.0,
        "avg_ticket_amount": 4166.666666666667,
        "avg_member_amount": 6250.0,
        "repeat_member_count": 1,
        "silent_member_count": 1,
        "high_value_member_count": 1,
        "nurture_member_count": 1,
    }
    assert {row["segment"] for row in result["service_segments"]} == {
        "待唤醒",
        "高价值维护",
        "潜力培育",
    }
    assert result["top_categories"][0]["sales_amount"] == 12500.0


def test_statement_timeout_is_reported_as_gateway_timeout():
    db = _Db()

    def timeout():
        raise OperationalError(
            "SELECT 1",
            {},
            RuntimeError("canceling statement due to statement timeout"),
        )

    try:
        activity_analysis._execute_star_diamond_query(db, timeout)
    except HTTPException as exc:
        assert exc.status_code == 504
        assert "查询超时" in exc.detail
    else:
        raise AssertionError("expected HTTPException")

    assert db.rolled_back is True
    assert "SET LOCAL statement_timeout = '60s'" in db.calls[0][0]


def test_detail_loaders_keep_index_lookup_correlated_for_year_to_date_tickets():
    # More tickets previously let the planner hash all salegoodslist rows.
    tickets = [{"billno": i, "member_no": "M001", "sale_time": "2026-09-12 12:00:00"} for i in range(12000)]
    db = _Db()
    activity_analysis._load_star_diamond_member_sales(db, tickets, include_preferences=False)
    activity_analysis._load_star_diamond_member_sales(db, tickets, include_preferences=True)
    activity_analysis._load_star_diamond_category_sales(db, tickets)
    activity_analysis._load_star_diamond_trail_rows(db, tickets[:300])
    for sql, params in db.calls:
        assert "JOIN LATERAL" in sql
        assert "WHERE detail.sglbillno = t.billno" in sql
        assert "OFFSET 0" in sql
        assert "sglmarket =" not in sql  # Preserve existing detail scope.
        assert params["ticket_billnos"][0] == 0
    assert "LEFT JOIN LATERAL" in db.calls[0][0]  # Keep tickets without details.
    assert len(db.calls[0][1]["ticket_billnos"]) == 12000


def test_empty_ticket_sets_skip_all_detail_queries():
    db = _Db()
    assert activity_analysis._load_star_diamond_member_sales(db, [], include_preferences=True) == []
    assert activity_analysis._load_star_diamond_category_sales(db, []) == []
    assert activity_analysis._load_star_diamond_trail_rows(db, []) == []
    assert db.calls == []


def test_overall_dimensions_use_the_same_scoped_ticket_lookup_as_overview():
    tickets = [{"billno": 1, "member_no": "M001", "sale_time": "2026-09-12 12:00:00"}]
    db = _Db([{"sales_amount": Decimal("-12.50"), "member_count": 1}])
    brands, departments = activity_analysis._load_star_diamond_overall_dimensions(db, tickets)
    assert brands == departments == [{"sales_amount": -12.5, "member_count": 1}]
    assert len(db.calls) == 2
    for sql, params in db.calls:
        assert "JOIN LATERAL" in sql
        assert "WHERE detail.sglbillno = t.billno" in sql
        assert "OFFSET 0" in sql
        assert "FROM salehead" not in sql
        assert "COUNT(DISTINCT t.member_no)" in sql
        assert "COUNT(DISTINCT t.billno)" in sql
        assert "SUM(COALESCE(s.sglxssr, 0))" in sql
        assert "sglmarket =" not in sql
        assert params["ticket_billnos"] == [1]
        assert params["ticket_member_nos"] == ["M001"]


def test_overall_dimensions_skip_queries_for_no_tickets():
    db = _Db()
    assert activity_analysis._load_star_diamond_overall_dimensions(db, []) == ([], [])
    assert db.calls == []


def _stub_overall_dependencies(monkeypatch):
    for name in ("require_permission", "_ensure_required_tables", "_require_center_store_scope"):
        monkeypatch.setattr(activity_analysis, name, lambda *args: None)
    async def overview(*args):
        return {"summary": {"star_member_count": 1, "active_member_count": 1}, "service_segments": [], "top_categories": []}
    async def rows(*args):
        return []
    monkeypatch.setattr(activity_analysis, "star_diamond_overview", overview)
    monkeypatch.setattr(activity_analysis, "star_diamond_members", rows)
    monkeypatch.setattr(activity_analysis, "star_diamond_trails", rows)
    monkeypatch.setattr(activity_analysis, "_load_star_diamond_members", lambda db: [{"member_no": "M001"}])


def test_overall_analysis_returns_504_for_dimension_timeout_before_calling_ai(monkeypatch):
    import asyncio
    import pytest
    _stub_overall_dependencies(monkeypatch)
    monkeypatch.setattr(activity_analysis, "_load_star_diamond_tickets", lambda *args: [])
    def timeout(*args):
        raise OperationalError("SELECT", {}, RuntimeError("canceling statement due to statement timeout"))
    monkeypatch.setattr(activity_analysis, "_load_star_diamond_overall_dimensions", timeout)
    def unexpected_ai(*args, **kwargs):
        pytest.fail("AI must not be called after data collection fails")
    monkeypatch.setattr(activity_analysis, "generate_ai_report", unexpected_ai)
    db = _Db()
    with pytest.raises(HTTPException) as error:
        asyncio.run(activity_analysis.star_diamond_overall_analysis(
            {"start_date": "2026-01-01", "end_date": "2026-09-12"}, db, object(),
        ))
    assert error.value.status_code == 504
    assert "查询超时" in error.value.detail
    assert db.rolled_back


def test_overall_analysis_preserves_period_and_passes_dimensions_to_ai(monkeypatch):
    import asyncio
    _stub_overall_dependencies(monkeypatch)
    calls = []
    tickets = [{"billno": 1, "member_no": "M001", "sale_time": "2026-09-12 12:00:00"}]
    def load_tickets(db, member_nos, start, end):
        calls.append((member_nos, start, end))
        return tickets
    monkeypatch.setattr(activity_analysis, "_load_star_diamond_tickets", load_tickets)
    received = []
    def ai(payload, **kwargs):
        assert kwargs["min_output_tokens"] == 8192
        received.append(payload)
        return {"status": "success", "report": "测试方案"}
    monkeypatch.setattr(activity_analysis, "generate_ai_report", ai)
    db = _Db([{"sales_amount": Decimal("100.25")}])
    result = asyncio.run(activity_analysis.star_diamond_overall_analysis(
        {"start_date": "2026-01-01", "end_date": "2026-09-12"}, db, object(),
    ))
    assert calls == [(["M001"], "2026-01-01", "2026-09-12")]
    assert result["top_brands"] == result["top_departments"] == [{"sales_amount": 100.25}]
    assert received[0]["top_brands"] == result["top_brands"]
    assert received[0]["period"]["end_date"] == "2026-09-12"
    assert result["ai"]["report"] == "测试方案"
