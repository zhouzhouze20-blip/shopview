from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any, Mapping

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.od0002_report import TrustedScopeSql


REPORT_NAME = "门店其他业务收入"
SUPPORTED_STORE_CODES = ("601", "602", "603", "604")
STORE_DISPLAY_NAMES = {
    "601": "中心",
    "602": "大楼",
    "603": "新世纪",
    "604": "半山",
}
STORE_SORT_ORDER = {"601": 0, "602": 1, "604": 2, "603": 3}

# 顺序与原报表一致；未在三家门店出现过的科目仍保留在查询口径中，
# 如后续产生数据会以科目编码作为可审计的兜底名称展示。
SUBJECT_DEFINITIONS: tuple[tuple[str, str, str], ...] = (
    ("605110", "合同收费收入", "综合管理费"),
    ("605112", "合同收费收入", "电费收入"),
    ("605111", "合同收费收入", "信用卡手续费"),
    ("605116", "合同收费收入", "储值卡管理费"),
    ("605113", "合同收费收入", "店庆服务费"),
    ("605106", "合同收费收入", "广告服务费"),
    ("605117", "合同收费收入", "会员服务费"),
    ("605114", "合同收费收入", "仓库服务费"),
    ("605108", "合同收费收入", "能耗服务费"),
    ("60515002", "临时收费收入", "办公费用"),
    ("60515004", "临时收费收入", "修理服务费"),
    ("60515008", "临时收费收入", "水费"),
    ("60515009", "临时收费收入", "财务费用"),
    ("60515010", "临时收费收入", "罚款"),
    ("60515099", "临时收费收入", "其他"),
    ("605104", "租赁", "租赁收入"),
    ("605109", "停车收入", "停车收入"),
    ("60515007", "多经收入", "服务费"),
    ("60515006", "多经收入", "能源费"),
    ("605199", "其他收入", "其他收入"),
)
TARGET_SUBJECT_CODES = (
    "605110", "605112", "605111", "605116", "605113", "605106",
    "605117", "605114", "605104", "605108", "60515001", "60515002",
    "60515003", "60515004", "60515005", "60515006", "60515007",
    "60515008", "60515009", "60515010", "60515099", "605109",
    "605199", "605105", "605107", "605103",
)
SUBJECT_LABELS = {
    code: {"category": category, "fee_name": fee_name, "order": index}
    for index, (code, category, fee_name) in enumerate(SUBJECT_DEFINITIONS)
}
CATEGORY_ORDER = {
    "合同收费收入": 0,
    "临时收费收入": 1,
    "租赁": 2,
    "停车收入": 3,
    "多经收入": 4,
    "其他收入": 5,
}

FINANCE_STORE_CODE_SQL = """
CASE
  WHEN f.pk_corp = '1018' AND f.valuecode LIKE '21%' THEN '601'
  WHEN f.pk_corp = '1018' AND f.valuecode LIKE '22%' THEN '602'
  WHEN f.pk_corp = '1021' AND f.valuecode LIKE '31%' THEN '603'
  WHEN f.pk_corp = '1084' AND f.valuecode LIKE '33%' THEN '604'
  ELSE NULL
END
""".strip()


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


def build_store_other_business_income_query(
    financial_year: int,
    end_period: int,
    scope_filter_sql: str | TrustedScopeSql,
    scope_params: Mapping[str, Any],
    *,
    selected_store: str | None = None,
) -> tuple[str, dict[str, Any]]:
    if not 1 <= end_period <= 12:
        raise ValueError("end_period must be between 1 and 12")
    store_code = (selected_store or "").strip()
    if store_code and store_code not in SUPPORTED_STORE_CODES:
        raise ValueError("unsupported store for other business income report")

    params = dict(scope_params)
    params.update(
        {
            "financial_years": [str(financial_year - 1), str(financial_year)],
            "periods": list(range(1, end_period + 1)),
            "subject_codes": list(TARGET_SUBJECT_CODES),
            "selected_store": store_code,
        }
    )
    scope_sql = _trusted_scope_value(scope_filter_sql)
    sql = f"""
WITH finance_rows AS MATERIALIZED (
  SELECT
    st.store_id::text AS store_id,
    st.store_code,
    CASE st.store_code
      WHEN '601' THEN '中心'
      WHEN '602' THEN '大楼'
      WHEN '603' THEN '新世纪'
      WHEN '604' THEN '半山'
      ELSE st.store_name
    END AS store_name,
    TRIM(f.valuecode) AS department_code,
    COALESCE(NULLIF(TRIM(f.valuename), ''), TRIM(f.valuecode)) AS department_name,
    f.account_year::int AS account_year,
    f.account_period::int AS account_period,
    TRIM(f.subject_code) AS subject_code,
    COALESCE(f.localdebitamount, 0) AS debit_amount,
    COALESCE(f.localcreditamount, 0) AS credit_amount
  FROM bh_dw_gl_detail_fact2 f
  JOIN stores st
    ON st.store_code = ({FINANCE_STORE_CODE_SQL})
   AND st.is_active = TRUE
  WHERE f.account_year = ANY(:financial_years)
    AND f.account_period::int = ANY(:periods)
    AND TRIM(f.subject_code) = ANY(:subject_codes)
    AND TRIM(COALESCE(f.valuecode, '')) NOT IN ('210109', '220109', '310109', '330109')
    AND (:selected_store = '' OR st.store_code = :selected_store)
    {scope_sql}
)
SELECT
  store_id,
  store_code,
  store_name,
  department_code,
  department_name,
  account_year,
  account_period,
  subject_code,
  SUM(debit_amount) AS debit_amount,
  SUM(credit_amount) AS credit_amount,
  SUM(credit_amount - debit_amount) AS net_income
FROM finance_rows
GROUP BY
  store_id, store_code, store_name, department_code, department_name,
  account_year, account_period, subject_code
ORDER BY store_code, department_code, subject_code, account_year, account_period
"""
    return sql, params


def _decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _comparison(current: Decimal, prior: Decimal) -> dict[str, float | None]:
    difference = current - prior
    return {
        "current": float(current),
        "prior": float(prior),
        "difference": float(difference),
        "rate": float(difference / prior) if prior != 0 else None,
    }


def _subject_label(subject_code: str) -> dict[str, Any]:
    known = SUBJECT_LABELS.get(subject_code)
    if known:
        return known
    return {
        "category": "其他收入",
        "fee_name": f"科目{subject_code}",
        "order": len(SUBJECT_DEFINITIONS) + TARGET_SUBJECT_CODES.index(subject_code),
    }


def _row_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        CATEGORY_ORDER.get(row["category"], 99),
        row["subject_order"],
        row["subject_code"],
    )


def _build_rows(
    raw_rows: list[dict[str, Any]],
    *,
    financial_year: int,
    end_period: int,
    dimension: str,
) -> list[dict[str, Any]]:
    prior_year = financial_year - 1
    grouped: dict[tuple[Any, ...], dict[str, Any]] = {}
    for source in raw_rows:
        store_code = str(source.get("store_code") or "").strip()
        department_code = str(source.get("department_code") or "").strip()
        if dimension == "store":
            group_key = (store_code,)
        else:
            group_key = (store_code, department_code)
        subject_code = str(source.get("subject_code") or "").strip()
        key = (*group_key, subject_code)
        if key not in grouped:
            label = _subject_label(subject_code)
            grouped[key] = {
                "row_type": "detail",
                "store_code": store_code,
                "store_name": str(source.get("store_name") or STORE_DISPLAY_NAMES.get(store_code, store_code)),
                "department_code": department_code if dimension == "department" else None,
                "department_name": (
                    str(source.get("department_name") or department_code)
                    if dimension == "department"
                    else None
                ),
                "subject_code": subject_code,
                "subject_order": label["order"],
                "category": label["category"],
                "fee_name": label["fee_name"],
                "amounts": defaultdict(Decimal),
            }
        year = int(source["account_year"])
        period = int(source["account_period"])
        grouped[key]["amounts"][(year, period)] += _decimal(source.get("net_income"))

    details_by_group: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for detail in grouped.values():
        amounts = detail.pop("amounts")
        months: dict[str, dict[str, float | None]] = {}
        annual_current = Decimal("0")
        annual_prior = Decimal("0")
        for period in range(1, end_period + 1):
            current = amounts[(financial_year, period)]
            prior = amounts[(prior_year, period)]
            annual_current += current
            annual_prior += prior
            months[str(period)] = _comparison(current, prior)
        detail["months"] = months
        detail["total"] = _comparison(annual_current, annual_prior)
        if dimension == "store":
            group_key = (detail["store_code"],)
        else:
            group_key = (detail["store_code"], detail["department_code"])
        details_by_group[group_key].append(detail)

    output: list[dict[str, Any]] = []
    group_keys = sorted(
        details_by_group,
        key=lambda key: (
            STORE_SORT_ORDER.get(key[0], 99),
            details_by_group[key][0].get("department_name") or "",
            key,
        ),
    )
    for group_key in group_keys:
        details = sorted(details_by_group[group_key], key=_row_sort_key)
        category_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for detail in details:
            category_rows[detail["category"]].append(detail)

        for category in sorted(category_rows, key=lambda value: CATEGORY_ORDER.get(value, 99)):
            category_details = category_rows[category]
            output.extend(category_details)
            output.append(
                _aggregate_output_rows(
                    category_details,
                    row_type="category_total",
                    category=category,
                    fee_name="小计",
                    end_period=end_period,
                )
            )
        output.append(
            _aggregate_output_rows(
                details,
                row_type="grand_total",
                category="合计",
                fee_name="",
                end_period=end_period,
            )
        )
    return output


def _aggregate_output_rows(
    rows: list[dict[str, Any]],
    *,
    row_type: str,
    category: str,
    fee_name: str,
    end_period: int,
) -> dict[str, Any]:
    first = rows[0]
    months: dict[str, dict[str, float | None]] = {}
    for period in range(1, end_period + 1):
        current = sum((_decimal(row["months"][str(period)]["current"]) for row in rows), Decimal("0"))
        prior = sum((_decimal(row["months"][str(period)]["prior"]) for row in rows), Decimal("0"))
        months[str(period)] = _comparison(current, prior)
    annual_current = sum((_decimal(row["total"]["current"]) for row in rows), Decimal("0"))
    annual_prior = sum((_decimal(row["total"]["prior"]) for row in rows), Decimal("0"))
    return {
        "row_type": row_type,
        "store_code": first["store_code"],
        "store_name": first["store_name"],
        "department_code": first.get("department_code"),
        "department_name": first.get("department_name"),
        "subject_code": None,
        "subject_order": 999,
        "category": category,
        "fee_name": fee_name,
        "months": months,
        "total": _comparison(annual_current, annual_prior),
    }


def normalize_store_other_business_income_rows(
    raw_rows: list[dict[str, Any]],
    *,
    financial_year: int,
    end_period: int,
) -> dict[str, Any]:
    store_rows = _build_rows(
        raw_rows,
        financial_year=financial_year,
        end_period=end_period,
        dimension="store",
    )
    department_rows = _build_rows(
        raw_rows,
        financial_year=financial_year,
        end_period=end_period,
        dimension="department",
    )
    store_totals = [row for row in store_rows if row["row_type"] == "grand_total"]
    if store_totals:
        summary = _aggregate_output_rows(
            store_totals,
            row_type="grand_total",
            category="合计",
            fee_name="",
            end_period=end_period,
        )["total"]
    else:
        summary = _comparison(Decimal("0"), Decimal("0"))
    return {
        "store_rows": store_rows,
        "department_rows": department_rows,
        "summary": summary,
        "quality": {
            "source_row_count": len(raw_rows),
            "store_count": len(store_totals),
            "department_count": sum(
                1 for row in department_rows if row["row_type"] == "grand_total"
            ),
        },
    }


def load_store_other_business_income_report(
    db: Session,
    scope_filter_sql: str | TrustedScopeSql,
    scope_params: Mapping[str, Any],
    *,
    financial_year: int,
    end_period: int,
    selected_store: str | None = None,
) -> dict[str, Any]:
    sql, params = build_store_other_business_income_query(
        financial_year,
        end_period,
        scope_filter_sql,
        scope_params,
        selected_store=selected_store,
    )
    raw_rows = [dict(row) for row in db.execute(text(sql), params).mappings().all()]
    normalized = normalize_store_other_business_income_rows(
        raw_rows,
        financial_year=financial_year,
        end_period=end_period,
    )
    return {
        "report_name": REPORT_NAME,
        "financial_year": financial_year,
        "prior_year": financial_year - 1,
        "end_period": end_period,
        "periods": list(range(1, end_period + 1)),
        "unit": "元",
        "selected_store": (selected_store or "").strip() or None,
        **normalized,
    }
