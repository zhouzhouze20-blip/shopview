from datetime import date
from decimal import Decimal
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_app"))
from services.activity_analysis.campaign import (
    CampaignInput, build_report, serializable, COHORT_CTE, FLOWS_SQL, SALES_SQL, parameters,
)
from services.activity_analysis.campaign_erp import rule_summary_sql, rule_parameters, fetch_rule_summary, RuleSourceError
from services.activity_analysis.campaign_lift import LIFT_SQL, build_lift_estimate, query_sales_lift

CONFIG = dict(name="七夕", store_code="601", start_date=date(2026,8,14), end_date=date(2026,8,19), coupon_types=["B","E","H","M"], erp_activity_id="2205")


def issue(member="owner", c="H", amount=200, issued="2026-08-10"):
    return dict(member_no=member, coupon_type=c, amount=amount, issue_date=issued, source_name="后台充券")


def flow(bill="1", member="owner", c="H", action="O", amount=200):
    return dict(billno=bill,member_no=member,coupon_type=c,action=action,amount=amount)


def sale(bill="1", amount=1000, original="", member="buyer", gp=100):
    return dict(billno=bill, original_billno=original,member_no=member,sales=amount,gross_profit=gp,brand_code="brand",sale_date="2026-08-15")


def test_accepts_preissue_and_normalizes_config():
    cfg=CampaignInput(**{**CONFIG,"coupon_types":["b"," E ","b"]})
    assert cfg.coupon_types==["B","E"]
    result=build_report(CONFIG,[issue()],[],[])
    assert result["summary"]["preissued_count"]==1
    assert ">= :start_date" in COHORT_CTE
    assert "l.tcfldate >= :start_date" not in COHORT_CTE
    assert "old.tcflvipseq=c.tcflvipseq" in COHORT_CTE


@pytest.mark.parametrize("updates", [{"start_date":date(2026,8,20)}, {"coupon_types":["B');DROP"]}, {"name":"   "}, {"store_code":"601 OR 1=1"}, {"erp_activity_id":"'2205'"}])
def test_rejects_invalid_config(updates):
    with pytest.raises(ValidationError):
        CampaignInput(**{**CONFIG,**updates})


def test_return_without_coupon_return_is_deducted():
    result=build_report(CONFIG,[issue()],[flow()], [sale(),sale("2",-400,"1",gp=-40)])
    assert result["summary"]["net_linked_sales"]==600
    assert result["summary"]["returned_coupon_amount"]==0
    assert result["summary"]["return_tickets"]==1
    assert result["summary"]["average_ticket_sales"]==600


def test_coupon_return_does_not_subtract_sales_twice():
    result=build_report(CONFIG,[issue()],[flow(),flow("2",action="P",amount=200)], [sale(),sale("2",-1000,"1",gp=-100)])
    assert result["summary"]["net_linked_sales"]==0
    assert result["summary"]["net_coupon_amount"]==0
    assert result["quality"]["return_without_original"]==0


def test_missing_original_uses_explicit_return_coupon_evidence_but_not_other_campaign():
    result=build_report(CONFIG,[issue()],[flow(),flow("2",action="P",amount=200)],
                        [sale(),sale("2",-400,"",gp=-40)])
    assert result["summary"]["net_linked_sales"]==600
    assert result["quality"]["returns_linked_by_coupon_log"]==1
    assert result["tickets"][-1]["association_basis"]=="退券日志（原小票缺失）"
    other=build_report(CONFIG,[issue()],[flow(),flow("2",action="P",amount=200)],
                       [sale(),sale("2",-400,"other-campaign",gp=-40)])
    assert other["summary"]["net_linked_sales"]==1000
    assert other["quality"]["return_without_original"]==1


def test_multi_holder_multi_coupon_ticket_and_return_are_exclusive():
    result=build_report(CONFIG,[issue("a","B",50),issue("b","E",100)],
                        [flow(member="a",c="B",amount=50),flow(member="b",c="E",amount=100)],
                        [sale(amount=900),sale("2",-300,"1",gp=-30)])
    assert result["summary"]["net_linked_sales"]==600
    assert sum(r["net_linked_sales"] for r in result["members"])==600
    assert sum(r["net_linked_sales"] for r in result["coupons"])==600
    assert result["summary"]["use_tickets"]==1
    assert result["summary"]["return_tickets"]==1


def test_own_store_sales_are_not_holder_linked_sales_and_no_member_is_unknown():
    result=build_report(CONFIG,[issue()],[flow()], [sale(member=""),sale("3",amount=200,member="owner")])
    owner=result["members"][0]
    assert owner["net_linked_sales"]==1000
    assert owner["own_store_net_sales"]==200
    assert owner["mismatch_coupon_amount"]==0
    assert result["tickets"][0]["member_match"]=="未登记会员"


def test_missing_ticket_and_unsupported_operation_raise_quality_flags():
    result=build_report(CONFIG,[issue()],[flow(None),flow(action="C")],[])
    assert result["quality"]["unmatched_use_flows"]==1
    assert result["quality"]["unsupported_action_flows"]==1
    assert result["summary"]["net_linked_sales"]==0
    assert result["summary"]["average_ticket_sales"] is None


def test_returns_of_previous_campaign_are_not_attributed_to_current():
    result=build_report(CONFIG,[issue()],[flow()], [sale(),sale("2",-400,"old-campaign")])
    assert result["summary"]["net_linked_sales"]==1000
    assert "l.tcfldate < :end_exclusive" in FLOWS_SQL
    assert "rqsj<:end_exclusive" in SALES_SQL
    assert parameters(CONFIG)["end_exclusive"]==date(2026,8,20)


def test_reversal_does_not_create_positive_allocation():
    result=build_report(CONFIG,[issue()],[flow(),flow(action="U")],[sale()])
    assert result["summary"]["net_coupon_amount"]==0
    assert result["summary"]["net_linked_sales"]==0


def test_four_sales_three_returns_example():
    issues=[issue(amount=650)]
    uses=[flow(str(i),amount=a) for i,a in enumerate([200,50,200,200],1)]
    returns=[flow(str(i+4),action="P",amount=a) for i,a in enumerate([200,50,200],1)]
    sales=[sale(str(i),a) for i,a in enumerate([1841,901,1800,29800],1)]
    sales += [sale(str(i+4),-a,str(i)) for i,a in enumerate([1841,901,1800],1)]
    result=build_report(CONFIG,issues,uses+returns,sales)
    s=result["summary"]
    assert (s["net_linked_sales"],s["use_tickets"],s["return_tickets"],s["average_ticket_sales"])==(29800,4,3,7450)


def test_rule_query_is_store_scoped_approved_and_not_hardcoded_to_b_threshold():
    sql=rule_summary_sql(CONFIG)
    assert "h.tbfhmkt=:store_code" in sql and "h.tbfhflag='Y'" in sql
    assert "ods.gpp_tktbgoodsfqhead" in sql and "h.batch_id=r.batch_id" in sql
    assert "r.tgyrtjje" in sql and "600" not in sql
    assert rule_parameters(CONFIG)["store_code"] == "601"
    with pytest.raises(RuleSourceError):
        rule_summary_sql({**CONFIG,"erp_activity_id":"1' OR 1=1"})


def test_missing_ods_schema_is_not_zero_rules():
    db=SimpleNamespace(execute=lambda sql:SimpleNamespace(scalar=lambda:False))
    with pytest.raises(RuleSourceError,match="尚未安装"):
        fetch_rule_summary(db,CONFIG)


def test_store_and_manage_permissions_checked_before_report(monkeypatch):
    from routers import coupon_campaigns as router
    calls=[]
    monkeypatch.setattr(router,"require_permission",lambda db,u,p:calls.append(p))
    monkeypatch.setattr(router,"load_business_scope",lambda db,u:SimpleNamespace(all_access=False,allow={"store":{"601"}},deny={}))
    monkeypatch.setattr(router,"_require_selected_activity_store",lambda db,s,c:calls.append(c))
    router.access(None,None,"601",manage=True)
    assert calls==["activity_analysis.campaign.view","activity_analysis.campaign.manage","601"]
    monkeypatch.setattr(router,"load_business_scope",lambda db,u:SimpleNamespace(all_access=False,allow={"group":{"x"}},deny={}))
    with pytest.raises(HTTPException) as exc:
        router.access(None,None,"601")
    assert exc.value.status_code==403


def test_missing_migration_is_explicit_service_unavailable():
    from routers.coupon_campaigns import ensure_schema
    db=SimpleNamespace(execute=lambda sql:SimpleNamespace(scalar=lambda:None))
    with pytest.raises(HTTPException) as exc:
        ensure_schema(db)
    assert exc.value.status_code==503


def test_initial_zero_balance_is_not_replaced_by_usage_source():
    result=build_report(CONFIG,[issue()],[flow()], [sale()])
    assert next(r for r in result["coupons"] if r["coupon_type"]=="H")["source_name"]=="后台充券"
    assert serializable({"v":Decimal("1.235")})=={"v":1.24}


def test_edit_cannot_change_activity_ownership(monkeypatch):
    from routers import coupon_campaigns as router
    monkeypatch.setattr(router,"load_campaign",lambda *a,**k:CONFIG)
    changed=CampaignInput(**{**CONFIG,"store_code":"603"})
    with pytest.raises(HTTPException) as exc:
        router.edit_campaign(1,changed,None,None)
    assert exc.value.status_code==409


def test_create_overlap_rejected_under_store_lock(monkeypatch):
    from routers import coupon_campaigns as router
    monkeypatch.setattr(router,"access",lambda *a,**k:None)
    monkeypatch.setattr(router,"ensure_schema",lambda *a:None)
    statements=[]
    class DB:
        def execute(self,sql,params):
            statements.append(str(sql))
            return SimpleNamespace(mappings=lambda:SimpleNamespace(first=lambda:{"id":1}))
    with pytest.raises(HTTPException) as exc:
        router.create_campaign(CampaignInput(**CONFIG),DB(),SimpleNamespace(user_id=1))
    assert exc.value.status_code==409
    assert "pg_advisory_xact_lock" in statements[0]
    assert "coupon_types &&" in statements[1]
    assert not any("INSERT" in s for s in statements)


def rule_db(batch, rows):
    statements=[]
    class DB:
        def execute(self,sql,params=None):
            statements.append((str(sql),dict(params or {})))
            if len(statements)==1:
                return SimpleNamespace(scalar=lambda:True)
            return SimpleNamespace(mappings=lambda:SimpleNamespace(first=lambda:batch,all=lambda:rows))
    return DB(),statements


def test_missing_or_loading_batch_cannot_be_read_as_zero_rules():
    db,statements=rule_db(None,[])
    with pytest.raises(RuleSourceError,match="尚未完成"):
        fetch_rule_summary(db,CONFIG)
    assert "b.status='published'" in statements[1][0]
    assert "b.store_code=c.store_code" in statements[1][0]


@pytest.mark.parametrize("rows",[[],[{"coupon_type":"B","accept_amount":Decimal("50")} ]])
def test_rule_read_is_pinned_to_published_batch_even_when_another_load_starts(rows):
    from datetime import datetime, timezone
    now=datetime.now(timezone.utc)
    db,statements=rule_db({"batch_id":"verified-old", "source_started_at":now,"published_at":now}, rows)
    result=fetch_rule_summary(db,CONFIG)
    assert result["rows"]==rows and result["ods_batch_id"]=="verified-old"
    assert statements[2][1]["batch_id"]=="verified-old"
    assert statements[2][1]["coupon_types"]==["B","E","H","M"]
    assert statements[2][1]["end_exclusive"]==date(2026,8,20)


def test_rule_refresh_preserves_snapshot_on_missing_ods(monkeypatch):
    from routers import coupon_campaigns as router
    monkeypatch.setattr(router,"load_campaign",lambda *a,**k:CONFIG)
    def fail(*args):raise RuleSourceError("尚未完成同步")
    monkeypatch.setattr(router,"fetch_rule_summary",fail)
    with pytest.raises(HTTPException) as exc:
        router.refresh_rules(1,None,None)
    assert exc.value.status_code==503


def test_sales_lift_uses_frozen_scope_same_weekdays_and_period_control_factor():
    row = {
        "treatment_actual": Decimal("120"), "treatment_baseline": Decimal("100"),
        "control_actual": Decimal("210"), "control_baseline": Decimal("200"),
        "treatment_group_count": 12, "mapped_treatment_group_count": 12,
        "department_count": 3, "control_group_count": 20,
    }
    result = build_lift_estimate(
        row, day_count=6, batch_id="frozen-batch",
        start_date=date(2026, 8, 14), end_date=date(2026, 8, 19),
    )
    assert result["status"] == "estimated"
    assert result["expected_sales"] == Decimal("105")
    assert result["estimated_increment"] == Decimal("15")
    assert result["estimated_growth_rate"] == Decimal("14.28571428571428571428571429")
    assert result["rule_batch_id"] == "frozen-batch"
    assert result["activity_start_date"] == "2026-08-14"
    assert result["activity_end_date"] == "2026-08-19"
    assert result["baseline_periods"] == [
        {"week_no": 1, "start_date": "2026-08-07", "end_date": "2026-08-12"},
        {"week_no": 2, "start_date": "2026-07-31", "end_date": "2026-08-05"},
        {"week_no": 3, "start_date": "2026-07-24", "end_date": "2026-07-29"},
        {"week_no": 4, "start_date": "2026-07-17", "end_date": "2026-07-22"},
    ]
    assert "comparison_dates" in LIFT_SQL
    assert "activity_date::date-(week_no*7)" in LIFT_SQL
    assert "r.batch_id=:batch_id" in LIFT_SQL
    assert "tgyrmode='1'" in LIFT_SQL and "tgyrmode='2'" in LIFT_SQL


def test_sales_lift_is_unavailable_without_frozen_rule_snapshot():
    result = query_sales_lift(None, CONFIG)
    assert result["status"] == "unavailable"
    assert "冻结ERP" in result["reason"]
    assert result["activity_start_date"] == "2026-08-14"


def test_sales_lift_refuses_zero_control_baseline():
    result = build_lift_estimate({
        "treatment_actual": 120, "treatment_baseline": 100,
        "control_actual": 0, "control_baseline": 0,
        "treatment_group_count": 1, "mapped_treatment_group_count": 1,
    })
    assert result["status"] == "unavailable"
    assert "对照" in result["reason"]


def test_ods_tasks_are_complete_disabled_precision_preserving_snapshots():
    from sync_campaign_rule_ods import task_body, extraction_sql
    batch="11111111-1111-1111-1111-111111111111"
    for kind in ("head","rule"):
        task=task_body(kind,"601","2205",batch,7,4)
        assert task["enabled"] is False and task["schedule"]["scheduleEnabled"] is False
        assert task["maxRows"]==0
        assert task["insertMode"]=="insert"
        assert task["keyColumns"].startswith("batch_id,")
    sql=extraction_sql("rule","601","2205",batch)
    assert "ORDER BY r.TGYRSEQNO" in sql and "h.TBFHMKT='601'" in sql
    assert "TO_CHAR(r.TGYRSEQNO,'TM9'" in sql
    assert "TGYRQTYPE IN" not in sql  # Full scope; application filters configured types.
    assert "ORA_HASH" in sql
    with pytest.raises(ValueError):extraction_sql("rule","601'","2205",batch)


@pytest.mark.parametrize("bad_field,bad_value",[("field_mapping",{}),("enabled",1),("max_rows",10),("insert_mode","update"),("running_count",1)])
def test_publisher_refuses_changed_mapping_partial_or_running_tasks(bad_field,bad_value):
    from sync_campaign_rule_ods import publish,task_body
    batch="11111111-1111-1111-1111-111111111111"
    config={"batch_id":batch,"store_code":"601","erp_activity_id":"2205","status":"loading","head_task_id":46,"rule_task_id":47}
    body=task_body("head","601","2205",batch,7,4)
    task={"id":46,"source_id":7,"target_source_id":4,"table_name":body["tableName"],"enabled":0,"schedule_enabled":0,"running_count":0,
          "sql_text":body["sqlText"],"field_mapping":body["fieldMapping"],"key_columns":body["keyColumns"],"insert_mode":"insert","max_rows":0}
    task[bad_field]=bad_value
    executed=[]
    def execute(sql,params):
        executed.append(str(sql))
        return SimpleNamespace(mappings=lambda:SimpleNamespace(one=lambda:config))
    conn=SimpleNamespace(execute=execute)
    client=SimpleNamespace(execute=lambda *a:[task])
    with pytest.raises(RuntimeError,match="scope/state"):
        publish(conn,client,lambda x:x,SimpleNamespace(batch=batch,source_id=7,target_id=4))
    assert not any(sql.lstrip().startswith("UPDATE") for sql in executed)
