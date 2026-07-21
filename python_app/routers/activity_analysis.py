"""
活动分析 API

一期口径：只分析卡券使用。活动由 tktpopinfo 定义，卡券日志取 tktcardfqlog，
卡券付款取 salepay 中 0500/0580，销售、成本、毛利取 salegoodslist。
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Callable, Iterable

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from models.database import get_db
from models.models import User
from routers.auth import get_current_user
from routers.authz import load_business_scope, require_permission
from services.sales_analysis.ai_report import generate_ai_report
from services.activity_analysis.coupon_monthly_balance import (
    month_bounds,
    normalize_period_month,
    previous_period_month,
)
from services.activity_analysis.point_rules import point_rule_source_tables, point_status_case_sql
from services.department_display_order import department_display_sort_key


router = APIRouter(prefix="/api/activity-analysis", tags=["activity-analysis"])
ACTIVITY_ANALYSIS_PERMISSION = "activity_analysis.view"
POINTS_ACTIVITY_ANALYSIS_PERMISSION = "activity_analysis.points.view"
POINTS_ACTIVITY_START_DATE = date(2026, 7, 9)
POINTS_QUERY_TIMEOUT_SECONDS = 60
STAR_DIAMOND_ANALYSIS_PERMISSION = "activity_analysis.star_diamond.view"
VOUCHER_MATCH_VIEW_PERMISSION = "activity_settlement.voucher_match.view"
VOUCHER_MATCH_CONFIRM_PERMISSION = "activity_settlement.voucher_match.confirm"
VOUCHER_MATCH_REJECT_PERMISSION = "activity_settlement.voucher_match.reject"
COUPON_MONTHLY_VIEW_PERMISSION = "activity_settlement.coupon_monthly.view"
COUPON_MONTHLY_REBUILD_PERMISSION = "activity_settlement.coupon_monthly.rebuild"
COUPON_MONTHLY_CONFIRM_PERMISSION = "activity_settlement.coupon_monthly.confirm"
COUPON_MONTHLY_CARRYOVER_CREATE_PERMISSION = "activity_settlement.coupon_monthly.carryover_create"
COUPON_CONFIRMED_REVENUE_VIEW_PERMISSION = "activity_settlement.confirmed_revenue.view"
CREDIT_BUY_MATCH_TYPE_NAME = "贷方前台买券"


def _points_effective_date_range(start_date: str, end_date: str) -> tuple[str, str] | None:
    try:
        requested_start = date.fromisoformat(start_date)
        requested_end = date.fromisoformat(end_date)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="日期必须为 YYYY-MM-DD") from exc
    if requested_start > requested_end:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="开始日期不能晚于结束日期")
    if requested_end < POINTS_ACTIVITY_START_DATE:
        return None
    effective_start = max(requested_start, POINTS_ACTIVITY_START_DATE)
    return effective_start.isoformat(), (requested_end + timedelta(days=1)).isoformat()


def _empty_points_dashboard_response() -> dict[str, Any]:
    return {
        "summary": {},
        "department_options": [],
        "departments": [],
        "groups": [],
        "members": [],
        "tickets": [],
        "source_status": [],
    }


def _is_points_statement_timeout(exc: OperationalError) -> bool:
    return "statement timeout" in str(exc).lower() or "querycanceled" in str(exc).lower()


def _execute_points_query(db: Session, loader: Callable[[], Any]) -> Any:
    db.execute(text(f"SET LOCAL statement_timeout = '{POINTS_QUERY_TIMEOUT_SECONDS}s'"))
    try:
        return loader()
    except OperationalError as exc:
        if not _is_points_statement_timeout(exc):
            raise
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="中心年中庆活动数据查询超时",
        ) from exc


VOUCHER_DETAIL_KEY_SQL = (
    "md5(concat_ws('|', "
    "COALESCE(v.pk_detail, ''), "
    "COALESCE(v.pk_voucher, ''), "
    "COALESCE(v.pk_accsubj, ''), "
    "COALESCE(v.subject_code, ''), "
    "COALESCE(v.pk_currtype, ''), "
    "COALESCE(v.pk_sob, ''), "
    "COALESCE(v.pk_corp, ''), "
    "COALESCE(v.price::text, ''), "
    "COALESCE(v.excrate1::text, ''), "
    "COALESCE(v.explanation, ''), "
    "COALESCE(v.excrate2::text, ''), "
    "COALESCE(v.debitquantity::text, ''), "
    "COALESCE(v.debitamount::text, ''), "
    "COALESCE(v.fracdebitamount::text, ''), "
    "COALESCE(v.localdebitamount::text, ''), "
    "COALESCE(v.creditquantity::text, ''), "
    "COALESCE(v.creditamount::text, ''), "
    "COALESCE(v.fraccreditamount::text, ''), "
    "COALESCE(v.localcreditamount::text, ''), "
    "COALESCE(v.checkcount::text, ''), "
    "COALESCE(v.valuecode, ''), "
    "COALESCE(v.valuename, ''), "
    "COALESCE(v.account_year, ''), "
    "COALESCE(v.account_period, ''), "
    "COALESCE(v.subject_classify, '')"
    "))"
)


VOUCHER_MATCH_EXCLUDED_FLOW_SEQNOS = ("29042789",)


def _voucher_match_flow_exclusion_sql(alias: str = "l") -> str:
    prefix = f"{alias}." if alias else ""
    excluded = ", ".join(f"'{seqno}'" for seqno in VOUCHER_MATCH_EXCLUDED_FLOW_SEQNOS)
    return f"{prefix}tcflseqno::text NOT IN ({excluded})"


class VoucherMatchEntry(BaseModel):
    business_date: str
    market_code: str | None = None
    business_store_code: str | None = None
    coupon_type: str
    coupon_name: str | None = None
    match_type: str
    match_type_name: str | None = None
    business_amount: float = 0
    flow_count: int = 0
    member_count: int = 0
    voucher_detail_id: str
    voucher_amount: float = 0
    amount_diff: float = 0
    match_score: int = 0
    match_status: str


class VoucherMatchBatchRequest(BaseModel):
    confirm_status: str = "AUTO_CONFIRMED"
    rejected_reason: str | None = None
    rows: list[VoucherMatchEntry]


class CouponRevenueMovementRebuildRequest(BaseModel):
    period_month: str
    market_code: str | None = None


class CouponNcCarryoverRequest(BaseModel):
    period_month: str
    market_code: str
    coupon_type: str
    coupon_name: str | None = None
    nc_voucher_no: str
    carryover_amount: float
    carryover_date: str | None = None
    remark: str | None = None


class CouponMonthlyBalanceConfirmRequest(BaseModel):
    period_month: str
    market_code: str | None = None

SALES_EXCLUDED_DEPARTMENT_NAMES = (
    "中心营运部",
    "本店尾部",
    "中心财务部",
    "中心企划客服部",
    "中心物业部",
    "中心企划执行部",
    "中心物业服务部",
    "中心信息",
    "中心信息部",
    "新世纪营运部",
    "新世纪企划客服部",
    "新世纪物业服务部",
    "新世纪企划执行部",
    "新世纪物业",
    "新世纪信息",
    "新世纪信息部",
    "半山租赁部",
    "华山租赁部",
)


def _sql_string_list(values: Iterable[str]) -> str:
    return ", ".join("'" + value.replace("'", "''") + "'" for value in values)


def _sales_department_exclusion_sql(alias: str = "cg") -> str:
    names = _sql_string_list(SALES_EXCLUDED_DEPARTMENT_NAMES)
    return f" AND TRIM(BOTH FROM COALESCE({alias}.department_name, '')) NOT IN ({names})"

ACTION_LABELS = {
    "L": "扣券补现",
    "m": "前台买券",
    "Q": "后台赠券",
    "n": "前台退买券",
    "w": "前台买券冲正",
    "z": "前台退券冲正",
    "B": "券补录",
    "I": "后台券新增",
    "K": "返券扣回",
    "M": "后台买券",
    "N": "退买券",
    "Z": "支票返券生效",
    "A": "券增减",
    "F": "返券",
    "O": "券消费",
    "P": "券退货",
    "U": "券消费冲正",
    "V": "券退货冲正",
    "C": "券转移",
    "9": "券延期",
    "D": "券作废",
    "b": "返订金券",
    "l": "扣券补现冲正",
    "X": "面值券",
}

SOURCE_LABELS = {
    "1": "销售返券",
    "2": "前台买券",
    "3": "银行追送",
    "4": "退货返券",
    "5": "券转入",
    "7": "后台手工新增",
    "8": "后台买券",
}

ACTIVITY_STORE_RULES = (
    ("新世纪", 3, "603", "常州新世纪商城"),
    ("大楼", 2, "602", "常州百货大楼"),
    ("中心", 1, "601", "常州购物中心"),
)

ACTION_AMOUNT_SQL = (
    "CASE "
    "WHEN l.tcflzy IN ('F', 'O') THEN ABS(COALESCE(l.tcflmoney, 0)) "
    "WHEN l.tcflzy = 'U' THEN -ABS(COALESCE(l.tcflmoney, 0)) "
    "ELSE COALESCE(l.tcflmoney, 0) "
    "END"
)


def _issued_amount_sql(alias: str = "") -> str:
    prefix = f"{alias}." if alias else ""
    action = f"{prefix}tcflzy"
    amount = f"COALESCE({prefix}tcflmoney, 0)"
    return (
        "CASE "
        f"WHEN {action} IN ('F', 'm', 'M', 'Q', 'I', 'B', 'Z', 'b', 'X') THEN ABS({amount}) "
        f"WHEN {action} IN ('n', 'N', 'w') THEN -ABS({amount}) "
        f"WHEN {action} = 'A' THEN {amount} "
        "ELSE 0 "
        "END"
    )


def _case_expr(column: str, labels: dict[str, str], fallback: str) -> str:
    parts = [f"WHEN {column} = '{code}' THEN '{label}'" for code, label in labels.items()]
    return "CASE " + " ".join(parts) + f" ELSE {fallback} END"


def _code_name_display_sql(code_expr: str, name_expr: str) -> str:
    code = f"NULLIF(TRIM(BOTH FROM COALESCE({code_expr}, '')), '')"
    name = f"NULLIF(TRIM(BOTH FROM COALESCE({name_expr}, '')), '')"
    return (
        "CASE "
        f"WHEN {code} IS NOT NULL AND {name} IS NOT NULL THEN {code} || ' ' || {name} "
        f"WHEN {code} IS NOT NULL THEN {code} "
        f"WHEN {name} IS NOT NULL THEN {name} "
        "ELSE '未标识' "
        "END"
    )


def _brand_join_sql(alias: str = "s", brand_alias: str = "cb") -> str:
    return (
        f"LEFT JOIN codebrand {brand_alias} "
        f"ON UPPER(TRIM(COALESCE({brand_alias}.cbid, ''))) = UPPER(TRIM(COALESCE({alias}.sglppcode, '')))"
    )


def _category_join_sql(alias: str = "s", category_alias: str = "gc") -> str:
    return (
        f"LEFT JOIN goodscat {category_alias} "
        f"ON UPPER(TRIM(COALESCE({category_alias}.catcode, ''))) = UPPER(TRIM(COALESCE({alias}.sglcatid, '')))"
    )


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _activity_store_case_sql(field_expr: str, value_index: int, else_sql: str = "NULL") -> str:
    parts = [
        f"WHEN {field_expr} LIKE '%{keyword}%' THEN {repr(value) if isinstance(value, str) else value}"
        for keyword, *values in ACTIVITY_STORE_RULES
        for value in [values[value_index]]
    ]
    return "CASE " + " ".join(parts) + f" ELSE {else_sql} END"


def _activity_store_id_sql(alias: str = "p") -> str:
    return _activity_store_case_sql(f"COALESCE({alias}.tpiname, '')", 0, "NULL")


def _activity_store_code_sql(alias: str = "p") -> str:
    return _activity_store_case_sql(f"COALESCE({alias}.tpiname, '')", 1, "NULL")


def _activity_store_name_sql(alias: str = "p") -> str:
    return _activity_store_case_sql(f"COALESCE({alias}.tpiname, '')", 2, "NULL")


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


def _scope_match_sql(expressions: list[str], param_name: str) -> str:
    return "(" + " OR ".join(f"upper(trim(COALESCE(({expr})::varchar, ''))) = ANY(:{param_name})" for expr in expressions) + ")"


def _expand_activity_store_scope_values(values: Iterable[str]) -> list[str]:
    expanded: set[str] = set()
    for raw_value in values:
        value = str(raw_value or "").strip().upper()
        if not value:
            continue
        expanded.add(value)
        for _keyword, store_id, store_code, _store_name in ACTIVITY_STORE_RULES:
            sid = str(store_id).upper()
            scode = str(store_code).upper()
            if value in {sid, scode}:
                expanded.add(sid)
                expanded.add(scode)
    return sorted(expanded)


def _points_business_scope_filter_sql(scope, params: dict[str, Any], *, prefix: str) -> str:
    if "__all__" in scope.deny:
        return " AND 1=0"

    clauses: list[str] = []
    dimensions = {
        "store": ["scope_row.market_code", "scope_row.store_id"],
        "department": ["scope_row.department_code", "scope_row.department_name"],
        "group": ["scope_row.group_code"],
    }
    for dimension, expressions in dimensions.items():
        denied = sorted(scope.deny.get(dimension, set()))
        if denied:
            param = f"{prefix}_deny_{dimension}"
            params[param] = _expand_activity_store_scope_values(denied) if dimension == "store" else denied
            clauses.append(f"AND NOT {_scope_match_sql(expressions, param)}")

    if getattr(scope, "all_access", False):
        return " " + " ".join(clauses) if clauses else ""

    allow_clauses: list[str] = []
    for dimension, expressions in dimensions.items():
        allowed = sorted(scope.allow.get(dimension, set()))
        if allowed:
            param = f"{prefix}_allow_{dimension}"
            params[param] = _expand_activity_store_scope_values(allowed) if dimension == "store" else allowed
            allow_clauses.append(_scope_match_sql(expressions, param))

    if not allow_clauses:
        clauses.append("AND 1=0")
    else:
        clauses.append("AND (" + " OR ".join(allow_clauses) + ")")
    return " " + " ".join(clauses)


def _ensure_point_rule_tables(db: Session) -> None:
    missing = [table for table in point_rule_source_tables() if not _table_exists(db, table)]
    for table in ("salehead", "salegoods", "manaframe"):
        if not _table_exists(db, table):
            missing.append(table)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"积分核对所需数据表未创建: {', '.join(sorted(set(missing)))}",
        )


def _point_rule_source_status(db: Session) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for table_name in (*point_rule_source_tables(), "salehead", "salegoods", "manaframe"):
        qualified_name = f"public.{table_name}"
        row = db.execute(
            text(
                """
                SELECT
                  to_regclass(:qualified_name) IS NOT NULL AS exists,
                  GREATEST(COALESCE(c.reltuples, 0), 0)::bigint AS estimated_row_count
                FROM (SELECT 1) anchor
                LEFT JOIN pg_class c ON c.oid = to_regclass(:qualified_name)
                """
            ),
            {"qualified_name": qualified_name},
        ).mappings().first()
        rows.append(
            {
                "table_name": table_name,
                "exists": bool(row and row.get("exists")),
                "row_count": int(row.get("estimated_row_count") or 0) if row else 0,
            }
        )
    return rows


def _points_base_sql(scope_filter_sql: str = "") -> str:
    status_sql = point_status_case_sql(
        actual_expr="actual_point",
        expected_expr="expected_point",
        rate_expr="jfrate",
        allocation_diff_expr="allocation_diff_amount",
    )
    return f"""
    WITH manaframe_groups AS (
      SELECT
        mf.mfcode AS group_code,
        mf.mfcname AS group_name,
        dept.mfcode AS department_code,
        dept.mfcname AS department_name,
        CASE
          WHEN SUBSTRING(TRIM(BOTH FROM COALESCE(mf.mfcode, '')) FROM 1 FOR 3) ~ '^[0-9]+$'
          THEN SUBSTRING(TRIM(BOTH FROM COALESCE(mf.mfcode, '')) FROM 1 FOR 3)
          ELSE NULL
        END AS store_id
      FROM manaframe mf
      LEFT JOIN manaframe dept
        ON UPPER(TRIM(COALESCE(mf.mfpcode, ''))) = UPPER(TRIM(COALESCE(dept.mfcode, '')))
    ),
    latest_rate AS (
      SELECT DISTINCT ON (NULLIF(TRIM(BOTH FROM COALESCE(jfmfid, '')), ''))
        NULLIF(TRIM(BOTH FROM COALESCE(jfmfid, '')), '') AS jfmfid,
        jfseq,
        jfrate
      FROM rulejfrate
      WHERE NULLIF(TRIM(BOTH FROM COALESCE(jfmfid, '')), '') IS NOT NULL
      ORDER BY NULLIF(TRIM(BOTH FROM COALESCE(jfmfid, '')), ''), jfseq DESC
    ),
    all_payment_goods AS MATERIALIZED (
      SELECT
        h.billno,
        h.rqsj::date AS sale_date,
        h.rqsj AS sale_time,
        h.mkt::varchar AS market_code,
        COALESCE(NULLIF(TRIM(BOTH FROM h.hykh), ''), '') AS member_no,
        TRIM(BOTH FROM COALESCE(h.custtype, '')) AS customer_level,
        g.rowno AS goods_rowno,
        g.code AS goods_code,
        COALESCE(NULLIF(g.name, ''), g.code) AS goods_name,
        TRIM(BOTH FROM COALESCE(g.gz, '')) AS group_code,
        cg.group_name,
        cg.department_code,
        cg.department_name,
        COALESCE(cg.store_id, h.mkt::varchar) AS store_id,
        spg.spgrowno,
        spg.spgpmcode,
        spg.spgpayerid,
        COALESCE(spg.spgmoney, 0) AS payment_amount,
        COALESCE(spg.spggdmoney, 0) AS payment_alloc_amount
      FROM salehead h
      JOIN sellpaygoods spg ON spg.spgbillno = h.billno
      JOIN salegoods g
        ON g.billno = spg.spgbillno
       AND g.rowno::numeric = spg.spggdrow
      LEFT JOIN manaframe_groups cg
        ON UPPER(TRIM(COALESCE(cg.group_code, ''))) = UPPER(TRIM(COALESCE(g.gz, '')))
      WHERE COALESCE(h.djlb, '') NOT IN ('V', 'W', 'Y', 'Z')
        AND h.mkt::text = '601'
        AND h.rqsj >= CAST(:start_date AS date)
        AND h.rqsj < CAST(:end_exclusive AS date)
        {_sales_department_exclusion_sql("cg")}
    ),
    scoped_payment_goods AS MATERIALIZED (
      SELECT scope_row.*
      FROM all_payment_goods scope_row
      WHERE 1=1
        {scope_filter_sql}
    ),
    scoped_bills AS MATERIALIZED (
      SELECT DISTINCT billno, market_code, sale_date
      FROM scoped_payment_goods
    ),
    relevant_payment_goods AS MATERIALIZED (
      SELECT apg.*
      FROM all_payment_goods apg
      JOIN scoped_bills sb
        ON sb.billno = apg.billno
       AND sb.market_code = apg.market_code
       AND sb.sale_date = apg.sale_date
    ),
    scoped_bill_groups AS MATERIALIZED (
      SELECT DISTINCT billno, market_code, sale_date, group_code
      FROM scoped_payment_goods
    ),
    accounting_sales_by_group AS MATERIALIZED (
      SELECT
        s.sglbillno AS billno,
        s.sglmarket::varchar AS market_code,
        s.sglhsrq::date AS sale_date,
        TRIM(BOTH FROM COALESCE(s.sglmfid, '')) AS group_code,
        SUM(COALESCE(s.sglxssr, 0)) AS sales_amount
      FROM scoped_bill_groups sbg
      JOIN salegoodslist s
        ON s.sglbillno = sbg.billno
       AND sbg.market_code = s.sglmarket::varchar
       AND sbg.sale_date = s.sglhsrq::date
       AND UPPER(TRIM(COALESCE(sbg.group_code, ''))) = UPPER(TRIM(COALESCE(s.sglmfid, '')))
      GROUP BY 1, 2, 3, 4
    ),
    point_bills AS MATERIALIZED (
      SELECT DISTINCT billno
      FROM relevant_payment_goods
      WHERE customer_level IN ('03', '04')
    ),
    point_by_bill AS (
      SELECT
        op.order_id AS billno,
        SUM(COALESCE(op.point, 0)) AS actual_point,
        SUM(CASE WHEN COALESCE(op.point_type, '') IN ('消费加积分', '消费获得积分') THEN COALESCE(op.point, 0) ELSE 0 END) AS consumption_point,
        SUM(CASE WHEN COALESCE(op.point_type, '') LIKE '生日月%' THEN COALESCE(op.point, 0) ELSE 0 END) AS birthday_month_point
      FROM order_point op
      JOIN point_bills pb ON op.order_id = pb.billno::text
      GROUP BY op.order_id
    ),
    pay_line_balance AS (
      SELECT
        billno AS spgbillno,
        spgrowno,
        spgpmcode,
        MAX(payment_amount) AS payment_amount,
        SUM(payment_alloc_amount) AS allocated_amount,
        SUM(payment_alloc_amount) - MAX(payment_amount) AS allocation_diff_amount
      FROM relevant_payment_goods
      WHERE customer_level IN ('03', '04')
      GROUP BY billno, spgrowno, spgpmcode
    ),
    spg_rows AS (
      SELECT
        psg.billno,
        psg.sale_date,
        psg.sale_time,
        psg.market_code,
        psg.member_no,
        psg.customer_level,
        psg.goods_rowno,
        psg.goods_code,
        psg.goods_name,
        psg.group_code,
        psg.group_name,
        psg.department_code,
        psg.department_name,
        psg.store_id,
        psg.spgrowno,
        psg.spgpmcode,
        psg.spgpayerid,
        COALESCE(sgl.sales_amount, 0) AS accounting_sales_amount,
        psg.payment_alloc_amount,
        COALESCE(plb.allocation_diff_amount, 0) AS allocation_diff_amount,
        lr.jfrate,
        CASE
          WHEN cpr.fkcode IS NOT NULL THEN 0
          WHEN psg.spgpmcode IN ('0500', '0514', '0580') THEN COALESCE(
            NULLIF(TRIM(BOTH FROM tm.tqmisjf), '')::numeric * COALESCE(tm.tqmevrate, 1),
            NULLIF(TRIM(BOTH FROM tq.tqisjf), '')::numeric * COALESCE(tq.tqrevrate, 1),
            0
          )
          WHEN psg.spgpmcode = '0400' THEN 0.5
          ELSE COALESCE(pm.pmrevrate, 1)
        END AS point_basis_rate
      FROM relevant_payment_goods psg
      LEFT JOIN accounting_sales_by_group sgl
        ON sgl.billno = psg.billno
       AND sgl.market_code = psg.market_code
       AND sgl.sale_date = psg.sale_date
       AND UPPER(TRIM(COALESCE(sgl.group_code, ''))) = UPPER(TRIM(COALESCE(psg.group_code, '')))
      LEFT JOIN paymode pm
        ON UPPER(TRIM(COALESCE(pm.pmcode, ''))) = UPPER(TRIM(COALESCE(psg.spgpmcode, '')))
      LEFT JOIN card_paymoderule cpr
        ON UPPER(TRIM(COALESCE(cpr.fkcode, ''))) = UPPER(TRIM(COALESCE(psg.spgpmcode, '')))
      LEFT JOIN tktqtypemkt tm
        ON tm.tqmmkt::text = psg.market_code
       AND UPPER(TRIM(COALESCE(tm.tqmcode, ''))) = UPPER(TRIM(COALESCE(SUBSTRING(psg.spgpayerid FROM 1 FOR 1), '')))
      LEFT JOIN tktqtype tq
        ON UPPER(TRIM(COALESCE(tq.tqcode, ''))) = UPPER(TRIM(COALESCE(SUBSTRING(psg.spgpayerid FROM 1 FOR 1), '')))
      LEFT JOIN latest_rate lr
        ON UPPER(TRIM(COALESCE(lr.jfmfid, ''))) = UPPER(TRIM(COALESCE(psg.group_code, '')))
      LEFT JOIN pay_line_balance plb
        ON plb.spgbillno = psg.billno
       AND plb.spgrowno = psg.spgrowno
       AND plb.spgpmcode = psg.spgpmcode
      WHERE psg.customer_level IN ('03', '04')
    ),
    row_calc AS (
      SELECT
        *,
        payment_alloc_amount * point_basis_rate AS row_point_basis_amount,
        CASE
          WHEN jfrate IS NOT NULL AND jfrate <> 0 AND TRIM(BOTH FROM COALESCE(customer_level, '')) = '03' THEN payment_alloc_amount * point_basis_rate * (2 / jfrate)
          WHEN jfrate IS NOT NULL AND jfrate <> 0 AND TRIM(BOTH FROM COALESCE(customer_level, '')) = '04' THEN payment_alloc_amount * point_basis_rate * (3 / jfrate)
          ELSE 0
        END AS row_expected_point
      FROM spg_rows
    ),
    grouped_rows AS (
      SELECT
        billno,
        sale_date,
        MIN(sale_time) AS sale_time,
        market_code,
        member_no,
        customer_level,
        group_code,
        group_name,
        department_code,
        department_name,
        store_id,
        MAX(accounting_sales_amount) AS total_sales_amount,
        SUM(row_point_basis_amount) AS point_basis_amount,
        SUM(row_expected_point) AS expected_point,
        MAX(ABS(allocation_diff_amount)) AS allocation_diff_amount,
        MIN(jfrate) FILTER (WHERE jfrate IS NOT NULL) AS jfrate,
        BOOL_OR(jfrate IS NULL) AS has_missing_rate,
        BOOL_OR(jfrate = 0) AS has_zero_rate
      FROM row_calc
      GROUP BY billno, sale_date, market_code, member_no, customer_level, group_code, group_name, department_code, department_name, store_id
    ),
    bill_basis AS (
      SELECT billno, SUM(point_basis_amount) AS bill_point_basis_amount
      FROM grouped_rows
      GROUP BY billno
    ),
    point_rows_unscored AS (
      SELECT
        gr.*,
        COALESCE(pb.actual_point, 0)
          * CASE WHEN COALESCE(bb.bill_point_basis_amount, 0) <> 0 THEN gr.point_basis_amount / bb.bill_point_basis_amount ELSE 0 END AS actual_point,
        COALESCE(pb.consumption_point, 0)
          * CASE WHEN COALESCE(bb.bill_point_basis_amount, 0) <> 0 THEN gr.point_basis_amount / bb.bill_point_basis_amount ELSE 0 END AS consumption_point,
        COALESCE(pb.birthday_month_point, 0)
          * CASE WHEN COALESCE(bb.bill_point_basis_amount, 0) <> 0 THEN gr.point_basis_amount / bb.bill_point_basis_amount ELSE 0 END AS birthday_month_point
      FROM grouped_rows gr
      JOIN bill_basis bb ON bb.billno = gr.billno
      LEFT JOIN point_by_bill pb ON pb.billno = gr.billno::text
    ),
    point_rows AS (
      SELECT
        pru.*,
        CASE
          WHEN pru.has_missing_rate THEN 'MISSING_RATE'
          WHEN pru.has_zero_rate THEN 'ZERO_RATE'
          ELSE {status_sql}
        END AS status
      FROM point_rows_unscored pru
      JOIN scoped_bill_groups sbg
        ON sbg.billno = pru.billno
       AND sbg.market_code = pru.market_code
       AND sbg.sale_date = pru.sale_date
       AND UPPER(TRIM(COALESCE(sbg.group_code, ''))) = UPPER(TRIM(COALESCE(pru.group_code, '')))
    )
    """


def coupon_confirmed_revenue_daily_sql(include_coupon_type: bool = False) -> str:
    coupon_filter = "AND UPPER(TRIM(rm.coupon_type)) = UPPER(TRIM(:coupon_type))" if include_coupon_type else ""
    return f"""
        SELECT
          rm.id,
          rm.business_date,
          rm.period_month,
          rm.market_code,
          rm.business_store_code,
          rm.coupon_type,
          rm.coupon_name,
          rm.match_type,
          rm.movement_direction,
          rm.voucher_match_id,
          rm.voucher_detail_id,
          COALESCE(rm.business_amount, 0) AS business_amount,
          rm.revenue_rate,
          COALESCE(rm.actual_revenue_amount, 0) AS actual_revenue_amount,
          rm.rate_status,
          m.confirmed_at,
          COALESCE(NULLIF(u.real_name, ''), u.username) AS confirmed_by_name
        FROM activity_coupon_revenue_movement rm
        JOIN activity_coupon_voucher_match m ON m.id = rm.voucher_match_id
        LEFT JOIN users u ON u.user_id = m.confirmed_by
        WHERE rm.business_date >= CAST(:start_date AS DATE)
          AND rm.business_date < CAST(:end_date AS DATE) + INTERVAL '1 day'
          AND m.confirm_status IN ('AUTO_CONFIRMED', 'MANUAL_CONFIRMED')
          AND (:market_code = '' OR rm.market_code = :market_code)
          {coupon_filter}
        ORDER BY rm.business_date DESC, m.confirmed_at DESC, rm.market_code, rm.coupon_type, rm.id
    """


def _store_name_from_code(code: object) -> str:
    value = str(code or "")
    return {"601": "购物中心", "602": "百货大楼", "603": "新世纪", "604": "半山"}.get(value, value or "—")


def summarize_confirmed_revenue_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {
        "movement_count": len(rows),
        "missing_rate_count": sum(1 for row in rows if row.get("rate_status") == "MISSING_RATE"),
        "business_amount": sum(float(row.get("business_amount") or 0) for row in rows),
        "confirmed_revenue_amount": sum(float(row.get("actual_revenue_amount") or 0) for row in rows),
        "sales_revenue_amount": None,
        "confirmed_revenue_ratio": None,
    }
    store_map: dict[str, dict[str, Any]] = {}
    for row in rows:
        code = str(row.get("market_code") or "")
        item = store_map.setdefault(
            code,
            {
                "market_code": code,
                "store_name": _store_name_from_code(code),
                "movement_count": 0,
                "missing_rate_count": 0,
                "business_amount": 0.0,
                "confirmed_revenue_amount": 0.0,
                "sales_revenue_amount": None,
                "confirmed_revenue_ratio": None,
            },
        )
        item["movement_count"] += 1
        if row.get("rate_status") == "MISSING_RATE":
            item["missing_rate_count"] += 1
        item["business_amount"] += float(row.get("business_amount") or 0)
        item["confirmed_revenue_amount"] += float(row.get("actual_revenue_amount") or 0)
    normalized_rows = [{**row, "store_name": _store_name_from_code(row.get("market_code"))} for row in rows]
    return {"summary": summary, "store_summary": list(store_map.values()), "rows": normalized_rows}


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


def finance_voucher_amount_filter_sql(alias: str = "v") -> str:
    return f"""{alias}.excrate1 = 0
            AND (
              COALESCE({alias}.localdebitamount, {alias}.debitamount, 0) <> 0
              OR COALESCE({alias}.localcreditamount, {alias}.creditamount, 0) <> 0
            )"""


def front_buy_sale_join_sql(log_alias: str = "l", sale_alias: str = "front_sale") -> str:
    """Return the one-to-one salehead lookup used by front buy/refund rows."""
    return f"""LEFT JOIN LATERAL (
              SELECT
                h.billno,
                h.ysje,
                h.sjfk,
                h.zl
              FROM salehead h
              WHERE h.mkt = {log_alias}.tcflmkt
                AND h.syjh = {log_alias}.tcflsyjid
                AND {log_alias}.tcflinvno ~ '^[0-9]+$'
                AND h.fphm = {log_alias}.tcflinvno::numeric
                AND h.rqsj::date = {log_alias}.tcfldate
              ORDER BY h.billno DESC
              LIMIT 1
            ) {sale_alias} ON TRUE"""


def front_buy_face_total_sql(log_alias: str = "l") -> str:
    """Face total used to allocate one front-buy sale across coupon log rows."""
    return f"""SUM(ABS(COALESCE({log_alias}.tcflmoney, 0)))
              FILTER (
                WHERE {log_alias}.tcflzy IN ('m', 'n')
                  AND {log_alias}.tcflsource IN ('2', '5')
              ) OVER (
                PARTITION BY
                  {log_alias}.tcfldate,
                  {log_alias}.tcflmkt,
                  {log_alias}.tcflsyjid,
                  {log_alias}.tcflinvno,
                  {log_alias}.tcflzy
              )"""


def front_buy_actual_amount_sql(log_alias: str = "l", sale_alias: str = "front_sale") -> str:
    """Signed actual amount for m/n, allocated by each row's share of face value."""
    face_total_sql = front_buy_face_total_sql(log_alias)
    allocated_amount_sql = f"""ABS(COALESCE(
                {sale_alias}.ysje,
                {sale_alias}.sjfk - COALESCE({sale_alias}.zl, 0)
              )) * ABS(COALESCE({log_alias}.tcflmoney, 0))
              / NULLIF(({face_total_sql}), 0)"""
    return f"""CASE
              WHEN {log_alias}.tcflzy = 'm'
               AND {log_alias}.tcflsource IN ('2', '5')
               AND {sale_alias}.billno IS NOT NULL
              THEN {allocated_amount_sql}
              WHEN {log_alias}.tcflzy = 'n'
               AND {log_alias}.tcflsource IN ('2', '5')
               AND {sale_alias}.billno IS NOT NULL
              THEN -({allocated_amount_sql})
              ELSE NULL
            END"""


def confirmed_voucher_match_movement_sql() -> str:
    """Build movements immediately for the confirmed voucher-match ids."""
    return f"""
            WITH target_matches AS MATERIALIZED (
              SELECT
                m.id AS voucher_match_id,
                m.business_date,
                to_char(m.business_date, 'YYYY-MM') AS period_month,
                COALESCE(NULLIF(m.market_code, ''), NULLIF(m.business_store_code, '')) AS market_code,
                m.business_store_code,
                UPPER(TRIM(m.coupon_type)) AS coupon_type,
                m.coupon_name,
                m.match_type,
                m.voucher_detail_id,
                COALESCE(m.business_amount, 0) AS business_amount
              FROM activity_coupon_voucher_match m
              WHERE m.id = ANY(:voucher_match_ids)
                AND m.confirm_status IN ('AUTO_CONFIRMED', 'MANUAL_CONFIRMED')
                AND m.match_type IN ('CREDIT_BUY', 'DEBIT_USE')
                AND COALESCE(NULLIF(m.market_code, ''), NULLIF(m.business_store_code, '')) IS NOT NULL
            ),
            target_days AS (
              SELECT DISTINCT business_date, market_code
              FROM target_matches
            ),
            front_credit_log_rows AS MATERIALIZED (
              SELECT
                l.tcfldate AS business_date,
                l.tcflmkt::varchar AS market_code,
                CASE
                  WHEN l.tcflzy = 'm'
                   AND l.tcflsource IN ('2', '5')
                   AND COALESCE(NULLIF(l.tcfljetype, ''), '未标识') = 'O'
                  THEN 'W'
                  ELSE UPPER(TRIM(COALESCE(NULLIF(l.tcfljetype, ''), '未标识')))
                END AS coupon_type,
                CASE
                  WHEN l.tcflzy = 'm' THEN ABS(COALESCE(l.tcflmoney, 0))
                  ELSE -ABS(COALESCE(l.tcflmoney, 0))
                END AS face_amount,
                {front_buy_actual_amount_sql("l", "front_sale")} AS actual_amount,
                CASE WHEN front_sale.billno IS NULL THEN 1 ELSE 0 END AS missing_actual_count
              FROM tktcardfqlog l
              JOIN target_days d
                ON d.business_date = l.tcfldate
               AND d.market_code = l.tcflmkt::varchar
              {front_buy_sale_join_sql("l", "front_sale")}
              WHERE l.tcflzy IN ('m', 'n')
                AND l.tcflsource IN ('2', '5')
            ),
            front_credit_rows AS (
              SELECT
                business_date,
                market_code,
                coupon_type,
                SUM(face_amount) AS face_amount,
                SUM(COALESCE(actual_amount, 0)) AS actual_amount,
                SUM(missing_actual_count) AS missing_actual_count
              FROM front_credit_log_rows
              GROUP BY business_date, market_code, coupon_type
            ),
            backend_credit_rows AS (
              SELECT
                l.tcfldate AS business_date,
                l.tcflmkt::varchar AS market_code,
                CASE
                  WHEN l.tcflzy = 'M'
                   AND l.tcflsource = '8'
                   AND COALESCE(NULLIF(l.tcfljetype, ''), '未标识') = 'O'
                  THEN 'W'
                  ELSE UPPER(TRIM(COALESCE(NULLIF(l.tcfljetype, ''), '未标识')))
                END AS coupon_type,
                SUM(CASE
                  WHEN l.tcflzy = 'M' THEN ABS(COALESCE(l.tcflmoney, 0))
                  ELSE -ABS(COALESCE(l.tcflmoney, 0))
                END) AS business_amount
              FROM tktcardfqlog l
              JOIN target_days d
                ON d.business_date = l.tcfldate
               AND d.market_code = l.tcflmkt::varchar
              WHERE l.tcflzy IN ('M', 'N', 'w')
                AND l.tcflsource IN ('2', '8')
              GROUP BY 1, 2, 3
            ),
            confirmed_matches AS (
              SELECT
                m.*,
                r.effective_revenue_rate,
                r.snapshot_date,
                f.face_amount AS front_face_amount,
                f.actual_amount AS front_actual_amount,
                COALESCE(f.missing_actual_count, 0) AS front_missing_actual_count,
                COALESCE(b.business_amount, 0) AS backend_business_amount,
                (m.match_type = 'CREDIT_BUY' AND f.business_date IS NOT NULL) AS has_front_actual
              FROM target_matches m
              LEFT JOIN activity_coupon_revenue_rate_snapshot r
                ON r.snapshot_date = m.business_date
               AND r.market_code = m.market_code
               AND UPPER(TRIM(r.coupon_type)) = m.coupon_type
              LEFT JOIN front_credit_rows f
                ON f.business_date = m.business_date
               AND f.market_code = m.market_code
               AND f.coupon_type = m.coupon_type
              LEFT JOIN backend_credit_rows b
                ON b.business_date = m.business_date
               AND b.market_code = m.market_code
               AND b.coupon_type = m.coupon_type
            )
            INSERT INTO activity_coupon_revenue_movement (
                business_date, period_month, market_code, business_store_code,
                coupon_type, coupon_name, match_type, voucher_match_id,
                source_type, source_key, voucher_detail_id, business_amount,
                revenue_rate, actual_revenue_amount, rate_snapshot_date,
                rate_status, movement_direction, created_at, updated_at
            )
            SELECT
                business_date,
                period_month,
                market_code,
                business_store_code,
                coupon_type,
                coupon_name,
                match_type,
                voucher_match_id,
                'VOUCHER_MATCH',
                'voucher_match:' || voucher_match_id::text,
                voucher_detail_id,
                CASE WHEN has_front_actual
                  THEN front_face_amount + backend_business_amount
                  ELSE business_amount
                END,
                CASE
                  WHEN has_front_actual
                   AND front_missing_actual_count = 0
                   AND (ABS(backend_business_amount) <= 0.005 OR effective_revenue_rate IS NOT NULL)
                   AND ABS(front_face_amount + backend_business_amount) > 0.005
                  THEN (front_actual_amount + backend_business_amount * COALESCE(effective_revenue_rate, 0))
                       / (front_face_amount + backend_business_amount)
                  ELSE effective_revenue_rate
                END,
                CASE
                  WHEN has_front_actual
                   AND front_missing_actual_count = 0
                   AND (ABS(backend_business_amount) <= 0.005 OR effective_revenue_rate IS NOT NULL)
                  THEN front_actual_amount + backend_business_amount * COALESCE(effective_revenue_rate, 0)
                  WHEN has_front_actual THEN 0
                  WHEN effective_revenue_rate IS NULL THEN 0
                  ELSE business_amount * effective_revenue_rate
                END,
                CASE WHEN has_front_actual AND ABS(backend_business_amount) <= 0.005 THEN NULL ELSE snapshot_date END,
                CASE
                  WHEN has_front_actual AND front_missing_actual_count > 0 THEN 'MISSING_RATE'
                  WHEN has_front_actual AND ABS(backend_business_amount) > 0.005 AND effective_revenue_rate IS NULL THEN 'MISSING_RATE'
                  WHEN has_front_actual THEN 'OK'
                  WHEN effective_revenue_rate IS NULL THEN 'MISSING_RATE'
                  ELSE 'OK'
                END,
                CASE WHEN match_type = 'CREDIT_BUY' THEN 'INCREASE' ELSE 'DECREASE' END,
                NOW(),
                NOW()
            FROM confirmed_matches
            ON CONFLICT (source_type, source_key)
            DO UPDATE SET
                voucher_match_id = EXCLUDED.voucher_match_id,
                business_date = EXCLUDED.business_date,
                period_month = EXCLUDED.period_month,
                market_code = EXCLUDED.market_code,
                business_store_code = EXCLUDED.business_store_code,
                coupon_type = EXCLUDED.coupon_type,
                coupon_name = EXCLUDED.coupon_name,
                match_type = EXCLUDED.match_type,
                voucher_detail_id = EXCLUDED.voucher_detail_id,
                business_amount = EXCLUDED.business_amount,
                revenue_rate = EXCLUDED.revenue_rate,
                actual_revenue_amount = EXCLUDED.actual_revenue_amount,
                rate_snapshot_date = EXCLUDED.rate_snapshot_date,
                rate_status = EXCLUDED.rate_status,
                movement_direction = EXCLUDED.movement_direction,
                updated_at = NOW()
            """


def _sync_confirmed_voucher_match_movements(db: Session, voucher_match_ids: list[int]) -> None:
    if not voucher_match_ids:
        return
    params = {"voucher_match_ids": voucher_match_ids}
    db.execute(
        text(
            """
            DELETE FROM activity_coupon_revenue_movement rm
            WHERE rm.source_type = 'VOUCHER_MATCH'
              AND rm.voucher_match_id = ANY(:voucher_match_ids)
              AND NOT EXISTS (
                SELECT 1
                FROM activity_coupon_voucher_match m
                WHERE m.id = rm.voucher_match_id
                  AND m.confirm_status IN ('AUTO_CONFIRMED', 'MANUAL_CONFIRMED')
              )
            """
        ),
        params,
    )
    db.execute(
        text(
            """
            DELETE FROM activity_coupon_revenue_movement rm
            USING activity_coupon_voucher_match m
            WHERE m.id = ANY(:voucher_match_ids)
              AND m.confirm_status IN ('AUTO_CONFIRMED', 'MANUAL_CONFIRMED')
              AND m.match_type = 'CREDIT_BUY'
              AND rm.source_type = 'COUPON_RECHARGE'
              AND rm.business_date = m.business_date
              AND rm.market_code = COALESCE(NULLIF(m.market_code, ''), NULLIF(m.business_store_code, ''))
              AND UPPER(TRIM(rm.coupon_type)) = UPPER(TRIM(m.coupon_type))
            """
        ),
        params,
    )
    db.execute(text(confirmed_voucher_match_movement_sql()), params)


def _period_or_400(period_month: str) -> str:
    try:
        return normalize_period_month(period_month)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="period_month 必须是 YYYY-MM") from exc


def _ensure_coupon_monthly_tables(db: Session) -> None:
    missing = [
        table
        for table in [
            "activity_coupon_revenue_movement",
            "activity_coupon_nc_carryover",
            "activity_coupon_monthly_balance",
        ]
        if not _table_exists(db, table)
    ]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"卡券月结表尚未创建: {', '.join(missing)}",
        )


def _reject_confirmed_coupon_month(db: Session, period_month: str, market_code: str | None) -> None:
    row = db.execute(
        text(
            """
            SELECT COUNT(*) AS count
            FROM activity_coupon_monthly_balance
            WHERE period_month = :period_month
              AND status = 'CONFIRMED'
              AND (:market_code = '' OR market_code = :market_code)
            """
        ),
        {"period_month": period_month, "market_code": market_code or ""},
    ).fetchone()
    if row is not None and int(row.count or 0) > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="目标月份已确认月结，不能覆盖或新增登记")


def _activity_store_scope_values(db: Session, scope) -> tuple[set[str], set[str]]:
    if getattr(scope, "all_access", False):
        return set(), set()

    store_ids: set[str] = set()
    store_codes: set[str] = set()
    store_rows = []
    if _table_exists(db, "stores"):
        store_rows = db.execute(text("SELECT store_id, store_code FROM stores")).mappings().all()

    raw_store_values = {str(value).strip().upper() for value in scope.allow.get("store", set()) if str(value).strip()}
    for value in raw_store_values:
        matched = False
        for row in store_rows:
            sid = str(row["store_id"]) if row["store_id"] is not None else ""
            scode = str(row["store_code"] or "").strip().upper()
            if value in {sid.upper(), scode}:
                if sid:
                    store_ids.add(sid)
                if scode:
                    store_codes.add(scode)
                matched = True
        if not matched:
            if value.isdigit() and len(value) == 3:
                store_codes.add(value)
            else:
                store_ids.add(value)

    allowed_departments = scope.allow.get("department", set())
    allowed_groups = scope.allow.get("group", set())
    if (allowed_departments or allowed_groups) and _table_exists(db, "manaframe"):
        params = {
            "department_values": sorted(allowed_departments) or ["__none__"],
            "group_values": sorted(allowed_groups) or ["__none__"],
        }
        rows = db.execute(
            text(
                """
                WITH manaframe_groups AS (
                  SELECT
                    mf.mfcode AS group_code,
                    dept.mfcode AS department_code,
                    dept.mfcname AS department_name
                  FROM manaframe mf
                  LEFT JOIN manaframe dept
                    ON UPPER(TRIM(COALESCE(mf.mfpcode, ''))) = UPPER(TRIM(COALESCE(dept.mfcode, '')))
                )
                SELECT DISTINCT SUBSTRING(TRIM(BOTH FROM COALESCE(group_code, '')) FROM 1 FOR 3) AS store_code
                FROM manaframe_groups
                WHERE UPPER(TRIM(COALESCE(group_code, ''))) = ANY(:group_values)
                   OR UPPER(TRIM(COALESCE(department_code, ''))) = ANY(:department_values)
                   OR UPPER(TRIM(COALESCE(department_name, ''))) = ANY(:department_values)
                """
            ),
            params,
        ).mappings().all()
        for row in rows:
            code = str(row["store_code"] or "").strip().upper()
            if code:
                store_codes.add(code)
                for store in store_rows:
                    if str(store["store_code"] or "").strip().upper() == code and store["store_id"] is not None:
                        store_ids.add(str(store["store_id"]))

    return store_ids, store_codes


def _activity_store_options_for_scope(db: Session, scope) -> list[dict[str, Any]]:
    rows = _rows(
        db,
        """
        SELECT store_id, store_code, store_name
        FROM stores
        WHERE COALESCE(is_active, TRUE) = TRUE
        ORDER BY store_id
        """,
        {},
    )
    deny = getattr(scope, "deny", {})
    if "__all__" in deny:
        return []

    all_access = getattr(scope, "all_access", False)
    allowed_store_ids: set[str] = set()
    allowed_store_codes: set[str] = set()
    if not all_access:
        allowed_store_ids, allowed_store_codes = _activity_store_scope_values(db, scope)
    denied_store_ids: set[str] = set()
    denied_store_codes: set[str] = set()
    deny_values = deny.get("store", set())
    if deny_values:
        deny_scope = type(
            "DenyScope",
            (),
            {"allow": {"store": deny_values}, "all_access": False},
        )()
        denied_store_ids, denied_store_codes = _activity_store_scope_values(db, deny_scope)

    return [
        row
        for row in rows
        if (
            all_access
            or str(row.get("store_id") or "") in allowed_store_ids
            or str(row.get("store_code") or "").strip().upper() in allowed_store_codes
        )
        and str(row.get("store_id") or "") not in denied_store_ids
        and str(row.get("store_code") or "").strip().upper() not in denied_store_codes
    ]


def _require_selected_activity_store(db: Session, scope, store_code: str | None) -> str | None:
    normalized = str(store_code or "").strip().upper()
    if not normalized:
        return None
    allowed_store_codes = {
        str(row.get("store_code") or "").strip().upper()
        for row in _activity_store_options_for_scope(db, scope)
    }
    if normalized not in allowed_store_codes:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="门店不存在或无数据权限")
    return normalized


def _selected_store_clause(
    selected_store_code: str | None,
    params: dict[str, Any],
    *,
    expression: str,
    prefix: str,
) -> str:
    if not selected_store_code:
        return ""
    key = f"{prefix}_selected_store_code"
    params[key] = selected_store_code
    return f" AND {expression}::varchar = :{key}"


def _activity_market_scope_filter_sql(
    db: Session,
    scope,
    params: dict[str, Any],
    *,
    expression: str,
    prefix: str,
) -> str:
    if "__all__" in getattr(scope, "deny", {}):
        return " AND 1=0"

    all_access = getattr(scope, "all_access", False)
    sql = ""
    if not all_access:
        store_ids, store_codes = _activity_store_scope_values(db, scope)
        if not store_ids and not store_codes:
            return " AND 1=0"

        clauses: list[str] = []
        if store_ids:
            key = f"{prefix}_store_ids"
            params[key] = sorted(store_ids)
            clauses.append(f"{expression}::varchar = ANY(:{key})")
        if store_codes:
            key = f"{prefix}_store_codes"
            params[key] = sorted(store_codes)
            clauses.append(f"{expression}::varchar = ANY(:{key})")
        sql = " AND (" + " OR ".join(clauses) + ")"

    deny_values = getattr(scope, "deny", {}).get("store", set())
    if not deny_values:
        return sql
    deny_scope = type(
        "DenyScope",
        (),
        {"allow": {"store": deny_values}, "all_access": False},
    )()
    denied_store_ids, denied_store_codes = _activity_store_scope_values(db, deny_scope)
    deny_clauses: list[str] = []
    if denied_store_ids:
        key = f"{prefix}_deny_store_ids"
        params[key] = sorted(denied_store_ids)
        deny_clauses.append(f"{expression}::varchar = ANY(:{key})")
    if denied_store_codes:
        key = f"{prefix}_deny_store_codes"
        params[key] = sorted(denied_store_codes)
        deny_clauses.append(f"{expression}::varchar = ANY(:{key})")
    if deny_clauses:
        sql += " AND NOT (" + " OR ".join(deny_clauses) + ")"
    return sql


def _activity_scope_filter_sql(db: Session, scope, params: dict[str, Any], *, alias: str = "p", prefix: str = "activity_scope") -> str:
    if "__all__" in scope.deny:
        return " AND 1=0"

    all_access = getattr(scope, "all_access", False)
    allow_sql = ""
    if not all_access:
        store_ids, store_codes = _activity_store_scope_values(db, scope)
        if not store_ids and not store_codes:
            return " AND 1=0"

        clauses: list[str] = []
        if store_ids:
            key = f"{prefix}_store_ids"
            params[key] = sorted(store_ids)
            clauses.append(f"{_activity_store_id_sql(alias)}::varchar = ANY(:{key})")
        if store_codes:
            key = f"{prefix}_store_codes"
            params[key] = sorted(store_codes)
            clauses.append(f"{_activity_store_code_sql(alias)} = ANY(:{key})")
        allow_sql = " AND (" + " OR ".join(clauses) + ")"

    denied_store_ids, denied_store_codes = set(), set()
    deny_scope = type("DenyScope", (), {"allow": {"store": scope.deny.get("store", set())}, "all_access": False})()
    if scope.deny.get("store"):
        denied_store_ids, denied_store_codes = _activity_store_scope_values(db, deny_scope)
    deny_sql = ""
    if denied_store_ids or denied_store_codes:
        deny_clauses: list[str] = []
        if denied_store_ids:
            key = f"{prefix}_deny_store_ids"
            params[key] = sorted(denied_store_ids)
            deny_clauses.append(f"{_activity_store_id_sql(alias)}::varchar = ANY(:{key})")
        if denied_store_codes:
            key = f"{prefix}_deny_store_codes"
            params[key] = sorted(denied_store_codes)
            deny_clauses.append(f"{_activity_store_code_sql(alias)} = ANY(:{key})")
        deny_sql = " AND NOT (" + " OR ".join(deny_clauses) + ")"

    return allow_sql + deny_sql


def _activity_log_scope_filter_sql(db: Session, scope, params: dict[str, Any], *, alias: str = "l", prefix: str = "activity_log_scope") -> str:
    if "__all__" in scope.deny:
        return " AND 1=0"

    all_access = getattr(scope, "all_access", False)
    allow_sql = ""
    if not all_access:
        store_ids, store_codes = _activity_store_scope_values(db, scope)
        if not store_ids and not store_codes:
            return " AND 1=0"

        clauses: list[str] = []
        if store_ids:
            key = f"{prefix}_store_ids"
            params[key] = sorted(store_ids)
            clauses.append(f"{alias}.tcflmkt::varchar = ANY(:{key})")
        if store_codes:
            key = f"{prefix}_store_codes"
            params[key] = sorted(store_codes)
            clauses.append(f"{alias}.tcflmkt::varchar = ANY(:{key})")
        allow_sql = " AND (" + " OR ".join(clauses) + ")"

    denied_store_ids, denied_store_codes = set(), set()
    deny_scope = type("DenyScope", (), {"allow": {"store": scope.deny.get("store", set())}, "all_access": False})()
    if scope.deny.get("store"):
        denied_store_ids, denied_store_codes = _activity_store_scope_values(db, deny_scope)
    deny_sql = ""
    deny_clauses: list[str] = []
    if denied_store_ids:
        key = f"{prefix}_deny_store_ids"
        params[key] = sorted(denied_store_ids)
        deny_clauses.append(f"{alias}.tcflmkt::varchar = ANY(:{key})")
    if denied_store_codes:
        key = f"{prefix}_deny_store_codes"
        params[key] = sorted(denied_store_codes)
        deny_clauses.append(f"{alias}.tcflmkt::varchar = ANY(:{key})")
    if deny_clauses:
        deny_sql = " AND NOT (" + " OR ".join(deny_clauses) + ")"

    return allow_sql + deny_sql


def _require_center_store_scope(db: Session, user: User) -> None:
    scope = load_business_scope(db, user, fallback_resource_code="sales")
    if getattr(scope, "all_access", False):
        return
    store_ids, store_codes = _activity_store_scope_values(db, scope)
    if "1" in store_ids or "601" in store_codes:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无常州购物中心星钻会员分析权限")


def _star_diamond_member_where(alias: str = "m") -> str:
    value = f"UPPER(TRIM(COALESCE({alias}.is_star_diamond_member, '')))"
    return f"{value} <> '' AND {value} NOT IN ('0', 'N', 'NO', 'FALSE', '否', '不是', '非')"


def _activity_filter(
    activity_id: str | None,
    start_date: str | None,
    end_date: str | None,
    scope: str = "activity",
    activity_scope_sql: str = "",
    log_scope_sql: str = "",
) -> tuple[str, dict[str, Any]]:
    params: dict[str, Any] = {}
    clauses: list[str] = []
    if activity_id:
        clauses.append("l.tcflpopid = :activity_id")
        params["activity_id"] = activity_id.strip()
    else:
        if scope == "standalone":
            clauses.append(
                "(COALESCE(l.tcflpopid, '') IN ('', '0') OR NOT EXISTS (SELECT 1 FROM tktpopinfo p WHERE p.tpiid = l.tcflpopid))"
            )
        elif scope == "all":
            clauses.append("1=1")
        else:
            clauses.append(
                "COALESCE(l.tcflpopid, '') NOT IN ('', '0') AND EXISTS (SELECT 1 FROM tktpopinfo p WHERE p.tpiid = l.tcflpopid)"
            )
    if activity_scope_sql:
        if scope == "standalone" and not activity_id:
            clauses.append(log_scope_sql.removeprefix(" AND ") if log_scope_sql else "1=0")
        elif scope == "all" and not activity_id and log_scope_sql:
            standalone_clause = "(COALESCE(l.tcflpopid, '') IN ('', '0') OR NOT EXISTS (SELECT 1 FROM tktpopinfo p WHERE p.tpiid = l.tcflpopid))"
            clauses.append(
                "("
                f"(COALESCE(l.tcflpopid, '') NOT IN ('', '0') AND EXISTS (SELECT 1 FROM tktpopinfo p WHERE p.tpiid = l.tcflpopid {activity_scope_sql}))"
                f" OR ({standalone_clause} AND {log_scope_sql.removeprefix(' AND ')})"
                ")"
            )
        else:
            clauses.append(f"EXISTS (SELECT 1 FROM tktpopinfo p WHERE p.tpiid = l.tcflpopid {activity_scope_sql})")
    elif log_scope_sql and scope == "standalone" and not activity_id:
        clauses.append(log_scope_sql.removeprefix(" AND "))
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
        params["start_date"] = start_date
        params["end_date"] = end_date
        return (
            """
            h.rqsj::date BETWEEN
              COALESCE(CAST(:start_date AS date), (SELECT tpistartdate FROM tktpopinfo WHERE tpiid = :activity_id), DATE '1900-01-01')
              AND
              COALESCE(CAST(:end_date AS date), (SELECT tpienddate FROM tktpopinfo WHERE tpiid = :activity_id), DATE '2999-12-31')
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


def _coupon_type_filter(coupon_type: str | None, alias: str = "l") -> tuple[str, dict[str, Any]]:
    if not coupon_type:
        return "", {}
    return f" AND COALESCE({alias}.tcfljetype, '') = :coupon_type", {"coupon_type": coupon_type.strip()}


def _supplier_discount_cte(extra_where: str = "") -> str:
    return f"""
        supplier_discount AS (
          SELECT
            sgpbillno AS billno,
            sgpmfid AS group_code,
            SUM(COALESCE(sgpjglpayzk, 0)) AS pay_discount_amount,
            SUM(COALESCE(sgpjglsupzk, 0)) AS supplier_discount_amount,
            SUM(COALESCE(sgpjglshopzk, 0)) AS shop_discount_amount
          FROM supgoodspayzkdet
          WHERE sgppmcode IN ('0500', '0580')
            {extra_where}
          GROUP BY sgpbillno, sgpmfid
        )
    """


@router.get("/star-diamond/overview")
async def star_diamond_overview(
    start_date: str = Query(..., description="消费日期起 YYYY-MM-DD"),
    end_date: str = Query(..., description="消费日期止 YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, STAR_DIAMOND_ANALYSIS_PERMISSION)
    _ensure_required_tables(db)
    _require_center_store_scope(db, current_user)

    params = {"start_date": start_date, "end_date": end_date}
    member_where = _star_diamond_member_where("m")
    summary = _one(
        db,
        f"""
        WITH star_members AS (
          SELECT
            UPPER(TRIM(COALESCE(customer_no, ''))) AS member_no,
            customer_name,
            telephone,
            customer_level,
            admission_date,
            is_star_diamond_member
          FROM fj_dw_member_dim m
          WHERE COALESCE(customer_no, '') <> ''
            AND {member_where}
        ),
        tickets AS (
          SELECT
            h.billno,
            UPPER(TRIM(COALESCE(h.hykh, ''))) AS member_no,
            MIN(h.rqsj) AS sale_time,
            SUM(COALESCE(s.sglxssr, 0)) AS sales_amount,
            SUM(COALESCE(s.sglnetml, s.sgln2, 0)) AS net_profit,
            SUM(COALESCE(s.sglsl, 0)) AS quantity,
            SUM(COALESCE(s.sglsqje, 0)) AS coupon_amount
          FROM salehead h
          JOIN star_members sm ON sm.member_no = UPPER(TRIM(COALESCE(h.hykh, '')))
          JOIN salegoodslist s ON s.sglbillno = h.billno
          WHERE h.mkt::varchar = '601'
            AND h.rqsj::date BETWEEN :start_date AND :end_date
          GROUP BY h.billno, UPPER(TRIM(COALESCE(h.hykh, '')))
        ),
        member_sales AS (
          SELECT
            sm.member_no,
            COUNT(DISTINCT t.billno) AS ticket_count,
            COALESCE(SUM(t.sales_amount), 0) AS sales_amount,
            COALESCE(SUM(t.net_profit), 0) AS net_profit,
            MAX(t.sale_time) AS last_sale_time
          FROM star_members sm
          LEFT JOIN tickets t ON t.member_no = sm.member_no
          GROUP BY sm.member_no
        )
        SELECT
          COUNT(*) AS star_member_count,
          COUNT(*) FILTER (WHERE ticket_count > 0) AS active_member_count,
          COALESCE(SUM(ticket_count), 0) AS ticket_count,
          COALESCE(SUM(sales_amount), 0) AS sales_amount,
          COALESCE(SUM(net_profit), 0) AS net_profit,
          CASE WHEN COALESCE(SUM(ticket_count), 0) > 0 THEN COALESCE(SUM(sales_amount), 0) / SUM(ticket_count) ELSE 0 END AS avg_ticket_amount,
          CASE WHEN COUNT(*) FILTER (WHERE ticket_count > 0) > 0 THEN COALESCE(SUM(sales_amount), 0) / COUNT(*) FILTER (WHERE ticket_count > 0) ELSE 0 END AS avg_member_amount,
          COUNT(*) FILTER (WHERE ticket_count >= 2) AS repeat_member_count,
          COUNT(*) FILTER (WHERE ticket_count = 0) AS silent_member_count,
          COUNT(*) FILTER (WHERE ticket_count > 0 AND sales_amount >= 10000) AS high_value_member_count,
          COUNT(*) FILTER (WHERE ticket_count > 0 AND sales_amount < 10000) AS nurture_member_count
        FROM member_sales
        """,
        params,
    )

    category_rows = _rows(
        db,
        f"""
        WITH star_members AS (
          SELECT UPPER(TRIM(COALESCE(customer_no, ''))) AS member_no
          FROM fj_dw_member_dim m
          WHERE COALESCE(customer_no, '') <> ''
            AND {member_where}
        )
        SELECT
          COALESCE(NULLIF(s.sglcatid, ''), '未标识') AS category_code,
          COALESCE(NULLIF(gc.catcname, ''), '') AS category_name,
          {_code_name_display_sql("s.sglcatid", "gc.catcname")} AS category_display,
          COUNT(DISTINCT h.hykh) AS member_count,
          COUNT(DISTINCT h.billno) AS ticket_count,
          SUM(COALESCE(s.sglxssr, 0)) AS sales_amount
        FROM salehead h
        JOIN star_members sm ON sm.member_no = UPPER(TRIM(COALESCE(h.hykh, '')))
        JOIN salegoodslist s ON s.sglbillno = h.billno
        {_category_join_sql("s", "gc")}
        WHERE h.mkt::varchar = '601'
          AND h.rqsj::date BETWEEN :start_date AND :end_date
        GROUP BY 1, 2, 3
        ORDER BY sales_amount DESC
        LIMIT 10
        """,
        params,
    )

    service_segments = _rows(
        db,
        f"""
        WITH star_members AS (
          SELECT UPPER(TRIM(COALESCE(customer_no, ''))) AS member_no
          FROM fj_dw_member_dim m
          WHERE COALESCE(customer_no, '') <> ''
            AND {member_where}
        ),
        member_sales AS (
          SELECT
            sm.member_no,
            COUNT(DISTINCT h.billno) AS ticket_count,
            COALESCE(SUM(s.sglxssr), 0) AS sales_amount,
            MAX(h.rqsj) AS last_sale_time
          FROM star_members sm
          LEFT JOIN salehead h
            ON sm.member_no = UPPER(TRIM(COALESCE(h.hykh, '')))
           AND h.mkt::varchar = '601'
           AND h.rqsj::date BETWEEN :start_date AND :end_date
          LEFT JOIN salegoodslist s ON s.sglbillno = h.billno
          GROUP BY sm.member_no
        )
        SELECT
          segment,
          COUNT(*) AS member_count,
          SUM(sales_amount) AS sales_amount,
          service_action
        FROM (
          SELECT
            member_no,
            sales_amount,
            CASE
              WHEN ticket_count = 0 THEN '待唤醒'
              WHEN sales_amount >= 10000 THEN '高价值维护'
              WHEN ticket_count >= 2 THEN '高频互动'
              ELSE '潜力培育'
            END AS segment,
            CASE
              WHEN ticket_count = 0 THEN '专属顾问一对一回访，提供新品预览、生日礼遇或到店预约。'
              WHEN sales_amount >= 10000 THEN '安排专属接待、重点品牌私享会、预留爆款和售后跟进。'
              WHEN ticket_count >= 2 THEN '推送跨品类搭配权益，邀请参加会员日和积分加速活动。'
              ELSE '根据最近购买品类推荐同楼层品牌券包，提升二次到店。'
            END AS service_action
          FROM member_sales
        ) x
        GROUP BY segment, service_action
        ORDER BY sales_amount DESC NULLS LAST, member_count DESC
        """,
        params,
    )

    return {"summary": summary, "top_categories": category_rows, "service_segments": service_segments}


@router.get("/star-diamond/members")
async def star_diamond_members(
    start_date: str = Query(...),
    end_date: str = Query(...),
    keyword: str | None = Query(None, description="会员号/姓名/手机号"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, STAR_DIAMOND_ANALYSIS_PERMISSION)
    _ensure_required_tables(db)
    _require_center_store_scope(db, current_user)

    params: dict[str, Any] = {"start_date": start_date, "end_date": end_date, "limit": limit}
    keyword_sql = ""
    if keyword:
        params["keyword"] = f"%{keyword.strip()}%"
        keyword_sql = "AND (m.customer_no ILIKE :keyword OR m.customer_name ILIKE :keyword OR m.telephone ILIKE :keyword)"

    return _rows(
        db,
        f"""
        WITH star_members AS (
          SELECT
            UPPER(TRIM(COALESCE(customer_no, ''))) AS member_no,
            customer_name,
            telephone,
            customer_level,
            admission_date,
            is_star_diamond_member
          FROM fj_dw_member_dim m
          WHERE COALESCE(customer_no, '') <> ''
            AND {_star_diamond_member_where("m")}
            {keyword_sql}
        ),
        member_sales AS (
          SELECT
            sm.member_no,
            COUNT(DISTINCT h.billno) AS ticket_count,
            COALESCE(SUM(s.sglxssr), 0) AS sales_amount,
            COALESCE(SUM(s.sglnetml), 0) AS net_profit,
            MAX(h.rqsj) AS last_sale_time,
            STRING_AGG(DISTINCT {_code_name_display_sql("s.sglcatid", "gc.catcname")}, ', ')
              FILTER (WHERE s.sglbillno IS NOT NULL) AS categories,
            STRING_AGG(DISTINCT {_code_name_display_sql("s.sglppcode", "cb.cbcname")}, ', ')
              FILTER (WHERE s.sglbillno IS NOT NULL) AS brands
          FROM star_members sm
          LEFT JOIN salehead h
            ON sm.member_no = UPPER(TRIM(COALESCE(h.hykh, '')))
           AND h.mkt::varchar = '601'
           AND h.rqsj::date BETWEEN :start_date AND :end_date
          LEFT JOIN salegoodslist s ON s.sglbillno = h.billno
          {_category_join_sql("s", "gc")}
          {_brand_join_sql("s", "cb")}
          GROUP BY sm.member_no
        )
        SELECT
          sm.member_no,
          sm.customer_name,
          sm.telephone,
          sm.customer_level,
          sm.admission_date,
          sm.is_star_diamond_member,
          COALESCE(ms.ticket_count, 0) AS ticket_count,
          COALESCE(ms.sales_amount, 0) AS sales_amount,
          COALESCE(ms.net_profit, 0) AS net_profit,
          CASE WHEN COALESCE(ms.ticket_count, 0) > 0 THEN COALESCE(ms.sales_amount, 0) / ms.ticket_count ELSE 0 END AS avg_ticket_amount,
          ms.last_sale_time,
          COALESCE(ms.categories, '') AS categories,
          COALESCE(ms.brands, '') AS brands,
          CASE
            WHEN COALESCE(ms.ticket_count, 0) = 0 THEN '待唤醒'
            WHEN COALESCE(ms.sales_amount, 0) >= 10000 THEN '高价值维护'
            WHEN COALESCE(ms.ticket_count, 0) >= 2 THEN '高频互动'
            ELSE '潜力培育'
          END AS service_segment
        FROM star_members sm
        LEFT JOIN member_sales ms ON ms.member_no = sm.member_no
        ORDER BY sales_amount DESC, ticket_count DESC, sm.member_no
        LIMIT :limit
        """,
        params,
    )


@router.get("/star-diamond/trails")
async def star_diamond_trails(
    start_date: str = Query(...),
    end_date: str = Query(...),
    member_no: str | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, STAR_DIAMOND_ANALYSIS_PERMISSION)
    _ensure_required_tables(db)
    _require_center_store_scope(db, current_user)

    params: dict[str, Any] = {"start_date": start_date, "end_date": end_date, "limit": limit}
    member_filter = ""
    if member_no:
        params["member_no"] = member_no.strip().upper()
        member_filter = "AND UPPER(TRIM(COALESCE(h.hykh, ''))) = :member_no"

    return _rows(
        db,
        f"""
        WITH star_members AS (
          SELECT UPPER(TRIM(COALESCE(customer_no, ''))) AS member_no, customer_name, telephone
          FROM fj_dw_member_dim m
          WHERE COALESCE(customer_no, '') <> ''
            AND {_star_diamond_member_where("m")}
        ),
        manaframe_groups AS (
          SELECT
            mf.mfcode AS group_code,
            mf.mfcname AS group_name,
            dept.mfcode AS department_code,
            dept.mfcname AS department_name
          FROM manaframe mf
          LEFT JOIN manaframe dept
            ON UPPER(TRIM(COALESCE(mf.mfpcode, ''))) = UPPER(TRIM(COALESCE(dept.mfcode, '')))
        )
        SELECT
          h.rqsj AS sale_time,
          h.billno,
          h.hykh AS member_no,
          sm.customer_name,
          sm.telephone,
          COUNT(*) AS sku_count,
          SUM(COALESCE(s.sglsl, 0)) AS quantity,
          SUM(COALESCE(s.sglxssr, 0)) AS sales_amount,
          SUM(COALESCE(s.sglnetml, s.sgln2, 0)) AS net_profit,
          STRING_AGG(DISTINCT {_code_name_display_sql("cg.department_code", "cg.department_name")}, ', ')
            FILTER (WHERE s.sglbillno IS NOT NULL) AS departments,
          STRING_AGG(DISTINCT {_code_name_display_sql("COALESCE(cg.group_code, s.sglmfid)", "cg.group_name")}, ', ')
            FILTER (WHERE s.sglbillno IS NOT NULL) AS groups,
          STRING_AGG(DISTINCT {_code_name_display_sql("s.sglcatid", "gc.catcname")}, ', ')
            FILTER (WHERE s.sglbillno IS NOT NULL) AS categories,
          STRING_AGG(DISTINCT {_code_name_display_sql("s.sglppcode", "cb.cbcname")}, ', ')
            FILTER (WHERE s.sglbillno IS NOT NULL) AS brands
        FROM salehead h
        JOIN star_members sm ON sm.member_no = UPPER(TRIM(COALESCE(h.hykh, '')))
        JOIN salegoodslist s ON s.sglbillno = h.billno
        LEFT JOIN manaframe_groups cg ON UPPER(TRIM(COALESCE(cg.group_code, ''))) = UPPER(TRIM(COALESCE(s.sglmfid, '')))
        {_category_join_sql("s", "gc")}
        {_brand_join_sql("s", "cb")}
        WHERE h.mkt::varchar = '601'
          AND h.rqsj::date BETWEEN :start_date AND :end_date
          {member_filter}
        GROUP BY h.rqsj, h.billno, h.hykh, sm.customer_name, sm.telephone
        ORDER BY h.rqsj DESC, h.billno DESC
        LIMIT :limit
        """,
        params,
    )


@router.post("/star-diamond/member-analysis")
async def star_diamond_member_analysis(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, STAR_DIAMOND_ANALYSIS_PERMISSION)
    _ensure_required_tables(db)
    _require_center_store_scope(db, current_user)

    member_no = str(payload.get("member_no") or "").strip().upper()
    start_date = str(payload.get("start_date") or "").strip()
    end_date = str(payload.get("end_date") or "").strip()
    if not member_no or not start_date or not end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="member_no/start_date/end_date 不能为空")

    params = {"member_no": member_no, "start_date": start_date, "end_date": end_date}
    member = _one(
        db,
        f"""
        SELECT
          customer_no AS member_no,
          customer_name,
          telephone,
          customer_level,
          admission_date,
          regist_channel,
          customer_status,
          is_star_diamond_member
        FROM fj_dw_member_dim m
        WHERE UPPER(TRIM(COALESCE(customer_no, ''))) = :member_no
          AND {_star_diamond_member_where("m")}
        """,
        params,
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="星钻会员不存在")

    summary = _one(
        db,
        """
        WITH tickets AS (
          SELECT
            h.billno,
            MIN(h.rqsj) AS sale_time,
            SUM(COALESCE(s.sglxssr, 0)) AS sales_amount,
            SUM(COALESCE(s.sglnetml, s.sgln2, 0)) AS net_profit,
            SUM(COALESCE(s.sglsl, 0)) AS quantity,
            COUNT(DISTINCT NULLIF(s.sglcatid, '')) AS category_count,
            COUNT(DISTINCT NULLIF(s.sglppcode, '')) AS brand_count
          FROM salehead h
          JOIN salegoodslist s ON s.sglbillno = h.billno
          WHERE h.mkt::varchar = '601'
            AND UPPER(TRIM(COALESCE(h.hykh, ''))) = :member_no
            AND h.rqsj::date BETWEEN :start_date AND :end_date
          GROUP BY h.billno
        )
        SELECT
          COUNT(*) AS ticket_count,
          COALESCE(SUM(sales_amount), 0) AS sales_amount,
          COALESCE(SUM(net_profit), 0) AS net_profit,
          COALESCE(SUM(quantity), 0) AS quantity,
          CASE WHEN COUNT(*) > 0 THEN COALESCE(SUM(sales_amount), 0) / COUNT(*) ELSE 0 END AS avg_ticket_amount,
          MAX(sale_time) AS last_sale_time,
          MIN(sale_time) AS first_sale_time,
          COALESCE(SUM(category_count), 0) AS category_touch_count,
          COALESCE(SUM(brand_count), 0) AS brand_touch_count
        FROM tickets
        """,
        params,
    )
    categories = _rows(
        db,
        f"""
        SELECT
          COALESCE(NULLIF(s.sglcatid, ''), '未标识') AS category_code,
          COALESCE(NULLIF(gc.catcname, ''), '') AS category_name,
          {_code_name_display_sql("s.sglcatid", "gc.catcname")} AS category_display,
          COUNT(DISTINCT h.billno) AS ticket_count,
          SUM(COALESCE(s.sglxssr, 0)) AS sales_amount
        FROM salehead h
        JOIN salegoodslist s ON s.sglbillno = h.billno
        {_category_join_sql("s", "gc")}
        WHERE h.mkt::varchar = '601'
          AND UPPER(TRIM(COALESCE(h.hykh, ''))) = :member_no
          AND h.rqsj::date BETWEEN :start_date AND :end_date
        GROUP BY 1, 2, 3
        ORDER BY sales_amount DESC
        LIMIT 8
        """,
        params,
    )
    trails = await star_diamond_trails(start_date, end_date, member_no, 20, db, current_user)

    rule_notes: list[str] = []
    sales_amount = float(summary.get("sales_amount") or 0)
    ticket_count = float(summary.get("ticket_count") or 0)
    if ticket_count == 0:
        rule_notes.append("期间未在中心消费，优先做一对一唤醒和到店预约。")
    elif sales_amount >= 10000:
        rule_notes.append("期间消费高，建议专属接待、重点品牌私享会和售后跟进。")
    if ticket_count >= 2:
        rule_notes.append("期间有复购，可围绕偏好品类做跨品牌组合权益。")
    if not rule_notes:
        rule_notes.append("期间有消费但频次不高，建议用同楼层品牌券包促进二次到店。")

    ai = generate_ai_report(
        {
            "member": member,
            "period": {"start_date": start_date, "end_date": end_date, "store": "常州购物中心"},
            "summary": summary,
            "top_categories": categories,
            "recent_trails": trails,
            "rule_notes": rule_notes,
        },
        instructions=(
            "你是百货商场高端会员运营顾问。"
            "基于提供的星钻会员消费、品类、购物轨迹，输出针对单个会员的服务建议。"
            "不要编造未提供的信息，不要输出思考过程。"
            "输出结构：会员画像、消费特征、服务机会、下一步动作。"
            "动作要具体到导购/客服可执行，控制在 400 字以内。"
        ),
    )
    return {
        "member": member,
        "summary": summary,
        "top_categories": categories,
        "recent_trails": trails,
        "rule_notes": rule_notes,
        "ai": ai,
    }


@router.post("/star-diamond/overall-analysis")
async def star_diamond_overall_analysis(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, STAR_DIAMOND_ANALYSIS_PERMISSION)
    _ensure_required_tables(db)
    _require_center_store_scope(db, current_user)

    start_date = str(payload.get("start_date") or "").strip()
    end_date = str(payload.get("end_date") or "").strip()
    if not start_date or not end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_date/end_date 不能为空")

    params = {"start_date": start_date, "end_date": end_date}
    member_where = _star_diamond_member_where("m")
    overview_data = await star_diamond_overview(start_date, end_date, db, current_user)
    top_members = await star_diamond_members(start_date, end_date, None, 30, db, current_user)
    recent_trails = await star_diamond_trails(start_date, end_date, None, 50, db, current_user)

    top_brands = _rows(
        db,
        f"""
        WITH star_members AS (
          SELECT UPPER(TRIM(COALESCE(customer_no, ''))) AS member_no
          FROM fj_dw_member_dim m
          WHERE COALESCE(customer_no, '') <> ''
            AND {member_where}
        )
        SELECT
          COALESCE(NULLIF(s.sglppcode, ''), '未标识') AS brand_code,
          COALESCE(NULLIF(cb.cbcname, ''), '') AS brand_name,
          {_code_name_display_sql("s.sglppcode", "cb.cbcname")} AS brand_display,
          COUNT(DISTINCT h.hykh) AS member_count,
          COUNT(DISTINCT h.billno) AS ticket_count,
          SUM(COALESCE(s.sglxssr, 0)) AS sales_amount
        FROM salehead h
        JOIN star_members sm ON sm.member_no = UPPER(TRIM(COALESCE(h.hykh, '')))
        JOIN salegoodslist s ON s.sglbillno = h.billno
        {_brand_join_sql("s", "cb")}
        WHERE h.mkt::varchar = '601'
          AND h.rqsj::date BETWEEN :start_date AND :end_date
        GROUP BY 1, 2, 3
        ORDER BY sales_amount DESC
        LIMIT 10
        """,
        params,
    )
    top_departments = _rows(
        db,
        f"""
        WITH star_members AS (
          SELECT UPPER(TRIM(COALESCE(customer_no, ''))) AS member_no
          FROM fj_dw_member_dim m
          WHERE COALESCE(customer_no, '') <> ''
            AND {member_where}
        ),
        manaframe_groups AS (
          SELECT
            mf.mfcode AS group_code,
            mf.mfcname AS group_name,
            dept.mfcode AS department_code,
            dept.mfcname AS department_name
          FROM manaframe mf
          LEFT JOIN manaframe dept
            ON UPPER(TRIM(COALESCE(mf.mfpcode, ''))) = UPPER(TRIM(COALESCE(dept.mfcode, '')))
        )
        SELECT
          COALESCE(NULLIF(cg.department_code, ''), '未归属') AS department_code,
          COALESCE(NULLIF(cg.department_name, ''), '未归属部门') AS department_name,
          {_code_name_display_sql("cg.department_code", "cg.department_name")} AS department_display,
          COUNT(DISTINCT h.hykh) AS member_count,
          COUNT(DISTINCT h.billno) AS ticket_count,
          SUM(COALESCE(s.sglxssr, 0)) AS sales_amount
        FROM salehead h
        JOIN star_members sm ON sm.member_no = UPPER(TRIM(COALESCE(h.hykh, '')))
        JOIN salegoodslist s ON s.sglbillno = h.billno
        LEFT JOIN manaframe_groups cg ON UPPER(TRIM(COALESCE(cg.group_code, ''))) = UPPER(TRIM(COALESCE(s.sglmfid, '')))
        WHERE h.mkt::varchar = '601'
          AND h.rqsj::date BETWEEN :start_date AND :end_date
        GROUP BY 1, 2, 3
        ORDER BY sales_amount DESC
        LIMIT 10
        """,
        params,
    )

    summary = overview_data.get("summary") or {}
    star_member_count = float(summary.get("star_member_count") or 0)
    active_member_count = float(summary.get("active_member_count") or 0)
    silent_member_count = float(summary.get("silent_member_count") or 0)
    repeat_member_count = float(summary.get("repeat_member_count") or 0)
    active_rate = active_member_count / star_member_count if star_member_count else 0
    repeat_rate = repeat_member_count / active_member_count if active_member_count else 0
    silent_rate = silent_member_count / star_member_count if star_member_count else 0
    rule_notes = [
        f"星钻会员消费覆盖率约 {active_rate:.1%}，需要同时管理高贡献人群与未消费人群。",
        f"活跃星钻会员复购率约 {repeat_rate:.1%}，可按复购人群设计专属二次到店权益。",
        f"未消费星钻会员占比约 {silent_rate:.1%}，建议形成顾问回访和预约到店清单。",
        "品牌、品类和部门建议优先使用销售贡献与消费会员数共同判断，避免只看单笔高客单。",
    ]

    ai_payload = {
        "period": {"start_date": start_date, "end_date": end_date, "store": "常州购物中心"},
        "summary": summary,
        "service_segments": overview_data.get("service_segments") or [],
        "top_categories": overview_data.get("top_categories") or [],
        "top_brands": top_brands,
        "top_departments": top_departments,
        "top_members": top_members,
        "recent_trails": recent_trails,
        "rule_notes": rule_notes,
    }
    ai = generate_ai_report(
        ai_payload,
        instructions=(
            "你是百货商场高端会员运营负责人。"
            "基于所选时间段内全部星钻会员销售明细、分层、品类、品牌、部门和购物轨迹样本，"
            "输出面向门店管理层和会员运营团队的整体经营分析与服务方案。"
            "不要编造未提供的信息，不要输出思考过程。"
            "输出结构：1. 核心判断 2. 会员分层动作 3. 品类/品牌/部门机会 4. 重点会员服务打法 5. 未来7天执行清单。"
            "建议要可执行，说明哪些人群优先、由谁跟进、跟进什么内容，控制在 800 字以内。"
        ),
    )
    return {
        **ai_payload,
        "ai": ai,
    }


@router.get("/points/department-options")
async def points_department_options(
    start_date: str = Query(..., description="销售日期起 YYYY-MM-DD"),
    end_date: str = Query(..., description="销售日期止 YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, POINTS_ACTIVITY_ANALYSIS_PERMISSION)
    effective_range = _points_effective_date_range(start_date, end_date)
    if effective_range is None:
        return {"items": []}
    effective_start_date, effective_end_exclusive = effective_range
    _ensure_required_tables(db)
    _ensure_point_rule_tables(db)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    params: dict[str, Any] = {
        "start_date": effective_start_date,
        "end_exclusive": effective_end_exclusive,
    }
    scope_sql = _points_business_scope_filter_sql(scope, params, prefix="points_department_options")
    items = _execute_points_query(db, lambda: _rows(
        db,
        _points_base_sql(scope_sql)
        + """
        SELECT DISTINCT
          COALESCE(NULLIF(department_code, ''), '未归属') AS department_code,
          COALESCE(NULLIF(department_name, ''), '未归属部门') AS department_name
        FROM point_rows
        ORDER BY department_name
        """,
        params,
    ))
    return {"items": items}


@router.get("/points/dashboard")
async def points_dashboard(
    start_date: str = Query(..., description="销售日期起 YYYY-MM-DD"),
    end_date: str = Query(..., description="销售日期止 YYYY-MM-DD"),
    department_name: str | None = Query(None, description="部门名称"),
    group_code: str | None = Query(None, description="柜组编码"),
    member_no: str | None = Query(None, description="会员号"),
    keyword: str | None = Query(None, description="会员号/等级搜索"),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, POINTS_ACTIVITY_ANALYSIS_PERMISSION)
    effective_range = _points_effective_date_range(start_date, end_date)
    if effective_range is None:
        return _empty_points_dashboard_response()
    effective_start_date, effective_end_exclusive = effective_range
    _ensure_required_tables(db)
    _ensure_point_rule_tables(db)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    params: dict[str, Any] = {
        "start_date": effective_start_date,
        "end_exclusive": effective_end_exclusive,
        "limit": limit,
    }
    scope_sql = _points_business_scope_filter_sql(scope, params, prefix="points_dashboard")
    extra_filters = []
    if department_name:
        params["department_name"] = f"%{department_name.strip()}%"
        extra_filters.append("AND department_name ILIKE :department_name")
    if group_code:
        params["group_code"] = group_code.strip()
        extra_filters.append("AND UPPER(TRIM(COALESCE(group_code, ''))) = UPPER(TRIM(:group_code))")

    member_filter = ""
    if member_no:
        params["member_no"] = member_no.strip()
        member_filter = "AND UPPER(TRIM(COALESCE(member_no, ''))) = UPPER(TRIM(:member_no))"

    keyword_filter = ""
    if keyword:
        params["keyword"] = f"%{keyword.strip()}%"
        keyword_filter = "AND (member_no ILIKE :keyword OR customer_level ILIKE :keyword)"

    row = _execute_points_query(db, lambda: _one(
        db,
        _points_base_sql(scope_sql)
        + f"""
        , base_point_rows AS MATERIALIZED (
          SELECT *
          FROM point_rows
        ),
        filtered_point_rows AS MATERIALIZED (
          SELECT *
          FROM base_point_rows
          WHERE 1=1
            {" ".join(extra_filters)}
        ),
        level_sales_source AS MATERIALIZED (
          SELECT customer_level, billno, market_code, sale_date, group_code, member_no
          FROM scoped_payment_goods
          WHERE 1=1
            {" ".join(extra_filters)}
          GROUP BY 1, 2, 3, 4, 5, 6
        ),
        level_sales_rows AS MATERIALIZED (
          SELECT
            src.customer_level,
            COALESCE(SUM(s.sales_amount), 0) AS total_sales_amount,
            CASE
              WHEN src.customer_level IN ('01', '02', '03', '04') THEN COUNT(DISTINCT NULLIF(src.member_no, ''))
              ELSE COUNT(DISTINCT src.billno)
            END AS person_count
          FROM level_sales_source src
          JOIN accounting_sales_by_group s
            ON s.billno = src.billno
           AND s.market_code = src.market_code
           AND s.sale_date = src.sale_date
           AND UPPER(TRIM(COALESCE(s.group_code, ''))) = UPPER(TRIM(COALESCE(src.group_code, '')))
          GROUP BY src.customer_level
        )
        SELECT
          (
            SELECT jsonb_build_object(
              'ticket_count', COUNT(DISTINCT billno),
              'member_count', COUNT(DISTINCT NULLIF(member_no, '')),
              'black_gold_member_count', COUNT(DISTINCT NULLIF(member_no, '')) FILTER (WHERE TRIM(BOTH FROM COALESCE(customer_level, '')) = '03'),
              'black_diamond_member_count', COUNT(DISTINCT NULLIF(member_no, '')) FILTER (WHERE TRIM(BOTH FROM COALESCE(customer_level, '')) = '04'),
              'total_sales_amount', COALESCE(SUM(total_sales_amount), 0),
              'point_basis_amount', COALESCE(SUM(point_basis_amount), 0),
              'actual_point', COALESCE(SUM(actual_point), 0),
              'expected_point', COALESCE(SUM(expected_point), 0),
              'point_diff', COALESCE(SUM(actual_point - expected_point), 0),
              'level_total_sales_amount', (SELECT COALESCE(SUM(total_sales_amount), 0) FROM level_sales_rows),
              'black_diamond_sales_amount', (SELECT COALESCE(SUM(total_sales_amount), 0) FROM level_sales_rows WHERE customer_level = '04'),
              'black_gold_sales_amount', (SELECT COALESCE(SUM(total_sales_amount), 0) FROM level_sales_rows WHERE customer_level = '03'),
              'gold_star_sales_amount', (SELECT COALESCE(SUM(total_sales_amount), 0) FROM level_sales_rows WHERE customer_level = '02'),
              'silver_star_sales_amount', (SELECT COALESCE(SUM(total_sales_amount), 0) FROM level_sales_rows WHERE customer_level = '01'),
              'non_member_sales_amount', (SELECT COALESCE(SUM(total_sales_amount), 0) FROM level_sales_rows WHERE customer_level NOT IN ('01', '02', '03', '04')),
              'level_total_person_count', (SELECT COALESCE(SUM(person_count), 0) FROM level_sales_rows),
              'black_diamond_person_count', (SELECT COALESCE(SUM(person_count), 0) FROM level_sales_rows WHERE customer_level = '04'),
              'black_gold_person_count', (SELECT COALESCE(SUM(person_count), 0) FROM level_sales_rows WHERE customer_level = '03'),
              'gold_star_person_count', (SELECT COALESCE(SUM(person_count), 0) FROM level_sales_rows WHERE customer_level = '02'),
              'silver_star_person_count', (SELECT COALESCE(SUM(person_count), 0) FROM level_sales_rows WHERE customer_level = '01'),
              'non_member_person_count', (SELECT COALESCE(SUM(person_count), 0) FROM level_sales_rows WHERE customer_level NOT IN ('01', '02', '03', '04')),
              'consumption_point', COALESCE(SUM(consumption_point), 0),
              'birthday_month_point', COALESCE(SUM(birthday_month_point), 0),
              'issue_count', COUNT(*) FILTER (WHERE status <> 'OK'),
              'missing_rate_count', COUNT(*) FILTER (WHERE status = 'MISSING_RATE'),
              'zero_rate_count', COUNT(*) FILTER (WHERE status = 'ZERO_RATE'),
              'allocation_imbalance_count', COUNT(*) FILTER (WHERE status = 'ALLOCATION_IMBALANCE'),
              'point_diff_count', COUNT(*) FILTER (WHERE status = 'POINT_DIFF')
            )
            FROM filtered_point_rows
          ) AS summary,
          COALESCE((
            SELECT jsonb_agg(row_to_json(item))
            FROM (
              SELECT DISTINCT
                COALESCE(NULLIF(department_code, ''), '未归属') AS department_code,
                COALESCE(NULLIF(department_name, ''), '未归属部门') AS department_name
              FROM base_point_rows
              ORDER BY department_name
            ) item
          ), '[]'::jsonb) AS department_options,
          COALESCE((
            SELECT jsonb_agg(row_to_json(item))
            FROM (
              SELECT
                COALESCE(NULLIF(department_code, ''), '未归属') AS department_code,
                COALESCE(NULLIF(department_name, ''), '未归属部门') AS department_name,
                COUNT(DISTINCT billno) AS ticket_count,
                COUNT(DISTINCT NULLIF(member_no, '')) AS member_count,
                COUNT(DISTINCT NULLIF(member_no, '')) FILTER (WHERE TRIM(BOTH FROM COALESCE(customer_level, '')) = '03') AS black_gold_member_count,
                COUNT(DISTINCT NULLIF(member_no, '')) FILTER (WHERE TRIM(BOTH FROM COALESCE(customer_level, '')) = '04') AS black_diamond_member_count,
                COALESCE(SUM(total_sales_amount), 0) AS total_sales_amount,
                COALESCE(SUM(point_basis_amount), 0) AS point_basis_amount,
                COALESCE(SUM(actual_point), 0) AS actual_point,
                COALESCE(SUM(expected_point), 0) AS expected_point,
                COALESCE(SUM(actual_point - expected_point), 0) AS point_diff,
                COUNT(*) FILTER (WHERE status <> 'OK') AS issue_count
              FROM filtered_point_rows
              GROUP BY 1, 2
              ORDER BY issue_count DESC, ABS(COALESCE(SUM(actual_point - expected_point), 0)) DESC, total_sales_amount DESC
              LIMIT :limit
            ) item
          ), '[]'::jsonb) AS departments,
          COALESCE((
            SELECT jsonb_agg(row_to_json(item))
            FROM (
              SELECT
                COALESCE(NULLIF(department_code, ''), '未归属') AS department_code,
                COALESCE(NULLIF(department_name, ''), '未归属部门') AS department_name,
                COALESCE(NULLIF(group_code, ''), '未归属') AS group_code,
                COALESCE(NULLIF(group_name, ''), '未归属柜组') AS group_name,
                COUNT(DISTINCT billno) AS ticket_count,
                COUNT(DISTINCT NULLIF(member_no, '')) AS member_count,
                COUNT(DISTINCT NULLIF(member_no, '')) FILTER (WHERE TRIM(BOTH FROM COALESCE(customer_level, '')) = '03') AS black_gold_member_count,
                COUNT(DISTINCT NULLIF(member_no, '')) FILTER (WHERE TRIM(BOTH FROM COALESCE(customer_level, '')) = '04') AS black_diamond_member_count,
                COALESCE(SUM(total_sales_amount), 0) AS total_sales_amount,
                COALESCE(SUM(point_basis_amount), 0) AS point_basis_amount,
                COALESCE(SUM(actual_point), 0) AS actual_point,
                COALESCE(SUM(expected_point), 0) AS expected_point,
                COALESCE(SUM(actual_point - expected_point), 0) AS point_diff,
                COUNT(*) FILTER (WHERE status <> 'OK') AS issue_count
              FROM filtered_point_rows
              GROUP BY 1, 2, 3, 4
              ORDER BY issue_count DESC, ABS(COALESCE(SUM(actual_point - expected_point), 0)) DESC, total_sales_amount DESC
              LIMIT :limit
            ) item
          ), '[]'::jsonb) AS groups,
          COALESCE((
            SELECT jsonb_agg(row_to_json(item))
            FROM (
              SELECT
                COALESCE(NULLIF(member_no, ''), '未刷卡') AS member_no,
                COALESCE(NULLIF(customer_level, ''), '未标识') AS customer_level,
                COUNT(DISTINCT billno) AS ticket_count,
                COUNT(DISTINCT COALESCE(NULLIF(department_code, ''), '未归属')) AS department_count,
                COALESCE(SUM(total_sales_amount), 0) AS total_sales_amount,
                COALESCE(SUM(point_basis_amount), 0) AS point_basis_amount,
                COALESCE(SUM(actual_point), 0) AS actual_point,
                COALESCE(SUM(expected_point), 0) AS expected_point,
                COALESCE(SUM(actual_point - expected_point), 0) AS point_diff,
                COUNT(*) FILTER (WHERE status <> 'OK') AS issue_count
              FROM filtered_point_rows
              WHERE 1=1
                {keyword_filter}
              GROUP BY 1, 2
              ORDER BY issue_count DESC, ABS(COALESCE(SUM(actual_point - expected_point), 0)) DESC, total_sales_amount DESC
              LIMIT :limit
            ) item
          ), '[]'::jsonb) AS members,
          COALESCE((
            SELECT jsonb_agg(row_to_json(item))
            FROM (
              SELECT
                billno,
                MIN(sale_time) AS sale_time,
                sale_date,
                COALESCE(NULLIF(member_no, ''), '未刷卡') AS member_no,
                COALESCE(NULLIF(customer_level, ''), '未标识') AS customer_level,
                COALESCE(NULLIF(department_code, ''), '未归属') AS department_code,
                COALESCE(NULLIF(department_name, ''), '未归属部门') AS department_name,
                COALESCE(NULLIF(group_code, ''), '未归属') AS group_code,
                COALESCE(NULLIF(group_name, ''), '未归属柜组') AS group_name,
                COALESCE(SUM(total_sales_amount), 0) AS total_sales_amount,
                COALESCE(SUM(point_basis_amount), 0) AS point_basis_amount,
                COALESCE(SUM(actual_point), 0) AS actual_point,
                COALESCE(SUM(expected_point), 0) AS expected_point,
                COALESCE(SUM(actual_point - expected_point), 0) AS point_diff,
                MAX(allocation_diff_amount) AS allocation_diff_amount,
                CASE
                  WHEN BOOL_OR(status = 'MISSING_RATE') THEN 'MISSING_RATE'
                  WHEN BOOL_OR(status = 'ZERO_RATE') THEN 'ZERO_RATE'
                  WHEN BOOL_OR(status = 'ALLOCATION_IMBALANCE') THEN 'ALLOCATION_IMBALANCE'
                  WHEN BOOL_OR(status = 'POINT_DIFF') THEN 'POINT_DIFF'
                  ELSE 'OK'
                END AS status
              FROM filtered_point_rows
              WHERE 1=1
                {member_filter}
              GROUP BY billno, sale_date, member_no, customer_level, department_code, department_name, group_code, group_name
              ORDER BY sale_time DESC, ABS(COALESCE(SUM(actual_point - expected_point), 0)) DESC
              LIMIT :limit
            ) item
          ), '[]'::jsonb) AS tickets
        """,
        params,
    ))
    departments = row.get("departments") or []
    departments.sort(key=department_display_sort_key)

    return {
        "summary": row.get("summary") or {},
        "departments": departments,
        "groups": row.get("groups") or [],
        "department_options": row.get("department_options") or [],
        "members": row.get("members") or [],
        "tickets": row.get("tickets") or [],
        "source_status": _execute_points_query(db, lambda: _point_rule_source_status(db)),
    }


@router.get("/points/overview")
async def points_overview(
    start_date: str = Query(..., description="销售日期起 YYYY-MM-DD"),
    end_date: str = Query(..., description="销售日期止 YYYY-MM-DD"),
    department_code: str | None = Query(None, description="部门编码"),
    group_code: str | None = Query(None, description="柜组编码"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, POINTS_ACTIVITY_ANALYSIS_PERMISSION)
    effective_range = _points_effective_date_range(start_date, end_date)
    if effective_range is None:
        return {"summary": {}, "source_status": []}
    effective_start_date, effective_end_exclusive = effective_range
    _ensure_required_tables(db)
    _ensure_point_rule_tables(db)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    params: dict[str, Any] = {
        "start_date": effective_start_date,
        "end_exclusive": effective_end_exclusive,
    }
    scope_sql = _points_business_scope_filter_sql(scope, params, prefix="points_overview")
    extra_filters = []
    if department_code:
        params["department_code"] = department_code.strip()
        extra_filters.append("AND UPPER(TRIM(COALESCE(department_code, ''))) = UPPER(TRIM(:department_code))")
    if group_code:
        params["group_code"] = group_code.strip()
        extra_filters.append("AND UPPER(TRIM(COALESCE(group_code, ''))) = UPPER(TRIM(:group_code))")

    summary = _execute_points_query(db, lambda: _one(
        db,
        _points_base_sql(scope_sql)
        + f"""
        SELECT
          COUNT(DISTINCT billno) AS ticket_count,
          COUNT(DISTINCT NULLIF(member_no, '')) AS member_count,
          COALESCE(SUM(total_sales_amount), 0) AS total_sales_amount,
          COALESCE(SUM(point_basis_amount), 0) AS point_basis_amount,
          COALESCE(SUM(actual_point), 0) AS actual_point,
          COALESCE(SUM(expected_point), 0) AS expected_point,
          COALESCE(SUM(actual_point - expected_point), 0) AS point_diff,
          COALESCE(SUM(consumption_point), 0) AS consumption_point,
          COALESCE(SUM(birthday_month_point), 0) AS birthday_month_point,
          COUNT(*) FILTER (WHERE status <> 'OK') AS issue_count,
          COUNT(*) FILTER (WHERE status = 'MISSING_RATE') AS missing_rate_count,
          COUNT(*) FILTER (WHERE status = 'ZERO_RATE') AS zero_rate_count,
          COUNT(*) FILTER (WHERE status = 'ALLOCATION_IMBALANCE') AS allocation_imbalance_count,
          COUNT(*) FILTER (WHERE status = 'POINT_DIFF') AS point_diff_count
        FROM point_rows
        WHERE 1=1
          {" ".join(extra_filters)}
        """,
        params,
    ))
    return {
        "summary": summary,
        "source_status": _execute_points_query(db, lambda: _point_rule_source_status(db)),
    }


@router.get("/points/departments")
async def points_departments(
    start_date: str = Query(..., description="销售日期起 YYYY-MM-DD"),
    end_date: str = Query(..., description="销售日期止 YYYY-MM-DD"),
    department_code: str | None = Query(None, description="部门编码"),
    group_code: str | None = Query(None, description="柜组编码"),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, POINTS_ACTIVITY_ANALYSIS_PERMISSION)
    effective_range = _points_effective_date_range(start_date, end_date)
    if effective_range is None:
        return {"items": [], "source_status": []}
    effective_start_date, effective_end_exclusive = effective_range
    _ensure_required_tables(db)
    _ensure_point_rule_tables(db)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    params: dict[str, Any] = {
        "start_date": effective_start_date,
        "end_exclusive": effective_end_exclusive,
        "limit": limit,
    }
    scope_sql = _points_business_scope_filter_sql(scope, params, prefix="points_departments")
    extra_filters = []
    if department_code:
        params["department_code"] = department_code.strip()
        extra_filters.append("AND UPPER(TRIM(COALESCE(department_code, ''))) = UPPER(TRIM(:department_code))")
    if group_code:
        params["group_code"] = group_code.strip()
        extra_filters.append("AND UPPER(TRIM(COALESCE(group_code, ''))) = UPPER(TRIM(:group_code))")

    items = _execute_points_query(db, lambda: _rows(
        db,
        _points_base_sql(scope_sql)
        + f"""
        SELECT
          COALESCE(NULLIF(department_code, ''), '未归属') AS department_code,
          COALESCE(NULLIF(department_name, ''), '未归属部门') AS department_name,
          COALESCE(NULLIF(group_code, ''), '未归属') AS group_code,
          COALESCE(NULLIF(group_name, ''), '未归属柜组') AS group_name,
          COUNT(DISTINCT billno) AS ticket_count,
          COUNT(DISTINCT NULLIF(member_no, '')) AS member_count,
          COALESCE(SUM(total_sales_amount), 0) AS total_sales_amount,
          COALESCE(SUM(point_basis_amount), 0) AS point_basis_amount,
          COALESCE(SUM(actual_point), 0) AS actual_point,
          COALESCE(SUM(expected_point), 0) AS expected_point,
          COALESCE(SUM(actual_point - expected_point), 0) AS point_diff,
          COUNT(*) FILTER (WHERE status <> 'OK') AS issue_count
        FROM point_rows
        WHERE 1=1
          {" ".join(extra_filters)}
        GROUP BY 1, 2, 3, 4
        ORDER BY issue_count DESC, ABS(COALESCE(SUM(actual_point - expected_point), 0)) DESC, total_sales_amount DESC
        LIMIT :limit
        """,
        params,
    ))
    return {
        "items": items,
        "source_status": _execute_points_query(db, lambda: _point_rule_source_status(db)),
    }


@router.get("/points/members")
async def points_members(
    start_date: str = Query(..., description="销售日期起 YYYY-MM-DD"),
    end_date: str = Query(..., description="销售日期止 YYYY-MM-DD"),
    department_code: str | None = Query(None, description="部门编码"),
    group_code: str | None = Query(None, description="柜组编码"),
    keyword: str | None = Query(None, description="会员号/等级搜索"),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, POINTS_ACTIVITY_ANALYSIS_PERMISSION)
    effective_range = _points_effective_date_range(start_date, end_date)
    if effective_range is None:
        return {"items": [], "source_status": []}
    effective_start_date, effective_end_exclusive = effective_range
    _ensure_required_tables(db)
    _ensure_point_rule_tables(db)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    params: dict[str, Any] = {
        "start_date": effective_start_date,
        "end_exclusive": effective_end_exclusive,
        "limit": limit,
    }
    scope_sql = _points_business_scope_filter_sql(scope, params, prefix="points_members")
    extra_filters = []
    if department_code:
        params["department_code"] = department_code.strip()
        extra_filters.append("AND UPPER(TRIM(COALESCE(department_code, ''))) = UPPER(TRIM(:department_code))")
    if group_code:
        params["group_code"] = group_code.strip()
        extra_filters.append("AND UPPER(TRIM(COALESCE(group_code, ''))) = UPPER(TRIM(:group_code))")
    if keyword:
        params["keyword"] = f"%{keyword.strip()}%"
        extra_filters.append("AND (member_no ILIKE :keyword OR customer_level ILIKE :keyword)")

    items = _execute_points_query(db, lambda: _rows(
        db,
        _points_base_sql(scope_sql)
        + f"""
        SELECT
          COALESCE(NULLIF(member_no, ''), '未刷卡') AS member_no,
          COALESCE(NULLIF(customer_level, ''), '未标识') AS customer_level,
          COUNT(DISTINCT billno) AS ticket_count,
          COUNT(DISTINCT COALESCE(NULLIF(department_code, ''), '未归属')) AS department_count,
          COALESCE(SUM(total_sales_amount), 0) AS total_sales_amount,
          COALESCE(SUM(point_basis_amount), 0) AS point_basis_amount,
          COALESCE(SUM(actual_point), 0) AS actual_point,
          COALESCE(SUM(expected_point), 0) AS expected_point,
          COALESCE(SUM(actual_point - expected_point), 0) AS point_diff,
          COUNT(*) FILTER (WHERE status <> 'OK') AS issue_count
        FROM point_rows
        WHERE 1=1
          {" ".join(extra_filters)}
        GROUP BY 1, 2
        ORDER BY issue_count DESC, ABS(COALESCE(SUM(actual_point - expected_point), 0)) DESC, total_sales_amount DESC
        LIMIT :limit
        """,
        params,
    ))
    return {
        "items": items,
        "source_status": _execute_points_query(db, lambda: _point_rule_source_status(db)),
    }


@router.get("/points/tickets")
async def points_tickets(
    start_date: str = Query(..., description="销售日期起 YYYY-MM-DD"),
    end_date: str = Query(..., description="销售日期止 YYYY-MM-DD"),
    department_code: str | None = Query(None, description="部门编码"),
    group_code: str | None = Query(None, description="柜组编码"),
    member_no: str | None = Query(None, description="会员号"),
    status_filter: str | None = Query(None, alias="status", description="OK/POINT_DIFF/MISSING_RATE/ZERO_RATE/ALLOCATION_IMBALANCE"),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, POINTS_ACTIVITY_ANALYSIS_PERMISSION)
    effective_range = _points_effective_date_range(start_date, end_date)
    if effective_range is None:
        return {"items": [], "source_status": []}
    effective_start_date, effective_end_exclusive = effective_range
    _ensure_required_tables(db)
    _ensure_point_rule_tables(db)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    params: dict[str, Any] = {
        "start_date": effective_start_date,
        "end_exclusive": effective_end_exclusive,
        "limit": limit,
    }
    scope_sql = _points_business_scope_filter_sql(scope, params, prefix="points_tickets")
    extra_filters = []
    if department_code:
        params["department_code"] = department_code.strip()
        extra_filters.append("AND UPPER(TRIM(COALESCE(department_code, ''))) = UPPER(TRIM(:department_code))")
    if group_code:
        params["group_code"] = group_code.strip()
        extra_filters.append("AND UPPER(TRIM(COALESCE(group_code, ''))) = UPPER(TRIM(:group_code))")
    if member_no:
        params["member_no"] = member_no.strip()
        extra_filters.append("AND UPPER(TRIM(COALESCE(member_no, ''))) = UPPER(TRIM(:member_no))")
    if status_filter:
        params["status_filter"] = status_filter.strip().upper()
        extra_filters.append("AND status = :status_filter")

    items = _execute_points_query(db, lambda: _rows(
        db,
        _points_base_sql(scope_sql)
        + f"""
        SELECT
          billno,
          MIN(sale_time) AS sale_time,
          sale_date,
          COALESCE(NULLIF(member_no, ''), '未刷卡') AS member_no,
          COALESCE(NULLIF(customer_level, ''), '未标识') AS customer_level,
          COALESCE(NULLIF(department_code, ''), '未归属') AS department_code,
          COALESCE(NULLIF(department_name, ''), '未归属部门') AS department_name,
          COALESCE(NULLIF(group_code, ''), '未归属') AS group_code,
          COALESCE(NULLIF(group_name, ''), '未归属柜组') AS group_name,
          COALESCE(SUM(total_sales_amount), 0) AS total_sales_amount,
          COALESCE(SUM(point_basis_amount), 0) AS point_basis_amount,
          COALESCE(SUM(actual_point), 0) AS actual_point,
          COALESCE(SUM(expected_point), 0) AS expected_point,
          COALESCE(SUM(actual_point - expected_point), 0) AS point_diff,
          MAX(allocation_diff_amount) AS allocation_diff_amount,
          CASE
            WHEN BOOL_OR(status = 'MISSING_RATE') THEN 'MISSING_RATE'
            WHEN BOOL_OR(status = 'ZERO_RATE') THEN 'ZERO_RATE'
            WHEN BOOL_OR(status = 'ALLOCATION_IMBALANCE') THEN 'ALLOCATION_IMBALANCE'
            WHEN BOOL_OR(status = 'POINT_DIFF') THEN 'POINT_DIFF'
            ELSE 'OK'
          END AS status
        FROM point_rows
        WHERE 1=1
          {" ".join(extra_filters)}
        GROUP BY billno, sale_date, member_no, customer_level, department_code, department_name, group_code, group_name
        ORDER BY sale_time DESC, ABS(COALESCE(SUM(actual_point - expected_point), 0)) DESC
        LIMIT :limit
        """,
        params,
    ))
    return {
        "items": items,
        "source_status": _execute_points_query(db, lambda: _point_rule_source_status(db)),
    }


@router.get("/store-options")
async def activity_store_options(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, ACTIVITY_ANALYSIS_PERMISSION)
    business_scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    return _activity_store_options_for_scope(db, business_scope)


@router.get("/activities")
async def activities(
    start_date: str | None = Query(None, description="活动开始日期下限 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="活动结束日期上限 YYYY-MM-DD"),
    keyword: str | None = Query(None, description="活动编码/主题"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, ACTIVITY_ANALYSIS_PERMISSION)
    _ensure_required_tables(db)

    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
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
    activity_scope_sql = _activity_scope_filter_sql(db, scope, params, alias="p", prefix="activities")
    if activity_scope_sql:
        filters.append(activity_scope_sql.removeprefix(" AND "))

    return _rows(
        db,
        f"""
        WITH log_bill AS (
          SELECT
            l.tcflpopid AS activity_id,
            h.billno,
            SUM({ACTION_AMOUNT_SQL}) AS log_amount,
            SUM({_issued_amount_sql("l")}) AS issued_log_amount,
            SUM(CASE WHEN l.tcflzy = 'O' THEN ABS(COALESCE(l.tcflmoney, 0)) WHEN l.tcflzy = 'U' THEN -ABS(COALESCE(l.tcflmoney, 0)) ELSE 0 END) AS consumed_log_amount,
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
          SELECT
            lb.activity_id,
            p.billno,
            SUM(COALESCE(p.je, 0)) AS coupon_pay_amount
          FROM salepay p
          JOIN log_bill lb
            ON lb.billno = p.billno
          JOIN tktcardfqlog l
            ON l.tcflpopid = lb.activity_id
           AND l.tcflzy = 'O'
           AND p.batch = l.tcflsyjtrace::varchar
          WHERE p.paycode IN ('0500', '0580')
          GROUP BY lb.activity_id, p.billno
        )
        SELECT
          p.tpiid AS activity_id,
          p.tpiname AS activity_name,
          {_activity_store_id_sql("p")} AS store_id,
          {_activity_store_code_sql("p")} AS store_code,
          {_activity_store_name_sql("p")} AS store_name,
          p.tpistartdate AS start_date,
          p.tpienddate AS end_date,
          COALESCE(COUNT(DISTINCT lb.billno), 0) AS ticket_count,
          COALESCE(SUM(lb.log_amount), 0) AS card_log_amount,
          COALESCE(SUM(lb.issued_log_amount), 0) AS issued_log_amount,
          COALESCE(SUM(lb.consumed_log_amount), 0) AS consumed_log_amount,
          COALESCE(SUM(pb.coupon_pay_amount), 0) AS coupon_pay_amount
        FROM tktpopinfo p
        LEFT JOIN log_bill lb ON lb.activity_id = p.tpiid
        LEFT JOIN pay_bill pb ON pb.activity_id = p.tpiid AND pb.billno = lb.billno
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
    scope: str = Query("activity", pattern="^(activity|standalone|all)$", description="activity 活动档期券；standalone 非档期券；all 全部卡券"),
    start_date: str | None = Query(None, description="日志日期起 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="日志日期止 YYYY-MM-DD"),
    store_code: str | None = Query(None, description="门店编码"),
    limit: int = Query(20, ge=5, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, ACTIVITY_ANALYSIS_PERMISSION)
    _ensure_required_tables(db)

    business_scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    activity_scope_params: dict[str, Any] = {}
    activity_scope_sql = _activity_scope_filter_sql(db, business_scope, activity_scope_params, alias="p", prefix="overview")
    log_scope_sql = _activity_log_scope_filter_sql(db, business_scope, activity_scope_params, alias="l", prefix="overview_logs")
    log_filter, log_params = _activity_filter(activity_id, start_date, end_date, scope, activity_scope_sql, log_scope_sql)
    period_filter, period_params = _period_filter(activity_id, start_date, end_date)
    params = {**activity_scope_params, **log_params, **period_params, "limit": limit}
    params.setdefault("activity_id", None)
    params.setdefault("start_date", None)
    params.setdefault("end_date", None)
    selected_store_code = _require_selected_activity_store(db, business_scope, store_code)
    selected_log_store_sql = _selected_store_clause(
        selected_store_code,
        params,
        expression="l.tcflmkt",
        prefix="overview_logs",
    )
    log_filter = f"({log_filter}){selected_log_store_sql}"
    period_scope_sql = _activity_market_scope_filter_sql(
        db,
        business_scope,
        params,
        expression="h.mkt",
        prefix="overview_period_scope",
    )
    period_store_sql = _selected_store_clause(
        selected_store_code,
        params,
        expression="h.mkt",
        prefix="overview_period",
    )
    period_filter = f"({period_filter}){period_scope_sql}{period_store_sql}"

    activity = None
    if activity_id:
        activity = _one(
            db,
            f"""
            SELECT
              p.tpiid AS activity_id,
              p.tpiname AS activity_name,
              {_activity_store_id_sql("p")} AS store_id,
              {_activity_store_code_sql("p")} AS store_code,
              {_activity_store_name_sql("p")} AS store_name,
              tpistartdate AS start_date,
              tpienddate AS end_date,
              tpiyqstartdate AS coupon_start_date,
              tpiyqenddate AS coupon_end_date,
              tpmemo AS memo
            FROM tktpopinfo p
            WHERE p.tpiid = :activity_id
              {activity_scope_sql}
            """,
            params,
        )
        if not activity:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="活动不存在或无数据权限")

    summary = _one(
        db,
        f"""
        WITH raw_logs AS MATERIALIZED (
          SELECT l.*
               , {ACTION_AMOUNT_SQL} AS action_amount
          FROM tktcardfqlog l
          WHERE {log_filter}
        ),
        matched_logs AS MATERIALIZED (
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
        pay_trace AS MATERIALIZED (
          SELECT DISTINCT billno, tcflsyjtrace
          FROM matched_logs
          WHERE tcflzy = 'O' AND tcflsyjtrace IS NOT NULL
        ),
        log_bill AS MATERIALIZED (
          SELECT
            billno,
            MIN(hykh) AS member_no,
            COUNT(*) AS log_count,
            SUM(COALESCE(tcflmoney, 0)) AS raw_card_log_amount,
            SUM(action_amount) AS card_log_amount,
            SUM({_issued_amount_sql()}) AS issued_log_amount,
            SUM(CASE WHEN tcflzy = 'O' THEN ABS(COALESCE(tcflmoney, 0)) WHEN tcflzy = 'U' THEN -ABS(COALESCE(tcflmoney, 0)) ELSE 0 END) AS consumed_log_amount,
            SUM(CASE WHEN tcflzy NOT IN ('F', 'O', 'U') THEN COALESCE(tcflmoney, 0) ELSE 0 END) AS other_log_amount
          FROM matched_logs
          GROUP BY billno
        ),
        pay_bill AS MATERIALIZED (
          SELECT
            p.billno,
            SUM(CASE WHEN p.paycode = '0500' THEN COALESCE(p.je, 0) ELSE 0 END) AS pay_0500_amount,
            SUM(CASE WHEN p.paycode = '0580' THEN COALESCE(p.je, 0) ELSE 0 END) AS pay_0580_amount,
            SUM(COALESCE(p.je, 0)) AS coupon_pay_amount,
            COUNT(*) AS coupon_pay_count
          FROM salepay p
          JOIN pay_trace pt
            ON pt.billno = p.billno
           AND p.batch = pt.tcflsyjtrace::varchar
          WHERE p.paycode IN ('0500', '0580')
          GROUP BY p.billno
        ),
        sales_bill AS MATERIALIZED (
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
        )
        SELECT
          COUNT(DISTINCT lb.billno) AS ticket_count,
          COUNT(DISTINCT NULLIF(lb.member_no, '')) AS member_count,
          COALESCE(SUM(lb.log_count), 0) AS card_log_count,
          COALESCE(SUM(lb.raw_card_log_amount), 0) AS raw_card_log_amount,
          COALESCE(SUM(lb.card_log_amount), 0) AS card_log_amount,
          COALESCE(SUM(lb.issued_log_amount), 0) AS issued_log_amount,
          COALESCE(SUM(lb.consumed_log_amount), 0) AS consumed_log_amount,
          COALESCE(SUM(lb.other_log_amount), 0) AS other_log_amount,
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
          0 AS new_member_count,
          0 AS new_member_sales_amount,
          0 AS period_coupon_pay_count,
          0 AS period_coupon_pay_amount
        FROM log_bill lb
        LEFT JOIN pay_bill pb ON pb.billno = lb.billno
        LEFT JOIN sales_bill sb ON sb.billno = lb.billno
        """,
        params,
    )

    new_member_summary = _one(
        db,
        f"""
        WITH raw_logs AS MATERIALIZED (
          SELECT l.*
          FROM tktcardfqlog l
          WHERE {log_filter}
        ),
        matched_logs AS MATERIALIZED (
          SELECT
            h.billno,
            h.hykh
          FROM raw_logs l
          JOIN salehead h
            ON l.tcflmkt = h.mkt
           AND l.tcflsyjid = h.syjh
           AND l.tcflinvno ~ '^[0-9]+$'
           AND h.fphm = l.tcflinvno::numeric
        ),
        log_bill AS MATERIALIZED (
          SELECT
            billno,
            MIN(hykh) AS member_no
          FROM matched_logs
          GROUP BY billno
        ),
        sales_bill AS MATERIALIZED (
          SELECT
            s.sglbillno AS billno,
            SUM(COALESCE(s.sglxssr, 0)) AS sales_amount
          FROM salegoodslist s
          JOIN log_bill lb ON lb.billno = s.sglbillno
          GROUP BY s.sglbillno
        ),
        member_keys AS MATERIALIZED (
          SELECT DISTINCT UPPER(TRIM(COALESCE(member_no, ''))) AS member_no_key
          FROM log_bill
          WHERE COALESCE(member_no, '') <> ''
        ),
        member_dim AS MATERIALIZED (
          SELECT
            UPPER(TRIM(COALESCE(m.customer_no, ''))) AS member_no_key,
            MIN(m.admission_date) AS admission_date
          FROM fj_dw_member_dim m
          JOIN member_keys mk
            ON UPPER(TRIM(COALESCE(m.customer_no, ''))) = mk.member_no_key
          GROUP BY 1
        ),
        new_member_bill AS (
          SELECT
            lb.billno,
            lb.member_no,
            COALESCE(sb.sales_amount, 0) AS sales_amount
          FROM log_bill lb
          JOIN member_dim m
            ON m.member_no_key = UPPER(TRIM(COALESCE(lb.member_no, '')))
          LEFT JOIN sales_bill sb ON sb.billno = lb.billno
          WHERE lb.member_no IS NOT NULL
            AND COALESCE(lb.member_no, '') <> ''
            AND m.admission_date BETWEEN
              CASE WHEN :activity_id IS NOT NULL
                THEN COALESCE((SELECT tpistartdate FROM tktpopinfo WHERE tpiid = :activity_id), DATE '1900-01-01')
                ELSE COALESCE(CAST(:start_date AS date), DATE '1900-01-01')
              END
              AND
              CASE WHEN :activity_id IS NOT NULL
                THEN COALESCE((SELECT tpienddate FROM tktpopinfo WHERE tpiid = :activity_id), DATE '2999-12-31')
                ELSE COALESCE(CAST(:end_date AS date), DATE '2999-12-31')
              END
        )
        SELECT
          COALESCE(COUNT(DISTINCT member_no), 0) AS new_member_count,
          COALESCE(SUM(sales_amount), 0) AS new_member_sales_amount
        FROM new_member_bill
        """,
        params,
    )
    period_pay_summary = _one(
        db,
        f"""
        SELECT
          COUNT(*) AS period_coupon_pay_count,
          COALESCE(SUM(COALESCE(p.je, 0)), 0) AS period_coupon_pay_amount
        FROM salepay p
        JOIN salehead h ON h.billno = p.billno
        WHERE p.paycode IN ('0500', '0580')
          AND {period_filter}
        """,
        params,
    )
    summary.update(new_member_summary)
    summary.update(period_pay_summary)

    payment_methods = _rows(
        db,
        f"""
        WITH matched_logs AS (
          SELECT
            h.billno,
            l.tcflzy,
            l.tcflmoney,
            l.tcflsyjtrace,
            COALESCE(NULLIF(l.tcfljetype, ''), '未标识') AS coupon_type
          FROM tktcardfqlog l
          JOIN salehead h
            ON l.tcflmkt = h.mkt
           AND l.tcflsyjid = h.syjh
           AND l.tcflinvno ~ '^[0-9]+$'
           AND h.fphm = l.tcflinvno::numeric
          WHERE {log_filter}
        ),
        coupon_logs AS (
          SELECT
            coupon_type,
            COUNT(*) AS log_count,
            SUM({_issued_amount_sql()}) AS issued_log_amount,
            SUM(CASE WHEN tcflzy = 'O' THEN ABS(COALESCE(tcflmoney, 0)) WHEN tcflzy = 'U' THEN -ABS(COALESCE(tcflmoney, 0)) ELSE 0 END) AS consumed_log_amount
          FROM matched_logs
          GROUP BY coupon_type
        ),
        pay_trace AS (
          SELECT DISTINCT billno, tcflsyjtrace, coupon_type
          FROM matched_logs
          WHERE tcflzy = 'O' AND tcflsyjtrace IS NOT NULL
        )
        SELECT
          p.paycode,
          COALESCE(NULLIF(p.payname, ''), '未命名') AS payname,
          pt.coupon_type,
          COUNT(*) AS payment_count,
          SUM(COALESCE(p.je, 0)) AS payment_amount,
          COALESCE(MAX(cl.log_count), 0) AS coupon_log_count,
          COALESCE(MAX(cl.issued_log_amount), 0) AS issued_log_amount,
          COALESCE(MAX(cl.consumed_log_amount), 0) AS consumed_log_amount
        FROM salepay p
        JOIN pay_trace pt
          ON pt.billno = p.billno
         AND p.batch = pt.tcflsyjtrace::varchar
        LEFT JOIN coupon_logs cl ON cl.coupon_type = pt.coupon_type
        WHERE p.paycode IN ('0500', '0580')
        GROUP BY p.paycode, COALESCE(NULLIF(p.payname, ''), '未命名'), pt.coupon_type
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
        ),
        matched_logs AS (
          SELECT
            h.billno,
            l.tcflzy,
            l.tcflmoney,
            l.tcflsyjtrace
          FROM tktcardfqlog l
          JOIN salehead h
            ON l.tcflmkt = h.mkt
           AND l.tcflsyjid = h.syjh
           AND l.tcflinvno ~ '^[0-9]+$'
           AND h.fphm = l.tcflinvno::numeric
          WHERE {log_filter}
        ),
        pay_bill AS (
          SELECT
            p.billno,
            SUM(COALESCE(p.je, 0)) AS coupon_pay_amount
          FROM salepay p
          JOIN matched_logs ml
            ON ml.billno = p.billno
           AND ml.tcflzy = 'O'
           AND p.batch = ml.tcflsyjtrace::varchar
          WHERE p.paycode IN ('0500', '0580')
          GROUP BY p.billno
        ),
        log_bill AS (
          SELECT
            billno,
            SUM({_issued_amount_sql()}) AS issued_log_amount,
            SUM(CASE WHEN tcflzy = 'O' THEN ABS(COALESCE(tcflmoney, 0)) WHEN tcflzy = 'U' THEN -ABS(COALESCE(tcflmoney, 0)) ELSE 0 END) AS consumed_log_amount
          FROM matched_logs
          GROUP BY billno
        ),
        {_supplier_discount_cte()},
        manaframe_groups AS (
          SELECT
            mf.mfcode AS group_code,
            mf.mfcname AS group_name,
            dept.mfcode AS department_code,
            dept.mfcname AS department_name
          FROM manaframe mf
          LEFT JOIN manaframe dept
            ON UPPER(TRIM(COALESCE(mf.mfpcode, ''))) = UPPER(TRIM(COALESCE(dept.mfcode, '')))
        ),
        sales_group AS (
          SELECT
            s.sglbillno AS billno,
            COALESCE(NULLIF(cg.department_code, ''), '未归属') AS department_code,
            COALESCE(NULLIF(cg.department_name, ''), '未归属部门') AS department_name,
            COALESCE(NULLIF(cg.group_code, ''), COALESCE(NULLIF(s.sglmfid, ''), '未归属')) AS group_code,
            COALESCE(NULLIF(cg.group_name, ''), COALESCE(NULLIF(s.sglmfid, ''), '未归属柜组')) AS group_name,
            SUM(COALESCE(s.sglxssr, 0)) AS sales_amount,
            SUM(COALESCE(s.sgln13, 0)) AS sales_cost,
            SUM(COALESCE(s.sgln2, 0)) AS gross_profit,
            SUM(COALESCE(s.sglnetml, s.sgln2, 0)) AS net_profit,
            SUM(COALESCE(s.sglsqje, 0)) AS received_coupon_amount,
            SUM(COALESCE(s.sglfqje, 0)) AS issued_coupon_amount,
            SUM(COALESCE(s.sglthss, 0)) AS return_loss,
            COALESCE(MAX(sd.pay_discount_amount), 0) AS pay_discount_amount,
            COALESCE(MAX(sd.supplier_discount_amount), 0) AS supplier_discount_amount,
            COALESCE(MAX(sd.shop_discount_amount), 0) AS shop_discount_amount
          FROM salegoodslist s
          JOIN matched_bills mb ON mb.billno = s.sglbillno
          LEFT JOIN manaframe_groups cg ON UPPER(TRIM(COALESCE(cg.group_code, ''))) = UPPER(TRIM(COALESCE(s.sglmfid, '')))
          LEFT JOIN supplier_discount sd ON sd.billno = s.sglbillno AND UPPER(TRIM(COALESCE(sd.group_code, ''))) = UPPER(TRIM(COALESCE(s.sglmfid, '')))
          WHERE 1=1 {_sales_department_exclusion_sql("cg")}
          GROUP BY 1, 2, 3, 4, 5
        ),
        bill_totals AS (
          SELECT
            billno,
            SUM(sales_amount) AS bill_sales_amount,
            COUNT(DISTINCT department_code) AS bill_department_count,
            COUNT(DISTINCT group_code) AS bill_group_count
          FROM sales_group
          GROUP BY billno
        ),
        allocated AS (
          SELECT
            sg.*,
            CASE
              WHEN COALESCE(bt.bill_sales_amount, 0) <> 0 THEN sg.sales_amount / bt.bill_sales_amount
              ELSE 0
            END AS allocation_ratio,
            COALESCE(pb.coupon_pay_amount, 0) AS bill_coupon_pay_amount,
            COALESCE(lb.issued_log_amount, 0) AS bill_issued_log_amount,
            COALESCE(lb.consumed_log_amount, 0) AS bill_consumed_log_amount,
            bt.bill_department_count,
            bt.bill_group_count
          FROM sales_group sg
          JOIN bill_totals bt ON bt.billno = sg.billno
          LEFT JOIN pay_bill pb ON pb.billno = sg.billno
          LEFT JOIN log_bill lb ON lb.billno = sg.billno
        )
        SELECT
          department_code,
          department_name,
          {_code_name_display_sql("department_code", "department_name")} AS department_display,
          group_code,
          group_name,
          {_code_name_display_sql("group_code", "group_name")} AS group_display,
          COUNT(DISTINCT billno) AS ticket_count,
          COUNT(DISTINCT CASE WHEN bill_department_count > 1 THEN billno END) AS cross_department_ticket_count,
          COUNT(DISTINCT CASE WHEN bill_group_count > 1 THEN billno END) AS cross_group_ticket_count,
          SUM(sales_amount) AS sales_amount,
          SUM(sales_cost) AS sales_cost,
          SUM(gross_profit) AS gross_profit,
          SUM(net_profit) AS net_profit,
          SUM(received_coupon_amount) AS received_coupon_amount,
          SUM(issued_coupon_amount) AS issued_coupon_amount,
          SUM(return_loss) AS return_loss,
          SUM(pay_discount_amount) AS pay_discount_amount,
          SUM(supplier_discount_amount) AS supplier_discount_amount,
          SUM(shop_discount_amount) AS shop_discount_amount,
          SUM(bill_coupon_pay_amount * allocation_ratio) AS allocated_coupon_pay_amount,
          SUM(bill_issued_log_amount * allocation_ratio) AS allocated_issued_log_amount,
          SUM(bill_consumed_log_amount * allocation_ratio) AS allocated_consumed_log_amount
        FROM allocated
        GROUP BY 1, 2, 3, 4, 5, 6
        ORDER BY allocated_coupon_pay_amount DESC, sales_amount DESC
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
          COALESCE(NULLIF(cb.cbcname, ''), '') AS brand_name,
          {_code_name_display_sql("s.sglppcode", "cb.cbcname")} AS brand_display,
          s.sglcatid AS category_code,
          COALESCE(NULLIF(gc.catcname, ''), '') AS category_name,
          {_code_name_display_sql("s.sglcatid", "gc.catcname")} AS category_display,
          COUNT(DISTINCT s.sglbillno) AS ticket_count,
          SUM(COALESCE(s.sglsl, 0)) AS quantity,
          SUM(COALESCE(s.sglxssr, 0)) AS sales_amount,
          SUM(COALESCE(s.sgln2, 0)) AS gross_profit,
          SUM(COALESCE(s.sglnetml, s.sgln2, 0)) AS net_profit,
          SUM(COALESCE(s.sglsqje, 0)) AS received_coupon_amount
        FROM salegoodslist s
        JOIN matched_bills mb ON mb.billno = s.sglbillno
        LEFT JOIN goodsbase gb ON UPPER(TRIM(COALESCE(gb.gbid, ''))) = UPPER(TRIM(COALESCE(s.sglgdid, '')))
        {_brand_join_sql("s", "cb")}
        {_category_join_sql("s", "gc")}
        GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
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
          SELECT l.tcflseqno, l.tcflzy, l.tcflsyjtrace, h.billno
          FROM raw_logs l
          JOIN salehead h
            ON l.tcflmkt = h.mkt
           AND l.tcflsyjid = h.syjh
           AND l.tcflinvno ~ '^[0-9]+$'
           AND h.fphm = l.tcflinvno::numeric
        ),
        period_pay AS (
          SELECT p.billno, p.rowno, p.batch
          FROM salepay p
          JOIN salehead h ON h.billno = p.billno
          WHERE p.paycode IN ('0500', '0580')
            AND {period_filter}
        ),
        period_coupon_logs AS (
          SELECT l.tcflvipno, l.tcflsyjtrace
          FROM tktcardfqlog l
          WHERE l.tcflsyjtrace IS NOT NULL
        )
        SELECT
          (SELECT COUNT(*) FROM raw_logs) AS raw_log_count,
          (SELECT COUNT(*) FROM matched_logs) AS matched_log_count,
          (SELECT COUNT(*) FROM raw_logs) - (SELECT COUNT(*) FROM matched_logs) AS unmatched_log_count,
          (SELECT COUNT(*) FROM period_pay) AS period_coupon_payment_count,
          (
            SELECT COUNT(*)
            FROM period_pay pp
            WHERE NOT EXISTS (
              SELECT 1
              FROM period_coupon_logs pcl
              WHERE pp.batch = pcl.tcflsyjtrace::varchar
            )
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


@router.get("/coupon-type-departments")
async def coupon_type_departments(
    activity_id: str | None = Query(None),
    scope: str = Query("activity", pattern="^(activity|standalone|all)$"),
    coupon_type: str = Query(...),
    department_code: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    store_code: str | None = Query(None, description="门店编码"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, ACTIVITY_ANALYSIS_PERMISSION)
    _ensure_required_tables(db)

    business_scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    params: dict[str, Any] = {}
    activity_scope_sql = _activity_scope_filter_sql(db, business_scope, params, alias="p", prefix="coupon_depts")
    log_scope_sql = _activity_log_scope_filter_sql(db, business_scope, params, alias="l", prefix="coupon_depts_logs")
    log_filter, log_params = _activity_filter(activity_id, start_date, end_date, scope, activity_scope_sql, log_scope_sql)
    params.update(log_params)
    selected_store_code = _require_selected_activity_store(db, business_scope, store_code)
    selected_store_sql = _selected_store_clause(
        selected_store_code,
        params,
        expression="l.tcflmkt",
        prefix="coupon_depts",
    )
    log_filter = f"({log_filter}){selected_store_sql}"
    coupon_filter, coupon_params = _coupon_type_filter(coupon_type)
    params.update(coupon_params)
    params.update({"department_code": department_code, "limit": limit})
    level_filter = "AND a.department_code = :department_code" if department_code else ""
    group_select = (
        f"a.group_code, a.group_name, {_code_name_display_sql('a.group_code', 'a.group_name')} AS group_display,"
        if department_code
        else "NULL::varchar AS group_code, NULL::varchar AS group_name, NULL::varchar AS group_display,"
    )
    group_by = "1, 2, 3, 4, 5, 6" if department_code else "1, 2, 3"

    return _rows(
        db,
        f"""
        WITH matched_logs AS (
          SELECT
            h.billno,
            l.tcflzy,
            l.tcflmoney,
            l.tcflsyjtrace
          FROM tktcardfqlog l
          JOIN salehead h
            ON l.tcflmkt = h.mkt
           AND l.tcflsyjid = h.syjh
           AND l.tcflinvno ~ '^[0-9]+$'
           AND h.fphm = l.tcflinvno::numeric
          WHERE {log_filter}
            {coupon_filter}
        ),
        pay_bill AS (
          SELECT
            p.billno,
            SUM(COALESCE(p.je, 0)) AS coupon_pay_amount
          FROM salepay p
          JOIN matched_logs ml
            ON ml.billno = p.billno
           AND ml.tcflzy = 'O'
           AND p.batch = ml.tcflsyjtrace::varchar
          WHERE p.paycode IN ('0500', '0580')
          GROUP BY p.billno
        ),
        log_bill AS (
          SELECT
            billno,
            SUM({_issued_amount_sql()}) AS issued_log_amount,
            SUM(CASE WHEN tcflzy = 'O' THEN ABS(COALESCE(tcflmoney, 0)) WHEN tcflzy = 'U' THEN -ABS(COALESCE(tcflmoney, 0)) ELSE 0 END) AS consumed_log_amount
          FROM matched_logs
          GROUP BY billno
        ),
        {_supplier_discount_cte("AND COALESCE(sgpqtype, '') = :coupon_type")},
        manaframe_groups AS (
          SELECT
            mf.mfcode AS group_code,
            mf.mfcname AS group_name,
            dept.mfcode AS department_code,
            dept.mfcname AS department_name
          FROM manaframe mf
          LEFT JOIN manaframe dept
            ON UPPER(TRIM(COALESCE(mf.mfpcode, ''))) = UPPER(TRIM(COALESCE(dept.mfcode, '')))
        ),
        sales_group AS (
          SELECT
            s.sglbillno AS billno,
            COALESCE(NULLIF(cg.department_code, ''), '未归属') AS department_code,
            COALESCE(NULLIF(cg.department_name, ''), '未归属部门') AS department_name,
            COALESCE(NULLIF(cg.group_code, ''), COALESCE(NULLIF(s.sglmfid, ''), '未归属')) AS group_code,
            COALESCE(NULLIF(cg.group_name, ''), COALESCE(NULLIF(s.sglmfid, ''), '未归属柜组')) AS group_name,
            SUM(COALESCE(s.sglxssr, 0)) AS sales_amount,
            SUM(COALESCE(s.sgln13, 0)) AS sales_cost,
            SUM(COALESCE(s.sgln2, 0)) AS gross_profit,
            SUM(COALESCE(s.sglnetml, s.sgln2, 0)) AS net_profit,
            SUM(COALESCE(s.sglsqje, 0)) AS received_coupon_amount,
            SUM(COALESCE(s.sglfqje, 0)) AS issued_coupon_amount,
            SUM(COALESCE(s.sglthss, 0)) AS return_loss,
            COALESCE(MAX(sd.pay_discount_amount), 0) AS pay_discount_amount,
            COALESCE(MAX(sd.supplier_discount_amount), 0) AS supplier_discount_amount,
            COALESCE(MAX(sd.shop_discount_amount), 0) AS shop_discount_amount
          FROM salegoodslist s
          JOIN (SELECT DISTINCT billno FROM matched_logs) mb ON mb.billno = s.sglbillno
          LEFT JOIN manaframe_groups cg ON UPPER(TRIM(COALESCE(cg.group_code, ''))) = UPPER(TRIM(COALESCE(s.sglmfid, '')))
          LEFT JOIN supplier_discount sd ON sd.billno = s.sglbillno AND UPPER(TRIM(COALESCE(sd.group_code, ''))) = UPPER(TRIM(COALESCE(s.sglmfid, '')))
          WHERE 1=1 {_sales_department_exclusion_sql("cg")}
          GROUP BY 1, 2, 3, 4, 5
        ),
        bill_totals AS (
          SELECT
            billno,
            SUM(sales_amount) AS bill_sales_amount,
            COUNT(DISTINCT department_code) AS bill_department_count,
            COUNT(DISTINCT group_code) AS bill_group_count
          FROM sales_group
          GROUP BY billno
        ),
        allocated AS (
          SELECT
            sg.*,
            CASE
              WHEN COALESCE(bt.bill_sales_amount, 0) <> 0 THEN sg.sales_amount / bt.bill_sales_amount
              ELSE 0
            END AS allocation_ratio,
            COALESCE(pb.coupon_pay_amount, 0) AS bill_coupon_pay_amount,
            COALESCE(lb.issued_log_amount, 0) AS bill_issued_log_amount,
            COALESCE(lb.consumed_log_amount, 0) AS bill_consumed_log_amount,
            bt.bill_department_count,
            bt.bill_group_count
          FROM sales_group sg
          JOIN bill_totals bt ON bt.billno = sg.billno
          LEFT JOIN pay_bill pb ON pb.billno = sg.billno
          LEFT JOIN log_bill lb ON lb.billno = sg.billno
        )
        SELECT
          a.department_code,
          a.department_name,
          {_code_name_display_sql("a.department_code", "a.department_name")} AS department_display,
          {group_select}
          COUNT(DISTINCT a.billno) AS ticket_count,
          COUNT(DISTINCT CASE WHEN a.bill_department_count > 1 THEN a.billno END) AS cross_department_ticket_count,
          COUNT(DISTINCT CASE WHEN a.bill_group_count > 1 THEN a.billno END) AS cross_group_ticket_count,
          SUM(a.sales_amount) AS sales_amount,
          SUM(a.sales_cost) AS sales_cost,
          SUM(a.gross_profit) AS gross_profit,
          SUM(a.net_profit) AS net_profit,
          SUM(a.received_coupon_amount) AS received_coupon_amount,
          SUM(a.issued_coupon_amount) AS issued_coupon_amount,
          SUM(a.return_loss) AS return_loss,
          SUM(a.pay_discount_amount) AS pay_discount_amount,
          SUM(a.supplier_discount_amount) AS supplier_discount_amount,
          SUM(a.shop_discount_amount) AS shop_discount_amount,
          SUM(a.bill_coupon_pay_amount * a.allocation_ratio) AS allocated_coupon_pay_amount,
          SUM(a.bill_issued_log_amount * a.allocation_ratio) AS allocated_issued_log_amount,
          SUM(a.bill_consumed_log_amount * a.allocation_ratio) AS allocated_consumed_log_amount
        FROM allocated a
        WHERE 1=1 {level_filter}
        GROUP BY {group_by}
        ORDER BY allocated_coupon_pay_amount DESC, sales_amount DESC
        LIMIT :limit
        """,
        params,
    )


@router.get("/department-tickets")
async def department_tickets(
    activity_id: str | None = Query(None),
    scope: str = Query("activity", pattern="^(activity|standalone|all)$"),
    department_code: str = Query(...),
    group_code: str = Query(...),
    coupon_type: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    store_code: str | None = Query(None, description="门店编码"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, ACTIVITY_ANALYSIS_PERMISSION)
    _ensure_required_tables(db)

    business_scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    params: dict[str, Any] = {}
    activity_scope_sql = _activity_scope_filter_sql(db, business_scope, params, alias="p", prefix="dept_tickets")
    log_scope_sql = _activity_log_scope_filter_sql(db, business_scope, params, alias="l", prefix="dept_tickets_logs")
    log_filter, log_params = _activity_filter(activity_id, start_date, end_date, scope, activity_scope_sql, log_scope_sql)
    params.update(log_params)
    selected_store_code = _require_selected_activity_store(db, business_scope, store_code)
    selected_store_sql = _selected_store_clause(
        selected_store_code,
        params,
        expression="l.tcflmkt",
        prefix="dept_tickets",
    )
    log_filter = f"({log_filter}){selected_store_sql}"
    coupon_filter, coupon_params = _coupon_type_filter(coupon_type)
    params.update(coupon_params)
    params.setdefault("coupon_type", None)
    params.update({"department_code": department_code, "group_code": group_code, "limit": limit})

    return _rows(
        db,
        f"""
        WITH matched_logs AS (
          SELECT
            h.billno,
            l.tcflzy,
            l.tcflmoney,
            l.tcflsyjtrace
          FROM tktcardfqlog l
          JOIN salehead h
            ON l.tcflmkt = h.mkt
           AND l.tcflsyjid = h.syjh
           AND l.tcflinvno ~ '^[0-9]+$'
           AND h.fphm = l.tcflinvno::numeric
          WHERE {log_filter}
            {coupon_filter}
        ),
        pay_bill AS (
          SELECT
            p.billno,
            SUM(COALESCE(p.je, 0)) AS coupon_pay_amount
          FROM salepay p
          JOIN matched_logs ml
            ON ml.billno = p.billno
           AND ml.tcflzy = 'O'
           AND p.batch = ml.tcflsyjtrace::varchar
          WHERE p.paycode IN ('0500', '0580')
          GROUP BY p.billno
        ),
        log_bill AS (
          SELECT
            billno,
            SUM({_issued_amount_sql()}) AS issued_log_amount,
            SUM(CASE WHEN tcflzy = 'O' THEN ABS(COALESCE(tcflmoney, 0)) WHEN tcflzy = 'U' THEN -ABS(COALESCE(tcflmoney, 0)) ELSE 0 END) AS consumed_log_amount
          FROM matched_logs
          GROUP BY billno
        ),
        {_supplier_discount_cte("AND (:coupon_type IS NULL OR COALESCE(sgpqtype, '') = :coupon_type)")},
        manaframe_groups AS (
          SELECT
            mf.mfcode AS group_code,
            mf.mfcname AS group_name,
            dept.mfcode AS department_code,
            dept.mfcname AS department_name
          FROM manaframe mf
          LEFT JOIN manaframe dept
            ON UPPER(TRIM(COALESCE(mf.mfpcode, ''))) = UPPER(TRIM(COALESCE(dept.mfcode, '')))
        ),
        sales_group AS (
          SELECT
            s.sglbillno AS billno,
            COALESCE(NULLIF(cg.department_code, ''), '未归属') AS department_code,
            COALESCE(NULLIF(cg.department_name, ''), '未归属部门') AS department_name,
            COALESCE(NULLIF(cg.group_code, ''), COALESCE(NULLIF(s.sglmfid, ''), '未归属')) AS group_code,
            COALESCE(NULLIF(cg.group_name, ''), COALESCE(NULLIF(s.sglmfid, ''), '未归属柜组')) AS group_name,
            SUM(COALESCE(s.sglxssr, 0)) AS sales_amount,
            SUM(COALESCE(s.sgln13, 0)) AS sales_cost,
            SUM(COALESCE(s.sgln2, 0)) AS gross_profit,
            SUM(COALESCE(s.sglnetml, s.sgln2, 0)) AS net_profit,
            SUM(COALESCE(s.sglsqje, 0)) AS received_coupon_amount,
            SUM(COALESCE(s.sglfqje, 0)) AS issued_coupon_amount,
            SUM(COALESCE(s.sglthss, 0)) AS return_loss,
            COALESCE(MAX(sd.pay_discount_amount), 0) AS pay_discount_amount,
            COALESCE(MAX(sd.supplier_discount_amount), 0) AS supplier_discount_amount,
            COALESCE(MAX(sd.shop_discount_amount), 0) AS shop_discount_amount
          FROM salegoodslist s
          JOIN (SELECT DISTINCT billno FROM matched_logs) mb ON mb.billno = s.sglbillno
          LEFT JOIN manaframe_groups cg ON UPPER(TRIM(COALESCE(cg.group_code, ''))) = UPPER(TRIM(COALESCE(s.sglmfid, '')))
          LEFT JOIN supplier_discount sd ON sd.billno = s.sglbillno AND UPPER(TRIM(COALESCE(sd.group_code, ''))) = UPPER(TRIM(COALESCE(s.sglmfid, '')))
          WHERE 1=1 {_sales_department_exclusion_sql("cg")}
          GROUP BY 1, 2, 3, 4, 5
        ),
        bill_totals AS (
          SELECT
            billno,
            SUM(sales_amount) AS bill_sales_amount,
            COUNT(DISTINCT department_code) AS bill_department_count,
            COUNT(DISTINCT group_code) AS bill_group_count
          FROM sales_group
          GROUP BY billno
        ),
        allocated AS (
          SELECT
            sg.*,
            CASE
              WHEN COALESCE(bt.bill_sales_amount, 0) <> 0 THEN sg.sales_amount / bt.bill_sales_amount
              ELSE 0
            END AS allocation_ratio,
            COALESCE(pb.coupon_pay_amount, 0) AS bill_coupon_pay_amount,
            COALESCE(lb.issued_log_amount, 0) AS bill_issued_log_amount,
            COALESCE(lb.consumed_log_amount, 0) AS bill_consumed_log_amount,
            bt.bill_sales_amount,
            bt.bill_department_count,
            bt.bill_group_count
          FROM sales_group sg
          JOIN bill_totals bt ON bt.billno = sg.billno
          LEFT JOIN pay_bill pb ON pb.billno = sg.billno
          LEFT JOIN log_bill lb ON lb.billno = sg.billno
        )
        SELECT
          h.billno,
          h.rqsj AS sale_time,
          h.mkt AS market_code,
          h.syjh AS cashier_no,
          h.fphm AS invoice_no,
          h.hykh AS member_no,
          a.department_code,
          a.department_name,
          a.group_code,
          a.group_name,
          a.sales_amount,
          a.sales_cost,
          a.gross_profit,
          a.net_profit,
          a.received_coupon_amount,
          a.issued_coupon_amount,
          a.return_loss,
          a.pay_discount_amount,
          a.supplier_discount_amount,
          a.shop_discount_amount,
          a.bill_coupon_pay_amount * a.allocation_ratio AS allocated_coupon_pay_amount,
          a.bill_issued_log_amount * a.allocation_ratio AS allocated_issued_log_amount,
          a.bill_consumed_log_amount * a.allocation_ratio AS allocated_consumed_log_amount,
          a.allocation_ratio,
          a.bill_sales_amount,
          a.bill_department_count,
          a.bill_group_count
        FROM allocated a
        JOIN salehead h ON h.billno = a.billno
        WHERE a.department_code = :department_code
          AND a.group_code = :group_code
        ORDER BY h.rqsj DESC, h.billno DESC
        LIMIT :limit
        """,
        params,
    )


@router.get("/coupon-summary")
async def coupon_summary(
    activity_id: str | None = Query(None, description="活动档期编码 tktpopinfo.tpiid"),
    scope: str = Query("activity", pattern="^(activity|standalone|all)$", description="activity 活动档期券；standalone 非档期券；all 全部卡券"),
    start_date: str | None = Query(None, description="日志日期起 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="日志日期止 YYYY-MM-DD"),
    store_code: str | None = Query(None, description="门店编码"),
    limit: int = Query(100, ge=1, le=300),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, ACTIVITY_ANALYSIS_PERMISSION)
    _ensure_required_tables(db)

    business_scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    params: dict[str, Any] = {"limit": limit}
    activity_scope_sql = _activity_scope_filter_sql(db, business_scope, params, alias="p", prefix="coupon_summary")
    log_scope_sql = _activity_log_scope_filter_sql(db, business_scope, params, alias="l", prefix="coupon_summary_logs")
    log_filter, log_params = _activity_filter(activity_id, start_date, end_date, scope, activity_scope_sql, log_scope_sql)
    params.update(log_params)
    selected_store_code = _require_selected_activity_store(db, business_scope, store_code)
    selected_store_sql = _selected_store_clause(
        selected_store_code,
        params,
        expression="l.tcflmkt",
        prefix="coupon_summary",
    )
    log_filter = f"({log_filter}){selected_store_sql}"
    summary_log_filter = log_filter
    if not activity_id and scope == "standalone":
        recharge_clauses = [
            "((l.tcflzy = 'm' AND l.tcflsource IN ('2', '5')) OR (l.tcflzy = 'M' AND l.tcflsource = '8'))",
            "COALESCE(NULLIF(l.tcfljetype, ''), '未标识') = 'O'",
        ]
        if log_scope_sql:
            recharge_clauses.append(log_scope_sql.removeprefix(" AND "))
        if selected_store_sql:
            recharge_clauses.append(selected_store_sql.removeprefix(" AND "))
        if start_date:
            recharge_clauses.append("l.tcfldate >= :start_date")
        if end_date:
            recharge_clauses.append("l.tcfldate <= :end_date")
        summary_log_filter = f"(({log_filter}) OR ({' AND '.join(recharge_clauses)}))"
    coupon_type_sql = (
        "CASE "
        "WHEN ((l.tcflzy = 'm' AND l.tcflsource IN ('2', '5')) OR (l.tcflzy = 'M' AND l.tcflsource = '8')) "
        " AND COALESCE(NULLIF(l.tcfljetype, ''), '未标识') = 'O' "
        "THEN 'W' "
        "ELSE COALESCE(NULLIF(l.tcfljetype, ''), '未标识') "
        "END"
    )

    return _rows(
        db,
        f"""
        WITH coupon_pay AS (
          SELECT
            billno,
            batch,
            SUM(COALESCE(je, 0)) AS coupon_pay_amount
          FROM salepay
          WHERE paycode IN ('0500', '0580')
          GROUP BY billno, batch
        ),
        log_rows AS (
          SELECT
            l.tcflseqno AS flow_id,
            l.tcfldate AS flow_date,
            l.tcflzy AS action_code,
            {_case_expr("l.tcflzy", ACTION_LABELS, "'未知动作'")} AS action_name,
            l.tcflsource AS source_code,
            {_case_expr("l.tcflsource", SOURCE_LABELS, "'未知来源'")} AS source_name,
            {coupon_type_sql} AS coupon_type,
            l.tcflvipno AS member_no,
            l.tcflqno AS coupon_no,
            l.tcflmoney AS raw_flow_amount,
            {ACTION_AMOUNT_SQL} AS flow_amount,
            {_issued_amount_sql("l")} AS issued_log_amount,
            CASE
              WHEN l.tcflzy = 'O' THEN ABS(COALESCE(l.tcflmoney, 0))
              WHEN l.tcflzy = 'U' THEN -ABS(COALESCE(l.tcflmoney, 0))
              ELSE 0
            END AS consumed_log_amount,
            h.billno,
            cp.coupon_pay_amount
          FROM tktcardfqlog l
          LEFT JOIN salehead h
            ON l.tcflmkt = h.mkt
           AND l.tcflsyjid = h.syjh
           AND l.tcflinvno ~ '^[0-9]+$'
           AND h.fphm = l.tcflinvno::numeric
          LEFT JOIN coupon_pay cp
            ON cp.billno = h.billno
           AND cp.batch = l.tcflsyjtrace::varchar
          WHERE {summary_log_filter}
        )
        SELECT
          action_code,
          action_name,
          source_code,
          source_name,
          coupon_type,
          MIN(flow_date) AS first_flow_date,
          MAX(flow_date) AS last_flow_date,
          COUNT(*) AS flow_count,
          COUNT(DISTINCT NULLIF(member_no, '')) AS member_count,
          COUNT(DISTINCT NULLIF(coupon_no, '')) AS coupon_count,
          COUNT(DISTINCT billno) AS ticket_count,
          SUM(COALESCE(raw_flow_amount, 0)) AS raw_flow_amount,
          SUM(COALESCE(flow_amount, 0)) AS flow_amount,
          SUM(COALESCE(issued_log_amount, 0)) AS issued_log_amount,
          SUM(COALESCE(consumed_log_amount, 0)) AS consumed_log_amount,
          SUM(CASE WHEN action_code = 'O' THEN COALESCE(coupon_pay_amount, 0) ELSE 0 END) AS coupon_pay_amount
        FROM log_rows
        GROUP BY action_code, action_name, source_code, source_name, coupon_type
        ORDER BY
          CASE
            WHEN action_code = 'F' THEN 1
            WHEN action_code = 'O' THEN 2
            WHEN action_code = 'U' THEN 3
            WHEN action_code IN ('P', 'K', 'V') THEN 4
            ELSE 9
          END,
          ABS(SUM(COALESCE(flow_amount, 0))) DESC,
          action_code,
          coupon_type
        LIMIT :limit
        """,
        params,
    )


@router.get("/voucher-match-candidates")
async def voucher_match_candidates(
    activity_id: str | None = Query(None, description="活动档期编码 tktpopinfo.tpiid"),
    scope: str = Query("activity", pattern="^(activity|standalone|all)$", description="activity 活动档期券；standalone 非档期券；all 全部卡券"),
    start_date: str | None = Query(None, description="日志日期起 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="日志日期止 YYYY-MM-DD"),
    subject_codes: list[str] = Query(default=["122104"], description="凭证科目编码，默认促销应收款 122104"),
    tolerance: float = Query(0.01, ge=0, le=1000, description="金额匹配容差"),
    candidate_limit: int = Query(1, ge=1, le=20, description="每个业务汇总行返回的候选凭证明细数"),
    hide_auto_confirmed: bool = Query(True, description="是否隐藏已自动确认的匹配"),
    exclude_coupon_types: list[str] = Query(default=["V", "W"], description="不需要凭证匹配的券字母"),
    store_code: str | None = Query(None, description="业务门店编码：601/602/603/604"),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, VOUCHER_MATCH_VIEW_PERMISSION)
    _ensure_required_tables(db)
    if not _table_exists(db, "bh_dw_gl_detail_fact2"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="财务凭证明细表 bh_dw_gl_detail_fact2 尚未创建或同步")

    business_scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    requested_subject_codes = [code.strip() for code in subject_codes if code.strip()] or ["122104"]
    selected_store_code = store_code.strip() if store_code else ""
    selected_voucher_store_code = {
        "601": "101",
        "602": "102",
        "603": "105",
        "604": "604",
    }.get(selected_store_code, selected_store_code)
    selected_pk_corp = {
        "601": "1018",
        "602": "1018",
        "603": "1021",
        "604": "1084",
    }.get(selected_store_code)

    params: dict[str, Any] = {
        "subject_codes": requested_subject_codes,
        "tolerance": tolerance,
        "candidate_limit": candidate_limit,
        "hide_auto_confirmed": hide_auto_confirmed,
        "exclude_coupon_types": [code.strip().upper() for code in exclude_coupon_types if code.strip()],
        "store_code": selected_store_code,
        "voucher_store_code": selected_voucher_store_code,
        "voucher_pk_corp": selected_pk_corp,
        "limit": limit,
    }
    subject_match_count = db.execute(
        text("SELECT COUNT(*) FROM bh_dw_gl_detail_fact2 WHERE subject_code = ANY(:subject_codes)"),
        {"subject_codes": requested_subject_codes},
    ).scalar() or 0
    subject_filter_sql = (
        "v.subject_code = ANY(:subject_codes)"
        if subject_match_count
        else "(v.explanation ILIKE '%券%' OR v.explanation ILIKE '%促销%')"
    )
    voucher_amount_filter_sql = finance_voucher_amount_filter_sql("v")
    activity_scope_sql = _activity_scope_filter_sql(db, business_scope, params, alias="p", prefix="voucher_match")
    log_scope_sql = _activity_log_scope_filter_sql(db, business_scope, params, alias="l", prefix="voucher_match_logs")
    log_filter, log_params = _activity_filter(activity_id, start_date, end_date, scope, activity_scope_sql, log_scope_sql)
    params.update(log_params)
    if selected_store_code:
        log_filter = f"({log_filter}) AND l.tcflmkt::varchar = :store_code"

    match_log_filter = log_filter
    if not activity_id and scope == "standalone":
        recharge_clauses = [
            "((l.tcflzy = 'm' AND l.tcflsource IN ('2', '5')) OR (l.tcflzy = 'M' AND l.tcflsource = '8'))",
            "COALESCE(NULLIF(l.tcfljetype, ''), '未标识') = 'O'",
        ]
        if log_scope_sql:
            recharge_clauses.append(log_scope_sql.removeprefix(" AND "))
        if selected_store_code:
            recharge_clauses.append("l.tcflmkt::varchar = :store_code")
        if start_date:
            recharge_clauses.append("l.tcfldate >= :start_date")
        if end_date:
            recharge_clauses.append("l.tcfldate <= :end_date")
        match_log_filter = f"(({log_filter}) OR ({' AND '.join(recharge_clauses)}))"

    coupon_type_sql = (
        "CASE "
        "WHEN ((l.tcflzy = 'm' AND l.tcflsource IN ('2', '5')) OR (l.tcflzy = 'M' AND l.tcflsource = '8')) "
        " AND COALESCE(NULLIF(l.tcfljetype, ''), '未标识') = 'O' "
        "THEN 'W' "
        "ELSE COALESCE(NULLIF(l.tcfljetype, ''), '未标识') "
        "END"
    )

    return _rows(
        db,
        f"""
        WITH log_rows AS MATERIALIZED (
          SELECT
            l.tcfldate AS business_date,
            l.tcflmkt::varchar AS market_code,
            CASE l.tcflmkt::varchar
              WHEN '601' THEN '101'
              WHEN '602' THEN '102'
              WHEN '603' THEN '105'
              WHEN '604' THEN '604'
              ELSE l.tcflmkt::varchar
            END AS voucher_store_code,
            l.tcflzy AS action_code,
            {coupon_type_sql} AS coupon_type,
            l.tcflvipno AS member_no,
            (l.tcflzy IN ('m', 'n') AND l.tcflsource IN ('2', '5')) AS is_front_buy,
            CASE
              WHEN l.tcflzy = 'O' THEN ABS(COALESCE(l.tcflmoney, 0))
              WHEN l.tcflzy = 'U' THEN -ABS(COALESCE(l.tcflmoney, 0))
              WHEN l.tcflzy = 'P' THEN -ABS(COALESCE(l.tcflmoney, 0))
              WHEN l.tcflzy = 'V' THEN ABS(COALESCE(l.tcflmoney, 0))
              ELSE 0
            END AS use_amount,
            CASE
              WHEN l.tcflzy IN ('m', 'n') AND l.tcflsource IN ('2', '5')
              THEN COALESCE(({front_buy_actual_amount_sql("l", "front_sale")}), 0)
              WHEN l.tcflzy = 'M' AND l.tcflsource IN ('2', '8') THEN ABS(COALESCE(l.tcflmoney, 0))
              WHEN l.tcflzy IN ('N', 'w') AND l.tcflsource IN ('2', '8') THEN -ABS(COALESCE(l.tcflmoney, 0))
              ELSE 0
            END AS buy_amount
          FROM tktcardfqlog l
          {front_buy_sale_join_sql("l", "front_sale")}
          WHERE {match_log_filter}
            AND {_voucher_match_flow_exclusion_sql("l")}
        ),
        business_rows AS (
          SELECT
            business_date,
            market_code,
            voucher_store_code,
            coupon_type,
            COALESCE(NULLIF(tq.tqname, ''), coupon_type) AS coupon_name,
            'DEBIT_USE' AS match_type,
            '借方用券' AS match_type_name,
            SUM(use_amount) AS business_amount,
            COUNT(*) FILTER (WHERE use_amount <> 0) AS flow_count,
            COUNT(DISTINCT NULLIF(member_no, '')) FILTER (WHERE use_amount <> 0) AS member_count
          FROM log_rows lr
          LEFT JOIN tktqtype tq ON tq.tqcode = lr.coupon_type
          WHERE lr.action_code IN ('O', 'U', 'P', 'V')
            AND NOT (UPPER(lr.coupon_type) = ANY(:exclude_coupon_types))
          GROUP BY business_date, market_code, voucher_store_code, coupon_type, COALESCE(NULLIF(tq.tqname, ''), coupon_type)
          HAVING ABS(SUM(use_amount)) > 0.005

          UNION ALL

          SELECT
            business_date,
            market_code,
            voucher_store_code,
            coupon_type,
            COALESCE(NULLIF(tq.tqname, ''), coupon_type) AS coupon_name,
            'CREDIT_BUY' AS match_type,
            CASE
              WHEN BOOL_AND(is_front_buy) FILTER (WHERE buy_amount <> 0)
              THEN '{CREDIT_BUY_MATCH_TYPE_NAME}'
              ELSE '贷方买券'
            END AS match_type_name,
            SUM(buy_amount) AS business_amount,
            COUNT(*) FILTER (WHERE buy_amount <> 0) AS flow_count,
            COUNT(DISTINCT NULLIF(member_no, '')) FILTER (WHERE buy_amount <> 0) AS member_count
          FROM log_rows lr
          LEFT JOIN tktqtype tq ON tq.tqcode = lr.coupon_type
          WHERE lr.buy_amount <> 0
            AND NOT (UPPER(lr.coupon_type) = ANY(:exclude_coupon_types))
          GROUP BY business_date, market_code, voucher_store_code, coupon_type, COALESCE(NULLIF(tq.tqname, ''), coupon_type)
          HAVING ABS(SUM(buy_amount)) > 0.005
        ),
        voucher_rows AS MATERIALIZED (
          SELECT
            {VOUCHER_DETAIL_KEY_SQL} AS voucher_detail_id,
            v.pk_detail,
            v.pk_voucher,
            v.pk_corp AS voucher_corp_code,
            CASE v.pk_corp
              WHEN '1018' THEN '购物中心/百货大楼'
              WHEN '1021' THEN '新世纪'
              WHEN '1084' THEN '半山'
              ELSE COALESCE(NULLIF(v.pk_corp, ''), '未标识')
            END AS voucher_corp_name,
            v.subject_code,
            v.explanation,
            COALESCE(v.localdebitamount, v.debitamount, 0) AS debit_amount,
            COALESCE(v.localcreditamount, v.creditamount, 0) AS credit_amount,
            v.valuecode,
            v.valuename,
            v.account_year,
            v.account_period,
            v.load_date,
            SUBSTRING(v.explanation FROM '^\\((10[125]|604)\\)') AS voucher_store_code,
            UPPER(SUBSTRING(v.explanation FROM '0500\\s*促销券\\s*([A-Z])')) AS voucher_coupon_type,
            CASE
              WHEN SUBSTRING(v.explanation FROM '(20[0-9]{{2}}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01]))') IS NOT NULL
                THEN TO_DATE(SUBSTRING(v.explanation FROM '(20[0-9]{{2}}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01]))'), 'YYYYMMDD')
              WHEN SUBSTRING(v.explanation FROM '(20[0-9]{{2}}\\.(0?[1-9]|1[0-2])\\.(0?[1-9]|[12][0-9]|3[01]))') IS NOT NULL
                THEN TO_DATE(SUBSTRING(v.explanation FROM '(20[0-9]{{2}}\\.(0?[1-9]|1[0-2])\\.(0?[1-9]|[12][0-9]|3[01]))'), 'YYYY.MM.DD')
              ELSE NULL
            END AS voucher_business_date
          FROM bh_dw_gl_detail_fact2 v
          WHERE {subject_filter_sql}
            AND (:store_code = '' OR v.pk_corp = :voucher_pk_corp OR SUBSTRING(v.explanation FROM '^\\((10[125]|604)\\)') = :voucher_store_code)
            AND {voucher_amount_filter_sql}
        )
        SELECT
          br.business_date,
          br.market_code,
          br.voucher_store_code AS business_store_code,
          br.coupon_type,
          br.coupon_name,
          br.match_type,
          br.match_type_name,
          br.business_amount,
          br.flow_count,
          br.member_count,
          c.pk_detail,
          c.pk_voucher,
          c.voucher_corp_code,
          c.voucher_corp_name,
          c.subject_code,
          c.explanation,
          c.debit_amount,
          c.credit_amount,
          c.voucher_amount,
          c.voucher_business_date,
          c.voucher_store_code,
          c.voucher_coupon_type,
          c.valuecode,
          c.valuename,
          c.account_year,
          c.account_period,
          c.load_date,
          c.voucher_detail_id,
          c.amount_diff,
          c.match_score,
          CASE
            WHEN c.voucher_detail_id IS NULL THEN 'NO_CANDIDATE'
            WHEN ABS(c.amount_diff) <= :tolerance AND c.voucher_business_date = br.business_date AND c.match_score >= 90 THEN 'AUTO_STRONG'
            WHEN ABS(c.amount_diff) <= :tolerance THEN 'AUTO_CANDIDATE'
            ELSE 'REVIEW'
          END AS match_status,
          m.id AS saved_match_id,
          COALESCE(m.confirm_status, 'UNCONFIRMED') AS confirm_status,
          m.confirmed_at,
          COALESCE(NULLIF(u.real_name, ''), u.username) AS confirmed_by_name,
          m.rejected_reason
        FROM business_rows br
        LEFT JOIN LATERAL (
          SELECT
            v.*,
            CASE
              WHEN br.match_type = 'DEBIT_USE' THEN v.debit_amount
              ELSE v.credit_amount
            END AS voucher_amount,
            CASE
              WHEN br.match_type = 'DEBIT_USE' THEN v.debit_amount - br.business_amount
              ELSE v.credit_amount - br.business_amount
            END AS amount_diff,
            (
              CASE
                WHEN ABS((CASE WHEN br.match_type = 'DEBIT_USE' THEN v.debit_amount ELSE v.credit_amount END) - br.business_amount) <= :tolerance THEN 60
                ELSE 0
              END
              + CASE WHEN v.voucher_business_date = br.business_date THEN 20 ELSE 0 END
              + CASE WHEN v.voucher_store_code = br.voucher_store_code THEN 20 ELSE 0 END
              + CASE WHEN v.voucher_coupon_type = br.coupon_type THEN 20 ELSE 0 END
              + CASE
                  WHEN br.match_type = 'DEBIT_USE' AND v.explanation ILIKE ('%0500%促销券' || br.coupon_type || '%') THEN 10
                  WHEN br.match_type = 'DEBIT_USE' AND v.explanation ILIKE ('%' || br.coupon_name || '%') THEN 10
                  WHEN br.match_type = 'CREDIT_BUY' AND v.explanation ILIKE ('%' || br.coupon_name || '%') THEN 20
                  ELSE 0
                END
            ) AS match_score
          FROM voucher_rows v
          WHERE ABS((CASE WHEN br.match_type = 'DEBIT_USE' THEN v.debit_amount ELSE v.credit_amount END) - br.business_amount) <= :tolerance
            AND (v.voucher_business_date IS NULL OR v.voucher_business_date = br.business_date)
            AND (v.voucher_store_code IS NULL OR v.voucher_store_code = br.voucher_store_code)
            AND (
              (
                br.match_type = 'DEBIT_USE'
                AND (
                  v.voucher_coupon_type = br.coupon_type
                  OR v.explanation ILIKE ('%促销券' || br.coupon_type || '%')
                )
              )
              OR (
                br.match_type = 'CREDIT_BUY'
                AND (
                  v.explanation ILIKE ('%' || br.coupon_name || '%')
                  OR v.explanation ILIKE '%券%'
                )
              )
            )
          ORDER BY match_score DESC, ABS((CASE WHEN br.match_type = 'DEBIT_USE' THEN v.debit_amount ELSE v.credit_amount END) - br.business_amount), v.voucher_business_date NULLS LAST
          LIMIT :candidate_limit
        ) c ON TRUE
        LEFT JOIN activity_coupon_voucher_match m
          ON m.business_date = br.business_date
         AND COALESCE(m.business_store_code, '') = COALESCE(br.voucher_store_code, '')
         AND m.coupon_type = br.coupon_type
         AND m.match_type = br.match_type
         AND m.voucher_detail_id = c.voucher_detail_id
        LEFT JOIN users u ON u.user_id = m.confirmed_by
        WHERE (:hide_auto_confirmed IS FALSE OR COALESCE(m.confirm_status, '') <> 'AUTO_CONFIRMED')
        ORDER BY br.business_date, br.coupon_type, br.match_type, c.match_score DESC NULLS LAST
        LIMIT :limit
        """,
        params,
    )


@router.post("/voucher-matches")
async def save_voucher_matches(
    payload: VoucherMatchBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _table_exists(db, "activity_coupon_voucher_match"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="凭证匹配确认表 activity_coupon_voucher_match 尚未创建")
    _ensure_coupon_monthly_tables(db)
    if not _table_exists(db, "activity_coupon_revenue_rate_snapshot"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="卡券收入占比快照表尚未创建")

    confirm_status = payload.confirm_status.upper().strip()
    if confirm_status not in {"AUTO_CONFIRMED", "MANUAL_CONFIRMED", "REJECTED"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="confirm_status 只能是 AUTO_CONFIRMED、MANUAL_CONFIRMED 或 REJECTED")
    require_permission(
        db,
        current_user,
        VOUCHER_MATCH_REJECT_PERMISSION if confirm_status == "REJECTED" else VOUCHER_MATCH_CONFIRM_PERMISSION,
    )

    rows = []
    skipped = 0
    for row in payload.rows:
        if not row.voucher_detail_id:
            skipped += 1
            continue
        rows.append(
            {
                "business_date": row.business_date,
                "market_code": row.market_code,
                "business_store_code": row.business_store_code,
                "coupon_type": row.coupon_type,
                "coupon_name": row.coupon_name,
                "match_type": row.match_type,
                "match_type_name": row.match_type_name,
                "business_amount": row.business_amount,
                "flow_count": row.flow_count,
                "member_count": row.member_count,
                "voucher_detail_id": row.voucher_detail_id,
                "voucher_amount": row.voucher_amount,
                "amount_diff": row.amount_diff,
                "match_score": row.match_score,
                "match_status": row.match_status,
                "confirm_status": confirm_status,
                "confirmed_by": current_user.user_id,
                "rejected_reason": payload.rejected_reason,
            }
        )

    if not rows:
        return {"saved": 0, "skipped": skipped}

    db.execute(
        text(
            """
            INSERT INTO activity_coupon_voucher_match (
                business_date,
                market_code,
                business_store_code,
                coupon_type,
                coupon_name,
                match_type,
                match_type_name,
                business_amount,
                flow_count,
                member_count,
                voucher_detail_id,
                voucher_amount,
                amount_diff,
                match_score,
                match_status,
                confirm_status,
                confirmed_by,
                confirmed_at,
                rejected_reason,
                created_at,
                updated_at
            )
            VALUES (
                :business_date,
                :market_code,
                :business_store_code,
                :coupon_type,
                :coupon_name,
                :match_type,
                :match_type_name,
                :business_amount,
                :flow_count,
                :member_count,
                :voucher_detail_id,
                :voucher_amount,
                :amount_diff,
                :match_score,
                :match_status,
                :confirm_status,
                :confirmed_by,
                NOW(),
                :rejected_reason,
                NOW(),
                NOW()
            )
            ON CONFLICT (business_date, business_store_code, coupon_type, match_type, voucher_detail_id)
            DO UPDATE SET
                market_code = EXCLUDED.market_code,
                coupon_name = EXCLUDED.coupon_name,
                match_type_name = EXCLUDED.match_type_name,
                business_amount = EXCLUDED.business_amount,
                flow_count = EXCLUDED.flow_count,
                member_count = EXCLUDED.member_count,
                voucher_amount = EXCLUDED.voucher_amount,
                amount_diff = EXCLUDED.amount_diff,
                match_score = EXCLUDED.match_score,
                match_status = EXCLUDED.match_status,
                confirm_status = EXCLUDED.confirm_status,
                confirmed_by = EXCLUDED.confirmed_by,
                confirmed_at = NOW(),
                rejected_reason = EXCLUDED.rejected_reason,
                updated_at = NOW()
            """
        ),
        rows,
    )
    voucher_match_ids = []
    for row in rows:
        match_id = db.execute(
            text(
                """
                SELECT id
                FROM activity_coupon_voucher_match
                WHERE business_date = :business_date
                  AND business_store_code = :business_store_code
                  AND coupon_type = :coupon_type
                  AND match_type = :match_type
                  AND voucher_detail_id = :voucher_detail_id
                """
            ),
            row,
        ).scalar_one()
        voucher_match_ids.append(int(match_id))
    _sync_confirmed_voucher_match_movements(db, voucher_match_ids)
    db.commit()
    return {"saved": len(rows), "skipped": skipped}


@router.post("/coupon-revenue-movements/rebuild")
async def rebuild_coupon_revenue_movements(
    payload: CouponRevenueMovementRebuildRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, COUPON_MONTHLY_REBUILD_PERMISSION)
    _ensure_coupon_monthly_tables(db)
    if not _table_exists(db, "activity_coupon_voucher_match") or not _table_exists(db, "activity_coupon_revenue_rate_snapshot"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="卡券凭证匹配表或收入占比快照表尚未创建")

    period_month = _period_or_400(payload.period_month)
    start_date, end_date = month_bounds(period_month)
    market_code = payload.market_code.strip() if payload.market_code else ""
    _reject_confirmed_coupon_month(db, period_month, market_code)

    db.execute(
        text(
            """
            DELETE FROM activity_coupon_revenue_movement
            WHERE period_month = :period_month
              AND (:market_code = '' OR market_code = :market_code)
            """
        ),
        {"period_month": period_month, "market_code": market_code},
    )
    result = db.execute(
        text(
            f"""
            WITH front_credit_log_rows AS MATERIALIZED (
              SELECT
                l.tcfldate AS business_date,
                l.tcflmkt::varchar AS market_code,
                CASE
                  WHEN l.tcflzy = 'm'
                   AND l.tcflsource IN ('2', '5')
                   AND COALESCE(NULLIF(l.tcfljetype, ''), '未标识') = 'O'
                  THEN 'W'
                  ELSE UPPER(TRIM(COALESCE(NULLIF(l.tcfljetype, ''), '未标识')))
                END AS coupon_type,
                CASE
                  WHEN l.tcflzy = 'm' THEN ABS(COALESCE(l.tcflmoney, 0))
                  ELSE -ABS(COALESCE(l.tcflmoney, 0))
                END AS face_amount,
                {front_buy_actual_amount_sql("l", "front_sale")} AS actual_amount,
                CASE WHEN front_sale.billno IS NULL THEN 1 ELSE 0 END AS missing_actual_count
              FROM tktcardfqlog l
              {front_buy_sale_join_sql("l", "front_sale")}
              WHERE l.tcfldate >= CAST(:start_date AS DATE)
                AND l.tcfldate < CAST(:end_date AS DATE)
                AND l.tcflzy IN ('m', 'n')
                AND l.tcflsource IN ('2', '5')
                AND (:market_code = '' OR l.tcflmkt::varchar = :market_code)
            ),
            front_credit_rows AS (
              SELECT
                business_date,
                market_code,
                coupon_type,
                SUM(face_amount) AS face_amount,
                SUM(COALESCE(actual_amount, 0)) AS actual_amount,
                SUM(missing_actual_count) AS missing_actual_count
              FROM front_credit_log_rows
              GROUP BY business_date, market_code, coupon_type
            ),
            backend_credit_rows AS (
              SELECT
                l.tcfldate AS business_date,
                l.tcflmkt::varchar AS market_code,
                CASE
                  WHEN l.tcflzy = 'M'
                   AND l.tcflsource = '8'
                   AND COALESCE(NULLIF(l.tcfljetype, ''), '未标识') = 'O'
                  THEN 'W'
                  ELSE UPPER(TRIM(COALESCE(NULLIF(l.tcfljetype, ''), '未标识')))
                END AS coupon_type,
                SUM(CASE
                  WHEN l.tcflzy = 'M' THEN ABS(COALESCE(l.tcflmoney, 0))
                  ELSE -ABS(COALESCE(l.tcflmoney, 0))
                END) AS business_amount
              FROM tktcardfqlog l
              WHERE l.tcfldate >= CAST(:start_date AS DATE)
                AND l.tcfldate < CAST(:end_date AS DATE)
                AND l.tcflzy IN ('M', 'N', 'w')
                AND l.tcflsource IN ('2', '8')
                AND (:market_code = '' OR l.tcflmkt::varchar = :market_code)
              GROUP BY business_date, market_code, coupon_type
            ),
            confirmed_matches AS (
              SELECT
                m.id AS voucher_match_id,
                m.business_date,
                :period_month AS period_month,
                COALESCE(NULLIF(m.market_code, ''), NULLIF(m.business_store_code, '')) AS market_code,
                m.business_store_code,
                UPPER(TRIM(m.coupon_type)) AS coupon_type,
                m.coupon_name,
                m.match_type,
                m.voucher_detail_id,
                COALESCE(m.business_amount, 0) AS business_amount,
                r.effective_revenue_rate,
                r.snapshot_date,
                f.face_amount AS front_face_amount,
                f.actual_amount AS front_actual_amount,
                COALESCE(f.missing_actual_count, 0) AS front_missing_actual_count,
                COALESCE(b.business_amount, 0) AS backend_business_amount,
                (
                  m.match_type = 'CREDIT_BUY'
                  AND f.business_date IS NOT NULL
                ) AS has_front_actual
              FROM activity_coupon_voucher_match m
              LEFT JOIN activity_coupon_revenue_rate_snapshot r
                ON r.snapshot_date = m.business_date
               AND r.market_code = COALESCE(NULLIF(m.market_code, ''), NULLIF(m.business_store_code, ''))
               AND UPPER(TRIM(r.coupon_type)) = UPPER(TRIM(m.coupon_type))
              LEFT JOIN front_credit_rows f
                ON f.business_date = m.business_date
               AND f.market_code = COALESCE(NULLIF(m.market_code, ''), NULLIF(m.business_store_code, ''))
               AND f.coupon_type = UPPER(TRIM(m.coupon_type))
              LEFT JOIN backend_credit_rows b
                ON b.business_date = m.business_date
               AND b.market_code = COALESCE(NULLIF(m.market_code, ''), NULLIF(m.business_store_code, ''))
               AND b.coupon_type = UPPER(TRIM(m.coupon_type))
              WHERE m.confirm_status IN ('AUTO_CONFIRMED', 'MANUAL_CONFIRMED')
                AND m.match_type IN ('CREDIT_BUY', 'DEBIT_USE')
                AND m.business_date >= CAST(:start_date AS DATE)
                AND m.business_date < CAST(:end_date AS DATE)
                AND (:market_code = '' OR COALESCE(NULLIF(m.market_code, ''), NULLIF(m.business_store_code, '')) = :market_code)
                AND COALESCE(NULLIF(m.market_code, ''), NULLIF(m.business_store_code, '')) IS NOT NULL
            )
            INSERT INTO activity_coupon_revenue_movement (
                business_date,
                period_month,
                market_code,
                business_store_code,
                coupon_type,
                coupon_name,
                match_type,
                voucher_match_id,
                source_type,
                source_key,
                voucher_detail_id,
                business_amount,
                revenue_rate,
                actual_revenue_amount,
                rate_snapshot_date,
                rate_status,
                movement_direction,
                created_at,
                updated_at
            )
            SELECT
                business_date,
                period_month,
                market_code,
                business_store_code,
                coupon_type,
                coupon_name,
                match_type,
                voucher_match_id,
                'VOUCHER_MATCH',
                'voucher_match:' || voucher_match_id::text,
                voucher_detail_id,
                CASE
                  WHEN has_front_actual THEN front_face_amount + backend_business_amount
                  ELSE business_amount
                END,
                CASE
                  WHEN has_front_actual
                   AND front_missing_actual_count = 0
                   AND (
                     ABS(backend_business_amount) <= 0.005
                     OR effective_revenue_rate IS NOT NULL
                   )
                   AND ABS(front_face_amount + backend_business_amount) > 0.005
                  THEN (
                    front_actual_amount
                    + backend_business_amount * COALESCE(effective_revenue_rate, 0)
                  ) / (front_face_amount + backend_business_amount)
                  ELSE effective_revenue_rate
                END,
                CASE
                  WHEN has_front_actual
                   AND front_missing_actual_count = 0
                   AND (
                     ABS(backend_business_amount) <= 0.005
                     OR effective_revenue_rate IS NOT NULL
                   )
                  THEN front_actual_amount
                     + backend_business_amount * COALESCE(effective_revenue_rate, 0)
                  WHEN has_front_actual THEN 0
                  WHEN effective_revenue_rate IS NULL THEN 0
                  ELSE business_amount * effective_revenue_rate
                END,
                CASE
                  WHEN has_front_actual AND ABS(backend_business_amount) <= 0.005 THEN NULL
                  ELSE snapshot_date
                END,
                CASE
                  WHEN has_front_actual AND front_missing_actual_count > 0 THEN 'MISSING_RATE'
                  WHEN has_front_actual
                   AND ABS(backend_business_amount) > 0.005
                   AND effective_revenue_rate IS NULL THEN 'MISSING_RATE'
                  WHEN has_front_actual THEN 'OK'
                  WHEN effective_revenue_rate IS NULL THEN 'MISSING_RATE'
                  ELSE 'OK'
                END,
                CASE WHEN match_type = 'CREDIT_BUY' THEN 'INCREASE' ELSE 'DECREASE' END,
                NOW(),
                NOW()
            FROM confirmed_matches
            ON CONFLICT (source_type, source_key)
            DO UPDATE SET
                voucher_match_id = EXCLUDED.voucher_match_id,
                business_date = EXCLUDED.business_date,
                period_month = EXCLUDED.period_month,
                market_code = EXCLUDED.market_code,
                business_store_code = EXCLUDED.business_store_code,
                coupon_type = EXCLUDED.coupon_type,
                coupon_name = EXCLUDED.coupon_name,
                match_type = EXCLUDED.match_type,
                voucher_detail_id = EXCLUDED.voucher_detail_id,
                business_amount = EXCLUDED.business_amount,
                revenue_rate = EXCLUDED.revenue_rate,
                actual_revenue_amount = EXCLUDED.actual_revenue_amount,
                rate_snapshot_date = EXCLUDED.rate_snapshot_date,
                rate_status = EXCLUDED.rate_status,
                movement_direction = EXCLUDED.movement_direction,
                updated_at = NOW()
            """
        ),
        {"period_month": period_month, "start_date": start_date, "end_date": end_date, "market_code": market_code},
    )
    recharge_result = db.execute(
        text(
            f"""
            WITH recharge_log_rows AS MATERIALIZED (
              SELECT
                l.tcfldate AS business_date,
                :period_month AS period_month,
                l.tcflmkt::varchar AS market_code,
                CASE
                  WHEN ((l.tcflzy = 'm' AND l.tcflsource IN ('2', '5')) OR (l.tcflzy = 'M' AND l.tcflsource = '8'))
                   AND COALESCE(NULLIF(l.tcfljetype, ''), '未标识') = 'O'
                  THEN 'W'
                  ELSE UPPER(TRIM(COALESCE(NULLIF(l.tcfljetype, ''), '未标识')))
                END AS coupon_type,
                CASE
                  WHEN l.tcflzy = 'm' AND l.tcflsource IN ('2', '5') THEN ABS(COALESCE(l.tcflmoney, 0))
                  WHEN l.tcflzy = 'n' AND l.tcflsource IN ('2', '5') THEN -ABS(COALESCE(l.tcflmoney, 0))
                  WHEN l.tcflzy = 'M' AND l.tcflsource IN ('2', '8') THEN ABS(COALESCE(l.tcflmoney, 0))
                  WHEN l.tcflzy IN ('N', 'w') AND l.tcflsource IN ('2', '8') THEN -ABS(COALESCE(l.tcflmoney, 0))
                  ELSE 0
                END AS business_amount,
                {front_buy_actual_amount_sql("l", "front_sale")} AS front_actual_amount,
                CASE
                  WHEN l.tcflzy = 'M' AND l.tcflsource IN ('2', '8') THEN ABS(COALESCE(l.tcflmoney, 0))
                  WHEN l.tcflzy IN ('N', 'w') AND l.tcflsource IN ('2', '8') THEN -ABS(COALESCE(l.tcflmoney, 0))
                  ELSE 0
                END AS rate_based_business_amount,
                CASE
                  WHEN l.tcflzy IN ('m', 'n')
                   AND l.tcflsource IN ('2', '5')
                   AND front_sale.billno IS NULL
                  THEN 1
                  ELSE 0
                END AS missing_actual_count
              FROM tktcardfqlog l
              {front_buy_sale_join_sql("l", "front_sale")}
              WHERE l.tcfldate >= CAST(:start_date AS DATE)
                AND l.tcfldate < CAST(:end_date AS DATE)
                AND (
                  (l.tcflzy IN ('m', 'n') AND l.tcflsource IN ('2', '5'))
                  OR (l.tcflzy IN ('M', 'N', 'w') AND l.tcflsource IN ('2', '8'))
                )
                AND (:market_code = '' OR l.tcflmkt::varchar = :market_code)
            ),
            recharge_rows AS (
              SELECT
                business_date,
                period_month,
                market_code,
                coupon_type,
                SUM(business_amount) AS business_amount,
                SUM(COALESCE(front_actual_amount, 0)) AS front_actual_amount,
                SUM(rate_based_business_amount) AS rate_based_business_amount,
                SUM(missing_actual_count) AS missing_actual_count,
                COUNT(*) AS flow_count
              FROM recharge_log_rows
              GROUP BY business_date, period_month, market_code, coupon_type
              HAVING ABS(SUM(business_amount)) > 0.005
            ),
            recharge_with_rate AS (
              SELECT
                rr.*,
                COALESCE(NULLIF(tq.tqname, ''), rr.coupon_type) AS coupon_name,
                r.effective_revenue_rate,
                r.snapshot_date
              FROM recharge_rows rr
              LEFT JOIN tktqtype tq ON tq.tqcode = rr.coupon_type
              LEFT JOIN activity_coupon_revenue_rate_snapshot r
                ON r.snapshot_date = rr.business_date
               AND r.market_code = rr.market_code
               AND UPPER(TRIM(r.coupon_type)) = rr.coupon_type
              WHERE NOT EXISTS (
                SELECT 1
                FROM activity_coupon_voucher_match m
                WHERE m.confirm_status IN ('AUTO_CONFIRMED', 'MANUAL_CONFIRMED')
                  AND m.match_type = 'CREDIT_BUY'
                  AND m.business_date = rr.business_date
                  AND COALESCE(NULLIF(m.market_code, ''), NULLIF(m.business_store_code, '')) = rr.market_code
                  AND UPPER(TRIM(m.coupon_type)) = rr.coupon_type
              )
            ),
            recharge_calculated AS (
              SELECT
                rw.*,
                CASE
                  WHEN rw.missing_actual_count > 0 THEN 'MISSING_RATE'
                  WHEN ABS(rw.rate_based_business_amount) > 0.005
                   AND rw.effective_revenue_rate IS NULL THEN 'MISSING_RATE'
                  ELSE 'OK'
                END AS calculated_rate_status,
                CASE
                  WHEN rw.missing_actual_count > 0 THEN 0
                  WHEN ABS(rw.rate_based_business_amount) > 0.005
                   AND rw.effective_revenue_rate IS NULL THEN 0
                  ELSE rw.front_actual_amount
                     + rw.rate_based_business_amount * COALESCE(rw.effective_revenue_rate, 0)
                END AS calculated_revenue_amount
              FROM recharge_with_rate rw
            )
            INSERT INTO activity_coupon_revenue_movement (
                business_date,
                period_month,
                market_code,
                business_store_code,
                coupon_type,
                coupon_name,
                match_type,
                voucher_match_id,
                source_type,
                source_key,
                voucher_detail_id,
                business_amount,
                revenue_rate,
                actual_revenue_amount,
                rate_snapshot_date,
                rate_status,
                movement_direction,
                created_at,
                updated_at
            )
            SELECT
                business_date,
                period_month,
                market_code,
                market_code,
                coupon_type,
                coupon_name,
                'CREDIT_BUY',
                NULL,
                'COUPON_RECHARGE',
                'coupon_recharge:' || business_date::text || ':' || market_code || ':' || coupon_type,
                md5('coupon_recharge:' || business_date::text || ':' || market_code || ':' || coupon_type),
                business_amount,
                CASE
                  WHEN calculated_rate_status = 'OK' AND ABS(business_amount) > 0.005
                  THEN calculated_revenue_amount / business_amount
                  ELSE NULL
                END,
                calculated_revenue_amount,
                CASE WHEN ABS(rate_based_business_amount) > 0.005 THEN snapshot_date ELSE NULL END,
                calculated_rate_status,
                'INCREASE',
                NOW(),
                NOW()
            FROM recharge_calculated
            ON CONFLICT (source_type, source_key)
            DO UPDATE SET
                business_date = EXCLUDED.business_date,
                period_month = EXCLUDED.period_month,
                market_code = EXCLUDED.market_code,
                business_store_code = EXCLUDED.business_store_code,
                coupon_type = EXCLUDED.coupon_type,
                coupon_name = EXCLUDED.coupon_name,
                match_type = EXCLUDED.match_type,
                voucher_detail_id = EXCLUDED.voucher_detail_id,
                business_amount = EXCLUDED.business_amount,
                revenue_rate = EXCLUDED.revenue_rate,
                actual_revenue_amount = EXCLUDED.actual_revenue_amount,
                rate_snapshot_date = EXCLUDED.rate_snapshot_date,
                rate_status = EXCLUDED.rate_status,
                movement_direction = EXCLUDED.movement_direction,
                updated_at = NOW()
            """
        ),
        {"period_month": period_month, "start_date": start_date, "end_date": end_date, "market_code": market_code},
    )
    db.commit()
    return {"rebuilt": (result.rowcount or 0) + (recharge_result.rowcount or 0)}


@router.get("/coupon-confirmed-revenue-daily")
async def coupon_confirmed_revenue_daily(
    start_date: str = Query(...),
    end_date: str | None = Query(None),
    market_code: str | None = Query(None),
    coupon_type: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, COUPON_CONFIRMED_REVENUE_VIEW_PERMISSION)
    _ensure_coupon_monthly_tables(db)
    if not _table_exists(db, "activity_coupon_voucher_match") or not _table_exists(db, "activity_coupon_revenue_movement"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="卡券凭证匹配表或每日收入变动表尚未创建")
    params = {
        "start_date": start_date,
        "end_date": end_date or start_date,
        "market_code": (market_code or "").strip(),
    }
    include_coupon_type = bool((coupon_type or "").strip())
    if include_coupon_type:
        params["coupon_type"] = coupon_type.strip()
    rows = _rows(db, coupon_confirmed_revenue_daily_sql(include_coupon_type), params)
    return summarize_confirmed_revenue_rows(rows)


@router.post("/coupon-nc-carryovers")
async def create_coupon_nc_carryover(
    payload: CouponNcCarryoverRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, COUPON_MONTHLY_CARRYOVER_CREATE_PERMISSION)
    _ensure_coupon_monthly_tables(db)
    period_month = _period_or_400(payload.period_month)
    market_code = payload.market_code.strip()
    coupon_type = payload.coupon_type.strip().upper()
    nc_voucher_no = payload.nc_voucher_no.strip()
    if not market_code or not coupon_type or not nc_voucher_no:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="门店、券种和 NC 凭证号不能为空")
    if payload.carryover_amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="结转金额必须大于 0")

    confirmed = db.execute(
        text(
            """
            SELECT COUNT(*) AS count
            FROM activity_coupon_monthly_balance
            WHERE period_month = :period_month
              AND market_code = :market_code
              AND coupon_type = :coupon_type
              AND status = 'CONFIRMED'
            """
        ),
        {"period_month": period_month, "market_code": market_code, "coupon_type": coupon_type},
    ).fetchone()
    if confirmed is not None and int(confirmed.count or 0) > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该门店券种已确认月结，不能新增 NC 结转登记")

    db.execute(
        text(
            """
            INSERT INTO activity_coupon_nc_carryover (
                period_month,
                market_code,
                coupon_type,
                coupon_name,
                nc_voucher_no,
                carryover_amount,
                carryover_date,
                remark,
                created_by,
                created_at,
                updated_at
            )
            VALUES (
                :period_month,
                :market_code,
                :coupon_type,
                :coupon_name,
                :nc_voucher_no,
                :carryover_amount,
                CAST(:carryover_date AS DATE),
                :remark,
                :created_by,
                NOW(),
                NOW()
            )
            """
        ),
        {
            "period_month": period_month,
            "market_code": market_code,
            "coupon_type": coupon_type,
            "coupon_name": payload.coupon_name,
            "nc_voucher_no": nc_voucher_no,
            "carryover_amount": payload.carryover_amount,
            "carryover_date": payload.carryover_date,
            "remark": payload.remark,
            "created_by": current_user.user_id,
        },
    )
    db.commit()
    return {"saved": 1}


@router.post("/coupon-monthly-balances/rebuild")
async def rebuild_coupon_monthly_balances(
    payload: CouponRevenueMovementRebuildRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, COUPON_MONTHLY_REBUILD_PERMISSION)
    _ensure_coupon_monthly_tables(db)
    period_month = _period_or_400(payload.period_month)
    market_code = payload.market_code.strip() if payload.market_code else ""
    previous_month = previous_period_month(period_month)
    _reject_confirmed_coupon_month(db, period_month, market_code)

    db.execute(
        text(
            """
            DELETE FROM activity_coupon_monthly_balance
            WHERE period_month = :period_month
              AND status = 'DRAFT'
              AND (:market_code = '' OR market_code = :market_code)
            """
        ),
        {"period_month": period_month, "market_code": market_code},
    )
    result = db.execute(
        text(
            """
            WITH movement_groups AS (
              SELECT
                period_month,
                market_code,
                coupon_type,
                MAX(coupon_name) AS coupon_name,
                SUM(CASE WHEN movement_direction = 'INCREASE' AND rate_status = 'OK' THEN actual_revenue_amount ELSE 0 END) AS current_month_increase,
                SUM(CASE WHEN movement_direction = 'DECREASE' AND rate_status = 'OK' THEN actual_revenue_amount ELSE 0 END) AS current_month_decrease,
                COUNT(*) FILTER (WHERE rate_status = 'MISSING_RATE') AS missing_rate_count,
                COUNT(*) AS movement_count
              FROM activity_coupon_revenue_movement
              WHERE period_month = :period_month
                AND (:market_code = '' OR market_code = :market_code)
              GROUP BY period_month, market_code, coupon_type
            ),
            carryover_groups AS (
              SELECT
                period_month,
                market_code,
                coupon_type,
                MAX(coupon_name) AS coupon_name,
                SUM(COALESCE(carryover_amount, 0)) AS nc_carryover_amount
              FROM activity_coupon_nc_carryover
              WHERE period_month = :period_month
                AND (:market_code = '' OR market_code = :market_code)
              GROUP BY period_month, market_code, coupon_type
            ),
            previous_balances AS (
              SELECT
                market_code,
                coupon_type,
                coupon_name,
                ending_balance
              FROM activity_coupon_monthly_balance
              WHERE period_month = :previous_month
                AND (:market_code = '' OR market_code = :market_code)
            ),
            balance_keys AS (
              SELECT market_code, coupon_type FROM movement_groups
              UNION
              SELECT market_code, coupon_type FROM carryover_groups
              UNION
              SELECT market_code, coupon_type FROM previous_balances
            ),
            balance_rows AS (
              SELECT
                :period_month AS period_month,
                k.market_code,
                k.coupon_type,
                COALESCE(m.coupon_name, c.coupon_name, p.coupon_name) AS coupon_name,
                COALESCE(p.ending_balance, 0) AS opening_balance,
                COALESCE(m.current_month_increase, 0) AS current_month_increase,
                COALESCE(m.current_month_decrease, 0) AS current_month_decrease,
                COALESCE(c.nc_carryover_amount, 0) AS nc_carryover_amount,
                COALESCE(m.missing_rate_count, 0) AS missing_rate_count,
                COALESCE(m.movement_count, 0) AS movement_count
              FROM balance_keys k
              LEFT JOIN movement_groups m
                ON m.market_code = k.market_code
               AND m.coupon_type = k.coupon_type
              LEFT JOIN carryover_groups c
                ON c.market_code = k.market_code
               AND c.coupon_type = k.coupon_type
              LEFT JOIN previous_balances p
                ON p.market_code = k.market_code
               AND p.coupon_type = k.coupon_type
            )
            INSERT INTO activity_coupon_monthly_balance (
                period_month,
                market_code,
                coupon_type,
                coupon_name,
                opening_balance,
                current_month_increase,
                current_month_decrease,
                nc_carryover_amount,
                ending_balance,
                missing_rate_count,
                movement_count,
                status,
                created_at,
                updated_at
            )
            SELECT
                period_month,
                market_code,
                coupon_type,
                coupon_name,
                opening_balance,
                current_month_increase,
                current_month_decrease,
                nc_carryover_amount,
                opening_balance + current_month_increase - current_month_decrease - nc_carryover_amount,
                missing_rate_count,
                movement_count,
                'DRAFT',
                NOW(),
                NOW()
            FROM balance_rows
            ON CONFLICT (period_month, market_code, coupon_type)
            DO UPDATE SET
                coupon_name = EXCLUDED.coupon_name,
                opening_balance = EXCLUDED.opening_balance,
                current_month_increase = EXCLUDED.current_month_increase,
                current_month_decrease = EXCLUDED.current_month_decrease,
                nc_carryover_amount = EXCLUDED.nc_carryover_amount,
                ending_balance = EXCLUDED.ending_balance,
                missing_rate_count = EXCLUDED.missing_rate_count,
                movement_count = EXCLUDED.movement_count,
                updated_at = NOW()
            WHERE activity_coupon_monthly_balance.status <> 'CONFIRMED'
            """
        ),
        {"period_month": period_month, "previous_month": previous_month, "market_code": market_code},
    )
    db.commit()
    return {"rebuilt": result.rowcount or 0}


@router.get("/coupon-monthly-balances")
async def coupon_monthly_balances(
    period_month: str = Query(..., description="月份 YYYY-MM"),
    market_code: str | None = Query(None, description="门店编码"),
    coupon_type: str | None = Query(None, description="券字母"),
    balance_status: str | None = Query(None, alias="status", description="DRAFT 或 CONFIRMED"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, COUPON_MONTHLY_VIEW_PERMISSION)
    _ensure_coupon_monthly_tables(db)
    selected_period = _period_or_400(period_month)
    params = {
        "period_month": selected_period,
        "market_code": market_code.strip() if market_code else "",
        "coupon_type": coupon_type.strip().upper() if coupon_type else "",
        "status": balance_status.strip().upper() if balance_status else "",
    }
    return _rows(
        db,
        """
        SELECT
          b.id,
          b.period_month,
          b.market_code,
          b.coupon_type,
          b.coupon_name,
          b.opening_balance,
          b.current_month_increase,
          b.current_month_decrease,
          b.nc_carryover_amount,
          b.ending_balance,
          b.missing_rate_count,
          b.movement_count,
          b.status,
          b.confirmed_at,
          COALESCE(NULLIF(u.real_name, ''), u.username) AS confirmed_by_name,
          b.created_at,
          b.updated_at
        FROM activity_coupon_monthly_balance b
        LEFT JOIN users u ON u.user_id = b.confirmed_by
        WHERE b.period_month = :period_month
          AND (:market_code = '' OR b.market_code = :market_code)
          AND (:coupon_type = '' OR b.coupon_type = :coupon_type)
          AND (:status = '' OR b.status = :status)
        ORDER BY b.period_month DESC, b.market_code, b.coupon_type
        """,
        params,
    )


@router.post("/coupon-monthly-balances/confirm")
async def confirm_coupon_monthly_balances(
    payload: CouponMonthlyBalanceConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, COUPON_MONTHLY_CONFIRM_PERMISSION)
    _ensure_coupon_monthly_tables(db)
    period_month = _period_or_400(payload.period_month)
    market_code = payload.market_code.strip() if payload.market_code else ""
    summary = _one(
        db,
        """
        SELECT
          COUNT(*) FILTER (WHERE status = 'DRAFT') AS draft_count,
          COUNT(*) FILTER (WHERE status = 'DRAFT' AND missing_rate_count > 0) AS missing_rate_rows
        FROM activity_coupon_monthly_balance
        WHERE period_month = :period_month
          AND (:market_code = '' OR market_code = :market_code)
        """,
        {"period_month": period_month, "market_code": market_code},
    )
    if int(summary.get("draft_count") or 0) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="没有可确认的月结草稿")
    if int(summary.get("missing_rate_rows") or 0) > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="存在缺收入占比的月结行，不能确认")

    result = db.execute(
        text(
            """
            UPDATE activity_coupon_monthly_balance
            SET status = 'CONFIRMED',
                confirmed_by = :confirmed_by,
                confirmed_at = NOW(),
                updated_at = NOW()
            WHERE period_month = :period_month
              AND status = 'DRAFT'
              AND (:market_code = '' OR market_code = :market_code)
            """
        ),
        {"period_month": period_month, "market_code": market_code, "confirmed_by": current_user.user_id},
    )
    db.commit()
    return {"confirmed": result.rowcount or 0}


@router.get("/voucher-details")
async def voucher_details(
    start_date: str | None = Query(None, description="凭证业务日期起 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="凭证业务日期止 YYYY-MM-DD"),
    store_code: str | None = Query(None, description="业务门店编码：601/602/603/604"),
    coupon_type: str | None = Query(None, description="券字母"),
    strict_coupon_type: bool = Query(False, description="是否强制按摘要券码过滤；手工选择默认不强制"),
    strict_business_scope: bool = Query(False, description="是否强制按业务日期和摘要门店过滤；手工选择使用"),
    match_type: str = Query("DEBIT_USE", pattern="^(DEBIT_USE|CREDIT_BUY)$"),
    amount: float | None = Query(None, description="参考金额"),
    amount_tolerance: float = Query(5000, ge=0, le=1000000, description="金额上下浮动范围"),
    keyword: str | None = Query(None, description="摘要、凭证主键、辅助核算搜索"),
    valuename: str | None = Query(None, description="辅助核算名称精确筛选"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, VOUCHER_MATCH_VIEW_PERMISSION)
    if not _table_exists(db, "bh_dw_gl_detail_fact2"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="财务凭证明细表 bh_dw_gl_detail_fact2 尚未创建或同步")

    selected_store_code = store_code.strip() if store_code else ""
    selected_voucher_store_code = {
        "601": "101",
        "602": "102",
        "603": "105",
        "604": "604",
    }.get(selected_store_code, selected_store_code)
    selected_pk_corp = {
        "601": "1018",
        "602": "1018",
        "603": "1021",
        "604": "1084",
    }.get(selected_store_code)
    params: dict[str, Any] = {
        "start_date": start_date,
        "end_date": end_date,
        "store_code": selected_store_code,
        "voucher_store_code": selected_voucher_store_code,
        "voucher_pk_corp": selected_pk_corp,
        "coupon_type": coupon_type.strip().upper() if coupon_type else "",
        "strict_coupon_type": strict_coupon_type,
        "strict_business_scope": strict_business_scope,
        "amount": amount,
        "amount_tolerance": amount_tolerance,
        "keyword": f"%{keyword.strip()}%" if keyword and keyword.strip() else "",
        "valuename": valuename.strip() if valuename and valuename.strip() else "",
        "limit": limit,
    }
    amount_expr = "COALESCE(v.localdebitamount, v.debitamount, 0)" if match_type == "DEBIT_USE" else "COALESCE(v.localcreditamount, v.creditamount, 0)"
    voucher_amount_filter_sql = finance_voucher_amount_filter_sql("v")

    return _rows(
        db,
        f"""
        WITH voucher_rows AS MATERIALIZED (
          SELECT
            {VOUCHER_DETAIL_KEY_SQL} AS voucher_detail_id,
            v.pk_detail,
            v.pk_voucher,
            v.pk_corp AS voucher_corp_code,
            CASE v.pk_corp
              WHEN '1018' THEN '购物中心/百货大楼'
              WHEN '1021' THEN '新世纪'
              WHEN '1084' THEN '半山'
              ELSE COALESCE(NULLIF(v.pk_corp, ''), '未标识')
            END AS voucher_corp_name,
            v.subject_code,
            v.explanation,
            COALESCE(v.localdebitamount, v.debitamount, 0) AS debit_amount,
            COALESCE(v.localcreditamount, v.creditamount, 0) AS credit_amount,
            {amount_expr} AS voucher_amount,
            v.valuecode,
            v.valuename,
            v.account_year,
            v.account_period,
            v.load_date,
            SUBSTRING(v.explanation FROM '^\\((10[125]|604)\\)') AS voucher_store_code,
            UPPER(SUBSTRING(v.explanation FROM '0500\\s*促销券\\s*([A-Z])')) AS voucher_coupon_type,
            CASE
              WHEN SUBSTRING(v.explanation FROM '(20[0-9]{{2}}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01]))') IS NOT NULL
                THEN TO_DATE(SUBSTRING(v.explanation FROM '(20[0-9]{{2}}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01]))'), 'YYYYMMDD')
              WHEN SUBSTRING(v.explanation FROM '(20[0-9]{{2}}\\.(0?[1-9]|1[0-2])\\.(0?[1-9]|[12][0-9]|3[01]))') IS NOT NULL
                THEN TO_DATE(SUBSTRING(v.explanation FROM '(20[0-9]{{2}}\\.(0?[1-9]|1[0-2])\\.(0?[1-9]|[12][0-9]|3[01]))'), 'YYYY.MM.DD')
              ELSE NULL
            END AS voucher_business_date
          FROM bh_dw_gl_detail_fact2 v
          WHERE {voucher_amount_filter_sql}
            AND (
              :store_code = ''
              OR (
                :strict_business_scope IS TRUE
                AND SUBSTRING(v.explanation FROM '^\\((10[125]|604)\\)') = :voucher_store_code
              )
              OR (
                :strict_business_scope IS FALSE
                AND (
                  v.pk_corp = :voucher_pk_corp
                  OR SUBSTRING(v.explanation FROM '^\\((10[125]|604)\\)') = :voucher_store_code
                )
              )
            )
            AND (
              :strict_coupon_type IS FALSE
              OR :coupon_type = ''
              OR UPPER(SUBSTRING(v.explanation FROM '0500\\s*促销券\\s*([A-Z])')) = :coupon_type
              OR v.explanation ILIKE ('%促销券' || :coupon_type || '%')
            )
            AND (:valuename = '' OR TRIM(BOTH FROM COALESCE(v.valuename, '')) = :valuename)
            AND (:keyword = '' OR v.explanation ILIKE :keyword OR v.pk_voucher ILIKE :keyword OR v.pk_detail ILIKE :keyword OR v.valuename ILIKE :keyword)
            AND (:amount IS NULL OR ABS({amount_expr} - :amount) <= :amount_tolerance)
        )
        SELECT
          *,
          CASE
            WHEN :amount IS NULL THEN NULL
            ELSE voucher_amount - :amount
          END AS amount_diff
        FROM voucher_rows
        WHERE (:strict_business_scope IS FALSE OR voucher_business_date IS NOT NULL)
          AND (:start_date IS NULL OR (:strict_business_scope IS FALSE AND voucher_business_date IS NULL) OR voucher_business_date >= CAST(:start_date AS DATE))
          AND (:end_date IS NULL OR (:strict_business_scope IS FALSE AND voucher_business_date IS NULL) OR voucher_business_date <= CAST(:end_date AS DATE))
        ORDER BY
          CASE
            WHEN :coupon_type <> '' AND (voucher_coupon_type = :coupon_type OR explanation ILIKE ('%促销券' || :coupon_type || '%')) THEN 0
            ELSE 1
          END,
          CASE WHEN :amount IS NULL THEN 0 ELSE ABS(voucher_amount - :amount) END,
          voucher_business_date NULLS LAST,
          load_date DESC NULLS LAST
        LIMIT :limit
        """,
        params,
    )


@router.get("/coupon-flows")
async def coupon_flows(
    activity_id: str | None = Query(None, description="活动档期编码 tktpopinfo.tpiid"),
    scope: str = Query("activity", pattern="^(activity|standalone|all)$", description="activity 活动档期券；standalone 非档期券；all 全部卡券"),
    start_date: str | None = Query(None, description="日志日期起 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="日志日期止 YYYY-MM-DD"),
    store_code: str | None = Query(None, description="门店编码"),
    keyword: str | None = Query(None, description="券号/会员/小票/流水搜索"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, ACTIVITY_ANALYSIS_PERMISSION)
    _ensure_required_tables(db)

    business_scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    params: dict[str, Any] = {}
    activity_scope_sql = _activity_scope_filter_sql(db, business_scope, params, alias="p", prefix="flows")
    log_scope_sql = _activity_log_scope_filter_sql(db, business_scope, params, alias="l", prefix="flows_logs")
    log_filter, log_params = _activity_filter(activity_id, start_date, end_date, scope, activity_scope_sql, log_scope_sql)
    params.update(log_params)
    selected_store_code = _require_selected_activity_store(db, business_scope, store_code)
    selected_store_sql = _selected_store_clause(
        selected_store_code,
        params,
        expression="l.tcflmkt",
        prefix="flows",
    )
    log_filter = f"({log_filter}){selected_store_sql}"
    params.update({"limit": limit, "offset": offset})
    keyword_filter = ""
    if keyword:
        params["keyword"] = f"%{keyword.strip()}%"
        keyword_filter = """
          AND (
            l.tcflvipno ILIKE :keyword
            OR l.tcflqno ILIKE :keyword
            OR l.tcflinvno ILIKE :keyword
            OR h.billno::varchar ILIKE :keyword
            OR h.hykh ILIKE :keyword
          )
        """

    return _rows(
        db,
        f"""
        WITH coupon_pay AS (
          SELECT
            billno,
            batch,
            SUM(COALESCE(je, 0)) AS coupon_pay_amount,
            STRING_AGG(DISTINCT COALESCE(NULLIF(payname, ''), paycode), '、') AS coupon_pay_names
          FROM salepay
          WHERE paycode IN ('0500', '0580')
          GROUP BY billno, batch
        ),
        sale_bill AS (
          SELECT
            sglbillno AS billno,
            SUM(COALESCE(sglxssr, 0)) AS sales_amount,
            SUM(COALESCE(sgln2, 0)) AS gross_profit,
            SUM(COALESCE(sglnetml, sgln2, 0)) AS net_profit
          FROM salegoodslist
          GROUP BY sglbillno
        )
        SELECT
          l.tcflseqno AS flow_id,
          l.tcfldate AS flow_date,
          l.tcflzy AS action_code,
          {_case_expr("l.tcflzy", ACTION_LABELS, "'未知动作'")} AS action_name,
          l.tcflsource AS source_code,
          {_case_expr("l.tcflsource", SOURCE_LABELS, "'未知来源'")} AS source_name,
          l.tcflpopid AS activity_id,
          p.tpiname AS activity_name,
          l.tcflvipno AS member_no,
          l.tcflqno AS coupon_no,
          l.tcflmoney AS raw_flow_amount,
          {ACTION_AMOUNT_SQL} AS flow_amount,
          l.tcflye AS balance_amount,
          l.tcflmkt AS market_code,
          l.tcflsyjid AS cashier_no,
          l.tcflinvno AS invoice_no,
          l.tcflsyjtrace AS trace_no,
          h.billno,
          h.rqsj AS sale_time,
          h.hykh AS sale_member_no,
          COALESCE(cp.coupon_pay_amount, 0) AS coupon_pay_amount,
          COALESCE(cp.coupon_pay_names, '') AS coupon_pay_names,
          COALESCE(sb.sales_amount, 0) AS sales_amount,
          COALESCE(sb.gross_profit, 0) AS gross_profit,
          COALESCE(sb.net_profit, 0) AS net_profit
        FROM tktcardfqlog l
        LEFT JOIN tktpopinfo p ON p.tpiid = l.tcflpopid
        LEFT JOIN salehead h
          ON l.tcflmkt = h.mkt
         AND l.tcflsyjid = h.syjh
         AND l.tcflinvno ~ '^[0-9]+$'
         AND h.fphm = l.tcflinvno::numeric
        LEFT JOIN coupon_pay cp
          ON cp.billno = h.billno
         AND cp.batch = l.tcflsyjtrace::varchar
        LEFT JOIN sale_bill sb ON sb.billno = h.billno
        WHERE {log_filter}
          {keyword_filter}
        ORDER BY l.tcfldate DESC, l.tcflseqno DESC
        LIMIT :limit OFFSET :offset
        """,
        params,
    )


@router.get("/quality-issues")
async def quality_issues(
    activity_id: str | None = Query(None, description="活动档期编码 tktpopinfo.tpiid"),
    scope: str = Query("activity", pattern="^(activity|standalone|all)$", description="activity 活动档期券；standalone 非档期券；all 全部卡券"),
    start_date: str | None = Query(None, description="日志/销售日期起 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="日志/销售日期止 YYYY-MM-DD"),
    store_code: str | None = Query(None, description="门店编码"),
    issue_type: str = Query("unmatched_logs", description="unmatched_logs/payments_without_logs/amount_mismatch/missing_member/unassigned_activity"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, ACTIVITY_ANALYSIS_PERMISSION)
    _ensure_required_tables(db)

    business_scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    activity_scope_params: dict[str, Any] = {}
    activity_scope_sql = _activity_scope_filter_sql(db, business_scope, activity_scope_params, alias="p", prefix="quality")
    log_scope_sql = _activity_log_scope_filter_sql(db, business_scope, activity_scope_params, alias="l", prefix="quality_logs")
    log_filter, log_params = _activity_filter(activity_id, start_date, end_date, scope, activity_scope_sql, log_scope_sql)
    period_filter, period_params = _period_filter(activity_id, start_date, end_date)
    params = {**activity_scope_params, **log_params, **period_params, "limit": limit}
    selected_store_code = _require_selected_activity_store(db, business_scope, store_code)
    selected_store_sql = _selected_store_clause(
        selected_store_code,
        params,
        expression="l.tcflmkt",
        prefix="quality_logs",
    )
    log_filter = f"({log_filter}){selected_store_sql}"
    period_scope_sql = _activity_market_scope_filter_sql(
        db,
        business_scope,
        params,
        expression="h.mkt",
        prefix="quality_period_scope",
    )
    period_store_sql = _selected_store_clause(
        selected_store_code,
        params,
        expression="h.mkt",
        prefix="quality_period",
    )
    period_filter = f"({period_filter}){period_scope_sql}{period_store_sql}"
    unassigned_store_sql = _selected_store_clause(
        selected_store_code,
        params,
        expression="l.tcflmkt",
        prefix="quality_unassigned",
    )

    if issue_type == "unmatched_logs":
        return _rows(
            db,
            f"""
            SELECT
              l.tcflseqno AS flow_id,
              l.tcfldate AS flow_date,
              l.tcflpopid AS activity_id,
              l.tcflvipno AS member_no,
              l.tcflqno AS coupon_no,
              l.tcflmoney AS flow_amount,
              l.tcflmkt AS market_code,
              l.tcflsyjid AS cashier_no,
              l.tcflinvno AS invoice_no,
              l.tcflsyjtrace AS trace_no,
              '卡券日志无法关联小票' AS issue
            FROM tktcardfqlog l
            WHERE {log_filter}
              AND NOT EXISTS (
                SELECT 1
                FROM salehead h
                WHERE l.tcflmkt = h.mkt
                  AND l.tcflsyjid = h.syjh
                  AND l.tcflinvno ~ '^[0-9]+$'
                  AND h.fphm = l.tcflinvno::numeric
              )
            ORDER BY l.tcfldate DESC, l.tcflseqno DESC
            LIMIT :limit
            """,
            params,
        )

    if issue_type == "unassigned_activity":
        return _rows(
            db,
            f"""
            SELECT
              l.tcflseqno AS flow_id,
              l.tcfldate AS flow_date,
              l.tcflpopid AS activity_id,
              l.tcflvipno AS member_no,
              l.tcflqno AS coupon_no,
              l.tcflzy AS action_code,
              {_case_expr("l.tcflzy", ACTION_LABELS, "'未知动作'")} AS action_name,
              l.tcflsource AS source_code,
              {_case_expr("l.tcflsource", SOURCE_LABELS, "'未知来源'")} AS source_name,
              l.tcflmoney AS raw_flow_amount,
              {ACTION_AMOUNT_SQL} AS flow_amount,
              l.tcflmkt AS market_code,
              l.tcflsyjid AS cashier_no,
              l.tcflinvno AS invoice_no,
              l.tcflsyjtrace AS trace_no,
              '卡券日志无活动档期归属' AS issue
            FROM tktcardfqlog l
            WHERE (COALESCE(l.tcflpopid, '') IN ('', '0') OR NOT EXISTS (SELECT 1 FROM tktpopinfo p WHERE p.tpiid = l.tcflpopid))
              {log_scope_sql}
              {unassigned_store_sql}
              { "AND l.tcfldate >= :start_date" if start_date else "" }
              { "AND l.tcfldate <= :end_date" if end_date else "" }
            ORDER BY l.tcfldate DESC, l.tcflseqno DESC
            LIMIT :limit
            """,
            params,
        )

    if issue_type == "payments_without_logs":
        return _rows(
            db,
            f"""
            SELECT
              p.billno,
              h.rqsj AS sale_time,
              h.mkt AS market_code,
              h.syjh AS cashier_no,
              h.fphm AS invoice_no,
              h.hykh AS member_no,
              p.rowno AS payment_rowno,
              p.paycode,
              COALESCE(NULLIF(p.payname, ''), p.paycode) AS payname,
              p.payno,
              p.batch,
              p.je AS payment_amount,
              '0500/0580付款未匹配卡券流水' AS issue
            FROM salepay p
            JOIN salehead h ON h.billno = p.billno
            WHERE p.paycode IN ('0500', '0580')
              AND {period_filter}
              AND NOT EXISTS (
                SELECT 1
                FROM tktcardfqlog l
                WHERE p.batch = l.tcflsyjtrace::varchar
              )
            ORDER BY h.rqsj DESC, p.billno DESC
            LIMIT :limit
            """,
            params,
        )

    if issue_type == "amount_mismatch":
        return _rows(
            db,
            f"""
            WITH log_bill AS (
              SELECT
                h.billno,
                MIN(h.rqsj) AS sale_time,
                MIN(h.hykh) AS member_no,
                SUM(CASE WHEN l.tcflzy = 'O' THEN ABS(COALESCE(l.tcflmoney, 0)) WHEN l.tcflzy = 'U' THEN -ABS(COALESCE(l.tcflmoney, 0)) ELSE 0 END) AS log_amount
              FROM tktcardfqlog l
              JOIN salehead h
                ON l.tcflmkt = h.mkt
               AND l.tcflsyjid = h.syjh
               AND l.tcflinvno ~ '^[0-9]+$'
               AND h.fphm = l.tcflinvno::numeric
              WHERE {log_filter}
              GROUP BY h.billno
            ),
            pay_bill AS (
              SELECT p.billno, SUM(COALESCE(p.je, 0)) AS payment_amount
              FROM salepay p
              JOIN tktcardfqlog l
                ON p.batch = l.tcflsyjtrace::varchar
               AND l.tcflzy = 'O'
              JOIN salehead h
                ON l.tcflmkt = h.mkt
               AND l.tcflsyjid = h.syjh
               AND l.tcflinvno ~ '^[0-9]+$'
               AND h.fphm = l.tcflinvno::numeric
               AND h.billno = p.billno
              WHERE p.paycode IN ('0500', '0580')
                AND {log_filter}
              GROUP BY p.billno
            )
            SELECT
              lb.billno,
              lb.sale_time,
              lb.member_no,
              lb.log_amount,
              COALESCE(pb.payment_amount, 0) AS payment_amount,
              COALESCE(pb.payment_amount, 0) - lb.log_amount AS difference_amount,
              '卡券日志金额与付款金额不一致' AS issue
            FROM log_bill lb
            LEFT JOIN pay_bill pb ON pb.billno = lb.billno
            WHERE lb.log_amount <> 0
              AND ABS(COALESCE(pb.payment_amount, 0) - lb.log_amount) > 0.01
            ORDER BY ABS(COALESCE(pb.payment_amount, 0) - lb.log_amount) DESC
            LIMIT :limit
            """,
            params,
        )

    if issue_type == "missing_member":
        return _rows(
            db,
            f"""
            SELECT DISTINCT
              h.billno,
              h.rqsj AS sale_time,
              h.mkt AS market_code,
              h.syjh AS cashier_no,
              h.fphm AS invoice_no,
              h.hykh AS member_no,
              SUM(COALESCE(l.tcflmoney, 0)) AS log_amount,
              '小票无会员号' AS issue
            FROM tktcardfqlog l
            JOIN salehead h
              ON l.tcflmkt = h.mkt
             AND l.tcflsyjid = h.syjh
             AND l.tcflinvno ~ '^[0-9]+$'
             AND h.fphm = l.tcflinvno::numeric
            WHERE {log_filter}
              AND NULLIF(h.hykh, '') IS NULL
            GROUP BY h.billno, h.rqsj, h.mkt, h.syjh, h.fphm, h.hykh
            ORDER BY h.rqsj DESC, h.billno DESC
            LIMIT :limit
            """,
            params,
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="issue_type 仅支持 unmatched_logs/payments_without_logs/amount_mismatch/missing_member/unassigned_activity",
    )
