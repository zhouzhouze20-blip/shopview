"""Reference sales-lift estimate for an archived coupon campaign.

This stays separate from coupon settlement. It uses the frozen ERP rule batch
to identify the participating sales scope, compares the activity dates with
the same weekdays in the prior four weeks, then applies a period-level control
factor from same-department, non-participating counter groups.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import text


BASELINE_WEEKS = 4


LIFT_SQL = """
WITH rules AS MATERIALIZED (
  SELECT r.*
  FROM ods.gpp_tktgoodsyqrate r
  JOIN ods.gpp_tktbgoodsfqhead h
    ON h.batch_id=r.batch_id AND h.tbfhbillno=r.tgyrbillno
  WHERE r.batch_id=:batch_id AND r.tgyrpid=:erp_activity_id
    AND h.tbfhmkt=:store_code AND h.tbfhflag='Y'
    AND r.tgyrqtype=ANY(CAST(:coupon_types AS text[]))
    AND r.tgyrstartdate<:end_exclusive AND r.tgyrenddate>=:start_date
), group_scope AS MATERIALIZED (
  -- ERP mode 2 is a combination/counter-group rule.
  SELECT DISTINCT TRIM(tgyrmfid) group_code
  FROM rules
  WHERE tgyrmode='2' AND NULLIF(TRIM(tgyrmfid),'') IS NOT NULL
    AND TRIM(tgyrmfid)<>'ALL'
), item_scope_specific AS MATERIALIZED (
  -- ERP mode 1 is an item rule. Keep its counter restriction when present.
  SELECT DISTINCT TRIM(tgyrmfid) group_code,TRIM(tgyrbarcode) barcode
  FROM rules
  WHERE tgyrmode='1' AND NULLIF(TRIM(tgyrbarcode),'') IS NOT NULL
    AND TRIM(tgyrbarcode)<>'ALL' AND NULLIF(TRIM(tgyrmfid),'') IS NOT NULL
    AND TRIM(tgyrmfid)<>'ALL'
), item_scope_any_group AS MATERIALIZED (
  SELECT DISTINCT TRIM(tgyrbarcode) barcode
  FROM rules
  WHERE tgyrmode='1' AND NULLIF(TRIM(tgyrbarcode),'') IS NOT NULL
    AND TRIM(tgyrbarcode)<>'ALL'
    AND COALESCE(NULLIF(TRIM(tgyrmfid),''),'ALL')='ALL'
), treatment_groups AS MATERIALIZED (
  SELECT group_code FROM group_scope
  UNION
  SELECT group_code FROM item_scope_specific
), treatment_departments AS MATERIALIZED (
  SELECT DISTINCT cg.department_code
  FROM counter_groups cg
  JOIN stores st ON st.store_id=cg.store_id AND st.store_code=:store_code
  JOIN treatment_groups t ON t.group_code=TRIM(cg.group_code)
  WHERE NULLIF(TRIM(cg.department_code),'') IS NOT NULL
), comparison_dates AS MATERIALIZED (
  -- Match every activity date to the same weekday in each prior week.
  SELECT activity_date::date activity_date,
    (activity_date::date-(week_no*7))::date comparison_date
  FROM generate_series(CAST(:start_date AS date),CAST(:end_date AS date),INTERVAL '1 day') activity_date
  CROSS JOIN generate_series(1,:baseline_weeks) week_no
), daily_segments AS MATERIALIZED (
  SELECT s.sgldate,
    CASE
      WHEN gs.group_code IS NOT NULL OR isp.barcode IS NOT NULL OR ia.barcode IS NOT NULL
        THEN 'treatment'
      -- Exclude an item-only participating counter from control in full.
      WHEN tg.group_code IS NULL AND d.department_code IS NOT NULL THEN 'control'
    END segment,
    SUM(COALESCE(s.sglxssr,0)) sales
  FROM salegoodslist s
  LEFT JOIN group_scope gs ON gs.group_code=TRIM(s.sglmfid)
  LEFT JOIN item_scope_specific isp
    ON isp.group_code=TRIM(s.sglmfid) AND isp.barcode=TRIM(s.sglbarcode)
  LEFT JOIN item_scope_any_group ia ON ia.barcode=TRIM(s.sglbarcode)
  LEFT JOIN treatment_groups tg ON tg.group_code=TRIM(s.sglmfid)
  LEFT JOIN counter_groups cg ON TRIM(cg.group_code)=TRIM(s.sglmfid)
  LEFT JOIN stores st ON st.store_id=cg.store_id AND st.store_code=:store_code
  LEFT JOIN treatment_departments d ON d.department_code=cg.department_code
  WHERE s.sglmarket=:store_code
    AND s.sgldate>=:baseline_start AND s.sgldate<:end_exclusive
    AND (
      gs.group_code IS NOT NULL OR isp.barcode IS NOT NULL OR ia.barcode IS NOT NULL
      OR (tg.group_code IS NULL AND d.department_code IS NOT NULL)
    )
  GROUP BY s.sgldate,segment
), daily AS MATERIALIZED (
  SELECT sgldate,
    COALESCE(SUM(sales) FILTER(WHERE segment='treatment'),0) treatment_sales,
    COALESCE(SUM(sales) FILTER(WHERE segment='control'),0) control_sales
  FROM daily_segments
  WHERE segment IS NOT NULL
  GROUP BY sgldate
), totals AS (
  SELECT
    COALESCE(SUM(treatment_sales) FILTER(WHERE sgldate>=:start_date),0) treatment_actual,
    COALESCE(SUM(control_sales) FILTER(WHERE sgldate>=:start_date),0) control_actual,
    COALESCE((
      SELECT SUM(d.treatment_sales)
      FROM daily d JOIN comparison_dates c ON c.comparison_date=d.sgldate
    ),0)/:baseline_weeks treatment_baseline,
    COALESCE((
      SELECT SUM(d.control_sales)
      FROM daily d JOIN comparison_dates c ON c.comparison_date=d.sgldate
    ),0)/:baseline_weeks control_baseline
  FROM daily
), scope_stats AS (
  SELECT
    (SELECT COUNT(*) FROM treatment_groups) treatment_group_count,
    (SELECT COUNT(*) FROM treatment_groups t WHERE EXISTS (
      SELECT 1 FROM counter_groups cg JOIN stores st ON st.store_id=cg.store_id
      WHERE st.store_code=:store_code AND TRIM(cg.group_code)=t.group_code
    )) mapped_treatment_group_count,
    (SELECT COUNT(*) FROM treatment_departments) department_count,
    (SELECT COUNT(*) FROM counter_groups cg
      JOIN stores st ON st.store_id=cg.store_id AND st.store_code=:store_code
      JOIN treatment_departments d ON d.department_code=cg.department_code
      WHERE NOT EXISTS (
        SELECT 1 FROM treatment_groups t WHERE t.group_code=TRIM(cg.group_code)
      )) control_group_count
)
SELECT totals.*,scope_stats.* FROM totals CROSS JOIN scope_stats
"""


def _decimal(value) -> Decimal:
    return Decimal(str(value or 0))


def _period_fields(start_date, end_date, baseline_weeks):
    if start_date is None or end_date is None:
        return {}
    start = start_date if isinstance(start_date, date) else date.fromisoformat(str(start_date))
    end = end_date if isinstance(end_date, date) else date.fromisoformat(str(end_date))
    return {
        "activity_start_date": start.isoformat(),
        "activity_end_date": end.isoformat(),
        "baseline_periods": [
            {
                "week_no": week_no,
                "start_date": (start - timedelta(days=7 * week_no)).isoformat(),
                "end_date": (end - timedelta(days=7 * week_no)).isoformat(),
            }
            for week_no in range(1, baseline_weeks + 1)
        ],
    }


def unavailable(reason: str, *, baseline_weeks: int = BASELINE_WEEKS, start_date=None, end_date=None):
    return {
        "status": "unavailable",
        "reason": reason,
        "baseline_weeks": baseline_weeks,
        "method": "前4周同星期参与范围基准 + 同部门非参与柜组期间校准",
        **_period_fields(start_date, end_date, baseline_weeks),
    }


def build_lift_estimate(
    row, *, baseline_weeks=BASELINE_WEEKS, day_count=0, batch_id="",
    start_date=None, end_date=None,
):
    """Calculate the reference estimate without claiming causal attribution."""
    if not row or int(row.get("treatment_group_count") or 0) <= 0:
        return unavailable(
            "ERP规则快照没有可识别的参与柜组范围", baseline_weeks=baseline_weeks,
            start_date=start_date, end_date=end_date,
        )
    treatment_actual = _decimal(row.get("treatment_actual"))
    treatment_baseline = _decimal(row.get("treatment_baseline"))
    control_actual = _decimal(row.get("control_actual"))
    control_baseline = _decimal(row.get("control_baseline"))
    if treatment_baseline <= 0:
        return unavailable(
            "参与范围缺少历史同星期销售基准", baseline_weeks=baseline_weeks,
            start_date=start_date, end_date=end_date,
        )
    if control_baseline <= 0:
        return unavailable(
            "同部门非参与对照范围缺少可用销售基准", baseline_weeks=baseline_weeks,
            start_date=start_date, end_date=end_date,
        )
    control_factor = control_actual / control_baseline
    expected_sales = treatment_baseline * control_factor
    estimated_increment = treatment_actual - expected_sales
    growth_rate = estimated_increment / expected_sales * 100 if expected_sales else None
    raw_change_rate = (treatment_actual - treatment_baseline) / treatment_baseline * 100
    control_change_rate = (control_actual - control_baseline) / control_baseline * 100
    group_count = int(row.get("treatment_group_count") or 0)
    mapped_count = int(row.get("mapped_treatment_group_count") or 0)
    caveats = [
        "试算值不是结算结果，也不能单独证明活动因果增量。",
        "往期活动未建档，前4周同星期可能包含未识别促销。",
        "对照范围为同部门非参与柜组；全店活动客流可能同时影响对照范围。",
        "活动后退货暂不回溯调整本档。",
    ]
    if mapped_count < group_count:
        caveats.append(f"{group_count-mapped_count}个参与柜组未映射到部门，对照校准未覆盖这些柜组的部门关系。")
    return {
        "status": "estimated",
        "method": "前4周同星期参与范围基准 + 同部门非参与柜组期间校准",
        "baseline_weeks": baseline_weeks,
        "day_count": day_count,
        "rule_batch_id": batch_id,
        "treatment_group_count": group_count,
        "mapped_treatment_group_count": mapped_count,
        "department_count": int(row.get("department_count") or 0),
        "control_group_count": int(row.get("control_group_count") or 0),
        "actual_sales": treatment_actual,
        "same_weekday_baseline_sales": treatment_baseline,
        "raw_change_rate": raw_change_rate,
        "control_actual_sales": control_actual,
        "control_baseline_sales": control_baseline,
        "control_change_rate": control_change_rate,
        "control_factor": control_factor,
        "expected_sales": expected_sales,
        "estimated_increment": estimated_increment,
        "estimated_growth_rate": growth_rate,
        "caveats": caveats,
        **_period_fields(start_date, end_date, baseline_weeks),
    }


def query_sales_lift(db, config, *, baseline_weeks=BASELINE_WEEKS):
    start = date.fromisoformat(str(config["start_date"]))
    end = date.fromisoformat(str(config["end_date"]))
    snapshot = config.get("rule_snapshot") or {}
    batch_id = str(snapshot.get("ods_batch_id") or "").strip()
    erp_activity_id = str(config.get("erp_activity_id") or "").strip()
    if not batch_id:
        return unavailable(
            "请先读取并冻结ERP收券规则快照", baseline_weeks=baseline_weeks,
            start_date=start, end_date=end,
        )
    if not erp_activity_id:
        return unavailable(
            "活动尚未关联ERP档期", baseline_weeks=baseline_weeks,
            start_date=start, end_date=end,
        )
    params = {
        "batch_id": batch_id,
        "erp_activity_id": erp_activity_id,
        "store_code": str(config["store_code"]),
        "coupon_types": list(config["coupon_types"]),
        "start_date": start,
        "end_date": end,
        "end_exclusive": end + timedelta(days=1),
        "baseline_start": start - timedelta(days=7 * baseline_weeks),
        "baseline_weeks": baseline_weeks,
    }
    row = db.execute(text(LIFT_SQL), params).mappings().one()
    return build_lift_estimate(
        dict(row), baseline_weeks=baseline_weeks,
        day_count=(end - start).days + 1, batch_id=batch_id,
        start_date=start, end_date=end,
    )
