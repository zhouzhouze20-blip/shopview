import inspect
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import HTTPException


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_app"))

from routers import activity_analysis


STORE_ROWS = [
    {"store_id": 1, "store_code": "601", "store_name": "常州购物中心"},
    {"store_id": 2, "store_code": "602", "store_name": "常州百货大楼"},
    {"store_id": 3, "store_code": "603", "store_name": "常州新世纪商城"},
]


class ActivityAnalysisStoreFilterTest(unittest.TestCase):
    def test_store_filter_helpers_are_available(self):
        self.assertTrue(hasattr(activity_analysis, "_activity_store_options_for_scope"))
        self.assertTrue(hasattr(activity_analysis, "_require_selected_activity_store"))
        self.assertTrue(hasattr(activity_analysis, "_selected_store_clause"))
        self.assertTrue(hasattr(activity_analysis, "_activity_market_scope_filter_sql"))

    def test_all_access_options_return_all_active_store_rows(self):
        helper = getattr(activity_analysis, "_activity_store_options_for_scope", None)
        self.assertIsNotNone(helper)
        with patch.object(activity_analysis, "_rows", return_value=STORE_ROWS):
            rows = helper(object(), SimpleNamespace(all_access=True, allow={}, deny={}))
        self.assertEqual([row["store_code"] for row in rows], ["601", "602", "603"])

    def test_restricted_options_only_include_allowed_store(self):
        helper = getattr(activity_analysis, "_activity_store_options_for_scope", None)
        self.assertIsNotNone(helper)
        scope = SimpleNamespace(all_access=False, allow={"store": {"1"}}, deny={})
        with (
            patch.object(activity_analysis, "_rows", return_value=STORE_ROWS),
            patch.object(
                activity_analysis,
                "_activity_store_scope_values",
                side_effect=[({"1"}, {"601"}), (set(), set())],
            ),
        ):
            rows = helper(object(), scope)
        self.assertEqual([row["store_code"] for row in rows], ["601"])

    def test_denied_store_is_removed_from_options(self):
        helper = getattr(activity_analysis, "_activity_store_options_for_scope", None)
        self.assertIsNotNone(helper)
        scope = SimpleNamespace(
            all_access=False,
            allow={"store": {"1", "2"}},
            deny={"store": {"2"}},
        )
        with (
            patch.object(activity_analysis, "_rows", return_value=STORE_ROWS),
            patch.object(
                activity_analysis,
                "_activity_store_scope_values",
                side_effect=[({"1", "2"}, {"601", "602"}), ({"2"}, {"602"})],
            ),
        ):
            rows = helper(object(), scope)
        self.assertEqual([row["store_code"] for row in rows], ["601"])

    def test_all_access_options_still_remove_denied_store(self):
        helper = activity_analysis._activity_store_options_for_scope
        scope = SimpleNamespace(all_access=True, allow={}, deny={"store": {"2"}})
        with (
            patch.object(activity_analysis, "_rows", return_value=STORE_ROWS),
            patch.object(
                activity_analysis,
                "_activity_store_scope_values",
                return_value=({"2"}, {"602"}),
            ),
        ):
            rows = helper(object(), scope)
        self.assertEqual([row["store_code"] for row in rows], ["601", "603"])

    def test_all_access_with_global_deny_has_no_store_options(self):
        helper = activity_analysis._activity_store_options_for_scope
        scope = SimpleNamespace(all_access=True, allow={}, deny={"__all__": {"*"}})
        with patch.object(activity_analysis, "_rows", return_value=STORE_ROWS):
            rows = helper(object(), scope)
        self.assertEqual(rows, [])

    def test_selected_store_is_normalized_and_authorized(self):
        helper = getattr(activity_analysis, "_require_selected_activity_store", None)
        self.assertIsNotNone(helper)
        with patch.object(
            activity_analysis,
            "_activity_store_options_for_scope",
            return_value=[{"store_id": 9, "store_code": "60a", "store_name": "测试门店"}],
        ):
            selected = helper(object(), SimpleNamespace(), " 60A ")
        self.assertEqual(selected, "60A")

    def test_selected_store_outside_scope_is_forbidden(self):
        helper = getattr(activity_analysis, "_require_selected_activity_store", None)
        self.assertIsNotNone(helper)
        with patch.object(
            activity_analysis,
            "_activity_store_options_for_scope",
            return_value=STORE_ROWS[:1],
        ):
            with self.assertRaises(HTTPException) as raised:
                helper(object(), SimpleNamespace(), "602")
        self.assertEqual(raised.exception.status_code, 403)
        self.assertEqual(raised.exception.detail, "门店不存在或无数据权限")

    def test_selected_store_clause_uses_bound_parameter(self):
        helper = getattr(activity_analysis, "_selected_store_clause", None)
        self.assertIsNotNone(helper)
        params = {}
        clause = helper("601", params, expression="l.tcflmkt", prefix="overview")
        self.assertEqual(clause, " AND l.tcflmkt::varchar = :overview_selected_store_code")
        self.assertEqual(params, {"overview_selected_store_code": "601"})

    def test_market_scope_filter_uses_salehead_market(self):
        helper = getattr(activity_analysis, "_activity_market_scope_filter_sql", None)
        self.assertIsNotNone(helper)
        scope = SimpleNamespace(all_access=False, allow={"store": {"1"}}, deny={})
        params = {}
        with patch.object(
            activity_analysis,
            "_activity_store_scope_values",
            return_value=({"1"}, {"601"}),
        ):
            clause = helper(object(), scope, params, expression="h.mkt", prefix="period")
        self.assertIn("h.mkt::varchar = ANY(:period_store_ids)", clause)
        self.assertIn("h.mkt::varchar = ANY(:period_store_codes)", clause)
        self.assertEqual(params["period_store_ids"], ["1"])
        self.assertEqual(params["period_store_codes"], ["601"])

    def test_market_scope_filter_excludes_denied_store(self):
        helper = activity_analysis._activity_market_scope_filter_sql
        scope = SimpleNamespace(
            all_access=False,
            allow={"store": {"1", "2"}},
            deny={"store": {"2"}},
        )
        params = {}
        with patch.object(
            activity_analysis,
            "_activity_store_scope_values",
            side_effect=[({"1", "2"}, {"601", "602"}), ({"2"}, {"602"})],
        ):
            clause = helper(object(), scope, params, expression="h.mkt", prefix="period")
        self.assertIn("AND NOT", clause)
        self.assertIn("h.mkt::varchar = ANY(:period_deny_store_codes)", clause)
        self.assertEqual(params["period_deny_store_codes"], ["602"])

    def test_all_access_market_and_log_scopes_still_apply_store_deny(self):
        scope = SimpleNamespace(all_access=True, allow={}, deny={"store": {"2"}})
        with patch.object(
            activity_analysis,
            "_activity_store_scope_values",
            return_value=({"2"}, {"602"}),
        ):
            market_params = {}
            market_clause = activity_analysis._activity_market_scope_filter_sql(
                object(), scope, market_params, expression="h.mkt", prefix="period"
            )
            activity_params = {}
            activity_clause = activity_analysis._activity_scope_filter_sql(
                object(), scope, activity_params, alias="p", prefix="activity"
            )
            log_params = {}
            log_clause = activity_analysis._activity_log_scope_filter_sql(
                object(), scope, log_params, alias="l", prefix="logs"
            )
        self.assertIn("AND NOT", market_clause)
        self.assertIn("AND NOT", activity_clause)
        self.assertIn("AND NOT", log_clause)
        self.assertEqual(market_params["period_deny_store_codes"], ["602"])
        self.assertEqual(activity_params["activity_deny_store_codes"], ["602"])
        self.assertEqual(log_params["logs_deny_store_codes"], ["602"])

    def test_store_options_endpoint_requires_activity_permission(self):
        endpoint = getattr(activity_analysis, "activity_store_options", None)
        self.assertIsNotNone(endpoint)
        source = inspect.getsource(endpoint)
        self.assertIn("require_permission(db, current_user, ACTIVITY_ANALYSIS_PERMISSION)", source)
        self.assertIn("_activity_store_options_for_scope(db, business_scope)", source)

    def test_general_analysis_endpoints_accept_and_validate_store_code(self):
        endpoints = (
            activity_analysis.overview,
            activity_analysis.coupon_summary,
            activity_analysis.coupon_flows,
            activity_analysis.quality_issues,
            activity_analysis.coupon_type_departments,
            activity_analysis.department_tickets,
        )
        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint.__name__):
                self.assertIn("store_code", inspect.signature(endpoint).parameters)
                source = inspect.getsource(endpoint)
                self.assertIn("_require_selected_activity_store", source)
                self.assertIn("selected_store_code", source)
                self.assertIn("_selected_store_clause", source)

    def test_period_only_and_unassigned_quality_queries_keep_store_scope(self):
        overview_source = inspect.getsource(activity_analysis.overview)
        quality_source = inspect.getsource(activity_analysis.quality_issues)
        self.assertIn("period_scope_sql", overview_source)
        self.assertIn("period_store_sql", overview_source)
        self.assertIn("period_scope_sql", quality_source)
        self.assertIn("period_store_sql", quality_source)
        self.assertIn("unassigned_store_sql", quality_source)
        self.assertIn("log_scope_sql", quality_source)

    def test_aggregate_activity_scope_counts_new_members_by_selected_dates(self):
        source = inspect.getsource(activity_analysis.overview)
        self.assertNotIn("AND :activity_id IS NOT NULL", source)
        self.assertIn("CASE WHEN :activity_id IS NOT NULL", source)
        self.assertIn("CAST(:start_date AS date)", source)
        self.assertIn("CAST(:end_date AS date)", source)


if __name__ == "__main__":
    unittest.main()
