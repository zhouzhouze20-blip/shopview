"""
收益地图与经营单元日收益 API。
"""

import logging
import unicodedata
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from models.database import get_db
from models.models import User
from routers.auth import get_current_user
from routers.authz import load_business_scope, require_permission, scope_allows_business
from services.department_display_order import department_display_sort_key
from services.monthly_followup_report import financial_month_period, financial_year_period
from services.store_other_business_income_report import FINANCE_STORE_CODE_SQL


router = APIRouter(prefix="/api/revenue-map", tags=["revenue"])
logger = logging.getLogger(__name__)

LOSS_BEARING_FEE_NAME_PREFIX = "损失承担"
LOSS_BEARING_TAX_DIVISOR = "1.13"
REVENUE_DASHBOARD_QUERY_TIMEOUT_SECONDS = 90
REVENUE_MONTHLY_QUERY_TIMEOUT_SECONDS = 90
FUJI_NON_MATCHABLE_FEE_CODES = frozenset({"18", "37", "38", "61", "69", "94", "95"})
FUJI_NON_MATCHABLE_FEE_NAME_KEYWORDS = (
    "保证金",
    "质保金",
    "代扣代缴保险费",
    "旅通",
    "瑞祥",
)
NON_FUJI_MONTH_CLOSE_DEPARTMENTS = {
    "601": frozenset({"210303", "2112", "2113", "2125"}),
    "602": frozenset({"220303", "2212", "2225"}),
    "603": frozenset({"310303", "3112", "3128"}),
}
HISTORICAL_NON_FUJI_MONTH_CLOSE_DEPARTMENTS = {
    # 2025年1月至2026年6月新世纪营运部的NC费用全部属于非富基费用，
    # 不进入富基费用匹配；2026年7月起继续沿用当月月结规则。
    "603": frozenset({"3125"}),
}
REVENUE_GROUP_DEPARTMENT_OVERRIDES = {
    # Goodyear/华瑶租金 is carried under Fuji's broader property department,
    # while NC posts the same supplier and amount to 210303. Keep this as a
    # cabinet-level exception so other 6010205 rows are not reassigned.
    ("601", "6012050002"): ("6010115", "中心物业服务部"),
    ("603", "6030104082"): ("6030116", "新世纪十部(特业)"),
    ("603", "6030104101"): ("6030116", "新世纪十部(特业)"),
    ("603", "6030104096"): ("6030116", "新世纪十部(特业)"),
    ("603", "6030104095"): ("6030116", "新世纪十部(特业)"),
}
REVENUE_GROUP_NC_DEPARTMENT_OVERRIDES = {
    ("601", "6012050002"): "210303",
}

# ODS_CODECHARGE.CCNUM3 fallback snapshot, verified from PAPI on 2026-07-27.
# A valid locally synchronized CODECHARGE.CCNUM3 value takes precedence.
FEE_TAX_RATE_FALLBACKS = {
    "01": "0.05",
    "02": "0.06",
    "04": "0.05",
    "06": "0.06",
    "07": "0.06",
    "08": "0.06",
    "09": "0.06",
    "10": "0.06",
    "11": "0.06",
    "12": "0.06",
    "13": "0.06",
    "14": "0.06",
    "15": "0.06",
    "16": "0.06",
    "19": "0.06",
    "20": "0.06",
    "21": "0.06",
    "22": "0.06",
    "23": "0.13",
    "24": "0.09",
    "25": "0.06",
    "26": "0.06",
    "28": "0.06",
    "29": "0.06",
    "30": "0.06",
    "31": "0.06",
    "32": "0.06",
    "33": "0.06",
    "34": "0.06",
    "35": "0.09",
    "36": "0.06",
    "39": "0.06",
    "41": "0.06",
    "42": "0.09",
    "43": "0.13",
    "44": "0.06",
    "45": "0.06",
    "47": "0.06",
    "48": "0.06",
    "49": "0.06",
    "50": "0.06",
    "51": "0.16",
    "52": "0.10",
    "53": "0.06",
    "55": "0.16",
    "56": "0.10",
    # ODS CCNUM3 is 0.6 for code 57, while CCNUM5 and the fee name both specify 6%.
    "57": "0.06",
    "59": "0.16",
    "60": "0.05",
    "62": "0.13",
    "63": "0.09",
    "64": "0.13",
    "65": "0.09",
    "66": "0.13",
    "67": "0.09",
    "68": "0.13",
    "69": "0.09",
    "70": "0.06",
    "71": "0.06",
    "72": "0.06",
    "73": "0.06",
    "74": "0.06",
    "75": "0.06",
    "76": "0.06",
    "77": "0.13",
    "78": "0.06",
    "79": "0.06",
    "80": "0.13",
    "81": "0.06",
    "ZN": "0.06",
}

# NC and Fuji use different department codes for the same New Century
# departments. Keep the NC code on source/month-close rows for audit, while
# resolving dashboard display and permission scope to Fuji's department code.
REVENUE_DEPARTMENT_ALIASES = (
    ("601", "210303", "6010115", "中心物业服务部"),
    ("601", "2112", "6010108", "中心企划执行部"),
    ("601", "2125", "6010110", "中心营运部"),
    ("601", "2106", "6010117", "中心三部(女装)"),
    ("601", "2107", "6010118", "中心五部(运休)"),
    ("601", "2113", "6010109", "中心企划客服部"),
    ("601", "2116", "6010101", "中心一部(名品)"),
    ("601", "2117", "6010102", "中心四部(男装)"),
    ("601", "2118", "6010103", "中心六部(儿童)"),
    ("601", "2119", "6010104", "中心BF部(超市)"),
    ("601", "2120", "6010112", "中心八部(特业)"),
    ("601", "2121", "6010113", "中心二部(女装)"),
    ("601", "2122", "6010114", "中心一部(化妆)"),
    ("601", "2124", "6010116", "中心七部(家居)"),
    ("602", "2212", "6020105", "大楼市场部"),
    ("602", "2217", "6020101", "营运一部"),
    ("602", "2220", "6020110", "营运二部"),
    ("603", "310303", "6030205", "新世纪物业服务部"),
    ("603", "3117", "6030104", "新世纪九部(超市)"),
    ("603", "3125", "6030109", "新世纪营运部"),
    ("603", "3130", "6030112", "新世纪三部"),
    ("603", "3131", "6030117", "新世纪一部(名品)"),
    ("603", "3132", "6030102", "新世纪二部"),
    ("603", "3133", "6030103", "新世纪六部(男装)"),
    ("603", "3135", "6030106", "新世纪八部(儿童)"),
    ("603", "3137", "6030116", "新世纪十部(特业)"),
    ("603", "3150", "6030113", "新世纪四部"),
    ("603", "3151", "6030114", "新世纪五部(运休)"),
    ("603", "3152", "6030115", "新世纪七部(家居)"),
    ("603", "3153", "6030101", "新世纪一部(化妆)"),
)
REVENUE_DEPARTMENT_ALIAS_LOOKUP = {
    (store_code, source_code): (canonical_code, canonical_name)
    for store_code, source_code, canonical_code, canonical_name
    in REVENUE_DEPARTMENT_ALIASES
}

# Audited NC 6051 subject-to-Fuji fee bridge used by the July 2026
# reconciliation workbook. Keep the source rows on both sides visible in the
# pending-binding view; the mapping only selects comparable Fuji detail and
# never changes either source amount.
REVENUE_SUBJECT_FEE_CODES = {
    "605104": ("01", "04", "60"),
    "605106": ("08", "47"),
    "605108": ("71", "73"),
    "605110": ("02", "06", "07"),
    "605111": ("19", "20", "22"),
    "605112": ("23", "43"),
    "605113": ("16", "75"),
    "605114": ("15", "45"),
    "605116": ("09", "10", "11"),
    "605117": ("12", "13", "14"),
    "60515002": ("72", "74", "81"),
    "60515006": ("77",),
    "60515007": ("25", "29", "76", "79"),
    "60515008": ("24",),
    "60515009": ("26",),
    "60515099": ("30", "44"),
}


def _fuji_fee_codes(value: object) -> list[str]:
    return [
        fee_code.strip()
        for fee_code in str(value or "").split(",")
        if fee_code.strip()
    ]


def _is_fuji_sales_fee_codes(value: object) -> bool:
    """Return whether every Fuji code in a month-close row belongs to sales."""
    fee_codes = _fuji_fee_codes(value)
    return bool(fee_codes) and all(fee_code.startswith("00") for fee_code in fee_codes)


def _is_fuji_non_matchable_fee_row(
    fee_type_code: object,
    fee_type_name: object,
) -> bool:
    """Return whether a Fuji month-close row contains only excluded fee types."""
    fee_codes = _fuji_fee_codes(fee_type_code)
    if fee_codes:
        return all(
            fee_code.startswith("00") or fee_code in FUJI_NON_MATCHABLE_FEE_CODES
            for fee_code in fee_codes
        )
    normalized_name = str(fee_type_name or "").strip()
    return bool(normalized_name) and any(
        keyword in normalized_name
        for keyword in FUJI_NON_MATCHABLE_FEE_NAME_KEYWORDS
    )


def _is_non_fuji_month_close_department(row: dict) -> bool:
    """Return whether a month-close row belongs to a non-Fuji department."""
    store_code = str(row.get("store_code") or "").strip()
    department_code = str(row.get("source_department_code") or "").strip()
    if department_code in NON_FUJI_MONTH_CLOSE_DEPARTMENTS.get(
        store_code,
        frozenset(),
    ):
        return True
    period_month = str(row.get("period_month") or "").strip()
    return (
        "2025-01" <= period_month <= "2026-06"
        and department_code
        in HISTORICAL_NON_FUJI_MONTH_CLOSE_DEPARTMENTS.get(
            store_code,
            frozenset(),
        )
    )


def _month_close_fuji_department(
    store_code: object,
    group_code: object,
    department_code: object,
    department_name: object,
) -> tuple[str, str]:
    """Return the audited cabinet-level department used for NC matching."""
    normalized_store_code = str(store_code or "").strip()
    normalized_group_code = str(group_code or "").strip()
    override = REVENUE_GROUP_DEPARTMENT_OVERRIDES.get(
        (normalized_store_code, normalized_group_code)
    )
    if override:
        return override
    return (
        str(department_code or "").strip(),
        str(department_name or "").strip(),
    )


def _month_close_adjustment_fuji_department(adjustment: dict) -> str:
    """Resolve the Fuji department used to attach source detail to an adjustment."""
    department_code = str(adjustment.get("department_code") or "").strip()
    if department_code:
        return department_code
    override, _override_name = _month_close_fuji_department(
        adjustment.get("store_code"),
        adjustment.get("source_group_code"),
        "",
        "",
    )
    return override


def _month_close_nc_department_sql() -> str:
    """Return the NC department key, including audited cabinet-level exceptions."""
    clauses = [
        (
            "WHEN TRIM(store.store_code) = "
            f"'{store_code}' AND TRIM(adjustment.source_group_code) = "
            f"'{group_code}' THEN '{department_code}'"
        )
        for (store_code, group_code), department_code
        in REVENUE_GROUP_NC_DEPARTMENT_OVERRIDES.items()
    ]
    return (
        "CASE "
        + " ".join(clauses)
        + " ELSE NULLIF(TRIM(adjustment.source_department_code), '') END"
    )


def _collapse_legacy_mapped_fuji_rows(rows: list[dict]) -> list[dict]:
    """Drop stale unmapped Fuji rows claimed by a mapped NC subject row.

    Older imported workbooks retain one Fuji-only adjustment per source row.
    When a fee-to-subject bridge is added later, the mapped NC adjustment owns
    those Fuji details for reconciliation. Suppress the legacy adjustment only
    inside the same month close and source department, and only when every fee
    code on it is covered by that mapped subject.
    """
    mapped_targets: set[tuple[int, str, str]] = set()
    for row in rows:
        subject_code = str(row.get("source_subject_code") or "").strip()
        for fee_code in REVENUE_SUBJECT_FEE_CODES.get(subject_code, ()):
            mapped_targets.add(
                (
                    int(row["month_close_id"]),
                    str(row.get("source_department_code") or "").strip(),
                    fee_code,
                )
            )

    filtered_rows = []
    for row in rows:
        subject_code = str(row.get("source_subject_code") or "").strip()
        fee_codes = _fuji_fee_codes(row.get("fee_type_code"))
        scope = (
            int(row["month_close_id"]),
            str(row.get("source_department_code") or "").strip(),
        )
        is_legacy_mapped_row = (
            subject_code in {"", "未映射"}
            and bool(fee_codes)
            and all((*scope, fee_code) in mapped_targets for fee_code in fee_codes)
        )
        if not is_legacy_mapped_row:
            filtered_rows.append(row)
    return filtered_rows


def _revenue_department_aliases_cte() -> str:
    """Return the audited NC-to-Fuji department bridge used by revenue views."""
    values = ",\n".join(
        "              "
        f"('{store_code}', '{source_code}', '{canonical_code}', '{canonical_name}')"
        for store_code, source_code, canonical_code, canonical_name
        in REVENUE_DEPARTMENT_ALIASES
    )
    return f"""
        revenue_department_aliases(
          store_code,
          source_department_code,
          canonical_department_code,
          canonical_department_name
        ) AS MATERIALIZED (
          VALUES
{values}
        )
    """


def _loss_bearing_fee_condition(alias: str = "fee") -> str:
    """Return the fee-name condition whose untaxed amount belongs to gross profit."""
    return (
        f"TRIM(COALESCE({alias}.fee_type_name, '')) "
        f"LIKE '{LOSS_BEARING_FEE_NAME_PREFIX}%'"
    )


def _contract_group_bindings_cte() -> str:
    """Resolve active unit/contract bindings to the groups carried by each contract."""
    return """
        contract_group_bindings AS MATERIALIZED (
            SELECT DISTINCT
              b.id AS binding_id,
              b.shop_unit_id AS unit_id,
              bu.floor_id,
              bu.unit_code,
              TRIM(unit_floor.store_code) AS store_code,
              UPPER(TRIM(cmf.cmfmfid)) AS source_group_code_norm,
              b.contract_id AS contract_code,
              UPPER(TRIM(b.contract_id)) AS contract_code_norm,
              UPPER(TRIM(cm.cmsupid)) AS contract_supplier_code_norm,
              TRIM(cm.cmwmid) AS contract_operation_mode_norm,
              b.business_type,
              b.supplier_id,
              b.brand_id,
              b.start_date AS binding_start_date,
              b.end_date AS binding_end_date,
              b.is_primary,
              cm.cmeffdate::date AS contract_start_date,
              cm.cmlapdate::date AS contract_end_date,
              cm.cmsupid AS contract_supplier_code,
              cm.cmppname AS contract_supplier_name,
              cm.cmwmid AS contract_operation_mode
            FROM business_unit_binding b
            JOIN business_units bu
              ON bu.id = b.shop_unit_id
            JOIN floors unit_floor
              ON unit_floor.id = bu.floor_id
            JOIN contmain cm
              ON cm.cmcontno = TRIM(b.contract_id)
             AND TRIM(cm.cmjsmkt) = TRIM(unit_floor.store_code)
            JOIN contmanaframe cmf
              ON cmf.cmfcontno = cm.cmcontno
             AND TRIM(cmf.cmfmarket) = TRIM(unit_floor.store_code)
            WHERE b.shop_unit_id IS NOT NULL
              AND NULLIF(TRIM(b.contract_id), '') IS NOT NULL
              AND COALESCE(b.status, 'ACTIVE') = 'ACTIVE'
              AND cm.cmeffdate IS NOT NULL
              AND cm.cmlapdate IS NOT NULL
              AND NULLIF(TRIM(cmf.cmfmfid), '') IS NOT NULL
        )
    """


def _live_sales_ctes(sales_date_filter: str, sales_store_filter: str = "") -> str:
    """Build the read-only sales source used by map totals and unit details."""
    contract_group_bindings_cte = _contract_group_bindings_cte()
    return f"""
        sales_by_group AS (
            SELECT
              s.sglhsrq::date AS revenue_date,
              NULLIF(TRIM(s.sglmarket), '') AS store_code,
              NULLIF(TRIM(s.sglmfid), '') AS source_group_code,
              NULLIF(TRIM(s.sglsupid), '') AS source_supplier_code,
              NULLIF(TRIM(s.sglwmid), '') AS source_operation_mode,
              COALESCE(SUM(s.sglsl), 0)::numeric(18,4) AS sales_qty,
              COALESCE(
                SUM(
                  (COALESCE(s.sglxssr, 0) + COALESCE(s.sglpfsr, 0))
                  / NULLIF(1 + COALESCE(s.sglxstax, 0), 0)
                ),
                0
              )::numeric AS sales_amount,
              COALESCE(
                SUM(COALESCE(s.sgln2, 0) / NULLIF(1 + COALESCE(s.sglxstax, 0), 0)),
                0
              )::numeric AS gross_profit_amount,
              COALESCE(SUM(s.sgln2), 0)::numeric AS front_gross_profit_amount,
              COUNT(*)::integer AS source_count,
              MIN(s.sglbillno::varchar) AS first_bill_no
            FROM salegoodslist s
            WHERE {sales_date_filter}
              AND NULLIF(TRIM(s.sglmfid), '') IS NOT NULL
              {sales_store_filter}
            GROUP BY
              s.sglhsrq,
              NULLIF(TRIM(s.sglmarket), ''),
              NULLIF(TRIM(s.sglmfid), ''),
              NULLIF(TRIM(s.sglsupid), ''),
              NULLIF(TRIM(s.sglwmid), '')
        ),
        {contract_group_bindings_cte},
        ranked_live_sales AS (
            SELECT
              st.store_id,
              sales_by_group.store_code,
              candidate.floor_id,
              candidate.unit_id,
              candidate.unit_code,
              sales_by_group.revenue_date,
              sales_by_group.source_group_code,
              sales_by_group.source_supplier_code,
              sales_by_group.source_operation_mode,
              mf.mfcname AS source_group_name,
              COALESCE(
                NULLIF(sales_by_group.source_operation_mode, ''),
                NULLIF(candidate.contract_operation_mode, ''),
                NULLIF(candidate.business_type, ''),
                NULLIF(mf.mfjyfs, '')
              ) AS operation_mode,
              COALESCE(
                NULLIF(candidate.supplier_id, ''),
                candidate.contract_supplier_code
              ) AS supplier_code,
              COALESCE(
                NULLIF(candidate.brand_id, ''),
                candidate.contract_supplier_name
              ) AS supplier_name,
              candidate.contract_code,
              sales_by_group.sales_qty,
              sales_by_group.sales_amount,
              sales_by_group.gross_profit_amount,
              sales_by_group.front_gross_profit_amount,
              sales_by_group.source_count,
              sales_by_group.first_bill_no,
              ROW_NUMBER() OVER (
                PARTITION BY
                  sales_by_group.revenue_date,
                  sales_by_group.store_code,
                  sales_by_group.source_group_code,
                  sales_by_group.source_supplier_code,
                  sales_by_group.source_operation_mode
                ORDER BY
                  COALESCE(candidate.is_primary, false) DESC,
                  candidate.contract_start_date DESC,
                  candidate.binding_id ASC
              ) AS resolution_rank
            FROM sales_by_group
            JOIN stores st
              ON TRIM(st.store_code) = sales_by_group.store_code
            JOIN manaframe mf
              ON UPPER(TRIM(mf.mfcode)) = UPPER(TRIM(sales_by_group.source_group_code))
             AND UPPER(TRIM(COALESCE(mf.mfstatus, ''))) = 'Y'
            JOIN contract_group_bindings candidate
              ON candidate.store_code = sales_by_group.store_code
             AND candidate.source_group_code_norm = UPPER(TRIM(sales_by_group.source_group_code))
             AND candidate.contract_supplier_code_norm = UPPER(TRIM(sales_by_group.source_supplier_code))
             AND candidate.contract_operation_mode_norm = TRIM(sales_by_group.source_operation_mode)
             AND (
               candidate.binding_start_date IS NULL
               OR candidate.binding_start_date <= sales_by_group.revenue_date
             )
             AND (
               candidate.binding_end_date IS NULL
               OR candidate.binding_end_date >= sales_by_group.revenue_date
             )
             AND candidate.contract_start_date <= sales_by_group.revenue_date
             AND candidate.contract_end_date >= sales_by_group.revenue_date
        ),
        live_sales AS (
            SELECT
              ranked.store_id,
              ranked.store_code,
              ranked.floor_id,
              ranked.unit_id,
              ranked.unit_code,
              ranked.revenue_date,
              ranked.source_group_code,
              ranked.source_supplier_code,
              ranked.source_operation_mode,
              ranked.source_group_name,
              ranked.operation_mode,
              ranked.supplier_code,
              ranked.supplier_name,
              ranked.contract_code,
              ranked.sales_qty,
              ranked.sales_amount,
              ranked.gross_profit_amount,
              ranked.front_gross_profit_amount,
              ranked.source_count,
              ranked.first_bill_no
            FROM ranked_live_sales ranked
            WHERE ranked.resolution_rank = 1
        )
    """


def _unmatched_sales_ctes(sales_date_filter: str, sales_store_filter: str = "") -> str:
    """Build the exact unmatched sales set shared by the summary and detail APIs."""
    live_sales_ctes = _live_sales_ctes(sales_date_filter, sales_store_filter)
    return f"""
        {live_sales_ctes},
        unmatched_sales AS (
            SELECT
              source.revenue_date,
              source.store_code,
              source.source_group_code,
              source.source_supplier_code,
              source.source_operation_mode,
              master_group.mfcname AS source_group_name,
              source.sales_qty,
              source.sales_amount,
              source.gross_profit_amount,
              source.source_count,
              source.first_bill_no,
              COALESCE(effective_contracts.contract_codes, ARRAY[]::text[]) AS contract_codes,
              CASE
                WHEN master_group.mfcode IS NULL
                  THEN 'GROUP_MASTER_NOT_FOUND'
                WHEN UPPER(TRIM(COALESCE(master_group.mfstatus, ''))) <> 'Y'
                  THEN 'GROUP_MASTER_INACTIVE'
                WHEN COALESCE(cardinality(effective_contracts.contract_codes), 0) = 0
                  THEN 'NO_EFFECTIVE_CONTRACT'
                WHEN NOT EXISTS (
                    SELECT 1
                    FROM contract_group_bindings candidate
                    WHERE candidate.store_code = source.store_code
                      AND candidate.source_group_code_norm = UPPER(TRIM(source.source_group_code))
                      AND (
                        candidate.binding_start_date IS NULL
                        OR candidate.binding_start_date <= source.revenue_date
                      )
                      AND (
                        candidate.binding_end_date IS NULL
                        OR candidate.binding_end_date >= source.revenue_date
                      )
                      AND candidate.contract_start_date <= source.revenue_date
                      AND candidate.contract_end_date >= source.revenue_date
                )
                  THEN 'NO_UNIT_BINDING'
                ELSE 'MATCHING_RULE_GAP'
              END AS reason_code
            FROM sales_by_group source
            LEFT JOIN LATERAL (
                SELECT mf.mfcode, mf.mfcname, mf.mfstatus
                FROM manaframe mf
                WHERE UPPER(TRIM(mf.mfcode)) = UPPER(TRIM(source.source_group_code))
                ORDER BY mf.mfcode
                LIMIT 1
            ) master_group ON true
            LEFT JOIN LATERAL (
                SELECT ARRAY_AGG(
                    DISTINCT TRIM(cm.cmcontno)::text
                    ORDER BY TRIM(cm.cmcontno)::text
                ) AS contract_codes
                    FROM contmanaframe cmf
                    JOIN contmain cm
                      ON cm.cmcontno = cmf.cmfcontno
                     AND TRIM(cm.cmjsmkt) = TRIM(cmf.cmfmarket)
                    WHERE TRIM(cmf.cmfmarket) = source.store_code
                      AND UPPER(TRIM(cmf.cmfmfid)) = UPPER(TRIM(source.source_group_code))
                      AND TRIM(cm.cmsupid) = source.source_supplier_code
                      AND TRIM(cm.cmwmid) = source.source_operation_mode
                      AND cm.cmeffdate::date <= source.revenue_date
                      AND cm.cmlapdate::date >= source.revenue_date
            ) effective_contracts ON true
            WHERE master_group.mfcode IS NULL
               OR UPPER(TRIM(COALESCE(master_group.mfstatus, ''))) <> 'Y'
               OR NOT EXISTS (
                    SELECT 1
                    FROM contract_group_bindings candidate
                    WHERE candidate.store_code = source.store_code
                      AND candidate.source_group_code_norm = UPPER(TRIM(source.source_group_code))
                      AND candidate.contract_supplier_code_norm = UPPER(TRIM(source.source_supplier_code))
                      AND candidate.contract_operation_mode_norm = TRIM(source.source_operation_mode)
                      AND (
                        candidate.binding_start_date IS NULL
                        OR candidate.binding_start_date <= source.revenue_date
                      )
                      AND (
                        candidate.binding_end_date IS NULL
                        OR candidate.binding_end_date >= source.revenue_date
                      )
                      AND candidate.contract_start_date <= source.revenue_date
                      AND candidate.contract_end_date >= source.revenue_date
               )
        )
    """


def _live_fees_cte(
    fee_date_filter: str,
    *,
    date_basis: str = "occurrence",
) -> str:
    """Resolve fee rows through their contract/group relationship to a unit."""
    if date_basis not in {"occurrence", "payment"}:
        raise ValueError(f"unsupported fee date basis: {date_basis}")

    loss_bearing_fee_condition = _loss_bearing_fee_condition("fee")
    fallback_rate_rows = ",\n".join(
        f"              ('{fee_code}', {tax_rate}::numeric)"
        for fee_code, tax_rate in FEE_TAX_RATE_FALLBACKS.items()
    )
    if date_basis == "payment":
        payment_reference_ctes = f"""
        fee_payment_references AS (
            SELECT
              'JOINT'::text AS source_kind,
              UPPER(TRIM(pb.pbpaybillno)) AS payment_no_norm,
              NULLIF(TRIM(pb.pbpaybillno), '') AS payment_no,
              NULLIF(TRIM(pb.pbjsno), '') AS settlement_no,
              UPPER(TRIM(pb.pbmfid)) AS source_group_code_norm,
              UPPER(
                COALESCE(
                  NULLIF(TRIM(pb.pbcontno), ''),
                  NULLIF(TRIM(pb.pbmcontno), '')
                )
              ) AS contract_code_norm,
              pb.pbjssdate::date AS period_start,
              pb.pbjsedate::date AS period_end,
              ssh.paydate::date AS payment_date,
              pb.pbseq AS source_sequence
            FROM paybatch pb
            JOIN supsettlehead ssh
              ON TRIM(ssh.sshbillno) = TRIM(pb.pbjsno)
            WHERE NULLIF(TRIM(pb.pbpaybillno), '') IS NOT NULL
              AND NULLIF(TRIM(pb.pbjsno), '') IS NOT NULL
              AND ssh.paydate IS NOT NULL
              AND TRIM(COALESCE(pb.pbwmid, '')) <> '5'

            UNION ALL

            SELECT
              'RENTAL'::text AS source_kind,
              UPPER(TRIM(mph.sphbillno)) AS payment_no_norm,
              NULLIF(TRIM(mph.sphbillno), '') AS payment_no,
              NULL::text AS settlement_no,
              UPPER(TRIM(mph.sphmfid)) AS source_group_code_norm,
              UPPER(TRIM(mph.sphcontno)) AS contract_code_norm,
              NULL::date AS period_start,
              NULL::date AS period_end,
              mph.sphpaydate::date AS payment_date,
              NULL::numeric AS source_sequence
            FROM mallsuppayhead mph
            WHERE NULLIF(TRIM(mph.sphbillno), '') IS NOT NULL
              AND mph.sphpaydate IS NOT NULL
        ),
        fee_payment_references_in_range AS MATERIALIZED (
            SELECT payment_ref.*
            FROM fee_payment_references payment_ref
            WHERE {fee_date_filter}
        ),
        fee_rows_with_payment AS MATERIALIZED (
            SELECT
              fee.*,
              payment_ref.payment_date AS resolved_payment_date,
              payment_ref.payment_no AS resolved_payment_no,
              payment_ref.settlement_no AS resolved_settlement_no,
              ROW_NUMBER() OVER (
                PARTITION BY fee.id
                ORDER BY
                  CASE
                    WHEN payment_ref.contract_code_norm = UPPER(TRIM(fee.contract_code))
                      THEN 0
                    ELSE 1
                  END,
                  CASE WHEN payment_ref.source_kind = 'JOINT' THEN 0 ELSE 1 END,
                  payment_ref.source_sequence DESC NULLS LAST,
                  payment_ref.settlement_no DESC NULLS LAST
              ) AS payment_resolution_rank
            FROM unit_revenue_fee_detail fee
            JOIN fee_payment_references_in_range payment_ref
              ON payment_ref.payment_no_norm = UPPER(TRIM(fee.source_doc_no))
             AND payment_ref.source_group_code_norm = UPPER(TRIM(fee.source_group_code))
             AND (
               payment_ref.contract_code_norm IS NULL
               OR payment_ref.contract_code_norm = UPPER(TRIM(fee.contract_code))
             )
             AND (
               payment_ref.source_kind = 'RENTAL'
               OR fee.revenue_date BETWEEN payment_ref.period_start AND payment_ref.period_end
             )
        ),
        """
        fee_source_relation = "fee_rows_with_payment fee"
        fee_source_filter = "fee.payment_resolution_rank = 1"
        fee_source_effective_date_expression = "fee.resolved_payment_date"
        fee_source_payment_no_expression = "fee.resolved_payment_no"
        fee_source_settlement_no_expression = "fee.resolved_settlement_no"
        fee_source_payment_date_expression = "fee.resolved_payment_date"
        effective_date_expression = "fee.effective_revenue_date"
        revenue_month_expression = "TO_CHAR(fee.effective_revenue_date, 'YYYY-MM')"
        binding_date_expression = "fee.occurrence_date"
    else:
        payment_reference_ctes = ""
        fee_source_relation = "unit_revenue_fee_detail fee"
        fee_source_filter = fee_date_filter
        fee_source_effective_date_expression = "fee.revenue_date"
        fee_source_payment_no_expression = (
            "NULLIF(NULLIF(TRIM(fee.source_doc_no), ''), '{}')"
        )
        fee_source_settlement_no_expression = "NULL::text"
        fee_source_payment_date_expression = "NULL::date"
        effective_date_expression = "fee.revenue_date"
        revenue_month_expression = "fee.revenue_month"
        binding_date_expression = "fee.revenue_date"

    return f"""
        reference_fee_tax_rates(fee_type_code, tax_rate) AS (
            VALUES
{fallback_rate_rows}
        ),
        fee_tax_rates AS MATERIALIZED (
            SELECT
              reference.fee_type_code,
              COALESCE(
                CASE
                  WHEN charge.ccnum3 BETWEEN 0 AND 0.20 THEN charge.ccnum3
                  ELSE NULL
                END,
                reference.tax_rate
              ) AS tax_rate
            FROM reference_fee_tax_rates reference
            LEFT JOIN codecharge charge
              ON TRIM(charge.cccode) = reference.fee_type_code
        ),
        ticket_reduction_fee_keys AS MATERIALIZED (
            SELECT DISTINCT
              UPPER(TRIM(charge.sscpaybillno)) AS payment_bill_no_norm,
              UPPER(TRIM(charge.sscmfid)) AS source_group_code_norm,
              UPPER(TRIM(charge.ssccontno)) AS contract_code_norm,
              UPPER(TRIM(charge.sscid)) AS fee_type_code_norm
            FROM ods.erp_supsetcharge charge
            WHERE TRIM(COALESCE(charge.person1, '')) = 'Y'
              AND NULLIF(TRIM(charge.sscpaybillno), '') IS NOT NULL
        ),
        {payment_reference_ctes}
        fee_source_rows AS MATERIALIZED (
            SELECT
              fee.*,
              fee.revenue_date AS occurrence_date,
              {fee_source_effective_date_expression} AS effective_revenue_date,
              {fee_source_payment_no_expression} AS payment_no,
              {fee_source_settlement_no_expression} AS settlement_no,
              {fee_source_payment_date_expression} AS payment_date,
              fee_tax_rates.tax_rate AS reference_tax_rate,
              ROW_NUMBER() OVER (
                PARTITION BY
                  CASE
                    WHEN NULLIF(TRIM(fee.source_doc_no), '') IS NOT NULL
                     AND NULLIF(TRIM(fee.source_row_key), '') IS NOT NULL
                      THEN ''
                    ELSE fee.id
                  END,
                  fee.store_id,
                  fee.revenue_date,
                  UPPER(TRIM(COALESCE(fee.source_type, ''))),
                  UPPER(TRIM(COALESCE(fee.source_group_code, ''))),
                  UPPER(TRIM(COALESCE(fee.contract_code, ''))),
                  UPPER(TRIM(COALESCE(fee.fee_type_code, ''))),
                  TRIM(COALESCE(fee.source_doc_no, '')),
                  TRIM(COALESCE(fee.source_row_key, '')),
                  COALESCE(fee.tax_included_amount, 0),
                  COALESCE(fee.tax_excluded_amount, 0)
                ORDER BY fee.id
              ) AS exact_duplicate_rank
            FROM {fee_source_relation}
            LEFT JOIN fee_tax_rates
              ON fee_tax_rates.fee_type_code = TRIM(fee.fee_type_code)
            WHERE {fee_source_filter}
              AND TRIM(COALESCE(fee.fee_type_code, '')) NOT IN ('37', '61', '69')
              AND TRIM(COALESCE(fee.fee_type_name, '')) NOT LIKE '%保证金%'
              AND NOT EXISTS (
                SELECT 1
                FROM ticket_reduction_fee_keys ticket
                WHERE ticket.payment_bill_no_norm = UPPER(TRIM(fee.source_doc_no))
                  AND ticket.source_group_code_norm = UPPER(TRIM(fee.source_group_code))
                  AND ticket.fee_type_code_norm = UPPER(TRIM(fee.fee_type_code))
                  AND (
                    ticket.contract_code_norm IS NULL
                    OR ticket.contract_code_norm = UPPER(TRIM(fee.contract_code))
                  )
              )
        ),
        live_fees AS (
            SELECT
              resolved.id,
              resolved.store_id,
              resolved.floor_id,
              resolved.unit_id,
              resolved.unit_code,
              resolved.revenue_date,
              resolved.revenue_month,
              resolved.occurrence_date,
              resolved.payment_date,
              resolved.payment_no,
              resolved.settlement_no,
              resolved.source_group_code,
              resolved.source_group_name,
              resolved.contract_code,
              resolved.contract_name,
              resolved.fee_type_code,
              resolved.fee_type_name,
              resolved.tax_included_amount,
              resolved.source_tax_excluded_amount,
              resolved.tax_excluded_amount,
              resolved.source_type,
              resolved.source_doc_no,
              resolved.etl_batch_id
            FROM (
                SELECT
                  fee.id,
                  st.store_id,
                  candidate.floor_id,
                  candidate.unit_id,
                  candidate.unit_code,
                  {effective_date_expression} AS revenue_date,
                  {revenue_month_expression} AS revenue_month,
                  fee.occurrence_date,
                  fee.payment_date,
                  fee.payment_no,
                  fee.settlement_no,
                  fee.source_group_code,
                  fee.source_group_name,
                  fee.contract_code,
                  fee.contract_name,
                  fee.fee_type_code,
                  fee.fee_type_name,
                  fee.tax_included_amount,
                  fee.tax_excluded_amount AS source_tax_excluded_amount,
                  CASE
                    WHEN {loss_bearing_fee_condition}
                      THEN fee.tax_excluded_amount / {LOSS_BEARING_TAX_DIVISOR}
                    WHEN fee.reference_tax_rate IS NOT NULL
                      THEN ROUND(
                        fee.tax_included_amount / (1 + fee.reference_tax_rate),
                        2
                      )
                    ELSE fee.tax_excluded_amount
                  END AS tax_excluded_amount,
                  fee.source_type,
                  fee.source_doc_no,
                  fee.etl_batch_id,
                  ROW_NUMBER() OVER (
                    PARTITION BY fee.id
                    ORDER BY
                      COALESCE(candidate.is_primary, false) DESC,
                      candidate.contract_start_date DESC,
                      candidate.binding_id ASC
                  ) AS resolution_rank
                FROM fee_source_rows fee
                JOIN contract_group_bindings candidate
                  ON candidate.contract_code_norm = UPPER(TRIM(fee.contract_code))
                 AND candidate.source_group_code_norm = UPPER(TRIM(fee.source_group_code))
                 AND (
                   candidate.binding_start_date IS NULL
                   OR candidate.binding_start_date <= {binding_date_expression}
                 )
                 AND (
                   candidate.binding_end_date IS NULL
                   OR candidate.binding_end_date >= {binding_date_expression}
                 )
                 AND candidate.contract_start_date <= {binding_date_expression}
                 AND candidate.contract_end_date >= {binding_date_expression}
                JOIN stores st
                  ON TRIM(st.store_code) = candidate.store_code
                WHERE fee.exact_duplicate_rank = 1
            ) resolved
            WHERE resolved.resolution_rank = 1
        )
    """


def _live_revenue_source_ctes(
    sales_date_filter: str,
    fee_date_filter: str,
    extra_date_filter: str,
    sales_store_filter: str = "",
    *,
    fee_date_basis: str = "occurrence",
) -> str:
    live_sales_ctes = _live_sales_ctes(sales_date_filter, sales_store_filter)
    live_fees_cte = _live_fees_cte(fee_date_filter, date_basis=fee_date_basis)
    loss_bearing_fee_condition = _loss_bearing_fee_condition("fee")
    return f"""
        {live_sales_ctes},
        {live_fees_cte},
        source_rows AS (
            SELECT
              store_id,
              floor_id,
              unit_id,
              unit_code,
              revenue_date,
              CASE
                WHEN EXTRACT(MONTH FROM revenue_date) = 12 THEN TO_CHAR(revenue_date, 'YYYY-12')
                WHEN EXTRACT(DAY FROM revenue_date) >= 29 THEN
                  TO_CHAR(revenue_date, 'YYYY-')
                  || LPAD((EXTRACT(MONTH FROM revenue_date)::integer + 1)::text, 2, '0')
                ELSE TO_CHAR(revenue_date, 'YYYY-MM')
              END AS financial_period_month,
              source_group_code,
              source_group_name,
              NULL::varchar AS source_department_code,
              NULL::varchar AS source_department_name,
              gross_profit_amount AS sales_amount,
              0::numeric AS fee_amount,
              0::numeric AS extra_amount,
              gross_profit_amount AS close_basis_sales_amount,
              0::numeric AS close_basis_fee_amount,
              0::numeric AS close_basis_extra_amount,
              1::integer AS sales_count,
              0::integer AS fee_count,
              0::integer AS extra_count
            FROM live_sales
            UNION ALL
            SELECT
              fee.store_id,
              fee.floor_id,
              fee.unit_id,
              fee.unit_code,
              fee.revenue_date,
              CASE
                WHEN EXTRACT(MONTH FROM fee.revenue_date) = 12 THEN TO_CHAR(fee.revenue_date, 'YYYY-12')
                WHEN EXTRACT(DAY FROM fee.revenue_date) >= 29 THEN
                  TO_CHAR(fee.revenue_date, 'YYYY-')
                  || LPAD((EXTRACT(MONTH FROM fee.revenue_date)::integer + 1)::text, 2, '0')
                ELSE TO_CHAR(fee.revenue_date, 'YYYY-MM')
              END,
              fee.source_group_code,
              fee.source_group_name,
              NULL::varchar,
              NULL::varchar,
              CASE
                WHEN {loss_bearing_fee_condition} THEN fee.tax_excluded_amount
                ELSE 0::numeric
              END,
              CASE
                WHEN {loss_bearing_fee_condition} THEN 0::numeric
                ELSE fee.tax_excluded_amount
              END,
              0::numeric,
              CASE
                WHEN {loss_bearing_fee_condition} THEN fee.tax_excluded_amount
                ELSE 0::numeric
              END,
              CASE
                WHEN {loss_bearing_fee_condition} THEN 0::numeric
                ELSE fee.tax_included_amount
              END,
              0::numeric,
              CASE WHEN {loss_bearing_fee_condition} THEN 1::integer ELSE 0::integer END,
              CASE WHEN {loss_bearing_fee_condition} THEN 0::integer ELSE 1::integer END,
              0::integer
            FROM live_fees fee
            UNION ALL
            SELECT
              st.store_id,
              bu.floor_id,
              bu.id,
              bu.unit_code,
              extra.revenue_date,
              extra.revenue_month,
              extra.source_group_code,
              extra.source_group_name,
              extra.source_department_code,
              extra.source_department_name,
              0::numeric,
              0::numeric,
              extra.amount,
              0::numeric,
              0::numeric,
              extra.amount,
              0::integer,
              0::integer,
              1::integer
            FROM revenue_extra_receipts extra
            JOIN business_units bu ON bu.id = extra.unit_id
            JOIN floors unit_floor ON unit_floor.id = bu.floor_id
            JOIN stores st ON TRIM(st.store_code) = TRIM(unit_floor.store_code)
            WHERE {extra_date_filter}
              AND extra.status = 'CONFIRMED'
              AND extra.source_type = 'NC6051'
        )
    """


def _revenue_month_close_overlay_ctes(
    close_filter: str = (
        "close.period_start_date = :start_date "
        "AND close.period_end_date = :end_date"
    ),
) -> str:
    """Overlay confirmed month-close adjustments without mutating source rows."""
    return """
        confirmed_month_closes AS MATERIALIZED (
          SELECT close.*
          FROM revenue_month_closes close
          WHERE close.status = 'CONFIRMED'
            AND {close_filter}
        ),
        dashboard_live_rows AS (
          SELECT
            src.store_id,
            src.floor_id,
            src.unit_id,
            src.unit_code,
            src.revenue_date,
            src.financial_period_month,
            src.source_group_code,
            src.source_group_name,
            src.source_department_code,
            src.source_department_name,
            CASE
              WHEN close.id IS NOT NULL THEN src.close_basis_sales_amount
              ELSE src.sales_amount
            END AS sales_amount,
            CASE
              WHEN close.id IS NOT NULL THEN src.close_basis_fee_amount
              ELSE src.fee_amount
            END AS fee_amount,
            CASE
              WHEN close.id IS NOT NULL THEN src.close_basis_extra_amount
              ELSE src.extra_amount
            END AS extra_amount,
            0::numeric AS sales_adjustment_amount,
            0::numeric AS fee_adjustment_amount,
            0::numeric AS extra_adjustment_amount,
            0::numeric AS tax_adjustment_amount,
            src.sales_count,
            src.fee_count,
            src.extra_count
          FROM source_rows src
          LEFT JOIN confirmed_month_closes close
            ON close.store_id = src.store_id
           AND close.period_month = src.financial_period_month
        ),
        dashboard_adjustment_rows AS (
          SELECT
            close.store_id,
            unit.floor_id,
            adjustment.unit_id,
            COALESCE(adjustment.unit_code, unit.unit_code) AS unit_code,
            close.period_end_date AS revenue_date,
            close.period_month AS financial_period_month,
            adjustment.source_group_code,
            adjustment.source_group_name,
            adjustment.source_department_code,
            adjustment.source_department_name,
            0::numeric AS sales_amount,
            CASE
              WHEN adjustment.target_component = 'FEE'
                THEN adjustment.adjustment_amount
              ELSE 0::numeric
            END AS fee_amount,
            CASE
              WHEN adjustment.target_component = 'EXTRA'
                THEN adjustment.adjustment_amount
              ELSE 0::numeric
            END AS extra_amount,
            0::numeric AS sales_adjustment_amount,
            CASE
              WHEN adjustment.target_component = 'FEE'
               AND NOT (
                 COALESCE(adjustment.raw_payload, '{{}}'::jsonb)
                 ? 'manual_binding_source_line_key'
               )
                THEN adjustment.adjustment_amount
              ELSE 0::numeric
            END AS fee_adjustment_amount,
            CASE
              WHEN adjustment.target_component = 'EXTRA'
               AND NOT (
                 COALESCE(adjustment.raw_payload, '{{}}'::jsonb)
                 ? 'manual_binding_source_line_key'
               )
                THEN adjustment.adjustment_amount
              ELSE 0::numeric
            END AS extra_adjustment_amount,
            adjustment.accrued_tax_amount::numeric AS tax_adjustment_amount,
            0::integer AS sales_count,
            0::integer AS fee_count,
            0::integer AS extra_count
          FROM confirmed_month_closes close
          JOIN revenue_month_close_adjustments adjustment
            ON adjustment.month_close_id = close.id
          LEFT JOIN business_units unit
            ON unit.id = adjustment.unit_id
          WHERE adjustment.adjustment_amount <> 0
            AND adjustment.binding_status = 'BOUND'
            AND COALESCE(TRIM(adjustment.fee_type_code), '') <> '37'
            AND COALESCE(TRIM(adjustment.fee_type_name), '') <> '代付费用'
        ),
        dashboard_pending_adjustment_rows AS (
          SELECT
            close.store_id,
            NULL::bigint AS floor_id,
            NULL::bigint AS unit_id,
            NULL::text AS unit_code,
            close.period_end_date AS revenue_date,
            close.period_month AS financial_period_month,
            NULL::text AS source_group_code,
            ('待人工绑定：' || COALESCE(adjustment.source_subject_name, adjustment.fee_type_name, '月结差异'))::text AS source_group_name,
            adjustment.source_department_code,
            adjustment.source_department_name,
            0::numeric AS sales_amount,
            CASE
              WHEN adjustment.target_component = 'FEE'
                THEN adjustment.adjustment_amount
              ELSE 0::numeric
            END AS fee_amount,
            CASE
              WHEN adjustment.target_component = 'EXTRA'
                THEN adjustment.adjustment_amount
              ELSE 0::numeric
            END AS extra_amount,
            0::numeric AS sales_adjustment_amount,
            CASE
              WHEN adjustment.target_component = 'FEE'
                THEN adjustment.adjustment_amount
              ELSE 0::numeric
            END AS fee_adjustment_amount,
            CASE
              WHEN adjustment.target_component = 'EXTRA'
                THEN adjustment.adjustment_amount
              ELSE 0::numeric
            END AS extra_adjustment_amount,
            adjustment.accrued_tax_amount::numeric AS tax_adjustment_amount,
            0::integer AS sales_count,
            0::integer AS fee_count,
            0::integer AS extra_count
          FROM confirmed_month_closes close
          JOIN revenue_month_close_adjustments adjustment
            ON adjustment.month_close_id = close.id
          WHERE adjustment.adjustment_amount <> 0
            AND adjustment.binding_status = 'PENDING'
            AND ROUND(
                  COALESCE(adjustment.adjustment_amount, 0)
                  - COALESCE(adjustment.accrued_tax_amount, 0),
                  2
                ) <> 0
            AND COALESCE(TRIM(adjustment.fee_type_code), '') <> '37'
            AND COALESCE(TRIM(adjustment.fee_type_name), '') <> '代付费用'
        ),
        dashboard_source_rows AS (
          SELECT * FROM dashboard_live_rows
          UNION ALL
          SELECT * FROM dashboard_adjustment_rows
          UNION ALL
          SELECT * FROM dashboard_pending_adjustment_rows
        )
    """.format(close_filter=close_filter)


def _nc_6051_extra_detail_ctes(
    extra_filter_sql: str = "",
    *,
    date_filter_sql: str = "extra.revenue_date BETWEEN :start_date AND :end_date",
) -> str:
    """Build traceable NC6051 rows with the exact account name from PK_ACCSUBJ."""
    return f"""
        subject_names AS (
          SELECT
            TRIM(subjcode) AS subject_code,
            MIN(NULLIF(TRIM(subjname), '')) AS subject_name
          FROM ods.nc_bd_accsubj
          WHERE COALESCE(dr, 0) = 0
            AND TRIM(subjcode) LIKE '6051%'
          GROUP BY TRIM(subjcode)
        ),
        filtered_extras AS (
          SELECT
            extra.*,
            COALESCE(
              exact_subject.subject_name,
              subject_names.subject_name,
              NULLIF(TRIM(extra.extra_type), ''),
              '未命名科目'
            ) AS source_subject_name
          FROM revenue_extra_receipts extra
          LEFT JOIN LATERAL (
            SELECT finance.pk_accsubj
            FROM bh_dw_gl_detail_fact2 finance
            WHERE finance.pk_detail = extra.source_detail_key
            ORDER BY finance.load_date DESC NULLS LAST
            LIMIT 1
          ) finance_subject ON true
          LEFT JOIN LATERAL (
            SELECT MIN(NULLIF(TRIM(acc.subjname), '')) AS subject_name
            FROM ods.nc_bd_accsubj acc
            WHERE acc.pk_accsubj = finance_subject.pk_accsubj
              AND COALESCE(acc.dr, 0) = 0
          ) exact_subject ON true
          LEFT JOIN subject_names
            ON subject_names.subject_code = TRIM(extra.source_subject_code)
          WHERE {date_filter_sql}
            AND extra.status = 'CONFIRMED'
            AND extra.source_type = 'NC6051'
            {extra_filter_sql}
        )
    """


def _money(value: object) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _dashboard_non_tax_adjustment(row: dict) -> float:
    """Return month-close variance after removing tax embedded in close rows."""
    adjustment = sum(
        (
            Decimal(str(row.get(key) or 0))
            for key in (
                "sales_adjustment_amount",
                "fee_adjustment_amount",
                "extra_adjustment_amount",
            )
        ),
        Decimal("0"),
    )
    accrued_tax = Decimal(str(row.get("tax_adjustment_amount") or 0))
    return _money((adjustment - accrued_tax).quantize(Decimal("0.01")))


def _dt(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _dashboard_row_allowed(scope, row: dict) -> bool:
    """Apply the shared store / department / group business scope at cabinet grain."""
    return scope_allows_business(
        scope,
        store_id=row.get("store_id"),
        department_code=row.get("department_code"),
        department_name=row.get("department_name"),
        group_code=row.get("group_code"),
    )


def _canonical_revenue_department_values(
    store_code: object,
    department_code: object,
    department_name: object,
) -> tuple[str | None, str | None]:
    normalized_store = str(store_code or "").strip()
    normalized_code = str(department_code or "").strip()
    normalized_name = str(department_name or "").strip()
    canonical = REVENUE_DEPARTMENT_ALIAS_LOOKUP.get(
        (normalized_store, normalized_code)
    )
    if canonical:
        return canonical
    return normalized_code or None, normalized_name or None


def _load_nc_6051_dashboard_summary(
    db: Session,
    scope,
    *,
    financial_year: int | None,
    financial_month: int | None,
) -> dict:
    """Return permission-scoped NC 6051 net-credit and accrued-tax totals."""
    summary = {
        "available": financial_year is not None,
        "subject_prefix": "6051",
        "amount_basis": "local_credit_minus_local_debit",
        "tax_basis": "explanation_matches_accrual_tax",
        "tax_period_basis": "confirmed_month_close_only",
        "store_amounts": [],
        "department_amounts": [],
    }
    if financial_year is None:
        return summary

    period_start = financial_month or 1
    period_end = financial_month or 12
    rows = db.execute(
        text(
            f"""
            SELECT
              st.store_id,
              st.store_code,
              TRIM(f.valuecode) AS department_code,
              COALESCE(
                NULLIF(TRIM(f.valuename), ''),
                NULLIF(TRIM(f.valuecode), '')
              ) AS department_name,
              SUM(
                COALESCE(f.localcreditamount, 0)
                - COALESCE(f.localdebitamount, 0)
              )::numeric AS nc_6051_amount,
              SUM(
                CASE
                  WHEN COALESCE(f.explanation, '') ~ '计提.*(销项)?税|电费收入结转销项税'
                   AND EXISTS (
                     SELECT 1
                     FROM revenue_month_closes tax_close
                     WHERE tax_close.store_id = st.store_id
                       AND tax_close.status = 'CONFIRMED'
                       AND tax_close.period_month = (
                         f.account_year::int::text
                         || '-'
                         || LPAD(f.account_period::int::text, 2, '0')
                       )
                   )
                    THEN COALESCE(f.localcreditamount, 0)
                         - COALESCE(f.localdebitamount, 0)
                  ELSE 0
                END
              )::numeric AS nc_6051_tax_amount
            FROM bh_dw_gl_detail_fact2 f
            JOIN stores st
              ON st.store_code = ({FINANCE_STORE_CODE_SQL})
             AND st.is_active = TRUE
            WHERE f.account_year::int = :financial_year
              AND f.account_period::int BETWEEN :period_start AND :period_end
              AND TRIM(f.subject_code) LIKE '6051%'
              AND TRIM(COALESCE(f.valuecode, '')) NOT IN (
                '210109', '220109', '310109', '330109'
              )
            GROUP BY
              st.store_id,
              st.store_code,
              TRIM(f.valuecode),
              COALESCE(
                NULLIF(TRIM(f.valuename), ''),
                NULLIF(TRIM(f.valuecode), '')
              )
            """
        ),
        {
            "financial_year": financial_year,
            "period_start": period_start,
            "period_end": period_end,
        },
    ).mappings().all()

    store_totals: dict[tuple[int, str], Decimal] = {}
    store_tax_totals: dict[tuple[int, str], Decimal] = {}
    department_totals: dict[tuple[int, str, str, str], Decimal] = {}
    department_tax_totals: dict[tuple[int, str, str, str], Decimal] = {}
    for source in rows:
        department_code, department_name = _canonical_revenue_department_values(
            source.get("store_code"),
            source.get("department_code"),
            source.get("department_name"),
        )
        scoped_row = {
            "store_id": source.get("store_id"),
            "department_code": department_code,
            "department_name": department_name,
            "group_code": None,
        }
        if not _dashboard_row_allowed(scope, scoped_row):
            continue
        amount = Decimal(str(source.get("nc_6051_amount") or 0))
        tax_amount = Decimal(str(source.get("nc_6051_tax_amount") or 0))
        store_key = (int(source["store_id"]), str(source["store_code"]).strip())
        store_totals[store_key] = store_totals.get(store_key, Decimal("0")) + amount
        store_tax_totals[store_key] = (
            store_tax_totals.get(store_key, Decimal("0")) + tax_amount
        )
        department_key = (
            store_key[0],
            store_key[1],
            department_code or "",
            department_name or "未归属部门",
        )
        department_totals[department_key] = (
            department_totals.get(department_key, Decimal("0")) + amount
        )
        department_tax_totals[department_key] = (
            department_tax_totals.get(department_key, Decimal("0")) + tax_amount
        )

    summary["store_amounts"] = [
        {
            "store_id": store_id,
            "store_code": store_code,
            "amount": _money(amount),
            "tax_amount": _money(store_tax_totals.get((store_id, store_code))),
        }
        for (store_id, store_code), amount in sorted(store_totals.items())
    ]
    summary["department_amounts"] = [
        {
            "store_id": store_id,
            "store_code": store_code,
            "department_code": department_code or None,
            "department_name": department_name,
            "amount": _money(amount),
            "tax_amount": _money(
                department_tax_totals.get(
                    (store_id, store_code, department_code, department_name)
                )
            ),
        }
        for (
            store_id,
            store_code,
            department_code,
            department_name,
        ), amount in sorted(department_totals.items())
    ]
    return summary


def _month_from_date(value: date) -> str:
    return value.strftime("%Y-%m")


def _dashboard_financial_period(
    *,
    start_date: date,
    end_date: date,
    financial_year: Optional[int],
    financial_month: Optional[int],
) -> dict:
    """Validate an optional financial-year/month selection and build SQL filters."""
    if financial_month is not None and financial_year is None:
        raise HTTPException(status_code=400, detail="选择财务月时必须同时选择年份")
    if financial_month is not None and not 1 <= financial_month <= 12:
        raise HTTPException(status_code=400, detail="financial_month 必须为 1 至 12")

    if financial_year is None:
        return {
            "fee_filter": "payment_ref.payment_date BETWEEN :start_date AND :end_date",
            "extra_filter": "extra.revenue_date BETWEEN :start_date AND :end_date",
            "close_filter": (
                "close.period_start_date = :start_date "
                "AND close.period_end_date = :end_date"
            ),
            "date_basis": "revenue_date",
            "period_count": 1,
        }

    expected_start, expected_end = (
        financial_month_period(financial_year, financial_month)
        if financial_month is not None
        else financial_year_period(financial_year)
    )
    if start_date != expected_start or end_date != expected_end:
        label = f"{financial_year}年第{financial_month}财务月" if financial_month else f"{financial_year}全年"
        raise HTTPException(
            status_code=400,
            detail=f"{label}应为 {expected_start.isoformat()} 至 {expected_end.isoformat()}",
        )

    period_start = f"{financial_year:04d}-{financial_month or 1:02d}"
    period_end = f"{financial_year:04d}-{financial_month or 12:02d}"
    return {
        "fee_filter": """
            (
              payment_ref.source_kind = 'JOINT'
              AND payment_ref.payment_date BETWEEN :start_date AND :end_date
            )
            OR (
              payment_ref.source_kind = 'RENTAL'
              AND payment_ref.payment_date >= TO_DATE(
                :period_month_start || '-01',
                'YYYY-MM-DD'
              )
              AND payment_ref.payment_date < TO_DATE(
                :period_month_end || '-01',
                'YYYY-MM-DD'
              ) + INTERVAL '1 month'
            )
        """,
        "extra_filter": "extra.revenue_month BETWEEN :period_month_start AND :period_month_end",
        "close_filter": "close.period_month BETWEEN :period_month_start AND :period_month_end",
        "date_basis": "financial_period",
        "period_month_start": period_start,
        "period_month_end": period_end,
        "period_count": 1 if financial_month is not None else 12,
    }


def _model_data(model: BaseModel) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


class RevenueExtraReceiptCreate(BaseModel):
    unit_id: Optional[int] = None
    unit_code: Optional[str] = None
    store_id: Optional[int] = None
    floor_id: Optional[int] = None
    revenue_date: date
    extra_type: str = Field(default="其他收益", max_length=100)
    amount: Decimal
    receipt_date: Optional[date] = None
    voucher_no: Optional[str] = None
    contract_code: Optional[str] = None
    supplier_code: Optional[str] = None
    supplier_name: Optional[str] = None
    source_group_code: Optional[str] = None
    source_group_name: Optional[str] = None
    remark: Optional[str] = None
    attachment_url: Optional[str] = None


class RevenueExtraReceiptUpdate(BaseModel):
    unit_id: Optional[int] = None
    unit_code: Optional[str] = None
    store_id: Optional[int] = None
    floor_id: Optional[int] = None
    revenue_date: Optional[date] = None
    extra_type: Optional[str] = Field(default=None, max_length=100)
    amount: Optional[Decimal] = None
    receipt_date: Optional[date] = None
    voucher_no: Optional[str] = None
    contract_code: Optional[str] = None
    supplier_code: Optional[str] = None
    supplier_name: Optional[str] = None
    source_group_code: Optional[str] = None
    source_group_name: Optional[str] = None
    remark: Optional[str] = None
    attachment_url: Optional[str] = None


class RevenueRecalculateRequest(BaseModel):
    start_date: date
    end_date: date
    unit_id: Optional[int] = None


class RevenueMonthCloseBindingRequest(BaseModel):
    unit_id: int = Field(gt=0)
    source_group_code: str = Field(min_length=1, max_length=50)
    source_line_key: str = Field(min_length=1, max_length=500)
    target_component: str = Field(pattern=r"^(FEE|EXTRA)$")
    adjustment_amount: Optional[Decimal] = None
    note: Optional[str] = Field(default=None, max_length=500)


def _normalize_unit_fields(db: Session, payload: dict) -> dict:
    unit_id = payload.get("unit_id")
    if unit_id:
        row = db.execute(
            text(
                """
                SELECT id, floor_id, unit_code
                FROM business_units
                WHERE id = :unit_id
                """
            ),
            {"unit_id": unit_id},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="经营单元不存在")
        payload["unit_id"] = int(row.id)
        payload["unit_code"] = payload.get("unit_code") or row.unit_code
        payload["floor_id"] = payload.get("floor_id") or int(row.floor_id)
    if not payload.get("unit_id") and not (payload.get("unit_code") or "").strip():
        raise HTTPException(status_code=400, detail="unit_id 或 unit_code 至少填写一个")
    return payload


def _receipt_to_dict(row) -> dict:
    return {
        "id": int(row.id),
        "store_id": row.store_id,
        "floor_id": row.floor_id,
        "unit_id": row.unit_id,
        "unit_code": row.unit_code,
        "revenue_date": _dt(row.revenue_date),
        "revenue_month": row.revenue_month,
        "extra_type": row.extra_type,
        "amount": _money(row.amount),
        "receipt_date": _dt(row.receipt_date),
        "voucher_no": row.voucher_no,
        "contract_code": row.contract_code,
        "supplier_code": row.supplier_code,
        "supplier_name": row.supplier_name,
        "source_group_code": row.source_group_code,
        "source_group_name": row.source_group_name,
        "remark": row.remark,
        "attachment_url": row.attachment_url,
        "status": row.status,
        "source_type": getattr(row, "source_type", None),
        "source_detail_key": getattr(row, "source_detail_key", None),
        "source_subject_code": getattr(row, "source_subject_code", None),
        "source_department_code": getattr(row, "source_department_code", None),
        "source_department_name": getattr(row, "source_department_name", None),
        "source_explanation": getattr(row, "source_explanation", None),
        "match_method": getattr(row, "match_method", None),
        "match_status": getattr(row, "match_status", None),
        "match_reason": getattr(row, "match_reason", None),
        "etl_batch_id": getattr(row, "etl_batch_id", None),
        "source_updated_at": _dt(getattr(row, "source_updated_at", None)),
        "created_by": row.created_by,
        "confirmed_by": row.confirmed_by,
        "voided_by": row.voided_by,
        "confirmed_at": _dt(row.confirmed_at),
        "voided_at": _dt(row.voided_at),
        "created_at": _dt(row.created_at),
        "updated_at": _dt(row.updated_at),
    }


@router.get("/dashboard")
async def revenue_dashboard(
    start_date: date,
    end_date: date,
    financial_year: Optional[int] = Query(None, ge=2000, le=2100),
    financial_month: Optional[int] = Query(None, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return permission-scoped revenue at store → department → cabinet grain.

    Sales and joint fees keep the finance-period basis. Rental fees use the
    linked payment date within the natural accounting month.
    """
    require_permission(db, current_user, "revenue.dashboard.view")
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date 不能早于 start_date")

    try:
        period = _dashboard_financial_period(
            start_date=start_date,
            end_date=end_date,
            financial_year=financial_year,
            financial_month=financial_month,
        )
        params = {
            "start_date": start_date,
            "end_date": end_date,
        }
        if period.get("period_month_start"):
            params["period_month_start"] = period["period_month_start"]
            params["period_month_end"] = period["period_month_end"]
        source_ctes = _live_revenue_source_ctes(
            "s.sglhsrq BETWEEN :start_date AND :end_date",
            period["fee_filter"],
            period["extra_filter"],
            fee_date_basis="payment",
        )
        month_close_ctes = _revenue_month_close_overlay_ctes(period["close_filter"])
        department_aliases_cte = _revenue_department_aliases_cte()
        loss_bearing_fee_condition = _loss_bearing_fee_condition("fee")
        # A multi-month view reuses the same auditable source query as a month,
        # but its payment and month-close joins legitimately exceed the global
        # 30-second default. Keep the exception transaction-local and retain
        # the stricter default for ordinary single-month requests.
        if period["period_count"] > 1:
            db.execute(
                text(
                    "SET LOCAL statement_timeout = "
                    f"'{REVENUE_DASHBOARD_QUERY_TIMEOUT_SECONDS}s'"
                ),
                {},
            )
        rows = db.execute(
            text(
                f"""
                WITH {source_ctes},
                {month_close_ctes},
                {department_aliases_cte},
                fee_breakdown_rows AS (
                  SELECT
                    fee.store_id,
                    UPPER(TRIM(fee.source_group_code)) AS group_code_norm,
                    NULLIF(TRIM(fee.fee_type_code), '') AS fee_type_code,
                    COALESCE(
                      NULLIF(TRIM(fee.fee_type_name), ''),
                      '未分类收费'
                    ) AS fee_type_name,
                    COALESCE(SUM(
                      CASE
                        WHEN close.id IS NOT NULL THEN fee.tax_included_amount
                        ELSE fee.tax_excluded_amount
                      END
                    ), 0)::numeric AS tax_excluded_amount
                  FROM live_fees fee
                  LEFT JOIN confirmed_month_closes close
                    ON close.store_id = fee.store_id
                   AND close.period_month = CASE
                     WHEN EXTRACT(MONTH FROM fee.revenue_date) = 12 THEN TO_CHAR(fee.revenue_date, 'YYYY-12')
                     WHEN EXTRACT(DAY FROM fee.revenue_date) >= 29 THEN
                       TO_CHAR(fee.revenue_date, 'YYYY-')
                       || LPAD((EXTRACT(MONTH FROM fee.revenue_date)::integer + 1)::text, 2, '0')
                     ELSE TO_CHAR(fee.revenue_date, 'YYYY-MM')
                   END
                  WHERE NOT ({loss_bearing_fee_condition})
                  GROUP BY
                    fee.store_id,
                    close.id,
                    UPPER(TRIM(fee.source_group_code)),
                    NULLIF(TRIM(fee.fee_type_code), ''),
                    COALESCE(
                      NULLIF(TRIM(fee.fee_type_name), ''),
                      '未分类收费'
                    )

                  UNION ALL

                  SELECT
                    close.store_id,
                    UPPER(TRIM(adjustment.source_group_code)) AS group_code_norm,
                    COALESCE(NULLIF(TRIM(adjustment.fee_type_code), ''), 'MONTH_CLOSE'),
                    COALESCE(
                      NULLIF(TRIM(adjustment.fee_type_name), ''),
                      '月结含税调整'
                    ),
                    COALESCE(SUM(adjustment.adjustment_amount), 0)::numeric
                  FROM confirmed_month_closes close
                  JOIN revenue_month_close_adjustments adjustment
                    ON adjustment.month_close_id = close.id
                   AND adjustment.target_component = 'FEE'
                   AND adjustment.binding_status = 'BOUND'
                  GROUP BY
                    close.store_id,
                    UPPER(TRIM(adjustment.source_group_code)),
                    COALESCE(NULLIF(TRIM(adjustment.fee_type_code), ''), 'MONTH_CLOSE'),
                    COALESCE(
                      NULLIF(TRIM(adjustment.fee_type_name), ''),
                      '月结含税调整'
                    )
                ),
                fee_breakdowns AS (
                  SELECT
                    store_id,
                    group_code_norm,
                    JSONB_AGG(
                      JSONB_BUILD_OBJECT(
                        'fee_type_code', fee_type_code,
                        'fee_type_name', fee_type_name,
                        'tax_excluded_amount', tax_excluded_amount
                      )
                      ORDER BY fee_type_code NULLS LAST, fee_type_name
                    ) AS fee_breakdown
                  FROM fee_breakdown_rows
                  GROUP BY store_id, group_code_norm
                )
                SELECT
                  src.store_id,
                  st.store_code,
                  st.store_name,
                  COALESCE(
                    NULLIF(TRIM(dept.mfcode), ''),
                    department_alias.canonical_department_code,
                    NULLIF(TRIM(src.source_department_code), '')
                  ) AS department_code,
                  COALESCE(
                    NULLIF(TRIM(dept.mfcname), ''),
                    department_alias.canonical_department_name,
                    NULLIF(TRIM(src.source_department_name), '')
                  ) AS department_name,
                  NULLIF(TRIM(src.source_group_code), '') AS group_code,
                  COALESCE(
                    NULLIF(TRIM(src.source_group_name), ''),
                    NULLIF(TRIM(group_mf.mfcname), '')
                  ) AS group_name,
                  STRING_AGG(
                    DISTINCT NULLIF(TRIM(src.unit_code), ''),
                    '、'
                    ORDER BY NULLIF(TRIM(src.unit_code), '')
                  ) AS unit_codes,
                  COUNT(DISTINCT src.unit_id)::integer AS unit_count,
                  COALESCE(
                    SUM(src.sales_amount - src.sales_adjustment_amount),
                    0
                  )::numeric AS raw_sales_gross_profit_amount,
                  COALESCE(
                    SUM(src.fee_amount - src.fee_adjustment_amount),
                    0
                  )::numeric AS raw_fee_amount,
                  COALESCE(
                    SUM(src.extra_amount - src.extra_adjustment_amount),
                    0
                  )::numeric AS raw_extra_amount,
                  COALESCE(SUM(src.sales_adjustment_amount), 0)::numeric
                    AS sales_adjustment_amount,
                  COALESCE(SUM(src.fee_adjustment_amount), 0)::numeric
                    AS fee_adjustment_amount,
                  COALESCE(SUM(src.extra_adjustment_amount), 0)::numeric
                    AS extra_adjustment_amount,
                  COALESCE(SUM(src.tax_adjustment_amount), 0)::numeric
                    AS tax_adjustment_amount,
                  COALESCE(SUM(src.sales_amount), 0)::numeric AS sales_gross_profit_amount,
                  COALESCE(SUM(src.fee_amount), 0)::numeric AS fee_amount,
                  COALESCE(SUM(src.extra_amount), 0)::numeric AS extra_amount,
                  COALESCE(
                    SUM(src.sales_amount + src.fee_amount + src.extra_amount),
                    0
                  )::numeric AS total_amount,
                  COALESCE(fee_breakdowns.fee_breakdown, '[]'::jsonb) AS fee_breakdown
                FROM dashboard_source_rows src
                JOIN stores st ON st.store_id = src.store_id
                LEFT JOIN revenue_department_aliases department_alias
                  ON TRIM(department_alias.store_code) = TRIM(st.store_code)
                 AND department_alias.source_department_code = NULLIF(
                   TRIM(src.source_department_code),
                   ''
                 )
                LEFT JOIN manaframe group_mf
                  ON UPPER(TRIM(group_mf.mfcode)) = UPPER(TRIM(src.source_group_code))
                LEFT JOIN manaframe dept
                  ON dept.mfcode = group_mf.mfpcode
                LEFT JOIN fee_breakdowns
                  ON fee_breakdowns.store_id = src.store_id
                 AND fee_breakdowns.group_code_norm = UPPER(TRIM(src.source_group_code))
                GROUP BY
                  src.store_id,
                  st.store_code,
                  st.store_name,
                  COALESCE(
                    NULLIF(TRIM(dept.mfcode), ''),
                    department_alias.canonical_department_code,
                    NULLIF(TRIM(src.source_department_code), '')
                  ),
                  COALESCE(
                    NULLIF(TRIM(dept.mfcname), ''),
                    department_alias.canonical_department_name,
                    NULLIF(TRIM(src.source_department_name), '')
                  ),
                  NULLIF(TRIM(src.source_group_code), ''),
                  COALESCE(
                    NULLIF(TRIM(src.source_group_name), ''),
                    NULLIF(TRIM(group_mf.mfcname), '')
                  ),
                  fee_breakdowns.fee_breakdown
                ORDER BY total_amount DESC, group_code ASC NULLS LAST
                """
            ),
            params,
        ).mappings().all()

        close_rows = db.execute(
            text(
                f"""
                SELECT
                  close.id,
                  close.store_id,
                  st.store_code,
                  st.store_name,
                  close.period_month,
                  close.period_start_date,
                  close.period_end_date,
                  close.version,
                  close.nc_amount_before_tax,
                  close.accrued_tax_amount,
                  close.nc_control_amount,
                  close.raw_fee_amount,
                  close.raw_extra_amount,
                  close.close_adjustment_amount,
                  close.final_fee_extra_amount,
                  close.source_snapshot_id,
                  close.confirmed_at
                FROM revenue_month_closes close
                JOIN stores st ON st.store_id = close.store_id
                WHERE close.status = 'CONFIRMED'
                  AND {period["close_filter"]}
                ORDER BY close.store_id
                """
            ),
            params,
        ).mappings().all()

        scope = load_business_scope(db, current_user, fallback_resource_code="revenue")
        allowed_rows = [dict(row) for row in rows if _dashboard_row_allowed(scope, dict(row))]
        department_sort_orders: dict[tuple[int, str, str], int] = {}
        departments_by_store: dict[int, dict[tuple[str, str], dict]] = {}
        for row in allowed_rows:
            store_id = int(row["store_id"])
            department_code = str(row.get("department_code") or "")
            department_name = str(row.get("department_name") or "未归属部门")
            departments_by_store.setdefault(store_id, {})[
                (department_code, department_name)
            ] = {
                "department_code": department_code,
                "department_name": department_name,
            }
        for store_id, departments in departments_by_store.items():
            for order, department in enumerate(
                sorted(departments.values(), key=department_display_sort_key),
                start=1,
            ):
                department_sort_orders[
                    (
                        store_id,
                        str(department.get("department_code") or ""),
                        str(department.get("department_name") or "未归属部门"),
                    )
                ] = order
        nc_6051_summary = _load_nc_6051_dashboard_summary(
            db,
            scope,
            financial_year=financial_year,
            financial_month=financial_month,
        )
        items = [
            {
                "store_id": int(row["store_id"]),
                "store_code": row.get("store_code"),
                "store_name": row.get("store_name"),
                "department_code": row.get("department_code"),
                "department_name": row.get("department_name") or "未归属部门",
                "department_sort_order": department_sort_orders.get(
                    (
                        int(row["store_id"]),
                        str(row.get("department_code") or ""),
                        str(row.get("department_name") or "未归属部门"),
                    )
                ),
                "group_code": row.get("group_code"),
                "group_name": row.get("group_name") or "未归属柜位",
                "unit_codes": row.get("unit_codes"),
                "unit_count": int(row.get("unit_count") or 0),
                "raw_sales_gross_profit_amount": _money(row.get("raw_sales_gross_profit_amount")),
                "raw_fee_amount": _money(row.get("raw_fee_amount")),
                "raw_extra_amount": _money(row.get("raw_extra_amount")),
                "sales_adjustment_amount": _money(row.get("sales_adjustment_amount")),
                "fee_adjustment_amount": _money(row.get("fee_adjustment_amount")),
                "extra_adjustment_amount": _money(row.get("extra_adjustment_amount")),
                "tax_adjustment_amount": _money(row.get("tax_adjustment_amount")),
                "close_adjustment_amount": _dashboard_non_tax_adjustment(row),
                "sales_gross_profit_amount": _money(row.get("sales_gross_profit_amount")),
                "fee_amount": _money(row.get("fee_amount")),
                "extra_amount": _money(row.get("extra_amount")),
                "total_amount": _money(row.get("total_amount")),
                "fee_breakdown": [
                    {
                        "fee_type_code": fee.get("fee_type_code"),
                        "fee_type_name": fee.get("fee_type_name") or "未分类收费",
                        "tax_excluded_amount": _money(fee.get("tax_excluded_amount")),
                    }
                    for fee in (row.get("fee_breakdown") or [])
                ],
            }
            for row in allowed_rows
        ]
        allowed_store_ids = {item["store_id"] for item in items}
        month_closes = [
            {
                "id": int(row["id"]),
                "store_id": int(row["store_id"]),
                "store_code": row.get("store_code"),
                "store_name": row.get("store_name"),
                "period_month": row.get("period_month"),
                "period_start_date": _dt(row.get("period_start_date")),
                "period_end_date": _dt(row.get("period_end_date")),
                "version": int(row.get("version") or 1),
                "nc_amount_before_tax": _money(row.get("nc_amount_before_tax")),
                "accrued_tax_amount": _money(row.get("accrued_tax_amount")),
                "nc_control_amount": _money(row.get("nc_control_amount")),
                "raw_fee_amount": _money(row.get("raw_fee_amount")),
                "raw_extra_amount": _money(row.get("raw_extra_amount")),
                "close_adjustment_amount": _money(row.get("close_adjustment_amount")),
                "final_fee_extra_amount": _money(row.get("final_fee_extra_amount")),
                "source_snapshot_id": row.get("source_snapshot_id"),
                "confirmed_at": _dt(row.get("confirmed_at")),
            }
            for row in close_rows
            if int(row["store_id"]) in allowed_store_ids
        ]
        close_counts_by_store: dict[int, int] = {}
        for close in month_closes:
            close_counts_by_store[close["store_id"]] = close_counts_by_store.get(close["store_id"], 0) + 1
        visible_store_ids = {item["store_id"] for item in items}
        fully_closed_store_ids = {
            store_id
            for store_id, count in close_counts_by_store.items()
            if count >= period["period_count"]
        }
        if visible_store_ids and fully_closed_store_ids == visible_store_ids:
            accounting_basis = "MONTH_CLOSED"
        elif close_counts_by_store:
            accounting_basis = "MIXED"
        else:
            accounting_basis = "REALTIME"
        return {
            "start_date": _dt(start_date),
            "end_date": _dt(end_date),
            "permission_scoped": True,
            "grain": "门店-部门-柜位",
            "date_basis": {
                "sales": "financial_date",
                "fees": "payment_date",
                "extra": period["date_basis"],
            },
            "fee_scope_note": "联营收费按财务月付款日期、租赁收费按自然月付款日期统计；剔除票减及保证金，同一来源行只计一次",
            "accounting_basis": accounting_basis,
            "fully_closed_store_ids": sorted(fully_closed_store_ids),
            "month_closes": month_closes,
            "nc_6051_summary": nc_6051_summary,
            "items": items,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "获取收益看板失败 start_date=%s end_date=%s",
            start_date,
            end_date,
        )
        raise HTTPException(
            status_code=500,
            detail="获取收益看板失败，请稍后重试",
        ) from exc


def _load_month_close_side_details(
    db: Session,
    authorized_adjustments: list[dict],
) -> tuple[dict[int, list[dict]], dict[int, list[dict]]]:
    """Load auditable NC and Fuji source rows for authorized pending differences."""
    if not authorized_adjustments:
        return {}, {}

    adjustment_ids = [int(row["id"]) for row in authorized_adjustments]
    id_params = {"adjustment_ids": adjustment_ids}
    nc_department_sql = _month_close_nc_department_sql()
    nc_rows = db.execute(
        text(
            f"""
            WITH {_revenue_department_aliases_cte()}
            SELECT
              adjustment.id AS adjustment_id,
              f.pk_detail,
              f.pk_voucher,
              TRIM(f.subject_code) AS subject_code,
              f.explanation,
              TRIM(f.valuecode) AS department_code,
              NULLIF(TRIM(f.valuename), '') AS department_name,
              COALESCE(f.localdebitamount, 0)::numeric AS debit_amount,
              COALESCE(f.localcreditamount, 0)::numeric AS credit_amount,
              (
                COALESCE(f.localcreditamount, 0)
                - COALESCE(f.localdebitamount, 0)
              )::numeric AS amount,
              (
                COALESCE(f.explanation, '')
                ~ '计提.*(销项)?税|电费收入结转销项税'
              ) AS is_accrued_tax,
              f.load_date
            FROM revenue_month_close_adjustments adjustment
            JOIN revenue_month_closes close ON close.id = adjustment.month_close_id
            JOIN stores store ON store.store_id = close.store_id
            JOIN bh_dw_gl_detail_fact2 f
              ON TRIM(f.account_year) = LEFT(close.period_month, 4)
             AND LPAD(TRIM(f.account_period), 2, '0') = RIGHT(close.period_month, 2)
             AND TRIM(f.subject_code) = TRIM(adjustment.source_subject_code)
             AND TRIM(f.valuecode) = ({nc_department_sql})
             AND TRIM(store.store_code) = ({FINANCE_STORE_CODE_SQL})
            WHERE adjustment.id IN :adjustment_ids
            ORDER BY adjustment.id, f.pk_voucher, f.pk_detail, f.load_date
            """
        ).bindparams(bindparam("adjustment_ids", expanding=True)),
        id_params,
    ).mappings().all()

    fee_type_codes = sorted(
        {
            fee_code
            for fee_codes in REVENUE_SUBJECT_FEE_CODES.values()
            for fee_code in fee_codes
        }
        | {
            fee_code.strip()
            for adjustment in authorized_adjustments
            for fee_code in str(adjustment.get("fee_type_code") or "").split(",")
            if fee_code.strip()
        }
    )
    fuji_rows = db.execute(
        text(
            """
            WITH selected_closes AS MATERIALIZED (
              SELECT DISTINCT
                close.id AS month_close_id,
                close.period_month,
                close.period_start_date,
                close.period_end_date,
                store.store_code
              FROM revenue_month_close_adjustments adjustment
              JOIN revenue_month_closes close ON close.id = adjustment.month_close_id
              JOIN stores store ON store.store_id = close.store_id
              WHERE adjustment.id IN :adjustment_ids
            )
            SELECT
              close.month_close_id,
              close.store_code,
              u.business_type,
              u.source_bill_no,
              u.source_row_no,
              u.payment_bill_no,
              CASE
                WHEN u.business_type = 'RENTAL'
                  THEN COALESCE(rental_detail.detail_group_code, u.source_group_code)
                ELSE u.source_group_code
              END AS source_group_code,
              COALESCE(group_frame.mfcname, u.source_group_name) AS source_group_name,
              department_frame.mfcode AS fuji_department_code,
              department_frame.mfcname AS fuji_department_name,
              u.supplier_code,
              u.supplier_name,
              u.contract_code,
              u.fee_type_code,
              u.fee_type_name,
              CASE
                WHEN u.business_type = 'JOINT' THEN joint_payment.auditdate
                ELSE rental_payment.auditdate
              END AS audit_date,
              COALESCE(u.tax_included_amount, 0)::numeric AS amount
            FROM selected_closes close
            JOIN dw.revenue_fee_unified u
              ON TRIM(u.store_code) = TRIM(close.store_code)
            LEFT JOIN ods.erp_suppayhead joint_payment
              ON u.business_type = 'JOINT'
             AND joint_payment.sphbillno = u.payment_bill_no
            LEFT JOIN ods.erp_mallsuppayhead rental_payment
              ON u.business_type = 'RENTAL'
             AND rental_payment.sphbillno = u.payment_bill_no
            LEFT JOIN ods.erp_supsetcharge ticket_charge
              ON u.business_type = 'JOINT'
             AND ticket_charge.sscbillno = u.source_bill_no
             AND ticket_charge.sscrowno = u.source_row_no
            LEFT JOIN dw.revenue_fee_rental_detail rental_detail
              ON u.business_type = 'RENTAL'
             AND rental_detail.source_payment_bill_no = u.source_bill_no
             AND rental_detail.source_payment_row_no = u.source_row_no
            LEFT JOIN public.manaframe group_frame
              ON group_frame.mfcode = CASE
                WHEN u.business_type = 'RENTAL'
                  THEN COALESCE(rental_detail.detail_group_code, u.source_group_code)
                ELSE u.source_group_code
              END
            LEFT JOIN public.manaframe department_frame
              ON department_frame.mfcode = group_frame.mfpcode
            WHERE TRIM(u.fee_type_code) IN :fee_type_codes
              AND COALESCE(TRIM(u.fee_type_code), '') NOT LIKE '00%'
              AND COALESCE(TRIM(ticket_charge.person1), 'N') <> 'Y'
              AND COALESCE(TRIM(u.fee_type_code), '') NOT IN ('18', '37', '38', '61', '69', '94', '95')
              AND COALESCE(TRIM(u.fee_type_name), '') !~ '保证金|质保金|代扣代缴保险费'
              AND COALESCE(TRIM(u.fee_type_name), '') !~ '旅通|瑞祥'
              AND (
                (
                  u.business_type = 'JOINT'
                  AND joint_payment.auditdate >= close.period_start_date
                  AND joint_payment.auditdate < close.period_end_date + INTERVAL '1 day'
                )
                OR (
                  u.business_type = 'RENTAL'
                  AND rental_payment.auditdate >= TO_DATE(
                    close.period_month || '-01',
                    'YYYY-MM-DD'
                  )
                  AND rental_payment.auditdate < TO_DATE(
                    close.period_month || '-01',
                    'YYYY-MM-DD'
                  ) + INTERVAL '1 month'
                )
              )
            ORDER BY
              close.month_close_id,
              audit_date,
              u.business_type,
              u.source_bill_no,
              u.source_row_no
            """
        ).bindparams(
            bindparam("adjustment_ids", expanding=True),
            bindparam("fee_type_codes", expanding=True),
        ),
        {**id_params, "fee_type_codes": fee_type_codes},
    ).mappings().all()

    nc_details: dict[int, list[dict]] = {}
    for source in nc_rows:
        adjustment_id = int(source["adjustment_id"])
        nc_details.setdefault(adjustment_id, []).append(
            {
                "detail_id": source.get("pk_detail"),
                "voucher_id": source.get("pk_voucher"),
                "subject_code": source.get("subject_code"),
                "department_code": source.get("department_code"),
                "department_name": source.get("department_name"),
                "explanation": source.get("explanation"),
                "debit_amount": _money(source.get("debit_amount")),
                "credit_amount": _money(source.get("credit_amount")),
                "amount": _money(source.get("amount")),
                "is_accrued_tax": bool(source.get("is_accrued_tax")),
                "load_date": _dt(source.get("load_date")),
            }
        )

    adjustments_by_close: dict[int, list[dict]] = {}
    for adjustment in authorized_adjustments:
        adjustments_by_close.setdefault(int(adjustment["month_close_id"]), []).append(
            adjustment
        )

    fuji_details: dict[int, list[dict]] = {}
    for source in fuji_rows:
        source_fee_code = str(source.get("fee_type_code") or "").strip()
        source_group_code = str(source.get("source_group_code") or "").strip()
        source_supplier_code = str(source.get("supplier_code") or "").strip()
        source_business_type = str(source.get("business_type") or "").strip()
        source_department_code, source_department_name = (
            _month_close_fuji_department(
                source.get("store_code"),
                source_group_code,
                source.get("fuji_department_code"),
                source.get("fuji_department_name"),
            )
        )
        detail = {
            "business_type": source.get("business_type"),
            "source_bill_no": source.get("source_bill_no"),
            "source_row_no": _dt(source.get("source_row_no")),
            "payment_bill_no": source.get("payment_bill_no"),
            "source_group_code": source.get("source_group_code"),
            "source_group_name": source.get("source_group_name"),
            "fuji_department_code": source_department_code,
            "fuji_department_name": source_department_name,
            "supplier_code": source.get("supplier_code"),
            "supplier_name": source.get("supplier_name"),
            "contract_code": source.get("contract_code"),
            "fee_type_code": source.get("fee_type_code"),
            "fee_type_name": source.get("fee_type_name"),
            "audit_date": _dt(source.get("audit_date")),
            "amount": _money(source.get("amount")),
        }
        for adjustment in adjustments_by_close.get(
            int(source["month_close_id"]), []
        ):
            adjustment_department_code = _month_close_adjustment_fuji_department(
                adjustment
            )
            mapped_fee_codes = set(
                REVENUE_SUBJECT_FEE_CODES.get(
                    str(adjustment.get("source_subject_code") or "").strip(),
                    (),
                )
            )
            explicit_fee_codes = {
                value.strip()
                for value in str(adjustment.get("fee_type_code") or "").split(",")
                if value.strip()
            }
            adjustment_group_code = str(
                adjustment.get("source_group_code") or ""
            ).strip()
            adjustment_supplier_code = str(
                adjustment.get("supplier_code") or ""
            ).strip()
            adjustment_business_type = str(
                adjustment.get("source_business_type") or ""
            ).strip()
            if source_department_code != adjustment_department_code:
                continue
            if source_fee_code not in mapped_fee_codes | explicit_fee_codes:
                continue
            if adjustment_group_code and source_group_code != adjustment_group_code:
                continue
            if (
                adjustment_supplier_code
                and source_supplier_code != adjustment_supplier_code
            ):
                continue
            if (
                adjustment_business_type in {"JOINT", "RENTAL"}
                and source_business_type != adjustment_business_type
            ):
                continue
            fuji_details.setdefault(int(adjustment["id"]), []).append(detail)
    return nc_details, fuji_details


def _month_close_match_text(value: object) -> str:
    """Normalize supplier/explanation text for conservative exact-row matching."""
    normalized = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return "".join(character for character in normalized if character.isalnum())


def _month_close_supplier_tokens(value: object) -> set[str]:
    """Return the full supplier name and a safe parent-company alias if applicable."""
    full_name = _month_close_match_text(value)
    if not full_name:
        return set()
    tokens = {full_name}
    for company_marker in (
        "有限责任公司",
        "股份有限公司",
        "有限公司",
        "股份公司",
    ):
        marker_index = full_name.find(company_marker)
        if marker_index < 0:
            continue
        marker_end = marker_index + len(company_marker)
        branch_suffix = full_name[marker_end:]
        if branch_suffix.endswith("分公司"):
            parent_name = full_name[:marker_end]
            if len(parent_name) >= 6:
                tokens.add(parent_name)
        break
    return tokens


def _month_close_supplier_match_tokens(value: object) -> set[str]:
    """Return conservative supplier tokens that also tolerate NC name truncation."""
    tokens: set[str] = set()
    supplier_aliases = set(_month_close_supplier_tokens(value))
    raw_name = unicodedata.normalize("NFKC", str(value or "")).casefold().strip()
    individual_business_qualifier = "(个体工商户)"
    if raw_name.endswith(individual_business_qualifier):
        unqualified_name = raw_name[: -len(individual_business_qualifier)].strip()
        if len(_month_close_match_text(unqualified_name)) >= 6:
            supplier_aliases.update(
                _month_close_supplier_tokens(unqualified_name)
            )
    for company_marker in (
        "有限责任公司",
        "股份有限公司",
        "有限公司",
        "股份公司",
    ):
        if not raw_name.endswith(company_marker):
            continue
        company_stem = raw_name[: -len(company_marker)]
        if company_stem.endswith(")") and "(" in company_stem:
            opening_index = company_stem.rfind("(")
            location = company_stem[opening_index + 1 : -1]
            if 1 <= len(location) <= 8:
                supplier_aliases.update(
                    _month_close_supplier_tokens(
                        f"{company_stem[:opening_index]}{company_marker}"
                    )
                )
        break
    for supplier_alias in supplier_aliases:
        tokens.add(supplier_alias)
        for company_marker in (
            "有限责任公司",
            "股份有限公司",
            "有限公司",
            "股份公司",
        ):
            if not supplier_alias.endswith(company_marker):
                continue
            company_stem = supplier_alias[: -len(company_marker)]
            if len(company_stem) >= 6:
                tokens.add(company_stem)
            break
    # NC explanations have a fixed-width supplier segment and can lose one or
    # two trailing characters. Prefix aliases remain conservative because the
    # caller still requires the same store, department, subject/fee and cents.
    for supplier_alias in tuple(tokens):
        for trim_length in (1, 2):
            if len(supplier_alias) - trim_length >= 8:
                tokens.add(supplier_alias[:-trim_length])
    return tokens


def _month_close_supplier_matches_explanation(
    supplier_name: object,
    explanation: object,
) -> bool:
    """Match an NC explanation to a Fuji supplier without using amount alone.

    NC sometimes keeps only the leading location-and-brand portion of a long
    legal supplier name. Existing full-name/legal-suffix aliases are preferred;
    otherwise require at least eight consecutive characters from the beginning
    of the normalized supplier name. This is longer than a shared district such
    as ``常州市新北区`` and avoids matching on generic company suffixes.
    """
    normalized_explanation = _month_close_match_text(explanation)
    if not normalized_explanation:
        return False

    supplier_tokens = {
        token
        for token in _month_close_supplier_match_tokens(supplier_name)
        if len(token) >= 4
    }
    if any(token in normalized_explanation for token in supplier_tokens):
        return True

    normalized_supplier = _month_close_match_text(supplier_name)
    minimum_brand_prefix_length = 8
    for prefix_length in range(
        len(normalized_supplier),
        minimum_brand_prefix_length - 1,
        -1,
    ):
        if normalized_supplier[:prefix_length] in normalized_explanation:
            return True
    return False


def _month_close_supplier_key(value: object) -> str:
    aliases = _month_close_supplier_tokens(value)
    return min(aliases, key=lambda token: (len(token), token)) if aliases else ""


def _month_close_fuji_offset_scope(detail: dict) -> tuple[str, ...] | None:
    """Return the conservative identity used for Fuji reversal offsetting."""
    business_type = str(detail.get("business_type") or "").strip().upper()
    source_bill_no = str(detail.get("source_bill_no") or "").strip().upper()
    source_group_code = str(detail.get("source_group_code") or "").strip().upper()
    supplier_key = str(detail.get("supplier_code") or "").strip().upper()
    if not supplier_key:
        supplier_key = _month_close_supplier_key(detail.get("supplier_name"))
    fee_key = str(detail.get("fee_type_code") or "").strip().upper()
    if not fee_key:
        fee_key = _month_close_match_text(detail.get("fee_type_name"))
    audit_date = str(detail.get("audit_date") or "").strip()
    scope = (
        business_type,
        source_bill_no,
        source_group_code,
        supplier_key,
        fee_key,
        audit_date,
    )
    return scope if all(scope) else None


def _offset_month_close_fuji_rows(
    fuji_details: list[dict],
) -> tuple[set[int], list[dict]]:
    """Pair exact positive/negative Fuji reversals before matching against NC."""
    candidates: dict[
        tuple[str, ...],
        dict[Decimal, dict[str, list[int]]],
    ] = {}
    for index, detail in enumerate(fuji_details):
        scope = _month_close_fuji_offset_scope(detail)
        amount = Decimal(str(detail.get("amount") or 0)).quantize(Decimal("0.01"))
        if scope is None or amount == 0:
            continue
        sign = "positive" if amount > 0 else "negative"
        candidates.setdefault(scope, {}).setdefault(
            abs(amount),
            {"positive": [], "negative": []},
        )[sign].append(index)

    matched_indexes: set[int] = set()
    offset_matches: list[dict] = []
    for amount_groups in candidates.values():
        for sign_groups in amount_groups.values():
            pair_count = min(
                len(sign_groups["positive"]),
                len(sign_groups["negative"]),
            )
            for pair_index in range(pair_count):
                indexes = sorted(
                    (
                        sign_groups["positive"][pair_index],
                        sign_groups["negative"][pair_index],
                    )
                )
                matched_indexes.update(indexes)
                details = [fuji_details[index] for index in indexes]
                offset_matches.append(
                    {
                        "match_type": "FUJI_OFFSET",
                        "amount": 0.0,
                        "supplier_name": details[0].get("supplier_name"),
                        "nc_detail_id": None,
                        "nc_voucher_id": None,
                        "fuji_source_bill_no": ",".join(
                            str(detail.get("source_bill_no") or "")
                            for detail in details
                        ),
                        "fuji_source_row_no": ",".join(
                            str(detail.get("source_row_no") or "")
                            for detail in details
                        ),
                        "source_group_code": details[0].get("source_group_code"),
                    }
                )
    return matched_indexes, offset_matches


def _reconcile_month_close_detail_rows(
    nc_details: list[dict],
    fuji_details: list[dict],
) -> dict:
    """Offset Fuji reversals, then remove exact NC/Fuji fee matches.

    The enclosing adjustment has already fixed the store, department and subject-to-fee
    scope. Exact positive/negative Fuji rows first offset only inside the same business,
    source document, group, supplier, fee item and audit date. Supplier stems then
    tolerate NC's truncated legal suffixes, while equal cents and unambiguous supplier
    grouping prevent amount-only coincidences. A single NC row may match multiple Fuji
    rows when their supplier total is equal. Accrued-tax rows remain separate because
    they do not have a Fuji fee counterpart.
    """
    tax_details = [detail for detail in nc_details if detail.get("is_accrued_tax")]
    nc_fee_details = [
        detail for detail in nc_details if not detail.get("is_accrued_tax")
    ]
    matched_nc_indexes: set[int] = set()
    matched_fuji_indexes, fuji_offset_matches = _offset_month_close_fuji_rows(
        fuji_details
    )
    auto_matches: list[dict] = list(fuji_offset_matches)

    for fuji_index, fuji_detail in enumerate(fuji_details):
        if fuji_index in matched_fuji_indexes:
            continue
        supplier_name = str(fuji_detail.get("supplier_name") or "").strip()
        fuji_amount = Decimal(str(fuji_detail.get("amount") or 0)).quantize(
            Decimal("0.01")
        )
        for nc_index, nc_detail in enumerate(nc_fee_details):
            if nc_index in matched_nc_indexes:
                continue
            nc_amount = Decimal(str(nc_detail.get("amount") or 0)).quantize(
                Decimal("0.01")
            )
            if nc_amount != fuji_amount:
                continue
            if not _month_close_supplier_matches_explanation(
                supplier_name,
                nc_detail.get("explanation"),
            ):
                continue
            matched_nc_indexes.add(nc_index)
            matched_fuji_indexes.add(fuji_index)
            auto_matches.append(
                {
                    "amount": _money(fuji_amount),
                    "supplier_name": supplier_name,
                    "nc_detail_id": nc_detail.get("detail_id"),
                    "nc_voucher_id": nc_detail.get("voucher_id"),
                    "fuji_source_bill_no": fuji_detail.get("source_bill_no"),
                    "fuji_source_row_no": fuji_detail.get("source_row_no"),
                    "source_group_code": fuji_detail.get("source_group_code"),
                }
            )
            break

    remaining_fuji_by_supplier: dict[str, list[int]] = {}
    for fuji_index, fuji_detail in enumerate(fuji_details):
        if fuji_index in matched_fuji_indexes:
            continue
        supplier_key = _month_close_supplier_key(fuji_detail.get("supplier_name"))
        if supplier_key:
            remaining_fuji_by_supplier.setdefault(supplier_key, []).append(fuji_index)

    for nc_index, nc_detail in enumerate(nc_fee_details):
        if nc_index in matched_nc_indexes:
            continue
        nc_amount = Decimal(str(nc_detail.get("amount") or 0)).quantize(
            Decimal("0.01")
        )
        aggregate_candidates: list[tuple[str, list[int], Decimal]] = []
        for supplier_key, fuji_indexes in remaining_fuji_by_supplier.items():
            if any(index in matched_fuji_indexes for index in fuji_indexes):
                continue
            supplier_name = fuji_details[fuji_indexes[0]].get("supplier_name")
            if not _month_close_supplier_matches_explanation(
                supplier_name,
                nc_detail.get("explanation"),
            ):
                continue
            supplier_amount = sum(
                (
                    Decimal(str(fuji_details[index].get("amount") or 0))
                    for index in fuji_indexes
                ),
                Decimal("0"),
            ).quantize(Decimal("0.01"))
            if supplier_amount == nc_amount:
                aggregate_candidates.append(
                    (supplier_key, fuji_indexes, supplier_amount)
                )
        if len(aggregate_candidates) != 1:
            continue
        _supplier_key, fuji_indexes, supplier_amount = aggregate_candidates[0]
        matched_nc_indexes.add(nc_index)
        matched_fuji_indexes.update(fuji_indexes)
        matched_fuji_details = [fuji_details[index] for index in fuji_indexes]
        source_group_codes = {
            str(detail.get("source_group_code") or "").strip()
            for detail in matched_fuji_details
            if str(detail.get("source_group_code") or "").strip()
        }
        auto_matches.append(
            {
                "amount": _money(supplier_amount),
                "supplier_name": matched_fuji_details[0].get("supplier_name"),
                "nc_detail_id": nc_detail.get("detail_id"),
                "nc_voucher_id": nc_detail.get("voucher_id"),
                "fuji_source_bill_no": ",".join(
                    str(detail.get("source_bill_no") or "")
                    for detail in matched_fuji_details
                ),
                "fuji_source_row_no": ",".join(
                    str(detail.get("source_row_no") or "")
                    for detail in matched_fuji_details
                ),
                "source_group_code": (
                    next(iter(source_group_codes))
                    if len(source_group_codes) == 1
                    else None
                ),
            }
        )

    # Some suppliers are split into several NC rows and several Fuji rows. After
    # exact-row and one-NC-to-many-Fuji matching, reconcile the remaining rows only
    # when every NC explanation identifies one unambiguous supplier and both
    # supplier totals agree to the cent.
    remaining_supplier_groups = {
        supplier_key: [
            index for index in fuji_indexes if index not in matched_fuji_indexes
        ]
        for supplier_key, fuji_indexes in remaining_fuji_by_supplier.items()
    }
    remaining_supplier_groups = {
        supplier_key: indexes
        for supplier_key, indexes in remaining_supplier_groups.items()
        if indexes
    }
    nc_supplier_candidates: dict[int, list[str]] = {}
    for nc_index, nc_detail in enumerate(nc_fee_details):
        if nc_index in matched_nc_indexes:
            continue
        candidate_keys = []
        for supplier_key, fuji_indexes in remaining_supplier_groups.items():
            supplier_name = fuji_details[fuji_indexes[0]].get("supplier_name")
            if _month_close_supplier_matches_explanation(
                supplier_name,
                nc_detail.get("explanation"),
            ):
                candidate_keys.append(supplier_key)
        nc_supplier_candidates[nc_index] = candidate_keys

    for supplier_key, fuji_indexes in remaining_supplier_groups.items():
        if any(index in matched_fuji_indexes for index in fuji_indexes):
            continue
        nc_indexes = [
            nc_index
            for nc_index, candidate_keys in nc_supplier_candidates.items()
            if candidate_keys == [supplier_key]
            and nc_index not in matched_nc_indexes
        ]
        if len(nc_indexes) < 2 or len(fuji_indexes) < 2:
            continue
        nc_total = sum(
            (
                Decimal(str(nc_fee_details[index].get("amount") or 0))
                for index in nc_indexes
            ),
            Decimal("0"),
        ).quantize(Decimal("0.01"))
        fuji_total = sum(
            (
                Decimal(str(fuji_details[index].get("amount") or 0))
                for index in fuji_indexes
            ),
            Decimal("0"),
        ).quantize(Decimal("0.01"))
        if nc_total != fuji_total:
            continue
        matched_nc_indexes.update(nc_indexes)
        matched_fuji_indexes.update(fuji_indexes)
        matched_fuji_details = [fuji_details[index] for index in fuji_indexes]
        source_group_codes = {
            str(detail.get("source_group_code") or "").strip()
            for detail in matched_fuji_details
            if str(detail.get("source_group_code") or "").strip()
        }
        auto_matches.append(
            {
                "amount": _money(fuji_total),
                "supplier_name": matched_fuji_details[0].get("supplier_name"),
                "nc_detail_id": ",".join(
                    str(nc_fee_details[index].get("detail_id") or "")
                    for index in nc_indexes
                ),
                "nc_voucher_id": ",".join(
                    str(nc_fee_details[index].get("voucher_id") or "")
                    for index in nc_indexes
                ),
                "fuji_source_bill_no": ",".join(
                    str(detail.get("source_bill_no") or "")
                    for detail in matched_fuji_details
                ),
                "fuji_source_row_no": ",".join(
                    str(detail.get("source_row_no") or "")
                    for detail in matched_fuji_details
                ),
                "source_group_code": (
                    next(iter(source_group_codes))
                    if len(source_group_codes) == 1
                    else None
                ),
            }
        )

    return {
        "nc_details": [
            detail
            for index, detail in enumerate(nc_fee_details)
            if index not in matched_nc_indexes
        ],
        "tax_details": tax_details,
        "tax_detail_count": len(tax_details),
        "tax_detail_amount": _money(
            sum(
                (
                    Decimal(str(detail.get("amount") or 0))
                    for detail in tax_details
                ),
                Decimal("0"),
            )
        ),
        "fuji_details": [
            detail
            for index, detail in enumerate(fuji_details)
            if index not in matched_fuji_indexes
        ],
        "auto_matched_count": len(auto_matches),
        "fuji_offset_count": len(fuji_offset_matches),
        "fuji_offset_amount": 0.0,
        "auto_matched_amount": _money(
            sum(
                (Decimal(str(item["amount"])) for item in auto_matches),
                Decimal("0"),
            )
        ),
        "auto_matches": auto_matches,
    }


def _month_close_binding_line_key(
    source_type: str,
    detail: dict,
    index: int,
) -> str:
    """Build a stable, auditable key for one unmatched NC or Fuji source row."""
    if source_type == "NC":
        identity = (
            detail.get("detail_id"),
            detail.get("voucher_id"),
        )
    elif source_type == "FUJI":
        identity = (
            detail.get("business_type"),
            detail.get("source_bill_no"),
            detail.get("source_row_no"),
        )
    else:
        identity = (detail.get("adjustment_id"),)
    normalized_parts = [str(value or "").strip() for value in identity]
    normalized = "|".join(normalized_parts)
    suffix = normalized if any(normalized_parts) else f"missing-identity-{index}"
    return f"{source_type}|{suffix}"


def _month_close_unbound_source_details(
    reconciled_details: dict,
    bound_source_line_keys: set[str] | None = None,
) -> dict:
    """Hide source rows already consumed by an earlier partial binding."""
    bound_source_line_keys = bound_source_line_keys or set()
    result = dict(reconciled_details)
    for source_type, detail_key in (("NC", "nc_details"), ("FUJI", "fuji_details")):
        details = list(reconciled_details.get(detail_key) or [])
        result[detail_key] = [
            detail
            for index, detail in enumerate(details)
            if _month_close_binding_line_key(source_type, detail, index)
            not in bound_source_line_keys
        ]
    return result


def _month_close_bindable_decimal(row: dict) -> Decimal:
    """Return the non-tax difference that still needs a cabinet assignment."""
    adjustment_amount = Decimal(str(row.get("adjustment_amount") or 0))
    accrued_tax_amount = Decimal(str(row.get("accrued_tax_amount") or 0))
    return (adjustment_amount - accrued_tax_amount).quantize(Decimal("0.01"))


def _month_close_bindable_amount(row: dict) -> float:
    return _money(_month_close_bindable_decimal(row))


def _month_close_binding_target_amount(row: dict) -> float:
    """Return the NC/Fuji comparison target before accrued tax."""
    final_amount = Decimal(str(row.get("final_amount") or 0))
    accrued_tax_amount = Decimal(str(row.get("accrued_tax_amount") or 0))
    return _money((final_amount - accrued_tax_amount).quantize(Decimal("0.01")))


def _month_close_binding_lines(
    row: dict,
    reconciled_details: dict,
    bound_source_line_keys: set[str] | None = None,
) -> list[dict]:
    """Split one pending adjustment into source-row binding operations.

    The total suggested binding amount always equals the current pending adjustment.
    NC/Fuji gross source amounts are only weights; the month-close adjustment itself
    remains the amount posted to the selected cabinet and counter group.
    """
    bound_source_line_keys = bound_source_line_keys or set()
    pending_amount = _month_close_bindable_decimal(row)
    direction = str(row.get("difference_direction") or "OTHER").upper()
    nc_details = list(reconciled_details.get("nc_details") or [])
    fuji_details = list(reconciled_details.get("fuji_details") or [])

    if direction == "NC_ONLY":
        source_type, source_details = "NC", nc_details
    elif direction == "FUJI_ONLY":
        source_type, source_details = "FUJI", fuji_details
    elif direction == "AMOUNT_DIFFERENCE":
        if pending_amount >= 0:
            source_type, source_details = "NC", nc_details
        else:
            source_type, source_details = "FUJI", fuji_details
    elif nc_details:
        source_type, source_details = "NC", nc_details
    else:
        source_type, source_details = "FUJI", fuji_details

    if not source_details:
        alternate_type = "FUJI" if source_type == "NC" else "NC"
        alternate_details = fuji_details if alternate_type == "FUJI" else nc_details
        if alternate_details:
            source_type, source_details = alternate_type, alternate_details

    candidates: list[dict] = []
    for index, detail in enumerate(source_details):
        source_line_key = _month_close_binding_line_key(source_type, detail, index)
        if source_line_key in bound_source_line_keys:
            continue
        candidates.append(
            {
                "source_line_key": source_line_key,
                "source_type": source_type,
                "source_detail_id": detail.get("detail_id"),
                "source_voucher_id": detail.get("voucher_id"),
                "source_bill_no": detail.get("source_bill_no"),
                "source_row_no": detail.get("source_row_no"),
                "source_amount": _money(detail.get("amount")),
            }
        )

    if not candidates:
        fallback_detail = {"adjustment_id": row.get("id")}
        fallback_key = _month_close_binding_line_key("ADJUSTMENT", fallback_detail, 0)
        if fallback_key not in bound_source_line_keys:
            candidates.append(
                {
                    "source_line_key": fallback_key,
                    "source_type": "ADJUSTMENT",
                    "source_detail_id": None,
                    "source_voucher_id": None,
                    "source_bill_no": None,
                    "source_row_no": None,
                    "source_amount": _money(pending_amount),
                }
            )

    if not candidates:
        return []

    weights = [abs(Decimal(str(line.get("source_amount") or 0))) for line in candidates]
    total_weight = sum(weights, Decimal("0"))
    if total_weight == 0:
        weights = [Decimal("1") for _line in candidates]
        total_weight = Decimal(len(candidates))

    allocated = Decimal("0")
    for index, line in enumerate(candidates):
        if index == len(candidates) - 1:
            suggested_amount = pending_amount - allocated
        else:
            suggested_amount = (
                pending_amount * weights[index] / total_weight
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            allocated += suggested_amount
        line["suggested_binding_amount"] = _money(suggested_amount)
    return candidates


def _load_bound_month_close_source_line_keys(
    db: Session,
    adjustment_ids: list[int],
) -> dict[int, set[str]]:
    """Return source rows already consumed by earlier partial bindings."""
    if not adjustment_ids:
        return {}
    rows = db.execute(
        text(
            """
            SELECT
              parent_adjustment_id,
              raw_payload ->> 'manual_binding_source_line_key' AS source_line_key
            FROM revenue_month_close_adjustments
            WHERE parent_adjustment_id IN :adjustment_ids
              AND binding_status = 'BOUND'
              AND NULLIF(
                TRIM(raw_payload ->> 'manual_binding_source_line_key'),
                ''
              ) IS NOT NULL
            """
        ).bindparams(bindparam("adjustment_ids", expanding=True)),
        {"adjustment_ids": adjustment_ids},
    ).mappings().all()
    result: dict[int, set[str]] = {}
    for row in rows:
        result.setdefault(int(row["parent_adjustment_id"]), set()).add(
            str(row["source_line_key"])
        )
    return result


def _filter_month_close_display_rows(
    rows: list[dict],
    reconciled_details_by_adjustment: dict[int, dict],
) -> list[dict]:
    """Hide tax detail and rows that have no remaining NC/Fuji fee variance."""
    visible_rows: list[dict] = []
    for row in rows:
        adjustment_id = int(row["id"])
        details = reconciled_details_by_adjustment.get(adjustment_id)
        if _month_close_bindable_decimal(row) == 0:
            continue
        if details is None:
            visible_rows.append(row)
            continue
        expected_tax = Decimal(str(row.get("accrued_tax_amount") or 0)).quantize(
            Decimal("0.01")
        )
        source_tax = Decimal(str(details.get("tax_detail_amount") or 0)).quantize(
            Decimal("0.01")
        )
        tax_detail_count = int(details.get("tax_detail_count") or 0)
        tax_reconciled = expected_tax == source_tax
        if tax_reconciled:
            details["reconciled_tax_amount"] = _money(source_tax)
        details["tax_details"] = []
        details["tax_detail_count"] = 0
        details["tax_detail_amount"] = 0.0
        has_unmatched_fees = bool(
            details.get("nc_details") or details.get("fuji_details")
        )
        has_reconciliation_evidence = bool(
            details.get("auto_matched_count") or tax_detail_count
        )
        if (
            not has_unmatched_fees
            and has_reconciliation_evidence
        ):
            continue
        visible_rows.append(row)
    return visible_rows


def _month_close_direction_summary(rows: list[dict]) -> dict[str, dict]:
    summary = {}
    for direction in ("NC_ONLY", "FUJI_ONLY", "AMOUNT_DIFFERENCE", "OTHER"):
        direction_rows = [
            row for row in rows if row.get("difference_direction") == direction
        ]
        summary[direction] = {
            "count": len(direction_rows),
            "amount": _money(
                sum(
                    (
                        _month_close_bindable_decimal(row)
                        for row in direction_rows
                    ),
                    Decimal("0"),
                )
            ),
        }
    return summary


def _month_close_store_summaries(
    visible_rows: list[dict],
    allowed_rows: list[dict],
    reconciled_details_by_adjustment: dict[int, dict],
) -> list[dict]:
    """Summarize unresolved and auto-matched month-close rows by store."""
    visible_store_ids = sorted(
        {int(row["store_id"]) for row in visible_rows},
        key=lambda store_id: min(
            str(row.get("store_code") or "")
            for row in visible_rows
            if int(row["store_id"]) == store_id
        ),
    )
    summaries = []
    for store_id in visible_store_ids:
        store_visible_rows = [
            row for row in visible_rows if int(row["store_id"]) == store_id
        ]
        store_allowed_rows = [
            row for row in allowed_rows if int(row["store_id"]) == store_id
        ]
        first_row = store_visible_rows[0]
        auto_matched_count = sum(
            int(
                reconciled_details_by_adjustment.get(int(row["id"]), {}).get(
                    "auto_matched_count", 0
                )
                or 0
            )
            for row in store_allowed_rows
        )
        auto_matched_amount = _money(
            sum(
                (
                    Decimal(
                        str(
                            reconciled_details_by_adjustment.get(
                                int(row["id"]), {}
                            ).get("auto_matched_amount", 0)
                            or 0
                        )
                    )
                    for row in store_allowed_rows
                ),
                Decimal("0"),
            )
        )
        summaries.append(
            {
                "store_id": store_id,
                "store_code": first_row.get("store_code"),
                "store_name": first_row.get("store_name"),
                "pending_count": len(store_visible_rows),
                "pending_amount": _money(
                    sum(
                        (
                            _month_close_bindable_decimal(row)
                            for row in store_visible_rows
                        ),
                        Decimal("0"),
                    )
                ),
                "auto_matched_count": auto_matched_count,
                "auto_matched_amount": auto_matched_amount,
                "direction_summary": _month_close_direction_summary(
                    store_visible_rows
                ),
            }
        )
    return summaries


@router.get("/dashboard/month-close-bindings")
async def revenue_month_close_pending_bindings(
    start_date: date,
    end_date: date,
    financial_year: Optional[int] = Query(None, ge=2000, le=2100),
    financial_month: Optional[int] = Query(None, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List every unresolved NC/Fuji month-close difference in both directions."""
    require_permission(db, current_user, "revenue.dashboard.view")
    period = _dashboard_financial_period(
        start_date=start_date,
        end_date=end_date,
        financial_year=financial_year,
        financial_month=financial_month,
    )
    params: dict = {"start_date": start_date, "end_date": end_date}
    if period.get("period_month_start"):
        params["period_month_start"] = period["period_month_start"]
        params["period_month_end"] = period["period_month_end"]

    rows = db.execute(
        text(
            f"""
            WITH {_revenue_department_aliases_cte()}
            SELECT
              adjustment.id,
              close.id AS month_close_id,
              close.store_id,
              store.store_code,
              store.store_name,
              close.period_month,
              adjustment.target_component,
              adjustment.adjustment_category,
              COALESCE(
                department_alias.canonical_department_code,
                adjustment.source_department_code
              ) AS department_code,
              COALESCE(
                department_alias.canonical_department_name,
                adjustment.source_department_name
              ) AS department_name,
              adjustment.source_department_code,
              adjustment.source_department_name,
              adjustment.source_subject_code,
              adjustment.source_subject_name,
              adjustment.source_business_type,
              adjustment.source_group_code,
              adjustment.source_group_name,
              CASE
                WHEN adjustment.source_business_type = 'NC_EXTRA_DIFFERENCE'
                  THEN 'NC_ONLY'
                WHEN adjustment.source_business_type = 'FEE_DIFFERENCE'
                  THEN 'AMOUNT_DIFFERENCE'
                WHEN adjustment.source_business_type IN ('JOINT', 'RENTAL')
                  THEN 'FUJI_ONLY'
                ELSE 'OTHER'
              END AS difference_direction,
              adjustment.supplier_code,
              adjustment.supplier_name,
              adjustment.fee_type_code,
              adjustment.fee_type_name,
              adjustment.raw_amount,
              adjustment.accrued_tax_amount,
              adjustment.adjustment_amount,
              adjustment.final_amount,
              adjustment.adjustment_reason,
              adjustment.allocation_basis,
              adjustment.created_at
            FROM revenue_month_closes close
            JOIN stores store ON store.store_id = close.store_id
            JOIN revenue_month_close_adjustments adjustment
              ON adjustment.month_close_id = close.id
             AND adjustment.binding_status = 'PENDING'
            LEFT JOIN revenue_department_aliases department_alias
              ON TRIM(department_alias.store_code) = TRIM(store.store_code)
             AND department_alias.source_department_code = NULLIF(
               TRIM(adjustment.source_department_code),
               ''
             )
            WHERE close.status = 'CONFIRMED'
              AND {period['close_filter']}
            ORDER BY
              store.store_code,
              adjustment.source_department_code,
              adjustment.source_subject_code,
              ABS(adjustment.adjustment_amount) DESC,
              adjustment.id
            """
        ),
        params,
    ).mappings().all()
    scope = load_business_scope(db, current_user, fallback_resource_code="revenue")
    allowed = _collapse_legacy_mapped_fuji_rows(
        [
            dict(row)
            for row in rows
            if _dashboard_row_allowed(scope, dict(row))
            and not _is_fuji_non_matchable_fee_row(
                row.get("fee_type_code"),
                row.get("fee_type_name"),
            )
            and not _is_non_fuji_month_close_department(dict(row))
        ]
    )
    nc_details_by_adjustment, fuji_details_by_adjustment = _load_month_close_side_details(
        db,
        allowed,
    )
    reconciled_details_by_adjustment = {
        int(row["id"]): _reconcile_month_close_detail_rows(
            nc_details_by_adjustment.get(int(row["id"]), []),
            fuji_details_by_adjustment.get(int(row["id"]), []),
        )
        for row in allowed
    }
    bound_source_line_keys_by_adjustment = _load_bound_month_close_source_line_keys(
        db,
        [int(row["id"]) for row in allowed],
    )
    auto_matched_count = sum(
        details["auto_matched_count"]
        for details in reconciled_details_by_adjustment.values()
    )
    auto_matched_amount = _money(
        sum(
            (
                Decimal(str(details["auto_matched_amount"]))
                for details in reconciled_details_by_adjustment.values()
            ),
            Decimal("0"),
        )
    )
    visible_rows = _filter_month_close_display_rows(
        allowed,
        reconciled_details_by_adjustment,
    )
    unbound_details_by_adjustment = {
        int(row["id"]): _month_close_unbound_source_details(
            reconciled_details_by_adjustment[int(row["id"])],
            bound_source_line_keys_by_adjustment.get(int(row["id"]), set()),
        )
        for row in visible_rows
    }
    direction_summary = _month_close_direction_summary(visible_rows)
    store_summaries = _month_close_store_summaries(
        visible_rows,
        allowed,
        reconciled_details_by_adjustment,
    )
    store_ids = sorted({int(row["store_id"]) for row in visible_rows})
    unit_options = []
    if store_ids:
        unit_rows = db.execute(
            text(
                """
                SELECT DISTINCT
                  store.store_id,
                  unit.id AS unit_id,
                  unit.unit_code,
                  floor.name AS floor_name,
                  COALESCE(binding.counter_group_id, legacy_group.group_id) AS group_id,
                  NULLIF(TRIM(contract_group.cmfmfid), '') AS group_code,
                  COALESCE(
                    NULLIF(TRIM(group_frame.mfcname), ''),
                    NULLIF(TRIM(legacy_group.group_name), ''),
                    NULLIF(TRIM(contract_group.cmfmfid), '')
                  ) AS group_name,
                  NULLIF(TRIM(department_frame.mfcode), '') AS group_department_code,
                  NULLIF(TRIM(department_frame.mfcname), '') AS group_department_name
                FROM business_units unit
                JOIN floors floor ON floor.id = unit.floor_id
                JOIN stores store
                  ON TRIM(store.store_code) = TRIM(floor.store_code)
                LEFT JOIN business_unit_binding binding
                  ON binding.shop_unit_id = unit.id
                 AND COALESCE(binding.status, 'ACTIVE') = 'ACTIVE'
                 AND COALESCE(binding.start_date, DATE '1900-01-01') <= :end_date
                 AND COALESCE(binding.end_date, DATE '2999-12-31') >= :start_date
                LEFT JOIN contmain contract
                  ON UPPER(TRIM(contract.cmcontno)) = UPPER(TRIM(binding.contract_id))
                 AND TRIM(contract.cmjsmkt) = TRIM(floor.store_code)
                 AND COALESCE(contract.cmeffdate::date, DATE '1900-01-01') <= :end_date
                 AND COALESCE(contract.cmlapdate::date, DATE '2999-12-31') >= :start_date
                LEFT JOIN contmanaframe contract_group
                  ON UPPER(TRIM(contract_group.cmfcontno)) = UPPER(TRIM(binding.contract_id))
                 AND TRIM(contract_group.cmfmarket) = TRIM(floor.store_code)
                 AND COALESCE(
                       contract_group.cmfeffdate::date,
                       contract.cmeffdate::date,
                       DATE '1900-01-01'
                     ) <= :end_date
                LEFT JOIN manaframe group_frame
                  ON TRIM(group_frame.mfcode) = TRIM(contract_group.cmfmfid)
                LEFT JOIN manaframe department_frame
                  ON TRIM(department_frame.mfcode) = TRIM(group_frame.mfpcode)
                LEFT JOIN counter_groups legacy_group
                  ON TRIM(legacy_group.group_code) = TRIM(contract_group.cmfmfid)
                WHERE store.store_id IN :store_ids
                  AND COALESCE(unit.status, 'ACTIVE') <> 'INACTIVE'
                ORDER BY
                  store.store_id,
                  floor.name,
                  unit.unit_code,
                  group_code
                """
            ).bindparams(bindparam("store_ids", expanding=True)),
            {
                "store_ids": store_ids,
                "start_date": start_date,
                "end_date": end_date,
            },
        ).mappings().all()
        unit_option_map: dict[tuple[int, int], dict] = {}
        for unit_row in unit_rows:
            option_key = (int(unit_row["store_id"]), int(unit_row["unit_id"]))
            option = unit_option_map.setdefault(
                option_key,
                {
                    "store_id": option_key[0],
                    "unit_id": option_key[1],
                    "unit_code": unit_row.get("unit_code"),
                    "floor_name": unit_row.get("floor_name"),
                    "group_options": [],
                },
            )
            if unit_row.get("group_code"):
                option["group_options"].append(
                    {
                        "group_id": (
                            int(unit_row["group_id"])
                            if unit_row.get("group_id") is not None
                            else None
                        ),
                        "group_code": unit_row.get("group_code"),
                        "group_name": unit_row.get("group_name"),
                        "department_code": unit_row.get("group_department_code"),
                        "department_name": unit_row.get("group_department_name"),
                    }
                )
        unit_options = list(unit_option_map.values())

    return {
        "start_date": _dt(start_date),
        "end_date": _dt(end_date),
        "pending_count": len(visible_rows),
        "pending_amount": _money(
            sum(
                (
                    _month_close_bindable_decimal(row)
                    for row in visible_rows
                ),
                Decimal("0"),
            )
        ),
        "auto_matched_count": auto_matched_count,
        "auto_matched_amount": auto_matched_amount,
        "direction_summary": direction_summary,
        "store_summaries": store_summaries,
        "items": [
            {
                **row,
                "id": int(row["id"]),
                "month_close_id": int(row["month_close_id"]),
                "store_id": int(row["store_id"]),
                "raw_amount": _money(row.get("raw_amount")),
                "accrued_tax_amount": _money(row.get("accrued_tax_amount")),
                "adjustment_amount": _month_close_bindable_amount(row),
                "final_amount": _month_close_binding_target_amount(row),
                "nc_details": unbound_details_by_adjustment[int(row["id"])][
                    "nc_details"
                ],
                "nc_detail_count": len(
                    unbound_details_by_adjustment[int(row["id"])]["nc_details"]
                ),
                "nc_detail_amount": _money(
                    sum(
                        (
                            Decimal(str(detail["amount"]))
                            for detail in unbound_details_by_adjustment[
                                int(row["id"])
                            ]["nc_details"]
                        ),
                        Decimal("0"),
                    )
                ),
                "tax_details": reconciled_details_by_adjustment[int(row["id"])][
                    "tax_details"
                ],
                "tax_detail_count": reconciled_details_by_adjustment[
                    int(row["id"])
                ]["tax_detail_count"],
                "tax_detail_amount": reconciled_details_by_adjustment[
                    int(row["id"])
                ]["tax_detail_amount"],
                "fuji_details": unbound_details_by_adjustment[int(row["id"])][
                    "fuji_details"
                ],
                "fuji_detail_count": len(
                    unbound_details_by_adjustment[int(row["id"])]["fuji_details"]
                ),
                "fuji_detail_amount": _money(
                    sum(
                        (
                            Decimal(str(detail["amount"]))
                            for detail in unbound_details_by_adjustment[
                                int(row["id"])
                            ]["fuji_details"]
                        ),
                        Decimal("0"),
                    )
                ),
                "auto_matched_count": reconciled_details_by_adjustment[
                    int(row["id"])
                ]["auto_matched_count"],
                "auto_matched_amount": reconciled_details_by_adjustment[
                    int(row["id"])
                ]["auto_matched_amount"],
                "auto_matches": reconciled_details_by_adjustment[int(row["id"])][
                    "auto_matches"
                ],
                "binding_lines": _month_close_binding_lines(
                    row,
                    unbound_details_by_adjustment[int(row["id"])],
                ),
                "created_at": _dt(row.get("created_at")),
            }
            for row in visible_rows
        ],
        "unit_options": unit_options,
    }


@router.post("/dashboard/month-close-bindings/{adjustment_id}/bind")
async def bind_revenue_month_close_difference(
    adjustment_id: int,
    body: RevenueMonthCloseBindingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bind one unresolved NC/Fuji month-close difference to a cabinet."""
    require_permission(db, current_user, "revenue.recalculate")
    adjustment = db.execute(
        text(
            f"""
            WITH {_revenue_department_aliases_cte()}
            SELECT
              adjustment.id,
              adjustment.month_close_id,
              adjustment.binding_status,
              adjustment.raw_amount,
              adjustment.accrued_tax_amount,
              adjustment.adjustment_amount,
              adjustment.final_amount,
              adjustment.source_department_code,
              adjustment.source_department_name,
              adjustment.source_subject_code,
              adjustment.source_subject_name,
              adjustment.source_business_type,
              adjustment.source_group_code,
              adjustment.source_group_name,
              adjustment.supplier_code,
              adjustment.supplier_name,
              adjustment.fee_type_code,
              adjustment.fee_type_name,
              COALESCE(
                department_alias.canonical_department_code,
                adjustment.source_department_code
              ) AS department_code,
              COALESCE(
                department_alias.canonical_department_name,
                adjustment.source_department_name
              ) AS department_name,
              close.store_id,
              store.store_code,
              close.period_month,
              close.period_start_date,
              close.period_end_date,
              CASE
                WHEN adjustment.source_business_type = 'NC_EXTRA_DIFFERENCE'
                  THEN 'NC_ONLY'
                WHEN adjustment.source_business_type = 'FEE_DIFFERENCE'
                  THEN 'AMOUNT_DIFFERENCE'
                WHEN adjustment.source_business_type IN ('JOINT', 'RENTAL')
                  THEN 'FUJI_ONLY'
                ELSE 'OTHER'
              END AS difference_direction
            FROM revenue_month_close_adjustments adjustment
            JOIN revenue_month_closes close ON close.id = adjustment.month_close_id
            JOIN stores store ON store.store_id = close.store_id
            LEFT JOIN revenue_department_aliases department_alias
              ON TRIM(department_alias.store_code) = TRIM(store.store_code)
             AND department_alias.source_department_code = NULLIF(
               TRIM(adjustment.source_department_code),
               ''
             )
            WHERE adjustment.id = :adjustment_id
              AND close.status = 'CONFIRMED'
            FOR UPDATE OF adjustment
            """
        ),
        {"adjustment_id": adjustment_id},
    ).mappings().one_or_none()
    if not adjustment:
        raise HTTPException(status_code=404, detail="待绑定月结差异不存在")
    if adjustment["binding_status"] != "PENDING":
        raise HTTPException(status_code=409, detail="该月结差异已完成绑定")

    scope = load_business_scope(db, current_user, fallback_resource_code="revenue")
    if not _dashboard_row_allowed(scope, dict(adjustment)):
        raise HTTPException(status_code=403, detail="无权处理该门店或部门的月结差异")

    nc_details_by_adjustment, fuji_details_by_adjustment = _load_month_close_side_details(
        db,
        [dict(adjustment)],
    )
    reconciled_details = _reconcile_month_close_detail_rows(
        nc_details_by_adjustment.get(adjustment_id, []),
        fuji_details_by_adjustment.get(adjustment_id, []),
    )
    bound_source_line_keys = _load_bound_month_close_source_line_keys(
        db,
        [adjustment_id],
    ).get(adjustment_id, set())
    binding_lines = _month_close_binding_lines(
        dict(adjustment),
        reconciled_details,
        bound_source_line_keys,
    )
    selected_line = next(
        (
            line
            for line in binding_lines
            if line["source_line_key"] == body.source_line_key
        ),
        None,
    )
    if selected_line is None:
        raise HTTPException(status_code=409, detail="该来源明细已绑定或不属于当前差异")

    unit = db.execute(
        text(
            """
            SELECT
              unit.id,
              unit.unit_code,
              store.store_id
            FROM business_units unit
            JOIN floors floor ON floor.id = unit.floor_id
            JOIN stores store
              ON TRIM(store.store_code) = TRIM(floor.store_code)
            WHERE unit.id = :unit_id
            """
        ),
        {"unit_id": body.unit_id},
    ).mappings().one_or_none()
    if not unit:
        raise HTTPException(status_code=400, detail="选择的柜位不存在")
    if int(unit["store_id"]) != int(adjustment["store_id"]):
        raise HTTPException(status_code=400, detail="只能绑定到同一门店的柜位")

    counter_group = db.execute(
        text(
            """
            SELECT DISTINCT
              COALESCE(binding.counter_group_id, legacy_group.group_id) AS group_id,
              TRIM(contract_group.cmfmfid) AS group_code,
              COALESCE(
                NULLIF(TRIM(group_frame.mfcname), ''),
                NULLIF(TRIM(legacy_group.group_name), ''),
                TRIM(contract_group.cmfmfid)
              ) AS group_name,
              NULLIF(TRIM(department_frame.mfcode), '') AS department_code,
              NULLIF(TRIM(department_frame.mfcname), '') AS department_name
            FROM business_unit_binding binding
            JOIN business_units unit ON unit.id = binding.shop_unit_id
            JOIN floors floor ON floor.id = unit.floor_id
            JOIN contmain contract
              ON UPPER(TRIM(contract.cmcontno)) = UPPER(TRIM(binding.contract_id))
             AND TRIM(contract.cmjsmkt) = TRIM(floor.store_code)
            JOIN contmanaframe contract_group
              ON UPPER(TRIM(contract_group.cmfcontno)) = UPPER(TRIM(binding.contract_id))
             AND TRIM(contract_group.cmfmarket) = TRIM(floor.store_code)
            LEFT JOIN manaframe group_frame
              ON TRIM(group_frame.mfcode) = TRIM(contract_group.cmfmfid)
            LEFT JOIN manaframe department_frame
              ON TRIM(department_frame.mfcode) = TRIM(group_frame.mfpcode)
            LEFT JOIN counter_groups legacy_group
              ON TRIM(legacy_group.group_code) = TRIM(contract_group.cmfmfid)
            WHERE binding.shop_unit_id = :unit_id
              AND UPPER(TRIM(contract_group.cmfmfid)) = UPPER(TRIM(:source_group_code))
              AND COALESCE(binding.status, 'ACTIVE') = 'ACTIVE'
              AND COALESCE(binding.start_date, DATE '1900-01-01') <= :period_end_date
              AND COALESCE(binding.end_date, DATE '2999-12-31') >= :period_start_date
              AND COALESCE(contract.cmeffdate::date, DATE '1900-01-01') <= :period_end_date
              AND COALESCE(contract.cmlapdate::date, DATE '2999-12-31') >= :period_start_date
              AND COALESCE(
                    contract_group.cmfeffdate::date,
                    contract.cmeffdate::date,
                    DATE '1900-01-01'
                  ) <= :period_end_date
            """
        ),
        {
            "unit_id": body.unit_id,
            "source_group_code": body.source_group_code,
            "period_start_date": adjustment["period_start_date"],
            "period_end_date": adjustment["period_end_date"],
        },
    ).mappings().one_or_none()
    if not counter_group:
        raise HTTPException(
            status_code=400,
            detail="所选柜组不是该柜位在本月有效的对应柜组",
        )

    pending_amount = _month_close_bindable_decimal(dict(adjustment))
    accrued_tax_amount = Decimal(
        str(adjustment.get("accrued_tax_amount") or 0)
    ).quantize(Decimal("0.01"))
    suggested_binding_amount = Decimal(
        str(selected_line["suggested_binding_amount"])
    ).quantize(Decimal("0.01"))
    binding_amount = (
        Decimal(str(body.adjustment_amount)).quantize(Decimal("0.01"))
        if body.adjustment_amount is not None
        else suggested_binding_amount
    )
    if binding_amount == 0:
        raise HTTPException(status_code=400, detail="绑定金额不能为0")
    if (pending_amount > 0) != (binding_amount > 0):
        raise HTTPException(status_code=400, detail="绑定金额方向必须与待绑定差额一致")
    if abs(binding_amount) > abs(pending_amount):
        raise HTTPException(status_code=400, detail="绑定金额不能超过待绑定差额")
    if binding_amount != suggested_binding_amount:
        raise HTTPException(
            status_code=400,
            detail="本行绑定金额已变化，请刷新后按最新金额绑定",
        )

    update_params = {
        "adjustment_id": adjustment_id,
        "target_component": body.target_component,
        "unit_id": int(unit["id"]),
        "unit_code": unit.get("unit_code"),
        "counter_group_id": (
            int(counter_group["group_id"])
            if counter_group.get("group_id") is not None
            else None
        ),
        "source_group_code": counter_group.get("group_code"),
        "source_group_name": counter_group.get("group_name"),
        "source_line_key": body.source_line_key,
        "source_line_type": selected_line.get("source_type"),
        "source_detail_id": selected_line.get("source_detail_id"),
        "source_voucher_id": selected_line.get("source_voucher_id"),
        "source_bill_no": selected_line.get("source_bill_no"),
        "source_row_no": selected_line.get("source_row_no"),
        "bound_by": int(current_user.user_id),
        "binding_note": body.note.strip() if body.note else None,
        "binding_amount": binding_amount,
        "accrued_tax_amount": accrued_tax_amount,
        "remaining_bindable_amount": pending_amount - binding_amount,
        "remaining_adjustment_amount": (
            pending_amount - binding_amount + accrued_tax_amount
        ),
    }
    if binding_amount == pending_amount and accrued_tax_amount == 0:
        updated = db.execute(
            text(
                """
                UPDATE revenue_month_close_adjustments
                SET target_component = :target_component,
                    unit_id = :unit_id,
                    unit_code = :unit_code,
                    source_group_code = COALESCE(:source_group_code, :unit_code),
                    source_group_name = COALESCE(:source_group_name, :unit_code),
                    binding_status = 'BOUND',
                    bound_by = :bound_by,
                    bound_at = NOW(),
                    binding_note = :binding_note,
                    raw_payload = COALESCE(raw_payload, '{}'::jsonb) || JSONB_BUILD_OBJECT(
                      'manual_binding_counter_group_id', :counter_group_id,
                      'manual_binding_target_component', :target_component,
                      'manual_binding_source_line_key', :source_line_key,
                      'manual_binding_source_line_type', :source_line_type,
                      'manual_binding_source_detail_id', :source_detail_id,
                      'manual_binding_source_voucher_id', :source_voucher_id,
                      'manual_binding_source_bill_no', :source_bill_no,
                      'manual_binding_source_row_no', :source_row_no
                    )
                WHERE id = :adjustment_id
                  AND binding_status = 'PENDING'
                RETURNING id, unit_id, unit_code, source_group_code, source_group_name,
                          binding_status, adjustment_amount, bound_at
                """
            ),
            update_params,
        ).mappings().one()
    else:
        updated = db.execute(
            text(
                """
                INSERT INTO revenue_month_close_adjustments (
                  month_close_id, target_component, adjustment_category,
                  unit_id, unit_code, source_group_code, source_group_name,
                  source_department_code, source_department_name,
                  source_subject_code, source_subject_name, source_business_type,
                  supplier_code, supplier_name, fee_type_code, fee_type_name,
                  raw_amount, accrued_tax_amount, adjustment_amount, final_amount,
                  allocation_basis, adjustment_reason, source_row_key,
                  binding_status, bound_by, bound_at, binding_note,
                  parent_adjustment_id, raw_payload
                )
                SELECT
                  source.month_close_id, :target_component, source.adjustment_category,
                  :unit_id, :unit_code,
                  COALESCE(:source_group_code, :unit_code),
                  COALESCE(:source_group_name, :unit_code),
                  source.source_department_code, source.source_department_name,
                  source.source_subject_code, source.source_subject_name,
                  source.source_business_type, source.supplier_code, source.supplier_name,
                  source.fee_type_code, source.fee_type_name,
                  0, 0, :binding_amount, :binding_amount,
                  '人工绑定部分金额', source.adjustment_reason,
                  LEFT(source.source_row_key || ':bound:' || source.id::text, 160),
                  'BOUND', :bound_by, NOW(), :binding_note,
                  source.id,
                  COALESCE(source.raw_payload, '{}'::jsonb) || JSONB_BUILD_OBJECT(
                    'manual_binding_amount', :binding_amount,
                    'manual_binding_unit_id', :unit_id,
                    'manual_binding_counter_group_id', :counter_group_id,
                    'manual_binding_target_component', :target_component,
                    'manual_binding_source_line_key', :source_line_key,
                    'manual_binding_source_line_type', :source_line_type,
                    'manual_binding_source_detail_id', :source_detail_id,
                    'manual_binding_source_voucher_id', :source_voucher_id,
                    'manual_binding_source_bill_no', :source_bill_no,
                    'manual_binding_source_row_no', :source_row_no
                  )
                FROM revenue_month_close_adjustments source
                WHERE source.id = :adjustment_id
                  AND source.binding_status = 'PENDING'
                RETURNING id, unit_id, unit_code, source_group_code, source_group_name,
                          binding_status, adjustment_amount, bound_at
                """
            ),
            update_params,
        ).mappings().one()
        if update_params["remaining_bindable_amount"] == 0:
            db.execute(
                text(
                    """
                    UPDATE revenue_month_close_adjustments
                    SET adjustment_amount = :accrued_tax_amount,
                        final_amount = raw_amount + :accrued_tax_amount,
                        binding_status = 'BOUND',
                        bound_by = :bound_by,
                        bound_at = NOW(),
                        allocation_basis = '计提税不参与柜位绑定',
                        binding_note = CONCAT(
                          COALESCE(binding_note || '；', ''),
                          '非税差额已逐笔绑定；计提税不绑定柜位'
                        ),
                        raw_payload = raw_payload || JSONB_BUILD_OBJECT(
                          'manual_binding_tax_only_remainder', TRUE
                        )
                    WHERE id = :adjustment_id
                      AND binding_status = 'PENDING'
                    """
                ),
                update_params,
            )
        else:
            db.execute(
                text(
                    """
                    UPDATE revenue_month_close_adjustments
                    SET adjustment_amount = :remaining_adjustment_amount,
                        final_amount = raw_amount + :remaining_adjustment_amount,
                        binding_note = CONCAT(
                          COALESCE(binding_note || '；', ''),
                          '已人工绑定非税部分金额 ', CAST(:binding_amount AS TEXT)
                        )
                    WHERE id = :adjustment_id
                      AND binding_status = 'PENDING'
                    """
                ),
                update_params,
            )
    db.commit()
    return {
        "message": "月结差异已绑定到柜位",
        "item": {
            **dict(updated),
            "id": int(updated["id"]),
            "unit_id": int(updated["unit_id"]),
            "counter_group_id": (
                int(counter_group["group_id"])
                if counter_group.get("group_id") is not None
                else None
            ),
            "source_group_code": counter_group.get("group_code"),
            "source_group_name": counter_group.get("group_name"),
            "source_line_key": body.source_line_key,
            "target_component": body.target_component,
            "adjustment_amount": _money(updated.get("adjustment_amount")),
            "bound_at": _dt(updated.get("bound_at")),
        },
    }


@router.get("/dashboard/groups/{group_code}/details")
async def revenue_dashboard_group_details(
    group_code: str,
    start_date: date,
    end_date: date,
    store_id: int,
    financial_year: Optional[int] = Query(None, ge=2000, le=2100),
    financial_month: Optional[int] = Query(None, ge=1, le=12),
    detail_type: str = Query("all", pattern=r"^(all|gross-profit|fees)$"),
    limit: int = Query(2000, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return daily gross profit and settlement-fee rows for one authorized cabinet."""
    require_permission(db, current_user, "revenue.dashboard.view")
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date 不能早于 start_date")

    normalized_group_code = group_code.strip()
    if not normalized_group_code:
        raise HTTPException(status_code=400, detail="柜位编码不能为空")

    try:
        period = _dashboard_financial_period(
            start_date=start_date,
            end_date=end_date,
            financial_year=financial_year,
            financial_month=financial_month,
        )
        scope_row = db.execute(
            text(
                """
                SELECT
                  st.store_id,
                  st.store_code,
                  st.store_name,
                  NULLIF(TRIM(group_mf.mfcode), '') AS group_code,
                  NULLIF(TRIM(group_mf.mfcname), '') AS group_name,
                  NULLIF(TRIM(dept.mfcode), '') AS department_code,
                  NULLIF(TRIM(dept.mfcname), '') AS department_name
                FROM stores st
                LEFT JOIN LATERAL (
                  SELECT mf.mfcode, mf.mfcname, mf.mfpcode
                  FROM manaframe mf
                  WHERE UPPER(TRIM(mf.mfcode)) = UPPER(:group_code)
                  ORDER BY mf.mfcode
                  LIMIT 1
                ) group_mf ON true
                LEFT JOIN manaframe dept
                  ON UPPER(TRIM(dept.mfcode)) = UPPER(TRIM(group_mf.mfpcode))
                WHERE st.store_id = :store_id
                """
            ),
            {"store_id": store_id, "group_code": normalized_group_code},
        ).mappings().first()
        if not scope_row:
            raise HTTPException(status_code=404, detail="门店不存在")

        scope_subject = dict(scope_row)
        scope_subject["group_code"] = scope_subject.get("group_code") or normalized_group_code
        scope = load_business_scope(db, current_user, fallback_resource_code="revenue")
        if not _dashboard_row_allowed(scope, scope_subject):
            raise HTTPException(status_code=403, detail="目标柜位不在当前用户数据权限范围内")

        params = {
            "start_date": start_date,
            "end_date": end_date,
            "store_id": store_id,
            "store_code": str(scope_row.get("store_code") or "").strip(),
            "group_code": normalized_group_code,
            "limit": limit,
        }
        if period.get("period_month_start"):
            params["period_month_start"] = period["period_month_start"]
            params["period_month_end"] = period["period_month_end"]
        gross_profit_daily = []
        if detail_type in {"all", "gross-profit"}:
            source_ctes = _live_revenue_source_ctes(
                "s.sglhsrq BETWEEN :start_date AND :end_date",
                period["fee_filter"],
                period["extra_filter"],
                "AND s.sglmarket = :store_code",
                fee_date_basis="payment",
            )
            gross_profit_daily = db.execute(
                text(
                    f"""
                    WITH {source_ctes}
                    SELECT
                      src.revenue_date,
                      COALESCE(SUM(src.sales_amount), 0)::numeric AS gross_profit_amount,
                      COALESCE(SUM(src.sales_count), 0)::bigint AS source_count
                    FROM source_rows src
                    WHERE src.store_id = :store_id
                      AND UPPER(TRIM(src.source_group_code)) = UPPER(:group_code)
                    GROUP BY src.revenue_date
                    HAVING
                      COALESCE(SUM(src.sales_amount), 0) <> 0
                      OR COALESCE(SUM(src.sales_count), 0) > 0
                    ORDER BY src.revenue_date ASC
                    """
                ),
                params,
            ).mappings().all()

        fee_rows = []
        if detail_type in {"all", "fees"}:
            paid_fee_ctes = _live_fees_cte(
                period["fee_filter"],
                date_basis="payment",
            )
            fee_ctes = (
                f"{_contract_group_bindings_cte()}, "
                f"{paid_fee_ctes}"
            )
            loss_bearing_fee_condition = _loss_bearing_fee_condition("fee")
            fee_rows = db.execute(
                text(
                    f"""
                    WITH {fee_ctes}
                    SELECT
                      fee.id,
                      fee.revenue_date,
                      fee.payment_no AS payment_no,
                      fee.settlement_no AS settlement_no,
                      fee.contract_code,
                      fee.contract_name,
                      fee.fee_type_code,
                      fee.fee_type_name,
                      fee.tax_included_amount,
                      fee.source_tax_excluded_amount,
                      fee.tax_excluded_amount,
                      fee.source_type,
                      COUNT(*) OVER ()::bigint AS total_count,
                      COALESCE(SUM(
                        CASE
                          WHEN month_close.id IS NOT NULL THEN fee.tax_included_amount
                          ELSE fee.tax_excluded_amount
                        END
                      ) OVER (), 0)::numeric AS total_amount
                    FROM live_fees fee
                    LEFT JOIN revenue_month_closes month_close
                      ON month_close.store_id = fee.store_id
                     AND month_close.status = 'CONFIRMED'
                     AND month_close.period_month = CASE
                       WHEN EXTRACT(MONTH FROM fee.revenue_date) = 12 THEN TO_CHAR(fee.revenue_date, 'YYYY-12')
                       WHEN EXTRACT(DAY FROM fee.revenue_date) >= 29 THEN
                         TO_CHAR(fee.revenue_date, 'YYYY-')
                         || LPAD((EXTRACT(MONTH FROM fee.revenue_date)::integer + 1)::text, 2, '0')
                       ELSE TO_CHAR(fee.revenue_date, 'YYYY-MM')
                     END
                     AND {period["close_filter"].replace("close.", "month_close.")}
                    WHERE fee.store_id = :store_id
                      AND UPPER(TRIM(fee.source_group_code)) = UPPER(:group_code)
                      AND NOT ({loss_bearing_fee_condition})
                    ORDER BY fee.revenue_date DESC, fee.id DESC
                    LIMIT :limit
                    """
                ),
                params,
            ).mappings().all()

        adjustment_rows = db.execute(
            text(
                f"""
                SELECT
                  adjustment.id,
                  adjustment.adjustment_category,
                  adjustment.source_subject_code,
                  adjustment.source_subject_name,
                  adjustment.fee_type_code,
                  adjustment.fee_type_name,
                  adjustment.raw_amount,
                  adjustment.accrued_tax_amount,
                  adjustment.adjustment_amount,
                  adjustment.final_amount,
                  adjustment.allocation_basis,
                  adjustment.adjustment_reason
                FROM revenue_month_closes month_close
                JOIN revenue_month_close_adjustments adjustment
                  ON adjustment.month_close_id = month_close.id
                 AND adjustment.target_component = 'FEE'
                 AND adjustment.binding_status = 'BOUND'
                WHERE month_close.store_id = :store_id
                  AND month_close.status = 'CONFIRMED'
                  AND {period["close_filter"].replace("close.", "month_close.")}
                  AND UPPER(TRIM(adjustment.source_group_code)) = UPPER(:group_code)
                ORDER BY adjustment.source_subject_code, adjustment.fee_type_code, adjustment.id
                """
            ),
            params,
        ).mappings().all() if detail_type in {"all", "fees"} else []

        daily_items = [
            {
                "revenue_date": _dt(row.get("revenue_date")),
                "gross_profit_amount": _money(row.get("gross_profit_amount")),
                "source_count": int(row.get("source_count") or 0),
            }
            for row in gross_profit_daily
        ]
        fee_items = [
            {
                "id": str(row.get("id")),
                "revenue_date": _dt(row.get("revenue_date")),
                "payment_no": row.get("payment_no"),
                "settlement_no": row.get("settlement_no"),
                "contract_code": row.get("contract_code"),
                "contract_name": row.get("contract_name"),
                "fee_type_code": row.get("fee_type_code"),
                "fee_type_name": row.get("fee_type_name"),
                "tax_included_amount": _money(row.get("tax_included_amount")),
                "source_tax_excluded_amount": _money(row.get("source_tax_excluded_amount")),
                "tax_excluded_amount": _money(row.get("tax_excluded_amount")),
                "source_type": row.get("source_type"),
            }
            for row in fee_rows
        ]
        fee_total_count = int(fee_rows[0].get("total_count") or 0) if fee_rows else 0
        fee_raw_total_amount = _money(fee_rows[0].get("total_amount")) if fee_rows else 0.0
        fee_adjustment_amount = sum(_money(row.get("adjustment_amount")) for row in adjustment_rows)
        adjustment_items = [
            {
                "id": int(row["id"]),
                "adjustment_category": row.get("adjustment_category"),
                "subject_code": row.get("source_subject_code"),
                "subject_name": row.get("source_subject_name"),
                "fee_type_code": row.get("fee_type_code"),
                "fee_type_name": row.get("fee_type_name"),
                "raw_amount": _money(row.get("raw_amount")),
                "accrued_tax_amount": _money(row.get("accrued_tax_amount")),
                "adjustment_amount": _money(row.get("adjustment_amount")),
                "final_amount": _money(row.get("final_amount")),
                "allocation_basis": row.get("allocation_basis"),
                "adjustment_reason": row.get("adjustment_reason"),
            }
            for row in adjustment_rows
        ]
        return {
            "store": {
                "store_id": int(scope_row["store_id"]),
                "store_code": scope_row.get("store_code"),
                "store_name": scope_row.get("store_name"),
            },
            "department": {
                "department_code": scope_row.get("department_code"),
                "department_name": scope_row.get("department_name") or "未归属部门",
            },
            "group": {
                "group_code": normalized_group_code,
                "group_name": scope_row.get("group_name") or normalized_group_code,
            },
            "start_date": _dt(start_date),
            "end_date": _dt(end_date),
            "gross_profit": {
                "total_amount": sum(item["gross_profit_amount"] for item in daily_items),
                "items": daily_items,
            },
            "fees": {
                "date_basis": "payment_date",
                "total_count": fee_total_count,
                "returned_count": len(fee_items),
                "is_truncated": fee_total_count > len(fee_items),
                "raw_total_amount": fee_raw_total_amount,
                "adjustment_amount": fee_adjustment_amount,
                "total_amount": fee_raw_total_amount + fee_adjustment_amount,
                "month_close_adjustments": adjustment_items,
                "items": fee_items,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "获取柜位收益看板明细失败 store_id=%s group_code=%s start_date=%s end_date=%s",
            store_id,
            normalized_group_code,
            start_date,
            end_date,
        )
        raise HTTPException(
            status_code=500,
            detail="获取柜位收益看板明细失败，请稍后重试",
        ) from exc


@router.get("/dashboard/extra-details")
async def revenue_dashboard_extra_details(
    start_date: date,
    end_date: date,
    store_id: int,
    financial_year: Optional[int] = Query(None, ge=2000, le=2100),
    financial_month: Optional[int] = Query(None, ge=1, le=12),
    source_group_code: Optional[str] = None,
    source_group_name: Optional[str] = None,
    unit_code: Optional[str] = None,
    limit: int = Query(2000, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return NC6051 subject summaries and voucher explanations for one dashboard row."""
    require_permission(db, current_user, "revenue.dashboard.view")
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date 不能早于 start_date")

    normalized_group_code = (source_group_code or "").strip()
    normalized_group_name = (source_group_name or "").strip()
    normalized_unit_code = (unit_code or "").strip()
    if not normalized_group_code and not normalized_group_name:
        raise HTTPException(status_code=400, detail="柜位编码或来源部门名称至少填写一个")

    try:
        period = _dashboard_financial_period(
            start_date=start_date,
            end_date=end_date,
            financial_year=financial_year,
            financial_month=financial_month,
        )
        store_row = db.execute(
            text(
                """
                SELECT store_id, store_code, store_name
                FROM stores
                WHERE store_id = :store_id
                """
            ),
            {"store_id": store_id},
        ).mappings().first()
        if not store_row:
            raise HTTPException(status_code=404, detail="门店不存在")

        params = {
            "start_date": start_date,
            "end_date": end_date,
            "store_id": store_id,
            "source_group_code": normalized_group_code,
            "source_group_name": normalized_group_name,
            "unit_code": normalized_unit_code,
            "limit": limit,
        }
        if period.get("period_month_start"):
            params["period_month_start"] = period["period_month_start"]
            params["period_month_end"] = period["period_month_end"]
        if normalized_group_code:
            row_filter = "AND UPPER(TRIM(extra.source_group_code)) = UPPER(:source_group_code)"
        else:
            row_filter = """
              AND NULLIF(TRIM(extra.source_group_code), '') IS NULL
              AND TRIM(extra.source_group_name) = :source_group_name
            """
        if normalized_unit_code:
            row_filter += " AND TRIM(extra.unit_code) = :unit_code"
        row_filter = "AND extra.store_id = :store_id " + row_filter
        common_ctes = _nc_6051_extra_detail_ctes(
            row_filter,
            date_filter_sql=period["extra_filter"],
        )

        metadata = db.execute(
            text(
                f"""
                WITH {common_ctes}
                SELECT
                  MIN(NULLIF(TRIM(source_department_code), '')) AS department_code,
                  MIN(NULLIF(TRIM(source_department_name), '')) AS department_name,
                  MIN(NULLIF(TRIM(source_group_code), '')) AS group_code,
                  MIN(NULLIF(TRIM(source_group_name), '')) AS group_name,
                  MIN(NULLIF(TRIM(unit_code), '')) AS unit_code
                FROM filtered_extras
                """
            ),
            params,
        ).mappings().first()

        scope_subject = {
            "store_id": int(store_row["store_id"]),
            "department_code": metadata.get("department_code") if metadata else None,
            "department_name": (
                metadata.get("department_name") if metadata else normalized_group_name
            ),
            "group_code": (
                metadata.get("group_code") if metadata else normalized_group_code or None
            ),
        }
        scope = load_business_scope(db, current_user, fallback_resource_code="revenue")
        if not _dashboard_row_allowed(scope, scope_subject):
            raise HTTPException(status_code=403, detail="目标其他收益不在当前用户数据权限范围内")

        subject_rows = db.execute(
            text(
                f"""
                WITH {common_ctes}
                SELECT
                  COALESCE(NULLIF(TRIM(source_subject_code), ''), '未编码') AS subject_code,
                  source_subject_name AS subject_name,
                  COUNT(*)::bigint AS detail_count,
                  COALESCE(SUM(amount), 0)::numeric AS amount
                FROM filtered_extras
                GROUP BY
                  COALESCE(NULLIF(TRIM(source_subject_code), ''), '未编码'),
                  source_subject_name
                ORDER BY ABS(COALESCE(SUM(amount), 0)) DESC, subject_code
                """
            ),
            params,
        ).mappings().all()

        detail_rows = db.execute(
            text(
                f"""
                WITH {common_ctes}
                SELECT
                  id,
                  revenue_date,
                  source_subject_code,
                  source_subject_name,
                  extra_type,
                  source_department_code,
                  source_department_name,
                  source_explanation,
                  voucher_no,
                  amount,
                  source_detail_key,
                  source_group_code,
                  source_group_name,
                  unit_code,
                  match_method,
                  match_status,
                  match_reason,
                  COUNT(*) OVER ()::bigint AS total_count,
                  COALESCE(SUM(amount) OVER (), 0)::numeric AS total_amount
                FROM filtered_extras
                ORDER BY revenue_date DESC, ABS(amount) DESC, id DESC
                LIMIT :limit
                """
            ),
            params,
        ).mappings().all()

        if normalized_group_code:
            adjustment_filter = (
                "AND UPPER(TRIM(adjustment.source_group_code)) = UPPER(:source_group_code)"
            )
        else:
            adjustment_filter = """
              AND NULLIF(TRIM(adjustment.source_group_code), '') IS NULL
              AND (
                TRIM(adjustment.source_group_name) = :source_group_name
                OR TRIM(adjustment.source_department_name) = :source_group_name
              )
            """
        extra_adjustment_rows = db.execute(
            text(
                f"""
                SELECT
                  adjustment.id,
                  adjustment.adjustment_category,
                  adjustment.source_subject_code,
                  adjustment.source_subject_name,
                  adjustment.raw_amount,
                  adjustment.accrued_tax_amount,
                  adjustment.adjustment_amount,
                  adjustment.final_amount,
                  adjustment.allocation_basis,
                  adjustment.adjustment_reason
                FROM revenue_month_closes month_close
                JOIN revenue_month_close_adjustments adjustment
                  ON adjustment.month_close_id = month_close.id
                 AND adjustment.target_component = 'EXTRA'
                 AND adjustment.binding_status = 'BOUND'
                WHERE month_close.store_id = :store_id
                  AND month_close.status = 'CONFIRMED'
                  AND {period["close_filter"].replace("close.", "month_close.")}
                  {adjustment_filter}
                ORDER BY adjustment.source_subject_code, adjustment.id
                """
            ),
            params,
        ).mappings().all()

        subject_items = [
            {
                "subject_code": row.get("subject_code"),
                "subject_name": row.get("subject_name"),
                "detail_count": int(row.get("detail_count") or 0),
                "amount": _money(row.get("amount")),
            }
            for row in subject_rows
        ]
        detail_items = [
            {
                "id": str(row.get("id")),
                "revenue_date": _dt(row.get("revenue_date")),
                "subject_code": row.get("source_subject_code"),
                "subject_name": row.get("source_subject_name"),
                "extra_type": row.get("extra_type"),
                "department_code": row.get("source_department_code"),
                "department_name": row.get("source_department_name"),
                "explanation": row.get("source_explanation"),
                "voucher_no": row.get("voucher_no"),
                "amount": _money(row.get("amount")),
                "source_detail_key": row.get("source_detail_key"),
                "source_group_code": row.get("source_group_code"),
                "source_group_name": row.get("source_group_name"),
                "unit_code": row.get("unit_code"),
                "match_method": row.get("match_method"),
                "match_status": row.get("match_status"),
                "match_reason": row.get("match_reason"),
            }
            for row in detail_rows
        ]
        total_count = int(detail_rows[0].get("total_count") or 0) if detail_rows else 0
        raw_total_amount = _money(detail_rows[0].get("total_amount")) if detail_rows else 0.0
        adjustment_amount = sum(
            _money(row.get("adjustment_amount")) for row in extra_adjustment_rows
        )
        adjustment_items = [
            {
                "id": int(row["id"]),
                "adjustment_category": row.get("adjustment_category"),
                "subject_code": row.get("source_subject_code"),
                "subject_name": row.get("source_subject_name"),
                "raw_amount": _money(row.get("raw_amount")),
                "accrued_tax_amount": _money(row.get("accrued_tax_amount")),
                "adjustment_amount": _money(row.get("adjustment_amount")),
                "final_amount": _money(row.get("final_amount")),
                "allocation_basis": row.get("allocation_basis"),
                "adjustment_reason": row.get("adjustment_reason"),
            }
            for row in extra_adjustment_rows
        ]
        return {
            "store": {
                "store_id": int(store_row["store_id"]),
                "store_code": store_row.get("store_code"),
                "store_name": store_row.get("store_name"),
            },
            "target": {
                "department_code": metadata.get("department_code") if metadata else None,
                "department_name": metadata.get("department_name") if metadata else normalized_group_name,
                "group_code": metadata.get("group_code") if metadata else normalized_group_code or None,
                "group_name": metadata.get("group_name") if metadata else normalized_group_name,
                "unit_code": metadata.get("unit_code") if metadata else normalized_unit_code or None,
            },
            "start_date": _dt(start_date),
            "end_date": _dt(end_date),
            "date_basis": period["date_basis"],
            "total_count": total_count,
            "returned_count": len(detail_items),
            "is_truncated": total_count > len(detail_items),
            "raw_total_amount": raw_total_amount,
            "adjustment_amount": adjustment_amount,
            "total_amount": raw_total_amount + adjustment_amount,
            "month_close_adjustments": adjustment_items,
            "subjects": subject_items,
            "items": detail_items,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "获取其他收益科目摘要明细失败 store_id=%s group_code=%s group_name=%s start_date=%s end_date=%s",
            store_id,
            normalized_group_code,
            normalized_group_name,
            start_date,
            end_date,
        )
        raise HTTPException(
            status_code=500,
            detail="获取其他收益科目摘要明细失败，请稍后重试",
        ) from exc


@router.get("/dashboard/extra-export-details")
async def revenue_dashboard_extra_export_details(
    start_date: date,
    end_date: date,
    financial_year: Optional[int] = Query(None, ge=2000, le=2100),
    financial_month: Optional[int] = Query(None, ge=1, le=12),
    limit: int = Query(20000, ge=1, le=50000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return permission-scoped NC6051 rows for the revenue dashboard workbook."""
    require_permission(db, current_user, "revenue.dashboard.view")
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date 不能早于 start_date")

    try:
        period = _dashboard_financial_period(
            start_date=start_date,
            end_date=end_date,
            financial_year=financial_year,
            financial_month=financial_month,
        )
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "scan_limit": 50001,
        }
        if period.get("period_month_start"):
            params["period_month_start"] = period["period_month_start"]
            params["period_month_end"] = period["period_month_end"]
        common_ctes = _nc_6051_extra_detail_ctes(date_filter_sql=period["extra_filter"])
        rows = db.execute(
            text(
                f"""
                WITH {common_ctes}
                SELECT
                  extra.id,
                  extra.store_id,
                  st.store_code,
                  st.store_name,
                  extra.revenue_date,
                  extra.source_subject_code,
                  extra.source_subject_name,
                  extra.extra_type,
                  extra.source_department_code,
                  extra.source_department_name,
                  extra.source_explanation,
                  extra.voucher_no,
                  extra.amount,
                  extra.source_detail_key,
                  extra.source_group_code,
                  extra.source_group_name,
                  extra.unit_code,
                  extra.match_method,
                  extra.match_status,
                  extra.match_reason
                FROM filtered_extras extra
                JOIN stores st ON st.store_id = extra.store_id
                ORDER BY
                  st.store_code,
                  extra.source_department_code,
                  extra.source_subject_code,
                  extra.revenue_date,
                  extra.voucher_no,
                  extra.id
                LIMIT :scan_limit
                """
            ),
            params,
        ).mappings().all()

        scope = load_business_scope(db, current_user, fallback_resource_code="revenue")
        allowed_rows = [
            dict(row)
            for row in rows
            if _dashboard_row_allowed(
                scope,
                {
                    "store_id": row.get("store_id"),
                    "department_code": row.get("source_department_code"),
                    "department_name": row.get("source_department_name"),
                    "group_code": row.get("source_group_code"),
                },
            )
        ]
        returned_rows = allowed_rows[:limit]
        items = [
            {
                "id": str(row.get("id")),
                "store_id": int(row.get("store_id")),
                "store_code": row.get("store_code"),
                "store_name": row.get("store_name"),
                "revenue_date": _dt(row.get("revenue_date")),
                "subject_code": row.get("source_subject_code"),
                "subject_name": row.get("source_subject_name"),
                "extra_type": row.get("extra_type"),
                "department_code": row.get("source_department_code"),
                "department_name": row.get("source_department_name"),
                "explanation": row.get("source_explanation"),
                "voucher_no": row.get("voucher_no"),
                "amount": _money(row.get("amount")),
                "source_detail_key": row.get("source_detail_key"),
                "source_group_code": row.get("source_group_code"),
                "source_group_name": row.get("source_group_name"),
                "unit_code": row.get("unit_code"),
                "match_method": row.get("match_method"),
                "match_status": row.get("match_status"),
                "match_reason": row.get("match_reason"),
            }
            for row in returned_rows
        ]
        return {
            "start_date": _dt(start_date),
            "end_date": _dt(end_date),
            "permission_scoped": True,
            "total_count": len(allowed_rows),
            "returned_count": len(items),
            "is_truncated": len(rows) >= params["scan_limit"] or len(allowed_rows) > len(items),
            "items": items,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "获取收益看板其他收益导出明细失败 start_date=%s end_date=%s",
            start_date,
            end_date,
        )
        raise HTTPException(
            status_code=500,
            detail="获取收益看板其他收益导出明细失败，请稍后重试",
        ) from exc


@router.get("/monthly")
async def monthly_revenue(
    revenue_month: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}$"),
    revenue_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    financial_year: Optional[int] = Query(None, ge=2000, le=2100),
    financial_month: Optional[int] = Query(None, ge=1, le=12),
    store_id: Optional[int] = None,
    floor_id: Optional[int] = None,
    metric: str = Query("total", regex=r"^(total|sales|fee|extra)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "revenue.view")
    if not (start_date and end_date) and not revenue_date and not revenue_month:
        raise HTTPException(status_code=400, detail="请传 start_date/end_date、revenue_date 或 revenue_month")
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date 不能早于 start_date")
    try:
        params: dict = {}
        result_filters: list[str] = []
        if start_date and end_date:
            params["start_date"] = start_date
            params["end_date"] = end_date
            sales_date_filter = "s.sglhsrq BETWEEN :start_date AND :end_date"
            fee_date_filter = "fee.revenue_date BETWEEN :start_date AND :end_date"
            period = _dashboard_financial_period(
                start_date=start_date,
                end_date=end_date,
                financial_year=financial_year,
                financial_month=financial_month,
            )
            extra_date_filter = period["extra_filter"]
            if period.get("period_month_start"):
                params["period_month_start"] = period["period_month_start"]
                params["period_month_end"] = period["period_month_end"]
            # The store-level unmatched-sales check repeats the live-sales
            # resolution work after the main aggregation. A full-year range
            # currently completes in about 35 seconds on production data, so
            # keep a transaction-local allowance for multi-month requests
            # while preserving the global 30-second limit for normal months.
            if period["period_count"] > 1:
                db.execute(
                    text(
                        "SET LOCAL statement_timeout = "
                        f"'{REVENUE_MONTHLY_QUERY_TIMEOUT_SECONDS}s'"
                    ),
                    {},
                )
            effective_month = _month_from_date(start_date)
        elif revenue_date:
            params["revenue_date"] = revenue_date
            sales_date_filter = "s.sglhsrq = :revenue_date"
            fee_date_filter = "fee.revenue_date = :revenue_date"
            extra_date_filter = "extra.revenue_date = :revenue_date"
            effective_month = _month_from_date(revenue_date)
        else:
            params["revenue_month"] = revenue_month
            sales_date_filter = (
                "s.sglhsrq >= to_date(:revenue_month || '-01', 'YYYY-MM-DD') "
                "AND s.sglhsrq < to_date(:revenue_month || '-01', 'YYYY-MM-DD') + INTERVAL '1 month'"
            )
            fee_date_filter = "fee.revenue_month = :revenue_month"
            extra_date_filter = "extra.revenue_month = :revenue_month"
            effective_month = revenue_month
        sales_store_filter = ""
        if store_id is not None:
            params["store_id"] = store_id
            store_row = db.execute(
                text("SELECT store_code FROM stores WHERE store_id = :store_id"),
                {"store_id": store_id},
            ).fetchone()
            store_code = str(store_row.store_code).strip() if store_row and store_row.store_code is not None else ""
            params["store_code"] = store_code
            sales_store_filter = "AND s.sglmarket = :store_code"
            result_filters.append("src.store_id = :store_id")
        if floor_id is not None:
            result_filters.append("src.floor_id = :floor_id")
            params["floor_id"] = floor_id

        source_ctes = _live_revenue_source_ctes(
            sales_date_filter,
            fee_date_filter,
            extra_date_filter,
            sales_store_filter,
        )
        source_relation = "source_rows"
        overlay_ctes = ""
        if start_date and end_date and financial_year is not None:
            overlay_ctes = f",\n{_revenue_month_close_overlay_ctes(period['close_filter'])}"
            source_relation = "dashboard_source_rows"
        sql = f"""
            WITH {source_ctes}{overlay_ctes}
            SELECT
              src.unit_id,
              src.unit_code,
              src.store_id,
              src.floor_id,
              bu.status AS unit_status,
              STRING_AGG(
                DISTINCT NULLIF(TRIM(src.source_group_name), ''),
                '、'
                ORDER BY NULLIF(TRIM(src.source_group_name), '')
              ) AS source_group_names,
              STRING_AGG(
                DISTINCT NULLIF(TRIM(src.source_group_code), ''),
                '、'
                ORDER BY NULLIF(TRIM(src.source_group_code), '')
              ) AS source_group_codes,
              COALESCE(SUM(src.sales_amount), 0)::numeric AS sales_gross_profit_amount,
              COALESCE(SUM(src.fee_amount), 0)::numeric AS fee_amount,
              COALESCE(SUM(src.extra_amount), 0)::numeric AS extra_amount,
              COALESCE(SUM(src.sales_amount + src.fee_amount + src.extra_amount), 0)::numeric AS total_amount,
              COALESCE(SUM(src.sales_count), 0)::bigint AS sales_detail_count,
              COALESCE(SUM(src.fee_count), 0)::bigint AS fee_detail_count,
              COALESCE(SUM(src.extra_count), 0)::bigint AS extra_detail_count
            FROM {source_relation} src
            JOIN business_units bu ON bu.id = src.unit_id
            WHERE {" AND ".join(result_filters) if result_filters else "TRUE"}
            GROUP BY src.unit_id, src.unit_code, src.store_id, src.floor_id, bu.status
            ORDER BY total_amount DESC, src.unit_code ASC
        """
        rows = db.execute(text(sql), params).fetchall()
        metric_key = {
            "total": "total_amount",
            "sales": "sales_gross_profit_amount",
            "fee": "fee_amount",
            "extra": "extra_amount",
        }[metric]
        items = []
        for row in rows:
            item = {
                "unit_id": row.unit_id,
                "unit_code": row.unit_code,
                "store_id": row.store_id,
                "floor_id": row.floor_id,
                "unit_status": row.unit_status,
                "source_group_names": row.source_group_names,
                "source_group_codes": row.source_group_codes,
                "sales_gross_profit_amount": _money(row.sales_gross_profit_amount),
                "fee_amount": _money(row.fee_amount),
                "extra_amount": _money(row.extra_amount),
                "total_amount": _money(row.total_amount),
                "sales_detail_count": int(row.sales_detail_count or 0),
                "fee_detail_count": int(row.fee_detail_count or 0),
                "extra_detail_count": int(row.extra_detail_count or 0),
            }
            item["metric_amount"] = item[metric_key]
            items.append(item)

        unmatched_sales_ctes = _unmatched_sales_ctes(sales_date_filter, sales_store_filter)
        unmatched = db.execute(
            text(
                f"""
                WITH {unmatched_sales_ctes}
                SELECT
                  COUNT(*)::bigint AS item_count,
                  COALESCE(SUM(gross_profit_amount), 0)::numeric AS amount
                FROM unmatched_sales
                """
            ),
            params,
        ).fetchone()
        return {
            "revenue_month": effective_month,
            "revenue_date": _dt(revenue_date) if revenue_date else None,
            "start_date": _dt(start_date) if start_date else (_dt(revenue_date) if revenue_date else None),
            "end_date": _dt(end_date) if end_date else (_dt(revenue_date) if revenue_date else None),
            "metric": metric,
            "items": items,
            "unmatched": {
                "item_count": int(unmatched.item_count or 0) if unmatched else 0,
                "amount": _money(unmatched.amount) if unmatched else 0.0,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "获取收益汇总失败 store_id=%s floor_id=%s start_date=%s end_date=%s revenue_date=%s revenue_month=%s",
            store_id,
            floor_id,
            start_date,
            end_date,
            revenue_date,
            revenue_month,
        )
        raise HTTPException(
            status_code=500,
            detail="获取收益汇总失败，请稍后重试",
        ) from exc


@router.get("/unmatched-details")
async def unmatched_revenue_details(
    start_date: date,
    end_date: date,
    store_id: int,
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "revenue.view")
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date 不能早于 start_date")

    try:
        store_row = db.execute(
            text(
                """
                SELECT store_id, store_code, store_name
                FROM stores
                WHERE store_id = :store_id
                """
            ),
            {"store_id": store_id},
        ).fetchone()
        if not store_row:
            raise HTTPException(status_code=404, detail="门店不存在")

        store_code = str(store_row.store_code or "").strip()
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "store_code": store_code,
            "limit": limit,
        }
        unmatched_sales_ctes = _unmatched_sales_ctes(
            "s.sglhsrq BETWEEN :start_date AND :end_date",
            "AND s.sglmarket = :store_code",
        )
        rows = db.execute(
            text(
                f"""
                WITH {unmatched_sales_ctes}
                SELECT
                  revenue_date,
                  store_code,
                  source_group_code,
                  source_supplier_code,
                  source_operation_mode,
                  source_group_name,
                  sales_qty,
                  sales_amount,
                  gross_profit_amount,
                  source_count,
                  first_bill_no,
                  contract_codes,
                  reason_code,
                  COUNT(*) OVER ()::bigint AS total_count,
                  COALESCE(SUM(gross_profit_amount) OVER (), 0)::numeric AS total_amount
                FROM unmatched_sales
                ORDER BY
                  ABS(gross_profit_amount) DESC,
                  revenue_date DESC,
                  source_group_code ASC
                LIMIT :limit
                """
            ),
            params,
        ).fetchall()

        reason_labels = {
            "GROUP_MASTER_NOT_FOUND": "ERP柜组主档不存在",
            "GROUP_MASTER_INACTIVE": "ERP柜组主档已停用",
            "NO_EFFECTIVE_CONTRACT": "销售日无有效合同",
            "NO_UNIT_BINDING": "有效合同未绑定柜位",
            "MATCHING_RULE_GAP": "匹配规则异常，需核查",
        }
        total_count = int(rows[0].total_count or 0) if rows else 0
        total_amount = _money(rows[0].total_amount) if rows else 0.0
        items = [
            {
                "revenue_date": _dt(row.revenue_date),
                "store_code": row.store_code,
                "source_group_code": row.source_group_code,
                "source_supplier_code": row.source_supplier_code,
                "source_operation_mode": row.source_operation_mode,
                "source_group_name": row.source_group_name,
                "sales_qty": _money(row.sales_qty),
                "sales_amount": _money(row.sales_amount),
                "gross_profit_amount": _money(row.gross_profit_amount),
                "source_count": int(row.source_count or 0),
                "first_bill_no": row.first_bill_no,
                "contract_codes": [
                    str(contract_code).strip()
                    for contract_code in (row.contract_codes or [])
                    if str(contract_code).strip()
                ],
                "reason_code": row.reason_code,
                "reason": reason_labels.get(row.reason_code, "未匹配到具体柜位"),
            }
            for row in rows
        ]
        return {
            "store": {
                "store_id": int(store_row.store_id),
                "store_code": store_code,
                "store_name": store_row.store_name,
            },
            "start_date": _dt(start_date),
            "end_date": _dt(end_date),
            "granularity": "按收益日期、来源柜组、供应商和经营方式汇总",
            "scope_note": "未匹配记录尚未归属具体柜位和楼层，因此按当前门店统计。",
            "total": {
                "item_count": total_count,
                "amount": total_amount,
            },
            "returned_count": len(items),
            "is_truncated": total_count > len(items),
            "items": items,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "获取未匹配收益明细失败 store_id=%s start_date=%s end_date=%s",
            store_id,
            start_date,
            end_date,
        )
        raise HTTPException(
            status_code=500,
            detail="获取未匹配收益明细失败，请稍后重试",
        ) from exc


@router.get("/units/{unit_id}/detail")
async def unit_revenue_detail(
    unit_id: int,
    revenue_month: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    financial_year: Optional[int] = Query(None, ge=2000, le=2100),
    financial_month: Optional[int] = Query(None, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "revenue.view")
    if revenue_month:
        params: dict = {"unit_id": unit_id, "revenue_month": revenue_month}
        sales_date_filter = (
            "s.sglhsrq >= to_date(:revenue_month || '-01', 'YYYY-MM-DD') "
            "AND s.sglhsrq < to_date(:revenue_month || '-01', 'YYYY-MM-DD') + INTERVAL '1 month'"
        )
        fee_date_filter = "fee.revenue_month = :revenue_month"
        extra_date_filter = "extra.revenue_month = :revenue_month"
    elif start_date and end_date:
        params = {"unit_id": unit_id, "start_date": start_date, "end_date": end_date}
        sales_date_filter = "s.sglhsrq BETWEEN :start_date AND :end_date"
        fee_date_filter = "fee.revenue_date BETWEEN :start_date AND :end_date"
        period = _dashboard_financial_period(
            start_date=start_date,
            end_date=end_date,
            financial_year=financial_year,
            financial_month=financial_month,
        )
        extra_date_filter = period["extra_filter"]
        if period.get("period_month_start"):
            params["period_month_start"] = period["period_month_start"]
            params["period_month_end"] = period["period_month_end"]
    else:
        raise HTTPException(status_code=400, detail="请传 revenue_month 或 start_date/end_date")

    try:
        unit = db.execute(
            text(
                """
                SELECT bu.id, bu.floor_id, bu.unit_code, bu.status, st.store_id, st.store_code
                FROM business_units bu
                JOIN floors floor ON floor.id = bu.floor_id
                LEFT JOIN stores st ON TRIM(st.store_code) = TRIM(floor.store_code)
                WHERE bu.id = :unit_id
                """
            ),
            {"unit_id": unit_id},
        ).fetchone()
        if not unit:
            raise HTTPException(status_code=404, detail="经营单元不存在")

        params["store_code"] = str(unit.store_code or "").strip()
        sales_store_filter = "AND s.sglmarket = :store_code"
        source_ctes = _live_revenue_source_ctes(
            sales_date_filter,
            fee_date_filter,
            extra_date_filter,
            sales_store_filter,
        )
        source_relation = "source_rows"
        overlay_ctes = ""
        if start_date and end_date and financial_year is not None:
            overlay_ctes = f",\n{_revenue_month_close_overlay_ctes(period['close_filter'])}"
            source_relation = "dashboard_source_rows"

        daily = db.execute(
            text(
                f"""
                WITH {source_ctes}{overlay_ctes}
                SELECT
                  src.revenue_date,
                  to_char(src.revenue_date, 'YYYY-MM') AS revenue_month,
                  COALESCE(SUM(src.sales_amount), 0)::numeric AS sales_gross_profit_amount,
                  COALESCE(SUM(src.fee_amount), 0)::numeric AS fee_amount,
                  COALESCE(SUM(src.extra_amount), 0)::numeric AS extra_amount,
                  COALESCE(SUM(src.sales_amount + src.fee_amount + src.extra_amount), 0)::numeric AS total_amount,
                  COALESCE(SUM(src.sales_count), 0)::bigint AS sales_detail_count,
                  COALESCE(SUM(src.fee_count), 0)::bigint AS fee_detail_count,
                  COALESCE(SUM(src.extra_count), 0)::bigint AS extra_detail_count
                FROM {source_relation} src
                WHERE src.unit_id = :unit_id
                GROUP BY src.revenue_date
                ORDER BY src.revenue_date ASC
                """
            ),
            params,
        ).fetchall()
        live_sales_ctes = _live_sales_ctes(sales_date_filter, sales_store_filter)
        sales = db.execute(
            text(
                f"""
                WITH {live_sales_ctes}
                SELECT
                  md5(
                    live_sales.revenue_date::text || '|' ||
                    live_sales.store_id::text || '|' ||
                    live_sales.source_group_code || '|' ||
                    COALESCE(live_sales.source_supplier_code, '') || '|' ||
                    COALESCE(live_sales.source_operation_mode, '') || '|' ||
                    live_sales.unit_id::text
                  ) AS id,
                  live_sales.revenue_date,
                  to_char(live_sales.revenue_date, 'YYYY-MM') AS revenue_month,
                  live_sales.source_group_code,
                  live_sales.source_group_name,
                  live_sales.operation_mode,
                  live_sales.supplier_code,
                  live_sales.supplier_name,
                  live_sales.contract_code,
                  live_sales.sales_qty,
                  live_sales.sales_amount AS tax_excluded_sales_amount,
                  live_sales.gross_profit_amount AS tax_excluded_profit_amount,
                  live_sales.first_bill_no AS source_doc_no,
                  'LIVE_SALEGOODSLIST'::varchar AS etl_batch_id
                FROM live_sales
                WHERE live_sales.unit_id = :unit_id
                ORDER BY live_sales.revenue_date DESC, live_sales.source_group_code ASC
                LIMIT 500
                """
            ),
            params,
        ).fetchall()
        fee_ctes = f"{_contract_group_bindings_cte()}, {_live_fees_cte(fee_date_filter)}"
        loss_bearing_fee_condition = _loss_bearing_fee_condition("fee")
        fees = db.execute(
            text(
                f"""
                WITH {fee_ctes}
                SELECT id, revenue_date, revenue_month, source_group_code, source_group_name,
                       contract_code, contract_name, fee_type_code, fee_type_name,
                       tax_included_amount, source_tax_excluded_amount, tax_excluded_amount,
                       source_type, source_doc_no, etl_batch_id
                FROM live_fees fee
                WHERE fee.unit_id = :unit_id
                  AND {fee_date_filter}
                  AND NOT ({loss_bearing_fee_condition})
                ORDER BY revenue_date DESC, id DESC
                LIMIT 500
                """
            ),
            params,
        ).fetchall()
        loss_bearing_fees = db.execute(
            text(
                f"""
                WITH {fee_ctes}
                SELECT id, revenue_date, revenue_month, source_group_code, source_group_name,
                       contract_code, contract_name, fee_type_code, fee_type_name,
                       tax_included_amount, source_tax_excluded_amount, tax_excluded_amount,
                       source_type, source_doc_no, etl_batch_id
                FROM live_fees fee
                WHERE fee.unit_id = :unit_id
                  AND {fee_date_filter}
                  AND {loss_bearing_fee_condition}
                ORDER BY revenue_date DESC, id DESC
                LIMIT 500
                """
            ),
            params,
        ).fetchall()
        extras = db.execute(
            text(
                f"""
                SELECT *
                FROM revenue_extra_receipts extra
                WHERE extra.unit_id = :unit_id
                  AND extra.source_type = 'NC6051'
                  AND {extra_date_filter}
                ORDER BY revenue_date DESC, id DESC
                LIMIT 500
                """
            ),
            params,
        ).fetchall()
        month_close_extra_details = []
        if start_date and end_date and financial_year is not None:
            month_close_extra_details = db.execute(
                text(
                    f"""
                    SELECT
                      adjustment.id,
                      close.period_end_date AS revenue_date,
                      close.period_month AS revenue_month,
                      adjustment.source_subject_code,
                      adjustment.source_subject_name,
                      adjustment.source_group_code,
                      adjustment.source_group_name,
                      adjustment.adjustment_amount AS amount,
                      adjustment.adjustment_reason,
                      adjustment.raw_payload ->> 'manual_binding_source_bill_no'
                        AS source_bill_no,
                      adjustment.raw_payload ->> 'manual_binding_source_voucher_id'
                        AS source_voucher_id
                    FROM revenue_month_closes close
                    JOIN revenue_month_close_adjustments adjustment
                      ON adjustment.month_close_id = close.id
                    WHERE close.status = 'CONFIRMED'
                      AND {period["close_filter"]}
                      AND adjustment.unit_id = :unit_id
                      AND adjustment.target_component = 'EXTRA'
                      AND adjustment.binding_status = 'BOUND'
                      AND adjustment.adjustment_amount <> 0
                    ORDER BY close.period_end_date DESC, adjustment.id DESC
                    """
                ),
                params,
            ).mappings().all()

        return {
            "unit": {
                "id": int(unit.id),
                "floor_id": int(unit.floor_id),
                "unit_code": unit.unit_code,
                "status": unit.status,
            },
            "daily_summary": [
                {
                    "revenue_date": _dt(row.revenue_date),
                    "revenue_month": row.revenue_month,
                    "sales_gross_profit_amount": _money(row.sales_gross_profit_amount),
                    "fee_amount": _money(row.fee_amount),
                    "extra_amount": _money(row.extra_amount),
                    "total_amount": _money(row.total_amount),
                    "sales_detail_count": int(row.sales_detail_count or 0),
                    "fee_detail_count": int(row.fee_detail_count or 0),
                    "extra_detail_count": int(row.extra_detail_count or 0),
                }
                for row in daily
            ],
            "sales_details": [
                {
                    "id": str(row.id),
                    "revenue_date": _dt(row.revenue_date),
                    "revenue_month": row.revenue_month,
                    "source_group_code": row.source_group_code,
                    "source_group_name": row.source_group_name,
                    "operation_mode": row.operation_mode,
                    "supplier_code": row.supplier_code,
                    "supplier_name": row.supplier_name,
                    "contract_code": row.contract_code,
                    "sales_qty": _money(row.sales_qty),
                    "tax_excluded_sales_amount": _money(row.tax_excluded_sales_amount),
                    "tax_excluded_profit_amount": _money(row.tax_excluded_profit_amount),
                    "source_doc_no": row.source_doc_no,
                    "etl_batch_id": row.etl_batch_id,
                }
                for row in sales
            ],
            "fee_details": [
                {
                    "id": str(row.id),
                    "revenue_date": _dt(row.revenue_date),
                    "revenue_month": row.revenue_month,
                    "source_group_code": row.source_group_code,
                    "source_group_name": row.source_group_name,
                    "contract_code": row.contract_code,
                    "contract_name": row.contract_name,
                    "fee_type_code": row.fee_type_code,
                    "fee_type_name": row.fee_type_name,
                    "tax_included_amount": _money(row.tax_included_amount),
                    "source_tax_excluded_amount": _money(
                        row.source_tax_excluded_amount
                    ),
                    "tax_excluded_amount": _money(row.tax_excluded_amount),
                    "source_type": row.source_type,
                    "source_doc_no": row.source_doc_no,
                    "etl_batch_id": row.etl_batch_id,
                }
                for row in fees
            ],
            "loss_bearing_details": [
                {
                    "id": str(row.id),
                    "revenue_date": _dt(row.revenue_date),
                    "revenue_month": row.revenue_month,
                    "source_group_code": row.source_group_code,
                    "source_group_name": row.source_group_name,
                    "contract_code": row.contract_code,
                    "contract_name": row.contract_name,
                    "fee_type_code": row.fee_type_code,
                    "fee_type_name": row.fee_type_name,
                    "tax_included_amount": _money(row.tax_included_amount),
                    "source_tax_excluded_amount": _money(
                        row.source_tax_excluded_amount
                    ),
                    "tax_excluded_amount": _money(row.tax_excluded_amount),
                    "source_type": row.source_type,
                    "source_doc_no": row.source_doc_no,
                    "etl_batch_id": row.etl_batch_id,
                }
                for row in loss_bearing_fees
            ],
            "extra_receipts": [_receipt_to_dict(row) for row in extras],
            "month_close_extra_details": [
                {
                    "id": int(row["id"]),
                    "revenue_date": _dt(row.get("revenue_date")),
                    "revenue_month": row.get("revenue_month"),
                    "source_subject_code": row.get("source_subject_code"),
                    "source_subject_name": row.get("source_subject_name"),
                    "source_group_code": row.get("source_group_code"),
                    "source_group_name": row.get("source_group_name"),
                    "amount": _money(row.get("amount")),
                    "adjustment_reason": row.get("adjustment_reason"),
                    "source_bill_no": row.get("source_bill_no"),
                    "source_voucher_id": row.get("source_voucher_id"),
                    "source_type": "MONTH_CLOSE_BINDING",
                    "match_status": "MATCHED",
                }
                for row in month_close_extra_details
            ],
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"获取柜位收益详情失败: {exc}")


@router.get("/extra-receipts")
async def list_extra_receipts(
    revenue_month: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}$"),
    revenue_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    financial_year: Optional[int] = Query(None, ge=2000, le=2100),
    financial_month: Optional[int] = Query(None, ge=1, le=12),
    store_id: Optional[int] = None,
    floor_id: Optional[int] = None,
    unit_id: Optional[int] = None,
    status_value: Optional[str] = Query(None, alias="status"),
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "revenue.view")
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date 不能早于 start_date")
    params: dict = {}
    filters: list[str] = ["source_type = 'NC6051'"]
    if start_date and end_date:
        params["start_date"] = start_date
        params["end_date"] = end_date
        period = _dashboard_financial_period(
            start_date=start_date,
            end_date=end_date,
            financial_year=financial_year,
            financial_month=financial_month,
        )
        filters.append(period["extra_filter"])
        if period.get("period_month_start"):
            params["period_month_start"] = period["period_month_start"]
            params["period_month_end"] = period["period_month_end"]
    elif revenue_date:
        filters.append("revenue_date = :revenue_date")
        params["revenue_date"] = revenue_date
    elif revenue_month:
        filters.append("revenue_month = :revenue_month")
        params["revenue_month"] = revenue_month
    if store_id is not None:
        filters.append("store_id = :store_id")
        params["store_id"] = store_id
    if floor_id is not None:
        filters.append("floor_id = :floor_id")
        params["floor_id"] = floor_id
    if unit_id is not None:
        filters.append("unit_id = :unit_id")
        params["unit_id"] = unit_id
    if status_value:
        filters.append("status = :status")
        params["status"] = status_value
    if keyword:
        filters.append(
            "(unit_code ILIKE :kw OR supplier_name ILIKE :kw OR contract_code ILIKE :kw OR remark ILIKE :kw)"
        )
        params["kw"] = f"%{keyword.strip()}%"
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    rows = db.execute(
        text(f"SELECT * FROM revenue_extra_receipts extra {where} ORDER BY revenue_date DESC, id DESC LIMIT 500"),
        params,
    ).fetchall()
    return [_receipt_to_dict(row) for row in rows]


@router.post("/extra-receipts", status_code=status.HTTP_201_CREATED)
async def create_extra_receipt(
    body: RevenueExtraReceiptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "revenue.extra.create")
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="手工补收已停用；电表、物业、营运收费由 NC6051 自动同步",
    )


@router.put("/extra-receipts/{receipt_id}")
async def update_extra_receipt(
    receipt_id: int,
    body: RevenueExtraReceiptUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "revenue.extra.edit")
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="NC6051 自动收费不允许手工修改，请修正来源或柜位绑定后重新同步",
    )


@router.post("/extra-receipts/{receipt_id}/confirm")
async def confirm_extra_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "revenue.extra.confirm")
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="NC6051 自动收费写入后即确认，不需要人工确认",
    )


@router.post("/extra-receipts/{receipt_id}/void")
async def void_extra_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "revenue.extra.void")
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="NC6051 自动收费不允许手工作废，请修正来源后重新同步",
    )


@router.post("/recalculate")
async def recalculate_revenue(
    body: RevenueRecalculateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "revenue.recalculate")
    if body.end_date < body.start_date:
        raise HTTPException(status_code=400, detail="end_date 不能早于 start_date")

    params = {"start_date": body.start_date, "end_date": body.end_date, "unit_id": body.unit_id}
    unit_filter = "AND unit_id = :unit_id" if body.unit_id is not None else ""
    live_sales_ctes = _live_sales_ctes("s.sglhsrq BETWEEN :start_date AND :end_date")
    try:
        nc_refresh = db.execute(
            text(
                """
                SELECT *
                FROM refresh_nc_6051_extra_receipts(
                    :start_date,
                    :end_date,
                    'recalc_' || TO_CHAR(clock_timestamp(), 'YYYYMMDDHH24MISSMS')
                )
                """
            ),
            params,
        ).fetchone()
        db.execute(
            text(
                """
                DELETE FROM unit_revenue_sales_detail
                WHERE revenue_date BETWEEN :start_date AND :end_date
                  AND (:unit_id IS NULL OR unit_id = :unit_id)
                """
            ),
            params,
        )
        sales_result = db.execute(
            text(
                f"""
                WITH {live_sales_ctes},
                matched AS (
                    SELECT
                      live.store_id,
                      live.floor_id,
                      live.unit_id,
                      live.unit_code,
                      live.revenue_date,
                      live.source_group_code,
                      COALESCE(live.source_group_name, metadata.group_name) AS source_group_name,
                      metadata.department_code,
                      metadata.department_name,
                      metadata.area_name,
                      f.name AS floor_name,
                      live.operation_mode,
                      live.source_supplier_code,
                      live.source_operation_mode,
                      live.supplier_code,
                      live.supplier_name,
                      live.contract_code,
                      live.sales_qty,
                      live.sales_amount,
                      live.gross_profit_amount,
                      live.front_gross_profit_amount,
                      live.first_bill_no,
                      live.source_count
                    FROM live_sales live
                    LEFT JOIN floors f ON f.id = live.floor_id
                    LEFT JOIN LATERAL (
                        SELECT
                          cg.group_name,
                          cg.department_code,
                          cg.department_name,
                          cg.area_name
                        FROM counter_groups cg
                        WHERE cg.store_id = live.store_id
                          AND UPPER(TRIM(cg.group_code)) = UPPER(TRIM(live.source_group_code))
                        ORDER BY cg.group_id ASC
                        LIMIT 1
                    ) metadata ON true
                    WHERE (:unit_id IS NULL OR live.unit_id = :unit_id)
                )
                INSERT INTO unit_revenue_sales_detail (
                    id, store_id, floor_id, unit_id, unit_code, revenue_date,
                    source_group_code, source_group_name, department_code, department_name,
                    area_name, floor_name, operation_mode, supplier_code, supplier_name,
                    contract_code, sales_qty, tax_excluded_sales_amount,
                    tax_excluded_profit_amount, front_gross_profit_amount,
                    source_doc_no, source_row_key,
                    etl_batch_id, raw_payload, updated_at
                )
                SELECT
                    md5(
                        matched.revenue_date::text || '|' ||
                        matched.store_id::text || '|' ||
                        matched.source_group_code || '|' ||
                        COALESCE(matched.source_supplier_code, '') || '|' ||
                        COALESCE(matched.source_operation_mode, '') || '|' ||
                        matched.unit_id::text
                    ) AS id,
                    matched.store_id,
                    matched.floor_id,
                    matched.unit_id,
                    matched.unit_code,
                    matched.revenue_date,
                    matched.source_group_code,
                    matched.source_group_name,
                    matched.department_code,
                    matched.department_name,
                    matched.area_name,
                    matched.floor_name,
                    matched.operation_mode,
                    matched.supplier_code,
                    matched.supplier_name,
                    matched.contract_code,
                    matched.sales_qty,
                    matched.sales_amount,
                    matched.gross_profit_amount,
                    matched.front_gross_profit_amount,
                    matched.first_bill_no,
                    concat_ws(
                      '|',
                      matched.revenue_date::text,
                      matched.store_id::text,
                      matched.source_group_code,
                      COALESCE(matched.source_supplier_code, ''),
                      COALESCE(matched.source_operation_mode, '')
                    ),
                    'RECALC_SALES_' || to_char(NOW(), 'YYYYMMDDHH24MISS'),
                    jsonb_build_object(
                      'source', 'salegoodslist',
                      'source_count', matched.source_count,
                      'source_supplier_code', matched.source_supplier_code,
                      'source_operation_mode', matched.source_operation_mode
                    ),
                    NOW()
                FROM matched
                WHERE matched.unit_id IS NOT NULL
                RETURNING id
                """
            ),
            params,
        )
        sales_detail_rows = len(sales_result.fetchall())

        loss_bearing_recalc_condition = _loss_bearing_fee_condition("fee")
        db.execute(
            text(
                f"""
                DELETE FROM unit_daily_revenue_summary
                WHERE revenue_date BETWEEN :start_date AND :end_date
                  {unit_filter}
                """
            ),
            params,
        )
        result = db.execute(
            text(
                f"""
                WITH fee_source_rows AS MATERIALIZED (
                    SELECT
                      fee.*,
                      ROW_NUMBER() OVER (
                        PARTITION BY
                          CASE
                            WHEN NULLIF(TRIM(fee.source_doc_no), '') IS NOT NULL
                             AND NULLIF(TRIM(fee.source_row_key), '') IS NOT NULL
                              THEN ''
                            ELSE fee.id
                          END,
                          fee.store_id,
                          fee.revenue_date,
                          UPPER(TRIM(COALESCE(fee.source_type, ''))),
                          UPPER(TRIM(COALESCE(fee.source_group_code, ''))),
                          UPPER(TRIM(COALESCE(fee.contract_code, ''))),
                          UPPER(TRIM(COALESCE(fee.fee_type_code, ''))),
                          TRIM(COALESCE(fee.source_doc_no, '')),
                          TRIM(COALESCE(fee.source_row_key, '')),
                          COALESCE(fee.tax_included_amount, 0),
                          COALESCE(fee.tax_excluded_amount, 0)
                        ORDER BY fee.id
                      ) AS exact_duplicate_rank
                    FROM unit_revenue_fee_detail fee
                    WHERE fee.revenue_date BETWEEN :start_date AND :end_date
                      AND fee.unit_id IS NOT NULL
                      {unit_filter}
                ),
                source_rows AS (
                    SELECT
                      store_id, floor_id, unit_id, unit_code, revenue_date,
                      tax_excluded_profit_amount AS sales_amount,
                      0::numeric AS fee_amount,
                      0::numeric AS extra_amount,
                      1 AS sales_count,
                      0 AS fee_count,
                      0 AS extra_count,
                      etl_batch_id
                    FROM unit_revenue_sales_detail
                    WHERE revenue_date BETWEEN :start_date AND :end_date
                      AND unit_id IS NOT NULL
                      {unit_filter}
                    UNION ALL
                    SELECT
                      fee.store_id, fee.floor_id, fee.unit_id, fee.unit_code, fee.revenue_date,
                      CASE
                        WHEN {loss_bearing_recalc_condition}
                          THEN fee.tax_excluded_amount / {LOSS_BEARING_TAX_DIVISOR}
                        ELSE 0::numeric
                      END,
                      CASE
                        WHEN {loss_bearing_recalc_condition} THEN 0::numeric
                        ELSE fee.tax_excluded_amount
                      END,
                      0::numeric,
                      CASE WHEN {loss_bearing_recalc_condition} THEN 1 ELSE 0 END,
                      CASE WHEN {loss_bearing_recalc_condition} THEN 0 ELSE 1 END,
                      0,
                      fee.etl_batch_id
                    FROM fee_source_rows fee
                    WHERE fee.exact_duplicate_rank = 1
                    UNION ALL
                    SELECT
                      store_id, floor_id, unit_id, unit_code, revenue_date,
                      0::numeric,
                      0::numeric,
                      amount,
                      0,
                      0,
                      1,
                      NULL::varchar
                    FROM revenue_extra_receipts
                    WHERE revenue_date BETWEEN :start_date AND :end_date
                      AND status = 'CONFIRMED'
                      AND source_type = 'NC6051'
                      AND unit_id IS NOT NULL
                      {unit_filter}
                ),
                grouped AS (
                    SELECT
                      MAX(source_rows.store_id) AS store_id,
                      COALESCE(MAX(bu.floor_id), MAX(source_rows.floor_id)) AS floor_id,
                      source_rows.unit_id,
                      COALESCE(MAX(source_rows.unit_code), MAX(bu.unit_code)) AS unit_code,
                      source_rows.revenue_date,
                      COALESCE(SUM(sales_amount), 0)::numeric(18,2) AS sales_gross_profit_amount,
                      COALESCE(SUM(fee_amount), 0)::numeric(18,2) AS fee_amount,
                      COALESCE(SUM(extra_amount), 0)::numeric(18,2) AS extra_amount,
                      COALESCE(SUM(sales_count), 0)::integer AS sales_detail_count,
                      COALESCE(SUM(fee_count), 0)::integer AS fee_detail_count,
                      COALESCE(SUM(extra_count), 0)::integer AS extra_detail_count,
                      MAX(etl_batch_id) AS etl_batch_id
                    FROM source_rows
                    LEFT JOIN business_units bu ON bu.id = source_rows.unit_id
                    GROUP BY source_rows.unit_id, source_rows.revenue_date
                )
                INSERT INTO unit_daily_revenue_summary (
                    store_id, floor_id, unit_id, unit_code, revenue_date,
                    sales_gross_profit_amount, fee_amount, extra_amount,
                    sales_detail_count, fee_detail_count, extra_detail_count,
                    etl_batch_id, calculated_at, updated_at
                )
                SELECT
                    store_id, floor_id, unit_id, unit_code, revenue_date,
                    sales_gross_profit_amount, fee_amount, extra_amount,
                    sales_detail_count, fee_detail_count, extra_detail_count,
                    etl_batch_id, NOW(), NOW()
                FROM grouped
                WHERE unit_code IS NOT NULL
                RETURNING id
                """
            ),
            params,
        )
        inserted = len(result.fetchall())
        db.commit()
        return {
            "message": "收益日汇总已重算",
            "start_date": body.start_date.isoformat(),
            "end_date": body.end_date.isoformat(),
            "unit_id": body.unit_id,
            "sales_detail_rows": sales_detail_rows,
            "nc_6051_source_rows": int(nc_refresh.source_rows or 0),
            "nc_6051_inserted_rows": int(nc_refresh.inserted_rows or 0),
            "nc_6051_physical_match_rows": int(nc_refresh.physical_match_rows or 0),
            "nc_6051_backoffice_fallback_rows": int(nc_refresh.backoffice_fallback_rows or 0),
            "nc_6051_unmatched_rows": int(nc_refresh.unmatched_rows or 0),
            "summary_rows": inserted,
        }
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"重算收益汇总失败: {exc}")
