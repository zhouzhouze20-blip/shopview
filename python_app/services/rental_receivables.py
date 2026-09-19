"""Rental receivables queried from the local headquarters ODS snapshot."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.orm import Session

from .department_display_order import department_display_sort_key


MAX_PAGE_SIZE = 100
MAX_EXPORT_DETAIL_ROWS = 50_000
LOCAL_ODS_SOURCE = {
    "id": 4,
    "name": "本地 ODS（PAPI 总部库同步）",
    "type": "postgres",
}
MOBILE_STORE_DISPLAY_ORDER = {"601": 0, "602": 1, "603": 2, "604": 3}

# Fuji's receivable/payable export labels these settlement lines by the complete
# composite payment code.  The final two digits alone are not a stable payment
# dictionary key (for example, 00-0330 and 00-2030 are different channels), so
# keep the verified composite-code labels ahead of the legacy PAYMODE fallback.
COMPOSITE_PAYMENT_ITEM_NAMES = {
    "00-01": "现金",
    "00-0301": "银联信用卡",
    "00-0303": "银联聚合支付",
    "00-0307": "银联聚合支付（手工）",
    "00-0324": "0324数字人民币(手工)",
    "00-0326": "0326数字人民币(优惠)",
    "00-0330": "0330 瑞祥卡实体卡",
    "00-0331": "0331 旅通卡实体卡",
    "00-0400": "储值卡",
    "00-0500": "0500促销券",
    "00-0511": "内转单",
    "00-2030": "2030建行数币（优惠）",
    "00-2037": "2037建行数币（手工）",
    "00-9999": "券返款",
}


class OdsUnavailableError(RuntimeError):
    """The local headquarters ODS tables are missing or not initialized."""


class ReceivableNotFoundError(LookupError):
    """The settlement bill is missing or outside the current business scope."""


@dataclass(frozen=True)
class ReceivableFilters:
    settle_from: date
    settle_to: date
    page: int = 1
    page_size: int = 50
    mkt: str | None = None
    department_code: str | None = None
    group_code: str | None = None
    group_prefix: str | None = None
    keyword: str | None = None


@dataclass(frozen=True)
class BusinessScopeFilter:
    all_access: bool = False
    allow: dict[str, frozenset[str]] = field(default_factory=dict)
    deny: dict[str, frozenset[str]] = field(default_factory=dict)


def _clean_code(value: str | None, *, max_length: int = 100) -> str | None:
    cleaned = (value or "").strip().upper()
    if not cleaned:
        return None
    if len(cleaned) > max_length or not re.fullmatch(r"[A-Z0-9_.-]+", cleaned):
        raise ValueError("编码只能包含字母、数字、点、下划线或短横线")
    return cleaned


def _scope_condition(
    expressions: list[str],
    values: frozenset[str],
    params: dict[str, Any],
    prefix: str,
) -> str | None:
    cleaned = sorted(
        {
            str(value).strip().upper()
            for value in values
            if str(value).strip() and len(str(value).strip()) <= 100
        }
    )
    if not cleaned:
        return None
    placeholders: list[str] = []
    for index, value in enumerate(cleaned):
        key = f"{prefix}_{index}"
        params[key] = value
        placeholders.append(f":{key}")
    in_sql = f"IN ({', '.join(placeholders)})"
    return "(" + " OR ".join(f"{expr} {in_sql}" for expr in expressions) + ")"


def _scope_conditions(scope: BusinessScopeFilter, params: dict[str, Any]) -> list[str]:
    if "__all__" in scope.deny:
        return ["1 = 0"]

    expressions: dict[str, list[str]] = {
        "store": [
            "TRIM(UPPER(sh.sshmkt))",
            "TRIM(UPPER(COALESCE(st.store_id::text, '')))",
        ],
        "department": [
            "TRIM(UPPER(COALESCE(sh.department_code, '')))",
            "TRIM(UPPER(COALESCE(sh.department_name, '')))",
        ],
        "group": ["TRIM(UPPER(COALESCE(sh.sshmfid, '')))"],
        "supplier": ["TRIM(UPPER(sh.sshsupid))"],
    }
    conditions: list[str] = []

    for dimension, dimension_expressions in expressions.items():
        denied = _scope_condition(
            dimension_expressions,
            scope.deny.get(dimension, frozenset()),
            params,
            f"deny_{dimension}",
        )
        if denied:
            conditions.append(f"NOT ({denied})")

    if scope.all_access:
        return conditions

    allow_parts = [
        condition
        for dimension, dimension_expressions in expressions.items()
        if (
            condition := _scope_condition(
                dimension_expressions,
                scope.allow.get(dimension, frozenset()),
                params,
                f"allow_{dimension}",
            )
        )
    ]
    conditions.append("(" + " OR ".join(allow_parts) + ")" if allow_parts else "1 = 0")
    return conditions


def build_receivables_query(
    filters: ReceivableFilters,
    scope: BusinessScopeFilter,
) -> tuple[str, dict[str, Any]]:
    """Build a bounded PostgreSQL query and bound parameters for the local ODS."""
    if filters.settle_from > filters.settle_to:
        raise ValueError("结算截止日起不能晚于止日期")
    if filters.page < 1:
        raise ValueError("页码必须大于等于 1")
    if not 1 <= filters.page_size <= MAX_PAGE_SIZE:
        raise ValueError(f"每页条数必须为 1-{MAX_PAGE_SIZE}")

    mkt = _clean_code(filters.mkt, max_length=20)
    department_code = _clean_code(filters.department_code, max_length=20)
    group_code = _clean_code(filters.group_code, max_length=40)
    group_prefix = _clean_code(filters.group_prefix, max_length=40)
    keyword = (filters.keyword or "").strip()
    if len(keyword) > 80:
        raise ValueError("关键词不能超过 80 个字符")

    params: dict[str, Any] = {
        "settle_from": filters.settle_from,
        "settle_to_exclusive": filters.settle_to + timedelta(days=1),
        "row_start": (filters.page - 1) * filters.page_size + 1,
        "row_end": filters.page * filters.page_size,
    }
    where = [
        "sh.sshwmid = '5'",
        "sh.sshdjlb = 'Z'",
        "sh.sshflag = 'Y'",
        "sh.sshthisdate >= :settle_from",
        "sh.sshthisdate < :settle_to_exclusive",
        *_scope_conditions(scope, params),
    ]
    if mkt:
        params["mkt"] = mkt
        where.append("TRIM(UPPER(sh.sshmkt)) = :mkt")
    if department_code:
        params["department_code"] = department_code
        where.append("TRIM(UPPER(sh.department_code)) = :department_code")
    if group_code:
        params["group_code"] = group_code
        where.append("TRIM(UPPER(sh.sshmfid)) = :group_code")
    if group_prefix:
        params["group_prefix"] = group_prefix + "%"
        where.append("TRIM(UPPER(sh.sshmfid)) LIKE :group_prefix")
    if keyword:
        params["keyword"] = (
            "%" + keyword.upper().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        )
        where.append(
            "(UPPER(sh.sshbillno) LIKE :keyword ESCAPE '\\' "
            "OR UPPER(sh.sshsupid) LIKE :keyword ESCAPE '\\' "
            "OR UPPER(COALESCE(sh.sshcontno, '')) LIKE :keyword ESCAPE '\\' "
            "OR UPPER(COALESCE(sh.sshmfid, '')) LIKE :keyword ESCAPE '\\' "
            "OR UPPER(COALESCE(sh.department_code, '')) LIKE :keyword ESCAPE '\\' "
            "OR UPPER(COALESCE(sh.department_name, '')) LIKE :keyword ESCAPE '\\' "
            "OR UPPER(COALESCE(sh.supplier_name, '')) LIKE :keyword ESCAPE '\\' "
            "OR UPPER(COALESCE(sh.group_name, '')) LIKE :keyword ESCAPE '\\')"
        )

    sql = f"""
WITH base AS (
  SELECT sh.sshbillno,
         sh.sshsupid,
         sh.supplier_name,
         sh.sshmkt,
         st.store_name,
         sh.sshmfid,
         sh.group_name,
         sh.department_code,
         sh.department_name,
         sh.sshcontno,
         sh.sshlastdate AS settle_from,
         sh.sshthisdate AS settle_to,
         ROUND(SUM(COALESCE(t.sdtamount, 0)), 2) AS original_amount,
         ROUND(ABS(SUM(CASE
           WHEN COALESCE(TRIM(t.sdtitemcode), '') NOT LIKE '00-%'
           THEN COALESCE(t.sdtamount, 0) ELSE 0 END)), 2) AS original_receivable_amount,
         ROUND(SUM(CASE
           WHEN COALESCE(TRIM(t.sdtitemcode), '') NOT LIKE '00-%'
           THEN COALESCE(t.sdtye, 0) ELSE 0 END), 2) AS receivable_amount,
         ROUND(SUM(CASE
           WHEN COALESCE(TRIM(t.sdtitemcode), '') LIKE '00-%'
            AND COALESCE(t.sdtye, 0) < 0
           THEN -COALESCE(t.sdtye, 0) ELSE 0 END), 2) AS sales_refund_amount
    FROM ods.hq_supsettlehead sh
    JOIN ods.hq_supsettledettot t ON t.sdtbillno = sh.sshbillno
    LEFT JOIN stores st ON TRIM(st.store_code) = TRIM(sh.sshmkt)
   WHERE {' AND '.join(where)}
   GROUP BY sh.sshbillno, sh.sshsupid, sh.supplier_name, sh.sshmkt, st.store_name,
            sh.sshmfid, sh.group_name, sh.department_code, sh.department_name,
            sh.sshcontno, sh.sshlastdate, sh.sshthisdate
  HAVING ABS(SUM(CASE
           WHEN COALESCE(TRIM(t.sdtitemcode), '') NOT LIKE '00-%'
           THEN COALESCE(t.sdtye, 0) ELSE 0 END)) > 0.005
), scored AS (
  SELECT base.*,
         CURRENT_DATE - settle_to::date AS aging_days,
         CASE
           WHEN ABS(receivable_amount) + 0.005 < original_receivable_amount THEN 'PARTIAL'
           WHEN ABS(receivable_amount) > original_receivable_amount + 0.005 THEN 'EXCEEDS_ORIGINAL'
           ELSE 'FULL'
         END AS outstanding_status
    FROM base
), ranked AS (
  SELECT scored.*,
         ROW_NUMBER() OVER (ORDER BY settle_to DESC, sshbillno DESC) AS rn,
         COUNT(*) OVER () AS total_count,
         ROUND(SUM(receivable_amount) OVER (), 2) AS total_receivable_amount,
         ROUND(SUM(original_receivable_amount) OVER (), 2) AS total_original_amount,
         ROUND(SUM(sales_refund_amount) OVER (), 2) AS total_sales_refund_amount,
         SUM((outstanding_status = 'PARTIAL')::INTEGER) OVER () AS partial_count,
         SUM((outstanding_status = 'EXCEEDS_ORIGINAL')::INTEGER) OVER () AS anomaly_count,
         ROUND(SUM(CASE WHEN aging_days > 90 THEN receivable_amount ELSE 0 END) OVER (), 2) AS over_90_amount
    FROM scored
)
SELECT sshbillno, sshsupid, supplier_name, sshmkt, store_name, sshmfid, group_name,
       department_code, department_name, sshcontno,
       settle_from::date AS settle_from, settle_to::date AS settle_to,
       original_amount, original_receivable_amount, receivable_amount, sales_refund_amount,
       aging_days, outstanding_status, rn, total_count, total_receivable_amount,
       total_original_amount, total_sales_refund_amount,
       partial_count, anomaly_count, over_90_amount
  FROM ranked
 WHERE rn BETWEEN :row_start AND :row_end
 ORDER BY rn
""".strip()
    return sql, params


def build_receivables_sql(filters: ReceivableFilters, scope: BusinessScopeFilter) -> str:
    """Compatibility helper used by tests and diagnostics."""
    return build_receivables_query(filters, scope)[0]


def build_receivable_expense_export_query(
    filters: ReceivableFilters,
    scope: BusinessScopeFilter,
) -> tuple[str, dict[str, Any]]:
    """Build the permission-scoped nonzero expense-line export query."""
    if filters.settle_from > filters.settle_to:
        raise ValueError("结算截止日起不能晚于止日期")

    mkt = _clean_code(filters.mkt, max_length=20)
    department_code = _clean_code(filters.department_code, max_length=20)
    group_code = _clean_code(filters.group_code, max_length=40)
    group_prefix = _clean_code(filters.group_prefix, max_length=40)
    keyword = (filters.keyword or "").strip()
    if len(keyword) > 80:
        raise ValueError("关键词不能超过 80 个字符")

    params: dict[str, Any] = {
        "settle_from": filters.settle_from,
        "settle_to_exclusive": filters.settle_to + timedelta(days=1),
        "export_limit_plus_one": MAX_EXPORT_DETAIL_ROWS + 1,
    }
    where = [
        "sh.sshwmid = '5'",
        "sh.sshdjlb = 'Z'",
        "sh.sshflag = 'Y'",
        "sh.sshthisdate >= :settle_from",
        "sh.sshthisdate < :settle_to_exclusive",
        *_scope_conditions(scope, params),
    ]
    if mkt:
        params["mkt"] = mkt
        where.append("TRIM(UPPER(sh.sshmkt)) = :mkt")
    if department_code:
        params["department_code"] = department_code
        where.append("TRIM(UPPER(sh.department_code)) = :department_code")
    if group_code:
        params["group_code"] = group_code
        where.append("TRIM(UPPER(sh.sshmfid)) = :group_code")
    if group_prefix:
        params["group_prefix"] = group_prefix + "%"
        where.append("TRIM(UPPER(sh.sshmfid)) LIKE :group_prefix")
    if keyword:
        params["keyword"] = (
            "%" + keyword.upper().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        )
        where.append(
            "(UPPER(sh.sshbillno) LIKE :keyword ESCAPE '\\' "
            "OR UPPER(sh.sshsupid) LIKE :keyword ESCAPE '\\' "
            "OR UPPER(COALESCE(sh.sshcontno, '')) LIKE :keyword ESCAPE '\\' "
            "OR UPPER(COALESCE(sh.sshmfid, '')) LIKE :keyword ESCAPE '\\' "
            "OR UPPER(COALESCE(sh.department_code, '')) LIKE :keyword ESCAPE '\\' "
            "OR UPPER(COALESCE(sh.department_name, '')) LIKE :keyword ESCAPE '\\' "
            "OR UPPER(COALESCE(sh.supplier_name, '')) LIKE :keyword ESCAPE '\\' "
            "OR UPPER(COALESCE(sh.group_name, '')) LIKE :keyword ESCAPE '\\')"
        )

    sql = f"""
WITH eligible_bills AS (
  SELECT sh.sshbillno,
         sh.sshsupid,
         sh.supplier_name,
         sh.sshmkt,
         st.store_name,
         sh.department_code,
         sh.department_name,
         sh.sshmfid,
         sh.group_name,
         sh.sshcontno,
         sh.sshlastdate,
         sh.sshthisdate,
         ROUND(SUM(CASE
           WHEN COALESCE(TRIM(summary_line.sdtitemcode), '') NOT LIKE '00-%'
           THEN COALESCE(summary_line.sdtye, 0) ELSE 0 END), 2) AS bill_receivable_amount
    FROM ods.hq_supsettlehead sh
    JOIN ods.hq_supsettledettot summary_line ON summary_line.sdtbillno = sh.sshbillno
    LEFT JOIN stores st ON TRIM(st.store_code) = TRIM(sh.sshmkt)
   WHERE {' AND '.join(where)}
   GROUP BY sh.sshbillno, sh.sshsupid, sh.supplier_name, sh.sshmkt, st.store_name,
            sh.department_code, sh.department_name, sh.sshmfid, sh.group_name,
            sh.sshcontno, sh.sshlastdate, sh.sshthisdate
  HAVING ABS(SUM(CASE
           WHEN COALESCE(TRIM(summary_line.sdtitemcode), '') NOT LIKE '00-%'
           THEN COALESCE(summary_line.sdtye, 0) ELSE 0 END)) > 0.005
)
SELECT bill.*,
       detail.sdtrowno,
       detail.sdtflag,
       detail.sdtitemcode,
       detail.item_name_raw,
       detail.payment_name_raw,
       detail.sdtstartdate,
       detail.sdtenddate,
       detail.sdtamount,
       detail.sdtckamount,
       detail.sdtyfamount,
       detail.sdtdkamount,
       detail.sdtye,
       detail.sdtadjamount,
       detail.sdtxssr,
       detail.sdthsy,
       detail.sdtcalcplace,
       detail.sdtmfjzmj,
       detail.sdtmfzjmj,
       detail.sdttaxrate,
       detail.sdtnotaxamount,
       detail.sdtmemo,
       detail.sdtisadv
  FROM eligible_bills bill
  JOIN ods.hq_supsettledettot detail ON detail.sdtbillno = bill.sshbillno
 WHERE ABS(COALESCE(detail.sdtye, 0)) > 0.005
 ORDER BY bill.sshthisdate DESC, bill.sshbillno DESC, detail.sdtrowno
 LIMIT :export_limit_plus_one
""".strip()
    return sql, params


def build_mobile_drilldown_query(
    *,
    level: str,
    settle_from: date,
    settle_to: date,
    scope: BusinessScopeFilter,
    mkt: str | None = None,
    department_code: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Aggregate one permission-scoped mobile hierarchy level from bill balances."""
    if settle_from > settle_to:
        raise ValueError("结算截止日起不能晚于止日期")
    if level not in {"store", "department", "group"}:
        raise ValueError("钻取层级只能是门店、部门或柜组")

    clean_mkt = _clean_code(mkt, max_length=20)
    clean_department = _clean_code(department_code, max_length=20)
    if level in {"department", "group"} and not clean_mkt:
        raise ValueError("进入部门或柜组前必须选择门店")
    if level == "group" and not clean_department:
        raise ValueError("进入柜组前必须选择部门")

    params: dict[str, Any] = {
        "settle_from": settle_from,
        "settle_to_exclusive": settle_to + timedelta(days=1),
    }
    where = [
        "sh.sshwmid = '5'",
        "sh.sshdjlb = 'Z'",
        "sh.sshflag = 'Y'",
        "sh.sshthisdate >= :settle_from",
        "sh.sshthisdate < :settle_to_exclusive",
        *_scope_conditions(scope, params),
    ]
    if clean_mkt:
        params["mkt"] = clean_mkt
        where.append("TRIM(UPPER(sh.sshmkt)) = :mkt")
    if clean_department:
        params["department_code"] = clean_department
        where.append("TRIM(UPPER(sh.department_code)) = :department_code")

    dimensions = {
        "store": {
            "code": "COALESCE(NULLIF(TRIM(sshmkt), ''), '未编码门店')",
            "name": "COALESCE(NULLIF(TRIM(store_name), ''), NULLIF(TRIM(sshmkt), ''), '未命名门店')",
            "next_count": "COUNT(DISTINCT COALESCE(NULLIF(TRIM(department_code), ''), NULLIF(TRIM(department_name), '')))",
        },
        "department": {
            "code": "COALESCE(NULLIF(TRIM(department_code), ''), NULLIF(TRIM(department_name), ''), '未编码部门')",
            "name": "COALESCE(NULLIF(TRIM(department_name), ''), NULLIF(TRIM(department_code), ''), '未命名部门')",
            "next_count": "COUNT(DISTINCT COALESCE(NULLIF(TRIM(sshmfid), ''), NULLIF(TRIM(group_name), '')))",
        },
        "group": {
            "code": "COALESCE(NULLIF(TRIM(sshmfid), ''), NULLIF(TRIM(group_name), ''), '未编码柜组')",
            "name": "COALESCE(NULLIF(TRIM(group_name), ''), NULLIF(TRIM(sshmfid), ''), '未命名柜组')",
            "next_count": "COUNT(DISTINCT sshsupid)",
        },
    }
    dimension = dimensions[level]
    code_expression = dimension["code"]
    name_expression = dimension["name"]

    sql = f"""
WITH bill_base AS (
  SELECT sh.sshbillno,
         sh.sshsupid,
         sh.sshmkt,
         st.store_name,
         sh.department_code,
         sh.department_name,
         sh.sshmfid,
         sh.group_name,
         sh.sshthisdate AS settle_to,
         ROUND(ABS(SUM(CASE
           WHEN COALESCE(TRIM(t.sdtitemcode), '') NOT LIKE '00-%'
           THEN COALESCE(t.sdtamount, 0) ELSE 0 END)), 2) AS original_receivable_amount,
         ROUND(SUM(CASE
           WHEN COALESCE(TRIM(t.sdtitemcode), '') NOT LIKE '00-%'
           THEN COALESCE(t.sdtye, 0) ELSE 0 END), 2) AS receivable_amount,
         ROUND(SUM(CASE
           WHEN COALESCE(TRIM(t.sdtitemcode), '') LIKE '00-%'
            AND COALESCE(t.sdtye, 0) < 0
           THEN -COALESCE(t.sdtye, 0) ELSE 0 END), 2) AS sales_refund_amount
    FROM ods.hq_supsettlehead sh
    JOIN ods.hq_supsettledettot t ON t.sdtbillno = sh.sshbillno
    LEFT JOIN stores st ON TRIM(st.store_code) = TRIM(sh.sshmkt)
   WHERE {' AND '.join(where)}
   GROUP BY sh.sshbillno, sh.sshsupid, sh.sshmkt, st.store_name,
            sh.department_code, sh.department_name, sh.sshmfid, sh.group_name,
            sh.sshthisdate
  HAVING ABS(SUM(CASE
           WHEN COALESCE(TRIM(t.sdtitemcode), '') NOT LIKE '00-%'
           THEN COALESCE(t.sdtye, 0) ELSE 0 END)) > 0.005
), scored AS (
  SELECT bill_base.*,
         CURRENT_DATE - settle_to::date AS aging_days,
         CASE
           WHEN ABS(receivable_amount) + 0.005 < original_receivable_amount THEN 'PARTIAL'
           WHEN ABS(receivable_amount) > original_receivable_amount + 0.005 THEN 'EXCEEDS_ORIGINAL'
           ELSE 'FULL'
         END AS outstanding_status
    FROM bill_base
)
SELECT {code_expression} AS code,
       {name_expression} AS name,
       COUNT(*) AS bill_count,
       {dimension['next_count']} AS next_count,
       ROUND(SUM(receivable_amount), 2) AS receivable_amount,
       ROUND(SUM(original_receivable_amount), 2) AS original_receivable_amount,
       ROUND(SUM(sales_refund_amount), 2) AS sales_refund_amount,
       SUM((outstanding_status = 'PARTIAL')::INTEGER) AS partial_count,
       SUM((outstanding_status = 'EXCEEDS_ORIGINAL')::INTEGER) AS anomaly_count,
       ROUND(SUM(CASE WHEN aging_days > 90 THEN receivable_amount ELSE 0 END), 2) AS over_90_amount,
       MAX(settle_to)::date AS latest_settle_to
  FROM scored
 GROUP BY {code_expression}, {name_expression}
 ORDER BY ABS(SUM(receivable_amount)) DESC, name
""".strip()
    return sql, params


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _date_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    return str(value)[:10]


def _sort_mobile_drilldown_items(level: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if level == "store":
        return sorted(
            items,
            key=lambda row: (
                MOBILE_STORE_DISPLAY_ORDER.get(str(row.get("code") or ""), 999),
                str(row.get("name") or ""),
            ),
        )
    if level == "department":
        return sorted(
            items,
            key=lambda row: department_display_sort_key(
                {
                    "department_code": row.get("code"),
                    "department_name": row.get("name"),
                }
            ),
        )
    return items


def _decode_legacy_text(value: Any) -> str | None:
    """Decode Chinese stored as GBK bytes in the legacy ISO-8859-1 Oracle DB."""
    if value is None:
        return None
    text_value = str(value).strip()
    if not text_value:
        return None
    try:
        return text_value.encode("latin-1").decode("gb18030")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text_value


def _detail_item_name(item_code: Any, raw_name: Any, payment_name_raw: Any = None) -> str:
    code = str(item_code or "").strip()
    decoded = _decode_legacy_text(raw_name)
    if decoded:
        return decoded
    if code.startswith("00-"):
        verified_name = COMPOSITE_PAYMENT_ITEM_NAMES.get(code)
        if verified_name:
            return verified_name
        payment_name = _decode_legacy_text(payment_name_raw)
        if payment_name:
            return f"支付项目（{payment_name}，编码 {code}）"
        return f"支付项目（{code}）"
    if code == "SALE":
        return "销售额参考"
    return f"结算项目（{code}）" if code else "未命名结算项目"


def query_rental_receivable_detail(
    db: Session,
    bill_no: str,
    scope: BusinessScopeFilter,
) -> dict[str, Any]:
    """Return one settlement bill's line composition after enforcing scope."""
    cleaned_bill_no = _clean_code(bill_no, max_length=30)
    if not cleaned_bill_no:
        raise ValueError("结算单号不能为空")

    params: dict[str, Any] = {"bill_no": cleaned_bill_no}
    where = [
        "sh.sshbillno = :bill_no",
        "sh.sshwmid = '5'",
        "sh.sshdjlb = 'Z'",
        "sh.sshflag = 'Y'",
        *_scope_conditions(scope, params),
    ]
    sql = f"""
WITH allowed_bill AS (
  SELECT sh.sshbillno,
         sh.sshsupid,
         sh.supplier_name,
         sh.sshmkt,
         st.store_name,
         sh.department_code,
         sh.department_name,
         sh.sshmfid,
         sh.group_name,
         sh.sshcontno,
         sh.sshlastdate,
         sh.sshthisdate
    FROM ods.hq_supsettlehead sh
    LEFT JOIN stores st ON TRIM(st.store_code) = TRIM(sh.sshmkt)
   WHERE {' AND '.join(where)}
)
SELECT b.*,
       t.sdtrowno,
       t.sdtflag,
       t.sdtitemcode,
       t.item_name_raw,
       t.payment_name_raw,
       t.sdtstartdate,
       t.sdtenddate,
       t.sdtdep,
       t.sdtamount,
       t.sdtckamount,
       t.sdtyfamount,
       t.sdtmemo,
       t.sdtdkamount,
       t.sdtye,
       t.sdttype,
       t.sdtisadv,
       t.sdtadjamount,
       t.sdtxssr,
       t.sdthsy,
       t.sdtcalcplace,
       t.sdtmfjzmj,
       t.sdtmfzjmj,
       t.sdttaxrate,
       t.sdtnotaxamount,
       t.source_loaded_at
  FROM allowed_bill b
  JOIN ods.hq_supsettledettot t ON t.sdtbillno = b.sshbillno
 ORDER BY t.sdtrowno
""".strip()
    try:
        rows = db.execute(text(sql), params).mappings().all()
    except (ProgrammingError, DBAPIError) as exc:
        raise OdsUnavailableError("总部库 ODS 明细字段不可用") from exc
    if not rows:
        raise ReceivableNotFoundError("结算单不存在或不在当前账号的数据权限范围内")

    first = rows[0]
    items: list[dict[str, Any]] = []
    totals = {
        "original_amount": 0.0,
        "checked_amount": 0.0,
        "paid_amount": 0.0,
        "deducted_amount": 0.0,
        "balance_amount": 0.0,
        "receivable_amount": 0.0,
        "sales_refund_amount": 0.0,
        "sales_reference_amount": 0.0,
    }
    nonzero_count = 0
    for row in rows:
        amount = _number(row.get("sdtamount"))
        checked_amount = _number(row.get("sdtckamount"))
        paid_amount = _number(row.get("sdtyfamount"))
        deducted_amount = _number(row.get("sdtdkamount"))
        balance_amount = _number(row.get("sdtye"))
        sales_reference_amount = _number(row.get("sdtxssr"))
        item_code = str(row.get("sdtitemcode") or "").strip()
        is_sales_refund = item_code.startswith("00-")
        is_receivable_line = not is_sales_refund
        receivable_component = balance_amount if is_receivable_line else 0.0
        if abs(balance_amount) >= 0.005:
            nonzero_count += 1
        totals["original_amount"] += amount
        totals["checked_amount"] += checked_amount
        totals["paid_amount"] += paid_amount
        totals["deducted_amount"] += deducted_amount
        totals["balance_amount"] += balance_amount
        totals["receivable_amount"] += receivable_component
        if is_sales_refund and balance_amount < 0:
            totals["sales_refund_amount"] += -balance_amount
        totals["sales_reference_amount"] += sales_reference_amount
        items.append(
            {
                "row_no": int(_number(row.get("sdtrowno"))),
                "status": str(row.get("sdtflag") or "").strip() or None,
                "item_code": item_code or None,
                "item_name": _detail_item_name(
                    row.get("sdtitemcode"),
                    row.get("item_name_raw"),
                    row.get("payment_name_raw"),
                ),
                "period_from": _date_text(row.get("sdtstartdate")),
                "period_to": _date_text(row.get("sdtenddate")),
                "finance_month": str(row.get("sdthsy") or "").strip() or None,
                "amount": amount,
                "checked_amount": checked_amount,
                "paid_amount": paid_amount,
                "deducted_amount": deducted_amount,
                "balance_amount": balance_amount,
                "receivable_component": receivable_component,
                "is_sales_refund": is_sales_refund,
                "is_receivable_line": is_receivable_line,
                "adjustment_amount": _number(row.get("sdtadjamount")),
                "sales_reference_amount": sales_reference_amount,
                "tax_rate": _number(row.get("sdttaxrate")),
                "no_tax_amount": _number(row.get("sdtnotaxamount")),
                "memo": row.get("sdtmemo"),
                "calculation_source": row.get("sdtcalcplace"),
                "is_advance": row.get("sdtisadv"),
                "area": _number(row.get("sdtmfjzmj")),
                "rental_area": _number(row.get("sdtmfzjmj")),
            }
        )

    rounded_totals = {key: round(value, 2) for key, value in totals.items()}
    loaded_at = max(
        (row.get("source_loaded_at") for row in rows if isinstance(row.get("source_loaded_at"), datetime)),
        default=None,
    )
    return {
        "bill": {
            "bill_no": first.get("sshbillno"),
            "supplier_id": first.get("sshsupid"),
            "supplier_name": first.get("supplier_name"),
            "store_code": first.get("sshmkt"),
            "store_name": first.get("store_name"),
            "department_code": first.get("department_code"),
            "department_name": first.get("department_name"),
            "group_code": first.get("sshmfid"),
            "group_name": first.get("group_name"),
            "contract_no": first.get("sshcontno"),
            "settle_from": _date_text(first.get("sshlastdate")),
            "settle_to": _date_text(first.get("sshthisdate")),
        },
        "items": items,
        "totals": rounded_totals,
        "detail_count": len(items),
        "nonzero_count": nonzero_count,
        "source_loaded_at": loaded_at.isoformat(timespec="seconds") if loaded_at else "",
    }


def query_rental_receivable_expense_export(
    db: Session,
    filters: ReceivableFilters,
    scope: BusinessScopeFilter,
) -> dict[str, Any]:
    """Return nonzero expense lines for every matching receivable bill."""
    sql, params = build_receivable_expense_export_query(filters, scope)
    try:
        sync_status = _sync_status(db)
        raw_rows = db.execute(text(sql), params).mappings().all()
    except OdsUnavailableError:
        raise
    except (ProgrammingError, DBAPIError) as exc:
        raise OdsUnavailableError("总部库 ODS 费用明细不可用") from exc

    if len(raw_rows) > MAX_EXPORT_DETAIL_ROWS:
        raise ValueError(
            f"费用明细超过单次导出上限 {MAX_EXPORT_DETAIL_ROWS:,} 条，请缩小查询范围后重试"
        )

    rows: list[dict[str, Any]] = []
    for row in raw_rows:
        item_code = str(row.get("sdtitemcode") or "").strip()
        balance_amount = _number(row.get("sdtye"))
        is_sales_refund = item_code.startswith("00-")
        rows.append(
            {
                "store_code": row.get("sshmkt"),
                "store_name": row.get("store_name"),
                "department_code": row.get("department_code"),
                "department_name": row.get("department_name"),
                "group_code": row.get("sshmfid"),
                "group_name": row.get("group_name"),
                "supplier_id": row.get("sshsupid"),
                "supplier_name": row.get("supplier_name"),
                "contract_no": row.get("sshcontno"),
                "bill_no": row.get("sshbillno"),
                "settle_from": _date_text(row.get("sshlastdate")),
                "settle_to": _date_text(row.get("sshthisdate")),
                "bill_receivable_amount": _number(row.get("bill_receivable_amount")),
                "row_no": int(_number(row.get("sdtrowno"))),
                "status": str(row.get("sdtflag") or "").strip() or None,
                "item_code": item_code or None,
                "item_name": _detail_item_name(
                    row.get("sdtitemcode"),
                    row.get("item_name_raw"),
                    row.get("payment_name_raw"),
                ),
                "period_from": _date_text(row.get("sdtstartdate")),
                "period_to": _date_text(row.get("sdtenddate")),
                "finance_month": str(row.get("sdthsy") or "").strip() or None,
                "amount": _number(row.get("sdtamount")),
                "checked_amount": _number(row.get("sdtckamount")),
                "paid_amount": _number(row.get("sdtyfamount")),
                "deducted_amount": _number(row.get("sdtdkamount")),
                "balance_amount": balance_amount,
                "receivable_component": 0.0 if is_sales_refund else balance_amount,
                "is_sales_refund": is_sales_refund,
                "is_receivable_line": not is_sales_refund,
                "adjustment_amount": _number(row.get("sdtadjamount")),
                "sales_reference_amount": _number(row.get("sdtxssr")),
                "tax_rate": _number(row.get("sdttaxrate")),
                "no_tax_amount": _number(row.get("sdtnotaxamount")),
                "memo": row.get("sdtmemo"),
                "calculation_source": row.get("sdtcalcplace"),
                "is_advance": row.get("sdtisadv"),
                "area": _number(row.get("sdtmfjzmj")),
                "rental_area": _number(row.get("sdtmfzjmj")),
            }
        )

    loaded_at = sync_status.get("source_loaded_at")
    return {
        "items": rows,
        "detail_count": len(rows),
        "bill_count": len({row["bill_no"] for row in rows}),
        "filters": {
            "settle_from": filters.settle_from.isoformat(),
            "settle_to": filters.settle_to.isoformat(),
            "mkt": filters.mkt,
            "department_code": filters.department_code,
            "group_prefix": filters.group_prefix,
            "keyword": filters.keyword,
        },
        "source": LOCAL_ODS_SOURCE,
        "source_loaded_at": (
            loaded_at.isoformat(timespec="seconds")
            if isinstance(loaded_at, datetime)
            else str(loaded_at or "")
        ),
        "generated_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
        "scope_note": "仅导出当前账号权限及当前查询条件内、明细余额非零的费用行；00-* 销售返款保留但不计入应收",
    }


def query_rental_receivable_options(
    db: Session,
    scope: BusinessScopeFilter,
) -> dict[str, list[dict[str, Any]]]:
    """Return store and department filters already constrained by data scope."""
    params: dict[str, Any] = {}
    conditions = [
        "sh.sshwmid = '5'",
        "sh.sshdjlb = 'Z'",
        "sh.sshflag = 'Y'",
        *_scope_conditions(scope, params),
    ]
    sql = f"""
        SELECT sh.sshmkt AS store_code,
               COALESCE(NULLIF(TRIM(st.store_name), ''), sh.sshmkt) AS store_name,
               sh.department_code,
               sh.department_name
          FROM ods.hq_supsettlehead sh
          LEFT JOIN stores st ON TRIM(st.store_code) = TRIM(sh.sshmkt)
         WHERE {' AND '.join(conditions)}
         GROUP BY sh.sshmkt, st.store_name, sh.department_code, sh.department_name
         ORDER BY sh.sshmkt, sh.department_code NULLS LAST
    """
    try:
        rows = db.execute(text(sql), params).mappings().all()
    except (ProgrammingError, DBAPIError) as exc:
        raise OdsUnavailableError("总部库 ODS 表不可用") from exc

    stores_by_code: dict[str, dict[str, Any]] = {}
    departments: list[dict[str, Any]] = []
    for row in rows:
        store_code = str(row.get("store_code") or "").strip()
        if store_code:
            stores_by_code.setdefault(
                store_code,
                {
                    "store_code": store_code,
                    "store_name": row.get("store_name") or store_code,
                },
            )
        department_code = str(row.get("department_code") or "").strip()
        if department_code:
            departments.append(
                {
                    "department_code": department_code,
                    "department_name": row.get("department_name") or department_code,
                    "store_code": store_code or None,
                }
            )

    return {
        "stores": list(stores_by_code.values()),
        "departments": departments,
    }


def _sync_status(db: Session) -> dict[str, Any]:
    status = db.execute(
        text(
            """
            SELECT h.row_count AS head_rows,
                   t.row_count AS detail_rows,
                   LEAST(h.loaded_at, t.loaded_at) AS source_loaded_at
              FROM (SELECT COUNT(*) AS row_count, MAX(source_loaded_at) AS loaded_at FROM ods.hq_supsettlehead) h
              CROSS JOIN (SELECT COUNT(*) AS row_count, MAX(source_loaded_at) AS loaded_at FROM ods.hq_supsettledettot) t
            """
        )
    ).mappings().one()
    if any(int(status[key] or 0) <= 0 for key in ("head_rows", "detail_rows")):
        raise OdsUnavailableError("总部库 ODS 尚未完成首次同步")
    return dict(status)


def query_mobile_rental_receivable_drilldown(
    db: Session,
    *,
    level: str,
    settle_from: date,
    settle_to: date,
    scope: BusinessScopeFilter,
    mkt: str | None = None,
    department_code: str | None = None,
) -> dict[str, Any]:
    sql, params = build_mobile_drilldown_query(
        level=level,
        settle_from=settle_from,
        settle_to=settle_to,
        scope=scope,
        mkt=mkt,
        department_code=department_code,
    )
    try:
        sync_status = _sync_status(db)
        raw_rows = db.execute(text(sql), params).mappings().all()
    except OdsUnavailableError:
        raise
    except (ProgrammingError, DBAPIError) as exc:
        raise OdsUnavailableError("总部库 ODS 表不可用") from exc

    items = [
        {
            "code": row.get("code"),
            "name": row.get("name"),
            "bill_count": int(_number(row.get("bill_count"))),
            "next_count": int(_number(row.get("next_count"))),
            "receivable_amount": _number(row.get("receivable_amount")),
            "original_receivable_amount": _number(row.get("original_receivable_amount")),
            "sales_refund_amount": _number(row.get("sales_refund_amount")),
            "partial_count": int(_number(row.get("partial_count"))),
            "anomaly_count": int(_number(row.get("anomaly_count"))),
            "over_90_amount": _number(row.get("over_90_amount")),
            "latest_settle_to": _date_text(row.get("latest_settle_to")),
        }
        for row in raw_rows
    ]
    items = _sort_mobile_drilldown_items(level, items)
    loaded_at = sync_status.get("source_loaded_at")
    return {
        "level": level,
        "items": items,
        "summary": {
            "bill_count": sum(row["bill_count"] for row in items),
            "receivable_amount": round(sum(row["receivable_amount"] for row in items), 2),
            "original_receivable_amount": round(
                sum(row["original_receivable_amount"] for row in items), 2
            ),
            "sales_refund_amount": round(sum(row["sales_refund_amount"] for row in items), 2),
            "partial_count": sum(row["partial_count"] for row in items),
            "anomaly_count": sum(row["anomaly_count"] for row in items),
            "over_90_amount": round(sum(row["over_90_amount"] for row in items), 2),
        },
        "source": LOCAL_ODS_SOURCE,
        "source_loaded_at": (
            loaded_at.isoformat(timespec="seconds")
            if isinstance(loaded_at, datetime)
            else str(loaded_at or "")
        ),
        "queried_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
        "permission_scoped": True,
    }


def query_rental_receivables(
    db: Session,
    filters: ReceivableFilters,
    scope: BusinessScopeFilter,
) -> dict[str, Any]:
    sql, params = build_receivables_query(filters, scope)
    try:
        sync_status = _sync_status(db)
        raw_rows = db.execute(text(sql), params).mappings().all()
    except OdsUnavailableError:
        raise
    except (ProgrammingError, DBAPIError) as exc:
        raise OdsUnavailableError("总部库 ODS 表不可用") from exc

    rows: list[dict[str, Any]] = []
    for row in raw_rows:
        rows.append(
            {
                "bill_no": row.get("sshbillno"),
                "supplier_id": row.get("sshsupid"),
                "supplier_name": row.get("supplier_name"),
                "store_code": row.get("sshmkt"),
                "store_name": row.get("store_name"),
                "department_code": row.get("department_code"),
                "department_name": row.get("department_name"),
                "group_code": row.get("sshmfid"),
                "group_name": row.get("group_name"),
                "contract_no": row.get("sshcontno"),
                "settle_from": _date_text(row.get("settle_from")),
                "settle_to": _date_text(row.get("settle_to")),
                "original_amount": _number(row.get("original_amount")),
                "original_receivable_amount": _number(row.get("original_receivable_amount")),
                "receivable_amount": _number(row.get("receivable_amount")),
                "sales_refund_amount": _number(row.get("sales_refund_amount")),
                "aging_days": int(_number(row.get("aging_days"))),
                "outstanding_status": row.get("outstanding_status") or "FULL",
            }
        )

    first = dict(raw_rows[0]) if raw_rows else {}
    total = int(_number(first.get("total_count")))
    loaded_at = sync_status.get("source_loaded_at")
    return {
        "items": rows,
        "total": total,
        "page": filters.page,
        "page_size": filters.page_size,
        "summary": {
            "bill_count": total,
            "receivable_amount": _number(first.get("total_receivable_amount")),
            "original_amount": _number(first.get("total_original_amount")),
            "sales_refund_amount": _number(first.get("total_sales_refund_amount")),
            "partial_count": int(_number(first.get("partial_count"))),
            "anomaly_count": int(_number(first.get("anomaly_count"))),
            "over_90_amount": _number(first.get("over_90_amount")),
        },
        "source": LOCAL_ODS_SOURCE,
        "source_loaded_at": loaded_at.isoformat(timespec="seconds") if isinstance(loaded_at, datetime) else str(loaded_at or ""),
        "queried_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
        "scope_note": "租赁结算单；已审核；非 00-* 项目存在非零未收余额；是否生成收款单不作为整单剔除依据",
    }
