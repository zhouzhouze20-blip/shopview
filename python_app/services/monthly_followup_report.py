from __future__ import annotations

from collections.abc import Iterable, Mapping
from calendar import monthrange
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import text

from services.daily_followup_report import (
    DAILY_FOLLOWUP_DIMENSIONS,
    DailyFollowupDimension,
    _add_amounts,
    _blank_amounts,
    _metric_from_amounts,
    _number,
    _operation_method_name,
    _previous_year,
    _row_dict,
    _shopview_today,
    build_daily_followup_query,
)
from services.department_display_order import department_display_sort_key
from services.od0002_report import OD0002_QUERY_TIMEOUT_SECONDS, TrustedScopeSql


def financial_month_period(financial_year: int, financial_month: int) -> tuple[date, date]:
    """Return one month in the natural financial year used by OD0004."""
    if not 1 <= financial_month <= 12:
        raise ValueError("financial_month must be between 1 and 12")
    if financial_month == 1:
        return date(financial_year, 1, 1), date(financial_year, 1, 28)
    if financial_month == 12:
        return date(financial_year, 11, 29), date(financial_year, 12, 31)

    previous_month = financial_month - 1
    previous_month_last_day = monthrange(financial_year, previous_month)[1]
    start_date = (
        date(financial_year, previous_month, 29)
        if previous_month_last_day >= 29
        else date(financial_year, financial_month, 1)
    )
    return start_date, date(financial_year, financial_month, 28)


def financial_year_period(financial_year: int) -> tuple[date, date]:
    """Return the natural financial year: January 1 through December 31."""
    return date(financial_year, 1, 1), date(financial_year, 12, 31)


def _month_index_for_date(value: date, financial_year: int) -> int | None:
    for month_index in range(12):
        start_date, end_date = financial_month_period(financial_year, month_index + 1)
        if start_date <= value <= end_date:
            return month_index
    return None


def build_monthly_followup_payload(
    rows: Iterable[Mapping[str, Any] | Any],
    *,
    financial_year: int,
    dimension: DailyFollowupDimension,
    selected_store: str | None = None,
    selected_department: str | None = None,
    as_of_date: date | None = None,
) -> dict[str, Any]:
    if dimension not in DAILY_FOLLOWUP_DIMENSIONS:
        raise ValueError(f"unsupported monthly follow-up dimension: {dimension}")

    today = as_of_date or _shopview_today()
    month_periods: list[dict[str, Any]] = []
    for month in range(1, 13):
        start_date, end_date = financial_month_period(financial_year, month)
        prior_start_date, prior_end_date = financial_month_period(
            financial_year - 1,
            month,
        )
        comparison_end = min(today, end_date)
        if comparison_end < start_date:
            comparison_end = None
        prior_comparison_end = (
            _previous_year(comparison_end)
            if comparison_end is not None
            else None
        )
        if (
            prior_comparison_end is not None
            and prior_comparison_end < prior_start_date
        ):
            prior_comparison_end = None
        month_periods.append(
            {
                "financial_month": f"{financial_year:04d}-{month:02d}",
                "label": f"{month}月",
                "start_date": start_date,
                "end_date": end_date,
                "prior_start_date": prior_start_date,
                "prior_end_date": prior_end_date,
                "comparison_end": comparison_end,
                "prior_comparison_end": prior_comparison_end,
            }
        )

    grouped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for source_row in rows:
        row = _row_dict(source_row)
        sale_date = row.get("sale_date")
        if isinstance(sale_date, datetime):
            sale_date = sale_date.date()
        if not isinstance(sale_date, date):
            continue

        month_index = _month_index_for_date(sale_date, financial_year)
        period_prefix = "current"
        if month_index is None:
            month_index = _month_index_for_date(sale_date, financial_year - 1)
            period_prefix = "prior"
        if month_index is None:
            continue

        period = month_periods[month_index]
        cutoff = (
            period["comparison_end"]
            if period_prefix == "current"
            else period["prior_comparison_end"]
        )
        if cutoff is None or sale_date > cutoff:
            continue

        key = (
            str(row.get("store_code") or ""),
            str(row.get("department_code") or ""),
            str(row.get("dimension_code") or ""),
            str(row.get("brand_code") or ""),
        )
        operation_method = _operation_method_name(row.get("operation_method_code"))
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
                "amounts_by_month": [_blank_amounts() for _ in range(12)],
            },
        )
        if period_prefix == "current" or entry["operation_method"] == "未匹配":
            entry["operation_method"] = operation_method
        amounts = entry["amounts_by_month"][month_index]
        amounts[f"sales_{period_prefix}"] += _number(row.get("sales"))
        amounts[f"profit_{period_prefix}"] += _number(row.get("profit"))

    report_rows: list[dict[str, Any]] = []
    total_by_month = [_blank_amounts() for _ in range(12)]
    for entry in grouped.values():
        row_totals = _blank_amounts()
        monthly = []
        for month_index, period in enumerate(month_periods):
            amounts = entry["amounts_by_month"][month_index]
            _add_amounts(row_totals, amounts)
            _add_amounts(total_by_month[month_index], amounts)
            monthly.append(
                {
                    "financial_month": period["financial_month"],
                    "label": period["label"],
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
                "monthly": monthly,
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
            return str(row.get("store_code") or ""), department_key
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
    monthly_totals = []
    for month_index, period in enumerate(month_periods):
        amounts = total_by_month[month_index]
        _add_amounts(grand_totals, amounts)
        monthly_totals.append(
            {
                "financial_month": period["financial_month"],
                "label": period["label"],
                **_metric_from_amounts(amounts),
            }
        )

    year_start, year_end = financial_year_period(financial_year)
    return {
        "financial_year": financial_year,
        "dates": {
            "start_date": year_start.isoformat(),
            "end_date": year_end.isoformat(),
            "prior_start_date": _previous_year(year_start).isoformat(),
            "prior_end_date": _previous_year(year_end).isoformat(),
        },
        "dimension": dimension,
        "selected_store": selected_store,
        "selected_department": selected_department,
        "months": [
            {
                "financial_month": period["financial_month"],
                "label": period["label"],
                "start_date": period["start_date"].isoformat(),
                "end_date": period["end_date"].isoformat(),
                "prior_start_date": period["prior_start_date"].isoformat(),
                "prior_end_date": period["prior_end_date"].isoformat(),
                "comparison_end": (
                    period["comparison_end"].isoformat()
                    if period["comparison_end"] is not None
                    else None
                ),
                "prior_comparison_end": (
                    period["prior_comparison_end"].isoformat()
                    if period["prior_comparison_end"] is not None
                    else None
                ),
            }
            for period in month_periods
        ],
        "rows": report_rows,
        "monthly_totals": monthly_totals,
        "totals": _metric_from_amounts(grand_totals),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def load_monthly_followup_report(
    db: Any,
    scope_filter_sql: TrustedScopeSql,
    scope_params: Mapping[str, Any],
    *,
    financial_year: int,
    dimension: DailyFollowupDimension,
    selected_store: str | None = None,
    selected_department: str | None = None,
    as_of_date: date | None = None,
) -> dict[str, Any]:
    start_date, end_date = financial_year_period(financial_year)
    prior_start_date, prior_end_date = financial_year_period(financial_year - 1)
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
    return build_monthly_followup_payload(
        rows,
        financial_year=financial_year,
        dimension=dimension,
        selected_store=selected_store,
        selected_department=selected_department,
        as_of_date=as_of_date,
    )
