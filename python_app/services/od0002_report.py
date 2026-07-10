from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from collections.abc import Iterable, Mapping
from typing import Any

from sqlalchemy import text


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
) -> dict[str, float | None]:
    sc, pc, sp, pp = map(
        _number, (sales_current, profit_current, sales_prior, profit_prior)
    )
    margin_current = _ratio(pc, sc)
    margin_prior = _ratio(pp, sp)
    margin_change = (
        round(margin_current - margin_prior, 12)
        if margin_current is not None and margin_prior is not None
        else None
    )
    return {
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
    "areas",
    "categories",
    "groups",
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


def build_report_query(
    start_date: date,
    end_date: date,
    prior_start_date: date,
    prior_end_date: date,
    scope_filter_sql: str | TrustedScopeSql,
    scope_params: Mapping[str, Any],
    selected_store: str | None = None,
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
    selected_store_sql = ""
    if selected_store is not None:
        params["selected_store"] = selected_store
        selected_store_sql = " AND s.sglmarket::text = :selected_store"

    floor_cases = "\n".join(
        f"WHEN '{code}' THEN '{name}'" for code, name in FLOOR_NAMES.items()
    )
    sql = f"""
WITH filtered_sales AS (
  -- Apply the selective date predicate before normalized ERP dimension joins.
  SELECT s.*
  FROM salegoodslist s
  WHERE (
       s.sglhsrq BETWEEN :start_date AND :end_date
       OR s.sglhsrq BETWEEN :prior_start_date AND :prior_end_date
  )
    AND (s.sglwmid IS NULL OR s.sglwmid <> '5')
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
base AS (
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
    SUM(CASE WHEN s.sglhsrq BETWEEN :start_date AND :end_date
             THEN COALESCE(s.sglxssr, 0) ELSE 0 END) AS sales_current,
    SUM(CASE WHEN s.sglhsrq BETWEEN :start_date AND :end_date
             THEN COALESCE(s.sgln2, 0) ELSE 0 END) AS profit_current,
    SUM(CASE WHEN s.sglhsrq BETWEEN :prior_start_date AND :prior_end_date
             THEN COALESCE(s.sglxssr, 0) ELSE 0 END) AS sales_prior,
    SUM(CASE WHEN s.sglhsrq BETWEEN :prior_start_date AND :prior_end_date
             THEN COALESCE(s.sgln2, 0) ELSE 0 END) AS profit_prior
  FROM filtered_sales s
  JOIN manaframe mf
    ON UPPER(TRIM(COALESCE(s.sglmfid, ''))) = UPPER(TRIM(COALESCE(mf.mfcode, '')))
  LEFT JOIN manaframe dept
    ON UPPER(TRIM(COALESCE(mf.mfpcode, ''))) = UPPER(TRIM(COALESCE(dept.mfcode, '')))
  LEFT JOIN area_category_dedup ac
    ON UPPER(TRIM(COALESCE(mf.mfchr1, ''))) = ac.normalized_category_code
  LEFT JOIN stores st
    ON TRIM(BOTH FROM COALESCE(st.store_code, '')) = s.sglmarket::text
  WHERE TRIM(BOTH FROM COALESCE(mf.mflc, '')) <> '00'
    AND TRIM(BOTH FROM COALESCE(dept.mfcode, '')) <> ALL(:excluded_department_codes)
    AND TRIM(BOTH FROM COALESCE(ac.area_name, '')) <> '其他类别区域'
    {scope_sql}
    {selected_store_sql}
  GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12
),
stores AS (
  SELECT 'stores' AS dimension_type, store_code, store_name,
         store_code AS dimension_code, store_name AS dimension_name,
         SUM(sales_current) AS sales_current, SUM(profit_current) AS profit_current,
         SUM(sales_prior) AS sales_prior, SUM(profit_prior) AS profit_prior
  FROM base GROUP BY store_code, store_name
),
departments AS (
  SELECT 'departments' AS dimension_type, store_code, store_name,
         department_code AS dimension_code, department_name AS dimension_name,
         SUM(sales_current) AS sales_current, SUM(profit_current) AS profit_current,
         SUM(sales_prior) AS sales_prior, SUM(profit_prior) AS profit_prior
  FROM base GROUP BY store_code, store_name, department_code, department_name
),
areas AS (
  SELECT 'areas' AS dimension_type, store_code, store_name,
         area_code AS dimension_code, area_name AS dimension_name,
         SUM(sales_current) AS sales_current, SUM(profit_current) AS profit_current,
         SUM(sales_prior) AS sales_prior, SUM(profit_prior) AS profit_prior
  FROM base GROUP BY store_code, store_name, area_code, area_name
),
categories AS (
  SELECT 'categories' AS dimension_type, store_code, store_name,
         category_code AS dimension_code, category_name AS dimension_name,
         SUM(sales_current) AS sales_current, SUM(profit_current) AS profit_current,
         SUM(sales_prior) AS sales_prior, SUM(profit_prior) AS profit_prior
  FROM base GROUP BY store_code, store_name, category_code, category_name
),
groups AS (
  SELECT 'groups' AS dimension_type, store_code, store_name,
         group_code AS dimension_code, group_name AS dimension_name,
         SUM(sales_current) AS sales_current, SUM(profit_current) AS profit_current,
         SUM(sales_prior) AS sales_prior, SUM(profit_prior) AS profit_prior
  FROM base GROUP BY store_code, store_name, group_code, group_name
),
floors AS (
  SELECT 'floors' AS dimension_type, store_code, store_name,
         floor_code AS dimension_code, floor_name AS dimension_name,
         SUM(sales_current) AS sales_current, SUM(profit_current) AS profit_current,
         SUM(sales_prior) AS sales_prior, SUM(profit_prior) AS profit_prior
  FROM base GROUP BY store_code, store_name, floor_code, floor_name
),
quality AS (
  SELECT 'quality' AS dimension_type, NULL::text AS store_code, NULL::text AS store_name,
         'unmatched_area_category' AS dimension_code,
         '未匹配区域品类' AS dimension_name,
         COALESCE(SUM(sales_current), 0) AS sales_current,
         COUNT(DISTINCT (store_code, group_code))::numeric AS profit_current,
         COALESCE(SUM(sales_prior), 0) AS sales_prior,
         0::numeric AS profit_prior
  FROM base
  WHERE category_code IS NULL
  UNION ALL
  SELECT 'quality', NULL::text, NULL::text,
         'unmatched_floor', '未匹配楼层',
         COALESCE(SUM(sales_current), 0),
         COUNT(DISTINCT (store_code, group_code))::numeric,
         COALESCE(SUM(sales_prior), 0), 0::numeric
  FROM base
  WHERE floor_name = '未匹配'
)
SELECT * FROM stores
UNION ALL SELECT * FROM departments
UNION ALL SELECT * FROM areas
UNION ALL SELECT * FROM categories
UNION ALL SELECT * FROM groups
UNION ALL SELECT * FROM floors
UNION ALL SELECT * FROM quality
ORDER BY dimension_type, store_code, dimension_code
"""
    return sql, params


def _row_dict(row: Mapping[str, Any] | Any) -> dict[str, Any]:
    if isinstance(row, Mapping):
        return dict(row)
    return {key: row[key] for key in row.keys()}


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
    for source_row in rows:
        row = _row_dict(source_row)
        dimension_type = str(row["dimension_type"])
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
            ),
        }
        dimensions[dimension_type].append(normalized)
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
    )
    rows = db.execute(text(sql), params).mappings().all()
    dimensions, quality = normalize_rows(rows)
    totals: dict[str, dict[str, float | None]] = {}
    for dimension_type, dimension_rows in dimensions.items():
        sales_current = sum(row["metrics"]["sales_current"] for row in dimension_rows)
        profit_current = sum(row["metrics"]["profit_current"] for row in dimension_rows)
        sales_prior = sum(row["metrics"]["sales_prior"] for row in dimension_rows)
        profit_prior = sum(row["metrics"]["profit_prior"] for row in dimension_rows)
        total = metric_triplet(sales_current, profit_current, sales_prior, profit_prior)
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
