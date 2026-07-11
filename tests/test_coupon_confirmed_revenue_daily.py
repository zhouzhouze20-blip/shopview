import unittest

from routers.activity_analysis import (
    COUPON_CONFIRMED_REVENUE_VIEW_PERMISSION,
    coupon_confirmed_revenue_daily_sql,
    summarize_confirmed_revenue_rows,
)


class CouponConfirmedRevenueDailyTest(unittest.TestCase):
    def test_query_filters_by_finance_confirmed_at(self):
        sql = coupon_confirmed_revenue_daily_sql(include_coupon_type=False)

        self.assertIn("JOIN activity_coupon_voucher_match m", sql)
        self.assertIn("m.confirmed_at >= CAST(:start_date AS DATE)", sql)
        self.assertIn("m.confirmed_at < CAST(:end_date AS DATE) + INTERVAL '1 day'", sql)
        self.assertIn("rm.business_date", sql)

    def test_query_can_filter_coupon_type_without_recomputing_amount(self):
        sql = coupon_confirmed_revenue_daily_sql(include_coupon_type=True)

        self.assertIn("UPPER(TRIM(rm.coupon_type)) = UPPER(TRIM(:coupon_type))", sql)
        self.assertIn("COALESCE(rm.actual_revenue_amount, 0) AS actual_revenue_amount", sql)
        self.assertNotIn("rm.business_amount * rm.revenue_rate", sql)

    def test_summary_counts_missing_rate_as_zero_revenue(self):
        result = summarize_confirmed_revenue_rows(
            [
                {"market_code": "603", "business_amount": 1000, "actual_revenue_amount": 250, "rate_status": "OK"},
                {"market_code": "603", "business_amount": 500, "actual_revenue_amount": 0, "rate_status": "MISSING_RATE"},
                {"market_code": "601", "business_amount": 200, "actual_revenue_amount": 60, "rate_status": "OK"},
            ]
        )

        self.assertEqual(result["summary"]["movement_count"], 3)
        self.assertEqual(result["summary"]["missing_rate_count"], 1)
        self.assertEqual(result["summary"]["business_amount"], 1700)
        self.assertEqual(result["summary"]["confirmed_revenue_amount"], 310)
        self.assertEqual([row["market_code"] for row in result["store_summary"]], ["603", "601"])

    def test_permission_constant_is_read_only(self):
        self.assertEqual(COUPON_CONFIRMED_REVENUE_VIEW_PERMISSION, "activity_settlement.confirmed_revenue.view")


if __name__ == "__main__":
    unittest.main()
