from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from .od0002_report import TrustedScopeSql, _trusted_scope_value, compare_period


HY0001_QUERY_TIMEOUT_SECONDS = 120

MEMBER_LEVELS = (
    ("03", "黑金卡会员"),
    ("04", "黑钻卡会员"),
    ("02", "金星卡会员"),
    ("01", "银星卡会员"),
)


def date_window(start_date: date, end_date: date) -> tuple[date, date, date, date]:
    """Return the selected date range and its prior-year comparison range."""
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")
    prior_start, prior_end = compare_period(start_date, end_date)
    return start_date, end_date, prior_start, prior_end


def _clean_optional(value: str | None) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None


def _yoy(current: float, prior: float) -> float | None:
    if prior == 0:
        return None
    return current / prior - 1


def build_report_query(
    *,
    start_date: date,
    end_date: date,
    scope_filter_sql: str | TrustedScopeSql,
    scope_params: Mapping[str, Any],
    selected_store: str,
    selected_department: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Build the permission-scoped HY0001 key-brand member comparison query."""
    current_start, current_end, prior_start, prior_end = date_window(start_date, end_date)
    scope_sql = _trusted_scope_value(scope_filter_sql)
    normalized_store = _clean_optional(selected_store)
    if normalized_store is None:
        raise ValueError("HY0001 requires one selected store")

    params = dict(scope_params)
    params.update(
        {
            "current_start": current_start,
            "current_end": current_end,
            "prior_start": prior_start,
            "prior_end": prior_end,
            "selected_store": normalized_store,
        }
    )
    department_sql = ""
    normalized_department = _clean_optional(selected_department)
    if normalized_department is not None:
        params["selected_department"] = normalized_department.upper()
        department_sql = (
            "AND UPPER(TRIM(BOTH FROM COALESCE(dept.mfcode, ''))) "
            "= :selected_department"
        )

    sql = f"""
WITH area_category_dedup AS (
  SELECT DISTINCT ON (UPPER(TRIM(BOTH FROM category_code)))
    UPPER(TRIM(BOTH FROM category_code)) AS normalized_category_code,
    TRIM(BOTH FROM category_code) AS category_code,
    area_name,
    category_name
  FROM area_category
  ORDER BY UPPER(TRIM(BOTH FROM category_code)), area_name, category_name
),
key_brands AS MATERIALIZED (
  SELECT DISTINCT ON (st.store_code, UPPER(TRIM(BOTH FROM mf.mfcode)))
    st.store_id,
    TRIM(BOTH FROM st.store_code) AS store_code,
    st.store_name,
    TRIM(BOTH FROM dept.mfcode) AS department_code,
    NULLIF(TRIM(BOTH FROM dept.mfcname), '') AS department_name,
    TRIM(BOTH FROM mf.mfcode) AS group_code,
    COALESCE(NULLIF(TRIM(BOTH FROM mf.mfcname), ''), TRIM(BOTH FROM mf.mfcode)) AS group_name,
    NULLIF(TRIM(BOTH FROM assignment.manager_name), '') AS manager_name
  FROM manaframe_key_brand marker
  JOIN manaframe mf
    ON UPPER(TRIM(BOTH FROM marker.mfcode)) = UPPER(TRIM(BOTH FROM mf.mfcode))
  LEFT JOIN manaframe dept
    ON UPPER(TRIM(BOTH FROM mf.mfpcode)) = UPPER(TRIM(BOTH FROM dept.mfcode))
  LEFT JOIN area_category_dedup ac
    ON UPPER(TRIM(BOTH FROM COALESCE(mf.mfchr1, ''))) = ac.normalized_category_code
  JOIN stores st
    ON st.is_active IS TRUE
   AND LEFT(TRIM(BOTH FROM mf.mfcode), 3) = TRIM(BOTH FROM st.store_code)
  LEFT JOIN category_manager_brand_assignments assignment
    ON assignment.store_id = st.store_id
   AND UPPER(TRIM(BOTH FROM assignment.group_code)) = UPPER(TRIM(BOTH FROM mf.mfcode))
   AND assignment.is_active IS TRUE
  WHERE marker.is_key_brand IS TRUE
    AND TRIM(BOTH FROM st.store_code) = :selected_store
    {department_sql}
    {scope_sql}
  ORDER BY st.store_code, UPPER(TRIM(BOTH FROM mf.mfcode)), assignment.updated_at DESC NULLS LAST
),
periods(period_key, start_date, end_date) AS (
  VALUES
    ('current', CAST(:current_start AS date), CAST(:current_end AS date)),
    ('prior', CAST(:prior_start AS date), CAST(:prior_end AS date))
),
member_receipts AS MATERIALIZED (
  SELECT
    periods.period_key,
    key_brands.store_code,
    key_brands.group_code,
    CASE
      WHEN TRIM(BOTH FROM COALESCE(h.custtype, '')) IN ('01', '02', '03', '04')
      THEN TRIM(BOTH FROM h.custtype)
      ELSE NULL
    END AS level_code,
    NULLIF(UPPER(TRIM(BOTH FROM COALESCE(h.hykh, ''))), '') AS member_no,
    s.sglbillno AS billno,
    SUM(COALESCE(s.sglxssr, 0)::numeric) AS sales_revenue
  FROM periods
  JOIN salegoodslist s
    ON s.sglhsrq BETWEEN periods.start_date AND periods.end_date
  JOIN key_brands
    ON key_brands.store_code = TRIM(BOTH FROM s.sglmarket::text)
   AND UPPER(key_brands.group_code) = UPPER(TRIM(BOTH FROM s.sglmfid))
  JOIN salehead h
    ON h.billno = s.sglbillno
   AND TRIM(BOTH FROM h.mkt::text) = TRIM(BOTH FROM s.sglmarket::text)
  WHERE NULLIF(TRIM(BOTH FROM COALESCE(h.hykh, '')), '') IS NOT NULL
    AND TRIM(BOTH FROM COALESCE(h.custtype, '')) IN ('01', '02', '03', '04')
  GROUP BY
    periods.period_key,
    key_brands.store_code,
    key_brands.group_code,
    level_code,
    member_no,
    s.sglbillno
),
member_level_members AS MATERIALIZED (
  SELECT
    period_key,
    store_code,
    group_code,
    level_code,
    member_no,
    SUM(sales_revenue) AS sales_revenue,
    BOOL_OR(sales_revenue > 0) AS has_positive_purchase
  FROM member_receipts
  GROUP BY period_key, store_code, group_code, level_code, member_no
),
level_totals AS (
  SELECT
    period_key,
    store_code,
    group_code,
    level_code,
    COALESCE(SUM(sales_revenue), 0) AS sales_revenue,
    COUNT(*) AS buyer_count
  FROM member_level_members
  WHERE has_positive_purchase IS TRUE
  GROUP BY period_key, store_code, group_code, level_code
),
level_defs(level_code, level_label, sort_order) AS (
  VALUES
    ('03', '黑金卡会员', 1),
    ('04', '黑钻卡会员', 2),
    ('02', '金星卡会员', 3),
    ('01', '银星卡会员', 4)
)
SELECT
  key_brands.store_code,
  key_brands.store_name,
  key_brands.department_code,
  key_brands.department_name,
  key_brands.group_code,
  key_brands.group_name,
  key_brands.manager_name,
  level_defs.level_code,
  level_defs.level_label,
  COALESCE(current_totals.sales_revenue, 0) AS current_sales,
  COALESCE(prior_totals.sales_revenue, 0) AS prior_sales,
  COALESCE(current_totals.buyer_count, 0) AS current_buyers,
  COALESCE(prior_totals.buyer_count, 0) AS prior_buyers
FROM key_brands
CROSS JOIN level_defs
LEFT JOIN level_totals current_totals
  ON current_totals.period_key = 'current'
 AND current_totals.store_code = key_brands.store_code
 AND current_totals.group_code = key_brands.group_code
 AND current_totals.level_code = level_defs.level_code
LEFT JOIN level_totals prior_totals
  ON prior_totals.period_key = 'prior'
 AND prior_totals.store_code = key_brands.store_code
 AND prior_totals.group_code = key_brands.group_code
 AND prior_totals.level_code = level_defs.level_code
ORDER BY
  COALESCE(key_brands.manager_name, ''),
  key_brands.department_code,
  key_brands.group_name,
  key_brands.group_code,
  level_defs.sort_order
"""
    return sql, params


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def assemble_report(
    raw_rows: list[Mapping[str, Any]],
    *,
    start_date: date,
    end_date: date,
    selected_store: str,
    selected_department: str | None,
) -> dict[str, Any]:
    current_start, current_end, prior_start, prior_end = date_window(start_date, end_date)
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    for source in raw_rows:
        row = {key: _json_value(value) for key, value in source.items()}
        key = (str(row.get("store_code") or ""), str(row.get("group_code") or ""))
        group = groups.setdefault(
            key,
            {
                "store_code": row.get("store_code"),
                "store_name": row.get("store_name"),
                "department_code": row.get("department_code"),
                "department_name": row.get("department_name"),
                "group_code": row.get("group_code"),
                "group_name": row.get("group_name"),
                "manager_name": row.get("manager_name") or "未维护",
                "levels": [],
            },
        )
        current_sales = float(row.get("current_sales") or 0)
        prior_sales = float(row.get("prior_sales") or 0)
        current_buyers = int(row.get("current_buyers") or 0)
        prior_buyers = int(row.get("prior_buyers") or 0)
        group["levels"].append(
            {
                "level_code": row.get("level_code"),
                "level_label": row.get("level_label"),
                "current_sales": current_sales,
                "prior_sales": prior_sales,
                "sales_yoy": _yoy(current_sales, prior_sales),
                "current_buyers": current_buyers,
                "prior_buyers": prior_buyers,
                "buyer_yoy": _yoy(float(current_buyers), float(prior_buyers)),
            }
        )

    rows = list(groups.values())
    level_order = {code: index for index, (code, _label) in enumerate(MEMBER_LEVELS)}
    for row in rows:
        row["levels"].sort(key=lambda item: level_order.get(str(item["level_code"]), 99))

    manager_totals: dict[str, dict[str, Any]] = {}
    for row in rows:
        manager_name = str(row["manager_name"])
        summary = manager_totals.setdefault(
            manager_name,
            {
                "manager_name": manager_name,
                "key_brand_count": 0,
                "current_premium_sales": 0.0,
                "prior_premium_sales": 0.0,
            },
        )
        summary["key_brand_count"] += 1
        for level in row["levels"]:
            if level["level_code"] in {"03", "04"}:
                summary["current_premium_sales"] += level["current_sales"]
                summary["prior_premium_sales"] += level["prior_sales"]
    manager_summary = []
    for summary in manager_totals.values():
        summary["premium_sales_yoy"] = _yoy(
            summary["current_premium_sales"], summary["prior_premium_sales"]
        )
        manager_summary.append(summary)
    manager_summary.sort(key=lambda item: (item["manager_name"] == "未维护", item["manager_name"]))

    return {
        "report_code": "HY0001",
        "report_name": "重点品牌会员消费情况",
        "dates": {
            "current_start": current_start.isoformat(),
            "current_end": current_end.isoformat(),
            "prior_start": prior_start.isoformat(),
            "prior_end": prior_end.isoformat(),
        },
        "selected_store": selected_store,
        "selected_department": _clean_optional(selected_department),
        "levels": [
            {"level_code": code, "level_label": label}
            for code, label in MEMBER_LEVELS
        ],
        "rows": rows,
        "manager_summary": manager_summary,
        "quality": {
            "key_brand_count": len(rows),
            "unassigned_manager_count": sum(
                1 for row in rows if row["manager_name"] == "未维护"
            ),
            "no_current_member_sales_count": sum(
                1
                for row in rows
                if sum(level["current_sales"] for level in row["levels"]) == 0
            ),
        },
    }


def load_hy0001_report(
    db: Any,
    scope_filter_sql: str | TrustedScopeSql,
    scope_params: Mapping[str, Any],
    *,
    start_date: date,
    end_date: date,
    selected_store: str,
    selected_department: str | None = None,
) -> dict[str, Any]:
    sql, params = build_report_query(
        start_date=start_date,
        end_date=end_date,
        scope_filter_sql=scope_filter_sql,
        scope_params=scope_params,
        selected_store=selected_store,
        selected_department=selected_department,
    )
    db.execute(text(f"SET LOCAL statement_timeout = '{HY0001_QUERY_TIMEOUT_SECONDS}s'"))
    raw_rows = db.execute(text(sql), params).mappings().all()
    return assemble_report(
        list(raw_rows),
        start_date=start_date,
        end_date=end_date,
        selected_store=selected_store,
        selected_department=selected_department,
    )
