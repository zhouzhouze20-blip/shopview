"""
活动分析 API

一期口径：只分析卡券使用。活动由 tktpopinfo 定义，卡券日志取 tktcardfqlog，
卡券付款取 salepay 中 0500/0580，销售、成本、毛利取 salegoodslist。
"""

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from models.database import get_db
from models.models import User
from routers.auth import get_current_user
from routers.authz import require_permission


router = APIRouter(prefix="/api/activity-analysis", tags=["activity-analysis"])


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _rows(db: Session, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    rows = db.execute(text(sql), params).mappings().all()
    return [{key: _json_value(value) for key, value in row.items()} for row in rows]


def _one(db: Session, sql: str, params: dict[str, Any]) -> dict[str, Any]:
    row = db.execute(text(sql), params).mappings().first()
    if row is None:
        return {}
    return {key: _json_value(value) for key, value in row.items()}


def _table_exists(db: Session, table_name: str) -> bool:
    row = db.execute(
        text(
            """
            SELECT EXISTS (
              SELECT 1
              FROM information_schema.tables
              WHERE table_schema = 'public' AND table_name = :table_name
            ) AS ok
            """
        ),
        {"table_name": table_name},
    ).fetchone()
    return bool(row.ok) if row is not None else False


def _ensure_required_tables(db: Session) -> None:
    missing = [
        table
        for table in [
            "tktpopinfo",
            "tktcardfqlog",
            "salehead",
            "salepay",
            "salegoodslist",
            "fj_dw_member_dim",
        ]
        if not _table_exists(db, table)
    ]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"活动分析所需数据表未创建: {', '.join(missing)}",
        )


def _activity_filter(activity_id: str | None, start_date: str | None, end_date: str | None) -> tuple[str, dict[str, Any]]:
    params: dict[str, Any] = {}
    clauses: list[str] = ["COALESCE(l.tcflpopid, '') <> '0'"]
    if activity_id:
        clauses.append("l.tcflpopid = :activity_id")
        params["activity_id"] = activity_id.strip()
    else:
        if start_date:
            clauses.append("l.tcfldate >= :start_date")
            params["start_date"] = start_date
        if end_date:
            clauses.append("l.tcfldate <= :end_date")
            params["end_date"] = end_date
    return " AND ".join(clauses), params


def _period_filter(activity_id: str | None, start_date: str | None, end_date: str | None) -> tuple[str, dict[str, Any]]:
    params: dict[str, Any] = {}
    if activity_id:
        params["activity_id"] = activity_id.strip()
        return (
            """
            h.rqsj::date BETWEEN
              COALESCE((SELECT tpistartdate FROM tktpopinfo WHERE tpiid = :activity_id), DATE '1900-01-01')
              AND
              COALESCE((SELECT tpienddate FROM tktpopinfo WHERE tpiid = :activity_id), DATE '2999-12-31')
            """,
            params,
        )
    clauses: list[str] = ["1=1"]
    if start_date:
        clauses.append("h.rqsj::date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        clauses.append("h.rqsj::date <= :end_date")
        params["end_date"] = end_date
    return " AND ".join(clauses), params


@router.get("/activities")
async def activities(
    start_date: str | None = Query(None, description="活动开始日期下限 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="活动结束日期上限 YYYY-MM-DD"),
    keyword: str | None = Query(None, description="活动编码/主题"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "sales.view")
    _ensure_required_tables(db)

    params: dict[str, Any] = {"limit": limit}
    filters: list[str] = ["1=1"]
    if start_date:
        filters.append("p.tpienddate >= :start_date")
        params["start_date"] = start_date
    if end_date:
        filters.append("p.tpistartdate <= :end_date")
        params["end_date"] = end_date
    if keyword:
        filters.append("(p.tpiid ILIKE :keyword OR p.tpiname ILIKE :keyword)")
        params["keyword"] = f"%{keyword.strip()}%"

    return _rows(
        db,
        f"""
        WITH log_bill AS (
          SELECT
            l.tcflpopid AS activity_id,
            h.billno,
            SUM(COALESCE(l.tcflmoney, 0)) AS log_amount,
            COUNT(*) AS log_count
          FROM tktcardfqlog l
          JOIN salehead h
            ON l.tcflmkt = h.mkt
           AND l.tcflsyjid = h.syjh
           AND l.tcflinvno ~ '^[0-9]+$'
           AND h.fphm = l.tcflinvno::numeric
          WHERE COALESCE(l.tcflpopid, '') <> '0'
          GROUP BY l.tcflpopid, h.billno
        ),
        pay_bill AS (
          SELECT billno, SUM(COALESCE(je, 0)) AS coupon_pay_amount
          FROM salepay
          WHERE paycode IN ('0500', '0580')
          GROUP BY billno
        )
        SELECT
          p.tpiid AS activity_id,
          p.tpiname AS activity_name,
          p.tpistartdate AS start_date,
          p.tpienddate AS end_date,
          COALESCE(COUNT(DISTINCT lb.billno), 0) AS ticket_count,
          COALESCE(SUM(lb.log_amount), 0) AS card_log_amount,
          COALESCE(SUM(pb.coupon_pay_amount), 0) AS coupon_pay_amount
        FROM tktpopinfo p
        LEFT JOIN log_bill lb ON lb.activity_id = p.tpiid
        LEFT JOIN pay_bill pb ON pb.billno = lb.billno
        WHERE {" AND ".join(filters)}
        GROUP BY p.tpiid, p.tpiname, p.tpistartdate, p.tpienddate
        ORDER BY p.tpistartdate DESC NULLS LAST, p.tpiid DESC
        LIMIT :limit
        """,
        params,
    )


@router.get("/overview")
async def overview(
    activity_id: str | None = Query(None, description="活动档期编码 tktpopinfo.tpiid"),
    start_date: str | None = Query(None, description="日志日期起 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="日志日期止 YYYY-MM-DD"),
    limit: int = Query(20, ge=5, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "sales.view")
    _ensure_required_tables(db)

    log_filter, log_params = _activity_filter(activity_id, start_date, end_date)
    period_filter, period_params = _period_filter(activity_id, start_date, end_date)
    params = {**log_params, **period_params, "limit": limit}

    activity = None
    if activity_id:
        activity = _one(
            db,
            """
            SELECT
              tpiid AS activity_id,
              tpiname AS activity_name,
              tpistartdate AS start_date,
              tpienddate AS end_date,
              tpiyqstartdate AS coupon_start_date,
              tpiyqenddate AS coupon_end_date,
              tpmemo AS memo
            FROM tktpopinfo
            WHERE tpiid = :activity_id
            """,
            {"activity_id": activity_id.strip()},
        )

    summary = _one(
        db,
        f"""
        WITH raw_logs AS (
          SELECT l.*
          FROM tktcardfqlog l
          WHERE {log_filter}
        ),
        matched_logs AS (
          SELECT
            l.*,
            h.billno,
            h.hykh,
            h.hycid,
            h.rqsj AS sale_time,
            h.ybillno,
            h.ysyjh,
            h.yfphm
          FROM raw_logs l
          JOIN salehead h
            ON l.tcflmkt = h.mkt
           AND l.tcflsyjid = h.syjh
           AND l.tcflinvno ~ '^[0-9]+$'
           AND h.fphm = l.tcflinvno::numeric
        ),
        log_bill AS (
          SELECT
            billno,
            MIN(hykh) AS member_no,
            COUNT(*) AS log_count,
            SUM(COALESCE(tcflmoney, 0)) AS card_log_amount
          FROM matched_logs
          GROUP BY billno
        ),
        pay_bill AS (
          SELECT
            p.billno,
            SUM(CASE WHEN p.paycode = '0500' THEN COALESCE(p.je, 0) ELSE 0 END) AS pay_0500_amount,
            SUM(CASE WHEN p.paycode = '0580' THEN COALESCE(p.je, 0) ELSE 0 END) AS pay_0580_amount,
            SUM(COALESCE(p.je, 0)) AS coupon_pay_amount,
            COUNT(*) AS coupon_pay_count
          FROM salepay p
          JOIN log_bill lb ON lb.billno = p.billno
          WHERE p.paycode IN ('0500', '0580')
          GROUP BY p.billno
        ),
        sales_bill AS (
          SELECT
            s.sglbillno AS billno,
            SUM(COALESCE(s.sglxssr, 0)) AS sales_amount,
            SUM(COALESCE(s.sgln13, 0)) AS sales_cost,
            SUM(COALESCE(s.sgln2, 0)) AS gross_profit,
            SUM(COALESCE(s.sglnetml, s.sgln2, 0)) AS net_profit,
            SUM(COALESCE(s.sglsqje, 0)) AS received_coupon_amount,
            SUM(COALESCE(s.sglfqje, 0)) AS issued_coupon_amount,
            SUM(COALESCE(s.sglthss, 0)) AS return_loss,
            SUM(COALESCE(s.sglsl, 0)) AS quantity
          FROM salegoodslist s
          JOIN log_bill lb ON lb.billno = s.sglbillno
          GROUP BY s.sglbillno
        ),
        period_pay AS (
          SELECT
            COUNT(*) AS period_coupon_pay_count,
            SUM(COALESCE(p.je, 0)) AS period_coupon_pay_amount
          FROM salepay p
          JOIN salehead h ON h.billno = p.billno
          WHERE p.paycode IN ('0500', '0580')
            AND {period_filter}
        )
        SELECT
          COUNT(DISTINCT lb.billno) AS ticket_count,
          COUNT(DISTINCT NULLIF(lb.member_no, '')) AS member_count,
          COALESCE(SUM(lb.log_count), 0) AS card_log_count,
          COALESCE(SUM(lb.card_log_amount), 0) AS card_log_amount,
          COALESCE(SUM(pb.coupon_pay_count), 0) AS coupon_pay_count,
          COALESCE(SUM(pb.coupon_pay_amount), 0) AS coupon_pay_amount,
          COALESCE(SUM(pb.pay_0500_amount), 0) AS pay_0500_amount,
          COALESCE(SUM(pb.pay_0580_amount), 0) AS pay_0580_amount,
          COALESCE(SUM(sb.sales_amount), 0) AS sales_amount,
          COALESCE(SUM(sb.sales_cost), 0) AS sales_cost,
          COALESCE(SUM(sb.gross_profit), 0) AS gross_profit,
          COALESCE(SUM(sb.net_profit), 0) AS net_profit,
          COALESCE(SUM(sb.received_coupon_amount), 0) AS received_coupon_amount,
          COALESCE(SUM(sb.issued_coupon_amount), 0) AS issued_coupon_amount,
          COALESCE(SUM(sb.return_loss), 0) AS return_loss,
          COALESCE(SUM(sb.quantity), 0) AS quantity,
          MAX(pp.period_coupon_pay_count) AS period_coupon_pay_count,
          MAX(pp.period_coupon_pay_amount) AS period_coupon_pay_amount
        FROM log_bill lb
        LEFT JOIN pay_bill pb ON pb.billno = lb.billno
        LEFT JOIN sales_bill sb ON sb.billno = lb.billno
        CROSS JOIN period_pay pp
        """,
        params,
    )

    payment_methods = _rows(
        db,
        f"""
        WITH matched_bills AS (
          SELECT DISTINCT h.billno
          FROM tktcardfqlog l
          JOIN salehead h
            ON l.tcflmkt = h.mkt
           AND l.tcflsyjid = h.syjh
           AND l.tcflinvno ~ '^[0-9]+$'
           AND h.fphm = l.tcflinvno::numeric
          WHERE {log_filter}
        )
        SELECT
          p.paycode,
          COALESCE(NULLIF(p.payname, ''), '未命名') AS payname,
          COUNT(*) AS payment_count,
          SUM(COALESCE(p.je, 0)) AS payment_amount
        FROM salepay p
        JOIN matched_bills mb ON mb.billno = p.billno
        WHERE p.paycode IN ('0500', '0580')
        GROUP BY p.paycode, COALESCE(NULLIF(p.payname, ''), '未命名')
        ORDER BY payment_amount DESC
        LIMIT :limit
        """,
        params,
    )

    departments = _rows(
        db,
        f"""
        WITH matched_bills AS (
          SELECT DISTINCT h.billno
          FROM tktcardfqlog l
          JOIN salehead h
            ON l.tcflmkt = h.mkt
           AND l.tcflsyjid = h.syjh
           AND l.tcflinvno ~ '^[0-9]+$'
           AND h.fphm = l.tcflinvno::numeric
          WHERE {log_filter}
        )
        SELECT
          COALESCE(NULLIF(cg.department_code, ''), '未归属') AS department_code,
          COALESCE(NULLIF(cg.department_name, ''), '未归属部门') AS department_name,
          COUNT(DISTINCT s.sglbillno) AS ticket_count,
          SUM(COALESCE(s.sglxssr, 0)) AS sales_amount,
          SUM(COALESCE(s.sgln13, 0)) AS sales_cost,
          SUM(COALESCE(s.sgln2, 0)) AS gross_profit,
          SUM(COALESCE(s.sglnetml, s.sgln2, 0)) AS net_profit,
          SUM(COALESCE(s.sglsqje, 0)) AS received_coupon_amount,
          SUM(COALESCE(s.sglfqje, 0)) AS issued_coupon_amount
        FROM salegoodslist s
        JOIN matched_bills mb ON mb.billno = s.sglbillno
        LEFT JOIN counter_groups cg ON UPPER(TRIM(COALESCE(cg.group_code, ''))) = UPPER(TRIM(COALESCE(s.sglmfid, '')))
        GROUP BY 1, 2
        ORDER BY sales_amount DESC
        LIMIT :limit
        """,
        params,
    )

    products = _rows(
        db,
        f"""
        WITH matched_bills AS (
          SELECT DISTINCT h.billno
          FROM tktcardfqlog l
          JOIN salehead h
            ON l.tcflmkt = h.mkt
           AND l.tcflsyjid = h.syjh
           AND l.tcflinvno ~ '^[0-9]+$'
           AND h.fphm = l.tcflinvno::numeric
          WHERE {log_filter}
        )
        SELECT
          s.sglgdid AS goods_code,
          COALESCE(NULLIF(gb.gbcname, ''), s.sglgdid) AS goods_name,
          s.sglppcode AS brand_code,
          s.sglcatid AS category_code,
          COUNT(DISTINCT s.sglbillno) AS ticket_count,
          SUM(COALESCE(s.sglsl, 0)) AS quantity,
          SUM(COALESCE(s.sglxssr, 0)) AS sales_amount,
          SUM(COALESCE(s.sgln2, 0)) AS gross_profit,
          SUM(COALESCE(s.sglnetml, s.sgln2, 0)) AS net_profit,
          SUM(COALESCE(s.sglsqje, 0)) AS received_coupon_amount
        FROM salegoodslist s
        JOIN matched_bills mb ON mb.billno = s.sglbillno
        LEFT JOIN goodsbase gb ON UPPER(TRIM(COALESCE(gb.gbid, ''))) = UPPER(TRIM(COALESCE(s.sglgdid, '')))
        GROUP BY 1, 2, 3, 4
        ORDER BY sales_amount DESC
        LIMIT :limit
        """,
        params,
    )

    members = _rows(
        db,
        f"""
        WITH matched_bills AS (
          SELECT DISTINCT h.billno, NULLIF(h.hykh, '') AS member_no
          FROM tktcardfqlog l
          JOIN salehead h
            ON l.tcflmkt = h.mkt
           AND l.tcflsyjid = h.syjh
           AND l.tcflinvno ~ '^[0-9]+$'
           AND h.fphm = l.tcflinvno::numeric
          WHERE {log_filter}
        ),
        sales_bill AS (
          SELECT
            s.sglbillno AS billno,
            SUM(COALESCE(s.sglxssr, 0)) AS sales_amount,
            SUM(COALESCE(s.sgln2, 0)) AS gross_profit,
            SUM(COALESCE(s.sglnetml, s.sgln2, 0)) AS net_profit
          FROM salegoodslist s
          JOIN matched_bills mb ON mb.billno = s.sglbillno
          GROUP BY s.sglbillno
        )
        SELECT
          COALESCE(NULLIF(m.customer_level, ''), '未识别') AS customer_level,
          COALESCE(NULLIF(m.regist_channel, ''), '未知') AS regist_channel,
          COALESCE(NULLIF(m.customer_status, ''), '未知') AS customer_status,
          COUNT(DISTINCT mb.member_no) AS member_count,
          COUNT(DISTINCT mb.billno) AS ticket_count,
          SUM(COALESCE(sb.sales_amount, 0)) AS sales_amount,
          SUM(COALESCE(sb.gross_profit, 0)) AS gross_profit,
          SUM(COALESCE(sb.net_profit, 0)) AS net_profit
        FROM matched_bills mb
        LEFT JOIN sales_bill sb ON sb.billno = mb.billno
        LEFT JOIN fj_dw_member_dim m ON UPPER(TRIM(COALESCE(m.customer_no, ''))) = UPPER(TRIM(COALESCE(mb.member_no, '')))
        GROUP BY 1, 2, 3
        ORDER BY sales_amount DESC
        LIMIT :limit
        """,
        params,
    )

    quality = _one(
        db,
        f"""
        WITH raw_logs AS (
          SELECT l.*
          FROM tktcardfqlog l
          WHERE {log_filter}
        ),
        matched_logs AS (
          SELECT l.tcflseqno, h.billno
          FROM raw_logs l
          JOIN salehead h
            ON l.tcflmkt = h.mkt
           AND l.tcflsyjid = h.syjh
           AND l.tcflinvno ~ '^[0-9]+$'
           AND h.fphm = l.tcflinvno::numeric
        ),
        period_pay AS (
          SELECT p.billno, p.rowno
          FROM salepay p
          JOIN salehead h ON h.billno = p.billno
          WHERE p.paycode IN ('0500', '0580')
            AND {period_filter}
        )
        SELECT
          (SELECT COUNT(*) FROM raw_logs) AS raw_log_count,
          (SELECT COUNT(*) FROM matched_logs) AS matched_log_count,
          (SELECT COUNT(*) FROM raw_logs) - (SELECT COUNT(*) FROM matched_logs) AS unmatched_log_count,
          (SELECT COUNT(*) FROM period_pay) AS period_coupon_payment_count,
          (
            SELECT COUNT(*)
            FROM period_pay pp
            WHERE NOT EXISTS (SELECT 1 FROM matched_logs ml WHERE ml.billno = pp.billno)
          ) AS period_payment_without_log_count
        """,
        params,
    )

    return {
        "activity": activity,
        "summary": summary,
        "payment_methods": payment_methods,
        "departments": departments,
        "products": products,
        "members": members,
        "quality": quality,
    }
