from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from .od0002_report import TrustedScopeSql, _trusted_scope_value


SETTLED_GROSS_PROFIT_QUERY_TIMEOUT_SECONDS = 120

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
    "16": "16",
    "17": "微商城",
    "18": "15F",
    "19": "16F",
}

OPERATION_MODE_NAMES = {
    "1": "经销",
    "2": "成本代销",
    "4": "联营",
    "5": "租赁",
}

NUMERIC_FIELDS = (
    "business_area",
    "sales_qty",
    "sales_revenue",
    "tax_excluded_sales",
    "front_profit",
    "tax_excluded_profit_adjustment",
    "floor_adjustment",
    "sales_floor_cost",
    "original_rate_profit",
    "appliance_rebate",
    "contract_profit",
)

TOTAL_FIELDS = tuple(field for field in NUMERIC_FIELDS if field != "business_area")


def _number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _floor_cases() -> str:
    return "\n".join(
        f"WHEN '{code}' THEN '{label}'" for code, label in FLOOR_NAMES.items()
    )


def _operation_mode_cases() -> str:
    return "\n".join(
        f"WHEN '{code}' THEN '{label}'"
        for code, label in OPERATION_MODE_NAMES.items()
    )


def build_settled_gross_profit_query(
    start_date: date,
    end_date: date,
    scope_filter_sql: str | TrustedScopeSql,
    scope_params: Mapping[str, Any],
    selected_store: str | None = None,
    selected_department: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Build the PostgreSQL equivalent of the Fuji settlement-profit report."""
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")

    scope_sql = _trusted_scope_value(scope_filter_sql)
    params = dict(scope_params)
    params.update({"start_date": start_date, "end_date": end_date})

    store_filter = ""
    if selected_store and selected_store.strip():
        params["selected_store"] = selected_store.strip()
        store_filter = " AND s.sglmarket = :selected_store"

    cost_store_filter = ""
    if selected_store and selected_store.strip():
        cost_store_filter = " AND s.scdmkt = :selected_store"

    department_filter = ""
    if selected_department and selected_department.strip():
        params["selected_department"] = selected_department.strip()
        department_filter = (
            " AND UPPER(TRIM(BOTH FROM COALESCE(dept.mfcode, ''))) "
            "= UPPER(:selected_department)"
        )

    sql = f"""
WITH area_category_dedup AS (
  SELECT DISTINCT ON (UPPER(TRIM(BOTH FROM category_code)))
    UPPER(TRIM(BOTH FROM category_code)) AS normalized_category_code,
    TRIM(BOTH FROM area_code) AS area_code,
    TRIM(BOTH FROM area_name) AS area_name,
    TRIM(BOTH FROM category_code) AS category_code,
    TRIM(BOTH FROM category_name) AS category_name
  FROM area_category
  ORDER BY UPPER(TRIM(BOTH FROM category_code)), area_code, area_name
),
sales_with_contract AS (
  SELECT
    s.*,
    contract.cmcontno AS resolved_contno
  FROM salegoodslist s
  LEFT JOIN LATERAL (
    SELECT cm.cmcontno
    FROM contmanaframe cmf
    JOIN contmain cm ON cm.cmcontno = cmf.cmfcontno
    WHERE cmf.cmfmfid = s.sglmfid
      AND cmf.cmfmarket = s.sglmarket
      AND cm.cmsupid = s.sglsupid
      AND cm.cmwmid = s.sglwmid
      AND cm.cmjsmkt = s.sglmarket
      AND s.sgldate BETWEEN cm.cmeffdate::date AND cm.cmlapdate::date
    -- Fuji FGetContNo keeps the contract-to-group relation after the
    -- contmanaframe row's own lapse date, so do not filter on cmf dates here.
    ORDER BY cm.cmeffdate DESC, cm.cmcontno DESC
    LIMIT 1
  ) contract ON TRUE
  WHERE s.sglhsrq >= :start_date
    AND s.sglhsrq < (:end_date + INTERVAL '1 day')
    {store_filter}
),
sales_aggregate AS (
  SELECT
    s.sglmarket AS store_code,
    st.store_name,
    TRIM(BOTH FROM COALESCE(dept.mfcode, '')) AS department_code,
    COALESCE(NULLIF(TRIM(BOTH FROM dept.mfcname), ''), '未匹配') AS department_name,
    s.sglmfid AS group_code,
    COALESCE(NULLIF(TRIM(BOTH FROM mf.mfcname), ''), s.sglmfid) AS group_name,
    s.sglsupid AS supplier_code,
    COALESCE(NULLIF(TRIM(BOTH FROM sb.sbcname), ''), '未匹配') AS supplier_name,
    TRIM(BOTH FROM COALESCE(mf.mflc, '')) AS floor_code,
    CASE TRIM(BOTH FROM COALESCE(mf.mflc, ''))
      {_floor_cases()}
      ELSE COALESCE(NULLIF(TRIM(BOTH FROM mf.mflc), ''), '未匹配')
    END AS floor_name,
    mf.mfyymj AS business_area,
    s.sglwmid AS operation_mode_code,
    CASE s.sglwmid
      {_operation_mode_cases()}
      ELSE COALESCE(NULLIF(TRIM(BOTH FROM s.sglwmid), ''), '未匹配')
    END AS operation_mode_name,
    SUBSTRING(mf.mfzlgh FROM 1 FOR 2) AS area_code,
    COALESCE(NULLIF(ac.area_name, ''), '未匹配') AS area_name,
    s.resolved_contno AS contract_code,
    SUM(s.sglsl) AS sales_qty,
    SUM(s.sglxssr + s.sglpfsr) AS sales_revenue,
    ROUND(SUM((s.sglxssr + s.sglpfsr) / (1 + s.sglxstax)), 2) AS tax_excluded_sales,
    ROUND(SUM(s.sgln2 / (1 + s.sglxstax)), 2) AS front_profit
  FROM sales_with_contract s
  JOIN manaframe mf ON mf.mfcode = s.sglmfid
  LEFT JOIN manaframe dept
    ON UPPER(TRIM(BOTH FROM COALESCE(mf.mfpcode, '')))
     = UPPER(TRIM(BOTH FROM COALESCE(dept.mfcode, '')))
  LEFT JOIN stores st ON TRIM(BOTH FROM st.store_code) = s.sglmarket
  LEFT JOIN supplierbase sb ON TRIM(BOTH FROM sb.sbid) = s.sglsupid
  LEFT JOIN area_category_dedup ac
    ON UPPER(TRIM(BOTH FROM COALESCE(mf.mfchr1, '')))
     = ac.normalized_category_code
  WHERE SUBSTRING(mf.mfzlgh FROM 1 FOR 2) IS NOT NULL
    {scope_sql}
    {department_filter}
  GROUP BY
    s.sglmarket, st.store_name, dept.mfcode, dept.mfcname,
    s.sglmfid, mf.mfcname, s.sglsupid, sb.sbcname,
    mf.mflc, mf.mfyymj, s.sglwmid,
    SUBSTRING(mf.mfzlgh FROM 1 FOR 2), ac.area_name,
    ac.category_code, ac.category_name,
    s.resolved_contno
),
charge_aggregate AS (
  SELECT
    sscmarket AS store_code,
    sscmfid,
    sscsupid,
    ssccontno,
    ROUND(
      SUM(CASE WHEN sscid = '51' THEN COALESCE(sscmoney, 0) / 1.16 ELSE 0 END) +
      SUM(CASE WHEN sscid = '52' THEN COALESCE(sscmoney, 0) / 1.10 ELSE 0 END) +
      SUM(CASE WHEN sscid = '53' THEN COALESCE(sscmoney, 0) / 1.06 ELSE 0 END) +
      SUM(CASE WHEN sscid = '62' THEN COALESCE(sscmoney, 0) / 1.13 ELSE 0 END) +
      SUM(CASE WHEN sscid = '63' THEN COALESCE(sscmoney, 0) / 1.09 ELSE 0 END) +
      SUM(CASE WHEN sscid = '54' THEN COALESCE(sscmoney, 0) ELSE 0 END), 2
    ) AS tax_excluded_profit_adjustment,
    ROUND(
      SUM(CASE WHEN sscid = '55' THEN COALESCE(sscmoney, 0) / 1.16 ELSE 0 END) +
      SUM(CASE WHEN sscid = '56' THEN COALESCE(sscmoney, 0) / 1.10 ELSE 0 END) +
      SUM(CASE WHEN sscid = '57' THEN COALESCE(sscmoney, 0) / 1.06 ELSE 0 END) +
      SUM(CASE WHEN sscid = '64' THEN COALESCE(sscmoney, 0) / 1.13 ELSE 0 END) +
      SUM(CASE WHEN sscid = '58' THEN COALESCE(sscmoney, 0) ELSE 0 END), 2
    ) AS floor_adjustment,
    ROUND(
      SUM(CASE WHEN sscid = '59' THEN COALESCE(sscmoney, 0) / 1.16 ELSE 0 END) +
      SUM(CASE WHEN sscid = '68' THEN COALESCE(sscmoney, 0) / 1.13 ELSE 0 END), 2
    ) AS appliance_rebate
  FROM supsetcharge
  WHERE sscfsdate >= :start_date
    AND sscfsdate < (:end_date + INTERVAL '1 day')
  GROUP BY sscmarket, sscmfid, sscsupid, ssccontno
),
cost_with_contract AS (
  SELECT
    s.*,
    contract.cmcontno AS resolved_contno
  FROM salecostday s
  LEFT JOIN LATERAL (
    SELECT cm.cmcontno
    FROM contmanaframe cmf
    JOIN contmain cm ON cm.cmcontno = cmf.cmfcontno
    WHERE cmf.cmfmfid = s.scdmfid
      AND cmf.cmfmarket = s.scdmkt
      AND cm.cmsupid = s.scdsupid
      AND cm.cmwmid = s.scdwmid
      AND cm.cmjsmkt = s.scdmkt
      AND s.scddate::date BETWEEN cm.cmeffdate::date AND cm.cmlapdate::date
    ORDER BY cm.cmeffdate DESC, cm.cmcontno DESC
    LIMIT 1
  ) contract ON TRUE
  WHERE s.scdhsrq >= :start_date
    AND s.scdhsrq < (:end_date + INTERVAL '1 day')
    {cost_store_filter}
),
sales_floor_aggregate AS (
  SELECT
    bd.cbmkt AS store_code,
    bd.cbcontno,
    bd.cbmfid,
    SUM(
      CASE
        WHEN sales.sales_revenue >= bd.cbsum THEN 0
        ELSE ROUND((COALESCE(bd.cbsum, 0) - sales.sales_revenue) * bd.cbrate, 2)
      END
    ) AS sales_floor_cost
  FROM (
    SELECT cbmkt, cbcontno, cbmfid, COALESCE(cbsum, 0) AS cbsum, cbrate
    FROM contbd
    WHERE cbeffdate >= :start_date
      AND cblapdate < (:end_date + INTERVAL '1 day')
  ) bd
  JOIN (
    SELECT scdmkt, scdmfid, resolved_contno AS contract_code, SUM(xssr) AS sales_revenue
    FROM cost_with_contract
    GROUP BY scdmkt, scdmfid, resolved_contno
  ) sales
    ON bd.cbmkt = sales.scdmkt
   AND bd.cbmfid = sales.scdmfid
   AND bd.cbcontno = sales.contract_code
  GROUP BY bd.cbmkt, bd.cbcontno, bd.cbmfid
),
original_rate_profit AS (
  SELECT
    sglmarket AS store_code,
    resolved_contno AS contract_code,
    SUM(ROUND((sglxssr + sglpfsr) / (1 + sglxstax) * sglbasekl, 2)) AS original_rate_profit
  FROM sales_with_contract
  GROUP BY sglmarket, resolved_contno
),
contract_profit AS (
  SELECT cbmkt AS store_code, cbcontno, SUM(cbsum) AS contract_profit
  FROM contbd
  WHERE cblapdate >= :start_date
    AND cbeffdate < (:end_date + INTERVAL '1 day')
  GROUP BY cbmkt, cbcontno
)
SELECT
  a.store_code,
  a.store_name,
  a.department_code,
  a.department_name,
  a.group_code,
  a.group_name,
  a.supplier_code,
  a.supplier_name,
  a.floor_code,
  a.floor_name,
  a.business_area,
  a.operation_mode_code,
  a.operation_mode_name,
  a.area_code,
  a.area_name,
  a.contract_code,
  a.sales_qty,
  a.sales_revenue,
  a.tax_excluded_sales,
  a.front_profit,
  COALESCE(b.tax_excluded_profit_adjustment, 0) AS tax_excluded_profit_adjustment,
  COALESCE(b.floor_adjustment, 0) AS floor_adjustment,
  COALESCE(c.sales_floor_cost, 0) AS sales_floor_cost,
  d.original_rate_profit,
  COALESCE(b.appliance_rebate, 0) AS appliance_rebate,
  e.cmlapdate::date AS contract_end_date,
  f.contract_profit
FROM sales_aggregate a
LEFT JOIN charge_aggregate b
  ON a.store_code = b.store_code
 AND a.group_code = b.sscmfid
 AND a.supplier_code = b.sscsupid
 AND a.contract_code = b.ssccontno
LEFT JOIN sales_floor_aggregate c
  ON a.store_code = c.store_code
 AND a.group_code = c.cbmfid
 AND a.contract_code = c.cbcontno
LEFT JOIN original_rate_profit d
  ON a.store_code = d.store_code
 AND a.contract_code = d.contract_code
LEFT JOIN contmain e
  ON a.store_code = e.cmjsmkt
 AND a.contract_code = e.cmcontno
LEFT JOIN contract_profit f
  ON a.store_code = f.store_code
 AND a.contract_code = f.cbcontno
ORDER BY a.store_code, a.department_code, a.group_code, a.area_code, a.supplier_code
"""
    return sql, params


def normalize_report_rows(rows: list[Mapping[str, Any] | Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for source in rows:
        row = dict(source) if isinstance(source, Mapping) else dict(source._mapping)
        for field in NUMERIC_FIELDS:
            row[field] = _number(row.get(field))
        contract_end = row.get("contract_end_date")
        if contract_end is not None and hasattr(contract_end, "isoformat"):
            row["contract_end_date"] = contract_end.isoformat()
        result.append(row)
    return result


def build_totals(rows: list[Mapping[str, Any]]) -> dict[str, float | None]:
    totals: dict[str, float | None] = {}
    for field in TOTAL_FIELDS:
        if field == "contract_profit":
            totals[field] = None
            continue
        totals[field] = sum(float(row.get(field) or 0) for row in rows)
    return totals


def build_quality(rows: list[Mapping[str, Any]]) -> dict[str, int | float]:
    unresolved = [row for row in rows if not str(row.get("contract_code") or "").strip()]
    return {
        "row_count": len(rows),
        "unresolved_contract_group_count": len(unresolved),
        "unresolved_contract_sales": sum(float(row.get("sales_revenue") or 0) for row in unresolved),
        "missing_supplier_name_count": sum(
            1 for row in rows if str(row.get("supplier_name") or "").strip() in ("", "未匹配")
        ),
        "missing_area_name_count": sum(
            1 for row in rows if str(row.get("area_name") or "").strip() in ("", "未匹配")
        ),
    }


def load_settled_gross_profit_report(
    db: Any,
    scope_filter_sql: TrustedScopeSql,
    scope_params: Mapping[str, Any],
    *,
    start_date: date,
    end_date: date,
    selected_store: str | None = None,
    selected_department: str | None = None,
) -> dict[str, Any]:
    sql, params = build_settled_gross_profit_query(
        start_date,
        end_date,
        scope_filter_sql,
        scope_params,
        selected_store,
        selected_department,
    )
    db.execute(
        text(
            "SET LOCAL statement_timeout = "
            f"'{SETTLED_GROSS_PROFIT_QUERY_TIMEOUT_SECONDS}s'"
        ),
        {},
    )
    source_rows = db.execute(text(sql), params).mappings().all()
    rows = normalize_report_rows(source_rows)
    return {
        "dates": {"start_date": start_date, "end_date": end_date},
        "selected_store": selected_store,
        "selected_department": selected_department,
        "rows": rows,
        "totals": build_totals(rows),
        "quality": build_quality(rows),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
