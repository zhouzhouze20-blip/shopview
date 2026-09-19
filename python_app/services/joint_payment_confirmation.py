"""联营付款单生成/审核状态查询。

联营口径来自 ``paybatch.pbwmid = '4'``，付款单状态来自
``suppayhead.sphflag``：M=生成，Y=已审核。付款单金额按当前可见的
paybatch 行汇总 ``pbsf``，避免多柜组付款单越权暴露其他柜组金额。
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass, replace
from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.daily_followup_report import _shopview_today
from services.erp_settlement_service import _row_dict, _sql_expr_in_binds, _table_exists
from services.monthly_followup_report import financial_month_period


@dataclass(frozen=True)
class JointPaymentFilters:
    page: int = 1
    page_size: int = 20
    status: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    market: str | None = None
    department_code: str | None = None
    group_prefix: str | None = None
    supplier_code: str | None = None
    supplier_name: str | None = None
    keyword: str | None = None
    market_exact: bool = False
    financial_month: str | None = None
    include_supplier_confirmation: bool = False
    include_banshan: bool = False


@dataclass(frozen=True)
class BusinessScope:
    all_access: bool = False
    group_allow: frozenset[str] = frozenset()
    group_deny: frozenset[str] = frozenset()
    department_allow: frozenset[str] = frozenset()
    department_deny: frozenset[str] = frozenset()


def payment_generation_month_period(financial_month: str) -> tuple[date, date]:
    """付款单按生成月份归属，29—31日仍归当月，不改变其他模块财务月规则。"""
    if not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", financial_month):
        raise ValueError("财务月格式应为 YYYY-MM")
    year, month = map(int, financial_month.split("-"))
    return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])


def current_financial_month_period(as_of_date: date | None = None) -> tuple[date, date]:
    """返回指定日期所在的 ShopView 财务月闭区间。"""
    current_date = as_of_date or _shopview_today()
    for financial_month in range(1, 13):
        start_date, end_date = financial_month_period(current_date.year, financial_month)
        if start_date <= current_date <= end_date:
            return start_date, end_date
    raise ValueError(f"date is outside the ShopView financial calendar: {current_date.isoformat()}")


def _payment_business_where(include_banshan: bool, alias: str = "pb", head_alias: str | None = None) -> str:
    joint = f"TRIM(COALESCE({alias}.pbwmid::text, '')) = '4'"
    if not include_banshan:
        return joint
    # The mobile module additionally includes Banshan's rate-based consignment.
    # Match the payment head's actual store, not a guessed group-code prefix.
    store_check = (
        f"TRIM({head_alias}.sphmkt::text) = '604'"
        if head_alias else f"""EXISTS (
            SELECT 1 FROM suppayhead banshan_head
            WHERE banshan_head.sphbillno = {alias}.pbpaybillno
              AND TRIM(banshan_head.sphmkt::text) = '604'
        )"""
    )
    return f"({joint} OR (TRIM(COALESCE({alias}.pbwmid::text, '')) = '3' AND {store_check}))"



def _visible_batch_where(filters: JointPaymentFilters, scope: BusinessScope, *, head_alias: str | None = None) -> tuple[str, dict[str, Any]]:
    conditions = [
        "NULLIF(TRIM(pb.pbpaybillno), '') IS NOT NULL",
        _payment_business_where(filters.include_banshan, head_alias=head_alias),
    ]
    params: dict[str, Any] = {}
    group_expr = "TRIM(UPPER(COALESCE(pb.pbmfid::text, '')))"
    department_code_expr = "TRIM(UPPER(COALESCE(dept.mfcode::text, '')))"
    department_name_expr = "TRIM(UPPER(COALESCE(dept.mfcname::text, '')))"

    if not scope.all_access:
        allow_conditions: list[str] = []
        if scope.group_allow:
            allow_sql, allow_params = _sql_expr_in_binds(
                group_expr,
                sorted(scope.group_allow),
                "joint_payment_allow_group",
            )
            allow_conditions.append(allow_sql)
            params.update(allow_params)
        if scope.department_allow:
            department_code_sql, department_code_params = _sql_expr_in_binds(
                department_code_expr,
                sorted(scope.department_allow),
                "joint_payment_allow_department_code",
            )
            department_name_sql, department_name_params = _sql_expr_in_binds(
                department_name_expr,
                sorted(scope.department_allow),
                "joint_payment_allow_department_name",
            )
            allow_conditions.append(f"({department_code_sql} OR {department_name_sql})")
            params.update(department_code_params)
            params.update(department_name_params)
        if not allow_conditions:
            conditions.append("FALSE")
        else:
            conditions.append("(" + " OR ".join(allow_conditions) + ")")
        if scope.group_deny:
            deny_sql, deny_params = _sql_expr_in_binds(
                group_expr,
                sorted(scope.group_deny),
                "joint_payment_deny_group",
            )
            conditions.append(f"NOT ({deny_sql})")
            params.update(deny_params)
        if scope.department_deny:
            deny_code_sql, deny_code_params = _sql_expr_in_binds(
                department_code_expr,
                sorted(scope.department_deny),
                "joint_payment_deny_department_code",
            )
            deny_name_sql, deny_name_params = _sql_expr_in_binds(
                department_name_expr,
                sorted(scope.department_deny),
                "joint_payment_deny_department_name",
            )
            conditions.append(f"NOT ({deny_code_sql} OR {deny_name_sql})")
            params.update(deny_code_params)
            params.update(deny_name_params)

    department_code = (filters.department_code or "").strip().upper()
    if department_code:
        conditions.append(f"{department_code_expr} = :joint_payment_department_code")
        params["joint_payment_department_code"] = department_code

    prefix = (filters.group_prefix or "").strip().upper()
    if prefix:
        conditions.append(f"{group_expr} LIKE :joint_payment_group_prefix")
        params["joint_payment_group_prefix"] = f"{prefix}%"

    return " AND ".join(conditions), params


def _visible_charge_where(scope: BusinessScope) -> tuple[str, dict[str, Any]]:
    """Build the same group/department scope for supsetcharge alias ``aa``."""
    conditions: list[str] = []
    params: dict[str, Any] = {}
    group_expr = "TRIM(UPPER(COALESCE(aa.sscmfid::text, '')))"

    if scope.all_access:
        return "TRUE", params

    allow_conditions: list[str] = []
    if scope.group_allow:
        allow_sql, allow_params = _sql_expr_in_binds(
            group_expr,
            sorted(scope.group_allow),
            "joint_payment_charge_allow_group",
        )
        allow_conditions.append(allow_sql)
        params.update(allow_params)
    if scope.department_allow:
        department_code_sql, department_code_params = _sql_expr_in_binds(
            "TRIM(UPPER(COALESCE(charge_dept.mfcode::text, '')))",
            sorted(scope.department_allow),
            "joint_payment_charge_allow_department_code",
        )
        department_name_sql, department_name_params = _sql_expr_in_binds(
            "TRIM(UPPER(COALESCE(charge_dept.mfcname::text, '')))",
            sorted(scope.department_allow),
            "joint_payment_charge_allow_department_name",
        )
        allow_conditions.append(
            "EXISTS ("
            "SELECT 1 FROM manaframe charge_group "
            "LEFT JOIN manaframe charge_dept "
            "ON TRIM(UPPER(charge_dept.mfcode)) = TRIM(UPPER(charge_group.mfpcode)) "
            "WHERE TRIM(UPPER(charge_group.mfcode)) = " + group_expr + " "
            f"AND ({department_code_sql} OR {department_name_sql})"
            ")"
        )
        params.update(department_code_params)
        params.update(department_name_params)
    conditions.append("(" + " OR ".join(allow_conditions) + ")" if allow_conditions else "FALSE")

    if scope.group_deny:
        deny_sql, deny_params = _sql_expr_in_binds(
            group_expr,
            sorted(scope.group_deny),
            "joint_payment_charge_deny_group",
        )
        conditions.append(f"NOT ({deny_sql})")
        params.update(deny_params)
    if scope.department_deny:
        deny_code_sql, deny_code_params = _sql_expr_in_binds(
            "TRIM(UPPER(COALESCE(charge_deny_dept.mfcode::text, '')))",
            sorted(scope.department_deny),
            "joint_payment_charge_deny_department_code",
        )
        deny_name_sql, deny_name_params = _sql_expr_in_binds(
            "TRIM(UPPER(COALESCE(charge_deny_dept.mfcname::text, '')))",
            sorted(scope.department_deny),
            "joint_payment_charge_deny_department_name",
        )
        conditions.append(
            "NOT EXISTS ("
            "SELECT 1 FROM manaframe charge_deny_group "
            "LEFT JOIN manaframe charge_deny_dept "
            "ON TRIM(UPPER(charge_deny_dept.mfcode)) = TRIM(UPPER(charge_deny_group.mfpcode)) "
            "WHERE TRIM(UPPER(charge_deny_group.mfcode)) = " + group_expr + " "
            f"AND ({deny_code_sql} OR {deny_name_sql})"
            ")"
        )
        params.update(deny_code_params)
        params.update(deny_name_params)

    return " AND ".join(conditions), params


def build_joint_payment_query_parts(
    filters: JointPaymentFilters,
    scope: BusinessScope,
    *,
    head_prefilter_audit_period: tuple[date, date] | None = None,
) -> tuple[str, str, dict[str, Any]]:
    """返回可复用于汇总、计数和列表的 CTE 与公共付款头筛选。"""
    batch_where, params = _visible_batch_where(filters, scope, head_alias="h_prefilter")
    market = (filters.market or "").strip()
    supplier_code = (filters.supplier_code or "").strip().upper()
    supplier_name = (filters.supplier_name or "").strip()
    keyword = (filters.keyword or "").strip()

    common_conditions = ["TRIM(COALESCE(h.sphflag::text, '')) IN ('M', 'Y')"]
    # 先用付款单头的月份、门店等高选择性条件缩小候选单据，再关联并聚合
    # paybatch。否则部门筛选会先扫描、关联和聚合全部历史批次，正式库容易
    # 触发 30 秒 statement_timeout。
    head_prefilter_conditions = [
        "TRIM(COALESCE(h_prefilter.sphflag::text, '')) IN ('M', 'Y')",
    ]
    if filters.financial_month:
        generation_start, generation_end = payment_generation_month_period(filters.financial_month)
        common_conditions.extend([
            "h.inputdate >= CAST(:joint_payment_generation_start AS date)",
            "h.inputdate < CAST(:joint_payment_generation_end AS date) + INTERVAL '1 day'",
        ])
        head_prefilter_conditions.extend([
            "h_prefilter.inputdate >= CAST(:joint_payment_generation_start AS date)",
            "h_prefilter.inputdate < CAST(:joint_payment_generation_end AS date) + INTERVAL '1 day'",
        ])
        params["joint_payment_generation_start"] = generation_start.isoformat()
        params["joint_payment_generation_end"] = generation_end.isoformat()
    if filters.date_from:
        status_date_from = (
            "CASE WHEN TRIM({alias}.sphflag::text) = 'Y' THEN {alias}.auditdate "
            "ELSE {alias}.inputdate END >= CAST(:joint_payment_date_from AS date)"
        )
        common_conditions.append(status_date_from.format(alias="h"))
        head_prefilter_conditions.append(status_date_from.format(alias="h_prefilter"))
        params["joint_payment_date_from"] = filters.date_from
    if filters.date_to:
        status_date_to = (
            "CASE WHEN TRIM({alias}.sphflag::text) = 'Y' THEN {alias}.auditdate "
            "ELSE {alias}.inputdate END < CAST(:joint_payment_date_to AS date) + INTERVAL '1 day'"
        )
        common_conditions.append(status_date_to.format(alias="h"))
        head_prefilter_conditions.append(status_date_to.format(alias="h_prefilter"))
        params["joint_payment_date_to"] = filters.date_to
    if market:
        operator = "=" if filters.market_exact else "ILIKE"
        common_conditions.append(f"TRIM(COALESCE(h.sphmkt::text, '')) {operator} :joint_payment_market")
        head_prefilter_conditions.append(
            f"TRIM(COALESCE(h_prefilter.sphmkt::text, '')) {operator} :joint_payment_market"
        )
        params["joint_payment_market"] = market if filters.market_exact else f"%{market}%"
    if supplier_code:
        common_conditions.append(
            "TRIM(UPPER(COALESCE(h.sphsupid::text, ''))) = :joint_payment_supplier_code"
        )
        head_prefilter_conditions.append(
            "TRIM(UPPER(COALESCE(h_prefilter.sphsupid::text, ''))) = :joint_payment_supplier_code"
        )
        params["joint_payment_supplier_code"] = supplier_code
    if head_prefilter_audit_period is not None:
        audit_start, audit_end = head_prefilter_audit_period
        head_prefilter_conditions.extend([
            "h_prefilter.auditdate >= :joint_payment_head_audit_start",
            "h_prefilter.auditdate < :joint_payment_head_audit_end + INTERVAL '1 day'",
        ])
        params["joint_payment_head_audit_start"] = audit_start
        params["joint_payment_head_audit_end"] = audit_end
    if supplier_name:
        common_conditions.append(
            "COALESCE(sb.sbcname::text, '') ILIKE :joint_payment_supplier_name"
        )
        params["joint_payment_supplier_name"] = f"%{supplier_name}%"
    if keyword:
        common_conditions.append(
            "(TRIM(COALESCE(h.sphbillno::text, '')) ILIKE :joint_payment_keyword "
            "OR TRIM(COALESCE(h.sphsupid::text, '')) ILIKE :joint_payment_keyword "
            "OR COALESCE(sb.sbcname::text, '') ILIKE :joint_payment_keyword "
            "OR EXISTS (SELECT 1 FROM paybatch pb_kw "
            "WHERE TRIM(pb_kw.pbpaybillno) = TRIM(h.sphbillno) "
            "AND (TRIM(COALESCE(pb_kw.pbjsno::text, '')) ILIKE :joint_payment_keyword "
            "OR TRIM(COALESCE(pb_kw.pbcontno::text, '')) ILIKE :joint_payment_keyword)))"
        )
        params["joint_payment_keyword"] = f"%{keyword}%"

    cte_sql = f"""
    WITH visible_batch AS (
      SELECT
        TRIM(pb.pbpaybillno) AS payment_bill_no,
        SUM(COALESCE(pb.pbsf, 0)) AS payment_amount,
        COUNT(*) AS detail_row_count,
        COUNT(DISTINCT NULLIF(TRIM(pb.pbjsno), '')) AS settlement_count,
        COUNT(DISTINCT NULLIF(TRIM(dept.mfcode::text), '')) AS department_count,
        STRING_AGG(
          DISTINCT TRIM(dept.mfcode::text), ', '
          ORDER BY TRIM(dept.mfcode::text)
        ) FILTER (WHERE NULLIF(TRIM(dept.mfcode::text), '') IS NOT NULL) AS department_codes,
        STRING_AGG(
          DISTINCT TRIM(dept.mfcname::text), ', '
          ORDER BY TRIM(dept.mfcname::text)
        ) FILTER (WHERE NULLIF(TRIM(dept.mfcname::text), '') IS NOT NULL) AS department_names,
        COUNT(DISTINCT NULLIF(TRIM(pb.pbmfid::text), '')) AS group_count
      FROM suppayhead h_prefilter
      INNER JOIN paybatch pb ON pb.pbpaybillno = h_prefilter.sphbillno
      LEFT JOIN manaframe group_mf ON group_mf.mfcode = pb.pbmfid
      LEFT JOIN manaframe dept ON dept.mfcode = group_mf.mfpcode
      WHERE {' AND '.join(head_prefilter_conditions)}
        AND {batch_where}
      GROUP BY TRIM(pb.pbpaybillno)
    )
    """
    return cte_sql, " AND ".join(common_conditions), params


def _supplier_confirmation_available(db: Session) -> bool:
    """The confirmation flag lives in the ODS payment head, not invoice rows."""
    return bool(db.execute(text(
        "SELECT to_regclass('ods.js_supplier_order_head_rela') IS NOT NULL"
    )).scalar())


def _supplier_confirmed_expression(available: bool) -> str:
    if not available:
        return "NULL::boolean"
    # EXISTS keeps one payment even if the source later contains duplicate rows.
    # Status 0 means active; invoice_status 1 is the explicit supplier confirmation.
    return """EXISTS (
        SELECT 1 FROM ods.js_supplier_order_head_rela supplier_confirmation
        WHERE TRIM(supplier_confirmation.id::text) = TRIM(h.sphbillno::text)
          AND TRIM(supplier_confirmation.status::text) = '0'
          AND TRIM(supplier_confirmation.invoice_status::text) = '1'
    )"""


def _empty_result(filters: JointPaymentFilters) -> dict[str, Any]:
    financial_month_start, financial_month_end = current_financial_month_period()
    return {
        "summary": {
            "total_generated_count": 0,
            "total_generated_supplier_count": 0,
            "total_generated_amount": 0.0,
            "supplier_confirmation_available": False,
            "supplier_confirmed_count": None,
            "supplier_confirmed_supplier_count": None,
            "supplier_confirmed_amount": None,
            "supplier_unreported_count": None,
            "supplier_unreported_supplier_count": None,
            "supplier_unreported_amount": None,
            "generated_count": 0,
            "generated_supplier_count": 0,
            "generated_amount": 0.0,
            "audited_count": 0,
            "audited_supplier_count": 0,
            "audited_amount": 0.0,
            "current_financial_month_audited_amount": 0.0,
            "current_financial_month_start": financial_month_start.isoformat(),
            "current_financial_month_end": financial_month_end.isoformat(),
            "latest_status_date": None,
        },
        "items": [],
        "total": 0,
        "page": filters.page,
        "page_size": filters.page_size,
    }


def query_joint_payments(
    db: Session,
    filters: JointPaymentFilters,
    scope: BusinessScope,
) -> dict[str, Any]:
    if (
        not _table_exists(db, "suppayhead")
        or not _table_exists(db, "paybatch")
        or not _table_exists(db, "manaframe")
    ):
        return _empty_result(filters)

    cte_sql, common_where, params = build_joint_payment_query_parts(filters, scope)
    has_supplier = _table_exists(db, "supplierbase")
    supplier_join = (
        "LEFT JOIN supplierbase sb ON TRIM(sb.sbid) = TRIM(h.sphsupid)"
        if has_supplier
        else ""
    )
    supplier_select = "sb.sbcname" if has_supplier else "NULL::text"
    if not has_supplier:
        common_where = common_where.replace(
            "OR COALESCE(sb.sbcname::text, '') ILIKE :joint_payment_keyword ",
            "",
        )
        common_where = common_where.replace(
            "COALESCE(sb.sbcname::text, '') ILIKE :joint_payment_supplier_name",
            "FALSE",
        )

    confirmation_available = filters.include_supplier_confirmation and _supplier_confirmation_available(db)
    confirmed_expr = _supplier_confirmed_expression(confirmation_available)

    from_sql = f"""
      FROM visible_batch vb
      INNER JOIN suppayhead h ON TRIM(h.sphbillno) = vb.payment_bill_no
      {supplier_join}
      WHERE {common_where}
    """

    summary_row = db.execute(
        text(
            f"""
            {cte_sql}
            SELECT
              COUNT(*) AS total_generated_count,
              COUNT(DISTINCT NULLIF(TRIM(h.sphsupid::text), '')) AS total_generated_supplier_count,
              COALESCE(SUM(vb.payment_amount), 0) AS total_generated_amount,
              COUNT(*) FILTER (WHERE NOT ({confirmed_expr})) AS supplier_unreported_count,
              COUNT(DISTINCT NULLIF(TRIM(h.sphsupid::text), ''))
                FILTER (WHERE NOT ({confirmed_expr})) AS supplier_unreported_supplier_count,
              COALESCE(SUM(vb.payment_amount) FILTER (WHERE NOT ({confirmed_expr})), 0) AS supplier_unreported_amount,
              COUNT(*) FILTER (WHERE {confirmed_expr}) AS supplier_confirmed_count,
              COUNT(DISTINCT NULLIF(TRIM(h.sphsupid::text), ''))
                FILTER (WHERE {confirmed_expr}) AS supplier_confirmed_supplier_count,
              COALESCE(SUM(vb.payment_amount) FILTER (WHERE {confirmed_expr}), 0) AS supplier_confirmed_amount,
              COUNT(*) FILTER (WHERE TRIM(h.sphflag::text) = 'M') AS generated_count,
              COUNT(DISTINCT NULLIF(TRIM(h.sphsupid::text), ''))
                FILTER (WHERE TRIM(h.sphflag::text) = 'M') AS generated_supplier_count,
              COALESCE(SUM(vb.payment_amount) FILTER (WHERE TRIM(h.sphflag::text) = 'M'), 0) AS generated_amount,
              COUNT(*) FILTER (WHERE TRIM(h.sphflag::text) = 'Y') AS audited_count,
              COUNT(DISTINCT NULLIF(TRIM(h.sphsupid::text), ''))
                FILTER (WHERE TRIM(h.sphflag::text) = 'Y') AS audited_supplier_count,
              COALESCE(SUM(vb.payment_amount) FILTER (WHERE TRIM(h.sphflag::text) = 'Y'), 0) AS audited_amount,
              MAX(CASE WHEN TRIM(h.sphflag::text) = 'Y' THEN h.auditdate ELSE h.inputdate END) AS latest_status_date
            {from_sql}
            """
        ),
        params,
    ).fetchone()

    financial_month_start, financial_month_end = current_financial_month_period()
    # 保留桌面端“本财务月按审核日期”指标；手机端所选生成月份使用上面的 audited_amount。
    financial_month_filters = replace(filters, date_from=None, date_to=None, financial_month=None)
    financial_month_cte, financial_month_where, financial_month_params = build_joint_payment_query_parts(
        financial_month_filters,
        scope,
        head_prefilter_audit_period=(financial_month_start, financial_month_end),
    )
    if not has_supplier:
        financial_month_where = financial_month_where.replace(
            "OR COALESCE(sb.sbcname::text, '') ILIKE :joint_payment_keyword ",
            "",
        )
        financial_month_where = financial_month_where.replace(
            "COALESCE(sb.sbcname::text, '') ILIKE :joint_payment_supplier_name",
            "FALSE",
        )
    financial_month_params.update(
        {
            "joint_payment_financial_month_start": financial_month_start,
            "joint_payment_financial_month_end": financial_month_end,
        }
    )
    financial_month_amount_row = db.execute(
        text(
            f"""
            {financial_month_cte}
            SELECT COALESCE(SUM(vb.payment_amount), 0) AS audited_amount
            FROM visible_batch vb
            INNER JOIN suppayhead h ON TRIM(h.sphbillno) = vb.payment_bill_no
            {supplier_join}
            WHERE {financial_month_where}
              AND TRIM(h.sphflag::text) = 'Y'
              AND h.auditdate >= :joint_payment_financial_month_start
              AND h.auditdate < :joint_payment_financial_month_end + INTERVAL '1 day'
            """
        ),
        financial_month_params,
    ).fetchone()

    list_conditions = []
    normalized_status = (filters.status or "").strip().upper()
    if normalized_status in {"M", "Y"}:
        list_conditions.append("TRIM(h.sphflag::text) = :joint_payment_status")
        params["joint_payment_status"] = normalized_status
    if normalized_status in {"C", "N", "U", "P"}:
        if not confirmation_available:
            raise ValueError("供应商确认数据尚未就绪，请稍后重试")
        list_conditions.append(f"NOT ({confirmed_expr})" if normalized_status in {"N", "U"} else confirmed_expr)
        if normalized_status in {"U", "P"}:
            # Both outstanding-work filters exclude audited payments.
            list_conditions.append("TRIM(h.sphflag::text) = :joint_payment_status")
            params["joint_payment_status"] = "M"
    list_tail = "" if not list_conditions else " AND " + " AND ".join(list_conditions)

    count_row = db.execute(
        text(f"{cte_sql} SELECT COUNT(*) AS n {from_sql}{list_tail}"),
        params,
    ).fetchone()
    total = int(count_row.n or 0) if count_row is not None else 0

    page_params = {
        **params,
        "joint_payment_limit": filters.page_size,
        "joint_payment_offset": (filters.page - 1) * filters.page_size,
    }
    rows = db.execute(
        text(
            f"""
            {cte_sql}
            SELECT
              h.sphbillno AS payment_bill_no,
              h.sphflag AS status,
              {confirmed_expr} AS supplier_confirmed,
              CASE TRIM(h.sphflag::text)
                WHEN 'M' THEN '生成（待确认）'
                WHEN 'Y' THEN '已审核（财务收入已确认）'
                ELSE TRIM(h.sphflag::text)
              END AS status_label,
              h.sphmkt AS market_code,
              h.sphsupid AS supplier_code,
              {supplier_select} AS supplier_name,
              vb.payment_amount,
              vb.detail_row_count,
              vb.settlement_count,
              vb.department_count,
              vb.department_codes,
              vb.department_names,
              vb.group_count,
              h.sphpaydate AS payment_date,
              h.inputor,
              h.inputdate,
              h.auditor,
              h.auditdate,
              CASE WHEN TRIM(h.sphflag::text) = 'Y' THEN h.auditdate ELSE h.inputdate END AS status_date
            {from_sql}{list_tail}
            ORDER BY
              CASE WHEN TRIM(h.sphflag::text) = 'M' THEN 0 ELSE 1 END,
              CASE WHEN TRIM(h.sphflag::text) = 'Y' THEN h.auditdate ELSE h.inputdate END DESC NULLS LAST,
              h.sphbillno DESC
            LIMIT :joint_payment_limit OFFSET :joint_payment_offset
            """
        ),
        page_params,
    ).fetchall()

    summary = {
        "total_generated_count": int(getattr(summary_row, "total_generated_count", 0) or 0),
        "total_generated_supplier_count": int(getattr(summary_row, "total_generated_supplier_count", 0) or 0),
        "total_generated_amount": float(getattr(summary_row, "total_generated_amount", 0) or 0),
        "supplier_confirmation_available": confirmation_available,
        "supplier_unreported_count": int(getattr(summary_row, "supplier_unreported_count", 0) or 0) if confirmation_available else None,
        "supplier_unreported_supplier_count": int(getattr(summary_row, "supplier_unreported_supplier_count", 0) or 0) if confirmation_available else None,
        "supplier_unreported_amount": float(getattr(summary_row, "supplier_unreported_amount", 0) or 0) if confirmation_available else None,
        "supplier_confirmed_count": int(getattr(summary_row, "supplier_confirmed_count", 0) or 0) if confirmation_available else None,
        "supplier_confirmed_supplier_count": int(getattr(summary_row, "supplier_confirmed_supplier_count", 0) or 0) if confirmation_available else None,
        "supplier_confirmed_amount": float(getattr(summary_row, "supplier_confirmed_amount", 0) or 0) if confirmation_available else None,
        "generated_count": int(getattr(summary_row, "generated_count", 0) or 0),
        "generated_supplier_count": int(getattr(summary_row, "generated_supplier_count", 0) or 0),
        "generated_amount": float(getattr(summary_row, "generated_amount", 0) or 0),
        "audited_count": int(getattr(summary_row, "audited_count", 0) or 0),
        "audited_supplier_count": int(getattr(summary_row, "audited_supplier_count", 0) or 0),
        "audited_amount": float(getattr(summary_row, "audited_amount", 0) or 0),
        "current_financial_month_audited_amount": float(
            getattr(financial_month_amount_row, "audited_amount", 0) or 0
        ),
        "current_financial_month_start": financial_month_start.isoformat(),
        "current_financial_month_end": financial_month_end.isoformat(),
        "latest_status_date": None,
    }
    latest = getattr(summary_row, "latest_status_date", None)
    if latest is not None:
        summary["latest_status_date"] = latest.isoformat() if hasattr(latest, "isoformat") else str(latest)

    return {
        "summary": summary,
        "items": [_row_dict(row) for row in rows],
        "total": total,
        "page": filters.page,
        "page_size": filters.page_size,
    }


def query_joint_payment_department_options(
    db: Session,
    scope: BusinessScope,
) -> list[dict[str, Any]]:
    """返回当前数据权限下存在联营付款单的部门选项。"""
    if (
        not _table_exists(db, "suppayhead")
        or not _table_exists(db, "paybatch")
        or not _table_exists(db, "manaframe")
    ):
        return []
    batch_where, params = _visible_batch_where(JointPaymentFilters(), scope)
    rows = db.execute(
        text(
            f"""
            SELECT DISTINCT
              TRIM(dept.mfcode::text) AS department_code,
              TRIM(dept.mfcname::text) AS department_name
            FROM paybatch pb
            INNER JOIN suppayhead h
              ON TRIM(h.sphbillno) = TRIM(pb.pbpaybillno)
            LEFT JOIN manaframe group_mf
              ON TRIM(group_mf.mfcode) = TRIM(pb.pbmfid::text)
            LEFT JOIN manaframe dept
              ON TRIM(UPPER(dept.mfcode)) = TRIM(UPPER(group_mf.mfpcode))
            WHERE {batch_where}
              AND TRIM(COALESCE(h.sphflag::text, '')) IN ('M', 'Y')
              AND NULLIF(TRIM(dept.mfcode::text), '') IS NOT NULL
            ORDER BY TRIM(dept.mfcode::text)
            """
        ),
        params,
    ).fetchall()
    return [_row_dict(row) for row in rows]


def query_mobile_supplier_payment_options(
    db: Session,
    scope: BusinessScope,
) -> dict[str, list[dict[str, Any]]]:
    """门店及部门选项使用与付款单金额一致的联营批次权限范围。"""
    if not all(_table_exists(db, table) for table in ("suppayhead", "paybatch", "manaframe")):
        return {"stores": [], "departments": []}
    batch_where, params = _visible_batch_where(JointPaymentFilters(include_banshan=True), scope, head_alias="h")
    has_stores = _table_exists(db, "stores")
    store_join = "LEFT JOIN stores st ON TRIM(st.store_code) = TRIM(h.sphmkt)" if has_stores else ""
    store_name = "NULLIF(TRIM(st.store_name), '')" if has_stores else "NULL::text"
    rows = db.execute(
        text(f"""
            SELECT DISTINCT
              TRIM(h.sphmkt::text) AS store_code,
              COALESCE({store_name}, TRIM(h.sphmkt::text)) AS store_name,
              TRIM(dept.mfcode::text) AS department_code,
              TRIM(dept.mfcname::text) AS department_name
            FROM paybatch pb
            INNER JOIN suppayhead h ON TRIM(h.sphbillno) = TRIM(pb.pbpaybillno)
            LEFT JOIN manaframe group_mf ON TRIM(group_mf.mfcode) = TRIM(pb.pbmfid::text)
            LEFT JOIN manaframe dept
              ON TRIM(UPPER(dept.mfcode)) = TRIM(UPPER(group_mf.mfpcode))
            {store_join}
            WHERE {batch_where}
              AND TRIM(COALESCE(h.sphflag::text, '')) IN ('M', 'Y')
            ORDER BY store_code, department_code
        """),
        params,
    ).fetchall()
    stores: dict[str, dict[str, Any]] = {}
    departments = []
    for row in rows:
        item = _row_dict(row)
        store_code = item.get("store_code") or ""
        if store_code:
            stores.setdefault(store_code, {
                "store_code": store_code,
                "store_name": item.get("store_name") or store_code,
            })
        if item.get("department_code"):
            departments.append({
                "store_code": store_code,
                "department_code": item["department_code"],
                "department_name": item.get("department_name") or item["department_code"],
            })
    return {"stores": list(stores.values()), "departments": departments}


def get_joint_payment_detail(
    db: Session,
    payment_bill_no: str,
    scope: BusinessScope,
    department_code: str | None = None,
    include_banshan: bool = False,
) -> dict[str, Any] | None:
    if (
        not _table_exists(db, "suppayhead")
        or not _table_exists(db, "paybatch")
        or not _table_exists(db, "manaframe")
    ):
        return None
    bill = (payment_bill_no or "").strip()
    if not bill:
        return None

    filters = JointPaymentFilters(department_code=department_code, include_banshan=include_banshan)
    batch_where, params = _visible_batch_where(filters, scope)
    params["joint_payment_bill_no"] = bill
    has_supplier = _table_exists(db, "supplierbase")
    supplier_join = (
        "LEFT JOIN supplierbase sb ON TRIM(sb.sbid) = TRIM(h.sphsupid)"
        if has_supplier
        else ""
    )
    supplier_select = "sb.sbcname" if has_supplier else "NULL::text"

    head = db.execute(
        text(
            f"""
            WITH visible_batch AS (
              SELECT
                TRIM(pb.pbpaybillno) AS payment_bill_no,
                SUM(COALESCE(pb.pbsf, 0)) AS payment_amount,
                COUNT(*) AS detail_row_count,
                COUNT(DISTINCT NULLIF(TRIM(pb.pbjsno), '')) AS settlement_count,
                COUNT(DISTINCT NULLIF(TRIM(dept.mfcode::text), '')) AS department_count,
                COUNT(DISTINCT NULLIF(TRIM(pb.pbmfid::text), '')) AS group_count,
                STRING_AGG(DISTINCT TRIM(dept.mfcode::text), ', ' ORDER BY TRIM(dept.mfcode::text))
                  FILTER (WHERE NULLIF(TRIM(dept.mfcode::text), '') IS NOT NULL) AS department_codes,
                STRING_AGG(DISTINCT TRIM(dept.mfcname::text), ', ' ORDER BY TRIM(dept.mfcname::text))
                  FILTER (WHERE NULLIF(TRIM(dept.mfcname::text), '') IS NOT NULL) AS department_names
              FROM paybatch pb
              LEFT JOIN manaframe group_mf
                ON TRIM(group_mf.mfcode) = TRIM(pb.pbmfid::text)
              LEFT JOIN manaframe dept
                ON TRIM(UPPER(dept.mfcode)) = TRIM(UPPER(group_mf.mfpcode))
              WHERE {batch_where}
                AND TRIM(pb.pbpaybillno) = :joint_payment_bill_no
              GROUP BY TRIM(pb.pbpaybillno)
            )
            SELECT
              h.sphbillno AS payment_bill_no,
              h.sphflag AS status,
              CASE TRIM(h.sphflag::text)
                WHEN 'M' THEN '生成（待确认）'
                WHEN 'Y' THEN '已审核（财务收入已确认）'
                ELSE TRIM(h.sphflag::text)
              END AS status_label,
              h.sphmkt AS market_code,
              h.sphsupid AS supplier_code,
              {supplier_select} AS supplier_name,
              vb.payment_amount,
              vb.detail_row_count,
              vb.settlement_count,
              vb.department_count,
              vb.group_count,
              vb.department_codes,
              vb.department_names,
              h.sphpaydate AS payment_date,
              h.inputor,
              h.inputdate,
              h.auditor,
              h.auditdate,
              CASE WHEN TRIM(h.sphflag::text) = 'Y' THEN h.auditdate ELSE h.inputdate END AS status_date,
              h.sphmemo AS memo
            FROM visible_batch vb
            INNER JOIN suppayhead h ON TRIM(h.sphbillno) = vb.payment_bill_no
            {supplier_join}
            LIMIT 1
            """
        ),
        params,
    ).fetchone()
    if head is None:
        return None

    rows = db.execute(
        text(
            f"""
            SELECT
              pb.pbseq AS row_no,
              pb.pbjsno AS settlement_bill_no,
              pb.pbbillno AS source_bill_no,
              dept.mfcode AS department_code,
              dept.mfcname AS department_name,
              pb.pbmfid AS group_code,
              group_mf.mfcname AS group_name,
              pb.pbcontno AS contract_no,
              pb.pbjssdate AS period_start,
              pb.pbjsedate AS period_end,
              pb.pbxssr AS sales_revenue,
              pb.pbkp AS invoiced_amount,
              pb.pbfy1 AS fee_amount_1,
              pb.pbfy2 AS fee_amount_2,
              pb.pbyf AS payable_amount,
              pb.pbsf AS payment_amount,
              pb.pbpaystatus AS payment_status
            FROM paybatch pb
            LEFT JOIN manaframe group_mf
              ON TRIM(group_mf.mfcode) = TRIM(pb.pbmfid::text)
            LEFT JOIN manaframe dept
              ON TRIM(UPPER(dept.mfcode)) = TRIM(UPPER(group_mf.mfpcode))
            WHERE {batch_where}
              AND TRIM(pb.pbpaybillno) = :joint_payment_bill_no
            ORDER BY pb.pbseq ASC NULLS LAST, pb.pbjsno, pb.pbbillno
            """
        ),
        params,
    ).fetchall()
    lines = [_row_dict(row) for row in rows]

    charges: list[dict[str, Any]] = []
    if _table_exists(db, "supsetcharge"):
        from services.erp_settlement_charge_display import query_supsetcharge_enriched

        charge_scope_where, charge_scope_params = _visible_charge_where(scope)
        if (department_code or "").strip():
            # 收费明细也限制到所选部门的可见柜组，保留原有允许/排除权限。
            group_where, group_params = _sql_expr_in_binds(
                "TRIM(UPPER(COALESCE(aa.sscmfid::text, '')))",
                sorted({str(line["group_code"]).strip().upper() for line in lines if line.get("group_code")}),
                "joint_payment_selected_department_group",
            )
            charge_scope_where = f"({charge_scope_where}) AND ({group_where})"
            charge_scope_params.update(group_params)
        charges = query_supsetcharge_enriched(
            db,
            where_sql=(
                "(TRIM(COALESCE(aa.sscpaybillno::text, '')) = :joint_payment_charge_bill_no "
                "OR EXISTS ("
                "SELECT 1 FROM paybatch charge_pb "
                "WHERE TRIM(charge_pb.pbpaybillno) = :joint_payment_charge_bill_no "
                "AND TRIM(COALESCE(charge_pb.pbjsno::text, '')) = TRIM(COALESCE(aa.sscjsno::text, '')) "
                "AND TRIM(UPPER(COALESCE(charge_pb.pbmfid::text, ''))) = TRIM(UPPER(COALESCE(aa.sscmfid::text, ''))) "
                "AND TRIM(UPPER(COALESCE(charge_pb.pbcontno::text, ''))) = TRIM(UPPER(COALESCE(aa.ssccontno::text, ''))) "
                f"AND {_payment_business_where(include_banshan, 'charge_pb')}"
                ")) "
                f"AND {charge_scope_where}"
            ),
            params={
                **charge_scope_params,
                "joint_payment_charge_bill_no": bill,
            },
            order_by="aa.sscrowno ASC NULLS LAST, aa.sscbillno ASC",
        )

    ticket_reduction_amount = sum(float(line.get("fee_amount_1") or 0) for line in lines)
    expense_amount = sum(float(line.get("fee_amount_2") or 0) for line in lines)
    ticket_reduction_detail_amount = sum(
        float(charge.get("sscmoney") or 0)
        for charge in charges
        if str(charge.get("person1") or "").strip().upper() == "Y"
    )
    expense_detail_amount = sum(
        float(charge.get("sscmoney") or 0)
        for charge in charges
        if str(charge.get("person1") or "N").strip().upper() != "Y"
    )
    head_dict = _row_dict(head)
    head_dict.update(
        {
            "sales_revenue": sum(float(line.get("sales_revenue") or 0) for line in lines),
            "invoiced_amount": sum(float(line.get("invoiced_amount") or 0) for line in lines),
            "ticket_reduction_amount": ticket_reduction_amount,
            "expense_amount": expense_amount,
            "fee_amount": ticket_reduction_amount + expense_amount,
            "ticket_reduction_detail_amount": ticket_reduction_detail_amount,
            "expense_detail_amount": expense_detail_amount,
            "ticket_reduction_detail_matches": abs(
                ticket_reduction_amount - ticket_reduction_detail_amount
            ) <= 0.01,
            "expense_detail_matches": abs(expense_amount - expense_detail_amount) <= 0.01,
        }
    )

    return {"head": head_dict, "lines": lines, "charges": charges}
