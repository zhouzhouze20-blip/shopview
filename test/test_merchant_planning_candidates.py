from datetime import date, timedelta
from decimal import Decimal
import sys
from pathlib import Path
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_app"))

from routers.merchant_planning import _classify_candidate


class MerchantPlanningCandidateClassificationTest(unittest.TestCase):
    def test_classifies_vacant_expiring_low_efficiency_and_normal(self):
        today = date(2026, 6, 7)
        medians = {196: Decimal("1000")}

        self.assertEqual(
            _classify_candidate(
                {"current_contract_id": None, "floor_id": 196, "period_revenue": Decimal("10"), "contract_end_date": None},
                medians,
                today=today,
            ),
            "VACANT",
        )
        self.assertEqual(
            _classify_candidate(
                {
                    "current_contract_id": "C-001",
                    "floor_id": 196,
                    "period_revenue": Decimal("900"),
                    "contract_end_date": today + timedelta(days=30),
                },
                medians,
                today=today,
            ),
            "EXPIRING",
        )
        self.assertEqual(
            _classify_candidate(
                {"current_contract_id": "C-002", "floor_id": 196, "period_revenue": Decimal("500"), "contract_end_date": None},
                medians,
                today=today,
            ),
            "LOW_EFFICIENCY",
        )
        self.assertEqual(
            _classify_candidate(
                {"current_contract_id": "C-003", "floor_id": 196, "period_revenue": Decimal("700"), "contract_end_date": None},
                medians,
                today=today,
            ),
            "NORMAL",
        )


if __name__ == "__main__":
    unittest.main()
