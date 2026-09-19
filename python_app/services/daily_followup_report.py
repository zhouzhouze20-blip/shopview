from __future__ import annotations

from calendar import monthrange
from collections.abc import Iterable, Mapping
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal
from zoneinfo import ZoneInfo

from sqlalchemy import text

from services.department_display_order import department_display_sort_key
from services.od0002_report import (
    EXCLUDED_DEPARTMENT_CODES,
    OD0002_QUERY_TIMEOUT_SECONDS,
    TrustedScopeSql,
    metric_triplet,
)


DailyFollowupDimension = Literal["departments", "groups", "special_sales"]
DAILY_FOLLOWUP_DIMENSIONS = frozenset(
    {"departments", "groups", "special_sales"}
)
OPERATION_METHOD_NAMES = {
    "1": "经销",
    "2": "成本代销",
    "3": "扣率代销",
    "4": "联营",
    "5": "租赁",
}
SHOPVIEW_TIMEZONE = ZoneInfo("Asia/Shanghai")


def financial_month_period(year: int, month: int) -> tuple[date, date]:
    """Return the ShopView financial month: previous month 29th through month 28th."""
    if year < 2:
        raise ValueError("financial year must be greater than 1")
    if month < 1 or month > 12:
        raise ValueError("financial month must be between 1 and 12")
    previous_year = year - 1 if month == 1 else year
    previous_month = 12 if month == 1 else month - 1
    previous_month_last_day = monthrange(previous_year, previous_month)[1]
    start_date = (
        date(previous_year, previous_month, 29)
        if previous_month_last_day >= 29
        else date(year, month, 1)
    )
    return start_date, date(year, month, 28)


def _previous_year(value: date) -> date:
    previous_year = value.year - 1
    last_day = monthrange(previous_year, value.month)[1]
    return date(previous_year, value.month, min(value.day, last_day))


def _shopview_today() -> date:
    return datetime.now(SHOPVIEW_TIMEZONE).date()


def _trusted_scope_value(scope_filter_sql: str | TrustedScopeSql) -> str:
    value = getattr(scope_filter_sql, "value", scope_filter_sql)
    if not isinstance(value, str) or any(
        marker in value for marker in (";", "--", "/*", "*/")
    ):
        raise ValueError(
            "scope_filter_sql must be an internally generated SQL fragment "
            "without statement or comment markers"
        )
    return value


def build_daily_followup_query(
    start_date: date,
    end_date: date,
    prior_start_date: date,
    prior_end_date: date,
    dimension: DailyFollowupDimension,
    scope_filter_sql: str | TrustedScopeSql,
    scope_params: Mapping[str, Any],
    selected_store: str | None = None,
    selected_department: str | None = None,
    operation_method_source: Literal["contract", "sales"] = "contract",
) -> tuple[str, dict[str, Any]]:
    if dimension not in DAILY_FOLLOWUP_DIMENSIONS:
        raise ValueError(f"unsupported daily follow-up dimension: {dimension}")
    if operation_method_source not in {"contract", "sales"}:
        raise ValueError(
            f"unsupported operation method source: {operation_method_source}"
        )

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
    if selected_store:
        params["selected_store"] = selected_store.strip()
        selected_store_sales_sql = " AND s.sglmarket::text = :selected_store"
    selected_department_sql = ""
    if selected_department and selected_department.strip():
        params["selected_department"] = selected_department.strip()
        selected_department_sql = (
            " AND UPPER(TRIM(BOTH FROM COALESCE(dept.mfcode, ''))) "
            "= UPPER(:selected_department)"
        )

    if dimension == "departments":
        dimension_code_sql = "TRIM(BOTH FROM COALESCE(dept.mfcode, ''))"
        dimension_name_sql = (
            "COALESCE(NULLIF(TRIM(BOTH FROM dept.mfcname), ''), '未匹配')"
        )
    else:
        dimension_code_sql = "TRIM(BOTH FROM COALESCE(mf.mfcode, ''))"
        dimension_name_sql = (
            "COALESCE(NULLIF(TRIM(BOTH FROM mf.mfcname), ''), '未匹配')"
        )
    if dimension == "special_sales":
        brand_code_sql = "TRIM(BOTH FROM COALESCE(s.sglppcode, ''))"
        brand_name_sql = (
            "COALESCE(NULLIF(TRIM(BOTH FROM cb.cbcname), ''), '未匹配')"
        )
        brand_join_sql = """
LEFT JOIN codebrand cb
  ON UPPER(TRIM(COALESCE(s.sglppcode, '')))
   = UPPER(TRIM(COALESCE(cb.cbid, '')))
"""
        special_sale_filter_sql = (
            "AND TRIM(BOTH FROM COALESCE(mf.mflc, '')) = '16'"
        )
    else:
        brand_code_sql = "NULL::text"
        brand_name_sql = "NULL::text"
        brand_join_sql = ""
        special_sale_filter_sql = ""

    if operation_method_source == "sales":
        filtered_operation_method_select_sql = "    s.sglwmid,\n"
        filtered_operation_method_group_sql = ",\n    s.sglwmid"
        operation_method_code_sql = "TRIM(BOTH FROM COALESCE(s.sglwmid, ''))"
        contract_join_sql = ""
    else:
        filtered_operation_method_select_sql = ""
        filtered_operation_method_group_sql = ""
        operation_method_code_sql = "TRIM(BOTH FROM COALESCE(contract.cmwmid, ''))"
        contract_join_sql = """
LEFT JOIN LATERAL (
  SELECT cm.cmwmid
  FROM contmanaframe cmf
  JOIN contmain cm
    ON UPPER(TRIM(COALESCE(cm.cmcontno, '')))
     = UPPER(TRIM(COALESCE(cmf.cmfcontno, '')))
  WHERE UPPER(TRIM(COALESCE(cmf.cmfmfid, '')))
      = UPPER(TRIM(COALESCE(s.sglmfid, '')))
    AND TRIM(BOTH FROM COALESCE(cmf.cmfmarket, '')) = s.sglmarket::text
    AND UPPER(TRIM(COALESCE(cm.cmsupid, '')))
      = UPPER(TRIM(COALESCE(s.sglsupid, '')))
    AND TRIM(BOTH FROM COALESCE(cm.cmjsmkt, '')) = s.sglmarket::text
    AND s.sglhsrq::date BETWEEN cm.cmeffdate::date AND cm.cmlapdate::date
  ORDER BY cm.cmeffdate DESC, cm.cmcontno DESC
  LIMIT 1
) contract ON TRUE
"""

    sql = f"""
WITH filtered_sales AS (
  SELECT
    s.sglhsrq::date AS sglhsrq,
    s.sglmarket,
    s.sglmfid,
    s.sglsupid,
    s.sglppcode,
{filtered_operation_method_select_sql}    SUM(COALESCE(s.sglxssr, 0)) AS sglxssr,
    SUM(COALESCE(s.sgln2, 0)) AS sgln2
  FROM salegoodslist s
  WHERE (
       s.sglhsrq BETWEEN :start_date AND :end_date
       OR s.sglhsrq BETWEEN :prior_start_date AND :prior_end_date
  )
    AND (s.sglwmid IS NULL OR s.sglwmid <> '5')
    {selected_store_sales_sql}
  GROUP BY
    s.sglhsrq::date,
    s.sglmarket,
    s.sglmfid,
    s.sglsupid,
    s.sglppcode{filtered_operation_method_group_sql}
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
)
SELECT
  s.sglhsrq::date AS sale_date,
  s.sglmarket::text AS store_code,
  st.store_name,
  TRIM(BOTH FROM COALESCE(dept.mfcode, '')) AS department_code,
  COALESCE(NULLIF(TRIM(BOTH FROM dept.mfcname), ''), '未匹配') AS department_name,
  COALESCE(NULLIF(TRIM(BOTH FROM ac.area_name), ''), '未匹配') AS area_name,
  COALESCE(NULLIF(TRIM(BOTH FROM ac.category_name), ''), '未匹配') AS category_name,
  TRIM(BOTH FROM COALESCE(mf.mflc, '')) AS floor_code,
  {operation_method_code_sql} AS operation_method_code,
  COALESCE(kb.is_key_brand, FALSE) AS is_key_brand,
  COALESCE(NULLIF(TRIM(BOTH FROM cba.manager_name), ''), '') AS manager_name,
  {dimension_code_sql} AS dimension_code,
  {dimension_name_sql} AS dimension_name,
  {brand_code_sql} AS brand_code,
  {brand_name_sql} AS brand_name,
  SUM(COALESCE(s.sglxssr, 0)) AS sales,
  SUM(COALESCE(s.sgln2, 0)) AS profit
FROM filtered_sales s
JOIN manaframe mf
  ON UPPER(TRIM(COALESCE(s.sglmfid, ''))) = UPPER(TRIM(COALESCE(mf.mfcode, '')))
LEFT JOIN manaframe dept
  ON UPPER(TRIM(COALESCE(mf.mfpcode, ''))) = UPPER(TRIM(COALESCE(dept.mfcode, '')))
{contract_join_sql}
LEFT JOIN area_category_dedup ac
  ON UPPER(TRIM(COALESCE(mf.mfchr1, ''))) = ac.normalized_category_code
{brand_join_sql}
LEFT JOIN stores st
  ON TRIM(BOTH FROM COALESCE(st.store_code, '')) = s.sglmarket::text
LEFT JOIN manaframe_key_brand kb
  ON UPPER(TRIM(BOTH FROM COALESCE(kb.mfcode, '')))
   = UPPER(TRIM(BOTH FROM COALESCE(mf.mfcode, '')))
LEFT JOIN category_manager_brand_assignments cba
  ON cba.store_id = st.store_id
 AND UPPER(TRIM(BOTH FROM COALESCE(cba.group_code, '')))
   = UPPER(TRIM(BOTH FROM COALESCE(mf.mfcode, '')))
 AND cba.is_active
WHERE TRIM(BOTH FROM COALESCE(mf.mflc, '')) <> '00'
  AND TRIM(BOTH FROM COALESCE(dept.mfcode, '')) <> ALL(:excluded_department_codes)
  AND TRIM(BOTH FROM COALESCE(ac.area_name, '')) <> '其他类别区域'
  {special_sale_filter_sql}
  {scope_sql}
  {selected_department_sql}
GROUP BY
  s.sglhsrq::date,
  s.sglmarket::text,
  st.store_name,
  TRIM(BOTH FROM COALESCE(dept.mfcode, '')),
  COALESCE(NULLIF(TRIM(BOTH FROM dept.mfcname), ''), '未匹配'),
  COALESCE(NULLIF(TRIM(BOTH FROM ac.area_name), ''), '未匹配'),
  COALESCE(NULLIF(TRIM(BOTH FROM ac.category_name), ''), '未匹配'),
  TRIM(BOTH FROM COALESCE(mf.mflc, '')),
  {operation_method_code_sql},
  COALESCE(kb.is_key_brand, FALSE),
  COALESCE(NULLIF(TRIM(BOTH FROM cba.manager_name), ''), ''),
  {dimension_code_sql},
  {dimension_name_sql},
  {brand_code_sql},
  {brand_name_sql}
ORDER BY
  s.sglmarket::text,
  TRIM(BOTH FROM COALESCE(dept.mfcode, '')),
  {dimension_code_sql},
  {brand_code_sql},
  s.sglhsrq::date
"""
    return sql, params


def _number(value: Any) -> float:
    return float(value or 0)


def _operation_method_name(value: Any) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return "未匹配"
    return OPERATION_METHOD_NAMES.get(normalized, normalized)


def _row_dict(row: Mapping[str, Any] | Any) -> dict[str, Any]:
    if isinstance(row, Mapping):
        return dict(row)
    return {key: row[key] for key in row.keys()}


def _blank_amounts() -> dict[str, float]:
    return {
        "sales_current": 0.0,
        "profit_current": 0.0,
        "sales_prior": 0.0,
        "profit_prior": 0.0,
    }


def _add_amounts(target: dict[str, float], source: Mapping[str, Any]) -> None:
    for key in ("sales_current", "profit_current", "sales_prior", "profit_prior"):
        target[key] += _number(source.get(key))


def _metric_from_amounts(amounts: Mapping[str, Any]) -> dict[str, float | None]:
    return metric_triplet(
        amounts.get("sales_current"),
        amounts.get("profit_current"),
        amounts.get("sales_prior"),
        amounts.get("profit_prior"),
    )


def _period_totals_by_key(
    rows: Iterable[Mapping[str, Any] | Any],
    *,
    current_start: date,
    current_end: date,
    prior_start: date,
    prior_end: date,
) -> tuple[
    dict[tuple[str, str, str, str], dict[str, float | None]],
    dict[str, float | None],
]:
    grouped: dict[tuple[str, str, str], dict[str, float]] = {}
    grand = _blank_amounts()
    for source_row in rows:
        row = _row_dict(source_row)
        sale_date = row.get("sale_date")
        if isinstance(sale_date, datetime):
            sale_date = sale_date.date()
        if not isinstance(sale_date, date):
            continue
        period_prefix = (
            "current"
            if current_start <= sale_date <= current_end
            else "prior"
            if prior_start <= sale_date <= prior_end
            else None
        )
        if period_prefix is None:
            continue
        key = (
            str(row.get("store_code") or ""),
            str(row.get("department_code") or ""),
            str(row.get("dimension_code") or ""),
            str(row.get("brand_code") or ""),
        )
        amounts = grouped.setdefault(key, _blank_amounts())
        sales = _number(row.get("sales"))
        profit = _number(row.get("profit"))
        amounts[f"sales_{period_prefix}"] += sales
        amounts[f"profit_{period_prefix}"] += profit
        grand[f"sales_{period_prefix}"] += sales
        grand[f"profit_{period_prefix}"] += profit
    return (
        {key: _metric_from_amounts(amounts) for key, amounts in grouped.items()},
        _metric_from_amounts(grand),
    )


def build_daily_followup_payload(
    rows: Iterable[Mapping[str, Any] | Any],
    *,
    financial_year: int,
    financial_month: int,
    dimension: DailyFollowupDimension,
    selected_store: str | None = None,
    selected_department: str | None = None,
    as_of_date: date | None = None,
    cutoff_at_yesterday: bool = False,
) -> dict[str, Any]:
    if dimension not in DAILY_FOLLOWUP_DIMENSIONS:
        raise ValueError(f"unsupported daily follow-up dimension: {dimension}")

    start_date, end_date = financial_month_period(financial_year, financial_month)
    reporting_cutoff = as_of_date or _shopview_today()
    if cutoff_at_yesterday:
        reporting_cutoff -= timedelta(days=1)
    cumulative_end_date = min(reporting_cutoff, end_date)
    current_days: list[date] = []
    cursor = start_date
    while cursor <= end_date:
        current_days.append(cursor)
        cursor += timedelta(days=1)
    prior_dates = {current_day: _previous_year(current_day) for current_day in current_days}
    current_date_set = set(current_days)
    prior_to_current = {prior: current for current, prior in prior_dates.items()}

    grouped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for source_row in rows:
        row = _row_dict(source_row)
        sale_date = row.get("sale_date")
        if isinstance(sale_date, datetime):
            sale_date = sale_date.date()
        if not isinstance(sale_date, date):
            continue
        current_date = (
            sale_date
            if sale_date in current_date_set
            else prior_to_current.get(sale_date)
        )
        if current_date is None:
            continue

        store_code = str(row.get("store_code") or "")
        department_code = str(row.get("department_code") or "")
        dimension_code = str(row.get("dimension_code") or "")
        brand_code = str(row.get("brand_code") or "")
        key = (store_code, department_code, dimension_code, brand_code)
        operation_method = _operation_method_name(
            row.get("operation_method_code")
        )
        entry = grouped.setdefault(
            key,
            {
                "store_code": row.get("store_code"),
                "store_name": row.get("store_name"),
                "department_code": row.get("department_code"),
                "department_name": row.get("department_name"),
                "area_name": row.get("area_name"),
                "category_name": row.get("category_name"),
                "floor_code": row.get("floor_code"),
                "operation_method": operation_method,
                "is_key_brand": bool(row.get("is_key_brand")),
                "manager_name": row.get("manager_name"),
                "dimension_code": row.get("dimension_code"),
                "dimension_name": row.get("dimension_name"),
                "brand_code": row.get("brand_code"),
                "brand_name": row.get("brand_name"),
                "amounts_by_date": {
                    day: _blank_amounts() for day in current_days
                },
            },
        )
        period_prefix = "current" if sale_date in current_date_set else "prior"
        if period_prefix == "current" or entry["operation_method"] == "未匹配":
            entry["operation_method"] = operation_method
        amounts = entry["amounts_by_date"][current_date]
        amounts[f"sales_{period_prefix}"] += _number(row.get("sales"))
        amounts[f"profit_{period_prefix}"] += _number(row.get("profit"))

    report_rows: list[dict[str, Any]] = []
    total_by_date = {day: _blank_amounts() for day in current_days}
    for entry in grouped.values():
        row_totals = _blank_amounts()
        daily = []
        for current_day in current_days:
            amounts = entry["amounts_by_date"][current_day]
            if current_day <= cumulative_end_date:
                _add_amounts(row_totals, amounts)
            _add_amounts(total_by_date[current_day], amounts)
            daily.append(
                {
                    "date": current_day.isoformat(),
                    "prior_date": prior_dates[current_day].isoformat(),
                    **_metric_from_amounts(amounts),
                }
            )
        report_rows.append(
            {
                key: entry.get(key)
                for key in (
                    "store_code",
                    "store_name",
                    "department_code",
                    "department_name",
                    "area_name",
                    "category_name",
                    "floor_code",
                    "operation_method",
                    "is_key_brand",
                    "manager_name",
                    "dimension_code",
                    "dimension_name",
                    "brand_code",
                    "brand_name",
                )
            }
            | {
                "daily": daily,
                "totals": _metric_from_amounts(row_totals),
            }
        )

    def row_sort_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
        department_key = department_display_sort_key(
            {
                "department_code": row.get("department_code"),
                "department_name": row.get("department_name"),
            }
        )
        if dimension == "departments":
            return (
                str(row.get("store_code") or ""),
                department_key,
            )
        key = (
            str(row.get("store_code") or ""),
            department_key,
            str(row.get("dimension_name") or ""),
            str(row.get("dimension_code") or ""),
        )
        if dimension == "special_sales":
            return key + (
                str(row.get("brand_name") or ""),
                str(row.get("brand_code") or ""),
            )
        return key

    report_rows.sort(key=row_sort_key)
    grand_totals = _blank_amounts()
    daily_totals = []
    for current_day in current_days:
        amounts = total_by_date[current_day]
        if current_day <= cumulative_end_date:
            _add_amounts(grand_totals, amounts)
        daily_totals.append(
            {
                "date": current_day.isoformat(),
                "prior_date": prior_dates[current_day].isoformat(),
                **_metric_from_amounts(amounts),
            }
        )

    prior_start_date = _previous_year(start_date)
    prior_end_date = _previous_year(end_date)
    cumulative_prior_end_date = _previous_year(cumulative_end_date)
    return {
        "financial_month": f"{financial_year:04d}-{financial_month:02d}",
        "dates": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "prior_start_date": prior_start_date.isoformat(),
            "prior_end_date": prior_end_date.isoformat(),
        },
        "cumulative_dates": {
            "start_date": start_date.isoformat(),
            "end_date": cumulative_end_date.isoformat(),
            "prior_start_date": prior_start_date.isoformat(),
            "prior_end_date": cumulative_prior_end_date.isoformat(),
        },
        "dimension": dimension,
        "selected_store": selected_store,
        "selected_department": selected_department,
        "days": [
            {
                "date": current_day.isoformat(),
                "prior_date": prior_dates[current_day].isoformat(),
                "label": current_day.strftime("%m-%d"),
            }
            for current_day in current_days
        ],
        "rows": report_rows,
        "daily_totals": daily_totals,
        "totals": _metric_from_amounts(grand_totals),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def load_daily_followup_report(
    db: Any,
    scope_filter_sql: TrustedScopeSql,
    scope_params: Mapping[str, Any],
    *,
    financial_year: int,
    financial_month: int,
    dimension: DailyFollowupDimension,
    selected_store: str | None = None,
    selected_department: str | None = None,
    include_ytd: bool = False,
    as_of_date: date | None = None,
    cutoff_at_yesterday: bool = False,
) -> dict[str, Any]:
    start_date, end_date = financial_month_period(financial_year, financial_month)
    prior_start_date, prior_end_date = _previous_year(start_date), _previous_year(end_date)
    sql, params = build_daily_followup_query(
        start_date,
        end_date,
        prior_start_date,
        prior_end_date,
        dimension,
        scope_filter_sql,
        scope_params,
        selected_store,
        selected_department,
    )
    db.execute(
        text(f"SET LOCAL statement_timeout = '{OD0002_QUERY_TIMEOUT_SECONDS}s'"),
        {},
    )
    rows = db.execute(text(sql), params).mappings().all()
    report = build_daily_followup_payload(
        rows,
        financial_year=financial_year,
        financial_month=financial_month,
        dimension=dimension,
        selected_store=selected_store,
        selected_department=selected_department,
        as_of_date=as_of_date,
        cutoff_at_yesterday=cutoff_at_yesterday,
    )
    if not include_ytd:
        return report

    ytd_start = date(financial_year, 1, 1)
    ytd_prior_start = date(financial_year - 1, 1, 1)
    ytd_prior_end = _previous_year(end_date)
    ytd_sql, ytd_params = build_daily_followup_query(
        ytd_start,
        end_date,
        ytd_prior_start,
        ytd_prior_end,
        dimension,
        scope_filter_sql,
        scope_params,
        selected_store,
        selected_department,
    )
    ytd_rows = db.execute(text(ytd_sql), ytd_params).mappings().all()
    ytd_by_key, ytd_totals = _period_totals_by_key(
        ytd_rows,
        current_start=ytd_start,
        current_end=end_date,
        prior_start=ytd_prior_start,
        prior_end=ytd_prior_end,
    )
    for row in report["rows"]:
        key = (
            str(row.get("store_code") or ""),
            str(row.get("department_code") or ""),
            str(row.get("dimension_code") or ""),
            str(row.get("brand_code") or ""),
        )
        row["ytd_totals"] = ytd_by_key.get(key, _metric_from_amounts(_blank_amounts()))
    report["ytd_totals"] = ytd_totals
    report["ytd_dates"] = {
        "start_date": ytd_start.isoformat(),
        "end_date": end_date.isoformat(),
        "prior_start_date": ytd_prior_start.isoformat(),
        "prior_end_date": ytd_prior_end.isoformat(),
    }
    return report
