"""
收益地图与经营单元日收益 API。
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from models.database import get_db
from models.models import User
from routers.auth import get_current_user
from routers.authz import load_business_scope, require_permission, scope_allows_business


router = APIRouter(prefix="/api/revenue-map", tags=["revenue"])
logger = logging.getLogger(__name__)

REVENUE_BINDING_ORDER_SQL = (
    "(b.shop_unit_id IS NOT NULL) DESC, "
    "COALESCE(b.is_primary, false) DESC, "
    "b.id ASC"
)

LOSS_BEARING_FEE_NAME_PREFIX = "损失承担"
LOSS_BEARING_TAX_DIVISOR = "1.13"

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
              COALESCE(SUM(s.sglxssr), 0)::numeric(18,2) AS sales_amount,
              COALESCE(
                SUM(COALESCE(s.sgln2, 0) / NULLIF(1 + COALESCE(s.sglxstax, 0), 0)),
                0
              )::numeric AS gross_profit_amount,
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
                NULLIF(mf.mfjyfs, ''),
                NULLIF(candidate.business_type, ''),
                NULLIF(candidate.contract_operation_mode, '')
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
            WHERE NOT EXISTS (
                SELECT 1
                FROM live_sales mapped
                WHERE mapped.revenue_date = source.revenue_date
                  AND mapped.store_code = source.store_code
                  AND mapped.source_group_code = source.source_group_code
                  AND mapped.source_supplier_code IS NOT DISTINCT FROM source.source_supplier_code
                  AND mapped.source_operation_mode IS NOT DISTINCT FROM source.source_operation_mode
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
                  fee.revenue_date,
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
                WHERE NOT ({loss_bearing_fee_condition})
                   OR fee.exact_duplicate_rank = 1
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
              source_group_code,
              source_group_name,
              gross_profit_amount AS sales_amount,
              0::numeric AS fee_amount,
              0::numeric AS extra_amount,
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
              fee.source_group_code,
              fee.source_group_name,
              CASE
                WHEN {loss_bearing_fee_condition} THEN fee.tax_excluded_amount
                ELSE 0::numeric
              END,
              CASE
                WHEN {loss_bearing_fee_condition} THEN 0::numeric
                ELSE fee.tax_excluded_amount
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
              extra.source_group_code,
              extra.source_group_name,
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
        )
    """


def _money(value: object) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


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


def _month_from_date(value: date) -> str:
    return value.strftime("%Y-%m")


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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return permission-scoped revenue at store → department → cabinet grain.

    Sales keep the finance-date basis; fee revenue uses the linked payment date.
    """
    require_permission(db, current_user, "revenue.dashboard.view")
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date 不能早于 start_date")

    try:
        params = {
            "start_date": start_date,
            "end_date": end_date,
        }
        source_ctes = _live_revenue_source_ctes(
            "s.sglhsrq BETWEEN :start_date AND :end_date",
            "payment_ref.payment_date BETWEEN :start_date AND :end_date",
            "extra.revenue_date BETWEEN :start_date AND :end_date",
            fee_date_basis="payment",
        )
        loss_bearing_fee_condition = _loss_bearing_fee_condition("fee")
        rows = db.execute(
            text(
                f"""
                WITH {source_ctes},
                fee_breakdown_rows AS (
                  SELECT
                    fee.store_id,
                    UPPER(TRIM(fee.source_group_code)) AS group_code_norm,
                    NULLIF(TRIM(fee.fee_type_code), '') AS fee_type_code,
                    COALESCE(
                      NULLIF(TRIM(fee.fee_type_name), ''),
                      '未分类收费'
                    ) AS fee_type_name,
                    COALESCE(SUM(fee.tax_excluded_amount), 0)::numeric AS tax_excluded_amount
                  FROM live_fees fee
                  WHERE NOT ({loss_bearing_fee_condition})
                  GROUP BY
                    fee.store_id,
                    UPPER(TRIM(fee.source_group_code)),
                    NULLIF(TRIM(fee.fee_type_code), ''),
                    COALESCE(
                      NULLIF(TRIM(fee.fee_type_name), ''),
                      '未分类收费'
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
                  NULLIF(TRIM(dept.mfcode), '') AS department_code,
                  NULLIF(TRIM(dept.mfcname), '') AS department_name,
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
                  COALESCE(SUM(src.sales_amount), 0)::numeric AS sales_gross_profit_amount,
                  COALESCE(SUM(src.fee_amount), 0)::numeric AS fee_amount,
                  COALESCE(SUM(src.extra_amount), 0)::numeric AS extra_amount,
                  COALESCE(
                    SUM(src.sales_amount + src.fee_amount + src.extra_amount),
                    0
                  )::numeric AS total_amount,
                  COALESCE(fee_breakdowns.fee_breakdown, '[]'::jsonb) AS fee_breakdown
                FROM source_rows src
                JOIN stores st ON st.store_id = src.store_id
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
                  NULLIF(TRIM(dept.mfcode), ''),
                  NULLIF(TRIM(dept.mfcname), ''),
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

        scope = load_business_scope(db, current_user, fallback_resource_code="revenue")
        allowed_rows = [dict(row) for row in rows if _dashboard_row_allowed(scope, dict(row))]
        items = [
            {
                "store_id": int(row["store_id"]),
                "store_code": row.get("store_code"),
                "store_name": row.get("store_name"),
                "department_code": row.get("department_code"),
                "department_name": row.get("department_name") or "未归属部门",
                "group_code": row.get("group_code"),
                "group_name": row.get("group_name") or "未归属柜位",
                "unit_codes": row.get("unit_codes"),
                "unit_count": int(row.get("unit_count") or 0),
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
        return {
            "start_date": _dt(start_date),
            "end_date": _dt(end_date),
            "permission_scoped": True,
            "grain": "门店-部门-柜位",
            "date_basis": {
                "sales": "financial_date",
                "fees": "payment_date",
                "extra": "revenue_date",
            },
            "fee_scope_note": "收费仅统计已关联结算付款日期或租赁付款日期的数据",
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


@router.get("/dashboard/groups/{group_code}/details")
async def revenue_dashboard_group_details(
    group_code: str,
    start_date: date,
    end_date: date,
    store_id: int,
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
        gross_profit_daily = []
        if detail_type in {"all", "gross-profit"}:
            source_ctes = _live_revenue_source_ctes(
                "s.sglhsrq BETWEEN :start_date AND :end_date",
                "payment_ref.payment_date BETWEEN :start_date AND :end_date",
                "extra.revenue_date BETWEEN :start_date AND :end_date",
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
                "payment_ref.payment_date BETWEEN :start_date AND :end_date",
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
                      COALESCE(SUM(fee.tax_excluded_amount) OVER (), 0)::numeric AS total_amount
                    FROM live_fees fee
                    WHERE fee.store_id = :store_id
                      AND UPPER(TRIM(fee.source_group_code)) = UPPER(:group_code)
                      AND NOT ({loss_bearing_fee_condition})
                    ORDER BY fee.revenue_date DESC, fee.id DESC
                    LIMIT :limit
                    """
                ),
                params,
            ).mappings().all()

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
        fee_total_amount = _money(fee_rows[0].get("total_amount")) if fee_rows else 0.0
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
                "total_amount": fee_total_amount,
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


@router.get("/monthly")
async def monthly_revenue(
    revenue_month: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}$"),
    revenue_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
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
            extra_date_filter = "extra.revenue_date BETWEEN :start_date AND :end_date"
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
        sql = f"""
            WITH {source_ctes}
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
            FROM source_rows src
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
        extra_date_filter = "extra.revenue_date BETWEEN :start_date AND :end_date"
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

        daily = db.execute(
            text(
                f"""
                WITH {source_ctes}
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
                FROM source_rows src
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
                    live_sales.source_group_code || '|' ||
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
                WHERE extra.unit_id = :unit_id AND {extra_date_filter}
                ORDER BY revenue_date DESC, id DESC
                LIMIT 500
                """
            ),
            params,
        ).fetchall()

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
    filters: list[str] = []
    if start_date and end_date:
        filters.append("revenue_date BETWEEN :start_date AND :end_date")
        params["start_date"] = start_date
        params["end_date"] = end_date
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
        text(f"SELECT * FROM revenue_extra_receipts {where} ORDER BY revenue_date DESC, id DESC LIMIT 500"),
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
    payload = _normalize_unit_fields(db, _model_data(body))
    if payload["amount"] == 0:
        raise HTTPException(status_code=400, detail="金额不能为 0")
    try:
        row = db.execute(
            text(
                """
                INSERT INTO revenue_extra_receipts (
                    store_id, floor_id, unit_id, unit_code, revenue_date, extra_type, amount,
                    receipt_date, voucher_no, contract_code, supplier_code, supplier_name,
                    source_group_code, source_group_name, remark, attachment_url, created_by
                )
                VALUES (
                    :store_id, :floor_id, :unit_id, :unit_code, :revenue_date, :extra_type, :amount,
                    :receipt_date, :voucher_no, :contract_code, :supplier_code, :supplier_name,
                    :source_group_code, :source_group_name, :remark, :attachment_url, :created_by
                )
                RETURNING *
                """
            ),
            {**payload, "created_by": current_user.user_id},
        ).fetchone()
        db.commit()
        return _receipt_to_dict(row)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建补收记录失败: {exc}")


@router.put("/extra-receipts/{receipt_id}")
async def update_extra_receipt(
    receipt_id: int,
    body: RevenueExtraReceiptUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "revenue.extra.edit")
    current = db.execute(
        text("SELECT id, status FROM revenue_extra_receipts WHERE id = :id"),
        {"id": receipt_id},
    ).fetchone()
    if not current:
        raise HTTPException(status_code=404, detail="补收记录不存在")
    if current.status != "DRAFT":
        raise HTTPException(status_code=400, detail="只有草稿状态可以修改")

    payload = {k: v for k, v in _model_data(body).items() if v is not None}
    if "unit_id" in payload:
        payload = _normalize_unit_fields(db, payload)
    if "amount" in payload and payload["amount"] == 0:
        raise HTTPException(status_code=400, detail="金额不能为 0")
    if not payload:
        raise HTTPException(status_code=400, detail="没有可更新字段")

    allowed = {
        "store_id",
        "floor_id",
        "unit_id",
        "unit_code",
        "revenue_date",
        "extra_type",
        "amount",
        "receipt_date",
        "voucher_no",
        "contract_code",
        "supplier_code",
        "supplier_name",
        "source_group_code",
        "source_group_name",
        "remark",
        "attachment_url",
    }
    sets = [f"{key} = :{key}" for key in payload if key in allowed]
    payload["id"] = receipt_id
    try:
        row = db.execute(
            text(
                f"""
                UPDATE revenue_extra_receipts
                SET {", ".join(sets)}, updated_at = NOW()
                WHERE id = :id
                RETURNING *
                """
            ),
            payload,
        ).fetchone()
        db.commit()
        return _receipt_to_dict(row)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新补收记录失败: {exc}")


@router.post("/extra-receipts/{receipt_id}/confirm")
async def confirm_extra_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "revenue.extra.confirm")
    row = db.execute(
        text(
            """
            UPDATE revenue_extra_receipts
            SET status = 'CONFIRMED', confirmed_by = :user_id, confirmed_at = NOW(), updated_at = NOW()
            WHERE id = :id AND status = 'DRAFT'
            RETURNING *
            """
        ),
        {"id": receipt_id, "user_id": current_user.user_id},
    ).fetchone()
    if not row:
        db.rollback()
        raise HTTPException(status_code=400, detail="只有草稿状态可以确认，或记录不存在")
    db.commit()
    return _receipt_to_dict(row)


@router.post("/extra-receipts/{receipt_id}/void")
async def void_extra_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "revenue.extra.void")
    row = db.execute(
        text(
            """
            UPDATE revenue_extra_receipts
            SET status = 'VOID', voided_by = :user_id, voided_at = NOW(), updated_at = NOW()
            WHERE id = :id AND status <> 'VOID'
            RETURNING *
            """
        ),
        {"id": receipt_id, "user_id": current_user.user_id},
    ).fetchone()
    if not row:
        db.rollback()
        raise HTTPException(status_code=400, detail="记录不存在或已作废")
    db.commit()
    return _receipt_to_dict(row)


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
    try:
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
                WITH sales_by_group AS (
                    SELECT
                      s.sglhsrq::date AS revenue_date,
                      NULLIF(TRIM(s.sglmarket), '') AS store_code,
                      NULLIF(TRIM(s.sglmfid), '') AS source_group_code,
                      COALESCE(SUM(s.sglsl), 0)::numeric(18,4) AS sales_qty,
                      COALESCE(SUM(s.sglxssr), 0)::numeric(18,2) AS sales_amount,
                      COALESCE(SUM(s.sgln2), 0)::numeric(18,2) AS gross_profit_amount,
                      COUNT(*)::integer AS source_count,
                      MIN(s.sglbillno::varchar) AS first_bill_no
                    FROM salegoodslist s
                    WHERE s.sglhsrq BETWEEN :start_date AND :end_date
                      AND NULLIF(TRIM(s.sglmfid), '') IS NOT NULL
                    GROUP BY s.sglhsrq, NULLIF(TRIM(s.sglmarket), ''), NULLIF(TRIM(s.sglmfid), '')
                ),
                matched AS (
                    SELECT
                      CASE WHEN sales_by_group.store_code ~ '^[0-9]+$' THEN sales_by_group.store_code::integer ELSE NULL END AS store_id,
                      bu.floor_id,
                      bu.id AS unit_id,
                      bu.unit_code,
                      sales_by_group.revenue_date,
                      sales_by_group.source_group_code,
                      cg.group_name AS source_group_name,
                      cg.department_code,
                      cg.department_name,
                      cg.area_name,
                      f.name AS floor_name,
                      COALESCE(NULLIF(cg.operation_method, ''), binding.business_type) AS operation_mode,
                      binding.supplier_id AS supplier_code,
                      binding.brand_id AS supplier_name,
                      binding.contract_id AS contract_code,
                      sales_by_group.sales_qty,
                      sales_by_group.sales_amount,
                      sales_by_group.gross_profit_amount,
                      sales_by_group.first_bill_no,
                      sales_by_group.source_count
                    FROM sales_by_group
                    JOIN counter_groups cg
                      ON UPPER(TRIM(cg.group_code)) = UPPER(TRIM(sales_by_group.source_group_code))
                    JOIN LATERAL (
                        SELECT b.*
                        FROM business_unit_binding b
                        WHERE b.counter_group_id = cg.group_id
                          AND COALESCE(b.status, 'ACTIVE') = 'ACTIVE'
                          AND (b.start_date IS NULL OR b.start_date <= sales_by_group.revenue_date)
                          AND (b.end_date IS NULL OR b.end_date >= sales_by_group.revenue_date)
                        ORDER BY {REVENUE_BINDING_ORDER_SQL}
                        LIMIT 1
                    ) binding ON true
                    JOIN business_units bu ON bu.id = binding.shop_unit_id
                    LEFT JOIN floors f ON f.id = bu.floor_id
                    WHERE (:unit_id IS NULL OR bu.id = :unit_id)
                )
                INSERT INTO unit_revenue_sales_detail (
                    id, store_id, floor_id, unit_id, unit_code, revenue_date,
                    source_group_code, source_group_name, department_code, department_name,
                    area_name, floor_name, operation_mode, supplier_code, supplier_name,
                    contract_code, sales_qty, tax_excluded_sales_amount,
                    tax_excluded_profit_amount, source_doc_no, source_row_key,
                    etl_batch_id, raw_payload, updated_at
                )
                SELECT
                    md5(
                        matched.revenue_date::text || '|' ||
                        matched.source_group_code || '|' ||
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
                    matched.first_bill_no,
                    matched.revenue_date::text || '_' || matched.source_group_code,
                    'RECALC_SALES_' || to_char(NOW(), 'YYYYMMDDHH24MISS'),
                    jsonb_build_object('source', 'salegoodslist', 'source_count', matched.source_count),
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
                          fee.revenue_date,
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
                    WHERE NOT ({loss_bearing_recalc_condition})
                       OR fee.exact_duplicate_rank = 1
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
            "summary_rows": inserted,
        }
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"重算收益汇总失败: {exc}")
