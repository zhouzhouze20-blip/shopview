from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from .od0002_report import (
    EXCLUDED_DEPARTMENT_CODES,
    TrustedScopeSql,
    _trusted_scope_value,
)


NUMERIC_FIELDS = (
    "area",
    "quantity",
    "sales_amount",
    "tax_cost",
    "profit",
    "member_sales",
    "stored_card_sales",
)
TOTAL_FIELDS = (
    "quantity",
    "sales_amount",
    "tax_cost",
    "profit",
    "ticket_count",
    "member_sales",
    "stored_card_sales",
)
CODE_FIELDS = (
    "store_code",
    "department_code",
    "group_code",
    "floor_code",
    "level1_code",
    "level2_code",
)
DISPLAY_FIELDS = (
    "store_name",
    "department_name",
    "group_name",
    "level1_name",
    "level2_name",
    "grade_label",
)


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def build_report_query(
    start_date: date,
    end_date: date,
    scope_filter_sql: str | TrustedScopeSql,
    scope_params: Mapping[str, Any],
    selected_store: str | None = None,
    selected_department: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Build the single permission-scoped HDYY01 report statement."""
    scope_sql = _trusted_scope_value(scope_filter_sql)
    params = dict(scope_params)
    params.update(
        {
            "start_date": start_date,
            "end_date": end_date,
            "excluded_department_codes": sorted(EXCLUDED_DEPARTMENT_CODES),
        }
    )

    normalized_store = _clean_optional(selected_store)
    selected_store_sql = ""
    if normalized_store is not None:
        params["selected_store"] = normalized_store
        selected_store_sql = " AND s.sglmarket::text = :selected_store"

    normalized_department = _clean_optional(selected_department)
    selected_department_sql = ""
    if normalized_department is not None:
        params["selected_department"] = normalized_department
        selected_department_sql = (
            " AND UPPER(TRIM(BOTH FROM COALESCE(dept.mfcode, ''))) "
            "= UPPER(:selected_department)"
        )

    sql = f"""
WITH manaframe_normalized AS MATERIALIZED (
  SELECT
    source.*,
    NULLIF(UPPER(TRIM(BOTH FROM COALESCE(source.mfcode, ''))), '')
      AS normalized_mfcode,
    COUNT(*) OVER (
      PARTITION BY NULLIF(
        UPPER(TRIM(BOTH FROM COALESCE(source.mfcode, ''))), ''
      )
    ) AS normalized_match_count
  FROM manaframe source
),
manaframe_unique AS MATERIALIZED (
  SELECT *
  FROM manaframe_normalized
  WHERE normalized_match_count = 1
),
stores_normalized AS MATERIALIZED (
  SELECT
    source.*,
    NULLIF(TRIM(BOTH FROM COALESCE(source.store_code, '')), '')
      AS normalized_store_code,
    COUNT(*) OVER (
      PARTITION BY NULLIF(
        TRIM(BOTH FROM COALESCE(source.store_code, '')), ''
      )
    ) AS normalized_match_count
  FROM stores source
  WHERE source.is_active IS TRUE
),
stores_unique AS MATERIALIZED (
  SELECT *
  FROM stores_normalized
  WHERE normalized_match_count = 1
),
hierarchy_normalized AS MATERIALIZED (
  SELECT
    source.*,
    NULLIF(UPPER(TRIM(BOTH FROM COALESCE(source.level3_code, ''))), '')
      AS normalized_level3_code,
    COUNT(*) OVER (
      PARTITION BY NULLIF(
        UPPER(TRIM(BOTH FROM COALESCE(source.level3_code, ''))), ''
      )
    ) AS normalized_match_count
  FROM mana_brand_hierarchy source
),
hierarchy_unique AS MATERIALIZED (
  SELECT *
  FROM hierarchy_normalized
  WHERE normalized_match_count = 1
),
base_sales AS MATERIALIZED (
  SELECT
    s.sglmarket,
    s.sglhsrq,
    s.sglbillno,
    s.sglsl,
    s.sglxssr,
    s.sgln13,
    s.sgln14,
    s.sglsupzk,
    s.sgln2,
    s.sglfcard,
    st.store_name,
    NULLIF(TRIM(BOTH FROM s.sglmfid), '') AS group_code,
    NULLIF(TRIM(BOTH FROM mf.mfcname), '') AS group_name,
    NULLIF(TRIM(BOTH FROM dept.mfcode), '') AS department_code,
    NULLIF(TRIM(BOTH FROM dept.mfcname), '') AS department_name,
    mf.mfyymj AS area,
    NULLIF(TRIM(BOTH FROM mf.mflc), '') AS floor_code,
    h.level1_code,
    h.level1_name,
    h.level2_code,
    h.level2_name,
    h.grade_label
  FROM salegoodslist s
  LEFT JOIN manaframe_unique mf
    ON NULLIF(UPPER(TRIM(BOTH FROM COALESCE(s.sglmfid, ''))), '')
       = mf.normalized_mfcode
  LEFT JOIN manaframe_unique dept
    ON NULLIF(UPPER(TRIM(BOTH FROM COALESCE(mf.mfpcode, ''))), '')
       = dept.normalized_mfcode
  LEFT JOIN stores_unique st
    ON s.sglmarket::text = st.normalized_store_code
  LEFT JOIN hierarchy_unique h
    ON NULLIF(UPPER(TRIM(BOTH FROM COALESCE(mf.mfchr2, ''))), '')
       = h.normalized_level3_code
  WHERE s.sglhsrq BETWEEN :start_date AND :end_date
    AND (s.sglwmid IS NULL OR s.sglwmid <> '5')
    AND TRIM(BOTH FROM COALESCE(dept.mfcode, '')) <> ALL(:excluded_department_codes)
    {scope_sql}
    {selected_store_sql}
    {selected_department_sql}
),
ticket_sales AS (
  SELECT
    sglmarket::text AS store_code,
    group_code,
    sglhsrq,
    sglbillno,
    SUM(COALESCE(sglxssr, 0)) AS ticket_sales
  FROM base_sales
  GROUP BY sglmarket::text, group_code, sglhsrq, sglbillno
),
ticket_counts AS (
  SELECT
    store_code,
    group_code,
    COUNT(*) FILTER (WHERE ticket_sales > 0) AS ticket_count
  FROM ticket_sales
  GROUP BY store_code, group_code
),
scoped_ticket_keys AS (
  SELECT DISTINCT sglmarket::text AS store_code, sglbillno
  FROM base_sales
),
member_tickets AS (
  SELECT DISTINCT h.billno, TRIM(BOTH FROM h.mkt) AS store_code
  FROM salehead h
  JOIN scoped_ticket_keys s
    ON h.billno = s.sglbillno
   AND TRIM(BOTH FROM h.mkt) = s.store_code
  WHERE h.rqsj >= :start_date
    AND h.rqsj < :end_date + INTERVAL '1 day'
    AND NULLIF(TRIM(BOTH FROM COALESCE(h.hykh, '')), '') IS NOT NULL
),
unmatched_member_tickets AS (
  -- A salehead ticket absent from the scoped facts cannot be attributed to a
  -- permitted group safely. Reporting zero avoids scanning or disclosing
  -- tickets belonging to groups outside the caller's data scope.
  SELECT 0::bigint AS unmatched_member_ticket_count
),
group_metrics AS (
  SELECT
    s.sglmarket::text AS store_code,
    MAX(s.store_name) AS store_name,
    s.department_code,
    MAX(s.department_name) AS department_name,
    s.group_code,
    MAX(s.group_name) AS group_name,
    MAX(s.area) AS area,
    MAX(s.floor_code) AS floor_code,
    MAX(s.level1_code) AS level1_code,
    MAX(s.level1_name) AS level1_name,
    MAX(s.level2_code) AS level2_code,
    MAX(s.level2_name) AS level2_name,
    MAX(s.grade_label) AS grade_label,
    SUM(COALESCE(s.sglsl, 0)) AS quantity,
    SUM(COALESCE(s.sglxssr, 0)) AS sales_amount,
    SUM(COALESCE(s.sgln13, 0) + COALESCE(s.sgln14, 0) - COALESCE(s.sglsupzk, 0)) AS tax_cost,
    SUM(COALESCE(s.sgln2, 0)) AS profit,
    SUM(
      CASE WHEN mt.billno IS NOT NULL
           THEN COALESCE(s.sglxssr, 0)
           ELSE 0 END
    ) AS member_sales,
    SUM(COALESCE(s.sglfcard, 0)) AS stored_card_sales
  FROM base_sales s
  LEFT JOIN member_tickets mt
    ON mt.billno = s.sglbillno
   AND mt.store_code = s.sglmarket::text
  GROUP BY 1, 3, 5
)
SELECT
  gm.*,
  COALESCE(tc.ticket_count, 0) AS ticket_count,
  (SELECT unmatched_member_ticket_count FROM unmatched_member_tickets)
    AS unmatched_member_ticket_count
FROM group_metrics gm
LEFT JOIN ticket_counts tc
  ON tc.store_code = gm.store_code
 AND tc.group_code IS NOT DISTINCT FROM gm.group_code
ORDER BY gm.store_code, gm.department_code, gm.group_code
"""
    return sql, params


def _row_dict(row: Mapping[str, Any] | Any) -> dict[str, Any]:
    if isinstance(row, Mapping):
        return dict(row)
    return {key: row[key] for key in row.keys()}


def _number(value: Any) -> float:
    return float(value or Decimal("0"))


def _missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def normalize_row(row: Mapping[str, Any] | Any) -> dict[str, Any]:
    """Normalize one database mapping without collapsing its group grain."""
    item = _row_dict(row)
    for key in CODE_FIELDS:
        if _missing(item.get(key)):
            item[key] = None
        elif isinstance(item[key], str):
            item[key] = item[key].strip()

    for key in DISPLAY_FIELDS:
        item[key] = "未匹配" if _missing(item.get(key)) else item[key]

    for key in NUMERIC_FIELDS:
        item[key] = _number(item.get(key))

    item["ticket_count"] = int(item.get("ticket_count") or 0)
    item["unmatched_member_ticket_count"] = int(
        item.get("unmatched_member_ticket_count") or 0
    )
    item["average_ticket"] = (
        item["sales_amount"] / item["ticket_count"]
        if item["ticket_count"]
        else None
    )
    return item


def _organization_unmatched(row: Mapping[str, Any]) -> bool:
    return any(
        _missing(row.get(key)) or row.get(key) == "未匹配"
        for key in (
            "store_name",
            "department_code",
            "department_name",
            "group_code",
            "group_name",
        )
    )


def build_report_payload(
    rows: Iterable[Mapping[str, Any] | Any],
    *,
    start_date: date,
    end_date: date,
    selected_store: str | None = None,
    selected_department: str | None = None,
) -> dict[str, Any]:
    normalized = [normalize_row(row) for row in rows]
    total = {
        key: (
            sum((row[key] for row in normalized), 0)
            if key == "ticket_count"
            else sum((row[key] for row in normalized), 0.0)
        )
        for key in TOTAL_FIELDS
    }
    total["average_ticket"] = (
        total["sales_amount"] / total["ticket_count"]
        if total["ticket_count"]
        else None
    )

    unmatched_organization = [
        row for row in normalized if _organization_unmatched(row)
    ]
    unmatched_hierarchy = [
        row
        for row in normalized
        if any(
            not row.get(key) or row.get(key) == "未匹配"
            for key in (
                "level1_code",
                "level1_name",
                "level2_code",
                "level2_name",
            )
        )
    ]
    missing_grade = [
        row for row in normalized if row.get("grade_label") == "未匹配"
    ]
    quality = {
        "unmatched_organization_group_count": len(unmatched_organization),
        "unmatched_organization_amount": sum(
            (row["sales_amount"] for row in unmatched_organization), 0.0
        ),
        "unmatched_hierarchy_group_count": len(unmatched_hierarchy),
        "unmatched_hierarchy_amount": sum(
            (row["sales_amount"] for row in unmatched_hierarchy), 0.0
        ),
        "missing_grade_group_count": len(missing_grade),
        "missing_grade_amount": sum(
            (row["sales_amount"] for row in missing_grade), 0.0
        ),
        "unmatched_member_ticket_count": max(
            (
                int(row.get("unmatched_member_ticket_count") or 0)
                for row in normalized
            ),
            default=0,
        ),
    }

    return {
        "dates": {"start_date": start_date, "end_date": end_date},
        "selected_store": _clean_optional(selected_store),
        "selected_department": _clean_optional(selected_department),
        "rows": normalized,
        "total": total,
        "quality": quality,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def load_hdyy01_report(
    db: Any,
    scope_filter_sql: str | TrustedScopeSql,
    scope_params: Mapping[str, Any],
    *,
    start_date: date,
    end_date: date,
    selected_store: str | None = None,
    selected_department: str | None = None,
) -> dict[str, Any]:
    """Execute one bound query and build the HDYY01 response payload."""
    sql, params = build_report_query(
        start_date,
        end_date,
        scope_filter_sql,
        scope_params,
        selected_store,
        selected_department,
    )
    rows = db.execute(text(sql), params).mappings().all()
    return build_report_payload(
        rows,
        start_date=start_date,
        end_date=end_date,
        selected_store=_clean_optional(selected_store),
        selected_department=_clean_optional(selected_department),
    )
