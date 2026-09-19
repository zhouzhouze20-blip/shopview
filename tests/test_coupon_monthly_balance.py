import unittest
from pathlib import Path

from services.activity_analysis.coupon_monthly_balance import (
    calculate_ending_balance,
    coupon_recharge_source_key,
    month_bounds,
    normalize_period_month,
    opening_balance_source_period,
)


class CouponMonthlyBalanceTest(unittest.TestCase):
    def test_normalize_period_month_accepts_year_month(self):
        self.assertEqual(normalize_period_month("2026-06"), "2026-06")

    def test_normalize_period_month_rejects_invalid_month(self):
        with self.assertRaises(ValueError):
            normalize_period_month("2026-13")

    def test_month_bounds_returns_financial_month_half_open_range(self):
        self.assertEqual(month_bounds("2026-07"), ("2026-06-29", "2026-07-29"))

    def test_month_bounds_handles_financial_month_across_year_boundary(self):
        self.assertEqual(month_bounds("2026-01"), ("2025-12-29", "2026-01-29"))

    def test_initial_month_has_no_opening_balance_source(self):
        self.assertIsNone(opening_balance_source_period("2026-07"))

    def test_month_after_initial_month_uses_previous_month(self):
        self.assertEqual(opening_balance_source_period("2026-08"), "2026-07")

    def test_calculate_ending_balance_subtracts_decrease_and_nc_carryover(self):
        self.assertEqual(
            calculate_ending_balance(
                opening_balance=1000,
                current_month_increase=500,
                current_month_decrease=200,
                nc_carryover_amount=300,
            ),
            1000,
        )

    def test_coupon_recharge_source_key_is_stable_by_day_store_coupon(self):
        self.assertEqual(
            coupon_recharge_source_key("2026-06-19", "601", "r"),
            "coupon_recharge:2026-06-19:601:R",
        )

    def test_sales_rebate_and_clawback_are_direct_monthly_increases(self):
        router_source = (
            Path(__file__).resolve().parents[1]
            / "python_app"
            / "routers"
            / "activity_analysis.py"
        ).read_text(encoding="utf-8")
        rebate_sql = router_source.split("sales_rebate_result = db.execute(", 1)[1].split(
            "db.commit()", 1
        )[0]

        self.assertIn("l.tcflzy IN ('F', 'K')", rebate_sql)
        self.assertIn("l.tcflsource = '1'", rebate_sql)
        self.assertIn("WHEN l.tcflzy = 'F' THEN ABS", rebate_sql)
        self.assertIn("WHEN l.tcflzy = 'K' THEN -ABS", rebate_sql)
        self.assertIn("'coupon_sales_rebate:'", rebate_sql)
        self.assertIn("'OK'", rebate_sql)
        self.assertIn("'INCREASE'", rebate_sql)


if __name__ == "__main__":
    unittest.main()
