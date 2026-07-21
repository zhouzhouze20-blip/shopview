"""联营续签合同收益影响分析（第一稿）。

第一稿只测算基础合同扣率变化。历史活动扣率、付款方式、储值卡及
其他结算调整保留在上一合同实际毛利中，不在本模块内重新解释。
"""

from __future__ import annotations

from collections import Counter
from datetime import date
from decimal import Decimal
import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from routers.authz import DataScope, scope_allows_business


EPSILON_AMOUNT = Decimal("1.00")
RATE_RECONCILIATION_TOLERANCE = Decimal("0.005")


PAIR_SQL = """
WITH new_groups AS (
    SELECT DISTINCT ON (
        upper(trim(cm.cmcontno)),
        upper(trim(cmf.cmfmfid))
    )
      upper(trim(cm.cmcontno)) AS new_contract_no,
      upper(trim(cm.cmsupid)) AS supplier_code,
      COALESCE(sb.sbcname, '') AS supplier_name,
      upper(trim(cmf.cmfmfid)) AS group_code,
      COALESCE(mf.mfcname, '') AS group_name,
      COALESCE(mf.mfpcode, '') AS department_code,
      COALESCE(dept.mfcname, '') AS department_name,
      substring(trim(cmf.cmfmfid) from 1 for 3) AS store_code,
      COALESCE(st.store_name, '') AS store_name,
      COALESCE(cmf.cmfbrand, cm.cmppname, '') AS brand_name,
      cm.cmeffdate::date AS new_start_date,
      cm.cmlapdate::date AS new_end_date,
      cmf.cmfeffdate::date AS new_rate_start_date,
      cmf.cmflapdate::date AS new_rate_end_date,
      cmf.cmfnum1 AS new_rate_1,
      cmf.cmfnum2 AS new_rate_2,
      cmf.cmfnum3 AS new_rate_3,
      cmf.cmfnum4 AS new_rate_4,
      cmf.cmfnum5 AS new_rate_5
    FROM contmain cm
    JOIN contmanaframe cmf
      ON upper(trim(cmf.cmfcontno)) = upper(trim(cm.cmcontno))
    LEFT JOIN supplierbase sb
      ON upper(trim(sb.sbid)) = upper(trim(cm.cmsupid))
    LEFT JOIN manaframe mf
      ON upper(trim(mf.mfcode)) = upper(trim(cmf.cmfmfid))
    LEFT JOIN manaframe dept
      ON upper(trim(dept.mfcode)) = upper(trim(mf.mfpcode))
    LEFT JOIN stores st
      ON trim(st.store_code) = substring(trim(cmf.cmfmfid) from 1 for 3)
    WHERE cm.cmeffdate::date BETWEEN :start_date AND :end_date
      AND upper(trim(COALESCE(cm.cmstatus, ''))) IN ('Y', 'Q')
      AND trim(COALESCE(cm.cmwmid, '')) = '4'
      AND NULLIF(trim(cm.cmsupid), '') IS NOT NULL
      AND NULLIF(trim(cmf.cmfmfid), '') IS NOT NULL
    ORDER BY
      upper(trim(cm.cmcontno)),
      upper(trim(cmf.cmfmfid)),
      cmf.cmfeffdate ASC NULLS LAST,
      cmf.cmflapdate ASC NULLS LAST
),
pairs AS (
    SELECT
      new_groups.*,
      old_contract.old_contract_no,
      old_contract.old_start_date,
      old_contract.old_end_date,
      old_contract.old_rate_start_date,
      old_contract.old_rate_end_date,
      old_contract.old_rate_1,
      old_contract.old_rate_2,
      old_contract.old_rate_3,
      old_contract.old_rate_4,
      old_contract.old_rate_5,
      (new_groups.new_start_date - old_contract.old_end_date - 1) AS gap_days
    FROM new_groups
    JOIN LATERAL (
        SELECT
          upper(trim(old_cm.cmcontno)) AS old_contract_no,
          old_cm.cmeffdate::date AS old_start_date,
          old_cm.cmlapdate::date AS old_end_date,
          old_rate.cmfeffdate::date AS old_rate_start_date,
          old_rate.cmflapdate::date AS old_rate_end_date,
          old_rate.cmfnum1 AS old_rate_1,
          old_rate.cmfnum2 AS old_rate_2,
          old_rate.cmfnum3 AS old_rate_3,
          old_rate.cmfnum4 AS old_rate_4,
          old_rate.cmfnum5 AS old_rate_5
        FROM contmain old_cm
        JOIN LATERAL (
            SELECT
              cmf.cmfeffdate,
              cmf.cmflapdate,
              cmf.cmfnum1,
              cmf.cmfnum2,
              cmf.cmfnum3,
              cmf.cmfnum4,
              cmf.cmfnum5
            FROM contmanaframe cmf
            WHERE upper(trim(cmf.cmfcontno)) = upper(trim(old_cm.cmcontno))
              AND upper(trim(cmf.cmfmfid)) = new_groups.group_code
            ORDER BY
              cmf.cmflapdate DESC NULLS LAST,
              cmf.cmfeffdate DESC NULLS LAST
            LIMIT 1
        ) old_rate ON TRUE
        WHERE upper(trim(old_cm.cmsupid)) = new_groups.supplier_code
          AND upper(trim(COALESCE(old_cm.cmstatus, ''))) IN ('Y', 'Q')
          AND trim(COALESCE(old_cm.cmwmid, '')) = '4'
          AND upper(trim(old_cm.cmcontno)) <> new_groups.new_contract_no
          AND old_cm.cmeffdate IS NOT NULL
          AND old_cm.cmlapdate IS NOT NULL
          AND old_cm.cmeffdate::date < new_groups.new_start_date
          AND old_cm.cmlapdate::date < new_groups.new_start_date
          AND (new_groups.new_start_date - old_cm.cmlapdate::date - 1) BETWEEN 0 AND 31
        ORDER BY
          old_cm.cmlapdate DESC,
          old_cm.cmeffdate DESC,
          upper(trim(old_cm.cmcontno))
        LIMIT 1
    ) old_contract ON TRUE
)
SELECT *
FROM pairs
ORDER BY store_code, department_code, supplier_code, group_code, new_start_date, new_contract_no
"""


SALES_SQL = """
WITH input_pairs AS (
    SELECT *
    FROM jsonb_to_recordset(CAST(:pairs_json AS jsonb)) AS pair(
      pair_id text,
      store_code text,
      group_code text,
      supplier_code text,
      old_start_date date,
      old_end_date date
    )
)
SELECT
  pair.pair_id,
  sales.*
FROM input_pairs pair
LEFT JOIN LATERAL (
    SELECT
      COUNT(*)::integer AS sales_row_count,
      MIN(s.revenue_date)::date AS sales_first_date,
      MAX(s.revenue_date)::date AS sales_last_date,
      COALESCE(SUM(s.sales_qty), 0)::numeric AS sales_qty,
      COALESCE(SUM(s.tax_excluded_sales_amount), 0)::numeric AS priced_sales_amount,
      COALESCE(SUM(s.tax_excluded_sales_amount), 0)::numeric AS sales_revenue,
      COALESCE(SUM(s.tax_excluded_profit_amount), 0)::numeric AS actual_gross_profit,
      NULL::numeric AS historical_base_profit,
      NULL::numeric AS historical_sales_rate_profit,
      NULL::numeric AS activity_rate_impact,
      0::integer AS activity_sales_row_count,
      NULL::numeric AS stored_card_amount,
      NULL::numeric AS voucher_amount,
      NULL::numeric AS member_discount_amount,
      NULL::numeric AS promotion_discount_amount,
      NULL::numeric AS recorded_payment_fee_amount
    FROM unit_revenue_sales_detail s
    WHERE s.source_group_code = pair.group_code
      AND s.revenue_date BETWEEN pair.old_start_date AND pair.old_end_date
) sales ON TRUE
"""


def _decimal(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _optional_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    return _decimal(value)


def _ratio(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _float(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def _date_text(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)[:10]


def _has_additional_rates(row: dict[str, Any]) -> bool:
    return any(
        _decimal(row.get(f"{side}_rate_{index}")) != 0
        for side in ("old", "new")
        for index in range(2, 6)
    )


def calculate_joint_renewal_item(
    raw: dict[str, Any],
    *,
    source_min_date: date | None,
    source_max_date: date | None,
) -> dict[str, Any]:
    priced_sales = _decimal(raw.get("priced_sales_amount"))
    sales_revenue = _decimal(raw.get("sales_revenue"))
    actual_profit = _decimal(raw.get("actual_gross_profit"))
    historical_base_profit = _optional_decimal(raw.get("historical_base_profit"))
    historical_sales_rate_profit = _optional_decimal(raw.get("historical_sales_rate_profit"))
    old_rate = _optional_decimal(raw.get("old_rate_1"))
    new_rate = _optional_decimal(raw.get("new_rate_1"))
    sales_row_count = int(raw.get("sales_row_count") or 0)

    weighted_base_rate = _ratio(historical_base_profit, priced_sales) if historical_base_profit is not None else None
    weighted_sales_rate = _ratio(historical_sales_rate_profit, priced_sales) if historical_sales_rate_profit is not None else None
    rate_delta = new_rate - old_rate if old_rate is not None and new_rate is not None else None
    base_rate_impact = priced_sales * rate_delta if rate_delta is not None else None
    simulated_new_profit = actual_profit + base_rate_impact if base_rate_impact is not None else None
    change_rate = _ratio(base_rate_impact, abs(actual_profit)) if base_rate_impact is not None else None
    payment_and_other_residual = (
        actual_profit - historical_sales_rate_profit
        if historical_sales_rate_profit is not None
        else None
    )

    review_reasons: list[str] = []
    if sales_row_count == 0:
        review_reasons.append("上一合同期间无匹配销售")
    if old_rate is None or new_rate is None:
        review_reasons.append("新旧合同基础扣率不完整")
    if _has_additional_rates(raw):
        review_reasons.append("存在扣率2-5，第一稿仅测算扣率1")
    if old_rate is not None and weighted_base_rate is not None:
        if abs(weighted_base_rate - old_rate) > RATE_RECONCILIATION_TOLERANCE:
            review_reasons.append("销售基础扣率与上一合同扣率差异超过0.5个百分点")

    old_start = raw.get("old_start_date")
    old_end = raw.get("old_end_date")
    if source_min_date and old_start and old_start < source_min_date:
        review_reasons.append("上一合同开始早于销售数据覆盖范围")
    if source_max_date and old_end and old_end > source_max_date:
        review_reasons.append("上一合同结束晚于销售数据覆盖范围")

    if base_rate_impact is None or sales_row_count == 0:
        classification = "待复核"
    elif base_rate_impact > EPSILON_AMOUNT:
        classification = "增长"
    elif base_rate_impact < -EPSILON_AMOUNT:
        classification = "下降"
    else:
        classification = "持平"

    return {
        "pair_id": f"{raw.get('new_contract_no', '')}|{raw.get('group_code', '')}",
        "store_code": raw.get("store_code") or "",
        "store_name": raw.get("store_name") or "",
        "department_code": raw.get("department_code") or "",
        "department_name": raw.get("department_name") or "",
        "supplier_code": raw.get("supplier_code") or "",
        "supplier_name": raw.get("supplier_name") or "",
        "group_code": raw.get("group_code") or "",
        "group_name": raw.get("group_name") or "",
        "brand_name": raw.get("brand_name") or "",
        "old_contract_no": raw.get("old_contract_no") or "",
        "old_start_date": _date_text(raw.get("old_start_date")),
        "old_end_date": _date_text(raw.get("old_end_date")),
        "new_contract_no": raw.get("new_contract_no") or "",
        "new_start_date": _date_text(raw.get("new_start_date")),
        "new_end_date": _date_text(raw.get("new_end_date")),
        "gap_days": int(raw.get("gap_days") or 0),
        "old_contract_rate": _float(old_rate),
        "new_contract_rate": _float(new_rate),
        "contract_rate_delta": _float(rate_delta),
        "weighted_historical_base_rate": _float(weighted_base_rate),
        "weighted_historical_sales_rate": _float(weighted_sales_rate),
        "sales_row_count": sales_row_count,
        "activity_sales_row_count": int(raw.get("activity_sales_row_count") or 0),
        "sales_first_date": _date_text(raw.get("sales_first_date")),
        "sales_last_date": _date_text(raw.get("sales_last_date")),
        "sales_qty": _float(_decimal(raw.get("sales_qty"))),
        "priced_sales_amount": _float(priced_sales),
        "sales_revenue": _float(sales_revenue),
        "actual_gross_profit": _float(actual_profit),
        "historical_base_profit": _float(historical_base_profit),
        "historical_sales_rate_profit": _float(historical_sales_rate_profit),
        "activity_rate_impact": _float(_optional_decimal(raw.get("activity_rate_impact"))),
        "payment_and_other_residual": _float(payment_and_other_residual),
        "stored_card_amount": _float(_optional_decimal(raw.get("stored_card_amount"))),
        "stored_card_ratio": None,
        "voucher_amount": _float(_optional_decimal(raw.get("voucher_amount"))),
        "voucher_ratio": None,
        "member_discount_amount": _float(_optional_decimal(raw.get("member_discount_amount"))),
        "promotion_discount_amount": _float(_optional_decimal(raw.get("promotion_discount_amount"))),
        "recorded_payment_fee_amount": _float(_optional_decimal(raw.get("recorded_payment_fee_amount"))),
        "activity_payment_breakdown_available": False,
        "base_rate_impact": _float(base_rate_impact),
        "simulated_new_profit": _float(simulated_new_profit),
        "change_rate": _float(change_rate),
        "classification": classification,
        "review_required": bool(review_reasons),
        "review_reasons": review_reasons,
    }


def summarize_joint_renewal_items(items: list[dict[str, Any]]) -> dict[str, Any]:
    classifications = Counter(item["classification"] for item in items)
    return {
        "renewal_contract_count": len({item["new_contract_no"] for item in items}),
        "pair_count": len(items),
        "growth_count": classifications["增长"],
        "decline_count": classifications["下降"],
        "flat_count": classifications["持平"],
        "pending_review_count": classifications["待复核"],
        "review_flag_count": sum(1 for item in items if item["review_required"]),
        "priced_sales_amount": sum(item["priced_sales_amount"] or 0 for item in items),
        "actual_gross_profit": sum(item["actual_gross_profit"] or 0 for item in items),
        "base_rate_impact": sum(item["base_rate_impact"] or 0 for item in items),
        "simulated_new_profit": sum(item["simulated_new_profit"] or 0 for item in items),
    }


def load_joint_renewal_revenue_report(
    db: Session,
    *,
    start_date: date,
    end_date: date,
    scope: DataScope,
) -> dict[str, Any]:
    coverage = db.execute(
        text(
            "SELECT MIN(revenue_date)::date AS min_date, MAX(revenue_date)::date AS max_date "
            "FROM unit_revenue_sales_detail"
        )
    ).mappings().first()
    source_min_date = coverage.get("min_date") if coverage else None
    source_max_date = coverage.get("max_date") if coverage else None

    pair_rows = db.execute(
        text(PAIR_SQL),
        {"start_date": start_date, "end_date": end_date},
    ).mappings().all()
    scoped_pairs = [
        dict(row)
        for row in pair_rows
        if scope_allows_business(
            scope,
            store_id=row.get("store_code"),
            department_code=row.get("department_code"),
            department_name=row.get("department_name"),
            group_code=row.get("group_code"),
            supplier_code=row.get("supplier_code"),
            brand_name=row.get("brand_name"),
        )
    ]
    if scoped_pairs:
        sales_inputs = [
            {
                "pair_id": f"{row.get('new_contract_no', '')}|{row.get('group_code', '')}",
                "store_code": row.get("store_code") or "",
                "group_code": row.get("group_code") or "",
                "supplier_code": row.get("supplier_code") or "",
                "old_start_date": _date_text(row.get("old_start_date")),
                "old_end_date": _date_text(row.get("old_end_date")),
            }
            for row in scoped_pairs
        ]
        sales_rows = db.execute(
            text(SALES_SQL),
            {"pairs_json": json.dumps(sales_inputs, ensure_ascii=False)},
        ).mappings().all()
        sales_by_pair = {str(row["pair_id"]): dict(row) for row in sales_rows}
    else:
        sales_by_pair = {}

    scoped_rows = []
    for pair in scoped_pairs:
        pair_id = f"{pair.get('new_contract_no', '')}|{pair.get('group_code', '')}"
        pair.update(sales_by_pair.get(pair_id, {}))
        scoped_rows.append(pair)
    items = [
        calculate_joint_renewal_item(
            row,
            source_min_date=source_min_date,
            source_max_date=source_max_date,
        )
        for row in scoped_rows
    ]
    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "operation_method": "联营",
        "operation_method_code": "4",
        "source_coverage": {
            "sales_min_date": _date_text(source_min_date),
            "sales_max_date": _date_text(source_max_date),
            "sales_source": "unit_revenue_sales_detail",
        },
        "calculation_note": (
            "新合同模拟毛利=上一合同实际毛利+上一合同售价金额×(新合同扣率1-上一合同扣率1)。"
            "上一合同实际毛利保留历史活动扣率、付款方式、储值卡及其他结算影响；"
            "第一稿使用日汇总数据，不拆分重算这些规则。"
        ),
        "summary": summarize_joint_renewal_items(items),
        "items": items,
    }
