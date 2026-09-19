"""Read-only JDREBHG monitor. No campaign tables, confirmation or writes required."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from services.activity_analysis.campaign import ISSUES_SQL, limited_rows, parameters, serializable

STORE = "601"
TYPES = ("J", "D", "R", "E", "B", "H", "G")
TRACKING_START = date(2026, 9, 18)
DIMENSIONS = {
    "department": ("department_code", "department_name"),
    "group": ("group_code",), "brand": ("brand_code", "brand_name"),
    "supplier": ("supplier_code",), "category": ("category_code", "category_name"),
    "floor": ("floor_code",),
}

PERIOD_SQL = """
SELECT DISTINCT tcflstartdate valid_from,tcflenddate valid_to
FROM tktcardfqlog WHERE tcflmkt=:store_code AND tcfljetype IN :coupon_types
AND tcflstartdate=:start_date AND tcflenddate>=:start_date
AND tcflenddate<:start_date + INTERVAL '366 days' AND tcfldate<:today_end
ORDER BY valid_to
"""

FLOW_SQL = """
SELECT l.tcflseqno::text flow_id,l.tcflvipseq::text asset_id,
 TRIM(l.tcflvipno) member_no,TRIM(l.tcfljetype) coupon_type,
 l.tcflzy action,ABS(COALESCE(l.tcflmoney,0)) amount,l.tcfldate flow_date,
 CASE WHEN h.match_count=1 THEN h.billno::text END billno
FROM tktcardfqlog l
LEFT JOIN LATERAL (
 SELECT MIN(s.billno) billno,COUNT(*) match_count FROM salehead s
 WHERE s.mkt=l.tcflmkt AND s.syjh=l.tcflsyjid
 AND s.fphm=CASE WHEN TRIM(l.tcflinvno) ~ '^[0-9]+$' THEN TRIM(l.tcflinvno)::numeric END
 AND s.rqsj>=l.tcfldate AND s.rqsj<l.tcfldate+INTERVAL '1 day'
 AND COALESCE(s.djlb,'') NOT IN ('V','W','Y','Z')
) h ON TRUE
WHERE l.tcflmkt=:store_code AND l.tcfljetype IN :coupon_types
 AND l.tcflzy IN ('O','P','U','V')
 AND l.tcflstartdate>=:start_date AND l.tcflenddate<=:end_date
 AND l.tcflstartdate<=l.tcflenddate AND l.tcflenddate>=:start_date
 AND l.tcfldate>=:start_date AND l.tcfldate<:data_end
"""

# Restrict the large merchandise join to coupon-linked receipts, their actual
# returns, and visible holders' shopping in the selected period or today.
SALES_SQL = """
WITH heads AS MATERIALIZED (
 SELECT billno,ybillno,rqsj,TRIM(hykh) checkout_member_no FROM salehead
 WHERE mkt=:store_code AND rqsj>=:start_date AND rqsj<:data_end
 AND COALESCE(djlb,'') NOT IN ('V','W','Y','Z')
 AND (billno=ANY(CAST(:bills AS numeric[])) OR ybillno=ANY(CAST(:bills AS numeric[]))
   OR (((rqsj>=:member_start AND rqsj<:member_end) OR rqsj>=:today)
       AND TRIM(hykh)=ANY(CAST(:holders AS text[]))))
), lines AS MATERIALIZED (
 SELECT h.billno::text billno,h.ybillno::text original_billno,h.rqsj sale_time,h.checkout_member_no,
 TRIM(s.sglmfid) group_code,TRIM(s.sglppcode) brand_code,TRIM(s.sglsupid) supplier_code,
 SUM(COALESCE(s.sglxssr,0)) sales,SUM(COALESCE(s.sgln2,0)) gross_profit,
 SUM(ABS(COALESCE(s.sglxssr,0))) allocation_base
 FROM heads h JOIN salegoodslist s ON s.sglbillno=h.billno AND s.sglmarket=:store_code
 GROUP BY h.billno,h.ybillno,h.rqsj,h.checkout_member_no,
 TRIM(s.sglmfid),TRIM(s.sglppcode),TRIM(s.sglsupid)
)
SELECT l.*,g.group_name,g.department_code,d.department_name,g.floor_code,
 g.category_code,c.category_name,b.brand_name
FROM lines l
LEFT JOIN LATERAL (
 SELECT MIN(TRIM(mfcname)) group_name,MIN(TRIM(mfpcode)) department_code,
 MIN(TRIM(mflc)) floor_code,MIN(TRIM(mfchr1)) category_code
 FROM manaframe WHERE TRIM(mfcode)=l.group_code HAVING COUNT(*)=1
) g ON TRUE
LEFT JOIN LATERAL (
 SELECT MIN(TRIM(mfcname)) department_name FROM manaframe
 WHERE TRIM(mfcode)=g.department_code HAVING COUNT(*)=1
) d ON TRUE
LEFT JOIN LATERAL (
 SELECT MIN(TRIM(category_name)) category_name FROM area_category
 WHERE TRIM(category_code)=g.category_code HAVING COUNT(*)=1
) c ON TRUE
LEFT JOIN LATERAL (
 SELECT MIN(TRIM(cbcname)) brand_name FROM codebrand
 WHERE TRIM(cbid)=l.brand_code HAVING COUNT(*)=1
) b ON TRUE
ORDER BY sale_time,billno,group_code,brand_code
"""


def dec(value):
    return Decimal(str(value or 0))


def norm(value):
    return str(value or "").strip().upper()


def check_scope(scope, store_id):
    """Fail closed on unknown policies and explicit store/global denies."""
    supported = set(DIMENSIONS) | {"store", "__all__"}
    if any(values for policy in (scope.allow, scope.deny) for dim, values in policy.items() if dim not in supported):
        raise PermissionError("当前数据权限含未支持的维度，暂不能查看卡券实时跟进")
    aliases = {STORE, norm(store_id)}
    if "__all__" in scope.deny or aliases & {norm(v) for v in scope.deny.get("store", ())}:
        raise PermissionError("无购物中心数据权限")
    store_allowed = bool(aliases & {norm(v) for v in scope.allow.get("store", ())})
    if not scope.all_access and not store_allowed and not any(scope.allow.get(d) for d in DIMENSIONS):
        raise PermissionError("无购物中心数据权限")
    return (scope.all_access or store_allowed) and not any(scope.deny.get(d) for d in DIMENSIONS)


def visible_line(scope, store_id, row):
    check_scope(scope, store_id)
    values = {d: {norm(row.get(k)) for k in keys} - {""} for d, keys in DIMENSIONS.items()}
    values["store"] = {STORE, norm(store_id)}
    for dim, denied in scope.deny.items():
        # Unknown dimension mappings cannot be used to evade a deny by name.
        if denied and (not values.get(dim) or (dim in {"department", "brand", "category"}
                      and any(not norm(row.get(k)) for k in DIMENSIONS[dim]))
                       or values[dim] & {norm(v) for v in denied}):
            return False
    return scope.all_access or any(values.get(d, set()) & {norm(v) for v in allowed}
                                   for d, allowed in scope.allow.items())


def flow_weights(flows, actions):
    result = defaultdict(lambda: defaultdict(Decimal))
    for f in flows:
        if f.get("billno") and f["action"] in actions:
            result[str(f["billno"])][(f["coupon_type"], f.get("member_no") or "")] += dec(f["amount"]) * actions[f["action"]]
    return {b: {key: val for key, val in weights.items() if val > 0} for b, weights in result.items()}


def split_money(amount, weights):
    """Allocate cents once per merchandise group, preserving the signed total."""
    keys = sorted(weights)
    denominator = sum(weights.values(), Decimal(0))
    if not denominator:
        return {}
    total = dec(amount).quantize(Decimal("0.01"))
    allocated = {key: (total * weights[key] / denominator).quantize(Decimal("0.01")) for key in keys[:-1]}
    allocated[keys[-1]] = total - sum(allocated.values(), Decimal(0))
    return allocated


def query_window(today, valid_to, query_start=None, query_end=None):
    start = query_start or TRACKING_START
    end = query_end or min(today, valid_to)
    if start > end:
        raise ValueError("查询开始日期不能晚于结束日期")
    if start < TRACKING_START or end > valid_to:
        raise ValueError("查询日期须在本档券有效期内")
    if end > today:
        raise ValueError("不能查询未来日期，请在对应日期到来后查询")
    return start, end


def within_dates(value, start, end):
    return start.isoformat() <= str(value)[:10] <= end.isoformat()


def build_report(issues, flows, sales, scope, store_id, today, end_date, query_start=None, query_end=None):
    full = check_scope(scope, store_id)
    query_start, query_end = query_window(today, end_date, query_start, query_end)
    # Earlier original uses are attribution context only, not current-window turnover.
    context_flows = [f for f in flows if within_dates(f["flow_date"], TRACKING_START, query_end)]
    selected_flows = [f for f in context_flows if within_dates(f["flow_date"], query_start, query_end)]
    use = flow_weights(context_flows, {"O": 1, "U": -1})
    refunds = flow_weights(context_flows, {"P": 1, "V": -1})
    selected_use = flow_weights(selected_flows, {"O": 1, "U": -1})
    today_use = flow_weights(flows, {"O": 1, "U": -1})
    today_refunds = flow_weights(flows, {"P": 1, "V": -1})
    issues = [i for i in issues if str(i["issue_date"])[:10] <= query_end.isoformat()]
    by_bill = defaultdict(list)
    for row in sales:
        by_bill[str(row["billno"])].append(row)
    visible, ratios = {}, {}
    for bill, rows in by_bill.items():
        kept = [r for r in rows if visible_line(scope, store_id, r)]
        if not kept:
            continue
        visible[bill] = kept
        denominator = sum((dec(r["allocation_base"]) for r in rows), Decimal(0))
        ratios[bill] = Decimal(1) if full else (
            sum((dec(r["allocation_base"]) for r in kept), Decimal(0)) / denominator if denominator else Decimal(0))

    def blank():
        return dict(redeemed_amount=Decimal(0), refunded_amount=Decimal(0), net_coupon_amount=Decimal(0),
                    linked_sales=Decimal(0), linked_returns=Decimal(0), linked_gross_profit=Decimal(0))
    totals = {c: dict(coupon_type=c, **blank()) for c in TYPES}
    daily, departments, groups = defaultdict(blank), defaultdict(blank), defaultdict(blank)

    def organization_keys(row, coupon):
        # Keep codes as part of the identity: display names need not be unique.
        department = (row.get("department_code") or "",
                      row.get("department_name") or row.get("department_code") or "未识别部门", coupon)
        group = (*department, row.get("group_code") or "",
                 row.get("group_name") or row.get("group_code") or "未识别柜组")
        return department, group

    members, assets, tickets = defaultdict(set), defaultdict(set), defaultdict(set)
    quality = dict(unmatched_flow_count=0, missing_issue_flow_count=0, missing_sales_flow_count=0)
    known_assets = {(i["coupon_type"], str(i["asset_id"])) for i in issues}
    # Log amounts are independent of sales/returns. Granular views only include
    # matched visible receipts, with coupon money proportionally allocated.
    for f in selected_flows:
        bill, coupon, action = str(f.get("billno") or ""), f["coupon_type"], f["action"]
        if not full and bill not in visible:
            continue
        if not bill:
            quality["unmatched_flow_count"] += 1
        elif bill not in by_bill:
            quality["missing_sales_flow_count"] += 1
        if (coupon, str(f["asset_id"])) not in known_assets:
            quality["missing_issue_flow_count"] += 1
        amount = dec(f["amount"]) * (ratios.get(bill, Decimal(1)) if full else ratios[bill])
        key = "redeemed_amount" if action in {"O", "U"} else "refunded_amount"
        amount *= -1 if action in {"U", "V"} else 1
        totals[coupon][key] += amount
        daily[str(f["flow_date"])[:10]][key] += amount
        if bill in visible:
            base = sum((dec(r["allocation_base"]) for r in by_bill[bill]), Decimal(0))
            for r in visible[bill]:
                part = dec(r["allocation_base"]) / base if base else Decimal(0)
                department_key, group_key = organization_keys(r, coupon)
                allocated = dec(f["amount"]) * part * (-1 if action in {"U", "V"} else 1)
                for target in (departments[department_key], groups[group_key]):
                    target[key] += allocated

    # Only effective uses establish the holder cohort. Department viewers cannot
    # infer that a person used a coupon exclusively in another department.
    holder_types = defaultdict(set)
    for bill, weights in selected_use.items():
        if not full and bill not in visible:
            continue
        for (coupon, member), amount in weights.items():
            if member:
                members[coupon].add(member)
                holder_types[member].add(coupon)
            tickets[coupon].add(bill)
    asset_balances = defaultdict(Decimal)
    for f in selected_flows:
        if f["action"] in {"O", "U"} and (full or str(f.get("billno") or "") in visible):
            asset_balances[(f["coupon_type"], str(f["asset_id"]))] += dec(f["amount"]) * (1 if f["action"] == "O" else -1)
    for (coupon, asset), amount in asset_balances.items():
        if amount > 0:
            assets[coupon].add(asset)

    details = []
    for bill, rows in visible.items():
        if not within_dates(rows[0]["sale_time"], query_start, query_end):
            continue
        all_sales = sum((dec(r["sales"]) for r in by_bill[bill]), Decimal(0))
        is_return = all_sales < 0
        original = str(rows[0].get("original_billno") or "")
        weights = (use.get(original, {}) if original and original != "0" else refunds.get(bill, {})) if is_return else use.get(bill, {})
        denom = sum(weights.values(), Decimal(0))
        if not denom:
            continue
        for row in rows:
            allocated_sales = split_money(row["sales"], weights)
            allocated_gp = split_money(row["gross_profit"], weights)
            for coupon, holder in weights:
                amount, gp = allocated_sales[(coupon, holder)], allocated_gp[(coupon, holder)]
                day = str(row["sale_time"])[:10]
                department_key, group_key = organization_keys(row, coupon)
                department = department_key[1]
                for target in (totals[coupon], daily[day], departments[department_key], groups[group_key]):
                    target["linked_sales"] += amount
                    target["linked_gross_profit"] += gp
                    if is_return:
                        target["linked_returns"] += amount
                details.append(dict(billno=bill, original_billno=original, sale_time=row["sale_time"],
                                    coupon_type=coupon, holder_member_no=holder,
                                    checkout_member_no=row.get("checkout_member_no") or "",
                                    department=department, group_name=row.get("group_name") or row.get("group_code"),
                                    brand_name=row.get("brand_name") or row.get("brand_code"),
                                    sales=amount, gross_profit=gp, ticket_kind="退货" if is_return else "销售"))

    def holder_shopping(start, end, uses, refund_weights):
        result = []
        for bill, rows in visible.items():
            if not within_dates(rows[0]["sale_time"], start, end):
                continue
            checkout = rows[0].get("checkout_member_no") or ""
            related = {holder for _, holder in uses.get(bill, {}) if holder in holder_types}
            is_return = sum((dec(r["sales"]) for r in by_bill[bill]), Decimal(0)) < 0
            original = str(rows[0].get("original_billno") or "")
            return_weights = (uses.get(original, {}) if original and original != "0" else refund_weights.get(bill, {})) if is_return else {}
            related.update(holder for _, holder in return_weights if holder in holder_types)
            if checkout in holder_types:
                related.add(checkout)
            ticket_weights = return_weights if is_return else uses.get(bill, {})
            for holder in sorted(related):
                used_here = sorted({coupon for coupon, member in ticket_weights if member == holder})
                relation = "本人购物" if checkout == holder else ("购物会员未登记" if not checkout else "持券/购物会员不一致（待核查）")
                for row in rows:
                    result.append(dict(holder_member_no=holder, used_coupon_types=sorted(holder_types[holder]),
                                       checkout_member_no=checkout, billno=bill, sale_time=row["sale_time"],
                                       original_billno=original, ticket_kind="退货" if is_return else "销售",
                                       ticket_coupon_types=sorted({c for c, _ in ticket_weights}),
                                       event_type=("退货 · " if is_return else "") + relation,
                                       coupon_types=("原单：" if is_return and used_here else "") + ("、".join(used_here) or "未用本档跟踪券"),
                                       department=row.get("department_name") or row.get("department_code") or "未识别部门",
                                       department_code=row.get("department_code") or "",
                                       group_code=row.get("group_code") or "", brand_code=row.get("brand_code") or "",
                                       supplier_code=row.get("supplier_code") or "",
                                       group_name=row.get("group_name") or row.get("group_code"),
                                       brand_name=row.get("brand_name") or row.get("brand_code"),
                                       sales=dec(row["sales"]), gross_profit=dec(row["gross_profit"])))
        return result

    trajectory = holder_shopping(today, today, today_use, today_refunds) if TRACKING_START <= today <= end_date else []
    # Keep historical reporting separate from the real-time trajectory. Later
    # reversals must not change the selected period's coupon classification.
    member_trajectory = holder_shopping(query_start, query_end, use, refunds)
    for coupon, target in totals.items():
        rows = [r for r in issues if r["coupon_type"] == coupon]
        target.update(issued_count=len(rows) if full else None,
                      issued_amount=sum((dec(r["amount"]) for r in rows), Decimal(0)) if full else None,
                      preissued_count=sum(str(r["issue_date"])[:10] < TRACKING_START.isoformat() for r in rows) if full else None,
                      used_assets=len(assets[coupon]), used_members=len(members[coupon]), use_tickets=len(tickets[coupon]))
    for target in [*totals.values(), *daily.values(), *departments.values(), *groups.values()]:
        target["net_coupon_amount"] = target["redeemed_amount"] - target["refunded_amount"]
    return serializable(dict(
        scope=dict(mode="full_store" if full else "business_scope", store_code=STORE,
                   label="购物中心整店" if full else "当前账号获授权的部门 / 柜组等范围"),
        tracking_start=TRACKING_START, valid_to=end_date, today=today,
        query_start=query_start, query_end=query_end, observed_end=query_end, coupons=list(totals.values()),
        daily=[dict(day=day, **values) for day, values in sorted(daily.items())],
        departments=[dict(department_code=code, department=d, coupon_type=c, **v)
                     for (code, d, c), v in sorted(departments.items())],
        groups=[dict(department_code=code, department=d, coupon_type=c, group_code=g, group_name=name, **v)
                for (code, d, c, g, name), v in sorted(groups.items())],
        tickets=details, trajectory=trajectory, member_trajectory=member_trajectory, quality=quality,
        holders=[dict(holder_member_no=holder, used_coupon_types=sorted(types))
                 for holder, types in sorted(holder_types.items())],
        trajectory_available=TRACKING_START <= today <= end_date,
        member_period_available=True,
        distinct_used_members=len(set().union(*members.values())) if members else 0,
        distinct_use_tickets=len(set().union(*tickets.values())) if tickets else 0,
    ))


def query_report(db, scope, store_id, selected_end=None, today=None, query_start=None, query_end=None):
    today = today or datetime.now(ZoneInfo("Asia/Shanghai")).date()
    full = check_scope(scope, store_id)
    params = dict(store_code=STORE, coupon_types=list(TYPES), start_date=TRACKING_START,
                  today_end=today + timedelta(days=1))
    periods = limited_rows(db, PERIOD_SQL, params)
    ends = [r["valid_to"] for r in periods]
    if selected_end and selected_end not in ends:
        raise ValueError("该有效期不在当前跟踪券日志中")
    if not selected_end and len(ends) != 1:
        return dict(status="choose_period" if ends else "no_period", periods=serializable(periods),
                    tracking_start=TRACKING_START.isoformat(), today=today.isoformat())
    end_date = selected_end or ends[0]
    query_start, query_end = query_window(today, end_date, query_start, query_end)
    params = parameters(dict(params, end_date=end_date))
    params.update(data_end=min(today, end_date) + timedelta(days=1), today=today,
                  member_start=query_start, member_end=query_end + timedelta(days=1))
    # Never include future issue rows even if source dates were entered ahead.
    issues = limited_rows(db, ISSUES_SQL, dict(params, end_exclusive=query_end + timedelta(days=1)))
    flows = limited_rows(db, FLOW_SQL, params)
    params.update(bills=sorted({f["billno"] for f in flows if f.get("billno")}), holders=[])
    sales = limited_rows(db, SALES_SQL, params) if params["bills"] else []
    # First apply scope to coupon receipts, then select holder trajectories.
    visible_bills = {r["billno"] for r in sales if visible_line(scope, store_id, r)}
    weights = flow_weights([f for f in flows if within_dates(f["flow_date"], query_start, query_end)], {"O": 1, "U": -1})
    # Full-store viewers can follow a known holder's own shopping even when the
    # original coupon receipt has no merchandise yet. Scoped viewers still need
    # a visible use receipt before that holder can enter the cohort.
    holders = sorted({m for b, w in weights.items() if full or b in visible_bills for (_, m) in w if m})
    if holders:
        sales = limited_rows(db, SALES_SQL, dict(params, holders=holders))
    result = build_report(issues, flows, sales, scope, store_id, today, end_date, query_start, query_end)
    result.update(status="ready", periods=serializable(periods),
                  generated_at=datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
                  latest_visible_sale=max((str(r["sale_time"]) for r in sales if visible_line(scope, store_id, r)), default=None),
                  latest_visible_coupon_date=max((str(f["flow_date"]) for f in flows
                      if check_scope(scope, store_id) or f.get("billno") in visible_bills), default=None))
    return result
