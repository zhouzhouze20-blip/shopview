from __future__ import annotations

import calendar
from collections import defaultdict
from collections.abc import Mapping
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from .od0002_report import TrustedScopeSql, _trusted_scope_value


QUERY_TIMEOUT_SECONDS = 120

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

# ODS_CODECHARGE.CCNUM3 snapshot. A valid synchronized CODECHARGE.CCNUM3
# remains authoritative; these values cover the local rows whose tax rate is blank.
FEE_TAX_RATE_FALLBACKS = {
    "01": Decimal("0.05"),
    "02": Decimal("0.06"),
    "04": Decimal("0.05"),
    "06": Decimal("0.06"),
    "07": Decimal("0.06"),
    "08": Decimal("0.06"),
    "09": Decimal("0.06"),
    "10": Decimal("0.06"),
    "11": Decimal("0.06"),
    "12": Decimal("0.06"),
    "13": Decimal("0.06"),
    "14": Decimal("0.06"),
    "15": Decimal("0.06"),
    "16": Decimal("0.06"),
    "19": Decimal("0.06"),
    "20": Decimal("0.06"),
    "21": Decimal("0.06"),
    "22": Decimal("0.06"),
    "23": Decimal("0.13"),
    "24": Decimal("0.09"),
    "25": Decimal("0.06"),
    "26": Decimal("0.06"),
    "28": Decimal("0.06"),
    "29": Decimal("0.06"),
    "30": Decimal("0.06"),
    "31": Decimal("0.06"),
    "32": Decimal("0.06"),
    "33": Decimal("0.06"),
    "34": Decimal("0.06"),
    "35": Decimal("0.09"),
    "36": Decimal("0.06"),
    "39": Decimal("0.06"),
    "41": Decimal("0.06"),
    "42": Decimal("0.09"),
    "43": Decimal("0.13"),
    "44": Decimal("0.06"),
    "45": Decimal("0.06"),
    "47": Decimal("0.06"),
    "48": Decimal("0.06"),
    "49": Decimal("0.06"),
    "50": Decimal("0.06"),
    "51": Decimal("0.16"),
    "52": Decimal("0.10"),
    "53": Decimal("0.06"),
    "55": Decimal("0.16"),
    "56": Decimal("0.10"),
    "57": Decimal("0.06"),
    "59": Decimal("0.16"),
    "60": Decimal("0.05"),
    "62": Decimal("0.13"),
    "63": Decimal("0.09"),
    "64": Decimal("0.13"),
    "65": Decimal("0.09"),
    "66": Decimal("0.13"),
    "67": Decimal("0.09"),
    "68": Decimal("0.13"),
    "69": Decimal("0.09"),
    "70": Decimal("0.06"),
    "71": Decimal("0.06"),
    "72": Decimal("0.06"),
    "73": Decimal("0.06"),
    "74": Decimal("0.06"),
    "75": Decimal("0.06"),
    "76": Decimal("0.06"),
    "77": Decimal("0.13"),
    "78": Decimal("0.06"),
    "79": Decimal("0.06"),
    "80": Decimal("0.13"),
    "81": Decimal("0.06"),
    "ZN": Decimal("0.06"),
}

AMOUNT_FIELDS = (
    "tax_included_sales",
    "tax_excluded_sales",
    "gross_profit",
    "fee",
    "contribution",
    "contract_profit",
    "concession_loss",
)


def financial_month_period(financial_year: int, financial_month: int) -> tuple[date, date]:
    if not 1 <= financial_month <= 12:
        raise ValueError("financial_month must be between 1 and 12")
    if financial_month == 1:
        return date(financial_year, 1, 1), date(financial_year, 1, 28)
    if financial_month == 12:
        return date(financial_year, 11, 29), date(financial_year, 12, 31)

    start_year = financial_year
    start_month = financial_month - 1
    previous_month_days = calendar.monthrange(start_year, start_month)[1]
    start_date = (
        date(start_year, start_month, 29)
        if previous_month_days >= 29
        else date(financial_year, financial_month, 1)
    )
    return start_date, date(financial_year, financial_month, 28)


def financial_year_period(financial_year: int) -> tuple[date, date]:
    return date(financial_year, 1, 1), date(financial_year, 12, 31)


def _floor_cases() -> str:
    return "\n".join(f"WHEN '{code}' THEN '{label}'" for code, label in FLOOR_NAMES.items())


def _fee_tax_rate_values() -> str:
    return ",\n".join(
        f"('{code}', {rate})" for code, rate in sorted(FEE_TAX_RATE_FALLBACKS.items())
    )


def build_non_rental_monthly_revenue_query(
    financial_year: int,
    scope_filter_sql: str | TrustedScopeSql,
    scope_params: Mapping[str, Any],
    *,
    selected_store: str,
    selected_department: str | None = None,
) -> tuple[str, dict[str, Any]]:
    start_date, end_date = financial_year_period(financial_year)
    scope_sql = _trusted_scope_value(scope_filter_sql)
    params = dict(scope_params)
    params.update(
        {
            "financial_year": financial_year,
            "start_date": start_date,
            "end_date": end_date,
            "fee_start_date": date(financial_year - 1, 12, 1),
            "fee_end_date": date(financial_year, 12, 1),
            "selected_store": selected_store.strip(),
        }
    )
    department_filter = ""
    if selected_department and selected_department.strip():
        params["selected_department"] = selected_department.strip()
        department_filter = (
            " AND UPPER(TRIM(COALESCE(dept.mfcode, ''))) "
            "= UPPER(:selected_department)"
        )

    sql = f"""
WITH area_category_dedup AS (
  SELECT DISTINCT ON (UPPER(TRIM(category_code)))
    UPPER(TRIM(category_code)) AS normalized_category_code,
    TRIM(area_code) AS area_code,
    TRIM(area_name) AS area_name,
    TRIM(category_code) AS category_code,
    TRIM(category_name) AS category_name
  FROM area_category
  ORDER BY UPPER(TRIM(category_code)), area_code, area_name
),
fee_tax_rate_fallbacks(fee_type_code, tax_rate) AS (
  VALUES
    {_fee_tax_rate_values()}
),
fee_tax_rates AS (
  SELECT
    fallback.fee_type_code,
    COALESCE(
      CASE
        WHEN charge.ccnum3 >= 0 AND charge.ccnum3 <= 1 THEN charge.ccnum3
        ELSE NULL
      END,
      fallback.tax_rate
    ) AS tax_rate
  FROM fee_tax_rate_fallbacks fallback
  LEFT JOIN codecharge charge
    ON TRIM(charge.cccode) = fallback.fee_type_code
),
sales_aggregate AS (
  SELECT
    s.sglmarket AS store_code,
    st.store_name,
    TRIM(COALESCE(dept.mfcode, '')) AS department_code,
    COALESCE(NULLIF(TRIM(dept.mfcname), ''), '未匹配') AS department_name,
    TRIM(s.sglmfid) AS group_code,
    COALESCE(NULLIF(TRIM(mf.mfcname), ''), TRIM(s.sglmfid)) AS group_name,
    TRIM(COALESCE(s.sglppcode, '')) AS brand_code,
    COALESCE(
      NULLIF(TRIM(cb.cbcname), ''),
      NULLIF(TRIM(s.sglppcode), ''),
      '未标识品牌'
    ) AS brand_name,
    TRIM(COALESCE(mf.mflc, '')) AS floor_code,
    CASE TRIM(COALESCE(mf.mflc, ''))
      {_floor_cases()}
      ELSE COALESCE(NULLIF(TRIM(mf.mflc), ''), '未匹配')
    END AS floor_name,
    COALESCE(NULLIF(ac.area_code, ''), '未匹配') AS area_code,
    COALESCE(NULLIF(ac.area_name, ''), '未匹配') AS area_name,
    COALESCE(NULLIF(ac.category_code, ''), '未匹配') AS category_code,
    COALESCE(NULLIF(ac.category_name, ''), '未匹配') AS category_name,
    CASE
      WHEN TRIM(COALESCE(mf.mflc, '')) = '16' THEN '穿着类'
      WHEN COALESCE(ac.area_name, '') IN ('化妆区', '配饰区', '钟表区', '珠宝区') THEN '百货类'
      WHEN COALESCE(ac.area_name, '') = '生活服务' THEN '配套类'
      WHEN COALESCE(ac.area_name, '') IN ('青春时尚区', '运动区', '男装区', '女装区', '鞋包区', '食品区') THEN '穿着类'
      WHEN COALESCE(NULLIF(TRIM(mf.mfcname), ''), '') = '大公鸡管家' THEN '穿着类'
      ELSE '其他类'
    END AS big_category,
    CASE
      WHEN EXTRACT(MONTH FROM s.sglhsrq) = 12 THEN 12
      WHEN EXTRACT(DAY FROM s.sglhsrq) >= 29
        THEN EXTRACT(MONTH FROM s.sglhsrq) + 1
      ELSE EXTRACT(MONTH FROM s.sglhsrq)
    END::int AS financial_month,
    SUM(COALESCE(s.sglxssr, 0) + COALESCE(s.sglpfsr, 0)) AS tax_included_sales,
    ROUND(SUM(
      (COALESCE(s.sglxssr, 0) + COALESCE(s.sglpfsr, 0))
      / NULLIF(1 + COALESCE(s.sglxstax, 0), 0)
    ), 2) AS tax_excluded_sales,
    ROUND(SUM(
      CASE
        WHEN TRIM(COALESCE(s.sglwmid, '')) = '1' THEN
          COALESCE(s.sglxssr, 0) / NULLIF(1 + COALESCE(s.sglxstax, 0), 0)
          - (
              COALESCE(s.sgln13, 0)
              + COALESCE(s.sgln14, 0)
              - COALESCE(s.sglsupzk, 0)
            ) / NULLIF(1 + COALESCE(s.sgljjtax, 0), 0)
        ELSE COALESCE(s.sgln2, 0) / NULLIF(1 + COALESCE(s.sglxstax, 0), 0)
      END
    ), 2) AS gross_profit,
    SUM(
      ROUND(
        (COALESCE(s.sglxssr, 0) + COALESCE(s.sglpfsr, 0))
        / NULLIF(1 + COALESCE(s.sglxstax, 0), 0)
        * COALESCE(s.sglbasekl, 0),
        2
      )
    ) AS contract_profit,
    MAX(s.sglhsrq) AS latest_sales_date
  FROM salegoodslist s
  JOIN manaframe mf ON mf.mfcode = s.sglmfid
  LEFT JOIN manaframe dept
    ON UPPER(TRIM(COALESCE(mf.mfpcode, '')))
     = UPPER(TRIM(COALESCE(dept.mfcode, '')))
  LEFT JOIN stores st ON TRIM(st.store_code) = TRIM(s.sglmarket)
  LEFT JOIN codebrand cb
    ON UPPER(TRIM(COALESCE(cb.cbid, '')))
     = UPPER(TRIM(COALESCE(s.sglppcode, '')))
  LEFT JOIN area_category_dedup ac
    ON UPPER(TRIM(COALESCE(mf.mfchr1, ''))) = ac.normalized_category_code
  WHERE s.sglhsrq >= :start_date
    AND s.sglhsrq < (:end_date + INTERVAL '1 day')
    AND TRIM(s.sglmarket) = :selected_store
    AND TRIM(COALESCE(s.sglwmid, '')) <> '5'
    {scope_sql}
    {department_filter}
  GROUP BY
    s.sglmarket, st.store_name, dept.mfcode, dept.mfcname,
    s.sglmfid, mf.mfcname, s.sglppcode, cb.cbcname, mf.mflc,
    ac.area_code, ac.area_name, ac.category_code, ac.category_name,
    financial_month
),
fee_aggregate AS (
  SELECT
    TRIM(fee.sscmarket) AS store_code,
    st.store_name,
    TRIM(COALESCE(dept.mfcode, '')) AS department_code,
    COALESCE(NULLIF(TRIM(dept.mfcname), ''), '未匹配') AS department_name,
    TRIM(fee.sscmfid) AS group_code,
    COALESCE(NULLIF(TRIM(mf.mfcname), ''), TRIM(fee.sscmfid)) AS group_name,
    ''::text AS brand_code,
    '收费未分配品牌'::text AS brand_name,
    TRIM(COALESCE(mf.mflc, '')) AS floor_code,
    CASE TRIM(COALESCE(mf.mflc, ''))
      {_floor_cases()}
      ELSE COALESCE(NULLIF(TRIM(mf.mflc), ''), '未匹配')
    END AS floor_name,
    COALESCE(NULLIF(ac.area_code, ''), '未匹配') AS area_code,
    COALESCE(NULLIF(ac.area_name, ''), '未匹配') AS area_name,
    COALESCE(NULLIF(ac.category_code, ''), '未匹配') AS category_code,
    COALESCE(NULLIF(ac.category_name, ''), '未匹配') AS category_name,
    CASE
      WHEN TRIM(COALESCE(mf.mflc, '')) = '16' THEN '穿着类'
      WHEN COALESCE(ac.area_name, '') IN ('化妆区', '配饰区', '钟表区', '珠宝区') THEN '百货类'
      WHEN COALESCE(ac.area_name, '') = '生活服务' THEN '配套类'
      WHEN COALESCE(ac.area_name, '') IN ('青春时尚区', '运动区', '男装区', '女装区', '鞋包区', '食品区') THEN '穿着类'
      WHEN COALESCE(NULLIF(TRIM(mf.mfcname), ''), '') = '大公鸡管家' THEN '穿着类'
      ELSE '其他类'
    END AS big_category,
    CASE
      WHEN EXTRACT(MONTH FROM fee.sscfsdate) = 12 THEN 1
      ELSE EXTRACT(MONTH FROM fee.sscfsdate) + 1
    END::int AS financial_month,
    0::numeric AS tax_included_sales,
    0::numeric AS tax_excluded_sales,
    0::numeric AS gross_profit,
    SUM(
      COALESCE(fee.sscmoney, 0)
      / (1 + COALESCE(tax.tax_rate, 0))
    ) AS fee,
    0::numeric AS contract_profit,
    NULL::date AS latest_sales_date
  FROM supsetcharge fee
  JOIN manaframe mf ON mf.mfcode = fee.sscmfid
  LEFT JOIN manaframe dept
    ON UPPER(TRIM(COALESCE(mf.mfpcode, '')))
     = UPPER(TRIM(COALESCE(dept.mfcode, '')))
  LEFT JOIN stores st ON TRIM(st.store_code) = TRIM(fee.sscmarket)
  LEFT JOIN area_category_dedup ac
    ON UPPER(TRIM(COALESCE(mf.mfchr1, ''))) = ac.normalized_category_code
  LEFT JOIN fee_tax_rates tax
    ON tax.fee_type_code = TRIM(fee.sscid)
  WHERE fee.sscfsdate >= :fee_start_date
    AND fee.sscfsdate < :fee_end_date
    AND TRIM(fee.sscmarket) = :selected_store
    AND TRIM(COALESCE(fee.sscid, '')) NOT IN ('38', '61', '94', '95')
    {scope_sql}
    {department_filter}
  GROUP BY
    fee.sscmarket, st.store_name, dept.mfcode, dept.mfcname,
    fee.sscmfid, mf.mfcname, mf.mflc,
    ac.area_code, ac.area_name, ac.category_code, ac.category_name,
    financial_month
),
combined_rows AS (
  SELECT
    sales.store_code,
    sales.store_name,
    sales.department_code,
    sales.department_name,
    sales.group_code,
    sales.group_name,
    sales.brand_code,
    sales.brand_name,
    sales.floor_code,
    sales.floor_name,
    sales.area_code,
    sales.area_name,
    sales.category_code,
    sales.category_name,
    sales.big_category,
    sales.financial_month,
    sales.tax_included_sales,
    sales.tax_excluded_sales,
    sales.gross_profit,
    0::numeric AS fee,
    sales.contract_profit,
    sales.latest_sales_date
  FROM sales_aggregate sales

  UNION ALL

  SELECT
    fee.store_code,
    fee.store_name,
    fee.department_code,
    fee.department_name,
    fee.group_code,
    fee.group_name,
    fee.brand_code,
    fee.brand_name,
    fee.floor_code,
    fee.floor_name,
    fee.area_code,
    fee.area_name,
    fee.category_code,
    fee.category_name,
    fee.big_category,
    fee.financial_month,
    fee.tax_included_sales,
    fee.tax_excluded_sales,
    fee.gross_profit,
    fee.fee,
    fee.contract_profit,
    fee.latest_sales_date
  FROM fee_aggregate fee
  WHERE EXISTS (
    SELECT 1
    FROM sales_aggregate sales
    WHERE TRIM(sales.store_code) = fee.store_code
      AND sales.group_code = fee.group_code
      AND sales.financial_month = fee.financial_month
  )
)
SELECT
  combined.*
FROM combined_rows combined
ORDER BY
  combined.department_code,
  combined.floor_code,
  combined.area_code,
  combined.category_code,
  combined.group_name,
  combined.group_code,
  combined.brand_name,
  combined.brand_code,
  combined.financial_month
"""
    return sql, params


def _decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def empty_metrics() -> dict[str, float | None]:
    return {
        "tax_included_sales": 0.0,
        "tax_excluded_sales": 0.0,
        "gross_profit": 0.0,
        "fee": 0.0,
        "contribution": 0.0,
        "gross_margin": None,
        "contract_profit": 0.0,
        "concession_loss": 0.0,
        "concession_loss_rate": None,
    }


def build_metrics(
    *,
    tax_included_sales: Any = 0,
    tax_excluded_sales: Any = 0,
    gross_profit: Any = 0,
    fee: Any = 0,
    contract_profit: Any = 0,
) -> dict[str, float | None]:
    tax_included = _decimal(tax_included_sales)
    tax_excluded = _decimal(tax_excluded_sales)
    gross = _decimal(gross_profit)
    fee_value = _decimal(fee)
    contract = _decimal(contract_profit)
    contribution = gross + fee_value
    concession_loss = gross - contract
    return {
        "tax_included_sales": float(tax_included),
        "tax_excluded_sales": float(tax_excluded),
        "gross_profit": float(gross),
        "fee": float(fee_value),
        "contribution": float(contribution),
        "gross_margin": float(gross / tax_excluded) if tax_excluded else None,
        "contract_profit": float(contract),
        "concession_loss": float(concession_loss),
        "concession_loss_rate": float(concession_loss / tax_excluded) if tax_excluded else None,
    }


def aggregate_metrics(metrics: list[Mapping[str, Any]]) -> dict[str, float | None]:
    return build_metrics(
        tax_included_sales=sum(_decimal(item.get("tax_included_sales")) for item in metrics),
        tax_excluded_sales=sum(_decimal(item.get("tax_excluded_sales")) for item in metrics),
        gross_profit=sum(_decimal(item.get("gross_profit")) for item in metrics),
        fee=sum(_decimal(item.get("fee")) for item in metrics),
        contract_profit=sum(_decimal(item.get("contract_profit")) for item in metrics),
    )


def _aggregate_rows(
    rows: list[Mapping[str, Any]],
    *,
    row_type: str,
    row_key: str,
    dimensions: Mapping[str, Any],
) -> dict[str, Any]:
    months = {
        str(month): aggregate_metrics(
            [row["months"][str(month)] for row in rows]
        )
        for month in range(1, 13)
    }
    return {
        "row_type": row_type,
        "row_key": row_key,
        **dimensions,
        "months": months,
        "annual": aggregate_metrics(list(months.values())),
    }


def normalize_non_rental_monthly_revenue_rows(
    source_rows: list[Mapping[str, Any] | Any],
) -> dict[str, Any]:
    brands: dict[str, dict[str, Any]] = {}
    latest_sales_date: date | None = None

    for source in source_rows:
        row = dict(source) if isinstance(source, Mapping) else dict(source._mapping)
        month = int(row["financial_month"])
        if not 1 <= month <= 12:
            continue
        source_latest = row.get("latest_sales_date")
        if isinstance(source_latest, datetime):
            source_latest = source_latest.date()
        if isinstance(source_latest, date) and (
            latest_sales_date is None or source_latest > latest_sales_date
        ):
            latest_sales_date = source_latest

        group_code = str(row.get("group_code") or "").strip()
        brand_code = str(row.get("brand_code") or "").strip()
        brand_name = str(row.get("brand_name") or "").strip() or "未标识品牌"
        is_special = str(row.get("floor_code") or "").strip() == "16"
        if is_special:
            special_brand_key = brand_code or (
                "__fee__" if brand_name == "收费未分配品牌" else "__unidentified__"
            )
            key = f"special:{special_brand_key}"
        else:
            key = group_code
        if key not in brands:
            brands[key] = {
                "row_type": "brand",
                "row_key": key,
                "store_code": str(row.get("store_code") or "").strip(),
                "store_name": str(row.get("store_name") or "").strip(),
                "big_category": "穿着类" if is_special else str(row.get("big_category") or "其他类"),
                "department_code": "" if is_special else str(row.get("department_code") or "").strip(),
                "department_name": "" if is_special else str(row.get("department_name") or "未匹配"),
                "floor_code": "16" if is_special else str(row.get("floor_code") or "").strip(),
                "floor_name": "" if is_special else str(row.get("floor_name") or "未匹配"),
                "area_code": "14" if is_special else str(row.get("area_code") or "").strip(),
                "area_name": "特卖区" if is_special else str(row.get("area_name") or "未匹配"),
                "category_code": "1401" if is_special else str(row.get("category_code") or "").strip(),
                "category_name": "特卖商品" if is_special else str(row.get("category_name") or "未匹配"),
                "group_code": "" if is_special else group_code,
                "group_name": "特卖厅" if is_special else str(row.get("group_name") or group_code),
                "brand_code": brand_code if is_special else "",
                "brand_name": brand_name if is_special else "",
                "is_special_sale": is_special,
                "months": {str(value): empty_metrics() for value in range(1, 13)},
            }

        current = brands[key]["months"][str(month)]
        brands[key]["months"][str(month)] = aggregate_metrics(
            [
                current,
                build_metrics(
                    tax_included_sales=row.get("tax_included_sales"),
                    tax_excluded_sales=row.get("tax_excluded_sales"),
                    gross_profit=row.get("gross_profit"),
                    fee=row.get("fee"),
                    contract_profit=row.get("contract_profit"),
                ),
            ]
        )

    for brand in brands.values():
        brand["annual"] = aggregate_metrics(list(brand["months"].values()))

    regular_brands = sorted(
        (row for row in brands.values() if not row["is_special_sale"]),
        key=lambda row: (
            row["department_code"],
            row["floor_code"],
            row["area_code"],
            row["category_code"],
            row["group_name"],
            row["group_code"],
        ),
    )
    special_brands = sorted(
        (row for row in brands.values() if row["is_special_sale"]),
        key=lambda row: (
            row["brand_name"] == "收费未分配品牌",
            row["brand_name"],
            row["brand_code"],
        ),
    )

    regular_rows: list[dict[str, Any]] = []
    department_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in regular_brands:
        department_groups[(row["department_code"], row["department_name"])].append(row)

    for (department_code, department_name), department_rows in department_groups.items():
        regular_rows.extend(department_rows)
        regular_rows.append(
            _aggregate_rows(
                department_rows,
                row_type="department_total",
                row_key=f"department:{department_code}",
                dimensions={
                    "store_code": department_rows[0]["store_code"],
                    "store_name": department_rows[0]["store_name"],
                    "big_category": "",
                    "department_code": department_code,
                    "department_name": department_name,
                    "floor_code": "",
                    "floor_name": "",
                    "area_code": "",
                    "area_name": "",
                    "category_code": "",
                    "category_name": "",
                    "group_code": "",
                    "group_name": department_name,
                    "brand_code": "",
                    "brand_name": "",
                    "is_special_sale": False,
                },
            )
        )

    if regular_brands:
        regular_total = _aggregate_rows(
            regular_brands,
            row_type="store_total",
            row_key="regular:total",
            dimensions={
                "store_code": regular_brands[0]["store_code"],
                "store_name": regular_brands[0]["store_name"],
                "big_category": "",
                "department_code": "",
                "department_name": "",
                "floor_code": "",
                "floor_name": "",
                "area_code": "",
                "area_name": "",
                "category_code": "",
                "category_name": "",
                "group_code": "",
                "group_name": "普通品牌合计",
                "brand_code": "",
                "brand_name": "",
                "is_special_sale": False,
            },
        )
        regular_rows.append(regular_total)

    if special_brands:
        special_total = _aggregate_rows(
            special_brands,
            row_type="special_total",
            row_key="special:total",
            dimensions={
                "store_code": special_brands[0]["store_code"],
                "store_name": special_brands[0]["store_name"],
                "big_category": "穿着类",
                "department_code": "",
                "department_name": "",
                "floor_code": "16",
                "floor_name": "",
                "area_code": "14",
                "area_name": "特卖区",
                "category_code": "1401",
                "category_name": "特卖商品",
                "group_code": "",
                "group_name": "特卖",
                "brand_code": "",
                "brand_name": "",
                "is_special_sale": True,
            },
        )
        special_rows = special_brands + [special_total]
    else:
        special_rows = []

    all_brands = regular_brands + special_brands
    if all_brands:
        grand_total = _aggregate_rows(
            all_brands,
            row_type="store_total",
            row_key="store:total",
            dimensions={
                "store_code": all_brands[0]["store_code"],
                "store_name": all_brands[0]["store_name"],
                "big_category": "",
                "department_code": "",
                "department_name": "",
                "floor_code": "",
                "floor_name": "",
                "area_code": "",
                "area_name": "",
                "category_code": "",
                "category_name": "",
                "group_code": "",
                "group_name": "门店",
                "brand_code": "",
                "brand_name": "",
                "is_special_sale": False,
            },
        )
    else:
        grand_total = _aggregate_rows(
            [],
            row_type="store_total",
            row_key="store:total",
            dimensions={
                "store_code": "",
                "store_name": "",
                "big_category": "",
                "department_code": "",
                "department_name": "",
                "floor_code": "",
                "floor_name": "",
                "area_code": "",
                "area_name": "",
                "category_code": "",
                "category_name": "",
                "group_code": "",
                "group_name": "门店",
                "brand_code": "",
                "brand_name": "",
                "is_special_sale": False,
            },
        )

    return {
        "regular_rows": regular_rows,
        "special_rows": special_rows,
        "grand_total": grand_total,
        "quality": {
            "regular_brand_count": len(regular_brands),
            "special_brand_count": sum(
                1
                for row in special_brands
                if row["brand_name"] != "收费未分配品牌"
            ),
            "missing_area_category_count": sum(
                1
                for row in regular_brands
                if row["area_name"] == "未匹配" or row["category_name"] == "未匹配"
            ),
            "latest_sales_date": latest_sales_date.isoformat() if latest_sales_date else None,
        },
    }


def load_non_rental_monthly_revenue_report(
    db: Any,
    scope_filter_sql: TrustedScopeSql,
    scope_params: Mapping[str, Any],
    *,
    financial_year: int,
    selected_store: str,
    selected_department: str | None = None,
) -> dict[str, Any]:
    sql, params = build_non_rental_monthly_revenue_query(
        financial_year,
        scope_filter_sql,
        scope_params,
        selected_store=selected_store,
        selected_department=selected_department,
    )
    db.execute(
        text(f"SET LOCAL statement_timeout = '{QUERY_TIMEOUT_SECONDS}s'"),
        {},
    )
    source_rows = db.execute(text(sql), params).mappings().all()
    normalized = normalize_non_rental_monthly_revenue_rows(source_rows)
    start_date, end_date = financial_year_period(financial_year)
    periods = [
        {
            "month": month,
            "label": f"{month}月",
            "start_date": financial_month_period(financial_year, month)[0].isoformat(),
            "end_date": financial_month_period(financial_year, month)[1].isoformat(),
        }
        for month in range(1, 13)
    ]
    return {
        "financial_year": financial_year,
        "dates": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "periods": periods,
        "selected_store": selected_store,
        "selected_department": selected_department,
        **normalized,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
