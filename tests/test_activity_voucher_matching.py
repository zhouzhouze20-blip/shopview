import unittest

from routers.activity_analysis import (
    CREDIT_BUY_MATCH_TYPE_NAME,
    _voucher_match_flow_exclusion_sql,
    confirmed_voucher_match_movement_sql,
    finance_voucher_amount_filter_sql,
    front_buy_actual_amount_sql,
    front_buy_face_total_sql,
    front_buy_sale_join_sql,
    voucher_business_rows_ctes_sql,
)


class ActivityVoucherMatchingTest(unittest.TestCase):
    def test_finance_voucher_filter_uses_zero_excrate1_and_nonzero_amount(self):
        filter_sql = finance_voucher_amount_filter_sql("v")

        self.assertIn("v.excrate1 = 0", filter_sql)
        self.assertIn("COALESCE(v.localdebitamount, v.debitamount, 0) <> 0", filter_sql)
        self.assertIn("COALESCE(v.localcreditamount, v.creditamount, 0) <> 0", filter_sql)

    def test_front_buy_sale_join_uses_store_register_invoice_and_business_date(self):
        join_sql = front_buy_sale_join_sql("l", "front_sale")

        self.assertIn("h.mkt = l.tcflmkt", join_sql)
        self.assertIn("h.syjh = l.tcflsyjid", join_sql)
        self.assertIn("h.fphm = l.tcflinvno::numeric", join_sql)
        self.assertIn("h.rqsj::date = l.tcfldate", join_sql)
        self.assertIn("LIMIT 1", join_sql)

    def test_front_buy_actual_amount_uses_salehead_receivable_and_allocates_face_share(self):
        amount_sql = front_buy_actual_amount_sql("l", "front_sale")
        face_total_sql = front_buy_face_total_sql("l")

        self.assertIn("front_sale.ysje", amount_sql)
        self.assertIn("front_sale.sjfk - COALESCE(front_sale.zl, 0)", amount_sql)
        self.assertIn("l.tcflzy = 'm'", amount_sql)
        self.assertIn("l.tcflzy = 'n'", amount_sql)
        self.assertIn("l.tcflsource IN ('2', '5')", amount_sql)
        self.assertIn("PARTITION BY", face_total_sql)
        self.assertIn("l.tcflinvno", face_total_sql)

    def test_credit_buy_match_is_named_front_counter_purchase(self):
        self.assertEqual(CREDIT_BUY_MATCH_TYPE_NAME, "贷方前台买券")

    def test_voucher_match_hides_backend_crm_recharges_and_refunds(self):
        sql = _voucher_match_flow_exclusion_sql("l")

        self.assertIn("l.tcflzy IN ('M', 'N')", sql)
        self.assertIn("COALESCE(l.tcflsource, '')", sql)
        self.assertIn("COALESCE(l.tcflsyjid, '')", sql)
        self.assertIn("COALESCE(l.tcflinvno, '')", sql)
        self.assertIn("= '2'", sql)
        self.assertIn("= '0000'", sql)
        self.assertNotIn("l.tcflsource, '')) = '8'", sql)

    def test_debit_use_business_amount_deducts_coupon_overage_once_per_ticket(self):
        sql = voucher_business_rows_ctes_sql()

        self.assertIn("GROUP BY", sql)
        self.assertIn("cashier_id", sql)
        self.assertIn("invoice_no", sql)
        self.assertIn("spg.spgsqyy", sql)
        self.assertIn("spg.spgpmtype = '5'", sql)
        self.assertIn("gross_business_amount - COALESCE(uo.overage_amount, 0)", sql)
        self.assertIn("IN ('2', '4')", sql)

    def test_debit_use_overage_falls_back_to_unique_goods_ticket_when_salehead_is_missing(self):
        sql = voucher_business_rows_ctes_sql()

        self.assertIn("FROM salegoodslist sgl", sql)
        self.assertIn("sgl.sgldate = utr.business_date", sql)
        self.assertIn("sgl.sglmarket = utr.market_code", sql)
        self.assertIn("sgl.sglsyjid = utr.cashier_id", sql)
        self.assertIn("sgl.sglinvno = utr.invoice_no::numeric", sql)
        self.assertIn("HAVING COUNT(DISTINCT sgl.sglbillno) = 1", sql)
        self.assertIn("COALESCE(ticket_head.billno, goods_fallback.billno)", sql)
        self.assertIn("SUM(use_amount) < 0 AS is_return", sql)
        self.assertIn("HAVING ABS(SUM(use_amount)) > 0.005", sql)

    def test_confirmed_match_sync_uses_front_actual_amount_and_targets_match_ids(self):
        sql = confirmed_voucher_match_movement_sql()

        self.assertIn("m.id = ANY(:voucher_match_ids)", sql)
        self.assertIn("front_sale.ysje", sql)
        self.assertIn("front_face_amount + backend_business_amount", sql)
        self.assertIn("'voucher_match:' || voucher_match_id::text", sql)
        self.assertIn("ON CONFLICT (source_type, source_key)", sql)


if __name__ == "__main__":
    unittest.main()
