"""create auditable revenue fee DW layer

Revision ID: x2f3a4b5c6d7
Revises: w1e2f3a4b5c6
Create Date: 2026-08-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "x2f3a4b5c6d7"
down_revision: Union[str, Sequence[str], None] = "w1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


REFRESH_FUNCTION_SQL = r"""
CREATE OR REPLACE FUNCTION dw.refresh_revenue_fee_layer(p_batch_id VARCHAR DEFAULT NULL)
RETURNS TABLE (
    bridge_rows BIGINT,
    detail_rows BIGINT,
    active_exception_rows BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_batch_id VARCHAR(100) := COALESCE(
        NULLIF(BTRIM(p_batch_id), ''),
        'dw_fee_' || TO_CHAR(clock_timestamp(), 'YYYYMMDDHH24MISSMS')
    );
BEGIN
    DROP TABLE IF EXISTS pg_temp.tmp_fee_payment_resolution;

    CREATE TEMP TABLE tmp_fee_payment_resolution ON COMMIT DROP AS
    WITH payment_candidates AS (
        SELECT
            NULLIF(BTRIM(pb.pbjsno), '') AS settlement_no,
            UPPER(NULLIF(BTRIM(pb.pbmfid), '')) AS source_group_code_norm,
            COUNT(DISTINCT NULLIF(BTRIM(pb.pbpaybillno), ''))
                FILTER (WHERE NULLIF(BTRIM(pb.pbpaybillno), '') IS NOT NULL)
                AS candidate_payment_count,
            JSONB_AGG(
                DISTINCT NULLIF(BTRIM(pb.pbpaybillno), '')
                ORDER BY NULLIF(BTRIM(pb.pbpaybillno), '')
            ) FILTER (WHERE NULLIF(BTRIM(pb.pbpaybillno), '') IS NOT NULL)
                AS candidate_payment_bill_nos,
            MIN(NULLIF(BTRIM(pb.pbpaybillno), ''))
                FILTER (WHERE NULLIF(BTRIM(pb.pbpaybillno), '') IS NOT NULL)
                AS only_payment_bill_no,
            MAX(pb.source_loaded_at) AS bridge_source_loaded_at
        FROM ods.erp_paybatch pb
        WHERE NULLIF(BTRIM(pb.pbjsno), '') IS NOT NULL
          AND NULLIF(BTRIM(pb.pbmfid), '') IS NOT NULL
        GROUP BY
            NULLIF(BTRIM(pb.pbjsno), ''),
            UPPER(NULLIF(BTRIM(pb.pbmfid), ''))
    ),
    resolution AS (
        SELECT
            charge.sscbillno AS source_charge_bill_no,
            charge.sscrowno AS source_charge_row_no,
            NULLIF(BTRIM(charge.sscjsno), '') AS source_settlement_no,
            NULLIF(BTRIM(charge.sscmfid), '') AS source_group_code,
            NULLIF(BTRIM(charge.sscpaybillno), '') AS direct_payment_bill_no,
            CASE
                WHEN NULLIF(BTRIM(charge.sscpaybillno), '') IS NULL
                 AND COALESCE(candidate.candidate_payment_count, 0) = 1
                THEN candidate.only_payment_bill_no
            END AS fallback_payment_bill_no,
            COALESCE(
                NULLIF(BTRIM(charge.sscpaybillno), ''),
                CASE
                    WHEN COALESCE(candidate.candidate_payment_count, 0) = 1
                    THEN candidate.only_payment_bill_no
                END
            ) AS resolved_payment_bill_no,
            CASE
                WHEN NULLIF(BTRIM(charge.sscpaybillno), '') IS NOT NULL THEN 'DIRECT'
                WHEN COALESCE(candidate.candidate_payment_count, 0) = 1 THEN 'UNIQUE_BRIDGE'
                WHEN COALESCE(candidate.candidate_payment_count, 0) > 1 THEN 'AMBIGUOUS_BRIDGE'
                ELSE 'UNMATCHED'
            END AS resolution_method,
            COALESCE(candidate.candidate_payment_count, 0)::INTEGER
                AS candidate_payment_count,
            COALESCE(candidate.candidate_payment_bill_nos, '[]'::JSONB)
                AS candidate_payment_bill_nos,
            GREATEST(
                charge.source_loaded_at,
                candidate.bridge_source_loaded_at
            ) AS resolution_source_loaded_at
        FROM ods.erp_supsetcharge charge
        LEFT JOIN payment_candidates candidate
          ON candidate.settlement_no = NULLIF(BTRIM(charge.sscjsno), '')
         AND candidate.source_group_code_norm = UPPER(NULLIF(BTRIM(charge.sscmfid), ''))
    )
    SELECT
        resolution.*,
        (payment.sphbillno IS NOT NULL) AS payment_head_found,
        payment.sphsupid AS payment_supplier_code,
        supplier.sbcname AS payment_supplier_name,
        payment.sphpaydate::DATE AS payment_date,
        payment.auditdate AS payment_audit_date,
        GREATEST(
            resolution.resolution_source_loaded_at,
            payment.source_loaded_at,
            supplier.source_loaded_at
        ) AS source_loaded_at
    FROM resolution
    LEFT JOIN ods.erp_suppayhead payment
      ON payment.sphbillno = resolution.resolved_payment_bill_no
    LEFT JOIN ods.erp_supplierbase supplier
      ON supplier.sbid = payment.sphsupid;

    INSERT INTO dw.fee_payment_bridge (
        source_charge_bill_no,
        source_charge_row_no,
        source_settlement_no,
        source_group_code,
        direct_payment_bill_no,
        fallback_payment_bill_no,
        resolved_payment_bill_no,
        resolution_method,
        candidate_payment_count,
        candidate_payment_bill_nos,
        payment_head_found,
        payment_supplier_code,
        payment_supplier_name,
        payment_date,
        payment_audit_date,
        source_loaded_at,
        etl_batch_id,
        transformed_at
    )
    SELECT
        source_charge_bill_no,
        source_charge_row_no,
        source_settlement_no,
        source_group_code,
        direct_payment_bill_no,
        fallback_payment_bill_no,
        resolved_payment_bill_no,
        resolution_method,
        candidate_payment_count,
        candidate_payment_bill_nos,
        payment_head_found,
        payment_supplier_code,
        payment_supplier_name,
        payment_date,
        payment_audit_date,
        source_loaded_at,
        v_batch_id,
        NOW()
    FROM tmp_fee_payment_resolution
    ON CONFLICT (source_charge_bill_no, source_charge_row_no) DO UPDATE SET
        source_settlement_no = EXCLUDED.source_settlement_no,
        source_group_code = EXCLUDED.source_group_code,
        direct_payment_bill_no = EXCLUDED.direct_payment_bill_no,
        fallback_payment_bill_no = EXCLUDED.fallback_payment_bill_no,
        resolved_payment_bill_no = EXCLUDED.resolved_payment_bill_no,
        resolution_method = EXCLUDED.resolution_method,
        candidate_payment_count = EXCLUDED.candidate_payment_count,
        candidate_payment_bill_nos = EXCLUDED.candidate_payment_bill_nos,
        payment_head_found = EXCLUDED.payment_head_found,
        payment_supplier_code = EXCLUDED.payment_supplier_code,
        payment_supplier_name = EXCLUDED.payment_supplier_name,
        payment_date = EXCLUDED.payment_date,
        payment_audit_date = EXCLUDED.payment_audit_date,
        source_loaded_at = EXCLUDED.source_loaded_at,
        etl_batch_id = EXCLUDED.etl_batch_id,
        transformed_at = EXCLUDED.transformed_at;

    UPDATE dw.fee_payment_exception
    SET is_active = FALSE,
        last_seen_at = NOW(),
        updated_at = NOW()
    WHERE is_active;

    INSERT INTO dw.fee_payment_exception (
        source_charge_bill_no,
        source_charge_row_no,
        exception_type,
        fee_month,
        charge_amount,
        source_settlement_no,
        source_group_code,
        supplier_code,
        contract_code,
        candidate_payment_count,
        candidate_payment_bill_nos,
        status,
        is_active,
        etl_batch_id,
        first_seen_at,
        last_seen_at,
        created_at,
        updated_at
    )
    SELECT
        charge.sscbillno,
        charge.sscrowno,
        bridge.resolution_method,
        charge.sscfsmon,
        COALESCE(charge.sscmoney, 0),
        NULLIF(BTRIM(charge.sscjsno), ''),
        NULLIF(BTRIM(charge.sscmfid), ''),
        NULLIF(BTRIM(charge.sscsupid), ''),
        NULLIF(BTRIM(charge.ssccontno), ''),
        bridge.candidate_payment_count,
        bridge.candidate_payment_bill_nos,
        'PENDING',
        TRUE,
        v_batch_id,
        NOW(),
        NOW(),
        NOW(),
        NOW()
    FROM ods.erp_supsetcharge charge
    JOIN dw.fee_payment_bridge bridge
      ON bridge.source_charge_bill_no = charge.sscbillno
     AND bridge.source_charge_row_no = charge.sscrowno
    WHERE bridge.resolution_method IN ('AMBIGUOUS_BRIDGE', 'UNMATCHED')
    ON CONFLICT (source_charge_bill_no, source_charge_row_no) DO UPDATE SET
        exception_type = EXCLUDED.exception_type,
        fee_month = EXCLUDED.fee_month,
        charge_amount = EXCLUDED.charge_amount,
        source_settlement_no = EXCLUDED.source_settlement_no,
        source_group_code = EXCLUDED.source_group_code,
        supplier_code = EXCLUDED.supplier_code,
        contract_code = EXCLUDED.contract_code,
        candidate_payment_count = EXCLUDED.candidate_payment_count,
        candidate_payment_bill_nos = EXCLUDED.candidate_payment_bill_nos,
        is_active = TRUE,
        etl_batch_id = EXCLUDED.etl_batch_id,
        last_seen_at = NOW(),
        updated_at = NOW();

    INSERT INTO dw.revenue_fee_detail (
        source_charge_bill_no,
        source_charge_row_no,
        source_document_no,
        source_charge_type,
        source_charge_flag,
        fee_date,
        fee_month,
        store_code,
        operation_mode_code,
        source_group_code,
        source_group_name,
        supplier_code,
        supplier_name,
        contract_code,
        settlement_no,
        fee_type_code,
        fee_type_name,
        tax_included_amount,
        source_tax_rate,
        tax_rate_status,
        provisional_tax_excluded_amount,
        direct_payment_bill_no,
        resolved_payment_bill_no,
        payment_resolution_method,
        payment_head_found,
        payment_date,
        payment_audit_date,
        payment_supplier_code,
        payment_supplier_name,
        mapping_status,
        included_in_revenue,
        source_row_hash,
        source_loaded_at,
        etl_batch_id,
        raw_payload,
        transformed_at,
        updated_at
    )
    SELECT
        charge.sscbillno,
        charge.sscrowno,
        NULLIF(BTRIM(charge.sscdjbh), ''),
        NULLIF(BTRIM(charge.ssctype), ''),
        NULLIF(BTRIM(charge.sscflag), ''),
        charge.sscfsdate::DATE,
        charge.sscfsmon,
        NULLIF(BTRIM(charge.sscmarket), ''),
        NULLIF(BTRIM(charge.sscwmid), ''),
        NULLIF(BTRIM(charge.sscmfid), ''),
        source_group.mfcname,
        NULLIF(BTRIM(charge.sscsupid), ''),
        source_supplier.sbcname,
        NULLIF(BTRIM(charge.ssccontno), ''),
        NULLIF(BTRIM(charge.sscjsno), ''),
        NULLIF(BTRIM(charge.sscid), ''),
        COALESCE(charge_item.ccname, charge.sscname),
        COALESCE(charge.sscmoney, 0),
        CASE
            WHEN charge_item.ccnum3 BETWEEN 0 AND 0.20 THEN charge_item.ccnum3
        END,
        CASE
            WHEN charge_item.ccnum3 BETWEEN 0 AND 0.20 THEN 'SOURCE'
            WHEN charge_item.ccnum3 IS NULL THEN 'MISSING'
            ELSE 'INVALID'
        END,
        CASE
            WHEN charge_item.ccnum3 BETWEEN 0 AND 0.20
            THEN ROUND(COALESCE(charge.sscmoney, 0) / (1 + charge_item.ccnum3), 2)
            ELSE COALESCE(charge.sscmoney, 0)
        END,
        bridge.direct_payment_bill_no,
        bridge.resolved_payment_bill_no,
        bridge.resolution_method,
        bridge.payment_head_found,
        bridge.payment_date,
        bridge.payment_audit_date,
        bridge.payment_supplier_code,
        bridge.payment_supplier_name,
        'PENDING',
        NULL,
        MD5(CONCAT_WS(
            CHR(31),
            charge.sscbillno,
            charge.sscrowno::TEXT,
            charge.sscfsdate::TEXT,
            charge.sscfsmon,
            charge.sscmarket,
            charge.sscmfid,
            charge.sscsupid,
            charge.ssccontno,
            charge.sscjsno,
            charge.sscid,
            charge.sscmoney::TEXT,
            charge.sscpaybillno
        )),
        GREATEST(
            charge.source_loaded_at,
            source_group.source_loaded_at,
            source_supplier.source_loaded_at,
            charge_item.source_loaded_at,
            bridge.source_loaded_at
        ),
        v_batch_id,
        JSONB_BUILD_OBJECT(
            'source_charge_bill_no', charge.sscbillno,
            'source_charge_row_no', charge.sscrowno,
            'source_document_no', charge.sscdjbh,
            'fee_occurrence_date', charge.sscfsdate,
            'fee_month', charge.sscfsmon,
            'source_group_code', charge.sscmfid,
            'supplier_code', charge.sscsupid,
            'contract_code', charge.ssccontno,
            'settlement_no', charge.sscjsno,
            'fee_type_code', charge.sscid,
            'fee_name_at_source', charge.sscname,
            'tax_included_amount', charge.sscmoney,
            'direct_payment_bill_no', charge.sscpaybillno,
            'source_input_date', charge.inputdate,
            'source_audit_date', charge.auditdate
        ),
        NOW(),
        NOW()
    FROM ods.erp_supsetcharge charge
    JOIN dw.fee_payment_bridge bridge
      ON bridge.source_charge_bill_no = charge.sscbillno
     AND bridge.source_charge_row_no = charge.sscrowno
    LEFT JOIN ods.erp_manaframe source_group
      ON source_group.mfcode = charge.sscmfid
    LEFT JOIN ods.erp_supplierbase source_supplier
      ON source_supplier.sbid = charge.sscsupid
    LEFT JOIN ods.erp_codecharge charge_item
      ON charge_item.cccode = charge.sscid
    ON CONFLICT (source_charge_bill_no, source_charge_row_no) DO UPDATE SET
        source_document_no = EXCLUDED.source_document_no,
        source_charge_type = EXCLUDED.source_charge_type,
        source_charge_flag = EXCLUDED.source_charge_flag,
        fee_date = EXCLUDED.fee_date,
        fee_month = EXCLUDED.fee_month,
        store_code = EXCLUDED.store_code,
        operation_mode_code = EXCLUDED.operation_mode_code,
        source_group_code = EXCLUDED.source_group_code,
        source_group_name = EXCLUDED.source_group_name,
        supplier_code = EXCLUDED.supplier_code,
        supplier_name = EXCLUDED.supplier_name,
        contract_code = EXCLUDED.contract_code,
        settlement_no = EXCLUDED.settlement_no,
        fee_type_code = EXCLUDED.fee_type_code,
        fee_type_name = EXCLUDED.fee_type_name,
        tax_included_amount = EXCLUDED.tax_included_amount,
        source_tax_rate = EXCLUDED.source_tax_rate,
        tax_rate_status = EXCLUDED.tax_rate_status,
        provisional_tax_excluded_amount = EXCLUDED.provisional_tax_excluded_amount,
        direct_payment_bill_no = EXCLUDED.direct_payment_bill_no,
        resolved_payment_bill_no = EXCLUDED.resolved_payment_bill_no,
        payment_resolution_method = EXCLUDED.payment_resolution_method,
        payment_head_found = EXCLUDED.payment_head_found,
        payment_date = EXCLUDED.payment_date,
        payment_audit_date = EXCLUDED.payment_audit_date,
        payment_supplier_code = EXCLUDED.payment_supplier_code,
        payment_supplier_name = EXCLUDED.payment_supplier_name,
        source_row_hash = EXCLUDED.source_row_hash,
        source_loaded_at = EXCLUDED.source_loaded_at,
        etl_batch_id = EXCLUDED.etl_batch_id,
        raw_payload = EXCLUDED.raw_payload,
        transformed_at = EXCLUDED.transformed_at,
        updated_at = EXCLUDED.updated_at;

    RETURN QUERY
    SELECT
        (SELECT COUNT(*) FROM dw.fee_payment_bridge),
        (SELECT COUNT(*) FROM dw.revenue_fee_detail),
        (SELECT COUNT(*) FROM dw.fee_payment_exception WHERE is_active);
END;
$$;
"""


def upgrade() -> None:
    op.create_table(
        "fee_payment_bridge",
        sa.Column("source_charge_bill_no", sa.String(100), nullable=False),
        sa.Column("source_charge_row_no", sa.Numeric(12, 0), nullable=False),
        sa.Column("source_settlement_no", sa.String(100)),
        sa.Column("source_group_code", sa.String(100)),
        sa.Column("direct_payment_bill_no", sa.String(100)),
        sa.Column("fallback_payment_bill_no", sa.String(100)),
        sa.Column("resolved_payment_bill_no", sa.String(100)),
        sa.Column("resolution_method", sa.String(30), nullable=False),
        sa.Column("candidate_payment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "candidate_payment_bill_nos",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("payment_head_found", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("payment_supplier_code", sa.String(100)),
        sa.Column("payment_supplier_name", sa.String(200)),
        sa.Column("payment_date", sa.Date()),
        sa.Column("payment_audit_date", sa.DateTime()),
        sa.Column("source_loaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("etl_batch_id", sa.String(100), nullable=False),
        sa.Column("transformed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint(
            "source_charge_bill_no",
            "source_charge_row_no",
            name="pk_dw_fee_payment_bridge",
        ),
        sa.CheckConstraint(
            "resolution_method IN ('DIRECT','UNIQUE_BRIDGE','AMBIGUOUS_BRIDGE','UNMATCHED')",
            name="ck_dw_fee_payment_bridge_method",
        ),
        sa.CheckConstraint(
            "candidate_payment_count >= 0",
            name="ck_dw_fee_payment_bridge_candidate_count",
        ),
        schema="dw",
        comment="One deterministic payment resolution row per Fuji ERP charge source row",
    )
    op.create_index(
        "ix_dw_fee_payment_bridge_resolved_bill",
        "fee_payment_bridge",
        ["resolved_payment_bill_no"],
        schema="dw",
    )
    op.create_index(
        "ix_dw_fee_payment_bridge_method",
        "fee_payment_bridge",
        ["resolution_method"],
        schema="dw",
    )
    op.create_index(
        "ix_dw_fee_payment_bridge_settlement_group",
        "fee_payment_bridge",
        ["source_settlement_no", "source_group_code"],
        schema="dw",
    )

    op.create_table(
        "fee_payment_exception",
        sa.Column("source_charge_bill_no", sa.String(100), nullable=False),
        sa.Column("source_charge_row_no", sa.Numeric(12, 0), nullable=False),
        sa.Column("exception_type", sa.String(30), nullable=False),
        sa.Column("fee_month", sa.String(6), nullable=False),
        sa.Column("charge_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("source_settlement_no", sa.String(100)),
        sa.Column("source_group_code", sa.String(100)),
        sa.Column("supplier_code", sa.String(100)),
        sa.Column("contract_code", sa.String(100)),
        sa.Column("candidate_payment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "candidate_payment_bill_nos",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("resolved_payment_bill_no", sa.String(100)),
        sa.Column("resolution_note", sa.Text()),
        sa.Column("resolved_by", sa.String(100)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("etl_batch_id", sa.String(100), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint(
            "source_charge_bill_no",
            "source_charge_row_no",
            name="pk_dw_fee_payment_exception",
        ),
        sa.CheckConstraint(
            "exception_type IN ('AMBIGUOUS_BRIDGE','UNMATCHED')",
            name="ck_dw_fee_payment_exception_type",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING','RESOLVED','IGNORED')",
            name="ck_dw_fee_payment_exception_status",
        ),
        schema="dw",
        comment="Persistent payment-resolution exception queue; manual resolution fields survive refreshes",
    )
    op.create_index(
        "ix_dw_fee_payment_exception_active_status",
        "fee_payment_exception",
        ["is_active", "status", "fee_month"],
        schema="dw",
    )

    op.create_table(
        "revenue_fee_detail",
        sa.Column("source_charge_bill_no", sa.String(100), nullable=False),
        sa.Column("source_charge_row_no", sa.Numeric(12, 0), nullable=False),
        sa.Column("source_document_no", sa.String(100)),
        sa.Column("source_charge_type", sa.String(10)),
        sa.Column("source_charge_flag", sa.String(10)),
        sa.Column("fee_date", sa.Date(), nullable=False),
        sa.Column("fee_month", sa.String(6), nullable=False),
        sa.Column("store_code", sa.String(100)),
        sa.Column("operation_mode_code", sa.String(20)),
        sa.Column("source_group_code", sa.String(100)),
        sa.Column("source_group_name", sa.String(200)),
        sa.Column("supplier_code", sa.String(100)),
        sa.Column("supplier_name", sa.String(200)),
        sa.Column("contract_code", sa.String(100)),
        sa.Column("settlement_no", sa.String(100)),
        sa.Column("fee_type_code", sa.String(50)),
        sa.Column("fee_type_name", sa.String(200)),
        sa.Column("tax_included_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("source_tax_rate", sa.Numeric(12, 6)),
        sa.Column("tax_rate_status", sa.String(20), nullable=False),
        sa.Column("provisional_tax_excluded_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("direct_payment_bill_no", sa.String(100)),
        sa.Column("resolved_payment_bill_no", sa.String(100)),
        sa.Column("payment_resolution_method", sa.String(30), nullable=False),
        sa.Column("payment_head_found", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("payment_date", sa.Date()),
        sa.Column("payment_audit_date", sa.DateTime()),
        sa.Column("payment_supplier_code", sa.String(100)),
        sa.Column("payment_supplier_name", sa.String(200)),
        sa.Column("mapping_version_id", sa.BigInteger()),
        sa.Column("unit_id", sa.BigInteger()),
        sa.Column("unit_code", sa.Text()),
        sa.Column("mapping_status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("revenue_rule_version_id", sa.BigInteger()),
        sa.Column("included_in_revenue", sa.Boolean()),
        sa.Column("source_row_hash", sa.String(32), nullable=False),
        sa.Column("source_loaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("etl_batch_id", sa.String(100), nullable=False),
        sa.Column(
            "raw_payload",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("transformed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint(
            "source_charge_bill_no",
            "source_charge_row_no",
            name="pk_dw_revenue_fee_detail",
        ),
        sa.CheckConstraint(
            "fee_month ~ '^[0-9]{6}$'",
            name="ck_dw_revenue_fee_detail_month",
        ),
        sa.CheckConstraint(
            "tax_rate_status IN ('SOURCE','MISSING','INVALID')",
            name="ck_dw_revenue_fee_detail_tax_status",
        ),
        sa.CheckConstraint(
            "payment_resolution_method IN ('DIRECT','UNIQUE_BRIDGE','AMBIGUOUS_BRIDGE','UNMATCHED')",
            name="ck_dw_revenue_fee_detail_payment_method",
        ),
        sa.CheckConstraint(
            "mapping_status IN ('PENDING','MAPPED','AMBIGUOUS','UNMATCHED')",
            name="ck_dw_revenue_fee_detail_mapping_status",
        ),
        schema="dw",
        comment="Current standardized fee row at the original Fuji charge grain; no fee exclusion or cabinet mapping is applied",
    )
    op.create_index(
        "ix_dw_revenue_fee_detail_month_store",
        "revenue_fee_detail",
        ["fee_month", "store_code"],
        schema="dw",
    )
    op.create_index(
        "ix_dw_revenue_fee_detail_group_date",
        "revenue_fee_detail",
        ["source_group_code", "fee_date"],
        schema="dw",
    )
    op.create_index(
        "ix_dw_revenue_fee_detail_payment",
        "revenue_fee_detail",
        ["resolved_payment_bill_no"],
        schema="dw",
    )
    op.create_index(
        "ix_dw_revenue_fee_detail_mapping",
        "revenue_fee_detail",
        ["mapping_status", "fee_month"],
        schema="dw",
    )

    op.execute(REFRESH_FUNCTION_SQL)
    op.execute("SELECT * FROM dw.refresh_revenue_fee_layer('alembic_x2f3a4b5c6d7')")

    op.execute(
        "COMMENT ON FUNCTION dw.refresh_revenue_fee_layer(VARCHAR) IS "
        "'Refresh deterministic payment bridge, persistent exception queue, and standardized fee detail from ODS'"
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS dw.refresh_revenue_fee_layer(VARCHAR)")
    op.drop_index("ix_dw_revenue_fee_detail_mapping", table_name="revenue_fee_detail", schema="dw")
    op.drop_index("ix_dw_revenue_fee_detail_payment", table_name="revenue_fee_detail", schema="dw")
    op.drop_index("ix_dw_revenue_fee_detail_group_date", table_name="revenue_fee_detail", schema="dw")
    op.drop_index("ix_dw_revenue_fee_detail_month_store", table_name="revenue_fee_detail", schema="dw")
    op.drop_table("revenue_fee_detail", schema="dw")
    op.drop_index("ix_dw_fee_payment_exception_active_status", table_name="fee_payment_exception", schema="dw")
    op.drop_table("fee_payment_exception", schema="dw")
    op.drop_index("ix_dw_fee_payment_bridge_settlement_group", table_name="fee_payment_bridge", schema="dw")
    op.drop_index("ix_dw_fee_payment_bridge_method", table_name="fee_payment_bridge", schema="dw")
    op.drop_index("ix_dw_fee_payment_bridge_resolved_bill", table_name="fee_payment_bridge", schema="dw")
    op.drop_table("fee_payment_bridge", schema="dw")
