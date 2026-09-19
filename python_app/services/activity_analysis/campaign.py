"""Configured coupon campaigns. Ownership comes from first issuance, not later sales."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import bindparam, text

from services.activity_analysis.campaign_lift import query_sales_lift
from services.activity_analysis.campaign_members import query_current_members
from services.activity_analysis.campaign_ownership import asset_key,load_ownership,ownership_view
from services.activity_analysis.campaign_returns import query_post_returns

VIEW_PERMISSION = "activity_analysis.campaign.view"
MANAGE_PERMISSION = "activity_analysis.campaign.manage"
ISSUE_ACTIONS = ("F", "m", "M", "Q", "I", "B", "Z", "b", "X")
MAX_ROWS = 100000


class CampaignInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    store_code: str = Field(pattern=r"^[0-9]{3}$")
    start_date: date
    end_date: date
    coupon_types: list[str] = Field(min_length=1, max_length=26)
    erp_activity_id: str = Field(default="", pattern=r"^[0-9]{0,20}$")
    notes: str = Field(default="", max_length=2000)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        if not value.strip():
            raise ValueError("活动名称不能为空")
        return value.strip()

    @field_validator("coupon_types")
    @classmethod
    def clean_types(cls, values):
        values = sorted(set(v.strip().upper() for v in values))
        if any(len(v) != 1 or not "A" <= v <= "Z" for v in values):
            raise ValueError("券种必须为 A–Z 字母")
        return values

    @model_validator(mode="after")
    def valid_period(self):
        if not 0 <= (self.end_date - self.start_date).days <= 365:
            raise ValueError("活动日期须正序，且不超过366天")
        return self


COHORT_CTE = """
WITH candidate AS MATERIALIZED (
 SELECT l.*, ROW_NUMBER() OVER (
   PARTITION BY l.tcflmkt,l.tcfljetype,l.tcflvipseq
   ORDER BY l.tcfldate,l.tcflseqno) rn
 FROM tktcardfqlog l
 WHERE l.tcflmkt=:store_code AND l.tcfljetype IN :coupon_types
   AND l.tcflzy IN :issue_actions AND l.tcflvipseq > 0
   AND l.tcflstartdate >= :start_date AND l.tcflenddate <= :end_date
   AND l.tcflenddate >= :start_date
   AND l.tcflstartdate <= l.tcflenddate AND l.tcfldate < :end_exclusive
), issued AS MATERIALIZED (
 SELECT c.* FROM candidate c WHERE c.rn=1 AND NOT EXISTS (
   SELECT 1 FROM tktcardfqlog old
   WHERE old.tcflmkt=c.tcflmkt AND old.tcfljetype=c.tcfljetype
     AND old.tcflvipseq=c.tcflvipseq AND old.tcflzy IN :issue_actions
     AND (old.tcfldate,old.tcflseqno)<(c.tcfldate,c.tcflseqno)
 )
)
"""
ISSUES_SQL = COHORT_CTE + """
SELECT tcflseqno::text issue_id,tcflvipseq::text asset_id,
 TRIM(tcflvipno) member_no,TRIM(tcfljetype) coupon_type,
 TRIM(tcflpopid) erp_period,tcflstartdate valid_from,tcflenddate valid_to,
 ABS(COALESCE(tcflmoney,0)) amount,tcfldate issue_date,
 CASE WHEN tcflzy IN ('M','N') AND tcflsource='2'
   AND TRIM(tcflsyjid)='0000' AND NULLIF(TRIM(tcflinvno),'') IS NULL
   THEN '后台充券'
   WHEN tcflsource IN ('7','8') THEN '后台充券'
   WHEN tcflsource='1' THEN '销售返券'
   WHEN tcflsource='2' THEN '前台买券' ELSE '其他发券' END source_name
FROM issued
"""
FLOWS_SQL = COHORT_CTE + """
SELECT l.tcflseqno::text flow_id,l.tcflvipseq::text asset_id,
 TRIM(l.tcflvipno) member_no,TRIM(l.tcfljetype) coupon_type,
 l.tcflzy action,ABS(COALESCE(l.tcflmoney,0)) amount,l.tcfldate flow_date,
 CASE WHEN h.match_count=1 THEN h.billno::text END billno,h.match_count
FROM issued i JOIN tktcardfqlog l ON l.tcflmkt=i.tcflmkt
 AND l.tcfljetype=i.tcfljetype AND l.tcflvipseq=i.tcflvipseq
 AND l.tcfldate >= :start_date AND l.tcfldate < :end_exclusive
 AND (l.tcfldate,l.tcflseqno)>(i.tcfldate,i.tcflseqno)
LEFT JOIN LATERAL (
 SELECT MIN(s.billno) billno,COUNT(*) match_count FROM salehead s
 WHERE s.mkt=l.tcflmkt AND s.syjh=l.tcflsyjid
 AND s.fphm=CASE WHEN TRIM(l.tcflinvno) ~ '^[0-9]+$' THEN TRIM(l.tcflinvno)::numeric END
 AND s.rqsj>=l.tcfldate::date AND s.rqsj<l.tcfldate::date+INTERVAL '1 day'
 AND COALESCE(s.djlb,'') NOT IN ('V','W','Y','Z')
) h ON l.tcflzy IN ('O','P','U','V')
"""
SALES_SQL = """
WITH heads AS MATERIALIZED (
 SELECT billno,ybillno,TRIM(hykh) member_no,rqsj FROM salehead
 WHERE mkt=:store_code AND rqsj>=:start_date AND rqsj<:end_exclusive
 AND COALESCE(djlb,'') NOT IN ('V','W','Y','Z')
)
SELECT h.billno::text billno,h.ybillno::text original_billno,
 h.member_no,h.rqsj sale_date,TRIM(s.sglppcode) brand_code,
 TRIM(s.sglsupid) supplier_code,
 SUM(COALESCE(s.sglxssr,0)) sales,SUM(COALESCE(s.sgln2,0)) gross_profit
FROM heads h JOIN salegoodslist s ON s.sglbillno=h.billno AND s.sglmarket=:store_code
GROUP BY h.billno,h.ybillno,h.member_no,h.rqsj,TRIM(s.sglppcode),TRIM(s.sglsupid)
"""
MISSING_ISSUES_SQL = COHORT_CTE + """
SELECT COUNT(*) FROM tktcardfqlog l WHERE l.tcflmkt=:store_code
 AND l.tcfljetype IN :coupon_types AND l.tcflzy IN ('O','P','U','V')
 AND l.tcfldate>=:start_date AND l.tcfldate<:end_exclusive
 AND l.tcflstartdate>=:start_date AND l.tcflenddate<=:end_date
 AND NOT EXISTS (SELECT 1 FROM issued i WHERE i.tcflvipseq=l.tcflvipseq
   AND i.tcfljetype=l.tcfljetype AND i.tcflmkt=l.tcflmkt)
"""

# Reuse the exact first-issuance cohort already read in the same repeatable-read
# transaction. Rebuilding its history anti-join for each downstream query costs
# three full cohort scans and can exceed the gateway deadline.
REUSED_COHORT_CTE = """
WITH issued AS MATERIALIZED (
 SELECT CAST(:store_code AS varchar) tcflmkt,c.*
 FROM UNNEST(CAST(:cohort_types AS text[]),CAST(:cohort_assets AS numeric[]),
             CAST(:cohort_dates AS date[]),CAST(:cohort_issues AS numeric[]))
   AS c(tcfljetype,tcflvipseq,tcfldate,tcflseqno)
)
"""


def reuse_cohort(sql, params, candidates):
    if not sql.startswith(COHORT_CTE):
        raise ValueError('仅允许复用初始发券队列查询')
    return REUSED_COHORT_CTE + sql[len(COHORT_CTE):], dict(
        params,cohort_types=[r['coupon_type'] for r in candidates],
        cohort_assets=[r['asset_id'] for r in candidates],
        cohort_dates=[r['issue_date'] for r in candidates],
        cohort_issues=[r['issue_id'] for r in candidates],
    )


def dec(value):
    return Decimal(str(value or 0))


def serializable(value):
    if isinstance(value, Decimal):
        return float(value.quantize(Decimal("0.01")))
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serializable(v) for v in value]
    return value


def parameters(config):
    return {**config, "end_exclusive": config["end_date"] + timedelta(days=1),
            "issue_actions": ISSUE_ACTIONS}


def statement(sql):
    stmt = text(sql)
    for key in ("coupon_types", "issue_actions"):
        if f":{key}" in sql:
            stmt = stmt.bindparams(bindparam(key, expanding=True))
    return stmt


def limited_rows(db, sql, params):
    rows = db.execute(statement(sql), params).mappings().fetchmany(MAX_ROWS + 1)
    if len(rows) > MAX_ROWS:
        raise ValueError("活动明细超过10万行，请缩短档期；未生成截断报告")
    return [dict(row) for row in rows]


def query_report(db, config):
    params = parameters(config)
    candidates = limited_rows(db, ISSUES_SQL, params)
    storage_ready,record=load_ownership(db,config.get('id'))
    ownership,owned=ownership_view(config,candidates,record,storage_ready)
    issues = [r for r in candidates if asset_key(r) in owned]
    flow_sql,cohort_params=reuse_cohort(FLOWS_SQL,params,candidates)
    flows = [r for r in limited_rows(db, flow_sql, cohort_params) if asset_key(r) in owned]
    sales = limited_rows(db, SALES_SQL, params)
    member_ids = sorted({r["member_no"] for r in issues + flows if r["member_no"]})
    members,member_source=query_current_members(db,config['store_code'],member_ids)
    report = build_report(config, issues, flows, sales, members)
    report['ownership']=ownership
    report['assets']=[dict(r,in_report=asset_key(r) in owned) for r in candidates]
    report['coupon_flows']=flows
    report['member_source']=member_source
    report['quality']['member_profile_unresolved']=len(member_ids)-member_source['matched']
    report['quality']['ownership_unconfirmed']=int(ownership['status']!='confirmed')
    report['quality']['ownership_added_assets']=ownership['unconfirmed_added']
    report['quality']['ownership_missing_assets']=ownership['confirmed_missing']
    report['quality']['ownership_conflicting_erp_period']=ownership['conflicting_erp_period']
    report['post_activity_returns']=query_post_returns(db,config,report['tickets'],report['summary']['net_linked_sales'])
    missing_sql,cohort_params=reuse_cohort(MISSING_ISSUES_SQL,params,candidates)
    report["quality"]["missing_initial_issue_flows"] = db.execute(statement(missing_sql), cohort_params).scalar_one()
    report["sales_lift"] = query_sales_lift(db, config)
    return serializable(report)


def build_report(config, issues, flows, sales, member_dims=()):
    """Amount allocation is exclusive per ticket; returns use original bill, not P logs."""
    def blank():
        return dict(issued_count=0, issued_amount=Decimal(0), preissued_count=0,
                    redeemed_amount=Decimal(0), returned_coupon_amount=Decimal(0),
                    gross_linked_sales=Decimal(0), linked_return_sales=Decimal(0),
                    net_linked_sales=Decimal(0), net_linked_gross_profit=Decimal(0),
                    own_store_net_sales=Decimal(0), mismatch_coupon_amount=Decimal(0))
    coupons = {c: blank() for c in config["coupon_types"]}
    holders = defaultdict(blank)
    totals = blank()
    sources = defaultdict(set)
    used_bills, return_bills, issued_members, used_members = (defaultdict(set) for _ in range(4))
    quality = dict(unmatched_use_flows=0, unmatched_return_flows=0,
                   unsupported_action_flows=0, missing_sales_tickets=0,
                   return_without_original=0, unassigned_return_coupon_flows=0,
                   returns_linked_by_coupon_log=0)
    for row in issues:
        c, m = row["coupon_type"], row["member_no"] or "未识别持券人"
        sources[c].add(row.get("source_name", "未识别"))
        issued_members[c].add(m)
        issued_members["ALL"].add(m)
        for target in (coupons[c], holders[m], totals):
            target["issued_count"] += 1
            target["issued_amount"] += dec(row["amount"])
            if str(row["issue_date"])[:10] < str(config["start_date"])[:10]:
                target["preissued_count"] += 1
    # Per ticket/type/holder net redemption weight; reversal U subtracts from O.
    weights = defaultdict(lambda: defaultdict(Decimal))
    return_weights = defaultdict(lambda: defaultdict(Decimal))
    return_flow_bills = set()
    for row in flows:
        c, m, action = row["coupon_type"], row["member_no"] or "未识别持券人", row["action"]
        if action not in ("O", "P", "U", "V"):
            quality["unsupported_action_flows"] += 1
            continue
        amount = dec(row["amount"]) * (-1 if action in ("U", "V") else 1)
        field = "redeemed_amount" if action in ("O", "U") else "returned_coupon_amount"
        for target in (coupons[c], holders[m], totals):
            target[field] += amount
        if action == "O":
            used_members[c].add(m)
            used_members["ALL"].add(m)
        if not row.get("billno"):
            quality["unmatched_use_flows" if action in ("O", "U") else "unmatched_return_flows"] += 1
        elif action in ("O", "U"):
            weights[str(row["billno"])][(c, m)] += amount
        else:
            return_flow_bills.add(str(row["billno"]))
            return_weights[str(row["billno"])][(c, m)] += amount
    tickets = {}
    for row in sales:
        bill = str(row["billno"])
        ticket = tickets.setdefault(bill, {"billno": bill, "original_billno": str(row.get("original_billno") or ""),
                                          "member_no": row.get("member_no") or "", "sale_date": row.get("sale_date"),
                                          "sales": Decimal(0), "gross_profit": Decimal(0), "brands": []})
        ticket["sales"] += dec(row["sales"])
        ticket["gross_profit"] += dec(row["gross_profit"])
        ticket["brands"].append(row)
    for ticket in tickets.values():
        if ticket["member_no"] in holders:
            holders[ticket["member_no"]]["own_store_net_sales"] += ticket["sales"]
    weights = {b: {key: v for key, v in group.items() if v > 0} for b, group in weights.items()}
    details, brands = [], defaultdict(lambda: dict(net_linked_sales=Decimal(0), net_linked_gross_profit=Decimal(0)))
    brand_details=[]
    assigned_return_bills = set()
    for bill, ticket in tickets.items():
        is_return = ticket["sales"] < 0
        anchor = ticket["original_billno"] if is_return else bill
        group = weights.get(anchor, {})
        basis = "原销售小票" if is_return else "核销日志"
        # A known original outside this campaign must NEVER fall back to date/type.
        # With no original number, same-cohort P/V logs on the exact return ticket
        # are explicit evidence. Keep this alternate chain visible in quality/detail.
        if is_return and not group and ticket["original_billno"] in ("", "0"):
            group = {key: v for key, v in return_weights.get(bill, {}).items() if v > 0}
            if group:
                basis = "退券日志（原小票缺失）"
                quality["returns_linked_by_coupon_log"] += 1
        if not group:
            if bill in return_flow_bills:
                quality["return_without_original"] += 1
            continue
        denominator = sum(group.values())
        if is_return:
            assigned_return_bills.add(bill)
        for (c, m), amount in group.items():
            share = amount / denominator
            linked, gp = ticket["sales"] * share, ticket["gross_profit"] * share
            match = "未登记会员" if not ticket["member_no"] else ("一致" if ticket["member_no"] == m else "不一致")
            for target in (coupons[c], holders[m], totals):
                target["net_linked_sales"] += linked
                target["net_linked_gross_profit"] += gp
                target["linked_return_sales" if is_return else "gross_linked_sales"] += linked
                if not is_return and match == "不一致":
                    target["mismatch_coupon_amount"] += amount
            for key in (c, "holder:"+m, "ALL"):
                (return_bills if is_return else used_bills)[key].add(bill)
            details.append(dict(billno=bill, original_billno=ticket["original_billno"], sale_date=ticket["sale_date"],
                                coupon_type=c, member_no=m, checkout_member_no=ticket["member_no"], member_match=match,
                                association_basis=basis,
                                ticket_kind="退货" if is_return else "销售", allocation=share,
                                coupon_amount=Decimal(0) if is_return else amount, linked_sales=linked, linked_gross_profit=gp))
            for line in ticket["brands"]:
                b = brands[(c, line.get("brand_code") or "未识别")]
                b["net_linked_sales"] += dec(line["sales"]) * share
                b["net_linked_gross_profit"] += dec(line["gross_profit"]) * share
                brand_details.append(dict(billno=bill,original_billno=ticket['original_billno'],
                    coupon_type=c,member_no=m,brand_code=line.get('brand_code') or '未识别',
                    supplier_code=line.get('supplier_code') or '未识别',ticket_kind='退货' if is_return else '销售',
                    allocation=share,linked_sales=dec(line['sales'])*share,
                    linked_gross_profit=dec(line['gross_profit'])*share))
    quality["missing_sales_tickets"] = len(set(weights) - set(tickets))
    quality["unassigned_return_coupon_flows"] = len(return_flow_bills - assigned_return_bills)
    dims = {r["member_no"]: r for r in member_dims}
    def finish(row, key):
        row["net_coupon_amount"] = row["redeemed_amount"] - row["returned_coupon_amount"]
        row["use_tickets"], row["return_tickets"] = len(used_bills[key]), len(return_bills[key])
        row["average_ticket_sales"] = row["net_linked_sales"] / row["use_tickets"] if row["use_tickets"] else None
        return row
    member_rows = []
    for m, row in holders.items():
        dim = dims.get(m, {})
        admission = str(dim.get("admission_date") or "")[:10]
        member_rows.append(dict(member_no=m, member_level=dim.get("member_level") or "未识别等级",
                               member_level_code=dim.get('member_level_code'),
                               member_match_status=dim.get('member_match_status') or '未匹配',
                               activity_member_level=dim.get('activity_member_level') or '未接入历史等级',
                               member_source_time=dim.get('source_update_time'),member_loaded_at=dim.get('source_loaded_at'),
                               is_new_member=(str(config["start_date"]) <= admission <= str(config["end_date"])) if admission else None,
                               **finish(row, "holder:"+m)))
    level_rows = {}
    for row in member_rows:
        level = row["member_level"]
        level_row = level_rows.setdefault(level, dict(member_level=level, members=0, used_members=0, net_linked_sales=Decimal(0), own_store_net_sales=Decimal(0)))
        level_row["members"] += 1
        level_row["used_members"] += row["redeemed_amount"] > 0
        level_row["net_linked_sales"] += row["net_linked_sales"]
        level_row["own_store_net_sales"] += row["own_store_net_sales"]
    coupon_rows = []
    for c, row in coupons.items():
        coupon_rows.append(dict(coupon_type=c, source_name="、".join(sorted(sources[c])),
                                issued_members=len(issued_members[c]), used_members=len(used_members[c]), **finish(row, c)))
    totals.update(issued_members=len(issued_members["ALL"]), used_members=len(used_members["ALL"]))
    totals["own_store_net_sales"] = sum(r["own_store_net_sales"] for r in member_rows)
    return dict(scope=config, summary=finish(totals, "ALL"), coupons=coupon_rows,
                members=sorted(member_rows, key=lambda r: r["net_linked_sales"], reverse=True),
                member_levels=list(level_rows.values()), tickets=details,
                brand_details=brand_details,
                brands=[dict(coupon_type=k[0], brand_code=k[1], **v) for k,v in brands.items()], quality=quality,
                definitions=[
                    "按门店、已设置券种及最初发券有效期归属；有效期须包含于活动档期，提前发券计入。",
                    "销售、退货以salegoodslist销售收入为准；优先按salehead.ybillno追溯原销售，不依赖是否退券。",
                    "退货缺原小票时，仅以该退货小票已匹配的本档退券日志补充关联，单独标记；原小票属于其他档期则不补入。",
                    "主报表只纳入活动期间销售及退货；活动后退货单独追溯原核销小票展示，不改写主报表，也不自动归入下一档。",
                    "当前会员等级来自四店CRM会员ODS，不是活动时等级；未匹配、重复会员号或字典异常单列，不取最高等级或回退旧维表。",
                    "档期内注册只依据共享主档注册日期，不等于本店首购、集团新客或活动带来的新增会员；注册日期缺失显示未知。",
                    "ERP编号用于档期规则关联；券资产归属另行人工确认。未确认或来源变化的报告是核查预览，不作为正式结算依据。",
                    "品牌/供应商明细为整票商品聚合分摊，并非券实际适用商品或供应商应承担费用。",
                    "同一小票多券、多持券人，按本活动净核销券金额比例分摊；活动总额按小票去重。",
                    "持券关联销售不是会员本人销售，也不等于活动带来的增量销售。",
                    "销售增长试算按冻结的ERP参与范围计算；以前4周同星期为基准，再用同部门非参与柜组的期间变化校准。",
                    "销售增长试算是参考估算，不作为结算依据；往期活动未建档时，历史基准可能包含其他促销。",
                    "平均单票=净连带销售/核销销售小票数；不以核销票数减退货票数作分母。",
                    "会员不一致仅为疑似代付线索；未登记小票会员单列，不直接判违规。",
                    "金额按源精度汇总后显示到分；分摊明细逐行四舍五入，合计可能有少量尾差。",
                    "缺失或歧义关联及非标准操作列入数据质量，未自动推测；规则快照不作违规判定。",
                ])
