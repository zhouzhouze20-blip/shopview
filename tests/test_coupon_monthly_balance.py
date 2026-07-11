import unittest

from services.activity_analysis.coupon_monthly_balance import (
    calculate_ending_balance,
    coupon_recharge_source_key,
    month_bounds,
    normalize_period_month,
)


class CouponMonthlyBalanceTest(unittest.TestCase):
    def test_normalize_period_month_accepts_year_month(self):
        self.assertEqual(normalize_period_month("2026-06"), "2026-06")

    def test_normalize_period_month_rejects_invalid_month(self):
        with self.assertRaises(ValueError):
            normalize_period_month("2026-13")

    def test_month_bounds_returns_half_open_range(self):
        self.assertEqual(month_bounds("2026-12"), ("2026-12-01", "2027-01-01"))

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


if __name__ == "__main__":
    unittest.main()
