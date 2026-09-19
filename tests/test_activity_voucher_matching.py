import unittest

from routers.activity_analysis import (
    CREDIT_BUY_MATCH_TYPE_NAME,
    _backend_coupon_recharge_condition_sql,
    _coupon_initial_issue_condition_sql,
    _voucher_match_flow_exclusion_sql,
    coupon_payment_allocation_sql,
    coupon_summary_source_code_sql,
    coupon_summary_source_name_sql,
    coupon_source_name_sql,
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

    def test_backend_coupon_recharge_source_reuses_voucher_match_identification(self):
        condition_sql = _backend_coupon_recharge_condition_sql("l")
        source_name_sql = coupon_source_name_sql("l")

        self.assertIn("l.tcflzy IN ('M', 'N')", condition_sql)
        self.assertIn("COALESCE(l.tcflsource, '')", condition_sql)
        self.assertIn("COALESCE(l.tcflsyjid, '')", condition_sql)
        self.assertIn("COALESCE(l.tcflinvno, '')", condition_sql)
        self.assertIn("= '2'", condition_sql)
        self.assertIn("= '0000'", condition_sql)
        self.assertIn(condition_sql, source_name_sql)
        self.assertIn("THEN '后台充券'", source_name_sql)
        self.assertIn("WHEN l.tcflsource = '2' THEN '前台买券'", source_name_sql)

    def test_coupon_summary_source_only_uses_initial_issue_actions(self):
        condition_sql = _coupon_initial_issue_condition_sql("l")
        source_code_sql = coupon_summary_source_code_sql("l")
        source_name_sql = coupon_summary_source_name_sql("l")

        self.assertEqual(
            condition_sql,
            "l.tcflzy IN ('F', 'm', 'M', 'Q', 'I', 'B', 'Z', 'b', 'X')",
        )
        self.assertIn(condition_sql, source_code_sql)
        self.assertIn("THEN l.tcflsource", source_code_sql)
        self.assertIn("ELSE NULL", source_code_sql)
        self.assertIn(condition_sql, source_name_sql)
        self.assertIn(coupon_source_name_sql("l"), source_name_sql)
        self.assertIn("ELSE NULL", source_name_sql)

    def test_coupon_payment_is_allocated_once_across_same_ticket_batch_logs(self):
        sql = coupon_payment_allocation_sql("l", "cp", "h")

        self.assertIn("WHEN l.tcflzy = 'O'", sql)
        self.assertIn("COALESCE(cp.coupon_pay_amount, 0)", sql)
        self.assertIn("ABS(COALESCE(l.tcflmoney, 0))", sql)
        self.assertIn("SUM(CASE WHEN l.tcflzy = 'O'", sql)
        self.assertIn("PARTITION BY h.billno, l.tcflsyjtrace::varchar", sql)
        self.assertIn("NULLIF", sql)

    def test_debit_use_business_amount_deducts_coupon_overage_once_per_ticket(self):
        sql = voucher_business_rows_ctes_sql()

        self.assertIn("GROUP BY", sql)
        self.assertIn("cashier_id", sql)
        self.assertIn("invoice_no", sql)
        self.assertIn("spg.spgsqyy", sql)
        self.assertIn("spg.spgpmtype = '5'", sql)
        self.assertIn("COALESCE(uo.overage_amount, 0)", sql)
        self.assertIn("COALESCE(uf.fallback_overage_amount, 0)", sql)
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

    def test_debit_use_overage_falls_back_to_sale_payments_when_allocation_is_missing(self):
        sql = voucher_business_rows_ctes_sql()

        self.assertIn("FROM salepay p", sql)
        self.assertIn("fallback_overage_amount", sql)
        self.assertIn("p.idno", sql)
        self.assertIn("p.memo", sql)
        self.assertIn("payments.target_coupon_payment", sql)
        self.assertIn("ticket_head.ysje", sql)
        self.assertIn("NOT EXISTS", sql)
        self.assertIn("COALESCE(uf.fallback_overage_amount, 0)", sql)

    def test_confirmed_match_sync_uses_front_actual_amount_and_targets_match_ids(self):
        sql = confirmed_voucher_match_movement_sql()

        self.assertIn("m.id = ANY(:voucher_match_ids)", sql)
        self.assertIn("front_sale.ysje", sql)
        self.assertIn("front_face_amount + backend_business_amount", sql)
        self.assertIn("'voucher_match:' || voucher_match_id::text", sql)
        self.assertIn("ON CONFLICT (source_type, source_key)", sql)


if __name__ == "__main__":
    unittest.main()
