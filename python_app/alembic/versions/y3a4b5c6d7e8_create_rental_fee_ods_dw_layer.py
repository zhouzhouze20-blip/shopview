"""create rental fee ODS and DW layers

Revision ID: y3a4b5c6d7e8
Revises: x2f3a4b5c6d7
Create Date: 2026-08-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "y3a4b5c6d7e8"
down_revision: Union[str, Sequence[str], None] = "x2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


REFRESH_RENTAL_FUNCTION_SQL = r"""
CREATE OR REPLACE FUNCTION dw.refresh_revenue_fee_rental_layer(p_batch_id VARCHAR DEFAULT NULL)
RETURNS TABLE (
    detail_rows BIGINT,
    active_exception_rows BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_batch_id VARCHAR(100) := COALESCE(
        NULLIF(BTRIM(p_batch_id), ''),
        'dw_rental_fee_' || TO_CHAR(clock_timestamp(), 'YYYYMMDDHH24MISSMS')
    );
BEGIN
    DROP TABLE IF EXISTS pg_temp.tmp_rental_fee_source;

    CREATE TEMP TABLE tmp_rental_fee_source ON COMMIT DROP AS
    SELECT
        detail.spdbillno AS source_payment_bill_no,
        detail.spdrowno AS source_payment_row_no,
        detail.spdsetbillno AS source_settlement_bill_no,
        detail.spdsetrowno AS source_settlement_row_no,
        head.sphbillno,
        head.sphtype AS document_type,
        head.sphflag AS document_status,
        head.sphmkt AS store_code,
        head.sphsupid AS supplier_code,
        supplier.sbcname AS supplier_name,
        head.sphmfid AS source_group_code,
        source_group.mfcname AS source_group_name,
        head.sphcontno AS contract_code,
        head.sphpaydate::DATE AS payment_date,
        detail.spdstartdate::DATE AS service_start_date,
        detail.spdenddate::DATE AS service_end_date,
        detail.spddep AS source_department_code,
        detail.spdmfid AS detail_group_code,
        detail.spditemcode AS fee_item_code,
        charge_item.ccname AS fee_item_name,
        detail.spdamount AS raw_amount,
        detail.spdtaxrate AS detail_tax_rate,
        detail.spdnotaxamount AS detail_tax_excluded_amount,
        CASE head.sphtype
            WHEN '1' THEN 1
            WHEN '4' THEN -1
        END AS amount_sign,
        CASE
            WHEN charge_item.cccode IS NOT NULL THEN 'FEE_DICTIONARY'
            WHEN detail.spditemcode LIKE '00-%' THEN 'ADJUSTMENT'
            ELSE 'UNMAPPED'
        END AS fee_item_classification,
        CASE
            WHEN head.sphtype IN ('1', '4') THEN 'SUPPORTED'
            ELSE 'UNSUPPORTED'
        END AS document_type_status,
        GREATEST(
            detail.source_loaded_at,
            head.source_loaded_at,
            supplier.source_loaded_at,
            source_group.source_loaded_at,
            charge_item.source_loaded_at
        ) AS source_loaded_at
    FROM ods.erp_supsettlepaydet detail
    LEFT JOIN ods.erp_mallsuppayhead head
      ON head.sphbillno = detail.spdbillno
    LEFT JOIN ods.erp_supplierbase supplier
      ON supplier.sbid = head.sphsupid
    LEFT JOIN ods.erp_manaframe source_group
      ON source_group.mfcode = head.sphmfid
    LEFT JOIN ods.erp_codecharge charge_item
      ON charge_item.cccode = detail.spditemcode;

    INSERT INTO dw.revenue_fee_rental_detail (
        source_payment_bill_no,
        source_payment_row_no,
        source_settlement_bill_no,
        source_settlement_row_no,
        document_type,
        document_status,
        document_type_status,
        store_code,
        source_group_code,
        source_group_name,
        detail_group_code,
        source_department_code,
        supplier_code,
        supplier_name,
        contract_code,
        payment_date,
        service_start_date,
        service_end_date,
        recognition_date,
        recognition_basis,
        fee_item_code,
        fee_item_name,
        fee_item_classification,
        raw_amount,
        amount_sign,
        tax_included_amount,
        source_tax_rate,
        source_tax_excluded_amount,
        tax_excluded_amount,
        tax_calculation_source,
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
        source.source_payment_bill_no,
        source.source_payment_row_no,
        source.source_settlement_bill_no,
        source.source_settlement_row_no,
        source.document_type,
        source.document_status,
        source.document_type_status,
        source.store_code,
        source.source_group_code,
        source.source_group_name,
        source.detail_group_code,
        source.source_department_code,
        source.supplier_code,
        source.supplier_name,
        source.contract_code,
        source.payment_date,
        source.service_start_date,
        source.service_end_date,
        source.payment_date,
        'PAYMENT_DATE',
        source.fee_item_code,
        source.fee_item_name,
        source.fee_item_classification,
        source.raw_amount,
        source.amount_sign,
        CASE
            WHEN source.amount_sign IS NOT NULL
            THEN ROUND(source.raw_amount * source.amount_sign, 2)
        END,
        CASE
            WHEN source.detail_tax_rate BETWEEN 0 AND 0.20
            THEN source.detail_tax_rate
        END,
        source.detail_tax_excluded_amount,
        CASE
            WHEN source.amount_sign IS NULL THEN NULL
            WHEN source.detail_tax_excluded_amount IS NOT NULL
            THEN ROUND(source.detail_tax_excluded_amount * source.amount_sign, 2)
            WHEN source.detail_tax_rate BETWEEN 0 AND 0.20
            THEN ROUND(source.raw_amount * source.amount_sign / (1 + source.detail_tax_rate), 2)
            ELSE ROUND(source.raw_amount * source.amount_sign, 2)
        END,
        CASE
            WHEN source.amount_sign IS NULL THEN 'UNRESOLVED_SIGN'
            WHEN source.detail_tax_excluded_amount IS NOT NULL THEN 'DETAIL_NOTAX_AMOUNT'
            WHEN source.detail_tax_rate BETWEEN 0 AND 0.20 THEN 'DETAIL_TAX_RATE'
            ELSE 'GROSS_FALLBACK'
        END,
        'PENDING',
        NULL,
        MD5(CONCAT_WS(
            CHR(31),
            source.source_payment_bill_no,
            source.source_payment_row_no::TEXT,
            source.source_settlement_bill_no,
            source.source_settlement_row_no::TEXT,
            source.document_type,
            source.document_status,
            source.store_code,
            source.source_group_code,
            source.supplier_code,
            source.contract_code,
            source.payment_date::TEXT,
            source.service_start_date::TEXT,
            source.service_end_date::TEXT,
            source.fee_item_code,
            source.raw_amount::TEXT,
            source.detail_tax_rate::TEXT,
            source.detail_tax_excluded_amount::TEXT
        )),
        source.source_loaded_at,
        v_batch_id,
        JSONB_BUILD_OBJECT(
            'source_payment_bill_no', source.source_payment_bill_no,
            'source_payment_row_no', source.source_payment_row_no,
            'source_settlement_bill_no', source.source_settlement_bill_no,
            'source_settlement_row_no', source.source_settlement_row_no,
            'document_type', source.document_type,
            'document_status', source.document_status,
            'payment_date', source.payment_date,
            'service_start_date', source.service_start_date,
            'service_end_date', source.service_end_date,
            'source_department_code', source.source_department_code,
            'source_group_code', source.source_group_code,
            'detail_group_code', source.detail_group_code,
            'supplier_code', source.supplier_code,
            'contract_code', source.contract_code,
            'fee_item_code', source.fee_item_code,
            'raw_amount', source.raw_amount,
            'detail_tax_rate', source.detail_tax_rate,
            'detail_tax_excluded_amount', source.detail_tax_excluded_amount
        ),
        NOW(),
        NOW()
    FROM tmp_rental_fee_source source
    WHERE source.sphbillno IS NOT NULL
    ON CONFLICT (source_payment_bill_no, source_payment_row_no) DO UPDATE SET
        source_settlement_bill_no = EXCLUDED.source_settlement_bill_no,
        source_settlement_row_no = EXCLUDED.source_settlement_row_no,
        document_type = EXCLUDED.document_type,
        document_status = EXCLUDED.document_status,
        document_type_status = EXCLUDED.document_type_status,
        store_code = EXCLUDED.store_code,
        source_group_code = EXCLUDED.source_group_code,
        source_group_name = EXCLUDED.source_group_name,
        detail_group_code = EXCLUDED.detail_group_code,
        source_department_code = EXCLUDED.source_department_code,
        supplier_code = EXCLUDED.supplier_code,
        supplier_name = EXCLUDED.supplier_name,
        contract_code = EXCLUDED.contract_code,
        payment_date = EXCLUDED.payment_date,
        service_start_date = EXCLUDED.service_start_date,
        service_end_date = EXCLUDED.service_end_date,
        recognition_date = EXCLUDED.recognition_date,
        recognition_basis = EXCLUDED.recognition_basis,
        fee_item_code = EXCLUDED.fee_item_code,
        fee_item_name = EXCLUDED.fee_item_name,
        fee_item_classification = EXCLUDED.fee_item_classification,
        raw_amount = EXCLUDED.raw_amount,
        amount_sign = EXCLUDED.amount_sign,
        tax_included_amount = EXCLUDED.tax_included_amount,
        source_tax_rate = EXCLUDED.source_tax_rate,
        source_tax_excluded_amount = EXCLUDED.source_tax_excluded_amount,
        tax_excluded_amount = EXCLUDED.tax_excluded_amount,
        tax_calculation_source = EXCLUDED.tax_calculation_source,
        source_row_hash = EXCLUDED.source_row_hash,
        source_loaded_at = EXCLUDED.source_loaded_at,
        etl_batch_id = EXCLUDED.etl_batch_id,
        raw_payload = EXCLUDED.raw_payload,
        transformed_at = EXCLUDED.transformed_at,
        updated_at = EXCLUDED.updated_at;

    UPDATE dw.revenue_fee_rental_exception
    SET is_active = FALSE,
        last_seen_at = NOW(),
        updated_at = NOW()
    WHERE is_active;

    INSERT INTO dw.revenue_fee_rental_exception (
        source_payment_bill_no,
        source_payment_row_no,
        exception_type,
        store_code,
        source_group_code,
        supplier_code,
        contract_code,
        fee_item_code,
        amount,
        status,
        is_active,
        etl_batch_id,
        first_seen_at,
        last_seen_at,
        created_at,
        updated_at
    )
    SELECT
        source.source_payment_bill_no,
        source.source_payment_row_no,
        exception.exception_type,
        source.store_code,
        source.source_group_code,
        source.supplier_code,
        source.contract_code,
        source.fee_item_code,
        source.raw_amount,
        'PENDING',
        TRUE,
        v_batch_id,
        NOW(),
        NOW(),
        NOW(),
        NOW()
    FROM tmp_rental_fee_source source
    CROSS JOIN LATERAL (
        SELECT 'HEAD_NOT_FOUND'::VARCHAR AS exception_type
        WHERE source.sphbillno IS NULL
        UNION ALL
        SELECT 'UNSUPPORTED_DOCUMENT_TYPE'::VARCHAR
        WHERE source.sphbillno IS NOT NULL
          AND source.document_type_status = 'UNSUPPORTED'
        UNION ALL
        SELECT 'GROUP_CODE_MISMATCH'::VARCHAR
        WHERE source.sphbillno IS NOT NULL
          AND source.detail_group_code IS NOT NULL
          AND source.source_group_code IS DISTINCT FROM source.detail_group_code
        UNION ALL
        SELECT 'FEE_ITEM_UNMAPPED'::VARCHAR
        WHERE source.sphbillno IS NOT NULL
          AND source.fee_item_classification = 'UNMAPPED'
    ) exception
    ON CONFLICT (
        source_payment_bill_no,
        source_payment_row_no,
        exception_type
    ) DO UPDATE SET
        store_code = EXCLUDED.store_code,
        source_group_code = EXCLUDED.source_group_code,
        supplier_code = EXCLUDED.supplier_code,
        contract_code = EXCLUDED.contract_code,
        fee_item_code = EXCLUDED.fee_item_code,
        amount = EXCLUDED.amount,
        is_active = TRUE,
        etl_batch_id = EXCLUDED.etl_batch_id,
        last_seen_at = NOW(),
        updated_at = NOW();

    RETURN QUERY
    SELECT
        (SELECT COUNT(*) FROM dw.revenue_fee_rental_detail),
        (SELECT COUNT(*) FROM dw.revenue_fee_rental_exception WHERE is_active);
END;
$$;
"""


UNIFIED_VIEW_SQL = r"""
CREATE OR REPLACE VIEW dw.revenue_fee_unified AS
SELECT
    'JOINT'::VARCHAR AS business_type,
    joint.source_charge_bill_no AS source_bill_no,
    joint.source_charge_row_no AS source_row_no,
    joint.store_code,
    joint.source_group_code,
    joint.source_group_name,
    joint.supplier_code,
    joint.supplier_name,
    joint.contract_code,
    joint.fee_type_code,
    joint.fee_type_name,
    joint.fee_date AS occurrence_date,
    NULL::DATE AS service_start_date,
    NULL::DATE AS service_end_date,
    joint.payment_date,
    joint.fee_date AS recognition_date,
    'OCCURRENCE_DATE'::VARCHAR AS recognition_basis,
    joint.tax_included_amount,
    joint.source_tax_rate AS tax_rate,
    joint.provisional_tax_excluded_amount AS tax_excluded_amount,
    joint.resolved_payment_bill_no AS payment_bill_no,
    joint.payment_resolution_method AS resolution_status,
    joint.mapping_version_id,
    joint.unit_id,
    joint.unit_code,
    joint.mapping_status,
    joint.revenue_rule_version_id,
    joint.included_in_revenue,
    joint.etl_batch_id,
    joint.source_loaded_at,
    joint.raw_payload
FROM dw.revenue_fee_detail joint

UNION ALL

SELECT
    'RENTAL'::VARCHAR AS business_type,
    rental.source_payment_bill_no AS source_bill_no,
    rental.source_payment_row_no AS source_row_no,
    rental.store_code,
    rental.source_group_code,
    rental.source_group_name,
    rental.supplier_code,
    rental.supplier_name,
    rental.contract_code,
    rental.fee_item_code AS fee_type_code,
    rental.fee_item_name AS fee_type_name,
    NULL::DATE AS occurrence_date,
    rental.service_start_date,
    rental.service_end_date,
    rental.payment_date,
    rental.recognition_date,
    rental.recognition_basis,
    rental.tax_included_amount,
    rental.source_tax_rate AS tax_rate,
    rental.tax_excluded_amount,
    rental.source_payment_bill_no AS payment_bill_no,
    rental.document_type_status AS resolution_status,
    rental.mapping_version_id,
    rental.unit_id,
    rental.unit_code,
    rental.mapping_status,
    rental.revenue_rule_version_id,
    rental.included_in_revenue,
    rental.etl_batch_id,
    rental.source_loaded_at,
    rental.raw_payload
FROM dw.revenue_fee_rental_detail rental;
"""


def _source_loaded_at() -> sa.Column:
    return sa.Column(
        "source_loaded_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )


def upgrade() -> None:
    op.create_table(
        "erp_mallsuppayhead",
        sa.Column("sphbillno", sa.String(100), primary_key=True),
        sa.Column("sphdjbh", sa.String(100)),
        sa.Column("sphtype", sa.String(1), nullable=False),
        sa.Column("sphmkt", sa.String(100), nullable=False),
        sa.Column("sphflag", sa.String(1), nullable=False),
        sa.Column("sphsupid", sa.String(100), nullable=False),
        sa.Column("sphmoney", sa.Numeric(18, 4), nullable=False),
        sa.Column("sphmoneyupper", sa.String(200)),
        sa.Column("sphhl", sa.Numeric(18, 6)),
        sa.Column("sphbz", sa.String(100)),
        sa.Column("sphbbje", sa.Numeric(18, 4)),
        sa.Column("sphbank", sa.String(200)),
        sa.Column("sphaccntno", sa.String(200)),
        sa.Column("sphtaxno", sa.String(100)),
        sa.Column("sphmktbank", sa.String(200)),
        sa.Column("sphmktaccntno", sa.String(200)),
        sa.Column("sphmkttaxno", sa.String(100)),
        sa.Column("sphpaydate", sa.DateTime(), nullable=False),
        sa.Column("inputor", sa.String(100), nullable=False),
        sa.Column("inputdate", sa.DateTime(), nullable=False),
        sa.Column("auditor", sa.String(100)),
        sa.Column("auditdate", sa.DateTime()),
        sa.Column("sphn1", sa.Numeric(18, 4)),
        sa.Column("sphn2", sa.Numeric(18, 4)),
        sa.Column("sphn3", sa.Numeric(18, 4)),
        sa.Column("sphvc1", sa.String(100)),
        sa.Column("sphvc2", sa.String(500)),
        sa.Column("sphvc3", sa.String(100)),
        sa.Column("sphmemo", sa.Text()),
        sa.Column("sphmfid", sa.String(100)),
        sa.Column("sphwmid", sa.String(10)),
        sa.Column("sphcontno", sa.String(100)),
        sa.Column("sphyckfs", sa.Numeric(18, 4)),
        _source_loaded_at(),
        schema="ods",
        comment="Fuji rental payment document headers from DBUSRSET.MALLSUPPAYHEAD",
    )
    op.create_index(
        "ix_ods_mallsuppayhead_paydate",
        "erp_mallsuppayhead",
        ["sphpaydate"],
        schema="ods",
    )
    op.create_index(
        "ix_ods_mallsuppayhead_auditdate",
        "erp_mallsuppayhead",
        ["auditdate", "inputdate"],
        schema="ods",
    )
    op.create_index(
        "ix_ods_mallsuppayhead_group_contract",
        "erp_mallsuppayhead",
        ["sphmkt", "sphmfid", "sphcontno"],
        schema="ods",
    )

    op.create_table(
        "erp_supsettlepaydet",
        sa.Column("spdbillno", sa.String(100), nullable=False),
        sa.Column("spdrowno", sa.Numeric(12, 0), nullable=False),
        sa.Column("spdsetbillno", sa.String(100), nullable=False),
        sa.Column("spdsetrowno", sa.Numeric(12, 0), nullable=False),
        sa.Column("spditemcode", sa.String(100), nullable=False),
        sa.Column("spdstartdate", sa.DateTime(), nullable=False),
        sa.Column("spdenddate", sa.DateTime(), nullable=False),
        sa.Column("spddep", sa.String(100), nullable=False),
        sa.Column("spdamount", sa.Numeric(18, 4), nullable=False),
        sa.Column("spdckamount", sa.Numeric(18, 4), nullable=False),
        sa.Column("spdyfamount", sa.Numeric(18, 4), nullable=False),
        sa.Column("spdbcpay", sa.Numeric(18, 4), nullable=False),
        sa.Column("spdbcdk", sa.Numeric(18, 4), nullable=False),
        sa.Column("spdmemo", sa.Text()),
        sa.Column("spdtype", sa.String(1), nullable=False),
        sa.Column("spdisadv", sa.String(1), nullable=False),
        sa.Column("spdmfid", sa.String(100)),
        sa.Column("spdzntype", sa.String(1)),
        sa.Column("spdtaxrate", sa.Numeric(12, 6)),
        sa.Column("spdnotaxamount", sa.Numeric(18, 4)),
        _source_loaded_at(),
        sa.PrimaryKeyConstraint(
            "spdbillno",
            "spdrowno",
            name="pk_ods_erp_supsettlepaydet",
        ),
        schema="ods",
        comment="Fuji rental payment fee rows from DBUSRSET.SUPSETTLEPAYDET",
    )
    op.create_index(
        "ix_ods_supsettlepaydet_settlement",
        "erp_supsettlepaydet",
        ["spdsetbillno", "spdsetrowno"],
        schema="ods",
    )
    op.create_index(
        "ix_ods_supsettlepaydet_fee_item",
        "erp_supsettlepaydet",
        ["spditemcode"],
        schema="ods",
    )
    op.create_index(
        "ix_ods_supsettlepaydet_period",
        "erp_supsettlepaydet",
        ["spdstartdate", "spdenddate"],
        schema="ods",
    )

    op.create_table(
        "revenue_fee_rental_detail",
        sa.Column("source_payment_bill_no", sa.String(100), nullable=False),
        sa.Column("source_payment_row_no", sa.Numeric(12, 0), nullable=False),
        sa.Column("source_settlement_bill_no", sa.String(100)),
        sa.Column("source_settlement_row_no", sa.Numeric(12, 0)),
        sa.Column("document_type", sa.String(10)),
        sa.Column("document_status", sa.String(10)),
        sa.Column("document_type_status", sa.String(20), nullable=False),
        sa.Column("store_code", sa.String(100)),
        sa.Column("source_group_code", sa.String(100)),
        sa.Column("source_group_name", sa.String(200)),
        sa.Column("detail_group_code", sa.String(100)),
        sa.Column("source_department_code", sa.String(100)),
        sa.Column("supplier_code", sa.String(100)),
        sa.Column("supplier_name", sa.String(200)),
        sa.Column("contract_code", sa.String(100)),
        sa.Column("payment_date", sa.Date()),
        sa.Column("service_start_date", sa.Date()),
        sa.Column("service_end_date", sa.Date()),
        sa.Column("recognition_date", sa.Date()),
        sa.Column("recognition_basis", sa.String(30), nullable=False),
        sa.Column("fee_item_code", sa.String(100)),
        sa.Column("fee_item_name", sa.String(200)),
        sa.Column("fee_item_classification", sa.String(30), nullable=False),
        sa.Column("raw_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("amount_sign", sa.SmallInteger()),
        sa.Column("tax_included_amount", sa.Numeric(18, 2)),
        sa.Column("source_tax_rate", sa.Numeric(12, 6)),
        sa.Column("source_tax_excluded_amount", sa.Numeric(18, 4)),
        sa.Column("tax_excluded_amount", sa.Numeric(18, 2)),
        sa.Column("tax_calculation_source", sa.String(30), nullable=False),
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
            "source_payment_bill_no",
            "source_payment_row_no",
            name="pk_dw_revenue_fee_rental_detail",
        ),
        sa.CheckConstraint(
            "document_type_status IN ('SUPPORTED','UNSUPPORTED')",
            name="ck_dw_rental_detail_document_type_status",
        ),
        sa.CheckConstraint(
            "fee_item_classification IN ('FEE_DICTIONARY','ADJUSTMENT','UNMAPPED')",
            name="ck_dw_rental_detail_item_classification",
        ),
        sa.CheckConstraint(
            "tax_calculation_source IN ('DETAIL_NOTAX_AMOUNT','DETAIL_TAX_RATE','GROSS_FALLBACK','UNRESOLVED_SIGN')",
            name="ck_dw_rental_detail_tax_source",
        ),
        sa.CheckConstraint(
            "mapping_status IN ('PENDING','MAPPED','AMBIGUOUS','UNMATCHED')",
            name="ck_dw_rental_detail_mapping_status",
        ),
        schema="dw",
        comment="Standardized rental fee rows at original payment-detail grain; revenue and cabinet rules remain pending",
    )
    op.create_index(
        "ix_dw_rental_detail_payment_date",
        "revenue_fee_rental_detail",
        ["payment_date", "store_code"],
        schema="dw",
    )
    op.create_index(
        "ix_dw_rental_detail_service_period",
        "revenue_fee_rental_detail",
        ["service_start_date", "service_end_date"],
        schema="dw",
    )
    op.create_index(
        "ix_dw_rental_detail_group_contract",
        "revenue_fee_rental_detail",
        ["source_group_code", "contract_code"],
        schema="dw",
    )
    op.create_index(
        "ix_dw_rental_detail_item_classification",
        "revenue_fee_rental_detail",
        ["fee_item_classification", "included_in_revenue"],
        schema="dw",
    )

    op.create_table(
        "revenue_fee_rental_exception",
        sa.Column("source_payment_bill_no", sa.String(100), nullable=False),
        sa.Column("source_payment_row_no", sa.Numeric(12, 0), nullable=False),
        sa.Column("exception_type", sa.String(40), nullable=False),
        sa.Column("store_code", sa.String(100)),
        sa.Column("source_group_code", sa.String(100)),
        sa.Column("supplier_code", sa.String(100)),
        sa.Column("contract_code", sa.String(100)),
        sa.Column("fee_item_code", sa.String(100)),
        sa.Column("amount", sa.Numeric(18, 4)),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("resolution_note", sa.Text()),
        sa.Column("resolved_by", sa.String(100)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("etl_batch_id", sa.String(100), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint(
            "source_payment_bill_no",
            "source_payment_row_no",
            "exception_type",
            name="pk_dw_revenue_fee_rental_exception",
        ),
        sa.CheckConstraint(
            "exception_type IN ('HEAD_NOT_FOUND','UNSUPPORTED_DOCUMENT_TYPE','GROUP_CODE_MISMATCH','FEE_ITEM_UNMAPPED')",
            name="ck_dw_rental_exception_type",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING','RESOLVED','IGNORED')",
            name="ck_dw_rental_exception_status",
        ),
        schema="dw",
        comment="Technical exception queue for rental fee ETL; adjustment classification remains a business rule, not a technical error",
    )
    op.create_index(
        "ix_dw_rental_exception_active_status",
        "revenue_fee_rental_exception",
        ["is_active", "status", "exception_type"],
        schema="dw",
    )

    op.execute(
        "COMMENT ON TABLE dw.revenue_fee_detail IS "
        "'Current standardized JOINT fee rows at original Fuji charge grain; use dw.revenue_fee_unified for cross-business consumption'"
    )
    op.execute(REFRESH_RENTAL_FUNCTION_SQL)
    op.execute(UNIFIED_VIEW_SQL)
    op.execute("SELECT * FROM dw.refresh_revenue_fee_rental_layer('alembic_y3a4b5c6d7e8')")


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS dw.revenue_fee_unified")
    op.execute("DROP FUNCTION IF EXISTS dw.refresh_revenue_fee_rental_layer(VARCHAR)")
    op.drop_index("ix_dw_rental_exception_active_status", table_name="revenue_fee_rental_exception", schema="dw")
    op.drop_table("revenue_fee_rental_exception", schema="dw")
    op.drop_index("ix_dw_rental_detail_item_classification", table_name="revenue_fee_rental_detail", schema="dw")
    op.drop_index("ix_dw_rental_detail_group_contract", table_name="revenue_fee_rental_detail", schema="dw")
    op.drop_index("ix_dw_rental_detail_service_period", table_name="revenue_fee_rental_detail", schema="dw")
    op.drop_index("ix_dw_rental_detail_payment_date", table_name="revenue_fee_rental_detail", schema="dw")
    op.drop_table("revenue_fee_rental_detail", schema="dw")
    op.drop_index("ix_ods_supsettlepaydet_period", table_name="erp_supsettlepaydet", schema="ods")
    op.drop_index("ix_ods_supsettlepaydet_fee_item", table_name="erp_supsettlepaydet", schema="ods")
    op.drop_index("ix_ods_supsettlepaydet_settlement", table_name="erp_supsettlepaydet", schema="ods")
    op.drop_table("erp_supsettlepaydet", schema="ods")
    op.drop_index("ix_ods_mallsuppayhead_group_contract", table_name="erp_mallsuppayhead", schema="ods")
    op.drop_index("ix_ods_mallsuppayhead_auditdate", table_name="erp_mallsuppayhead", schema="ods")
    op.drop_index("ix_ods_mallsuppayhead_paydate", table_name="erp_mallsuppayhead", schema="ods")
    op.drop_table("erp_mallsuppayhead", schema="ods")
