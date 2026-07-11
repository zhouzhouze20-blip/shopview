import sys
from pathlib import Path
import re
from types import SimpleNamespace
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_app"))

from services.activity_analysis.point_rules import (
    point_rule_source_tables,
    point_status_case_sql,
)
from services.department_display_order import department_display_sort_key


class ActivityPointsRuleSqlTest(unittest.TestCase):
    def test_source_tables_include_required_erp_dependencies(self):
        self.assertEqual(
            point_rule_source_tables(),
            (
                "order_point",
                "salegoodslist",
                "sellpaygoods",
                "paymode",
                "tktqtype",
                "tktqtypemkt",
                "card_paymoderule",
                "rulejfrate",
            ),
        )

    def test_status_case_exposes_degraded_calculation_states(self):
        sql = point_status_case_sql()

        self.assertIn("MISSING_RATE", sql)
        self.assertIn("ZERO_RATE", sql)
        self.assertIn("ALLOCATION_IMBALANCE", sql)
        self.assertIn("POINT_DIFF", sql)
        self.assertIn("OK", sql)


class ActivityPointsRouterContractTest(unittest.TestCase):
    def test_points_date_range_clamps_to_activity_start(self):
        from routers.activity_analysis import _points_effective_date_range

        self.assertEqual(
            _points_effective_date_range("2026-07-01", "2026-07-10"),
            ("2026-07-09", "2026-07-11"),
        )
        self.assertIsNone(_points_effective_date_range("2026-07-01", "2026-07-08"))

    def test_points_date_range_rejects_reversed_or_invalid_dates(self):
        from fastapi import HTTPException
        from routers.activity_analysis import _points_effective_date_range

        with self.assertRaises(HTTPException) as reversed_error:
            _points_effective_date_range("2026-07-10", "2026-07-09")
        self.assertEqual(reversed_error.exception.status_code, 400)

        with self.assertRaises(HTTPException) as invalid_error:
            _points_effective_date_range("2026/07/09", "2026-07-10")
        self.assertEqual(invalid_error.exception.status_code, 400)

    def test_empty_points_dashboard_keeps_the_response_contract(self):
        from routers.activity_analysis import _empty_points_dashboard_response

        response = _empty_points_dashboard_response()
        self.assertEqual(response["summary"], {})
        for key in ("department_options", "departments", "groups", "members", "tickets", "source_status"):
            self.assertEqual(response[key], [])

    def test_pre_activity_dashboard_returns_before_business_table_checks(self):
        import asyncio
        from unittest.mock import patch
        from routers import activity_analysis as router

        with (
            patch.object(router, "require_permission") as permission,
            patch.object(router, "_ensure_required_tables", side_effect=AssertionError("business tables inspected")),
            patch.object(router, "_ensure_point_rule_tables", side_effect=AssertionError("point tables inspected")),
            patch.object(router, "load_business_scope", side_effect=AssertionError("business scope loaded")),
            patch.object(router, "_one", side_effect=AssertionError("business query executed")),
        ):
            response = asyncio.run(
                router.points_dashboard(
                    start_date="2026-07-01",
                    end_date="2026-07-08",
                    department_name=None,
                    group_code=None,
                    member_no=None,
                    keyword=None,
                    limit=200,
                    db=object(),
                    current_user=object(),
                )
            )

        permission.assert_called_once()
        self.assertEqual(response, router._empty_points_dashboard_response())

    def test_other_points_endpoints_return_exact_pre_activity_responses(self):
        import asyncio
        from unittest.mock import patch
        from routers import activity_analysis as router

        cases = (
            (
                router.points_department_options,
                {},
                {"items": []},
            ),
            (
                router.points_overview,
                {"department_code": None, "group_code": None},
                {"summary": {}, "source_status": []},
            ),
            (
                router.points_departments,
                {"department_code": None, "group_code": None, "limit": 200},
                {"items": [], "source_status": []},
            ),
            (
                router.points_members,
                {"department_code": None, "group_code": None, "keyword": None, "limit": 200},
                {"items": [], "source_status": []},
            ),
            (
                router.points_tickets,
                {
                    "department_code": None,
                    "group_code": None,
                    "member_no": None,
                    "status_filter": None,
                    "limit": 200,
                },
                {"items": [], "source_status": []},
            ),
        )

        for endpoint, endpoint_kwargs, expected in cases:
            with self.subTest(endpoint=endpoint.__name__):
                with (
                    patch.object(router, "require_permission") as permission,
                    patch.object(router, "_ensure_required_tables", side_effect=AssertionError("business tables inspected")),
                    patch.object(router, "_ensure_point_rule_tables", side_effect=AssertionError("point tables inspected")),
                    patch.object(router, "load_business_scope", side_effect=AssertionError("business scope loaded")),
                    patch.object(router, "_rows", side_effect=AssertionError("business query executed")),
                    patch.object(router, "_one", side_effect=AssertionError("business query executed")),
                ):
                    response = asyncio.run(
                        endpoint(
                            start_date="2026-07-01",
                            end_date="2026-07-08",
                            db=object(),
                            current_user=object(),
                            **endpoint_kwargs,
                        )
                    )

                permission.assert_called_once()
                self.assertEqual(response, expected)

    def test_points_query_timeout_is_local_and_maps_to_504(self):
        from fastapi import HTTPException
        from sqlalchemy.exc import OperationalError
        from routers.activity_analysis import _execute_points_query

        class FakeDb:
            def __init__(self):
                self.statements = []
                self.rolled_back = False

            def execute(self, statement, params=None):
                self.statements.append(str(statement))

            def rollback(self):
                self.rolled_back = True

        for message in ("canceling statement due to statement timeout", "QueryCanceled"):
            with self.subTest(message=message):
                db = FakeDb()
                timeout = OperationalError("SELECT", {}, RuntimeError(message))

                with self.assertRaises(HTTPException) as raised:
                    _execute_points_query(db, lambda: (_ for _ in ()).throw(timeout))

                self.assertEqual(raised.exception.status_code, 504)
                self.assertEqual(raised.exception.detail, "中心年中庆活动数据查询超时")
                self.assertTrue(db.rolled_back)
                self.assertTrue(any("statement_timeout = '60s'" in statement for statement in db.statements))

    def test_points_query_preserves_other_operational_errors(self):
        from sqlalchemy.exc import OperationalError
        from routers.activity_analysis import _execute_points_query

        class FakeDb:
            rolled_back = False

            def execute(self, statement, params=None):
                return None

            def rollback(self):
                self.rolled_back = True

        db = FakeDb()
        connection_error = OperationalError("SELECT", {}, RuntimeError("connection reset"))

        with self.assertRaises(OperationalError) as raised:
            _execute_points_query(db, lambda: (_ for _ in ()).throw(connection_error))

        self.assertIs(raised.exception, connection_error)
        self.assertFalse(db.rolled_back)

    def test_all_points_endpoints_use_effective_half_open_ranges_and_timeout_wrapper(self):
        import inspect
        from routers import activity_analysis as router

        endpoints = (
            router.points_department_options,
            router.points_dashboard,
            router.points_overview,
            router.points_departments,
            router.points_members,
            router.points_tickets,
        )

        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint.__name__):
                source = inspect.getsource(endpoint)
                compact_source = re.sub(r"\s+", " ", source)
                self.assertLess(source.index("require_permission"), source.index("_points_effective_date_range"))
                self.assertLess(source.index("_points_effective_date_range"), source.index("_ensure_required_tables"))
                self.assertIn('"start_date": effective_start_date', source)
                self.assertIn('"end_exclusive": effective_end_exclusive', source)
                self.assertIn("_points_base_sql(scope_sql)", compact_source)
                self.assertNotIn("h.rqsj::date", source)
                self.assertNotIn("sale_date >= CAST(:start_date AS date)", source)
                self.assertNotIn("sale_date < CAST(:end_exclusive AS date)", source)
                self.assertNotIn(":end_date", source)
                self.assertIn("_execute_points_query", source)
                self.assertRegex(compact_source, r"lambda: _(one|rows)\(")

                if endpoint is not router.points_department_options:
                    self.assertIn(
                        "_execute_points_query(db, lambda: _point_rule_source_status(db))",
                        compact_source,
                    )

    def test_department_display_order_matches_sales_dashboard(self):
        rows = [
            {"department_code": "6010117", "department_name": "中心三部(女装)"},
            {"department_code": "6010113", "department_name": "中心二部(女装)"},
            {"department_code": "6010106", "department_name": "中心BF部(生鲜)"},
            {"department_code": "6010114", "department_name": "中心一部(化妆)"},
            {"department_code": "6010103", "department_name": "中心六部(儿童)"},
        ]

        ordered = [row["department_name"] for row in sorted(rows, key=department_display_sort_key)]

        self.assertEqual(
            ordered,
            [
                "中心BF部(生鲜)",
                "中心一部(化妆)",
                "中心二部(女装)",
                "中心三部(女装)",
                "中心六部(儿童)",
            ],
        )

    def test_points_dashboard_sorts_departments_with_sales_dashboard_display_order(self):
        router_file = Path(__file__).resolve().parents[1] / "python_app" / "routers" / "activity_analysis.py"
        text = router_file.read_text(encoding="utf-8")

        self.assertIn("department_display_sort_key", text)
        self.assertIn('departments = row.get("departments") or []', text)
        self.assertIn("departments.sort(key=department_display_sort_key)", text)

    def test_points_base_sql_filters_early_and_limits_large_tables_to_relevant_bills(self):
        from routers.activity_analysis import _points_base_sql

        sql = _points_base_sql("AND scope_row.group_code = 'VISIBLE'")
        self.assertIn("all_payment_goods AS MATERIALIZED", sql)
        self.assertIn("scoped_payment_goods AS MATERIALIZED", sql)
        self.assertIn("h.rqsj >= CAST(:start_date AS date)", sql)
        self.assertIn("h.rqsj < CAST(:end_exclusive AS date)", sql)
        self.assertNotIn("h.rqsj::date BETWEEN", sql)
        self.assertIn("FROM all_payment_goods scope_row", sql)
        self.assertIn("AND scope_row.group_code = 'VISIBLE'", sql)
        self.assertIn("scoped_bills AS MATERIALIZED", sql)
        self.assertIn("relevant_payment_goods AS MATERIALIZED", sql)
        self.assertIn("scoped_bill_groups AS MATERIALIZED", sql)
        self.assertIn("accounting_sales_by_group AS MATERIALIZED", sql)
        self.assertIn("JOIN point_bills pb", sql)
        self.assertIn("ON op.order_id = pb.billno::text", sql)
        self.assertEqual(sql.count("JOIN salegoodslist s"), 1)
        self.assertIn("FROM relevant_payment_goods psg", sql)

    def test_points_base_sql_uses_full_relevant_bills_for_point_allocation(self):
        from routers.activity_analysis import _points_base_sql

        sql = _points_base_sql("AND scope_row.group_code = 'VISIBLE'")
        all_rows = re.search(
            r"all_payment_goods AS MATERIALIZED \((.*?)scoped_payment_goods AS MATERIALIZED",
            sql,
            re.S,
        )
        scoped_rows = re.search(
            r"scoped_payment_goods AS MATERIALIZED \((.*?)scoped_bills AS MATERIALIZED",
            sql,
            re.S,
        )
        relevant_rows = re.search(
            r"relevant_payment_goods AS MATERIALIZED \((.*?)scoped_bill_groups AS MATERIALIZED",
            sql,
            re.S,
        )
        point_bills = re.search(r"point_bills AS MATERIALIZED \((.*?)point_by_bill AS", sql, re.S)
        pay_balance = re.search(r"pay_line_balance AS \((.*?)spg_rows AS", sql, re.S)
        spg_rows = re.search(r"spg_rows AS \((.*?)row_calc AS", sql, re.S)

        for match in (all_rows, scoped_rows, relevant_rows, point_bills, pay_balance, spg_rows):
            self.assertIsNotNone(match)
        self.assertNotIn("scope_row.group_code = 'VISIBLE'", all_rows.group(1))
        self.assertIn("FROM all_payment_goods scope_row", scoped_rows.group(1))
        self.assertIn("scope_row.group_code = 'VISIBLE'", scoped_rows.group(1))
        self.assertIn("FROM all_payment_goods apg", relevant_rows.group(1))
        self.assertIn("JOIN scoped_bills sb", relevant_rows.group(1))
        self.assertIn("sb.billno = apg.billno", relevant_rows.group(1))
        self.assertIn("sb.market_code = apg.market_code", relevant_rows.group(1))
        self.assertIn("sb.sale_date = apg.sale_date", relevant_rows.group(1))
        self.assertIn("FROM relevant_payment_goods", point_bills.group(1))
        self.assertIn("FROM relevant_payment_goods", pay_balance.group(1))
        self.assertIn("FROM relevant_payment_goods psg", spg_rows.group(1))

    def test_points_base_sql_filters_complete_bill_results_to_scoped_groups(self):
        from routers.activity_analysis import _points_base_sql

        sql = _points_base_sql("AND scope_row.group_code = 'VISIBLE'")
        point_rows = re.search(r"point_rows AS \((.*)\)\s*$", sql, re.S)

        self.assertIsNotNone(point_rows)
        point_rows_sql = point_rows.group(1)
        self.assertIn("FROM point_rows_unscored pru", point_rows_sql)
        self.assertIn("JOIN scoped_bill_groups sbg", point_rows_sql)
        self.assertIn("sbg.billno = pru.billno", point_rows_sql)
        self.assertIn("sbg.market_code = pru.market_code", point_rows_sql)
        self.assertIn("sbg.sale_date = pru.sale_date", point_rows_sql)
        self.assertIn("COALESCE(sbg.group_code, '')", point_rows_sql)
        self.assertIn("COALESCE(pru.group_code, '')", point_rows_sql)

    def test_point_source_status_uses_catalog_estimates_not_full_counts(self):
        import inspect
        from routers.activity_analysis import _point_rule_source_status

        source = inspect.getsource(_point_rule_source_status)
        self.assertIn("reltuples", source)
        self.assertIn("GREATEST(COALESCE(c.reltuples, 0), 0)::bigint", source)
        self.assertNotIn("COUNT(*)", source)

    def test_points_base_sql_limits_to_shopping_center_black_gold_and_black_diamond(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_app"))
        from routers.activity_analysis import _points_base_sql

        sql = _points_base_sql()

        self.assertIn("h.mkt::text = '601'", sql)
        self.assertIn("WHERE customer_level IN ('03', '04')", sql)
        self.assertIn("= '03' THEN payment_alloc_amount * point_basis_rate * (2 / jfrate)", sql)
        self.assertIn("= '04' THEN payment_alloc_amount * point_basis_rate * (3 / jfrate)", sql)
        self.assertIn("point_rows_unscored AS", sql)
        self.assertIn("FROM point_rows_unscored", sql)

    def test_points_sales_amount_uses_salegoodslist_revenue_not_payment_allocation(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_app"))
        from routers.activity_analysis import _points_base_sql

        sql = _points_base_sql()

        self.assertIn("scoped_bill_groups AS MATERIALIZED", sql)
        self.assertIn("accounting_sales_by_group AS MATERIALIZED", sql)
        self.assertIn("s.sglbillno AS billno", sql)
        self.assertIn("s.sglmarket::varchar AS market_code", sql)
        self.assertIn("s.sglhsrq::date AS sale_date", sql)
        self.assertIn("TRIM(BOTH FROM COALESCE(s.sglmfid, '')) AS group_code", sql)
        self.assertIn("SUM(COALESCE(s.sglxssr, 0)) AS sales_amount", sql)
        self.assertIn("FROM scoped_bill_groups sbg", sql)
        self.assertIn("JOIN salegoodslist s", sql)
        self.assertIn("sbg.market_code = s.sglmarket::varchar", sql)
        self.assertIn("sbg.sale_date = s.sglhsrq::date", sql)
        self.assertIn("sgl.billno = psg.billno", sql)
        self.assertIn("sgl.market_code = psg.market_code", sql)
        self.assertIn("sgl.sale_date = psg.sale_date", sql)
        self.assertIn("UPPER(TRIM(COALESCE(sgl.group_code, ''))) = UPPER(TRIM(COALESCE(psg.group_code, '')))", sql)
        self.assertIn("MAX(accounting_sales_amount) AS total_sales_amount", sql)
        self.assertNotIn("COALESCE(spg.spggdmoney, 0) AS total_sales_amount", sql)
        self.assertNotIn("COALESCE(spg.spggdcjje, 0) AS total_sales_amount", sql)

    def test_activity_analysis_router_exposes_points_paths(self):
        router_file = Path(__file__).resolve().parents[1] / "python_app" / "routers" / "activity_analysis.py"
        text = router_file.read_text(encoding="utf-8")

        self.assertIn('@router.get("/points/dashboard")', text)
        self.assertIn('@router.get("/points/department-options")', text)
        self.assertIn('@router.get("/points/overview")', text)
        self.assertIn('@router.get("/points/departments")', text)
        self.assertIn('@router.get("/points/members")', text)
        self.assertIn('@router.get("/points/tickets")', text)

    def test_points_nginx_timeout_is_60_seconds_without_changing_general_api_timeout(self):
        config = (Path(__file__).resolve().parents[1] / "config" / "nginx.conf").read_text(encoding="utf-8")
        points_location = re.search(r"location \^~ /api/activity-analysis/points/ \{(.*?)\n\s*\}", config, re.S)
        general_location = re.search(r"location /api/ \{(.*?)\n\s*\}", config, re.S)

        self.assertIsNotNone(points_location)
        self.assertIsNotNone(general_location)
        self.assertLess(points_location.start(), general_location.start())

        points_config = points_location.group(1)
        self.assertIn("proxy_pass http://shopview_backend;", points_config)
        self.assertIn("proxy_set_header Host $host;", points_config)
        self.assertIn("proxy_set_header X-Real-IP $remote_addr;", points_config)
        self.assertIn("proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;", points_config)
        self.assertIn("proxy_set_header X-Forwarded-Proto $scheme;", points_config)
        self.assertIn("proxy_connect_timeout 30s;", points_config)
        self.assertIn("proxy_send_timeout 30s;", points_config)
        self.assertEqual(re.findall(r"^\s*proxy_read_timeout\s+(\S+);", points_config, re.M), ["60s"])

        general_config = general_location.group(1)
        self.assertEqual(re.findall(r"^\s*proxy_read_timeout\s+(\S+);", general_config, re.M), ["30s"])

    def test_points_dashboard_filters_by_department_name(self):
        router_file = Path(__file__).resolve().parents[1] / "python_app" / "routers" / "activity_analysis.py"
        text = router_file.read_text(encoding="utf-8")

        self.assertIn("department_name: str | None", text)
        self.assertIn("department_name ILIKE :department_name", text)
        self.assertIn("department_options", text)
        self.assertIn("'black_gold_member_count'", text)
        self.assertIn("'black_diamond_member_count'", text)
        self.assertIn("level_sales_rows AS MATERIALIZED", text)
        self.assertIn("'black_diamond_sales_amount'", text)
        self.assertIn("'gold_star_sales_amount'", text)
        self.assertIn("'silver_star_sales_amount'", text)
        self.assertIn("'non_member_sales_amount'", text)
        self.assertIn("'level_total_person_count'", text)
        self.assertIn("'black_diamond_person_count'", text)
        self.assertIn("'black_gold_person_count'", text)
        self.assertIn("'gold_star_person_count'", text)
        self.assertIn("'silver_star_person_count'", text)
        self.assertIn("'non_member_person_count'", text)
        self.assertIn("level_sales_source AS MATERIALIZED", text)
        self.assertIn("level_sales_rows AS MATERIALIZED", text)
        self.assertIn("COALESCE(NULLIF(TRIM(BOTH FROM h.hykh), ''), '') AS member_no", text)
        self.assertIn("JOIN accounting_sales_by_group s", text)
        self.assertIn("COALESCE(SUM(s.sales_amount), 0) AS total_sales_amount", text)
        self.assertIn("COUNT(DISTINCT NULLIF(src.member_no, ''))", text)
        self.assertIn("COUNT(DISTINCT src.billno)", text)
        self.assertIn("s.market_code = src.market_code", text)
        self.assertIn("s.sale_date = src.sale_date", text)
        self.assertIn("UPPER(TRIM(COALESCE(s.group_code, ''))) = UPPER(TRIM(COALESCE(src.group_code, '')))", text)
        self.assertNotIn("COALESCE(SUM(spg.spggdmoney), 0) AS total_sales_amount", text)
        self.assertNotIn("COALESCE(SUM(spg.spggdcjje), 0) AS total_sales_amount", text)

    def test_points_dashboard_reuses_scoped_rows_for_level_sales(self):
        router_file = Path(__file__).resolve().parents[1] / "python_app" / "routers" / "activity_analysis.py"
        source = router_file.read_text(encoding="utf-8")
        match = re.search(r"level_sales_source AS MATERIALIZED \((.*?)level_sales_rows AS MATERIALIZED", source, re.S)

        self.assertIsNotNone(match)
        level_sql = match.group(1)
        self.assertIn("FROM scoped_payment_goods", level_sql)
        self.assertNotIn("JOIN salehead", level_sql)
        self.assertNotIn("JOIN salegoodslist", level_sql)
        self.assertIn("GROUP BY 1, 2, 3, 4, 5, 6", level_sql)

    def test_points_dashboard_exposes_department_and_group_drilldowns(self):
        router_file = Path(__file__).resolve().parents[1] / "python_app" / "routers" / "activity_analysis.py"
        text = router_file.read_text(encoding="utf-8")

        self.assertIn('AS departments', text)
        self.assertIn('AS groups', text)
        self.assertIn('"groups": row.get("groups") or []', text)
        self.assertIn("black_gold_member_count", text)
        self.assertIn("black_diamond_member_count", text)

    def test_points_scope_maps_shopview_store_id_to_activity_market_code(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_app"))
        from routers.activity_analysis import _points_business_scope_filter_sql

        params = {}
        scope = SimpleNamespace(
            all_access=False,
            allow={"store": {"1"}, "department": {"D1"}, "group": {"G1"}},
            deny={},
        )

        sql = _points_business_scope_filter_sql(scope, params, prefix="points_dashboard")

        self.assertIn("points_dashboard_allow_store", params)
        self.assertIn("601", params["points_dashboard_allow_store"])
        self.assertIn("scope_row.market_code", sql)
        self.assertIn("scope_row.store_id", sql)
        self.assertIn("scope_row.department_code", sql)
        self.assertIn("scope_row.department_name", sql)
        self.assertIn("scope_row.group_code", sql)
        self.assertNotIn("h.mkt", sql)
        self.assertNotIn("cg.", sql)
        self.assertNotIn("g.gz", sql)


if __name__ == "__main__":
    unittest.main()
