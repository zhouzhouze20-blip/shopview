from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from collections.abc import Iterable, Mapping
from itertools import groupby
from typing import Any

from sqlalchemy import text

from services.department_display_order import department_display_sort_key


OD0002_QUERY_TIMEOUT_SECONDS = 120


EXCLUDED_DEPARTMENT_CODES = frozenset(
    {
        "6010115",
        "6010108",
        "6010109",
        "6010110",
        "6010202",
        "6010205",
        "6020105",
        "6020107",
        "6020109",
        "6020202",
        "6020205",
        "6030108",
        "6030109",
        "6030111",
        "6030202",
        "6030205",
    }
)

FLOOR_NAMES = {
    "01": "BF",
    "02": "1F",
    "03": "2F",
    "04": "3F",
    "05": "4F",
    "06": "5F",
    "07": "6F",
    "08": "7F",
    "09": "8F",
    "10": "9F",
    "11": "10F",
    "12": "11F",
    "13": "12F",
    "14": "13F",
    "15": "14F",
    "16": "特卖",
    "17": "微商城",
    "18": "15F",
    "19": "16F",
}


def _previous_year(value: date) -> date:
    previous_year = value.year - 1
    last_day = monthrange(previous_year, value.month)[1]
    return date(previous_year, value.month, min(value.day, last_day))


def compare_period(start: date, end: date) -> tuple[date, date]:
    if end < start:
        raise ValueError("end_date must be on or after start_date")
    return _previous_year(start), _previous_year(end)


def _number(value: Any) -> float:
    return float(value or Decimal("0"))


def _ratio(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def metric_triplet(
    sales_current: Any,
    profit_current: Any,
    sales_prior: Any,
    profit_prior: Any,
    ticket_count_current: Any = 0,
    ticket_count_prior: Any = 0,
) -> dict[str, float | None]:
    sc, pc, sp, pp, tc, tp = map(
        _number,
        (
            sales_current,
            profit_current,
            sales_prior,
            profit_prior,
            ticket_count_current,
            ticket_count_prior,
        ),
    )
    margin_current = _ratio(pc, sc)
    margin_prior = _ratio(pp, sp)
    average_ticket_current = _ratio(sc, tc)
    average_ticket_prior = _ratio(sp, tp)
    average_ticket_yoy = (
        _ratio(
            average_ticket_current - average_ticket_prior,
            average_ticket_prior,
        )
        if average_ticket_current is not None and average_ticket_prior is not None
        else None
    )
    margin_change = (
        round(margin_current - margin_prior, 12)
        if margin_current is not None and margin_prior is not None
        else None
    )
    return {
        "ticket_count_current": int(tc),
        "ticket_count_prior": int(tp),
        "ticket_count_yoy": _ratio(tc - tp, tp),
        "average_ticket_current": average_ticket_current,
        "average_ticket_prior": average_ticket_prior,
        "average_ticket_yoy": average_ticket_yoy,
        "sales_current": sc,
        "sales_prior": sp,
        "sales_yoy": _ratio(sc - sp, sp),
        "profit_current": pc,
        "profit_prior": pp,
        "profit_yoy": _ratio(pc - pp, pp),
        "margin_current": margin_current,
        "margin_prior": margin_prior,
        "margin_change": margin_change,
    }


DIMENSION_TYPES = (
    "stores",
    "departments",
    "department_categories",
    "areas",
    "categories",
    "groups",
    "special_sales",
    "floors",
)


@dataclass(frozen=True)
class TrustedScopeSql:
    """SQL fragment produced only by routers.sales._business_scope_filter_sql."""

    value: str


def _trusted_scope_value(scope_filter_sql: str | TrustedScopeSql) -> str:
    value = (
        scope_filter_sql.value
        if isinstance(scope_filter_sql, TrustedScopeSql)
        else scope_filter_sql
    )
    if not isinstance(value, str) or any(
        marker in value for marker in (";", "--", "/*", "*/")
    ):
        raise ValueError(
            "scope_filter_sql must be an internally generated SQL fragment "
            "without statement or comment markers"
        )
    return value


def build_authorized_stores_query(
    scope_filter_sql: str | TrustedScopeSql,
    scope_params: Mapping[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Build the dimension-backed OD0002 store selector query.

    This deliberately avoids salegoodslist so an authorized store remains
    selectable when it has no sales in the requested report period.
    """
    scope_sql = _trusted_scope_value(scope_filter_sql)
    sql = f"""
SELECT DISTINCT
  st.store_id,
  TRIM(BOTH FROM st.store_code) AS store_code,
  st.store_name
FROM stores st
JOIN manaframe mf
  ON TRIM(BOTH FROM COALESCE(st.store_code, '')) = CASE
    WHEN SUBSTRING(TRIM(BOTH FROM COALESCE(mf.mfcode, '')) FROM 1 FOR 3) ~ '^[0-9]{{3}}$'
    THEN SUBSTRING(TRIM(BOTH FROM mf.mfcode) FROM 1 FOR 3)
    ELSE NULL
  END
LEFT JOIN manaframe dept
  ON UPPER(TRIM(COALESCE(mf.mfpcode, ''))) = UPPER(TRIM(COALESCE(dept.mfcode, '')))
LEFT JOIN area_category ac
  ON UPPER(TRIM(COALESCE(mf.mfchr1, ''))) = UPPER(TRIM(COALESCE(ac.category_code, '')))
WHERE st.is_active IS TRUE
  AND TRIM(BOTH FROM COALESCE(mf.mflc, '')) <> '00'
  {scope_sql}
ORDER BY store_code, st.store_id
"""
    return sql, dict(scope_params)


def load_od0002_authorized_stores(
    db: Any,
    scope_filter_sql: str | TrustedScopeSql,
    scope_params: Mapping[str, Any],
) -> list[dict[str, Any]]:
    sql, params = build_authorized_stores_query(scope_filter_sql, scope_params)
    rows = db.execute(text(sql), params).mappings().all()
    return [dict(row) for row in rows]


def build_authorized_departments_query(
    scope_filter_sql: str | TrustedScopeSql,
    scope_params: Mapping[str, Any],
    selected_store: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Build the permission-scoped OD0002 department selector query."""
    scope_sql = _trusted_scope_value(scope_filter_sql)
    params = dict(scope_params)
    params["excluded_department_codes"] = sorted(EXCLUDED_DEPARTMENT_CODES)
    selected_store_sql = ""
    if selected_store:
        params["selected_store"] = selected_store.strip()
        selected_store_sql = " AND TRIM(BOTH FROM st.store_code) = :selected_store"
    sql = f"""
SELECT DISTINCT
  TRIM(BOTH FROM st.store_code) AS store_code,
  TRIM(BOTH FROM dept.mfcode) AS department_code,
  COALESCE(NULLIF(TRIM(BOTH FROM dept.mfcname), ''), TRIM(BOTH FROM dept.mfcode)) AS department_name
FROM stores st
JOIN manaframe mf
  ON TRIM(BOTH FROM st.store_code) = SUBSTRING(TRIM(BOTH FROM mf.mfcode) FROM 1 FOR 3)
JOIN manaframe dept
  ON UPPER(TRIM(COALESCE(mf.mfpcode, ''))) = UPPER(TRIM(COALESCE(dept.mfcode, '')))
LEFT JOIN area_category ac
  ON UPPER(TRIM(COALESCE(mf.mfchr1, ''))) = UPPER(TRIM(COALESCE(ac.category_code, '')))
WHERE st.is_active IS TRUE
  AND TRIM(BOTH FROM COALESCE(mf.mflc, '')) <> '00'
  AND TRIM(BOTH FROM COALESCE(dept.mfcode, '')) <> ''
  AND TRIM(BOTH FROM dept.mfcode) <> ALL(:excluded_department_codes)
  {scope_sql}
  {selected_store_sql}
"""
    return sql, params


def load_od0002_authorized_departments(
    db: Any,
    scope_filter_sql: str | TrustedScopeSql,
    scope_params: Mapping[str, Any],
    selected_store: str | None = None,
) -> list[dict[str, Any]]:
    sql, params = build_authorized_departments_query(
        scope_filter_sql, scope_params, selected_store
    )
    rows = [dict(row) for row in db.execute(text(sql), params).mappings().all()]
    rows.sort(
        key=lambda row: (
            str(row.get("store_code") or ""),
            department_display_sort_key(row),
        )
    )
    return rows


def build_report_query(
    start_date: date,
    end_date: date,
    prior_start_date: date,
    prior_end_date: date,
    scope_filter_sql: str | TrustedScopeSql,
    scope_params: Mapping[str, Any],
    selected_store: str | None = None,
    selected_department: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Build the bound PostgreSQL query for all OD0002 report dimensions."""
    # The SQL shape is trusted internal structure; all user-controlled scope
    # values remain in scope_params and are passed to the database as binds.
    scope_sql = _trusted_scope_value(scope_filter_sql)
    params = dict(scope_params)
    params.update(
        {
            "start_date": start_date,
            "end_date": end_date,
            "prior_start_date": prior_start_date,
            "prior_end_date": prior_end_date,
            "excluded_department_codes": sorted(EXCLUDED_DEPARTMENT_CODES),
        }
    )
    selected_store_sales_sql = ""
    if selected_store is not None:
        params["selected_store"] = selected_store
        selected_store_sales_sql = " AND s.sglmarket = :selected_store"
    selected_department_sql = ""
    if selected_department and selected_department.strip():
        params["selected_department"] = selected_department.strip()
        selected_department_sql = (
            " AND UPPER(TRIM(BOTH FROM COALESCE(dept.mfcode, ''))) "
            "= UPPER(:selected_department)"
        )

    floor_cases = "\n".join(
        f"WHEN '{code}' THEN '{name}'" for code, name in FLOOR_NAMES.items()
    )
    sql = f"""
WITH filtered_sales AS (
  -- Collapse raw tickets before normalized ERP dimension joins. The normalized
  -- joins cannot use the source indexes, so their input must stay bounded.
  SELECT
    s.sglmarket,
    s.sglmfid,
    s.sglppcode,
    s.sglbillno,
    MAX(CASE WHEN s.sglhsrq BETWEEN :start_date AND :end_date
             THEN s.sglbillno END) AS ticket_current,
    MAX(CASE WHEN s.sglhsrq BETWEEN :prior_start_date AND :prior_end_date
             THEN s.sglbillno END) AS ticket_prior,
    SUM(CASE WHEN s.sglhsrq BETWEEN :start_date AND :end_date
             THEN COALESCE(s.sglxssr, 0) ELSE 0 END) AS sales_current,
    SUM(CASE WHEN s.sglhsrq BETWEEN :start_date AND :end_date
             THEN COALESCE(s.sgln2, 0) ELSE 0 END) AS profit_current,
    SUM(CASE WHEN s.sglhsrq BETWEEN :prior_start_date AND :prior_end_date
             THEN COALESCE(s.sglxssr, 0) ELSE 0 END) AS sales_prior,
    SUM(CASE WHEN s.sglhsrq BETWEEN :prior_start_date AND :prior_end_date
             THEN COALESCE(s.sgln2, 0) ELSE 0 END) AS profit_prior
  FROM salegoodslist s
  WHERE (
       s.sglhsrq BETWEEN :start_date AND :end_date
       OR s.sglhsrq BETWEEN :prior_start_date AND :prior_end_date
  )
    AND (s.sglwmid IS NULL OR s.sglwmid <> '5')
    {selected_store_sales_sql}
  GROUP BY s.sglmarket, s.sglmfid, s.sglppcode, s.sglbillno
),
area_category_dedup AS (
  SELECT DISTINCT ON (UPPER(TRIM(BOTH FROM category_code)))
    UPPER(TRIM(BOTH FROM category_code)) AS normalized_category_code,
    TRIM(BOTH FROM category_code) AS category_code,
    area_code,
    area_name,
    category_name
  FROM area_category
  ORDER BY UPPER(TRIM(BOTH FROM category_code)), area_code, area_name, category_name
),
enriched_sales AS (
  SELECT
    s.sglmarket::text AS store_code,
    st.store_name AS store_name,
    TRIM(BOTH FROM COALESCE(dept.mfcode, '')) AS department_code,
    COALESCE(NULLIF(TRIM(BOTH FROM dept.mfcname), ''), '未匹配') AS department_name,
    ac.area_code,
    COALESCE(NULLIF(TRIM(BOTH FROM ac.area_name), ''), '未匹配') AS area_name,
    ac.category_code,
    COALESCE(NULLIF(TRIM(BOTH FROM ac.category_name), ''), '未匹配') AS category_name,
    TRIM(BOTH FROM COALESCE(mf.mfcode, '')) AS group_code,
    COALESCE(NULLIF(TRIM(BOTH FROM mf.mfcname), ''), '未匹配') AS group_name,
    TRIM(BOTH FROM COALESCE(mf.mflc, '')) AS floor_code,
    CASE TRIM(BOTH FROM COALESCE(mf.mflc, ''))
      {floor_cases}
      ELSE '未匹配'
    END AS floor_name,
    TRIM(BOTH FROM COALESCE(s.sglppcode, '')) AS brand_code,
    COALESCE(NULLIF(TRIM(BOTH FROM cb.cbcname), ''), '未匹配') AS brand_name,
    s.ticket_current,
    s.ticket_prior,
    s.sales_current,
    s.profit_current,
    s.sales_prior,
    s.profit_prior
  FROM filtered_sales s
  JOIN manaframe mf
    ON UPPER(TRIM(COALESCE(s.sglmfid, ''))) = UPPER(TRIM(COALESCE(mf.mfcode, '')))
  LEFT JOIN manaframe dept
    ON UPPER(TRIM(COALESCE(mf.mfpcode, ''))) = UPPER(TRIM(COALESCE(dept.mfcode, '')))
  LEFT JOIN area_category_dedup ac
    ON UPPER(TRIM(COALESCE(mf.mfchr1, ''))) = ac.normalized_category_code
  LEFT JOIN codebrand cb
    ON UPPER(TRIM(COALESCE(s.sglppcode, ''))) = UPPER(TRIM(COALESCE(cb.cbid, '')))
  LEFT JOIN stores st
    ON TRIM(BOTH FROM COALESCE(st.store_code, '')) = s.sglmarket::text
  WHERE TRIM(BOTH FROM COALESCE(mf.mflc, '')) <> '00'
    AND TRIM(BOTH FROM COALESCE(dept.mfcode, '')) <> ALL(:excluded_department_codes)
    AND TRIM(BOTH FROM COALESCE(ac.area_name, '')) <> '其他类别区域'
    {scope_sql}
    {selected_department_sql}
),
base AS (
  SELECT
    store_code,
    store_name,
    department_code,
    department_name,
    area_code,
    area_name,
    category_code,
    category_name,
    group_code,
    group_name,
    floor_code,
    floor_name,
    ticket_current,
    ticket_prior,
    SUM(sales_current) AS sales_current,
    SUM(profit_current) AS profit_current,
    SUM(sales_prior) AS sales_prior,
    SUM(profit_prior) AS profit_prior
  FROM enriched_sales
  GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14
),
stores AS (
  SELECT 'stores' AS dimension_type, store_code, store_name,
         store_code AS dimension_code, store_name AS dimension_name,
         NULL::text AS department_code, NULL::text AS department_name,
         NULL::text AS area_code, NULL::text AS area_name,
         NULL::text AS category_code, NULL::text AS category_name,
         NULL::text AS brand_code, NULL::text AS brand_name,
         SUM(sales_current) AS sales_current, SUM(profit_current) AS profit_current,
         SUM(sales_prior) AS sales_prior, SUM(profit_prior) AS profit_prior,
         COUNT(DISTINCT ticket_current) AS ticket_count_current,
         COUNT(DISTINCT ticket_prior) AS ticket_count_prior
  FROM base GROUP BY store_code, store_name
),
departments AS (
  SELECT 'departments' AS dimension_type, store_code, store_name,
         department_code AS dimension_code, department_name AS dimension_name,
         NULL::text AS department_code, NULL::text AS department_name,
         NULL::text AS area_code, NULL::text AS area_name,
         NULL::text AS category_code, NULL::text AS category_name,
         NULL::text AS brand_code, NULL::text AS brand_name,
         SUM(sales_current) AS sales_current, SUM(profit_current) AS profit_current,
         SUM(sales_prior) AS sales_prior, SUM(profit_prior) AS profit_prior,
         COUNT(DISTINCT ticket_current) AS ticket_count_current,
         COUNT(DISTINCT ticket_prior) AS ticket_count_prior
  FROM base GROUP BY store_code, store_name, department_code, department_name
),
department_categories AS (
  SELECT 'department_categories' AS dimension_type, store_code, store_name,
         category_code AS dimension_code, category_name AS dimension_name,
         department_code, department_name, area_code, area_name,
         category_code, category_name,
         NULL::text AS brand_code, NULL::text AS brand_name,
         SUM(sales_current) AS sales_current, SUM(profit_current) AS profit_current,
         SUM(sales_prior) AS sales_prior, SUM(profit_prior) AS profit_prior,
         COUNT(DISTINCT ticket_current) AS ticket_count_current,
         COUNT(DISTINCT ticket_prior) AS ticket_count_prior
  FROM base
  GROUP BY store_code, store_name, department_code, department_name,
           area_code, area_name, category_code, category_name
),
areas AS (
  SELECT 'areas' AS dimension_type, store_code, store_name,
         area_code AS dimension_code, area_name AS dimension_name,
         NULL::text AS department_code, NULL::text AS department_name,
         NULL::text AS area_code, NULL::text AS area_name,
         NULL::text AS category_code, NULL::text AS category_name,
         NULL::text AS brand_code, NULL::text AS brand_name,
         SUM(sales_current) AS sales_current, SUM(profit_current) AS profit_current,
         SUM(sales_prior) AS sales_prior, SUM(profit_prior) AS profit_prior,
         COUNT(DISTINCT ticket_current) AS ticket_count_current,
         COUNT(DISTINCT ticket_prior) AS ticket_count_prior
  FROM base GROUP BY store_code, store_name, area_code, area_name
),
categories AS (
  SELECT 'categories' AS dimension_type, store_code, store_name,
         category_code AS dimension_code, category_name AS dimension_name,
         NULL::text AS department_code, NULL::text AS department_name,
         NULL::text AS area_code, NULL::text AS area_name,
         NULL::text AS category_code, NULL::text AS category_name,
         NULL::text AS brand_code, NULL::text AS brand_name,
         SUM(sales_current) AS sales_current, SUM(profit_current) AS profit_current,
         SUM(sales_prior) AS sales_prior, SUM(profit_prior) AS profit_prior,
         COUNT(DISTINCT ticket_current) AS ticket_count_current,
         COUNT(DISTINCT ticket_prior) AS ticket_count_prior
  FROM base GROUP BY store_code, store_name, category_code, category_name
),
groups AS (
  SELECT 'groups' AS dimension_type, store_code, store_name,
         group_code AS dimension_code, group_name AS dimension_name,
         department_code, department_name,
         area_code, area_name,
         category_code, category_name,
         NULL::text AS brand_code, NULL::text AS brand_name,
         SUM(sales_current) AS sales_current, SUM(profit_current) AS profit_current,
         SUM(sales_prior) AS sales_prior, SUM(profit_prior) AS profit_prior,
         COUNT(DISTINCT ticket_current) AS ticket_count_current,
         COUNT(DISTINCT ticket_prior) AS ticket_count_prior
  FROM base
  GROUP BY store_code, store_name, department_code, department_name,
           area_code, area_name, category_code, category_name,
           group_code, group_name
),
special_sales AS (
  SELECT 'special_sales' AS dimension_type,
         store_code,
         store_name,
         group_code AS dimension_code,
         group_name AS dimension_name,
         department_code,
         department_name,
         NULL::text AS area_code, NULL::text AS area_name,
         NULL::text AS category_code, NULL::text AS category_name,
         brand_code,
         brand_name,
         SUM(sales_current) AS sales_current,
         SUM(profit_current) AS profit_current,
         SUM(sales_prior) AS sales_prior,
         SUM(profit_prior) AS profit_prior,
         COUNT(DISTINCT ticket_current) AS ticket_count_current,
         COUNT(DISTINCT ticket_prior) AS ticket_count_prior
  FROM enriched_sales
  WHERE floor_code = '16'
  GROUP BY
    store_code, store_name, group_code, group_name,
    department_code, department_name, brand_code, brand_name
),
floors AS (
  SELECT 'floors' AS dimension_type, store_code, store_name,
         floor_code AS dimension_code, floor_name AS dimension_name,
         NULL::text AS department_code, NULL::text AS department_name,
         NULL::text AS area_code, NULL::text AS area_name,
         NULL::text AS category_code, NULL::text AS category_name,
         NULL::text AS brand_code, NULL::text AS brand_name,
         SUM(sales_current) AS sales_current, SUM(profit_current) AS profit_current,
         SUM(sales_prior) AS sales_prior, SUM(profit_prior) AS profit_prior,
         COUNT(DISTINCT ticket_current) AS ticket_count_current,
         COUNT(DISTINCT ticket_prior) AS ticket_count_prior
  FROM base GROUP BY store_code, store_name, floor_code, floor_name
),
hierarchy_area_totals AS (
  SELECT 'hierarchy_area_totals' AS dimension_type, store_code, store_name,
         area_code AS dimension_code, area_name AS dimension_name,
         department_code, department_name, area_code, area_name,
         NULL::text AS category_code, NULL::text AS category_name,
         NULL::text AS brand_code, NULL::text AS brand_name,
         0::numeric AS sales_current, 0::numeric AS profit_current,
         0::numeric AS sales_prior, 0::numeric AS profit_prior,
         COUNT(DISTINCT ticket_current) AS ticket_count_current,
         COUNT(DISTINCT ticket_prior) AS ticket_count_prior
  FROM base
  GROUP BY store_code, store_name, department_code, department_name,
           area_code, area_name
),
overall_ticket_totals AS (
  SELECT
    COUNT(DISTINCT (store_code, ticket_current))
      FILTER (WHERE ticket_current IS NOT NULL) AS ticket_count_current,
    COUNT(DISTINCT (store_code, ticket_prior))
      FILTER (WHERE ticket_prior IS NOT NULL) AS ticket_count_prior
  FROM base
),
special_ticket_totals AS (
  SELECT
    COUNT(DISTINCT (store_code, ticket_current))
      FILTER (WHERE ticket_current IS NOT NULL) AS ticket_count_current,
    COUNT(DISTINCT (store_code, ticket_prior))
      FILTER (WHERE ticket_prior IS NOT NULL) AS ticket_count_prior
  FROM enriched_sales
  WHERE floor_code = '16'
),
dimension_totals AS (
  SELECT 'dimension_totals' AS dimension_type,
         NULL::text AS store_code, NULL::text AS store_name,
         target.dimension_key AS dimension_code,
         '来客数合计'::text AS dimension_name,
         NULL::text AS department_code, NULL::text AS department_name,
         NULL::text AS area_code, NULL::text AS area_name,
         NULL::text AS category_code, NULL::text AS category_name,
         NULL::text AS brand_code, NULL::text AS brand_name,
         0::numeric AS sales_current, 0::numeric AS profit_current,
         0::numeric AS sales_prior, 0::numeric AS profit_prior,
         totals.ticket_count_current,
         totals.ticket_count_prior
  FROM overall_ticket_totals totals
  CROSS JOIN (
    VALUES
      ('stores'::text),
      ('departments'::text),
      ('department_categories'::text),
      ('areas'::text),
      ('categories'::text),
      ('groups'::text),
      ('floors'::text)
  ) AS target(dimension_key)
  UNION ALL
  SELECT 'dimension_totals', NULL::text, NULL::text,
         'special_sales', '来客数合计',
         NULL::text, NULL::text, NULL::text, NULL::text,
         NULL::text, NULL::text, NULL::text, NULL::text,
         0::numeric, 0::numeric, 0::numeric, 0::numeric,
         ticket_count_current, ticket_count_prior
  FROM special_ticket_totals
),
quality AS (
  SELECT 'quality' AS dimension_type, NULL::text AS store_code, NULL::text AS store_name,
         'unmatched_area_category' AS dimension_code,
         '未匹配区域品类' AS dimension_name,
         NULL::text AS department_code, NULL::text AS department_name,
         NULL::text AS area_code, NULL::text AS area_name,
         NULL::text AS category_code, NULL::text AS category_name,
         NULL::text AS brand_code, NULL::text AS brand_name,
         COALESCE(SUM(sales_current), 0) AS sales_current,
         COUNT(DISTINCT (store_code, group_code))::numeric AS profit_current,
         COALESCE(SUM(sales_prior), 0) AS sales_prior,
         0::numeric AS profit_prior,
         0::bigint AS ticket_count_current,
         0::bigint AS ticket_count_prior
  FROM base
  WHERE category_code IS NULL
  UNION ALL
  SELECT 'quality', NULL::text, NULL::text,
         'unmatched_floor', '未匹配楼层',
         NULL::text, NULL::text, NULL::text, NULL::text, NULL::text, NULL::text,
         NULL::text, NULL::text,
         COALESCE(SUM(sales_current), 0),
         COUNT(DISTINCT (store_code, group_code))::numeric,
         COALESCE(SUM(sales_prior), 0), 0::numeric,
         0::bigint, 0::bigint
  FROM base
  WHERE floor_name = '未匹配'
)
SELECT * FROM stores
UNION ALL SELECT * FROM departments
UNION ALL SELECT * FROM department_categories
UNION ALL SELECT * FROM areas
UNION ALL SELECT * FROM categories
UNION ALL SELECT * FROM groups
UNION ALL SELECT * FROM special_sales
UNION ALL SELECT * FROM floors
UNION ALL SELECT * FROM hierarchy_area_totals
UNION ALL SELECT * FROM dimension_totals
UNION ALL SELECT * FROM quality
ORDER BY dimension_type, store_code, dimension_code, brand_code
"""
    return sql, params


def _row_dict(row: Mapping[str, Any] | Any) -> dict[str, Any]:
    if isinstance(row, Mapping):
        return dict(row)
    return {key: row[key] for key in row.keys()}


def _combined_metrics(
    rows: Iterable[Mapping[str, Any]],
    *,
    ticket_count_current: Any | None = None,
    ticket_count_prior: Any | None = None,
) -> dict[str, float | None]:
    items = list(rows)
    current_tickets = (
        sum(_number(row["metrics"].get("ticket_count_current")) for row in items)
        if ticket_count_current is None
        else ticket_count_current
    )
    prior_tickets = (
        sum(_number(row["metrics"].get("ticket_count_prior")) for row in items)
        if ticket_count_prior is None
        else ticket_count_prior
    )
    return metric_triplet(
        sum(_number(row["metrics"].get("sales_current")) for row in items),
        sum(_number(row["metrics"].get("profit_current")) for row in items),
        sum(_number(row["metrics"].get("sales_prior")) for row in items),
        sum(_number(row["metrics"].get("profit_prior")) for row in items),
        current_tickets,
        prior_tickets,
    )


def _department_category_sort_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        str(row.get("store_code") or ""),
        department_display_sort_key(
            {
                "department_code": row.get("department_code"),
                "department_name": row.get("department_name"),
            }
        ),
        str(row.get("department_code") or ""),
        str(row.get("area_code") or ""),
        str(row.get("area_name") or ""),
        str(row.get("category_code") or ""),
        str(row.get("category_name") or ""),
    )


def _build_department_category_hierarchy(
    rows: Iterable[Mapping[str, Any]],
    *,
    area_ticket_counts: Mapping[tuple[Any, ...], tuple[int, int]] | None = None,
    department_ticket_counts: Mapping[tuple[Any, ...], tuple[int, int]] | None = None,
) -> list[dict[str, Any]]:
    detail_rows = [dict(row) for row in sorted(rows, key=_department_category_sort_key)]
    result: list[dict[str, Any]] = []
    area_counts = area_ticket_counts or {}
    department_counts = department_ticket_counts or {}

    def department_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
        return (
            row.get("store_code"),
            row.get("store_name"),
            row.get("department_code"),
            row.get("department_name"),
        )

    def area_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
        return row.get("area_code"), row.get("area_name")

    for _, department_group in groupby(detail_rows, key=department_key):
        department_rows = list(department_group)
        for _, area_group in groupby(department_rows, key=area_key):
            area_rows = list(area_group)
            for row in area_rows:
                row["row_type"] = "category"
                result.append(row)
            area_first = area_rows[0]
            area_count = area_counts.get(
                (
                    area_first.get("store_code"),
                    area_first.get("department_code"),
                    area_first.get("area_code"),
                )
            )
            result.append(
                {
                    "store_code": area_first.get("store_code"),
                    "store_name": area_first.get("store_name"),
                    "department_code": area_first.get("department_code"),
                    "department_name": area_first.get("department_name"),
                    "area_code": area_first.get("area_code"),
                    "area_name": area_first.get("area_name"),
                    "category_code": None,
                    "category_name": None,
                    "dimension_code": area_first.get("area_code"),
                    "dimension_name": f"{area_first.get('area_name') or '未匹配'}小计",
                    "row_type": "area_subtotal",
                    "metrics": _combined_metrics(
                        area_rows,
                        ticket_count_current=area_count[0] if area_count else None,
                        ticket_count_prior=area_count[1] if area_count else None,
                    ),
                }
            )
        department_first = department_rows[0]
        department_count = department_counts.get(
            (
                department_first.get("store_code"),
                department_first.get("department_code"),
            )
        )
        result.append(
            {
                "store_code": department_first.get("store_code"),
                "store_name": department_first.get("store_name"),
                "department_code": department_first.get("department_code"),
                "department_name": department_first.get("department_name"),
                "area_code": None,
                "area_name": None,
                "category_code": None,
                "category_name": None,
                "dimension_code": department_first.get("department_code"),
                "dimension_name": f"{department_first.get('department_name') or '未匹配'}小计",
                "row_type": "department_subtotal",
                "metrics": _combined_metrics(
                    department_rows,
                    ticket_count_current=(
                        department_count[0] if department_count else None
                    ),
                    ticket_count_prior=(
                        department_count[1] if department_count else None
                    ),
                ),
            }
        )
    return result


def normalize_rows(
    rows: Iterable[Mapping[str, Any] | Any],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, int | float]]:
    """Group database rows by dimension and attach derived metric triplets."""
    dimensions: dict[str, list[dict[str, Any]]] = {
        dimension_type: [] for dimension_type in DIMENSION_TYPES
    }
    quality: dict[str, int | float] = {
        "unmatched_area_category_group_count": 0,
        "unmatched_floor_group_count": 0,
        "unmatched_area_category_sales_current": 0.0,
        "unmatched_floor_sales_current": 0.0,
    }
    area_ticket_counts: dict[tuple[Any, ...], tuple[int, int]] = {}
    for source_row in rows:
        row = _row_dict(source_row)
        dimension_type = str(row["dimension_type"])
        if dimension_type == "hierarchy_area_totals":
            area_ticket_counts[
                (
                    row.get("store_code"),
                    row.get("department_code"),
                    row.get("area_code"),
                )
            ] = (
                int(_number(row.get("ticket_count_current"))),
                int(_number(row.get("ticket_count_prior"))),
            )
            continue
        if dimension_type == "dimension_totals":
            continue
        if dimension_type == "quality":
            code = row.get("dimension_code")
            if code == "unmatched_area_category":
                quality["unmatched_area_category_group_count"] = int(
                    _number(row.get("profit_current"))
                )
                quality["unmatched_area_category_sales_current"] = _number(
                    row.get("sales_current")
                )
            elif code == "unmatched_floor":
                quality["unmatched_floor_group_count"] = int(
                    _number(row.get("profit_current"))
                )
                quality["unmatched_floor_sales_current"] = _number(
                    row.get("sales_current")
                )
            continue
        if dimension_type not in dimensions:
            continue
        normalized = {
            "store_code": row.get("store_code"),
            "store_name": row.get("store_name"),
            "dimension_code": row.get("dimension_code"),
            "dimension_name": row.get("dimension_name"),
            "metrics": metric_triplet(
                row.get("sales_current"),
                row.get("profit_current"),
                row.get("sales_prior"),
                row.get("profit_prior"),
                row.get("ticket_count_current"),
                row.get("ticket_count_prior"),
            ),
        }
        if dimension_type in ("department_categories", "groups", "special_sales"):
            normalized.update(
                {
                    "department_code": row.get("department_code"),
                    "department_name": row.get("department_name"),
                }
            )
        if dimension_type in ("department_categories", "groups"):
            normalized.update(
                {
                    "area_code": row.get("area_code"),
                    "area_name": row.get("area_name"),
                    "category_code": row.get("category_code"),
                    "category_name": row.get("category_name"),
                }
            )
        if dimension_type == "special_sales":
            normalized.update(
                {
                    "brand_code": row.get("brand_code"),
                    "brand_name": row.get("brand_name"),
                }
            )
        dimensions[dimension_type].append(normalized)
    dimensions["departments"].sort(
        key=lambda row: (
            str(row.get("store_code") or ""),
            department_display_sort_key(
                {
                    "department_code": row.get("dimension_code"),
                    "department_name": row.get("dimension_name"),
                }
            ),
        )
    )
    department_ticket_counts = {
        (row.get("store_code"), row.get("dimension_code")): (
            int(_number(row["metrics"].get("ticket_count_current"))),
            int(_number(row["metrics"].get("ticket_count_prior"))),
        )
        for row in dimensions["departments"]
    }
    dimensions["department_categories"] = _build_department_category_hierarchy(
        dimensions["department_categories"],
        area_ticket_counts=area_ticket_counts,
        department_ticket_counts=department_ticket_counts,
    )
    dimensions["special_sales"].sort(
        key=lambda row: (
            str(row.get("store_code") or ""),
            department_display_sort_key(
                {
                    "department_code": row.get("department_code"),
                    "department_name": row.get("department_name"),
                }
            ),
            str(row.get("dimension_code") or ""),
            str(row.get("brand_code") or ""),
        )
    )
    return dimensions, quality


def build_report_payload(
    rows: Iterable[Mapping[str, Any] | Any],
    *,
    start_date: date,
    end_date: date,
    prior_start_date: date,
    prior_end_date: date,
    selected_store: str | None = None,
) -> dict[str, Any]:
    dimensions, quality = normalize_rows(rows)
    return {
        "period": {"start_date": start_date, "end_date": end_date},
        "prior_period": {
            "start_date": prior_start_date,
            "end_date": prior_end_date,
        },
        "selected_store": selected_store,
        "dimensions": dimensions,
        "quality": quality,
    }


def load_od0002_report(
    db: Any,
    scope_filter_sql: TrustedScopeSql,
    scope_params: Mapping[str, Any],
    *,
    start_date: date,
    end_date: date,
    prior_start_date: date,
    prior_end_date: date,
    selected_store: str | None = None,
    selected_department: str | None = None,
) -> dict[str, Any]:
    """Execute the bound OD0002 query and assemble its API payload."""
    sql, params = build_report_query(
        start_date,
        end_date,
        prior_start_date,
        prior_end_date,
        scope_filter_sql,
        scope_params,
        selected_store,
        selected_department,
    )
    db.execute(
        text(f"SET LOCAL statement_timeout = '{OD0002_QUERY_TIMEOUT_SECONDS}s'"),
        {},
    )
    rows = list(db.execute(text(sql), params).mappings().all())
    dimension_ticket_totals = {
        str(row.get("dimension_code")): (
            int(_number(row.get("ticket_count_current"))),
            int(_number(row.get("ticket_count_prior"))),
        )
        for row in rows
        if str(row.get("dimension_type")) == "dimension_totals"
    }
    dimensions, quality = normalize_rows(rows)
    totals: dict[str, dict[str, float | None]] = {}
    for dimension_type, dimension_rows in dimensions.items():
        total_rows = (
            [row for row in dimension_rows if row.get("row_type") == "category"]
            if dimension_type == "department_categories"
            else dimension_rows
        )
        sales_current = sum(row["metrics"]["sales_current"] for row in total_rows)
        profit_current = sum(row["metrics"]["profit_current"] for row in total_rows)
        sales_prior = sum(row["metrics"]["sales_prior"] for row in total_rows)
        profit_prior = sum(row["metrics"]["profit_prior"] for row in total_rows)
        fallback_ticket_current = sum(
            _number(row["metrics"].get("ticket_count_current")) for row in total_rows
        )
        fallback_ticket_prior = sum(
            _number(row["metrics"].get("ticket_count_prior")) for row in total_rows
        )
        ticket_total = dimension_ticket_totals.get(
            dimension_type,
            (int(fallback_ticket_current), int(fallback_ticket_prior)),
        )
        total = metric_triplet(
            sales_current,
            profit_current,
            sales_prior,
            profit_prior,
            ticket_total[0],
            ticket_total[1],
        )
        totals[dimension_type] = total
        for row in dimension_rows:
            row["total"] = total

    return {
        "dates": {
            "start_date": start_date,
            "end_date": end_date,
            "prior_start_date": prior_start_date,
            "prior_end_date": prior_end_date,
        },
        "selected_store": selected_store,
        "dimensions": dimensions,
        "totals": totals,
        "quality": quality,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
