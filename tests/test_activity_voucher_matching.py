import unittest

from routers.activity_analysis import finance_voucher_amount_filter_sql


class ActivityVoucherMatchingTest(unittest.TestCase):
    def test_finance_voucher_filter_uses_zero_excrate1_and_nonzero_amount(self):
        filter_sql = finance_voucher_amount_filter_sql("v")

        self.assertIn("v.excrate1 = 0", filter_sql)
        self.assertIn("COALESCE(v.localdebitamount, v.debitamount, 0) <> 0", filter_sql)
        self.assertIn("COALESCE(v.localcreditamount, v.creditamount, 0) <> 0", filter_sql)


if __name__ == "__main__":
    unittest.main()
