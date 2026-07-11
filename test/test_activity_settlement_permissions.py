import sys
from pathlib import Path
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_app"))

from routers.authz import CORE_PERMISSION_DEFINITIONS


class ActivitySettlementPermissionTest(unittest.TestCase):
    def test_core_permissions_include_activity_settlement_operations(self):
        permission_codes = {permission[0] for permission in CORE_PERMISSION_DEFINITIONS}

        self.assertTrue({
            "activity_settlement.voucher_match.view",
            "activity_settlement.voucher_match.confirm",
            "activity_settlement.voucher_match.reject",
            "activity_settlement.coupon_monthly.view",
            "activity_settlement.coupon_monthly.rebuild",
            "activity_settlement.coupon_monthly.confirm",
            "activity_settlement.coupon_monthly.carryover_create",
        }.issubset(permission_codes))


if __name__ == "__main__":
    unittest.main()
