from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from .od0002_report import OD0002_QUERY_TIMEOUT_SECONDS, TrustedScopeSql, _trusted_scope_value


MICRO_MALL_CASHIER_BY_STORE = {
    "601": "300411",
    "602": "600518",
    "603": "500708",
}


def micro_mall_cashier(store_code: str) -> str:
    normalized = str(store_code or "").strip()
    try:
        return MICRO_MALL_CASHIER_BY_STORE[normalized]
    except KeyError as exc:
        raise ValueError(f"unsupported OD0005 store: {normalized or '(blank)'}") from exc


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

    params = dict(scope_params)
    params.update(
        {
            "start_date": start_date,
            "end_date": end_date,
            "selected_store": store_code,
            "micro_mall_cashier": micro_mall_cashier(store_code),
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
  WHERE s.sgldate::date BETWEEN :start_date AND :end_date
    AND TRIM(BOTH FROM s.sglmarket::text) = :selected_store
    AND TRIM(BOTH FROM COALESCE(s.sglchecker, '')) = :micro_mall_cashier
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
        "cashier_code": micro_mall_cashier(selected_store),
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
    return assemble_od0005_report(
        list(rows),
        start_date=start_date,
        end_date=end_date,
        selected_store=selected_store,
        selected_department=selected_department,
    )
