from __future__ import annotations

from collections.abc import Mapping
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from .od0002_report import (
    OD0002_QUERY_TIMEOUT_SECONDS,
    TrustedScopeSql,
    _trusted_scope_value,
    compare_period,
)


MICRO_MALL_STORES = frozenset({"601", "602", "603"})
MICRO_MALL_PAYMENT_CODE = "0581"

# Identify tickets by payment code, regardless of cashier or payment type.
# EXISTS keeps split payments and multiple goods allocations from multiplying sales.
MICRO_MALL_PAYMENT_FILTER_SQL = """
    AND EXISTS (
      SELECT 1
      FROM sellpaygoods micro_payment
      WHERE micro_payment.spgbillno = s.sglbillno
        AND TRIM(BOTH FROM micro_payment.spgpmcode) = :micro_mall_payment_code
    )
"""


def _validate_store(store_code: str) -> None:
    if store_code not in MICRO_MALL_STORES:
        raise ValueError(f"unsupported OD0005 store: {store_code or '(blank)'}")


def _number(value: Any) -> float:
    return float(value or Decimal("0"))


def build_od0005_query(
    *,
    start_date: date,
    end_date: date,
    selected_store: str,
    selected_department: str | None,
    scope_filter_sql: str | TrustedScopeSql,
    scope_params: Mapping[str, Any],
) -> tuple[str, dict[str, Any]]:
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")
    store_code = str(selected_store or "").strip()
    if not store_code:
        raise ValueError("OD0005 requires one selected store")

    _validate_store(store_code)
    params = dict(scope_params)
    params.update(
        {
            "start_date": start_date,
            "end_date": end_date,
            "selected_store": store_code,
            "micro_mall_payment_code": MICRO_MALL_PAYMENT_CODE,
        }
    )
    department_sql = ""
    department_code = str(selected_department or "").strip()
    if department_code:
        params["selected_department"] = department_code.upper()
        department_sql = (
            "AND UPPER(TRIM(BOTH FROM COALESCE(dept.mfcode, ''))) "
            "= :selected_department"
        )

    scope_sql = _trusted_scope_value(scope_filter_sql)
    sql = f"""
WITH area_category_dedup AS (
  SELECT DISTINCT ON (UPPER(TRIM(BOTH FROM category_code)))
    UPPER(TRIM(BOTH FROM category_code)) AS normalized_category_code,
    category_code,
    category_name
  FROM area_category
  ORDER BY UPPER(TRIM(BOTH FROM category_code)), area_code, area_name, category_name
),
micro_sales AS MATERIALIZED (
  SELECT
    TRIM(BOTH FROM s.sglmarket::text) AS store_code,
    TRIM(BOTH FROM s.sglmfid) AS group_code,
    s.sglbillno AS billno,
    SUM(COALESCE(s.sglsl, 0)) AS sales_quantity,
    SUM(COALESCE(s.sglsjje, 0)) AS price_amount,
    SUM(COALESCE(s.sglxssr, 0) + COALESCE(s.sgltotzk, 0)) AS sales_before_discount,
    SUM(COALESCE(s.sglxssr, 0)) AS sales_revenue,
    SUM(COALESCE(s.sgln2, 0)) AS gross_profit
  FROM salegoodslist s
  WHERE s.sgldate BETWEEN :start_date AND :end_date
    AND TRIM(BOTH FROM s.sglmarket::text) = :selected_store
    {MICRO_MALL_PAYMENT_FILTER_SQL}
  GROUP BY
    TRIM(BOTH FROM s.sglmarket::text),
    TRIM(BOTH FROM s.sglmfid),
    s.sglbillno
),
sales_by_group AS (
  SELECT
    store_code,
    group_code,
    SUM(sales_quantity) AS sales_quantity,
    SUM(price_amount) AS price_amount,
    SUM(sales_before_discount) AS sales_before_discount,
    SUM(sales_revenue) AS sales_revenue,
    SUM(gross_profit) AS gross_profit
  FROM micro_sales
  GROUP BY store_code, group_code
),
micro_bill_groups AS MATERIALIZED (
  SELECT DISTINCT billno, store_code, group_code
  FROM micro_sales
),
payments_by_group AS (
  SELECT
    mbg.store_code,
    mbg.group_code,
    SUM(
      CASE WHEN spg.spgpmcode IN ('2031', '1014', '3064')
        THEN CASE WHEN TRIM(BOTH FROM COALESCE(h.djlb::text, '')) = '4' THEN -1 ELSE 1 END
             * COALESCE(spg.spggdmoney, 0)
        ELSE 0 END
    ) AS yzq_amount,
    SUM(
      CASE WHEN spg.spgpmcode = '0511'
        THEN CASE WHEN TRIM(BOTH FROM COALESCE(h.djlb::text, '')) = '4' THEN -1 ELSE 1 END
             * COALESCE(spg.spggdmoney, 0)
        ELSE 0 END
    ) AS nzd_amount,
    SUM(
      CASE WHEN spg.spgpmcode NOT IN ('0511', '2031', '1014', '3064')
        THEN CASE WHEN TRIM(BOTH FROM COALESCE(h.djlb::text, '')) = '4' THEN -1 ELSE 1 END
             * COALESCE(spg.spggdmoney, 0)
        ELSE 0 END
    ) AS other_payment_amount
  FROM micro_bill_groups mbg
  JOIN salehead h
    ON h.billno = mbg.billno
   AND TRIM(BOTH FROM h.mkt::text) = mbg.store_code
  JOIN salegoods g
    ON g.billno = mbg.billno
   AND UPPER(TRIM(BOTH FROM COALESCE(g.gz, ''))) = UPPER(mbg.group_code)
  JOIN sellpaygoods spg
    ON spg.spgbillno = g.billno
   AND spg.spggdrow = g.rowno::numeric
  JOIN paymode pm
    ON UPPER(TRIM(BOTH FROM pm.pmcode)) = UPPER(TRIM(BOTH FROM spg.spgpmcode))
  WHERE spg.spgpmtype = '5'
    AND h.rqsj::date BETWEEN :start_date AND :end_date
  GROUP BY mbg.store_code, mbg.group_code
)
SELECT
  sales.store_code,
  COALESCE(st.store_name, sales.store_code) AS store_name,
  TRIM(BOTH FROM COALESCE(dept.mfcode, '')) AS department_code,
  COALESCE(NULLIF(TRIM(BOTH FROM dept.mfcname), ''), '未匹配') AS department_name,
  sales.group_code,
  COALESCE(NULLIF(TRIM(BOTH FROM mf.mfcname), ''), sales.group_code) AS group_name,
  sales.sales_quantity,
  sales.price_amount,
  sales.sales_before_discount,
  sales.sales_revenue,
  sales.gross_profit,
  CASE WHEN sales.sales_revenue <> 0
    THEN sales.gross_profit / sales.sales_revenue
    ELSE NULL END AS gross_margin,
  COALESCE(payments.yzq_amount, 0) AS yzq_amount,
  COALESCE(payments.other_payment_amount, 0) AS other_payment_amount,
  COALESCE(payments.nzd_amount, 0) AS nzd_amount
FROM sales_by_group sales
JOIN manaframe mf
  ON UPPER(TRIM(BOTH FROM mf.mfcode)) = UPPER(sales.group_code)
LEFT JOIN manaframe dept
  ON UPPER(TRIM(BOTH FROM COALESCE(mf.mfpcode, '')))
   = UPPER(TRIM(BOTH FROM COALESCE(dept.mfcode, '')))
LEFT JOIN stores st
  ON TRIM(BOTH FROM COALESCE(st.store_code, '')) = sales.store_code
LEFT JOIN area_category_dedup ac
  ON UPPER(TRIM(BOTH FROM COALESCE(mf.mfchr1, '')))
   = ac.normalized_category_code
LEFT JOIN payments_by_group payments
  ON payments.store_code = sales.store_code
 AND UPPER(payments.group_code) = UPPER(sales.group_code)
WHERE 1 = 1
  {department_sql}
  {scope_sql}
ORDER BY
  department_code,
  sales.group_code
"""
    return sql, params


def build_od0005_daily_query(
    *,
    start_date: date,
    end_date: date,
    selected_store: str,
    selected_department: str | None,
    scope_filter_sql: str | TrustedScopeSql,
    scope_params: Mapping[str, Any],
    include_two_year_prior: bool = False,
) -> tuple[str, dict[str, Any]]:
    """Build the permission-scoped daily sales query for comparison periods."""
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")
    store_code = str(selected_store or "").strip()
    if not store_code:
        raise ValueError("OD0005 requires one selected store")

    prior_start_date, prior_end_date = compare_period(start_date, end_date)
    two_year_prior_start_date, two_year_prior_end_date = compare_period(
        prior_start_date,
        prior_end_date,
    )
    _validate_store(store_code)
    params = dict(scope_params)
    params.update(
        {
            "start_date": start_date,
            "end_date": end_date,
            "prior_start_date": prior_start_date,
            "prior_end_date": prior_end_date,
            "two_year_prior_start_date": two_year_prior_start_date,
            "two_year_prior_end_date": two_year_prior_end_date,
            "selected_store": store_code,
            "micro_mall_payment_code": MICRO_MALL_PAYMENT_CODE,
        }
    )
    department_sql = ""
    department_code = str(selected_department or "").strip()
    if department_code:
        params["selected_department"] = department_code.upper()
        department_sql = (
            "AND UPPER(TRIM(BOTH FROM COALESCE(dept.mfcode, ''))) "
            "= :selected_department"
        )

    scope_sql = _trusted_scope_value(scope_filter_sql)
    two_year_prior_period_sql = (
        ",\n    ('two_year_prior', CAST(:two_year_prior_start_date AS date), "
        "CAST(:two_year_prior_end_date AS date))"
        if include_two_year_prior
        else ""
    )
    sql = f"""
WITH area_category_dedup AS (
  SELECT DISTINCT ON (UPPER(TRIM(BOTH FROM category_code)))
    UPPER(TRIM(BOTH FROM category_code)) AS normalized_category_code,
    category_code,
    category_name
  FROM area_category
  ORDER BY UPPER(TRIM(BOTH FROM category_code)), area_code, area_name, category_name
),
periods(period_key, start_date, end_date) AS (
  VALUES
    ('current', CAST(:start_date AS date), CAST(:end_date AS date)),
    ('prior', CAST(:prior_start_date AS date), CAST(:prior_end_date AS date))
    {two_year_prior_period_sql}
),
daily_sales AS MATERIALIZED (
  SELECT
    periods.period_key,
    s.sgldate AS sales_date,
    TRIM(BOTH FROM s.sglmarket::text) AS store_code,
    TRIM(BOTH FROM s.sglmfid) AS group_code,
    SUM(COALESCE(s.sglxssr, 0)) AS sales_revenue
  FROM periods
  JOIN salegoodslist s
    ON s.sgldate BETWEEN periods.start_date AND periods.end_date
  WHERE TRIM(BOTH FROM s.sglmarket::text) = :selected_store
    {MICRO_MALL_PAYMENT_FILTER_SQL}
  GROUP BY
    periods.period_key,
    s.sgldate,
    TRIM(BOTH FROM s.sglmarket::text),
    TRIM(BOTH FROM s.sglmfid)
)
SELECT
  sales.period_key,
  sales.sales_date,
  sales.store_code,
  COALESCE(st.store_name, sales.store_code) AS store_name,
  TRIM(BOTH FROM COALESCE(dept.mfcode, '')) AS department_code,
  COALESCE(NULLIF(TRIM(BOTH FROM dept.mfcname), ''), '未匹配') AS department_name,
  sales.group_code,
  COALESCE(NULLIF(TRIM(BOTH FROM mf.mfcname), ''), sales.group_code) AS group_name,
  sales.sales_revenue
FROM daily_sales sales
JOIN manaframe mf
  ON UPPER(TRIM(BOTH FROM mf.mfcode)) = UPPER(sales.group_code)
LEFT JOIN manaframe dept
  ON UPPER(TRIM(BOTH FROM COALESCE(mf.mfpcode, '')))
   = UPPER(TRIM(BOTH FROM COALESCE(dept.mfcode, '')))
LEFT JOIN stores st
  ON TRIM(BOTH FROM COALESCE(st.store_code, '')) = sales.store_code
LEFT JOIN area_category_dedup ac
  ON UPPER(TRIM(BOTH FROM COALESCE(mf.mfchr1, '')))
   = ac.normalized_category_code
WHERE 1 = 1
  {department_sql}
  {scope_sql}
ORDER BY
  department_code,
  sales.group_code,
  sales.period_key,
  sales.sales_date
"""
    return sql, params


def assemble_od0005_brand_yoy(
    rows: list[Mapping[str, Any]],
    *,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    prior_start_date, prior_end_date = compare_period(start_date, end_date)
    two_year_prior_start_date, two_year_prior_end_date = compare_period(
        prior_start_date,
        prior_end_date,
    )
    period_amount_keys = {
        "current": "sales_current",
        "prior": "sales_prior",
        "two_year_prior": "sales_two_year_prior",
    }
    groups: dict[tuple[str, str, str, str, str, str], dict[str, Any]] = {}
    for source in rows:
        period_key = str(source.get("period_key") or "")
        amount_key = period_amount_keys.get(period_key)
        if amount_key is None:
            continue
        identity = (
            str(source.get("store_code") or ""),
            str(source.get("store_name") or ""),
            str(source.get("department_code") or ""),
            str(source.get("department_name") or "未匹配"),
            str(source.get("group_code") or ""),
            str(source.get("group_name") or ""),
        )
        group = groups.setdefault(
            identity,
            {
                "store_code": identity[0],
                "store_name": identity[1],
                "department_code": identity[2],
                "department_name": identity[3],
                "group_code": identity[4],
                "group_name": identity[5],
                "sales_two_year_prior": 0.0,
                "sales_prior": 0.0,
                "sales_current": 0.0,
            },
        )
        group[amount_key] += _number(source.get("sales_revenue"))

    brand_rows: list[dict[str, Any]] = []
    for group in groups.values():
        difference = group["sales_current"] - group["sales_prior"]
        brand_rows.append(
            {
                **group,
                "difference": difference,
                "yoy": difference / group["sales_prior"] if group["sales_prior"] else None,
            }
        )
    brand_rows.sort(key=lambda row: (row["department_code"], row["group_code"]))

    totals = {
        amount_key: sum(row[amount_key] for row in brand_rows)
        for amount_key in (
            "sales_two_year_prior",
            "sales_prior",
            "sales_current",
        )
    }
    totals["difference"] = totals["sales_current"] - totals["sales_prior"]
    totals["yoy"] = (
        totals["difference"] / totals["sales_prior"]
        if totals["sales_prior"]
        else None
    )
    return {
        "periods": {
            "two_year_prior": {
                "year": two_year_prior_start_date.year,
                "start_date": two_year_prior_start_date.isoformat(),
                "end_date": two_year_prior_end_date.isoformat(),
            },
            "prior": {
                "year": prior_start_date.year,
                "start_date": prior_start_date.isoformat(),
                "end_date": prior_end_date.isoformat(),
            },
            "current": {
                "year": start_date.year,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        },
        "rows": brand_rows,
        "totals": totals,
    }


def assemble_od0005_daily(
    rows: list[Mapping[str, Any]],
    *,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    prior_start_date, prior_end_date = compare_period(start_date, end_date)
    day_count = (end_date - start_date).days + 1
    days = [
        {
            "date": (start_date + timedelta(days=offset)).isoformat(),
            "prior_date": compare_period(
                start_date + timedelta(days=offset),
                start_date + timedelta(days=offset),
            )[0].isoformat(),
        }
        for offset in range(day_count)
    ]

    groups: dict[tuple[str, str, str, str, str, str], dict[str, Any]] = {}
    for source in rows:
        sales_date = source.get("sales_date")
        date_key = sales_date.isoformat() if hasattr(sales_date, "isoformat") else str(sales_date)
        period_key = str(source.get("period_key") or "")
        if period_key not in ("current", "prior"):
            continue
        identity = (
            str(source.get("store_code") or ""),
            str(source.get("store_name") or ""),
            str(source.get("department_code") or ""),
            str(source.get("department_name") or "未匹配"),
            str(source.get("group_code") or ""),
            str(source.get("group_name") or ""),
        )
        group = groups.setdefault(
            identity,
            {
                "store_code": identity[0],
                "store_name": identity[1],
                "department_code": identity[2],
                "department_name": identity[3],
                "group_code": identity[4],
                "group_name": identity[5],
                "current": {},
                "prior": {},
            },
        )
        group[period_key][date_key] = group[period_key].get(date_key, 0.0) + _number(
            source.get("sales_revenue")
        )

    daily_rows: list[dict[str, Any]] = []
    for group in groups.values():
        daily = []
        for day in days:
            current_sales = group["current"].get(day["date"], 0.0)
            prior_sales = group["prior"].get(day["prior_date"], 0.0)
            daily.append(
                {
                    **day,
                    "sales_current": current_sales,
                    "sales_prior": prior_sales,
                    "sales_yoy": (
                        current_sales / prior_sales - 1 if prior_sales else None
                    ),
                }
            )
        daily_rows.append(
            {
                **{key: value for key, value in group.items() if key not in ("current", "prior")},
                "daily": daily,
            }
        )

    daily_rows.sort(
        key=lambda row: (
            row["department_code"],
            row["group_code"],
        )
    )
    totals = []
    for day_index, day in enumerate(days):
        current_sales = sum(row["daily"][day_index]["sales_current"] for row in daily_rows)
        prior_sales = sum(row["daily"][day_index]["sales_prior"] for row in daily_rows)
        totals.append(
            {
                **day,
                "sales_current": current_sales,
                "sales_prior": prior_sales,
                "sales_yoy": current_sales / prior_sales - 1 if prior_sales else None,
            }
        )

    return {
        "prior_start_date": prior_start_date.isoformat(),
        "prior_end_date": prior_end_date.isoformat(),
        "days": days,
        "rows": daily_rows,
        "totals": totals,
    }


def assemble_od0005_report(
    rows: list[Mapping[str, Any]],
    *,
    start_date: date,
    end_date: date,
    selected_store: str,
    selected_department: str | None,
) -> dict[str, Any]:
    normalized_rows: list[dict[str, Any]] = []
    totals = {
        "sales_quantity": 0.0,
        "price_amount": 0.0,
        "sales_before_discount": 0.0,
        "sales_revenue": 0.0,
        "gross_profit": 0.0,
        "yzq_amount": 0.0,
        "other_payment_amount": 0.0,
        "nzd_amount": 0.0,
    }
    store_name = str(selected_store)
    for source in rows:
        row = dict(source)
        store_name = str(row.get("store_name") or store_name)
        for key in totals:
            value = _number(row.get(key))
            row[key] = value
            totals[key] += value
        sales_revenue = row["sales_revenue"]
        row["gross_margin"] = (
            row["gross_profit"] / sales_revenue if sales_revenue else None
        )
        normalized_rows.append(row)

    totals["gross_margin"] = (
        totals["gross_profit"] / totals["sales_revenue"]
        if totals["sales_revenue"]
        else None
    )
    return {
        "report_code": "OD0005",
        "title": "微商城品牌销售统计",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "store_code": str(selected_store),
        "store_name": store_name,
        "department_code": str(selected_department or ""),
        "payment_code": MICRO_MALL_PAYMENT_CODE,
        "rows": normalized_rows,
        "totals": totals,
    }


def load_od0005_report(
    db: Any,
    *,
    start_date: date,
    end_date: date,
    selected_store: str,
    selected_department: str | None,
    scope_filter_sql: str | TrustedScopeSql,
    scope_params: Mapping[str, Any],
    include_daily: bool = True,
    include_brand_yoy: bool = True,
) -> dict[str, Any]:
    sql, params = build_od0005_query(
        start_date=start_date,
        end_date=end_date,
        selected_store=selected_store,
        selected_department=selected_department,
        scope_filter_sql=scope_filter_sql,
        scope_params=scope_params,
    )
    db.execute(text(f"SET LOCAL statement_timeout = '{OD0002_QUERY_TIMEOUT_SECONDS}s'"))
    rows = db.execute(text(sql), params).mappings().all()
    report = assemble_od0005_report(
        list(rows),
        start_date=start_date,
        end_date=end_date,
        selected_store=selected_store,
        selected_department=selected_department,
    )
    daily_rows: list[Mapping[str, Any]] = []
    if include_daily or include_brand_yoy:
        daily_sql, daily_params = build_od0005_daily_query(
            start_date=start_date,
            end_date=end_date,
            selected_store=selected_store,
            selected_department=selected_department,
            scope_filter_sql=scope_filter_sql,
            scope_params=scope_params,
            include_two_year_prior=include_brand_yoy,
        )
        daily_rows = list(db.execute(text(daily_sql), daily_params).mappings().all())
    report["daily"] = assemble_od0005_daily(
        daily_rows if include_daily else [],
        start_date=start_date,
        end_date=end_date,
    )
    report["brand_yoy"] = assemble_od0005_brand_yoy(
        daily_rows if include_brand_yoy else [],
        start_date=start_date,
        end_date=end_date,
    )
    return report
