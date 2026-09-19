"""C券黑金/黑钻会员的品牌及品类主管跟进分配。"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session


FOLLOWUP_MEMBER_LEVELS = ("黑金卡会员", "黑钻卡会员")
FOLLOWUP_STATUS_CODES = {
    "NOT_VISITED",
    "VISITED_NOT_REDEEMED",
    "REDEEMED",
    "REDEEMED_RETURNED",
    "UNASSIGNED_BRAND",
    "UNASSIGNED_MANAGER",
}


def normalize_followup_status(value: str | None) -> str | None:
    normalized = str(value or "").strip().upper()
    if not normalized or normalized == "ALL":
        return None
    if normalized not in FOLLOWUP_STATUS_CODES:
        raise ValueError("跟进状态不正确")
    return normalized


def followup_status_label(value: str | None) -> str:
    return {
        "NOT_VISITED": "未到店",
        "VISITED_NOT_REDEEMED": "已到店未用券",
        "REDEEMED": "已用券",
        "REDEEMED_RETURNED": "用券后已退",
        "UNASSIGNED_BRAND": "待分配品牌",
        "UNASSIGNED_MANAGER": "待分配品类主管",
    }.get(str(value or "").upper(), "待核对")


def mask_member_no(value: Any) -> str:
    member_no = str(value or "").strip()
    if len(member_no) <= 4:
        return member_no or "—"
    hidden = "*" * min(6, max(2, len(member_no) - 6))
    return f"{member_no[:2]}{hidden}{member_no[-4:]}"


def mask_member_name(value: Any) -> str:
    name = str(value or "").strip()
    if len(name) <= 1:
        return name or "—"
    return f"{name[0]}{'*' * (len(name) - 1)}"


def _serializable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


def _rows(rows: Iterable[Any]) -> list[dict[str, Any]]:
    return [
        {key: _serializable(value) for key, value in row.items()}
        for row in rows
    ]


def _chunks(values: list[Any], size: int = 500) -> Iterable[list[Any]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]


FOLLOWUP_QUERY = """
WITH issued_coupons AS MATERIALIZED (
  SELECT
    UPPER(TRIM(l.tcflvipno)) AS member_no,
    l.tcflvipseq AS coupon_asset_id,
    COALESCE(l.tcflmoney, 0)::numeric AS issue_amount
  FROM tktcardfqlog l
  WHERE TRIM(COALESCE(l.tcflmkt, '')) = :market_code
    AND UPPER(TRIM(COALESCE(l.tcfljetype, ''))) = 'C'
    AND TRIM(COALESCE(l.tcflzy, '')) = :issue_action
    AND l.tcfldate >= CAST(:period_start AS date)
    AND l.tcfldate < CAST(:period_end AS date)
    AND NULLIF(TRIM(COALESCE(l.tcflvipno, '')), '') IS NOT NULL
),
issued_members AS MATERIALIZED (
  SELECT
    member_no,
    COUNT(*) AS issue_count,
    SUM(issue_amount) AS issued_amount
  FROM issued_coupons
  GROUP BY member_no
),
member_dim AS MATERIALIZED (
  SELECT
    issued.member_no,
    MAX(NULLIF(TRIM(member.customer_name), '')) AS customer_name,
    MAX(NULLIF(TRIM(member.customer_level), '')) AS customer_level
  FROM issued_members issued
  JOIN fj_dw_member_dim member
    ON UPPER(TRIM(member.customer_no)) = issued.member_no
  GROUP BY issued.member_no
),
eligible_members AS MATERIALIZED (
  SELECT issued.*, dim.customer_name, dim.customer_level
  FROM issued_members issued
  JOIN member_dim dim ON dim.member_no = issued.member_no
  WHERE dim.customer_level IN ('黑金卡会员', '黑钻卡会员')
),
history_group_sales AS MATERIALIZED (
  SELECT
    eligible.member_no,
    TRIM(s.sglmfid) AS group_code,
    SUM(COALESCE(s.sglxssr, 0)::numeric) AS history_sales_amount,
    COUNT(DISTINCT h.billno) AS history_ticket_count,
    MAX(h.rqsj) AS last_history_sale_time
  FROM eligible_members eligible
  JOIN salehead h
    ON NULLIF(UPPER(TRIM(COALESCE(h.hykh, ''))), '') = eligible.member_no
   AND TRIM(h.mkt::text) = :market_code
   AND h.rqsj >= CAST(:period_start AS date) - INTERVAL '12 months'
   AND h.rqsj < CAST(:period_start AS date)
  JOIN salegoodslist s
    ON s.sglbillno = h.billno
   AND TRIM(s.sglmarket::text) = :market_code
   AND NULLIF(TRIM(COALESCE(s.sglmfid, '')), '') IS NOT NULL
  GROUP BY eligible.member_no, TRIM(s.sglmfid)
  HAVING SUM(COALESCE(s.sglxssr, 0)::numeric) > 0
),
ranked_history AS MATERIALIZED (
  SELECT
    history.*,
    ROW_NUMBER() OVER (
      PARTITION BY history.member_no
      ORDER BY history.history_sales_amount DESC,
               history.last_history_sale_time DESC,
               history.group_code
    ) AS preference_rank
  FROM history_group_sales history
),
current_bill_sales AS MATERIALIZED (
  SELECT
    eligible.member_no,
    h.billno,
    MAX(h.rqsj) AS sale_time,
    SUM(COALESCE(s.sglxssr, 0)::numeric) AS bill_sales_amount
  FROM eligible_members eligible
  JOIN salehead h
    ON NULLIF(UPPER(TRIM(COALESCE(h.hykh, ''))), '') = eligible.member_no
   AND TRIM(h.mkt::text) = :market_code
   AND h.rqsj >= CAST(:period_start AS date)
   AND h.rqsj < CAST(:period_end AS date)
  JOIN salegoodslist s
    ON s.sglbillno = h.billno
   AND TRIM(s.sglmarket::text) = :market_code
  GROUP BY eligible.member_no, h.billno
),
current_member_sales AS MATERIALIZED (
  SELECT
    member_no,
    COUNT(*) AS current_ticket_count,
    SUM(bill_sales_amount) AS current_sales_amount,
    MAX(sale_time) AS last_current_sale_time
  FROM current_bill_sales
  WHERE bill_sales_amount > 0
  GROUP BY member_no
),
coupon_usage AS MATERIALIZED (
  SELECT
    issued.member_no,
    COUNT(*) FILTER (WHERE flow.tcflzy = 'O') AS coupon_use_count,
    SUM(
      CASE
        WHEN flow.tcflzy = 'O' THEN ABS(COALESCE(flow.tcflmoney, 0))
        WHEN flow.tcflzy IN ('P', 'U') THEN -ABS(COALESCE(flow.tcflmoney, 0))
        WHEN flow.tcflzy = 'V' THEN ABS(COALESCE(flow.tcflmoney, 0))
        ELSE 0
      END
    )::numeric AS net_redeemed_amount,
    MAX(flow.tcfldate) FILTER (WHERE flow.tcflzy = 'O') AS last_coupon_use_date
  FROM issued_coupons issued
  JOIN tktcardfqlog flow ON flow.tcflvipseq = issued.coupon_asset_id
  WHERE flow.tcflzy IN ('O', 'P', 'U', 'V')
    AND flow.tcfldate >= CAST(:period_start AS date)
    AND flow.tcfldate < CAST(:period_end AS date)
  GROUP BY issued.member_no
),
store_row AS MATERIALIZED (
  SELECT store_id
  FROM stores
  WHERE TRIM(store_code) = :market_code
    AND COALESCE(is_active, TRUE)
  ORDER BY store_id
  LIMIT 1
)
SELECT
  CAST(:period_start AS date) AS period_month,
  eligible.member_no,
  eligible.customer_name,
  eligible.customer_level,
  eligible.issue_count,
  eligible.issued_amount,
  history.group_code AS followup_group_code,
  COALESCE(NULLIF(TRIM(mf.mfcname), ''), history.group_code) AS followup_group_name,
  NULLIF(TRIM(dept.mfcode), '') AS department_code,
  NULLIF(TRIM(dept.mfcname), '') AS department_name,
  history.history_sales_amount,
  history.history_ticket_count,
  history.last_history_sale_time,
  assignment.manager_user_id,
  assignment.manager_name,
  COALESCE(current_sales.current_ticket_count, 0) AS current_ticket_count,
  COALESCE(current_sales.current_sales_amount, 0) AS current_sales_amount,
  current_sales.last_current_sale_time,
  COALESCE(usage.coupon_use_count, 0) AS coupon_use_count,
  COALESCE(usage.net_redeemed_amount, 0) AS net_redeemed_amount,
  usage.last_coupon_use_date,
  CASE
    WHEN history.group_code IS NULL THEN 'UNASSIGNED_BRAND'
    WHEN assignment.manager_user_id IS NULL THEN 'UNASSIGNED_MANAGER'
    WHEN COALESCE(usage.net_redeemed_amount, 0) > 0 THEN 'REDEEMED'
    WHEN COALESCE(usage.coupon_use_count, 0) > 0 THEN 'REDEEMED_RETURNED'
    WHEN COALESCE(current_sales.current_ticket_count, 0) > 0 THEN 'VISITED_NOT_REDEEMED'
    ELSE 'NOT_VISITED'
  END AS followup_status
FROM eligible_members eligible
LEFT JOIN ranked_history history
  ON history.member_no = eligible.member_no
 AND history.preference_rank = 1
LEFT JOIN manaframe mf
  ON UPPER(TRIM(mf.mfcode)) = UPPER(history.group_code)
LEFT JOIN manaframe dept
  ON UPPER(TRIM(dept.mfcode)) = UPPER(TRIM(mf.mfpcode))
LEFT JOIN store_row store_scope ON TRUE
LEFT JOIN category_manager_brand_assignments assignment
  ON assignment.store_id = store_scope.store_id
 AND UPPER(TRIM(assignment.group_code)) = UPPER(history.group_code)
 AND assignment.is_active
LEFT JOIN current_member_sales current_sales ON current_sales.member_no = eligible.member_no
LEFT JOIN coupon_usage usage ON usage.member_no = eligible.member_no
ORDER BY
  CASE WHEN assignment.manager_user_id IS NULL THEN 1 ELSE 0 END,
  assignment.manager_name,
  eligible.customer_level,
  history.history_sales_amount DESC NULLS LAST,
  eligible.member_no
"""


def query_coupon_followups(
    db: Session,
    *,
    period_start: date,
    period_end: date,
    market_code: str,
    issue_action: str,
    manager_user_id: int | None = None,
    member_levels: tuple[str, ...] = FOLLOWUP_MEMBER_LEVELS,
    status_code: str | None = None,
    keyword: str | None = None,
    limit: int = 500,
    offset: int = 0,
) -> dict[str, Any]:
    """Build a stable one-member/one-primary-brand follow-up queue."""
    selected_status = normalize_followup_status(status_code)
    common_params = {
        "period_start": period_start,
        "period_end": period_end,
        "market_code": market_code,
        "issue_action": issue_action,
    }
    issued_coupon_rows = db.execute(
        text(
            """
            SELECT
              UPPER(TRIM(l.tcflvipno)) AS member_no,
              l.tcflvipseq AS coupon_asset_id,
              COALESCE(l.tcflmoney, 0)::numeric AS issue_amount
            FROM tktcardfqlog l
            WHERE TRIM(COALESCE(l.tcflmkt, '')) = :market_code
              AND UPPER(TRIM(COALESCE(l.tcfljetype, ''))) = 'C'
              AND TRIM(COALESCE(l.tcflzy, '')) = :issue_action
              AND l.tcfldate >= CAST(:period_start AS date)
              AND l.tcfldate < CAST(:period_end AS date)
              AND NULLIF(TRIM(COALESCE(l.tcflvipno, '')), '') IS NOT NULL
            """
        ),
        common_params,
    ).mappings().all()

    issued_by_member: dict[str, dict[str, Any]] = {}
    asset_owner: dict[Any, str] = {}
    for coupon in issued_coupon_rows:
        member_no = str(coupon["member_no"])
        member = issued_by_member.setdefault(
            member_no,
            {"member_no": member_no, "issue_count": 0, "issued_amount": Decimal("0")},
        )
        member["issue_count"] += 1
        member["issued_amount"] += Decimal(str(coupon["issue_amount"] or 0))
        asset_owner[coupon["coupon_asset_id"]] = member_no

    member_nos = list(issued_by_member)
    if not member_nos:
        rows: list[dict[str, Any]] = []
    else:
        member_dim_query = text(
            """
            SELECT
              UPPER(TRIM(customer_no)) AS member_no,
              MAX(NULLIF(TRIM(customer_name), '')) AS customer_name,
              MAX(NULLIF(TRIM(customer_level), '')) AS customer_level
            FROM fj_dw_member_dim
            WHERE UPPER(TRIM(customer_no)) IN :member_nos
            GROUP BY UPPER(TRIM(customer_no))
            """
        ).bindparams(bindparam("member_nos", expanding=True))
        member_dims = {
            str(row["member_no"]): dict(row)
            for row in db.execute(member_dim_query, {"member_nos": member_nos}).mappings().all()
        }
        eligible_nos = [
            member_no
            for member_no in member_nos
            if member_dims.get(member_no, {}).get("customer_level") in member_levels
        ]

        salehead_query = text(
            """
            SELECT
              NULLIF(UPPER(TRIM(COALESCE(h.hykh, ''))), '') AS member_no,
              h.billno,
              h.rqsj AS sale_time
            FROM salehead h
            WHERE h.mkt = :market_code
              AND NULLIF(TRIM(COALESCE(h.hykh, '')), '') IS NOT NULL
              AND NULLIF(UPPER(TRIM(COALESCE(h.hykh, ''))), '') IN :member_nos
              AND h.rqsj >= CAST(:sales_start AS date)
              AND h.rqsj < CAST(:sales_end AS date)
            """
        ).bindparams(bindparam("member_nos", expanding=True))

        def saleheads(sales_start: date, sales_end: date) -> list[dict[str, Any]]:
            if not eligible_nos:
                return []
            return [
                dict(row)
                for row in db.execute(
                    salehead_query,
                    {
                        "market_code": market_code,
                        "member_nos": eligible_nos,
                        "sales_start": sales_start,
                        "sales_end": sales_end,
                    },
                ).mappings().all()
            ]

        goods_query = text(
            """
            SELECT
              s.sglbillno AS billno,
              NULLIF(TRIM(COALESCE(s.sglmfid, '')), '') AS group_code,
              SUM(COALESCE(s.sglxssr, 0)::numeric) AS sales_amount
            FROM salegoodslist s
            WHERE s.sglmarket = :market_code
              AND s.sglbillno IN :billnos
            GROUP BY s.sglbillno, NULLIF(TRIM(COALESCE(s.sglmfid, '')), '')
            """
        ).bindparams(bindparam("billnos", expanding=True))

        def goods_for_heads(heads: list[dict[str, Any]]) -> list[dict[str, Any]]:
            billnos = list(dict.fromkeys(row["billno"] for row in heads))
            goods: list[dict[str, Any]] = []
            for batch in _chunks(billnos):
                goods.extend(
                    dict(row)
                    for row in db.execute(
                        goods_query,
                        {"market_code": market_code, "billnos": batch},
                    ).mappings().all()
                )
            return goods

        history_start = period_start.replace(year=period_start.year - 1)
        history_heads = saleheads(history_start, period_start)
        history_head_by_bill = {row["billno"]: row for row in history_heads}
        history_groups: dict[tuple[str, str], dict[str, Any]] = {}
        for goods in goods_for_heads(history_heads):
            group_code = str(goods.get("group_code") or "").strip()
            if not group_code:
                continue
            head = history_head_by_bill.get(goods["billno"])
            if not head:
                continue
            key = (str(head["member_no"]), group_code)
            aggregate = history_groups.setdefault(
                key,
                {
                    "history_sales_amount": Decimal("0"),
                    "history_billnos": set(),
                    "last_history_sale_time": None,
                },
            )
            aggregate["history_sales_amount"] += Decimal(str(goods["sales_amount"] or 0))
            aggregate["history_billnos"].add(head["billno"])
            if aggregate["last_history_sale_time"] is None or head["sale_time"] > aggregate["last_history_sale_time"]:
                aggregate["last_history_sale_time"] = head["sale_time"]

        preferred_history: dict[str, tuple[str, dict[str, Any]]] = {}
        for (member_no, group_code), aggregate in history_groups.items():
            if aggregate["history_sales_amount"] <= 0:
                continue
            previous = preferred_history.get(member_no)
            candidate_key = (
                aggregate["history_sales_amount"],
                aggregate["last_history_sale_time"],
                group_code,
            )
            previous_key = (
                previous[1]["history_sales_amount"],
                previous[1]["last_history_sale_time"],
                previous[0],
            ) if previous else None
            if previous_key is None or candidate_key > previous_key:
                preferred_history[member_no] = (group_code, aggregate)

        current_heads = saleheads(period_start, period_end)
        current_head_by_bill = {row["billno"]: row for row in current_heads}
        current_bill_amounts: dict[Any, Decimal] = defaultdict(lambda: Decimal("0"))
        for goods in goods_for_heads(current_heads):
            current_bill_amounts[goods["billno"]] += Decimal(str(goods["sales_amount"] or 0))
        current_sales: dict[str, dict[str, Any]] = {}
        for billno, bill_amount in current_bill_amounts.items():
            if bill_amount <= 0:
                continue
            head = current_head_by_bill[billno]
            member_no = str(head["member_no"])
            aggregate = current_sales.setdefault(
                member_no,
                {"current_ticket_count": 0, "current_sales_amount": Decimal("0"), "last_current_sale_time": None},
            )
            aggregate["current_ticket_count"] += 1
            aggregate["current_sales_amount"] += bill_amount
            if aggregate["last_current_sale_time"] is None or head["sale_time"] > aggregate["last_current_sale_time"]:
                aggregate["last_current_sale_time"] = head["sale_time"]

        usage_query = text(
            """
            SELECT
              flow.tcflvipseq AS coupon_asset_id,
              COUNT(*) FILTER (WHERE flow.tcflzy = 'O') AS coupon_use_count,
              SUM(
                CASE
                  WHEN flow.tcflzy = 'O' THEN ABS(COALESCE(flow.tcflmoney, 0))
                  WHEN flow.tcflzy IN ('P', 'U') THEN -ABS(COALESCE(flow.tcflmoney, 0))
                  WHEN flow.tcflzy = 'V' THEN ABS(COALESCE(flow.tcflmoney, 0))
                  ELSE 0
                END
              )::numeric AS net_redeemed_amount,
              MAX(flow.tcfldate) FILTER (WHERE flow.tcflzy = 'O') AS last_coupon_use_date
            FROM tktcardfqlog flow
            WHERE flow.tcflvipseq IN :asset_ids
              AND flow.tcflzy IN ('O', 'P', 'U', 'V')
              AND flow.tcfldate >= CAST(:period_start AS date)
              AND flow.tcfldate < CAST(:period_end AS date)
            GROUP BY flow.tcflvipseq
            """
        ).bindparams(bindparam("asset_ids", expanding=True))
        usage_by_member: dict[str, dict[str, Any]] = {}
        asset_ids = list(asset_owner)
        for batch in _chunks(asset_ids):
            usage_rows = db.execute(
                usage_query,
                {"asset_ids": batch, "period_start": period_start, "period_end": period_end},
            ).mappings().all()
            for usage in usage_rows:
                member_no = asset_owner.get(usage["coupon_asset_id"])
                if member_no not in eligible_nos:
                    continue
                aggregate = usage_by_member.setdefault(
                    member_no,
                    {"coupon_use_count": 0, "net_redeemed_amount": Decimal("0"), "last_coupon_use_date": None},
                )
                aggregate["coupon_use_count"] += int(usage["coupon_use_count"] or 0)
                aggregate["net_redeemed_amount"] += Decimal(str(usage["net_redeemed_amount"] or 0))
                last_use = usage["last_coupon_use_date"]
                if last_use and (aggregate["last_coupon_use_date"] is None or last_use > aggregate["last_coupon_use_date"]):
                    aggregate["last_coupon_use_date"] = last_use

        group_query = text(
            """
            SELECT
              TRIM(mf.mfcode) AS group_code,
              COALESCE(NULLIF(TRIM(mf.mfcname), ''), TRIM(mf.mfcode)) AS group_name,
              NULLIF(TRIM(dept.mfcode), '') AS department_code,
              NULLIF(TRIM(dept.mfcname), '') AS department_name,
              assignment.manager_user_id,
              assignment.manager_name
            FROM manaframe mf
            LEFT JOIN manaframe dept
              ON UPPER(TRIM(dept.mfcode)) = UPPER(TRIM(mf.mfpcode))
            LEFT JOIN stores store_scope
              ON TRIM(store_scope.store_code) = :market_code
             AND COALESCE(store_scope.is_active, TRUE)
            LEFT JOIN category_manager_brand_assignments assignment
              ON assignment.store_id = store_scope.store_id
             AND UPPER(TRIM(assignment.group_code)) = UPPER(TRIM(mf.mfcode))
             AND assignment.is_active
            WHERE TRIM(mf.mfcode) IN :group_codes
            """
        ).bindparams(bindparam("group_codes", expanding=True))
        preferred_group_codes = list({value[0] for value in preferred_history.values()})
        group_meta = {}
        if preferred_group_codes:
            group_meta = {
                str(row["group_code"]): dict(row)
                for row in db.execute(
                    group_query,
                    {"market_code": market_code, "group_codes": preferred_group_codes},
                ).mappings().all()
            }

        rows = []
        for member_no in eligible_nos:
            issued = issued_by_member[member_no]
            dim = member_dims[member_no]
            preferred = preferred_history.get(member_no)
            group_code = preferred[0] if preferred else None
            history = preferred[1] if preferred else {}
            group = group_meta.get(group_code or "", {})
            current = current_sales.get(member_no, {})
            usage = usage_by_member.get(member_no, {})
            manager_user = group.get("manager_user_id")
            net_redeemed = Decimal(str(usage.get("net_redeemed_amount") or 0))
            coupon_use_count = int(usage.get("coupon_use_count") or 0)
            current_ticket_count = int(current.get("current_ticket_count") or 0)
            if not group_code:
                followup_status = "UNASSIGNED_BRAND"
            elif not manager_user:
                followup_status = "UNASSIGNED_MANAGER"
            elif net_redeemed > 0:
                followup_status = "REDEEMED"
            elif coupon_use_count > 0:
                followup_status = "REDEEMED_RETURNED"
            elif current_ticket_count > 0:
                followup_status = "VISITED_NOT_REDEEMED"
            else:
                followup_status = "NOT_VISITED"
            rows.append(
                {
                    "period_month": period_start,
                    "member_no": member_no,
                    "customer_name": dim.get("customer_name"),
                    "customer_level": dim.get("customer_level"),
                    "issue_count": issued["issue_count"],
                    "issued_amount": issued["issued_amount"],
                    "followup_group_code": group_code,
                    "followup_group_name": group.get("group_name"),
                    "department_code": group.get("department_code"),
                    "department_name": group.get("department_name"),
                    "history_sales_amount": history.get("history_sales_amount", Decimal("0")),
                    "history_ticket_count": len(history.get("history_billnos", set())),
                    "last_history_sale_time": history.get("last_history_sale_time"),
                    "manager_user_id": manager_user,
                    "manager_name": group.get("manager_name"),
                    "current_ticket_count": current_ticket_count,
                    "current_sales_amount": current.get("current_sales_amount", Decimal("0")),
                    "last_current_sale_time": current.get("last_current_sale_time"),
                    "coupon_use_count": coupon_use_count,
                    "net_redeemed_amount": net_redeemed,
                    "last_coupon_use_date": usage.get("last_coupon_use_date"),
                    "followup_status": followup_status,
                }
            )
        rows.sort(
            key=lambda row: (
                row.get("manager_user_id") is None,
                str(row.get("manager_name") or ""),
                str(row.get("customer_level") or ""),
                -float(row.get("history_sales_amount") or 0),
                str(row.get("member_no") or ""),
            )
        )
        rows = [{key: _serializable(value) for key, value in row.items()} for row in rows]

    scoped_rows = [
        row
        for row in rows
        if manager_user_id is None or int(row.get("manager_user_id") or 0) == manager_user_id
    ]
    summary = {
        "target_member_count": len(scoped_rows),
        "assigned_brand_count": sum(bool(row.get("followup_group_code")) for row in scoped_rows),
        "assigned_manager_count": sum(bool(row.get("manager_user_id")) for row in scoped_rows),
        "visited_member_count": sum(int(row.get("current_ticket_count") or 0) > 0 for row in scoped_rows),
        "redeemed_member_count": sum(float(row.get("net_redeemed_amount") or 0) > 0 for row in scoped_rows),
        "unassigned_brand_count": sum(row.get("followup_status") == "UNASSIGNED_BRAND" for row in scoped_rows),
        "unassigned_manager_count": sum(row.get("followup_status") == "UNASSIGNED_MANAGER" for row in scoped_rows),
    }

    normalized_keyword = str(keyword or "").strip().lower()
    filtered_rows = []
    for row in scoped_rows:
        if selected_status and row.get("followup_status") != selected_status:
            continue
        if normalized_keyword and not any(
            normalized_keyword in str(row.get(field) or "").lower()
            for field in ("member_no", "customer_name", "followup_group_code", "followup_group_name", "manager_name")
        ):
            continue
        filtered_rows.append(row)

    page = filtered_rows[offset : offset + limit]
    for row in page:
        row["masked_member_no"] = mask_member_no(row.get("member_no"))
        row["masked_customer_name"] = mask_member_name(row.get("customer_name"))
        row["followup_status_label"] = followup_status_label(row.get("followup_status"))

    return {
        "period_month": period_start.isoformat(),
        "history_window": {
            "start_date": period_start.replace(year=period_start.year - 1).isoformat(),
            "end_date": period_start.isoformat(),
            "basis": "发券月前12个月正向净消费金额最高柜组，金额相同时取最近消费柜组",
        },
        "summary": summary,
        "items": page,
        "total": len(filtered_rows),
        "limit": limit,
        "offset": offset,
    }
