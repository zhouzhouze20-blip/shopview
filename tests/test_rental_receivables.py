from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from python_app.services import rental_receivables as svc


def filters(**overrides):
    values = {
        "settle_from": date(2026, 1, 1),
        "settle_to": date(2026, 8, 14),
        "page": 1,
        "page_size": 50,
    }
    values.update(overrides)
    return svc.ReceivableFilters(**values)


def test_sql_preserves_receivable_business_definition_and_local_ods_schema():
    sql, params = svc.build_receivables_query(
        filters(),
        svc.BusinessScopeFilter(all_access=True),
    )

    assert "ods.hq_supsettlehead" in sql
    assert "ods.hq_supsettledettot" in sql
    assert "ods.hq_supsettlepaydet" not in sql
    assert "ods.hq_mallsuppayhead" not in sql
    assert "sh.sshwmid = '5'" in sql
    assert "sh.sshdjlb = 'Z'" in sql
    assert "sh.sshflag = 'Y'" in sql
    assert "NOT EXISTS" not in sql
    assert "HAVING ABS(SUM(CASE" in sql
    assert "THEN COALESCE(t.sdtye, 0) ELSE 0 END)) > 0.005" in sql
    assert "SUM(COALESCE(t.sdtye, 0)) < -0.005" not in sql
    assert "COALESCE(TRIM(t.sdtitemcode), '') NOT LIKE '00-%'" in sql
    assert "AS receivable_amount" in sql
    assert "COALESCE(TRIM(t.sdtitemcode), '') LIKE '00-%'" in sql
    assert "AS sales_refund_amount" in sql
    assert params["settle_from"] == date(2026, 1, 1)
    assert params["settle_to_exclusive"] == date(2026, 8, 15)


def test_sql_binds_supported_business_scope_and_pagination():
    scope = svc.BusinessScopeFilter(
        allow={
            "group": frozenset({"6020101173"}),
            "supplier": frozenset({"30643"}),
        },
        deny={"store": frozenset({"603"})},
    )
    sql, params = svc.build_receivables_query(
        filters(page=2, page_size=25, group_prefix="60201"),
        scope,
    )

    assert "TRIM(UPPER(COALESCE(sh.sshmfid, ''))) IN (:allow_group_0)" in sql
    assert "TRIM(UPPER(sh.sshsupid)) IN (:allow_supplier_0)" in sql
    assert "TRIM(UPPER(sh.sshmkt)) IN (:deny_store_0)" in sql
    assert "TRIM(UPPER(COALESCE(st.store_id::text, ''))) IN (:deny_store_0)" in sql
    assert "TRIM(UPPER(sh.sshmfid)) LIKE :group_prefix" in sql
    assert "rn BETWEEN :row_start AND :row_end" in sql
    assert params["allow_group_0"] == "6020101173"
    assert params["allow_supplier_0"] == "30643"
    assert params["deny_store_0"] == "603"
    assert params["group_prefix"] == "60201%"
    assert params["row_start"] == 26
    assert params["row_end"] == 50


def test_department_scope_is_supported_by_code_or_name():
    scope = svc.BusinessScopeFilter(
        allow={"department": frozenset({"财务部"})},
    )
    sql, params = svc.build_receivables_query(filters(), scope)
    assert "COALESCE(sh.department_code, '')" in sql
    assert "COALESCE(sh.department_name, '')" in sql
    assert params["allow_department_0"] == "财务部"


def test_department_filter_is_bound_independently_of_permission_scope():
    sql, params = svc.build_receivables_query(
        filters(department_code="6020101"),
        svc.BusinessScopeFilter(all_access=True),
    )
    assert "TRIM(UPPER(sh.department_code)) = :department_code" in sql
    assert params["department_code"] == "6020101"


class _FakeResult:
    def __init__(self, *, one=None, all_rows=None):
        self._one = one
        self._all = all_rows

    def mappings(self):
        return self

    def one(self):
        return self._one

    def all(self):
        return self._all


class _FakeSession:
    def __init__(self, row):
        self.row = row
        self.calls = []

    def execute(self, statement, params=None):
        self.calls.append((str(statement), params))
        if len(self.calls) == 1:
            return _FakeResult(
                one={
                    "head_rows": 13054,
                    "detail_rows": 327576,
                    "pay_detail_rows": 84043,
                    "pay_head_rows": 12262,
                    "source_loaded_at": datetime(2026, 8, 15, 0, 6, 54, tzinfo=ZoneInfo("Asia/Shanghai")),
                }
            )
        return _FakeResult(all_rows=[self.row])


def test_query_normalizes_local_rows_summary_and_freshness():
    db = _FakeSession(
        {
            "sshbillno": "260812602Z0000000006",
            "sshsupid": "30643",
            "supplier_name": "常州泰鼎珠宝有限公司",
            "sshmkt": "602",
            "store_name": "常州新世纪商城",
            "department_code": "6020101",
            "department_name": "营运一部",
            "sshmfid": "6020101173",
            "group_name": "老凤祥厅",
            "sshcontno": "30643001",
            "settle_from": date(2026, 6, 30),
            "settle_to": date(2026, 7, 31),
            "original_amount": Decimal("-37500.84"),
            "original_receivable_amount": Decimal("37500.84"),
            "receivable_amount": Decimal("10331.06"),
            "sales_refund_amount": Decimal("27168.94"),
            "aging_days": 14,
            "outstanding_status": "PARTIAL",
            "total_count": 3,
            "total_receivable_amount": Decimal("48000.00"),
            "total_original_amount": Decimal("75200.00"),
            "total_sales_refund_amount": Decimal("32168.94"),
            "partial_count": 1,
            "anomaly_count": 2,
            "over_90_amount": Decimal("5000.00"),
        }
    )

    result = svc.query_rental_receivables(
        db,
        filters(),
        svc.BusinessScopeFilter(all_access=True),
    )

    assert result["total"] == 3
    assert result["summary"] == {
        "bill_count": 3,
        "receivable_amount": 48000.0,
        "original_amount": 75200.0,
        "sales_refund_amount": 32168.94,
        "partial_count": 1,
        "anomaly_count": 2,
        "over_90_amount": 5000.0,
    }
    assert result["items"][0]["receivable_amount"] == 10331.06
    assert result["items"][0]["outstanding_status"] == "PARTIAL"
    assert result["items"][0]["department_name"] == "营运一部"
    assert result["source"]["name"] == "本地 ODS（PAPI 总部库同步）"
    assert result["source_loaded_at"].startswith("2026-08-15T00:06:54")
    assert "hq_supsettlepaydet" not in db.calls[0][0]
    assert "hq_mallsuppayhead" not in db.calls[0][0]
    assert "ods.hq_supsettlehead" in db.calls[1][0]


def test_sync_status_rejects_incomplete_first_load():
    class EmptySession:
        def execute(self, _statement, _params=None):
            return _FakeResult(
                one={
                    "head_rows": 1,
                    "detail_rows": 0,
                    "pay_detail_rows": 1,
                    "pay_head_rows": 1,
                    "source_loaded_at": None,
                }
            )

    with pytest.raises(svc.OdsUnavailableError, match="尚未完成首次同步"):
        svc.query_rental_receivables(
            EmptySession(),
            filters(),
            svc.BusinessScopeFilter(all_access=True),
        )


def test_filter_options_are_permission_scoped_and_grouped_by_store():
    class OptionsSession:
        def __init__(self):
            self.sql = ""
            self.params = {}

        def execute(self, statement, params=None):
            self.sql = str(statement)
            self.params = params or {}
            return _FakeResult(
                all_rows=[
                    {
                        "store_code": "602",
                        "store_name": "常州新世纪商城",
                        "department_code": "6020101",
                        "department_name": "营运一部",
                    },
                    {
                        "store_code": "602",
                        "store_name": "常州新世纪商城",
                        "department_code": "6020112",
                        "department_name": "营运六部",
                    },
                ]
            )

    db = OptionsSession()
    result = svc.query_rental_receivable_options(
        db,
        svc.BusinessScopeFilter(allow={"store": frozenset({"2"})}),
    )

    assert result["stores"] == [{"store_code": "602", "store_name": "常州新世纪商城"}]
    assert [row["department_code"] for row in result["departments"]] == ["6020101", "6020112"]
    assert "st.store_id::text" in db.sql
    assert db.params["allow_store_0"] == "2"


def test_sql_marks_absolute_receivable_balance_above_receivable_original_as_anomaly():
    sql = svc.build_receivables_sql(
        filters(),
        svc.BusinessScopeFilter(all_access=True),
    )
    assert "ABS(receivable_amount) > original_receivable_amount + 0.005 THEN 'EXCEEDS_ORIGINAL'" in sql
    assert "AS anomaly_count" in sql


def test_invalid_code_is_rejected_before_local_query():
    with pytest.raises(ValueError, match="编码只能包含"):
        svc.build_receivables_sql(
            filters(mkt="602' OR 1=1"),
            svc.BusinessScopeFilter(all_access=True),
        )


def test_expense_export_query_reuses_filters_scope_and_only_exports_nonzero_lines():
    sql, params = svc.build_receivable_expense_export_query(
        filters(mkt="602", department_code="6020101", group_prefix="60201", keyword="泰鼎"),
        svc.BusinessScopeFilter(allow={"store": frozenset({"2"})}),
    )

    assert "WITH eligible_bills AS" in sql
    assert "HAVING ABS(SUM(CASE" in sql
    assert "detail.sdtbillno = bill.sshbillno" in sql
    assert "ABS(COALESCE(detail.sdtye, 0)) > 0.005" in sql
    assert "TRIM(UPPER(sh.sshmkt)) = :mkt" in sql
    assert "TRIM(UPPER(sh.department_code)) = :department_code" in sql
    assert "TRIM(UPPER(sh.sshmfid)) LIKE :group_prefix" in sql
    assert "allow_store_0" in params
    assert params["export_limit_plus_one"] == svc.MAX_EXPORT_DETAIL_ROWS + 1


def test_expense_export_preserves_signed_rows_and_marks_sales_refunds():
    class ExportSession:
        def __init__(self):
            self.calls = []

        def execute(self, statement, params=None):
            self.calls.append((str(statement), params or {}))
            if len(self.calls) == 1:
                return _FakeResult(
                    one={
                        "head_rows": 10,
                        "detail_rows": 20,
                        "source_loaded_at": datetime(2026, 8, 17, 3, 31, 25, tzinfo=ZoneInfo("Asia/Shanghai")),
                    }
                )
            common = {
                "sshbillno": "260812602Z0000000006",
                "sshsupid": "30643",
                "supplier_name": "常州泰鼎珠宝有限公司",
                "sshmkt": "602",
                "store_name": "常州百货大楼",
                "department_code": "6020101",
                "department_name": "营运一部",
                "sshmfid": "6020101173",
                "group_name": "老凤祥厅",
                "sshcontno": "30643001",
                "sshlastdate": date(2026, 6, 30),
                "sshthisdate": date(2026, 7, 31),
                "bill_receivable_amount": Decimal("1376.20"),
                "sdtflag": "Y",
                "sdtstartdate": date(2026, 7, 1),
                "sdtenddate": date(2026, 7, 31),
                "sdtckamount": Decimal("0"),
                "sdtyfamount": Decimal("0"),
                "sdtdkamount": Decimal("0"),
                "sdtadjamount": Decimal("0"),
                "sdtxssr": Decimal("0"),
                "sdthsy": "202607",
                "sdtcalcplace": "CHARGELIST",
                "sdtmfjzmj": Decimal("88"),
                "sdtmfzjmj": Decimal("88"),
                "sdttaxrate": Decimal("0"),
                "sdtnotaxamount": Decimal("0"),
                "sdtmemo": None,
                "sdtisadv": "N",
            }
            return _FakeResult(
                all_rows=[
                    {
                        **common,
                        "sdtrowno": 1,
                        "sdtitemcode": "60",
                        "item_name_raw": "×â½ð(¹Ì¶¨)",
                        "payment_name_raw": None,
                        "sdtamount": Decimal("4695.40"),
                        "sdtye": Decimal("4695.40"),
                    },
                    {
                        **common,
                        "sdtrowno": 2,
                        "sdtitemcode": "00-0303",
                        "item_name_raw": None,
                        "payment_name_raw": "ÐÅÓÃ¿¨",
                        "sdtamount": Decimal("-42196.24"),
                        "sdtye": Decimal("-42196.24"),
                    },
                ]
            )

    report = svc.query_rental_receivable_expense_export(
        ExportSession(),
        filters(),
        svc.BusinessScopeFilter(all_access=True),
    )

    assert report["bill_count"] == 1
    assert report["detail_count"] == 2
    assert report["items"][0]["item_name"] == "租金(固定)"
    assert report["items"][0]["receivable_component"] == 4695.4
    assert report["items"][1]["item_name"] == "银联聚合支付"
    assert report["items"][1]["balance_amount"] == -42196.24
    assert report["items"][1]["receivable_component"] == 0
    assert report["items"][1]["is_sales_refund"] is True


def test_detail_query_enforces_scope_decodes_item_name_and_reconciles_amount():
    class DetailSession:
        def __init__(self):
            self.sql = ""
            self.params = {}

        def execute(self, statement, params=None):
            self.sql = str(statement)
            self.params = params or {}
            common = {
                "sshbillno": "260812602Z0000000006",
                "sshsupid": "30643",
                "supplier_name": "常州泰鼎珠宝有限公司",
                "sshmkt": "602",
                "store_name": "常州百货大楼",
                "department_code": "6020101",
                "department_name": "营运一部",
                "sshmfid": "6020101173",
                "group_name": "老凤祥厅",
                "sshcontno": "30643001",
                "sshlastdate": date(2026, 6, 30),
                "sshthisdate": date(2026, 7, 31),
                "sdtflag": "Y",
                "sdtstartdate": date(2026, 7, 1),
                "sdtenddate": date(2026, 7, 31),
                "sdtckamount": Decimal("0"),
                "sdtyfamount": Decimal("0"),
                "sdtmemo": None,
                "sdtdkamount": Decimal("0"),
                "sdttype": "N",
                "sdtisadv": "N",
                "sdtadjamount": Decimal("0"),
                "sdtxssr": Decimal("0"),
                "sdthsy": "202607",
                "sdtcalcplace": "CHARGELIST",
                "sdtmfjzmj": Decimal("88"),
                "sdtmfzjmj": Decimal("88"),
                "sdttaxrate": Decimal("0"),
                "sdtnotaxamount": Decimal("0"),
                "source_loaded_at": datetime(2026, 8, 14, 17, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
            }
            return _FakeResult(
                all_rows=[
                    {
                        **common,
                        "sdtrowno": 1,
                        "sdtitemcode": "60",
                        "item_name_raw": "×â½ð(¹Ì¶¨)",
                        "sdtamount": Decimal("4695.40"),
                        "sdtye": Decimal("4695.40"),
                    },
                    {
                        **common,
                        "sdtrowno": 2,
                        "sdtitemcode": "00-0303",
                        "item_name_raw": None,
                        "payment_name_raw": "ÐÅÓÃ¿¨",
                        "sdtamount": Decimal("-42196.24"),
                        "sdtye": Decimal("-42196.24"),
                    },
                    {
                        **common,
                        "sdtrowno": 3,
                        "sdtitemcode": "01",
                        "item_name_raw": "×â½ð",
                        "payment_name_raw": None,
                        "sdtamount": Decimal("-3319.20"),
                        "sdtye": Decimal("-3319.20"),
                    },
                ]
            )

    db = DetailSession()
    result = svc.query_rental_receivable_detail(
        db,
        "260812602Z0000000006",
        svc.BusinessScopeFilter(allow={"department": frozenset({"营运一部"})}),
    )

    assert result["bill"]["department_code"] == "6020101"
    assert result["items"][0]["item_name"] == "租金(固定)"
    assert result["items"][1]["item_name"] == "银联聚合支付"
    assert result["totals"]["balance_amount"] == -40820.04
    assert result["totals"]["receivable_amount"] == 1376.2
    assert result["totals"]["sales_refund_amount"] == 42196.24
    assert result["items"][0]["receivable_component"] == 4695.4
    assert result["items"][0]["is_receivable_line"] is True
    assert result["items"][1]["receivable_component"] == 0
    assert result["items"][1]["is_sales_refund"] is True
    assert result["items"][2]["receivable_component"] == -3319.2
    assert result["items"][2]["is_receivable_line"] is True
    assert result["detail_count"] == 3
    assert result["nonzero_count"] == 3
    assert "allow_department_0" in db.params
    assert "NOT EXISTS" not in db.sql
    assert db.params["bill_no"] == "260812602Z0000000006"


def test_composite_payment_codes_use_exported_fuji_item_names():
    assert svc._detail_item_name("00-0330", None, "ÐÂÊÀ¼ÍÀñÈ¯") == "0330 瑞祥卡实体卡"
    assert svc._detail_item_name("00-2030", None, "ÐÂÊÀ¼ÍÀñÈ¯") == "2030建行数币（优惠）"
    assert svc._detail_item_name("00-9999", None, "ÍøÒø×ªÕÊ") == "券返款"
    assert svc._detail_item_name("00-7777", None, None) == "支付项目（00-7777）"


def test_detail_query_hides_missing_or_unauthorized_bill():
    class EmptyDetailSession:
        def execute(self, _statement, _params=None):
            return _FakeResult(all_rows=[])

    with pytest.raises(svc.ReceivableNotFoundError, match="权限范围"):
        svc.query_rental_receivable_detail(
            EmptyDetailSession(),
            "260812602Z0000000006",
            svc.BusinessScopeFilter(allow={"store": frozenset({"601"})}),
        )


def test_mobile_drilldown_query_reapplies_scope_and_parent_filters_at_every_level():
    sql, params = svc.build_mobile_drilldown_query(
        level="group",
        settle_from=date(2026, 1, 1),
        settle_to=date(2026, 8, 15),
        scope=svc.BusinessScopeFilter(
            allow={"department": frozenset({"6020101"})},
            deny={"group": frozenset({"6020101999"})},
        ),
        mkt="602",
        department_code="6020101",
    )

    assert "ods.hq_supsettlehead" in sql
    assert "ods.hq_supsettledettot" in sql
    assert "TRIM(UPPER(sh.sshmkt)) = :mkt" in sql
    assert "TRIM(UPPER(sh.department_code)) = :department_code" in sql
    assert "allow_department_0" in params
    assert "deny_group_0" in params
    assert params["mkt"] == "602"
    assert params["department_code"] == "6020101"
    assert "NOT LIKE '00-%'" in sql
    assert "COUNT(*) AS bill_count" in sql


def test_mobile_drilldown_requires_complete_parent_path():
    with pytest.raises(ValueError, match="门店"):
        svc.build_mobile_drilldown_query(
            level="department",
            settle_from=date(2026, 1, 1),
            settle_to=date(2026, 8, 15),
            scope=svc.BusinessScopeFilter(all_access=True),
        )

    with pytest.raises(ValueError, match="部门"):
        svc.build_mobile_drilldown_query(
            level="group",
            settle_from=date(2026, 1, 1),
            settle_to=date(2026, 8, 15),
            scope=svc.BusinessScopeFilter(all_access=True),
            mkt="602",
        )


def test_mobile_bill_filter_uses_exact_group_code_not_prefix():
    sql, params = svc.build_receivables_query(
        filters(mkt="602", department_code="6020101", group_code="6020102127"),
        svc.BusinessScopeFilter(all_access=True),
    )

    assert "TRIM(UPPER(sh.sshmfid)) = :group_code" in sql
    assert params["group_code"] == "6020102127"


def test_mobile_drilldown_uses_fixed_store_order_and_sales_dashboard_department_order():
    stores = [
        {"code": "604", "name": "常州半山书局"},
        {"code": "602", "name": "常州百货大楼"},
        {"code": "601", "name": "常州购物中心"},
        {"code": "603", "name": "常州新世纪商城"},
    ]
    departments = [
        {"code": "6030116", "name": "新世纪十部(特业)"},
        {"code": "6030112", "name": "新世纪三部"},
        {"code": "6030101", "name": "新世纪一部"},
    ]

    assert [row["code"] for row in svc._sort_mobile_drilldown_items("store", stores)] == [
        "601",
        "602",
        "603",
        "604",
    ]
    assert [row["code"] for row in svc._sort_mobile_drilldown_items("department", departments)] == [
        "6030101",
        "6030112",
        "6030116",
    ]
