from datetime import date
from decimal import Decimal
import inspect
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_app"))

from routers import category_performance
from services.category_performance import (
    build_score_row,
    parse_period_month,
    performance_coefficient,
)


class CategoryPerformanceTest(unittest.TestCase):
    def test_parse_period_month_uses_calendar_month_boundaries(self):
        leap_month = parse_period_month("2024-02")
        normal_month = parse_period_month("2026-06")

        self.assertEqual(leap_month.start_date, date(2024, 2, 1))
        self.assertEqual(leap_month.end_date, date(2024, 2, 29))
        self.assertEqual(normal_month.start_date, date(2026, 6, 1))
        self.assertEqual(normal_month.end_date, date(2026, 6, 30))

        with self.assertRaisesRegex(ValueError, "YYYY-MM"):
            parse_period_month("2026-13")

    def test_standard_score_matches_source_workbook_formula_and_is_not_capped(self):
        score = build_score_row(
            area_target=100,
            area_actual=110,
            area_weight=40,
            key_target=200,
            key_actual=240,
            key_weight=40,
            self_score=18,
        )

        self.assertEqual(score["area_score"], Decimal("44.00"))
        self.assertEqual(score["key_score"], Decimal("48.00"))
        self.assertEqual(score["total_score"], Decimal("110.00"))
        self.assertEqual(score["coefficient"], Decimal("1.2"))

    def test_zero_weight_key_brand_does_not_block_children_score(self):
        score = build_score_row(
            area_target=100,
            area_actual=90,
            area_weight=80,
            key_target=0,
            key_actual=0,
            key_weight=0,
            self_score=20,
        )

        self.assertEqual(score["key_score"], Decimal("0.00"))
        self.assertTrue(score["score_complete"])
        self.assertEqual(score["total_score"], Decimal("92.00"))
        self.assertEqual(score["coefficient"], Decimal("1.0"))

    def test_performance_coefficient_thresholds(self):
        cases = [
            ("100", "1.2"),
            ("99.99", "1.0"),
            ("90", "1.0"),
            ("89.99", "0.9"),
            ("80", "0.9"),
            ("79.99", "0.8"),
        ]
        for score, expected in cases:
            with self.subTest(score=score):
                self.assertEqual(performance_coefficient(Decimal(score)), Decimal(expected))

    def test_realtime_sources_keep_finance_and_sales_evidence_separate(self):
        area_source = inspect.getsource(category_performance._manager_actuals)
        key_source = inspect.getsource(category_performance._key_brand_actuals)

        self.assertIn("COALESCE(s.sgln2, 0)", area_source)
        self.assertIn("unit_revenue_fee_detail", area_source)
        self.assertIn("revenue_extra_receipts", area_source)
        self.assertIn("status = 'CONFIRMED'", area_source)
        self.assertIn("LEFT(TRIM(fee.source_group_code), 3) = :store_code", area_source)
        self.assertIn("SUM(COALESCE(sglsjje, 0))", key_source)
        self.assertIn("category_manager_brand_assignments", key_source)
        self.assertIn("manaframe_key_brand", key_source)
        self.assertIn("LEFT JOIN category_key_brand_targets", key_source)
        self.assertIn("sales_target", key_source)

    def test_options_exposes_latest_maintained_performance_period(self):
        source = inspect.getsource(category_performance.category_performance_options)

        self.assertIn("latest_period", source)
        self.assertIn("category_key_brand_targets", source)
        self.assertIn("category_manager_performance_targets", source)
        self.assertIn("salegoodslist", source)


if __name__ == "__main__":
    unittest.main()
