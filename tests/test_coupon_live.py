"""Money, first-issue period, cohort privacy and local-calendar boundaries."""
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import sys

import pytest
from fastapi import HTTPException, Response

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_app"))
from routers.authz import DataScope
from services.activity_analysis import coupon_live as live

TODAY = date(2026, 9, 18)
END = date(2026, 9, 27)
ADMIN = DataScope(all_access=True)
DEPT = DataScope(allow={"department": {"D3"}})


def issue(coupon="E", asset="1", **updates):
    return dict(coupon_type=coupon, asset_id=asset, amount=100, issue_date=date(2026, 9, 15), **updates)


def flow(coupon="E", asset="1", member="M1", bill="100", action="O", amount=100, day=TODAY):
    return dict(coupon_type=coupon, asset_id=asset, member_no=member, billno=bill,
                action=action, amount=amount, flow_date=day)


def line(bill="100", sales=1000, department="D3", member="M1", **updates):
    row = dict(billno=bill, original_billno="0", sale_time=f"{TODAY} 12:00:00", checkout_member_no=member,
               sales=sales, gross_profit=sales * .2, allocation_base=abs(sales), department_code=department,
               department_name=department, group_code=department + "G", group_name=department + "柜",
               brand_code="BR", brand_name="品牌", supplier_code="SP", category_code="C", category_name="品类", floor_code="3")
    return dict(row, **updates)


def report(flows=None, sales=None, scope=ADMIN, issues=None, today=TODAY, query_start=None, query_end=None):
    return live.build_report([issue()] if issues is None else issues,
                             [flow()] if flows is None else flows,
                             [line()] if sales is None else sales, scope, "1", today, END, query_start, query_end)


def coupon(result, c="E"):
    return next(row for row in result["coupons"] if row["coupon_type"] == c)


def test_preissued_is_counted_and_not_confused_with_today():
    row = coupon(report())
    assert row["issued_count"] == row["preissued_count"] == 1
    assert row["issued_amount"] == 100 and row["net_coupon_amount"] == 100


def test_real_return_without_refunding_coupon_reduces_sales():
    r = report(sales=[line(), line("101", -400, original_billno="100")])
    assert coupon(r)["linked_sales"] == 600
    assert coupon(r)["linked_returns"] == -400
    assert coupon(r)["net_coupon_amount"] == 100
    assert sum(row["sales"] for row in r["member_trajectory"]) == 600
    returned = next(row for row in r["member_trajectory"] if row["billno"] == "101")
    assert returned["ticket_kind"] == "退货" and returned["ticket_coupon_types"] == ["E"]


def test_refund_is_not_double_subtracted_from_sales():
    r = report(flows=[flow(), flow(bill="101", action="P", amount=40)],
               sales=[line(), line("101", -400, original_billno="100")])
    assert coupon(r)["net_coupon_amount"] == 60
    assert coupon(r)["linked_sales"] == 600


def test_canceled_use_does_not_establish_holder_cohort_or_linked_sale():
    r = report(flows=[flow(), flow(action="U")])
    assert coupon(r)["net_coupon_amount"] == 0
    assert coupon(r)["linked_sales"] == 0
    assert r["trajectory"] == [] and coupon(r)["used_assets"] == 0


def test_refund_reversal_restores_net_amount():
    r = report(flows=[flow(), flow(action="P", amount=40), flow(action="V", amount=40)])
    assert coupon(r)["net_coupon_amount"] == 100


def test_multiple_coupons_and_holders_allocate_receipt_once():
    r = report(flows=[flow(amount=100), flow("R", "2", "M2", amount=300)],
               issues=[issue(), issue("R", "2")])
    assert coupon(r)["linked_sales"] == 250 and coupon(r, "R")["linked_sales"] == 750
    assert sum(x["sales"] for x in r["tickets"]) == 1000
    assert r["distinct_used_members"] == 2 and r["distinct_use_tickets"] == 1


def test_mixed_department_receipt_hides_other_department_and_store_issuance():
    r = report(sales=[line(sales=400), line(sales=600, department="D4")], scope=DEPT)
    c = coupon(r)
    assert c["issued_count"] is None and c["issued_amount"] is None
    assert c["redeemed_amount"] == 40 and c["linked_sales"] == 400
    assert {row["department"] for row in r["tickets"]} == {"D3"}
    assert {row["department"] for row in r["trajectory"]} == {"D3"}
    assert {row["department"] for row in r["member_trajectory"]} == {"D3"}
    assert sum(row["sales"] for row in r["member_trajectory"]) == 400


def test_hidden_coupon_users_do_not_enter_trajectory_even_if_they_shop_in_visible_department():
    r = report(sales=[line(department="D4"), line("102", 500)], scope=DEPT)
    assert coupon(r)["used_assets"] == coupon(r)["used_members"] == 0
    assert r["trajectory"] == [] and r["tickets"] == []
    assert r["member_trajectory"] == []
    assert r["quality"] == {"unmatched_flow_count": 0, "missing_issue_flow_count": 0, "missing_sales_flow_count": 0}


def test_previous_day_e_usage_establishes_today_shopping_cohort():
    r = report(flows=[flow()], sales=[line(), line("102", 300, sale_time="2026-09-19 10:00:00")], today=date(2026, 9, 19))
    assert len(r["trajectory"]) == 1
    assert r["trajectory"][0]["billno"] == "102"
    assert r["trajectory"][0]["coupon_types"] == "未用本档跟踪券"


def test_holder_and_shopper_are_distinct_and_unrelated_shopping_not_attributed():
    r = report(sales=[line(member="OTHER"), line("102", 300), line("103", 999, member="OTHER")])
    assert {row["billno"] for row in r["trajectory"]} == {"100", "102"}
    assert "待核查" in r["trajectory"][0]["event_type"]


@pytest.mark.parametrize("scope", [DataScope(), DataScope(allow={"store": {"603"}}),
    DataScope(all_access=True, deny={"store": {"601"}}), DataScope(all_access=True, deny={"store": {"1"}}),
    DataScope(all_access=True, deny={"__all__": set()}), DataScope(all_access=True, deny={"unknown": {"x"}}),
    DataScope(allow={"self": {"1"}})])
def test_scope_denials(scope):
    with pytest.raises(PermissionError):
        report(scope=scope)


@pytest.mark.parametrize("dimension,value", [("department", "D3"), ("group", "D3G"), ("brand", "BR"),
    ("supplier", "SP"), ("category", "C"), ("floor", "3"), ("store", "601"), ("store", "1")])
def test_every_supported_allow_dimension(dimension, value):
    scope = DataScope(allow={dimension: {value}})
    assert live.visible_line(scope, "1", line())


@pytest.mark.parametrize("dimension,value", [("department", "D3"), ("group", "D3G"), ("brand", "BR"),
    ("supplier", "SP"), ("category", "C"), ("floor", "3")])
def test_deny_overrides_admin(dimension, value):
    scope = DataScope(all_access=True, deny={dimension: {value}})
    assert not live.visible_line(scope, "1", line())
    assert not live.check_scope(scope, "1")


def test_unresolved_name_cannot_bypass_deny():
    scope = DataScope(all_access=True, deny={"department": {"中心三部"}})
    assert not live.visible_line(scope, "1", line(department_name=None))


def test_empty_data_is_zero_not_a_fake_period():
    r = report(flows=[], issues=[], sales=[])
    assert all(c["linked_sales"] == 0 for c in r["coupons"])
    assert r["daily"] == [] and r["trajectory"] == []


def test_unmatched_flows_are_flagged_and_not_used_to_invent_sales():
    r = report(flows=[flow(bill=None)], issues=[], sales=[])
    assert coupon(r)["net_coupon_amount"] == 100 and coupon(r)["linked_sales"] == 0
    assert r["quality"] == dict(unmatched_flow_count=1, missing_issue_flow_count=1, missing_sales_flow_count=0)
    assert report(flows=[flow(bill=None)], issues=[], sales=[], scope=DEPT)["quality"]["unmatched_flow_count"] == 0


def test_multiple_periods_require_selection_and_do_not_query_detail(monkeypatch):
    calls = []
    def rows(db, sql, params):
        calls.append(sql)
        return [dict(valid_from=TODAY, valid_to=END), dict(valid_from=TODAY, valid_to=date(2026, 9, 30))]
    monkeypatch.setattr(live, "limited_rows", rows)
    assert live.query_report(Mock(), ADMIN, "1", today=TODAY)["status"] == "choose_period"
    assert calls == [live.PERIOD_SQL]
    with pytest.raises(ValueError):
        live.query_report(Mock(), ADMIN, "1", date(2026, 10, 1), TODAY)


def test_future_and_postperiod_dates_are_bounded_without_campaign_dependency(monkeypatch):
    calls = []
    def rows(db, sql, params):
        calls.append((sql, params.copy()))
        return [dict(valid_from=TODAY, valid_to=END)] if sql == live.PERIOD_SQL else []
    monkeypatch.setattr(live, "limited_rows", rows)
    result = live.query_report(Mock(), ADMIN, "1", today=date(2026, 10, 2))
    assert result["observed_end"] == END.isoformat()
    assert calls[1][1]["end_exclusive"] == date(2026, 9, 28)
    assert calls[2][1]["data_end"] == date(2026, 9, 28)
    assert all("coupon_campaigns" not in sql and "ownership" not in sql for sql, _ in calls)
    assert "l.tcflenddate<=:end_date" in live.FLOW_SQL


def test_route_permission_checked_before_business_data(monkeypatch):
    from routers import coupon_live as route
    def deny(*args):
        raise HTTPException(403, "无功能权限")
    monkeypatch.setattr(route, "require_permission", deny)
    db = Mock()
    with pytest.raises(HTTPException):
        route.report(Response(), None, db, SimpleNamespace(user_id=1))
    db.execute.assert_not_called()


def test_return_proxy_holder_keeps_today_return_in_trajectory():
    r = report(sales=[line(member="OTHER"), line("101", -400, member="OTHER", original_billno="100")])
    assert {row["billno"] for row in r["trajectory"]} == {"100", "101"}


def test_cent_allocation_preserves_signed_sales_and_profit():
    from decimal import Decimal
    weights = {("E", "A"): Decimal(1), ("R", "B"): Decimal(1), ("D", "C"): Decimal(1)}
    for amount in (1, -1, 100.01, -100.01):
        assert sum(live.split_money(amount, weights).values()) == Decimal(str(amount))


def test_missing_merchandise_is_not_silently_a_zero_sale():
    result = report(sales=[])
    assert result["quality"]["missing_sales_flow_count"] == 1
    assert coupon(result)["linked_sales"] == 0


def test_group_drilldown_reconciles_departments_with_coupons_refunds_and_returns():
    result = report(
        flows=[flow(amount=100), flow("R", "2", "M2", amount=300),
               flow(bill="101", action="P", amount=40), flow(bill="101", action="V", amount=10)],
        sales=[line(sales=400, group_code="G1", group_name="一柜"),
               line(sales=200, group_code="G2", group_name="二柜", brand_code="BR2"),
               line(sales=100, group_code="G2", group_name="二柜", brand_code="BR3"),
               line(sales=300, department="D4"),
               line("101", -400, original_billno="100", group_code="G1", group_name="一柜"),
               line("102", -100, original_billno="100", group_code="G2", group_name="二柜")],
    )
    metrics = ("redeemed_amount", "refunded_amount", "net_coupon_amount", "linked_sales",
               "linked_returns", "linked_gross_profit")
    for department in result["departments"]:
        groups = [row for row in result["groups"]
                  if (row["department_code"], row["coupon_type"]) ==
                  (department["department_code"], department["coupon_type"])]
        for key in metrics:
            assert sum(row[key] for row in groups) == pytest.approx(department[key])
    e_groups = {row["group_code"]: row for row in result["groups"] if row["coupon_type"] == "E"}
    assert len(e_groups) == 3  # Multiple brands in G2 do not create duplicate group rows.
    assert e_groups["G1"]["redeemed_amount"] == 40
    assert e_groups["G1"]["refunded_amount"] == 30
    assert e_groups["G1"]["linked_sales"] == 0
    assert e_groups["G2"]["linked_sales"] == 50  # Actual return without refund still deducted.
    assert e_groups["G2"]["linked_returns"] == -25


@pytest.mark.parametrize("scope,expected_groups,expected_coupon", [
    (DEPT, {"G1", "G2"}, 60),
    (DataScope(allow={"group": {"G1"}}), {"G1"}, 40),
    (DataScope(all_access=True, deny={"group": {"G1"}}), {"G2", "G4"}, 60),
])
def test_group_drilldown_filters_lines_before_aggregation(scope, expected_groups, expected_coupon):
    result = report(scope=scope, sales=[line(sales=400, group_code="G1"),
                                       line(sales=200, group_code="G2"),
                                       line(sales=400, department="D4", group_code="G4")])
    assert {row["group_code"] for row in result["groups"]} == expected_groups
    assert sum(row["redeemed_amount"] for row in result["groups"]) == expected_coupon
    assert coupon(result)["redeemed_amount"] == expected_coupon


def test_same_name_departments_and_groups_are_kept_separate_by_code():
    result = report(sales=[line(sales=400, department_name="同名部门", group_code="G1", group_name="同名柜组"),
                           line(sales=600, department="D4", department_name="同名部门",
                                group_code="G2", group_name="同名柜组")])
    assert len(result["departments"]) == len(result["groups"]) == 2
    assert {row["department_code"] for row in result["departments"]} == {"D3", "D4"}
    assert {row["group_code"] for row in result["groups"]} == {"G1", "G2"}


def test_group_drilldown_handles_empty_unknown_and_canceled_records():
    assert report(flows=[], sales=[])["groups"] == []
    result = report(flows=[flow(), flow(action="U", amount=40)],
                    sales=[line(department_code=None, department_name=None, group_code=None, group_name=None)])
    row = result["groups"][0]
    assert row["department"] == "未识别部门" and row["group_name"] == "未识别柜组"
    assert row["department_code"] == row["group_code"] == ""
    assert row["redeemed_amount"] == 60


def test_single_day_query_includes_only_that_days_use_sales_and_returns():
    day = date(2026, 9, 19)
    result = report(today=day, query_start=day, query_end=day,
        flows=[flow(), flow(bill="101", action="P", amount=40, day=day),
               flow(bill="102", member="M2", asset="2", day=day)],
        sales=[line(), line("101", -400, original_billno="100", sale_time="2026-09-19 00:00:00"),
               line("102", 1200, member="M2", sale_time="2026-09-19 23:59:59"),
               line("103", 9999, sale_time="2026-09-20 00:00:00")])
    c = coupon(result)
    assert c["redeemed_amount"] == 100 and c["refunded_amount"] == 40
    assert c["linked_sales"] == 800 and c["linked_returns"] == -400
    assert c["used_members"] == c["use_tickets"] == 1
    assert result["query_start"] == result["query_end"] == "2026-09-19"
    assert result["tracking_start"] == "2026-09-18" and result["valid_to"] == "2026-09-27"
    assert {row["day"] for row in result["daily"]} == {"2026-09-19"}
    assert {row["billno"] for row in result["tickets"]} == {"101", "102"}
    assert sum(row["linked_sales"] for row in result["groups"]) == 800
    assert {row["holder_member_no"] for row in result["trajectory"]} == {"M2"}


def test_historical_window_does_not_include_later_reversals_but_trajectory_is_today():
    day = date(2026, 9, 19)
    result = report(today=day, query_start=TODAY, query_end=TODAY,
        flows=[flow(), flow(action="U", day=day)],
        issues=[issue(), dict(issue(asset="later"), issue_date=day)],
        sales=[line(), line("101", 200, sale_time="2026-09-19 09:00:00")])
    c = coupon(result)
    assert c["redeemed_amount"] == 100 and c["linked_sales"] == 1000
    assert c["issued_count"] == c["preissued_count"] == 1
    assert {row["billno"] for row in result["trajectory"]} == {"101"}
    assert result["trajectory"][0]["sales"] == 200
    assert {row["billno"] for row in result["member_trajectory"]} == {"100"}
    assert result["member_trajectory"][0]["ticket_coupon_types"] == ["E"]


def test_member_period_includes_own_other_shopping_and_returns_on_selected_dates_not_today():
    tomorrow = date(2026, 9, 19)
    result = report(today=tomorrow, query_start=TODAY, query_end=TODAY,
        sales=[line(), line("101", 300), line("102", -100, original_billno="101"),
               line("103", 9999, sale_time="2026-09-19 12:00:00")])
    assert result["member_period_available"] is True
    assert {row["billno"] for row in result["member_trajectory"]} == {"100", "101", "102"}
    assert sum(row["sales"] for row in result["member_trajectory"]) == 1200
    assert {row["billno"] for row in result["trajectory"]} == {"103"}


def test_member_period_query_loads_historical_holder_purchases_even_after_campaign(monkeypatch):
    calls = []
    def rows(db, sql, params):
        calls.append((sql, params.copy()))
        if sql == live.PERIOD_SQL:
            return [dict(valid_from=TODAY, valid_to=END)]
        if sql == live.FLOW_SQL:
            return [flow()]
        if sql == live.SALES_SQL:
            return [line(), line("200", 300)] if params["holders"] else [line()]
        return []
    monkeypatch.setattr(live, "limited_rows", rows)
    result = live.query_report(Mock(), ADMIN, "1", today=date(2026, 10, 1), query_start=TODAY, query_end=TODAY)
    assert calls[-1][1]["holders"] == ["M1"]
    assert calls[-1][1]["member_start"] == TODAY
    assert calls[-1][1]["member_end"] == date(2026, 9, 19)
    assert result["trajectory_available"] is False
    assert result["member_period_available"] is True
    assert {row["billno"] for row in result["member_trajectory"]} == {"100", "200"}


@pytest.mark.parametrize("start,expected", [(TODAY, {"100", "101", "102"}),
                                         (date(2026, 9, 19), {"101", "102"})])
def test_member_period_inclusive_boundaries_and_later_single_day(start, expected):
    day = date(2026, 9, 19)
    result = report(today=date(2026, 9, 20), query_start=start, query_end=day,
        flows=[flow(), flow(bill="101", asset="2", day=day)],
        sales=[line(sale_time="2026-09-18 00:00:00"),
               line("101", 300, sale_time="2026-09-19 00:00:00"),
               line("102", -100, original_billno="100", sale_time="2026-09-19 23:59:59"),
               line("103", 9999, sale_time="2026-09-20 00:00:00")])
    assert {row["billno"] for row in result["member_trajectory"]} == expected
    assert {row["billno"] for row in result["trajectory"]} == {"103"}


def test_historical_member_period_keeps_department_scope_and_holder_cohort():
    result = report(today=date(2026, 9, 19), query_start=TODAY, query_end=TODAY, scope=DEPT,
        flows=[flow(), flow(bill="200", member="HIDDEN", asset="2")],
        sales=[line(sales=400), line(sales=600, department="D4"),
               line("101", 300), line("102", 9999, department="D4"),
               line("200", 9999, department="D4", member="HIDDEN"),
               line("201", 9999, member="HIDDEN")])
    assert {row["holder_member_no"] for row in result["holders"]} == {"M1"}
    assert {row["department"] for row in result["member_trajectory"]} == {"D3"}
    assert {row["billno"] for row in result["member_trajectory"]} == {"100", "101"}
    assert sum(row["sales"] for row in result["member_trajectory"]) == 700


def test_daily_return_without_refund_keeps_previous_original_as_context_only():
    day = date(2026, 9, 19)
    result = report(today=day, query_start=day, query_end=day,
        sales=[line(), line("101", -400, original_billno="100", sale_time="2026-09-19 12:00:00")])
    c = coupon(result)
    assert c["redeemed_amount"] == c["refunded_amount"] == c["used_members"] == 0
    assert c["linked_sales"] == c["linked_returns"] == -400
    assert result["trajectory"] == []


def test_selected_day_partial_scope_preserves_money_and_cohort_privacy():
    day = date(2026, 9, 19)
    result = report(today=day, query_start=day, query_end=day, scope=DEPT,
        flows=[flow(), flow(bill="102", member="HIDDEN", day=day)],
        sales=[line(), line("101", -200, original_billno="100", sale_time="2026-09-19 10:00:00"),
               line("102", department="D4", member="HIDDEN", sale_time="2026-09-19 12:00:00"),
               line("103", member="HIDDEN", sale_time="2026-09-19 14:00:00")])
    assert coupon(result)["linked_sales"] == -200
    assert coupon(result)["used_members"] == 0
    assert result["trajectory"] == []
    assert {row["department_code"] for row in result["groups"]} == {"D3"}


@pytest.mark.parametrize("start,end,message", [
    (date(2026, 9, 19), TODAY, "开始日期"),
    (date(2026, 9, 17), TODAY, "有效期"),
    (TODAY, date(2026, 9, 28), "有效期"),
    (date(2026, 9, 19), date(2026, 9, 19), "未来日期"),
])
def test_query_dates_are_validated_before_detail_queries(monkeypatch, start, end, message):
    rows = Mock(return_value=[dict(valid_from=TODAY, valid_to=END)])
    monkeypatch.setattr(live, "limited_rows", rows)
    with pytest.raises(ValueError, match=message):
        live.query_report(Mock(), ADMIN, "1", today=TODAY, query_start=start, query_end=end)
    assert rows.call_count == 1


def test_query_window_keeps_validity_and_prior_flows_for_attribution(monkeypatch):
    calls = []
    day = date(2026, 9, 19)
    def rows(db, sql, params):
        calls.append((sql, params.copy()))
        if sql == live.PERIOD_SQL:
            return [dict(valid_from=TODAY, valid_to=END)]
        if sql == live.FLOW_SQL:
            return [flow(), flow(bill="102", member="M2", day=day)]
        if sql == live.SALES_SQL:
            return [line(), line("102", sale_time="2026-09-19 12:00:00", member="M2")]
        return [issue()]
    monkeypatch.setattr(live, "limited_rows", rows)
    result = live.query_report(Mock(), ADMIN, "1", today=day, query_start=day, query_end=day)
    assert all(params["start_date"] == TODAY for _, params in calls)
    assert calls[1][1]["end_date"] == END  # Coupon validity is not the selected query date.
    assert calls[1][1]["end_exclusive"] == date(2026, 9, 20)
    assert calls[-1][1]["holders"] == ["M2"]
    assert calls[-1][1]["member_start"] == day
    assert calls[-1][1]["member_end"] == date(2026, 9, 20)
    assert "rqsj>=:member_start AND rqsj<:member_end" in live.SALES_SQL
    assert coupon(result)["redeemed_amount"] == 100


def test_route_passes_both_query_dates_without_changing_authorization(monkeypatch):
    from routers import coupon_live as route
    monkeypatch.setattr(route, "require_permission", Mock())
    monkeypatch.setattr(route, "load_business_scope", Mock(return_value=ADMIN))
    query = Mock(return_value={"status": "ready"})
    monkeypatch.setattr(route, "query_report", query)
    db = Mock()
    db.execute.return_value.scalar_one_or_none.return_value = "1"
    response = Response()
    route.report(response, END, db, SimpleNamespace(user_id=1), TODAY, TODAY)
    query.assert_called_once_with(db, ADMIN, "1", END, query_start=TODAY, query_end=TODAY)
    assert response.headers["Cache-Control"] == "private, no-store"


@pytest.mark.parametrize("kind", ["B", "H", "G"])
def test_added_coupons_cover_issuance_use_returns_drilldown_and_holder_trajectory(kind):
    result = report(issues=[issue(kind)],
        flows=[flow(kind), flow(kind, bill="101", action="P", amount=40)],
        sales=[line(member="OTHER"), line("101", -400, member="OTHER", original_billno="100"),
               line("102", 300)])
    row = coupon(result, kind)
    assert row["issued_count"] == row["preissued_count"] == row["used_assets"] == 1
    assert row["issued_amount"] == row["redeemed_amount"] == 100
    assert row["refunded_amount"] == 40 and row["net_coupon_amount"] == 60
    assert row["linked_sales"] == 600 and row["linked_returns"] == -400
    assert row["linked_gross_profit"] == 120
    assert row["used_members"] == row["use_tickets"] == 1
    for key in ("redeemed_amount", "refunded_amount", "linked_sales", "linked_returns", "linked_gross_profit"):
        assert sum(x[key] for x in result["departments"]) == row[key]
        assert sum(x[key] for x in result["groups"]) == row[key]
    assert {x["coupon_type"] for x in result["tickets"]} == {kind}
    assert {x["billno"] for x in result["trajectory"]} == {"100", "101", "102"}
    assert all(x["used_coupon_types"] == [kind] for x in result["trajectory"])
    assert "待核查" in result["trajectory"][0]["event_type"]


def test_added_coupons_share_existing_receipt_without_double_counting():
    result = report(issues=[issue(), issue("B", "2"), issue("H", "3")],
        flows=[flow(amount=100), flow("B", "2", amount=50), flow("H", "3", amount=200)],
        sales=[line(sales=3500), line("101", -700, original_billno="100")])
    assert [row["coupon_type"] for row in result["coupons"]] == ["J", "D", "R", "E", "B", "H", "G"]
    assert coupon(result, "E")["linked_sales"] == 800
    assert coupon(result, "B")["linked_sales"] == 400
    assert coupon(result, "H")["linked_sales"] == 1600
    assert sum(row["linked_sales"] for row in result["coupons"]) == 2800
    assert sum(row["sales"] for row in result["tickets"]) == 2800
    assert sum(row["linked_returns"] for row in result["coupons"]) == -700
    assert result["distinct_used_members"] == result["distinct_use_tickets"] == 1


@pytest.mark.parametrize("kind", ["B", "H", "G"])
def test_added_coupons_keep_department_permissions_and_hide_other_holders(kind):
    result = report(scope=DEPT, issues=[issue(kind), issue(kind, "2")],
        flows=[flow(kind), flow(kind, "2", "HIDDEN", bill="200")],
        sales=[line(sales=400), line(sales=600, department="D4"),
               line("200", department="D4", member="HIDDEN"), line("201", member="HIDDEN")])
    row = coupon(result, kind)
    assert row["issued_count"] is None and row["issued_amount"] is None
    assert row["redeemed_amount"] == 40 and row["linked_sales"] == 400
    assert row["used_members"] == 1
    assert {x["department_code"] for x in result["groups"]} == {"D3"}
    assert {x["holder_member_no"] for x in result["trajectory"]} == {"M1"}
    assert {x["department"] for x in result["trajectory"]} == {"D3"}
    assert {x["billno"] for x in result["tickets"]} == {"100"}


def test_all_database_queries_include_b_h_g_without_widening_store_or_period(monkeypatch):
    calls = []
    def rows(db, sql, params):
        calls.append((sql, params.copy()))
        if sql == live.PERIOD_SQL:
            return [dict(valid_from=TODAY, valid_to=END)]
        if sql == live.ISSUES_SQL:
            return [issue("B"), issue("H", "2"), issue("G", "3")]
        if sql == live.FLOW_SQL:
            return [flow("B"), flow("H", "2", "M2", bill="101"), flow("G", "3", "M3", bill="102")]
        return [line(), line("101", member="M2"), line("102", member="M3")]
    monkeypatch.setattr(live, "limited_rows", rows)
    result = live.query_report(Mock(), ADMIN, "1", today=TODAY)
    assert all(params["coupon_types"] == ["J", "D", "R", "E", "B", "H", "G"] for _, params in calls)
    assert all(params["store_code"] == "601" and params["start_date"] == TODAY for _, params in calls)
    assert calls[1][1]["end_date"] == END
    assert calls[-1][1]["holders"] == ["M1", "M2", "M3"]
    assert coupon(result, "B")["redeemed_amount"] == coupon(result, "H")["redeemed_amount"] == coupon(result, "G")["redeemed_amount"] == 100


def test_g_and_e_share_sale_and_actual_return_without_double_counting():
    result = report(issues=[issue("E"), issue("G", "2")],
        flows=[flow("E", amount=100), flow("G", "2", amount=200)],
        sales=[line(sales=900), line("101", -300, original_billno="100")])
    assert coupon(result, "E")["linked_sales"] == 200
    assert coupon(result, "G")["linked_sales"] == 400
    assert coupon(result, "G")["linked_returns"] == -200
    assert coupon(result, "G")["net_coupon_amount"] == 200
    assert sum(row["linked_sales"] for row in result["coupons"]) == 600
    assert sum(row["sales"] for row in result["tickets"]) == 600
    assert result["holders"] == [{"holder_member_no": "M1", "used_coupon_types": ["E", "G"]}]
    assert all(row["ticket_coupon_types"] == ["E", "G"] for row in result["trajectory"])


def test_holder_cohort_keeps_members_without_today_shopping_and_current_period_flag():
    tomorrow = date(2026, 9, 19)
    result = report(today=tomorrow)
    assert result["holders"] == [{"holder_member_no": "M1", "used_coupon_types": ["E"]}]
    assert result["trajectory"] == []
    assert result["trajectory_available"] is True
    assert report(today=date(2026, 9, 28))["trajectory_available"] is False
    assert report(flows=[flow(), flow(action="U")])["holders"] == []


def test_trajectory_exposes_receipt_grain_and_original_coupon_types_for_returns():
    result = report(flows=[flow(), flow("H", "2", "M2", amount=200)],
                    sales=[line(), line("101", -400, original_billno="100")])
    own = next(row for row in result["trajectory"] if row["billno"] == "100" and row["holder_member_no"] == "M1")
    returned = next(row for row in result["trajectory"] if row["billno"] == "101" and row["holder_member_no"] == "M1")
    assert own["coupon_types"] == "E"
    assert own["ticket_coupon_types"] == returned["ticket_coupon_types"] == ["E", "H"]
    assert returned["ticket_kind"] == "退货" and returned["original_billno"] == "100"
    assert (own["group_code"], own["brand_code"], own["supplier_code"]) == ("D3G", "BR", "SP")


def test_member_cohort_and_new_receipt_fields_do_not_leak_hidden_department():
    result = report(scope=DEPT, flows=[flow(), flow("B", "2", "HIDDEN", bill="200")],
                    sales=[line(), line("200", department="D4", member="HIDDEN"),
                           line("201", member="HIDDEN"), line("300", department="D4")])
    assert result["holders"] == [{"holder_member_no": "M1", "used_coupon_types": ["E"]}]
    assert {row["billno"] for row in result["trajectory"]} == {"100"}
    assert {row["department_code"] for row in result["trajectory"]} == {"D3"}


@pytest.mark.parametrize("scope,expected_holders", [(ADMIN, ["M1"]), (DEPT, [])])
def test_holder_shopping_query_for_missing_use_merchandise_is_full_store_only(monkeypatch, scope, expected_holders):
    calls = []
    def rows(db, sql, params):
        calls.append((sql, params.copy()))
        if sql == live.PERIOD_SQL:
            return [dict(valid_from=TODAY, valid_to=END)]
        if sql == live.ISSUES_SQL:
            return [issue()]
        if sql == live.FLOW_SQL:
            return [flow()]
        return [line("200", 500)] if params["holders"] else []
    monkeypatch.setattr(live, "limited_rows", rows)
    result = live.query_report(Mock(), scope, "1", today=TODAY)
    assert calls[-1][1]["holders"] == expected_holders
    assert [row["holder_member_no"] for row in result["holders"]] == expected_holders
    assert len(result["trajectory"]) == len(expected_holders)
