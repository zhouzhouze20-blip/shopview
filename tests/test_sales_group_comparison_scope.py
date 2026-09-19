import unittest
from unittest.mock import patch

from python_app.routers import sales


class SalesGroupComparisonScopeTests(unittest.TestCase):
    def query(self, current, prior, *, limit=1, compare=True):
        def fetch(_db, **kwargs):
            source = current if kwargs["start_date"] == "2026-08-29" else prior
            rows = [dict(row) for row in source]
            return rows[:kwargs["limit"]] if kwargs["limit"] is not None else rows

        with (
            patch.object(sales, "require_permission"),
            patch.object(sales, "_configure_sales_summary_timeout"),
            patch.object(sales, "load_business_scope", return_value=object()),
            patch.object(sales, "_row_allowed", side_effect=lambda _scope, row: row["group_code"] != "DENIED"),
            patch.object(sales, "_group_level_sales_rows", side_effect=fetch),
            patch.object(sales, "_prior_year_same_period", return_value=(None, None)),
        ):
            return sales.group_summary(
                start_date="2026-08-29", end_date="2026-08-30",
                prior_start_date="2025-08-29" if compare else None,
                prior_end_date="2025-08-30" if compare else None,
                store_id="1", department_code="D1", unassigned_department=False,
                group_code=None, keyword=None, exclude_rental=True,
                exclude_backoffice_departments=True, limit=limit,
                db=object(), current_user=object(),
            )

    def test_limit_before_permission_filter_must_not_turn_visible_current_sales_into_zero(self):
        rows = self.query(
            [{"group_code": "DENIED", "effective_sales": 1000}, {"group_code": "VISIBLE", "effective_sales": 120}],
            [{"group_code": "VISIBLE", "effective_sales": 100}],
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["group_code"], "VISIBLE")
        self.assertEqual(rows[0]["effective_sales"], 120)
        self.assertEqual(rows[0]["same_period_effective_sales"], 100)

    def test_negative_current_sales_remain_negative_when_prior_only_groups_sort_ahead(self):
        rows = self.query(
            [{"group_code": "HIGH", "effective_sales": 100}, {"group_code": "RETURN", "effective_sales": -20}],
            [{"group_code": "PRIOR_ONLY", "effective_sales": 10}, {"group_code": "RETURN", "effective_sales": 80}],
            limit=3,
        )
        by_code = {row["group_code"]: row for row in rows}
        self.assertEqual(by_code["RETURN"]["effective_sales"], -20)
        self.assertEqual(by_code["PRIOR_ONLY"]["effective_sales"], 0)

    def test_without_comparison_applies_response_limit_after_scope(self):
        rows = self.query(
            [{"group_code": "DENIED", "effective_sales": 1000},
             {"group_code": "VISIBLE", "effective_sales": 120},
             {"group_code": "OTHER", "effective_sales": 60}],
            [], compare=False,
        )
        self.assertEqual([row["group_code"] for row in rows], ["VISIBLE"])


if __name__ == "__main__":
    unittest.main()
