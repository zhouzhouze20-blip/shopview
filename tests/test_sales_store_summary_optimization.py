from pathlib import Path
import re
from unittest.mock import patch

from python_app.routers import sales
from python_app.routers.authz import DataScope


def _compact(sql: str) -> str:
    return " ".join(sql.lower().split())


def test_store_comparison_uses_one_permission_scoped_scan_for_two_full_years():
    captured = {"calls": 0}
    scope = DataScope(allow={"store": {"604"}})

    def fake_fetch(_db, sql, params):
        captured["calls"] += 1
        captured["sql"] = _compact(sql)
        captured["params"] = params
        return [
            {
                "store_id": "604",
                "department_count": 8,
                "group_count": 120,
                "ticket_count": 1000,
                "quantity": 1500,
                "gross_sales": 200000,
                "effective_sales": 200000,
                "net_profit": 40000,
                "net_margin": 0.2,
                "ticket_margin": 0.2,
                "same_period_effective_sales": 180000,
                "same_period_net_profit": 36000,
                "same_period_ticket_count": 900,
                "same_period_margin": 0.2,
            }
        ]

    with (
        patch.object(sales, "_salegoodslist_table", lambda _db: "salegoodslist"),
        patch.object(sales, "_table_exists", lambda _db, table: table in {"manaframe", "stores"}),
        patch.object(sales, "_fetch_mappings", fake_fetch),
    ):
        rows = sales._store_summary_rows_with_comparison(
            object(),
            scope=scope,
            start_date="2026-01-01",
            end_date="2026-12-31",
            prior_start_date="2025-01-01",
            prior_end_date="2025-12-31",
            limit=200,
        )

    assert captured["calls"] == 1
    assert captured["sql"].count("from salegoodslist s") == 1
    assert "case when s.sglhsrq >= cast(:current_start_date as date)" in captured["sql"]
    assert "case when s.sglhsrq >= cast(:prior_start_date as date)" in captured["sql"]
    assert "store_summary_allow_store" in captured["sql"]
    assert captured["params"]["store_summary_allow_store"] == ["604"]
    assert captured["params"]["current_start_date"] == "2026-01-01"
    assert captured["params"]["current_end_date"] == "2026-12-31"
    assert captured["params"]["prior_start_date"] == "2025-01-01"
    assert captured["params"]["prior_end_date"] == "2025-12-31"
    assert rows[0]["same_period_effective_sales"] == 180000


def test_store_comparison_applies_both_optional_sales_exclusions_in_the_same_scan():
    captured = {}
    scope = DataScope(all_access=True)

    def fake_fetch(_db, sql, params):
        captured["sql"] = _compact(sql)
        captured["params"] = params
        return []

    with (
        patch.object(sales, "_salegoodslist_table", lambda _db: "salegoodslist"),
        patch.object(sales, "_table_exists", lambda _db, table: table in {"manaframe", "stores"}),
        patch.object(sales, "_fetch_mappings", fake_fetch),
    ):
        sales._store_summary_rows_with_comparison(
            object(),
            scope=scope,
            start_date="2026-07-01",
            end_date="2026-07-31",
            prior_start_date="2025-07-01",
            prior_end_date="2025-07-31",
            limit=200,
            exclude_rental=True,
            exclude_backoffice_departments=True,
        )

    assert "trim(both from coalesce(s.sglwmid, '')) <> '5'" in captured["sql"]
    assert "trim(both from coalesce(cg.department_name, '')) not in" in captured["sql"]
    assert "'中心营运部'" in captured["sql"]
    assert "'大楼信息'" in captured["sql"]


def test_sales_summary_timeout_is_relaxed_only_for_cross_month_queries():
    class FakeDb:
        def __init__(self):
            self.statements = []

        def execute(self, statement):
            self.statements.append(_compact(str(statement)))

    single_month_db = FakeDb()
    sales._configure_sales_summary_timeout(
        single_month_db,
        start_date="2026-08-01",
        end_date="2026-08-21",
    )
    assert single_month_db.statements == []

    cross_month_db = FakeDb()
    sales._configure_sales_summary_timeout(
        cross_month_db,
        start_date="2026-01-01",
        end_date="2026-08-21",
    )
    assert cross_month_db.statements == ["set local statement_timeout = '90s'"]


def test_sales_date_index_migration_is_concurrent_and_date_first():
    migration = Path(
        "python_app/alembic/versions/q5e6f7a8b9c0_optimize_sales_store_summary.py"
    ).read_text(encoding="utf-8")
    compact = _compact(migration)

    assert "create index concurrently if not exists" in compact
    assert "on salegoodslist (sglhsrq, sglmarket, sglmfid, sglbillno)" in compact
    assert "autocommit_block" in compact


def test_nginx_allows_sales_summary_to_finish_after_database_long_range_limit():
    source = (Path(__file__).parents[1] / "config" / "nginx.conf").read_text()
    match = re.search(
        r"location \^~ /api/sales/summary/ \{(?P<body>.*?)\n\s*\}",
        source,
        re.DOTALL,
    )

    assert match is not None
    assert "proxy_read_timeout 100s;" in match.group("body")
