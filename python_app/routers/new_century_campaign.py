"""New Century campaign analysis dashboard API (market 603 only)."""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from models.database import get_db
from models.models import User
from routers.activity_analysis import _require_selected_activity_store
from routers.auth import get_current_user
from routers.authz import load_business_scope, require_permission
from services.new_century_campaign import (
    MARKET_CODE,
    PERMISSION_CODE,
    STORE_NAME,
    json_value,
    mask_member_no,
    mask_mobile,
    previous_year_period,
    safe_change_percent,
    safe_ratio,
    validate_period,
)


router = APIRouter(prefix="/api/activity-analysis/new-century", tags=["new-century-campaign"])


def _rows(db: Session, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {key: json_value(value) for key, value in row.items()}
        for row in db.execute(text(sql), params).mappings().all()
    ]


def _one(db: Session, sql: str, params: dict[str, Any]) -> dict[str, Any]:
    row = db.execute(text(sql), params).mappings().first()
    return {key: json_value(value) for key, value in row.items()} if row else {}


def _period_metrics(db: Session, start_date: date, end_date: date) -> dict[str, Any]:
    return _one(
        db,
        """
        WITH goods AS MATERIALIZED (
          SELECT sglbillno AS billno, SUM(COALESCE(sglxssr, 0)) AS sales_amount
          FROM salegoodslist
          WHERE sglmarket = :market_code
            AND sglhsrq BETWEEN :start_date AND :end_date
          GROUP BY sglbillno
        ),
        heads AS MATERIALIZED (
          SELECT
            h.billno,
            NULLIF(TRIM(COALESCE(h.hykh, '')), '') AS member_no
          FROM salehead h
          WHERE h.mkt = :market_code
            AND h.rqsj >= :start_date
            AND h.rqsj < CAST(:end_date AS date) + INTERVAL '1 day'
            AND COALESCE(h.djlb, '') NOT IN ('V', 'W', 'Y', 'Z')
        ),
        ticket_sales AS MATERIALIZED (
          SELECT h.billno, h.member_no, g.sales_amount
          FROM heads h JOIN goods g ON g.billno = h.billno
        ),
        new_members AS MATERIALIZED (
          SELECT DISTINCT NULLIF(TRIM(COALESCE(customer_no, '')), '') AS member_no
          FROM fj_dw_member_dim
          WHERE admission_date BETWEEN :start_date AND :end_date
            AND COALESCE(lead_store, '') LIKE '%新世纪%'
            AND NULLIF(TRIM(COALESCE(customer_no, '')), '') IS NOT NULL
        ),
        new_member_sales AS (
          SELECT DISTINCT t.billno, t.member_no, t.sales_amount
          FROM ticket_sales t
          JOIN new_members n ON n.member_no = t.member_no
        )
        SELECT
          COALESCE(SUM(t.sales_amount), 0) AS sales_amount,
          COUNT(t.billno) AS ticket_count,
          COALESCE(SUM(t.sales_amount) FILTER (WHERE t.member_no IS NOT NULL), 0) AS member_sales_amount,
          COUNT(t.billno) FILTER (WHERE t.member_no IS NOT NULL) AS member_ticket_count,
          COUNT(DISTINCT t.member_no) FILTER (WHERE t.member_no IS NOT NULL) AS consuming_member_count,
          (SELECT COUNT(*) FROM new_members) AS new_member_count,
          (SELECT COUNT(DISTINCT member_no) FROM new_member_sales) AS new_member_consuming_count,
          (SELECT COALESCE(SUM(sales_amount), 0) FROM new_member_sales) AS new_member_sales_amount
        FROM ticket_sales t
        """,
        {"market_code": MARKET_CODE, "start_date": start_date, "end_date": end_date},
    )


def _enrich_period(metrics: dict[str, Any]) -> dict[str, Any]:
    metrics["average_ticket"] = safe_ratio(metrics.get("sales_amount"), metrics.get("ticket_count"))
    metrics["member_average_ticket"] = safe_ratio(
        metrics.get("member_sales_amount"), metrics.get("member_ticket_count")
    )
    metrics["member_spend"] = safe_ratio(
        metrics.get("member_sales_amount"), metrics.get("consuming_member_count")
    )
    metrics["member_sales_share"] = safe_ratio(
        metrics.get("member_sales_amount"), metrics.get("sales_amount"), percent=True
    )
    metrics["new_member_conversion"] = safe_ratio(
        metrics.get("new_member_consuming_count"), metrics.get("new_member_count"), percent=True
    )
    return metrics


def _quality(db: Session) -> dict[str, Any]:
    result = _one(
        db,
        """
        WITH record_stats AS (
          SELECT
            COUNT(*) AS record_count,
            MAX(source_dt) AS max_source_dt,
            MAX(source_update_time) AS max_source_update_time,
            MAX(used_date_time) AS max_used_date_time,
            MAX(source_loaded_at) AS record_loaded_at
          FROM ods.crm_coupon_record_603
        ),
        template_stats AS (
          SELECT COUNT(*) AS template_count, MAX(source_loaded_at) AS template_loaded_at
          FROM ods.crm_coupon_template_603
        ),
        orphans AS (
          SELECT
            COUNT(*) AS orphan_record_count,
            COUNT(DISTINCT r.template_id) AS orphan_template_count,
            COUNT(*) FILTER (WHERE r.used_date_time IS NOT NULL) AS used_orphan_record_count
          FROM ods.crm_coupon_record_603 r
          LEFT JOIN ods.crm_coupon_template_603 t ON t.id = r.template_id
          WHERE t.id IS NULL
        )
        SELECT record_stats.*, template_stats.*, orphans.*
        FROM record_stats CROSS JOIN template_stats CROSS JOIN orphans
        """,
        {},
    )
    source_date_text = result.get("max_source_dt") or result.get("max_source_update_time")
    source_date = date.fromisoformat(str(source_date_text)[:10]) if source_date_text else None
    stale_days = (date.today() - source_date).days if source_date else None
    result["stale_days"] = stale_days
    result["status"] = "critical" if stale_days is None or stale_days > 1 else "warning" if stale_days == 1 else "ok"
    result["coverage_start"] = "2026-01-01"
    result["message"] = (
        f"CRM 卡券源数据已停滞 {stale_days} 天，礼品券结果可能缺失。"
        if stale_days is not None and stale_days > 1
        else "CRM 卡券源数据新鲜度正常。"
    )
    return result


def _daily_sales(db: Session, start_date: date, end_date: date) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        WITH goods AS MATERIALIZED (
          SELECT sglbillno AS billno, SUM(COALESCE(sglxssr, 0)) AS sales_amount
          FROM salegoodslist
          WHERE sglmarket = :market_code
            AND sglhsrq BETWEEN :start_date AND :end_date
          GROUP BY sglbillno
        ),
        heads AS MATERIALIZED (
          SELECT
            h.rqsj::date AS business_date,
            h.billno,
            NULLIF(TRIM(COALESCE(h.hykh, '')), '') AS member_no
          FROM salehead h
          WHERE h.mkt = :market_code
            AND h.rqsj >= :start_date
            AND h.rqsj < CAST(:end_date AS date) + INTERVAL '1 day'
            AND COALESCE(h.djlb, '') NOT IN ('V', 'W', 'Y', 'Z')
        ),
        ticket_sales AS MATERIALIZED (
          SELECT h.business_date, h.billno, h.member_no, g.sales_amount
          FROM heads h JOIN goods g ON g.billno = h.billno
        )
        SELECT
          d::date AS business_date,
          COALESCE(SUM(t.sales_amount), 0) AS sales_amount,
          COUNT(t.billno) AS ticket_count,
          COUNT(DISTINCT t.member_no) FILTER (WHERE t.member_no IS NOT NULL) AS member_count
        FROM generate_series(:start_date, :end_date, INTERVAL '1 day') d
        LEFT JOIN ticket_sales t ON t.business_date = d::date
        GROUP BY d::date
        ORDER BY d::date
        """,
        {"market_code": MARKET_CODE, "start_date": start_date, "end_date": end_date},
    )


def _recharge(db: Session, start_date: date, end_date: date, detail_limit: int) -> dict[str, Any]:
    params = {
        "market_code": MARKET_CODE,
        "start_date": start_date,
        "end_date": end_date,
        "detail_limit": detail_limit,
    }
    summary = _one(
        db,
        """
        WITH logs AS (
          SELECT
            l.tcflvipno AS member_no,
            l.tcflzy AS action_code,
            ABS(COALESCE(l.tcflmoney, 0)) AS face_amount
          FROM tktcardfqlog l
          WHERE l.tcflmkt = :market_code
            AND l.tcfldate BETWEEN :start_date AND :end_date
            AND (
              (l.tcflzy IN ('m', 'n') AND l.tcflsource IN ('2', '5'))
              OR (l.tcflzy IN ('M', 'N', 'w') AND l.tcflsource IN ('2', '8'))
            )
        )
        SELECT
          COUNT(*) AS flow_count,
          COUNT(DISTINCT NULLIF(TRIM(COALESCE(member_no, '')), '')) AS member_count,
          COALESCE(SUM(face_amount) FILTER (WHERE action_code IN ('m', 'M')), 0) AS increase_face_amount,
          COALESCE(SUM(face_amount) FILTER (WHERE action_code IN ('n', 'N', 'w')), 0) AS reversal_face_amount,
          COALESCE(SUM(CASE WHEN action_code IN ('m', 'M') THEN face_amount ELSE -face_amount END), 0) AS net_face_amount
        FROM logs
        """,
        params,
    )
    details = _rows(
        db,
        """
        SELECT
          l.tcflseqno AS sequence_no,
          l.tcfldate AS business_date,
          l.tcflvipno AS member_no,
          l.tcfltype AS coupon_type,
          COALESCE(q.tqname, NULLIF(TRIM(l.tcfltype), ''), '未定义券种') AS coupon_name,
          l.tcflzy AS action_code,
          CASE WHEN l.tcflzy IN ('m', 'M') THEN '增值' ELSE '冲正/退值' END AS action_name,
          l.tcflsource AS source_code,
          CASE l.tcflsource WHEN '2' THEN '前台买券' WHEN '5' THEN '券转入' WHEN '8' THEN '后台买券' ELSE '其他' END AS source_name,
          ABS(COALESCE(l.tcflmoney, 0)) AS face_amount
        FROM tktcardfqlog l
        LEFT JOIN tktqtype q ON q.tqcode = l.tcfltype
        WHERE l.tcflmkt = :market_code
          AND l.tcfldate BETWEEN :start_date AND :end_date
          AND (
            (l.tcflzy IN ('m', 'n') AND l.tcflsource IN ('2', '5'))
            OR (l.tcflzy IN ('M', 'N', 'w') AND l.tcflsource IN ('2', '8'))
          )
        ORDER BY l.tcfldate DESC, l.tcflseqno DESC
        LIMIT :detail_limit
        """,
        params,
    )
    for row in details:
        row["member_no"] = mask_member_no(row.get("member_no"))
    return {"summary": summary, "details": details}


def _gift_redemptions(db: Session, start_date: date, end_date: date, detail_limit: int) -> dict[str, Any]:
    params = {"start_date": start_date, "end_date": end_date, "market_code": MARKET_CODE, "detail_limit": detail_limit}
    ctes = """
      gift_rows AS MATERIALIZED (
        SELECT
          r.coupon_code,
          r.template_id,
          COALESCE(NULLIF(TRIM(t.name), ''), '未命名礼品券') AS gift_name,
          r.used_date_time,
          r.used_date_time::date AS used_date,
          r.mem_mobile,
          r.mem_name,
          r.level_code,
          r.coupon_money,
          regexp_replace(COALESCE(r.mem_mobile, ''), '[^0-9]', '', 'g') AS mobile_digits
        FROM ods.crm_coupon_record_603 r
        JOIN ods.crm_coupon_template_603 t ON t.id = r.template_id
        WHERE LOWER(COALESCE(t.coupon_type, '')) = 'gift'
          AND COALESCE(r.deleted, 0) <> 1
          AND r.used_date_time >= :start_date
          AND r.used_date_time < CAST(:end_date AS date) + INTERVAL '1 day'
      ),
      gift_mobiles AS MATERIALIZED (
        SELECT DISTINCT mobile_digits
        FROM gift_rows
        WHERE mobile_digits <> ''
      ),
      member_lookup AS MATERIALIZED (
        SELECT DISTINCT ON (g.mobile_digits)
          g.mobile_digits,
          m.customer_no
        FROM gift_mobiles g
        JOIN fj_dw_member_dim m
          ON regexp_replace(COALESCE(m.telephone, ''), '[^0-9]', '', 'g') = g.mobile_digits
        ORDER BY g.mobile_digits, m.admission_date DESC NULLS LAST, m.customer_no
      ),
      mapped_gifts AS MATERIALIZED (
        SELECT g.*, member.customer_no
        FROM gift_rows g
        LEFT JOIN member_lookup member ON member.mobile_digits = g.mobile_digits
      ),
      goods AS MATERIALIZED (
        SELECT sglbillno AS billno, SUM(COALESCE(sglxssr, 0)) AS sales_amount
        FROM salegoodslist
        WHERE sglmarket = :market_code
          AND sglhsrq BETWEEN :start_date AND :end_date
        GROUP BY sglbillno
      ),
      heads AS MATERIALIZED (
        SELECT
          h.rqsj::date AS business_date,
          NULLIF(TRIM(COALESCE(h.hykh, '')), '') AS member_no,
          h.billno
        FROM salehead h
        WHERE h.mkt = :market_code
          AND h.rqsj >= :start_date
          AND h.rqsj < CAST(:end_date AS date) + INTERVAL '1 day'
          AND COALESCE(h.djlb, '') NOT IN ('V', 'W', 'Y', 'Z')
      ),
      ticket_sales AS MATERIALIZED (
        SELECT h.business_date, h.member_no, h.billno, g.sales_amount
        FROM heads h JOIN goods g ON g.billno = h.billno
      ),
      member_day_sales AS (
        SELECT business_date, member_no, COUNT(*) AS ticket_count, SUM(sales_amount) AS sales_amount
        FROM ticket_sales
        WHERE member_no IS NOT NULL
        GROUP BY business_date, member_no
      ),
      enriched AS (
        SELECT
          g.*,
          COALESCE(s.ticket_count, 0) AS same_day_ticket_count,
          COALESCE(s.sales_amount, 0) AS same_day_sales_amount
        FROM mapped_gifts g
        LEFT JOIN member_day_sales s ON s.business_date = g.used_date AND s.member_no = g.customer_no
      )
    """
    summary = _one(
        db,
        f"""
        WITH {ctes}, member_days AS (
          SELECT
            COALESCE(NULLIF(customer_no, ''), NULLIF('MOBILE:' || mobile_digits, 'MOBILE:'), 'COUPON:' || coupon_code::text) AS member_key,
            used_date,
            MAX(same_day_ticket_count) AS ticket_count,
            MAX(same_day_sales_amount) AS sales_amount
          FROM enriched
          GROUP BY COALESCE(NULLIF(customer_no, ''), NULLIF('MOBILE:' || mobile_digits, 'MOBILE:'), 'COUPON:' || coupon_code::text), used_date
        )
        SELECT
          (SELECT COUNT(*) FROM enriched) AS redemption_count,
          COUNT(*) AS member_day_count,
          COUNT(DISTINCT member_key) AS unique_member_count,
          COUNT(*) FILTER (WHERE ticket_count > 0) AS consuming_member_day_count,
          COALESCE(SUM(ticket_count), 0) AS same_day_ticket_count,
          COALESCE(SUM(sales_amount), 0) AS same_day_sales_amount,
          (SELECT COUNT(*) FILTER (WHERE customer_no IS NULL) FROM enriched) AS unmatched_redemption_count
        FROM member_days
        """,
        params,
    )
    summary["conversion_rate"] = safe_ratio(summary.get("consuming_member_day_count"), summary.get("member_day_count"), percent=True)
    summary["spend_per_consumer"] = safe_ratio(summary.get("same_day_sales_amount"), summary.get("consuming_member_day_count"))

    daily = _rows(
        db,
        f"""
        WITH {ctes}, member_days AS (
          SELECT COALESCE(NULLIF(customer_no, ''), NULLIF('MOBILE:' || mobile_digits, 'MOBILE:'), 'COUPON:' || coupon_code::text) AS member_key,
                 used_date, MAX(same_day_ticket_count) AS ticket_count, MAX(same_day_sales_amount) AS sales_amount
          FROM enriched
          GROUP BY COALESCE(NULLIF(customer_no, ''), NULLIF('MOBILE:' || mobile_digits, 'MOBILE:'), 'COUPON:' || coupon_code::text), used_date
        )
        SELECT d::date AS business_date,
               COUNT(DISTINCT e.coupon_code) AS redemption_count,
               COUNT(DISTINCT md.member_key) AS member_day_count,
               COUNT(DISTINCT md.member_key) FILTER (WHERE md.ticket_count > 0) AS consuming_member_day_count,
               COALESCE(SUM(md.sales_amount), 0) AS same_day_sales_amount
        FROM generate_series(:start_date, :end_date, INTERVAL '1 day') d
        LEFT JOIN enriched e ON e.used_date = d::date
        LEFT JOIN member_days md ON md.used_date = d::date
        GROUP BY d::date ORDER BY d::date
        """,
        params,
    )
    # The two independent one-to-many joins above can multiply sums; correct the daily
    # amounts from member-day grain in a second lightweight aggregate.
    daily_sales = _rows(
        db,
        f"""WITH {ctes}, member_days AS (
          SELECT COALESCE(NULLIF(customer_no, ''), NULLIF('MOBILE:' || mobile_digits, 'MOBILE:'), 'COUPON:' || coupon_code::text) AS member_key,
                 used_date, MAX(same_day_ticket_count) AS ticket_count, MAX(same_day_sales_amount) AS sales_amount
          FROM enriched GROUP BY COALESCE(NULLIF(customer_no, ''), NULLIF('MOBILE:' || mobile_digits, 'MOBILE:'), 'COUPON:' || coupon_code::text), used_date
        ) SELECT used_date AS business_date, COUNT(*) AS member_day_count,
          COUNT(*) FILTER (WHERE ticket_count > 0) AS consuming_member_day_count,
          COALESCE(SUM(sales_amount), 0) AS same_day_sales_amount
        FROM member_days GROUP BY used_date""",
        params,
    )
    daily_sales_by_date = {row["business_date"]: row for row in daily_sales}
    for row in daily:
        corrected = daily_sales_by_date.get(row["business_date"], {})
        row.update({key: corrected.get(key, 0) for key in ("member_day_count", "consuming_member_day_count", "same_day_sales_amount")})

    templates = _rows(
        db,
        f"""
        WITH {ctes}
        SELECT template_id, gift_name, COUNT(*) AS redemption_count,
               COUNT(DISTINCT COALESCE(NULLIF(customer_no, ''), NULLIF('MOBILE:' || mobile_digits, 'MOBILE:'), 'COUPON:' || coupon_code::text)) AS member_count,
               COUNT(*) FILTER (WHERE same_day_ticket_count > 0) AS consuming_redemption_count
        FROM enriched GROUP BY template_id, gift_name ORDER BY redemption_count DESC, gift_name
        """,
        params,
    )
    details = _rows(
        db,
        f"""
        WITH {ctes}
        SELECT coupon_code, template_id, gift_name, used_date_time, mem_mobile, mem_name, level_code,
               customer_no, coupon_money, same_day_ticket_count, same_day_sales_amount
        FROM enriched ORDER BY used_date_time DESC, coupon_code DESC LIMIT :detail_limit
        """,
        params,
    )
    for row in details:
        row["coupon_code"] = mask_member_no(row.get("coupon_code"))
        row["member_no"] = mask_member_no(row.pop("customer_no", None))
        row["mobile"] = mask_mobile(row.pop("mem_mobile", None))
        row.pop("mem_name", None)
    return {"summary": summary, "daily": daily, "templates": templates, "details": details}


@router.get("/dashboard")
async def dashboard(
    start_date: date = Query(...),
    end_date: date = Query(...),
    compare_start_date: date | None = Query(None),
    compare_end_date: date | None = Query(None),
    detail_limit: int = Query(500, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, PERMISSION_CODE)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    _require_selected_activity_store(db, scope, MARKET_CODE)

    if compare_start_date is None or compare_end_date is None:
        compare_start_date, compare_end_date = previous_year_period(start_date, end_date)
    try:
        validate_period(start_date, end_date, label="活动期")
        validate_period(compare_start_date, compare_end_date, label="同期")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    current = _enrich_period(_period_metrics(db, start_date, end_date))
    comparison = _enrich_period(_period_metrics(db, compare_start_date, compare_end_date))
    change = {
        key: safe_change_percent(current.get(key), comparison.get(key))
        for key in (
            "sales_amount",
            "ticket_count",
            "average_ticket",
            "member_sales_amount",
            "consuming_member_count",
            "member_spend",
            "new_member_count",
            "new_member_conversion",
        )
    }
    return {
        "scope": {
            "store_code": MARKET_CODE,
            "store_name": STORE_NAME,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "compare_start_date": compare_start_date.isoformat(),
            "compare_end_date": compare_end_date.isoformat(),
        },
        "quality": _quality(db),
        "overview": {"current": current, "comparison": comparison, "change_percent": change},
        "daily_sales": _daily_sales(db, start_date, end_date),
        "recharge": _recharge(db, start_date, end_date, detail_limit),
        "gift_redemption": _gift_redemptions(db, start_date, end_date, detail_limit),
        "definitions": {
            "sales": "603 门店有效小票的商品行销售收入；退货按商品行符号计入。",
            "member": "小票会员号非空；会员人数按活动期去重。",
            "recharge": "卡券日志 m/M 为增值，n/N/w 为冲正或退值，按日志面值统计。",
            "gift": "CRM gift 类型核销记录按手机号映射会员号，再关联 603 门店同日消费。",
        },
    }
