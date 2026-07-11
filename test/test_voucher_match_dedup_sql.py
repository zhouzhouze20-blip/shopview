import sys
from pathlib import Path
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_app"))

from routers.activity_analysis import _voucher_match_flow_exclusion_sql


class VoucherMatchFlowExclusionSqlTest(unittest.TestCase):
    def test_excludes_confirmed_duplicate_flow_without_window_deduping(self):
        sql = _voucher_match_flow_exclusion_sql("l")

        self.assertIn("l.tcflseqno::text", sql)
        self.assertIn("29042789", sql)
        self.assertNotIn("ROW_NUMBER()", sql)


if __name__ == "__main__":
    unittest.main()
