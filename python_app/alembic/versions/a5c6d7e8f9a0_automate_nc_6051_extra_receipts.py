"""automate NC 6051 extra receipts

Revision ID: a5c6d7e8f9a0
Revises: z4b5c6d7e8f9
Create Date: 2026-08-06
"""
from typing import Sequence, Union

from alembic import op


revision: str = "a5c6d7e8f9a0"
down_revision: Union[str, Sequence[str], None] = "z4b5c6d7e8f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


REFRESH_FUNCTION_SQL = r"""
CREATE OR REPLACE FUNCTION refresh_nc_6051_extra_receipts(
    p_start_date DATE,
    p_end_date DATE,
    p_batch_id VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    source_rows BIGINT,
    inserted_rows BIGINT,
    physical_match_rows BIGINT,
    backoffice_fallback_rows BIGINT,
    unmatched_rows BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_batch_id VARCHAR(100) := COALESCE(
        NULLIF(BTRIM(p_batch_id), ''),
        'nc6051_' || TO_CHAR(clock_timestamp(), 'YYYYMMDDHH24MISSMS')
    );
    v_start_month DATE;
    v_end_month DATE;
    v_inserted_rows BIGINT := 0;
BEGIN
    IF p_start_date IS NULL OR p_end_date IS NULL OR p_end_date < p_start_date THEN
        RAISE EXCEPTION 'invalid NC6051 refresh date range';
    END IF;

    v_start_month := DATE_TRUNC('month', p_start_date)::DATE;
    v_end_month := DATE_TRUNC('month', p_end_date)::DATE;

    DROP TABLE IF EXISTS pg_temp.tmp_nc_6051_extra_receipts;

    CREATE TEMP TABLE tmp_nc_6051_extra_receipts ON COMMIT DROP AS
    WITH ranked_finance AS (
        SELECT
            f.*,
            COALESCE(
                NULLIF(BTRIM(f.pk_detail), ''),
                MD5(CONCAT_WS(
                    CHR(31),
                    f.pk_voucher,
                    f.subject_code,
                    f.valuecode,
                    f.explanation,
                    f.localdebitamount::TEXT,
                    f.localcreditamount::TEXT
                ))
            ) AS source_detail_key,
            ROW_NUMBER() OVER (
                PARTITION BY COALESCE(
                    NULLIF(BTRIM(f.pk_detail), ''),
                    MD5(CONCAT_WS(
                        CHR(31),
                        f.pk_voucher,
                        f.subject_code,
                        f.valuecode,
                        f.explanation,
                        f.localdebitamount::TEXT,
                        f.localcreditamount::TEXT
                    ))
                )
                ORDER BY f.load_date DESC NULLS LAST, f.pk_voucher, f.subject_code
            ) AS source_rank
        FROM bh_dw_gl_detail_fact2 f
        WHERE f.account_year ~ '^[0-9]{4}$'
          AND f.account_period ~ '^(0?[1-9]|1[0-2])$'
          AND MAKE_DATE(f.account_year::INTEGER, f.account_period::INTEGER, 1)
                BETWEEN v_start_month AND v_end_month
          AND BTRIM(COALESCE(f.subject_code, '')) LIKE '6051%'
          AND BTRIM(COALESCE(f.valuecode, '')) NOT IN (
              '210109', '220109', '310109', '330109'
          )
    ),
    finance_base AS (
        SELECT
            source_detail_key,
            BTRIM(pk_detail) AS pk_detail,
            BTRIM(pk_voucher) AS pk_voucher,
            BTRIM(subject_code) AS subject_code,
            BTRIM(pk_corp) AS pk_corp,
            BTRIM(valuecode) AS department_code,
            COALESCE(NULLIF(BTRIM(valuename), ''), BTRIM(valuecode)) AS department_name,
            COALESCE(explanation, '') AS explanation,
            account_year::INTEGER AS account_year,
            account_period::INTEGER AS account_period,
            COALESCE(localdebitamount, 0)::NUMERIC AS debit_amount,
            COALESCE(localcreditamount, 0)::NUMERIC AS credit_amount,
            ROUND(
                (COALESCE(localcreditamount, 0) - COALESCE(localdebitamount, 0))::NUMERIC,
                2
            ) AS amount,
            CASE
              WHEN pk_corp = '1018' AND valuecode LIKE '21%' THEN '601'
              WHEN pk_corp = '1018' AND valuecode LIKE '22%' THEN '602'
              WHEN pk_corp = '1021' AND valuecode LIKE '31%' THEN '603'
              WHEN pk_corp = '1084' AND valuecode LIKE '33%' THEN '604'
              ELSE NULL
            END AS store_code,
            CASE
              WHEN BTRIM(subject_code) IN ('605108', '605112')
               AND COALESCE(explanation, '') LIKE '%微信电费%'
                THEN '电表收费'
              WHEN COALESCE(valuename, '') LIKE '%物业%'
                THEN '物业收费'
              WHEN COALESCE(valuename, '') LIKE '%运营%'
                THEN '营运收费'
              ELSE NULL
            END AS extra_type,
            CASE
              WHEN BTRIM(subject_code) IN ('605108', '605112')
               AND COALESCE(explanation, '') LIKE '%微信电费%'
                THEN NULLIF(BTRIM(REGEXP_REPLACE(
                    REGEXP_REPLACE(
                        COALESCE(explanation, ''),
                        '^[0-9]{2}[.][0-9]{2}[.][0-9]{2}[[:space:]]*',
                        ''
                    ),
                    '微信电费(管理费)?[[:space:]]*$',
                    ''
                )), '')
              ELSE NULL
            END AS cabinet_name,
            CASE
              WHEN COALESCE(explanation, '') ~ '^[0-9]{2}[.][0-9]{2}[.][0-9]{2}'
               AND ('20' || SUBSTRING(COALESCE(explanation, '') FROM 1 FOR 2))::INTEGER
                    = account_year::INTEGER
               AND SUBSTRING(COALESCE(explanation, '') FROM 4 FOR 2)::INTEGER
                    = account_period::INTEGER
                THEN TO_DATE(
                    '20' || SUBSTRING(COALESCE(explanation, '') FROM 1 FOR 8),
                    'YYYY.MM.DD'
                )
              WHEN COALESCE(explanation, '') ~ '^[0-9]{8}'
               AND SUBSTRING(COALESCE(explanation, '') FROM 1 FOR 4)::INTEGER
                    = account_year::INTEGER
               AND SUBSTRING(COALESCE(explanation, '') FROM 5 FOR 2)::INTEGER
                    = account_period::INTEGER
                THEN TO_DATE(SUBSTRING(COALESCE(explanation, '') FROM 1 FOR 8), 'YYYYMMDD')
              ELSE (
                  MAKE_DATE(account_year::INTEGER, account_period::INTEGER, 1)
                  + INTERVAL '1 month - 1 day'
              )::DATE
            END AS revenue_date,
            load_date
        FROM ranked_finance
        WHERE source_rank = 1
    ),
    classified AS (
        SELECT finance_base.*
        FROM finance_base
        WHERE store_code IS NOT NULL
          AND extra_type IS NOT NULL
          AND amount <> 0
          AND NOT (explanation ~ '计提.*(销项)?税')
    ),
    store_rows AS (
        SELECT
            classified.*,
            st.store_id,
            REGEXP_REPLACE(
                REGEXP_REPLACE(UPPER(COALESCE(classified.cabinet_name, '')), '厅$', ''),
                '[^A-Z0-9一-龥]',
                '',
                'g'
            ) AS cabinet_name_norm
        FROM classified
        JOIN stores st
          ON BTRIM(st.store_code) = classified.store_code
         AND COALESCE(st.is_active, TRUE)
    ),
    group_master AS (
        SELECT
            cg.store_id,
            cg.group_id,
            NULLIF(BTRIM(cg.group_code), '') AS group_code,
            NULLIF(BTRIM(cg.group_name), '') AS group_name,
            REGEXP_REPLACE(
                REGEXP_REPLACE(UPPER(COALESCE(cg.group_name, '')), '厅$', ''),
                '[^A-Z0-9一-龥]',
                '',
                'g'
            ) AS group_name_norm
        FROM counter_groups cg
        WHERE NULLIF(BTRIM(cg.group_name), '') IS NOT NULL
    ),
    erp_group_master AS (
        SELECT
            NULLIF(BTRIM(mf.mfcode), '') AS group_code,
            NULLIF(BTRIM(mf.mfcname), '') AS group_name,
            REGEXP_REPLACE(
                REGEXP_REPLACE(UPPER(COALESCE(mf.mfcname, '')), '厅$', ''),
                '[^A-Z0-9一-龥]',
                '',
                'g'
            ) AS group_name_norm
        FROM manaframe mf
        WHERE NULLIF(BTRIM(mf.mfcode), '') IS NOT NULL
          AND NULLIF(BTRIM(mf.mfcname), '') IS NOT NULL
    ),
    physical_candidates AS (
        SELECT DISTINCT
            src.source_detail_key,
            binding.shop_unit_id AS unit_id,
            unit.floor_id,
            unit.unit_code,
            master.group_code,
            master.group_name,
            CASE
              WHEN master.group_name_norm = src.cabinet_name_norm THEN 2
              ELSE 4
            END AS match_rank
        FROM store_rows src
        JOIN group_master master
          ON master.store_id = src.store_id
         AND src.extra_type = '电表收费'
         AND LENGTH(src.cabinet_name_norm) >= 3
         AND LENGTH(master.group_name_norm) >= 3
         AND (
              master.group_name_norm = src.cabinet_name_norm
              OR master.group_name_norm LIKE '%' || src.cabinet_name_norm || '%'
              OR src.cabinet_name_norm LIKE '%' || master.group_name_norm || '%'
         )
        JOIN business_unit_binding binding
          ON binding.counter_group_id = master.group_id
         AND COALESCE(binding.status, 'ACTIVE') = 'ACTIVE'
         AND (binding.start_date IS NULL OR binding.start_date <= src.revenue_date)
         AND (binding.end_date IS NULL OR binding.end_date >= src.revenue_date)
        JOIN business_units unit
          ON unit.id = binding.shop_unit_id
         AND COALESCE(unit.status, 'ACTIVE') <> 'DISABLED'

        UNION

        SELECT DISTINCT
            src.source_detail_key,
            binding.shop_unit_id AS unit_id,
            unit.floor_id,
            unit.unit_code,
            master.group_code,
            master.group_name,
            CASE
              WHEN alias.id IS NOT NULL THEN 0
              WHEN master.group_name_norm = src.cabinet_name_norm THEN 1
              ELSE 3
            END AS match_rank
        FROM store_rows src
        LEFT JOIN revenue_nc_cabinet_alias alias
          ON alias.store_code = src.store_code
         AND alias.is_active
         AND REGEXP_REPLACE(
                REGEXP_REPLACE(UPPER(alias.source_cabinet_name), '厅$', ''),
                '[^A-Z0-9一-龥]',
                '',
                'g'
             ) = src.cabinet_name_norm
        JOIN erp_group_master master
          ON src.extra_type = '电表收费'
         AND LENGTH(src.cabinet_name_norm) >= 3
         AND (
              (alias.id IS NOT NULL AND master.group_code = alias.target_group_code)
              OR (
                  alias.id IS NULL
                  AND LENGTH(master.group_name_norm) >= 3
                  AND (
                      master.group_name_norm = src.cabinet_name_norm
                      OR master.group_name_norm LIKE '%' || src.cabinet_name_norm || '%'
                      OR src.cabinet_name_norm LIKE '%' || master.group_name_norm || '%'
                  )
              )
         )
        JOIN contmanaframe contract_group
          ON UPPER(BTRIM(contract_group.cmfmfid)) = UPPER(master.group_code)
         AND BTRIM(contract_group.cmfmarket) = src.store_code
        JOIN contmain contract
          ON BTRIM(contract.cmcontno) = BTRIM(contract_group.cmfcontno)
         AND BTRIM(contract.cmjsmkt) = src.store_code
         AND contract.cmeffdate::DATE <= src.revenue_date
         AND contract.cmlapdate::DATE >= src.revenue_date
        JOIN business_unit_binding binding
          ON BTRIM(binding.contract_id) = BTRIM(contract.cmcontno)
         AND COALESCE(binding.status, 'ACTIVE') = 'ACTIVE'
         AND (binding.start_date IS NULL OR binding.start_date <= src.revenue_date)
         AND (binding.end_date IS NULL OR binding.end_date >= src.revenue_date)
        JOIN business_units unit
          ON unit.id = binding.shop_unit_id
         AND COALESCE(unit.status, 'ACTIVE') <> 'DISABLED'
        JOIN floors unit_floor
          ON unit_floor.id = unit.floor_id
         AND BTRIM(unit_floor.store_code) = src.store_code
    ),
    best_candidate_rank AS (
        SELECT source_detail_key, MIN(match_rank) AS match_rank
        FROM physical_candidates
        GROUP BY source_detail_key
    ),
    physical_resolution AS (
        SELECT
            candidate.source_detail_key,
            CASE WHEN COUNT(DISTINCT candidate.unit_id) = 1 THEN MAX(candidate.unit_id) END AS unit_id,
            CASE WHEN COUNT(DISTINCT candidate.unit_id) = 1 THEN MAX(candidate.floor_id) END AS floor_id,
            CASE WHEN COUNT(DISTINCT candidate.unit_id) = 1 THEN MAX(candidate.unit_code) END AS unit_code,
            CASE WHEN COUNT(DISTINCT candidate.unit_id) = 1 THEN MAX(candidate.group_code) END AS group_code,
            CASE WHEN COUNT(DISTINCT candidate.unit_id) = 1 THEN MAX(candidate.group_name) END AS group_name,
            COUNT(DISTINCT candidate.unit_id)::INTEGER AS candidate_unit_count
        FROM physical_candidates candidate
        JOIN best_candidate_rank best
          ON best.source_detail_key = candidate.source_detail_key
         AND best.match_rank = candidate.match_rank
        GROUP BY candidate.source_detail_key
    ),
    backoffice_units AS (
        SELECT DISTINCT ON (st.store_id)
            st.store_id,
            unit.id AS unit_id,
            unit.floor_id,
            unit.unit_code
        FROM stores st
        JOIN floors floor
          ON BTRIM(floor.store_code) = BTRIM(st.store_code)
         AND BTRIM(floor.floor_code) = 'BO'
         AND BTRIM(floor.name) = '后台部门'
        JOIN business_units unit
          ON unit.floor_id = floor.id
         AND BTRIM(unit.unit_code) = '后台部门收益'
         AND COALESCE(unit.status, 'ACTIVE') <> 'DISABLED'
        ORDER BY st.store_id, unit.id
    ),
    resolved AS (
        SELECT
            src.*,
            COALESCE(physical.unit_id, backoffice.unit_id) AS unit_id,
            COALESCE(physical.floor_id, backoffice.floor_id) AS floor_id,
            COALESCE(physical.unit_code, backoffice.unit_code) AS unit_code,
            physical.group_code AS matched_group_code,
            physical.group_name AS matched_group_name,
            COALESCE(physical.candidate_unit_count, 0) AS candidate_unit_count,
            CASE
              WHEN physical.unit_id IS NOT NULL THEN 'PHYSICAL_CABINET'
              WHEN backoffice.unit_id IS NOT NULL THEN 'BACKOFFICE_FALLBACK'
              ELSE 'UNMATCHED'
            END AS match_method,
            CASE
              WHEN physical.unit_id IS NOT NULL THEN 'MATCHED'
              WHEN backoffice.unit_id IS NOT NULL THEN 'FALLBACK'
              ELSE 'UNMATCHED'
            END AS match_status
        FROM store_rows src
        LEFT JOIN physical_resolution physical
          ON physical.source_detail_key = src.source_detail_key
        LEFT JOIN backoffice_units backoffice
          ON backoffice.store_id = src.store_id
    )
    SELECT
        resolved.*,
        CASE
          WHEN match_method = 'PHYSICAL_CABINET' THEN NULL
          WHEN extra_type <> '电表收费' THEN '物业/营运收费按门店归入后台部门收益逻辑柜位'
          WHEN candidate_unit_count > 1 THEN '电表摘要命中多个柜位，暂归入后台部门收益逻辑柜位'
          ELSE '电表摘要未唯一命中柜位，暂归入后台部门收益逻辑柜位'
        END AS match_reason
    FROM resolved;

    DELETE FROM revenue_extra_receipts receipt
    WHERE receipt.source_type = 'NC6051'
      AND receipt.revenue_month BETWEEN TO_CHAR(v_start_month, 'YYYY-MM')
                                    AND TO_CHAR(v_end_month, 'YYYY-MM');

    INSERT INTO revenue_extra_receipts (
        store_id,
        floor_id,
        unit_id,
        unit_code,
        revenue_date,
        extra_type,
        amount,
        receipt_date,
        voucher_no,
        source_group_code,
        source_group_name,
        remark,
        status,
        confirmed_at,
        source_type,
        source_detail_key,
        source_voucher_id,
        source_subject_code,
        source_department_code,
        source_department_name,
        source_explanation,
        match_method,
        match_status,
        match_reason,
        etl_batch_id,
        raw_payload,
        source_updated_at,
        updated_at
    )
    SELECT
        store_id,
        floor_id,
        unit_id,
        unit_code,
        revenue_date,
        extra_type,
        amount,
        revenue_date,
        pk_voucher,
        matched_group_code,
        COALESCE(matched_group_name, cabinet_name, department_name),
        explanation,
        'CONFIRMED',
        NOW(),
        'NC6051',
        source_detail_key,
        pk_voucher,
        subject_code,
        department_code,
        department_name,
        explanation,
        match_method,
        match_status,
        match_reason,
        v_batch_id,
        JSONB_BUILD_OBJECT(
            'pk_detail', pk_detail,
            'pk_voucher', pk_voucher,
            'pk_corp', pk_corp,
            'store_code', store_code,
            'account_year', account_year,
            'account_period', account_period,
            'subject_code', subject_code,
            'department_code', department_code,
            'department_name', department_name,
            'explanation', explanation,
            'debit_amount', debit_amount,
            'credit_amount', credit_amount,
            'cabinet_name', cabinet_name,
            'candidate_unit_count', candidate_unit_count
        ),
        load_date,
        NOW()
    FROM tmp_nc_6051_extra_receipts
    WHERE unit_id IS NOT NULL
    ON CONFLICT (source_type, source_detail_key)
      WHERE source_detail_key IS NOT NULL
    DO UPDATE SET
        store_id = EXCLUDED.store_id,
        floor_id = EXCLUDED.floor_id,
        unit_id = EXCLUDED.unit_id,
        unit_code = EXCLUDED.unit_code,
        revenue_date = EXCLUDED.revenue_date,
        extra_type = EXCLUDED.extra_type,
        amount = EXCLUDED.amount,
        receipt_date = EXCLUDED.receipt_date,
        voucher_no = EXCLUDED.voucher_no,
        source_group_code = EXCLUDED.source_group_code,
        source_group_name = EXCLUDED.source_group_name,
        remark = EXCLUDED.remark,
        status = 'CONFIRMED',
        confirmed_at = NOW(),
        source_voucher_id = EXCLUDED.source_voucher_id,
        source_subject_code = EXCLUDED.source_subject_code,
        source_department_code = EXCLUDED.source_department_code,
        source_department_name = EXCLUDED.source_department_name,
        source_explanation = EXCLUDED.source_explanation,
        match_method = EXCLUDED.match_method,
        match_status = EXCLUDED.match_status,
        match_reason = EXCLUDED.match_reason,
        etl_batch_id = EXCLUDED.etl_batch_id,
        raw_payload = EXCLUDED.raw_payload,
        source_updated_at = EXCLUDED.source_updated_at,
        updated_at = NOW();

    GET DIAGNOSTICS v_inserted_rows = ROW_COUNT;

    RETURN QUERY
    SELECT
        (SELECT COUNT(*) FROM tmp_nc_6051_extra_receipts),
        v_inserted_rows,
        (SELECT COUNT(*) FROM tmp_nc_6051_extra_receipts WHERE match_method = 'PHYSICAL_CABINET'),
        (SELECT COUNT(*) FROM tmp_nc_6051_extra_receipts WHERE match_method = 'BACKOFFICE_FALLBACK'),
        (SELECT COUNT(*) FROM tmp_nc_6051_extra_receipts WHERE match_method = 'UNMATCHED');
END;
$$;
"""


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE revenue_extra_receipts
          ADD COLUMN IF NOT EXISTS source_type VARCHAR(30) NOT NULL DEFAULT 'MANUAL',
          ADD COLUMN IF NOT EXISTS source_detail_key VARCHAR(100),
          ADD COLUMN IF NOT EXISTS source_voucher_id VARCHAR(100),
          ADD COLUMN IF NOT EXISTS source_subject_code VARCHAR(50),
          ADD COLUMN IF NOT EXISTS source_department_code VARCHAR(50),
          ADD COLUMN IF NOT EXISTS source_department_name VARCHAR(200),
          ADD COLUMN IF NOT EXISTS source_explanation TEXT,
          ADD COLUMN IF NOT EXISTS match_method VARCHAR(50),
          ADD COLUMN IF NOT EXISTS match_status VARCHAR(30),
          ADD COLUMN IF NOT EXISTS match_reason TEXT,
          ADD COLUMN IF NOT EXISTS etl_batch_id VARCHAR(100),
          ADD COLUMN IF NOT EXISTS raw_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
          ADD COLUMN IF NOT EXISTS source_updated_at TIMESTAMPTZ;

        CREATE UNIQUE INDEX IF NOT EXISTS ux_revenue_extra_receipts_source_row
          ON revenue_extra_receipts(source_type, source_detail_key)
          WHERE source_detail_key IS NOT NULL;

        CREATE INDEX IF NOT EXISTS ix_revenue_extra_receipts_source_month
          ON revenue_extra_receipts(source_type, revenue_month);

        CREATE TABLE IF NOT EXISTS revenue_nc_cabinet_alias (
          id BIGSERIAL PRIMARY KEY,
          store_code VARCHAR(20) NOT NULL,
          source_cabinet_name VARCHAR(200) NOT NULL,
          target_group_code VARCHAR(50) NOT NULL,
          reason TEXT,
          is_active BOOLEAN NOT NULL DEFAULT TRUE,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          CONSTRAINT uq_revenue_nc_cabinet_alias_source
            UNIQUE (store_code, source_cabinet_name)
        );

        INSERT INTO revenue_nc_cabinet_alias (
          store_code, source_cabinet_name, target_group_code, reason
        ) VALUES (
          '603',
          '熹木和牛',
          '6030116065',
          'NC 电表摘要使用旧品牌名，富基现柜组名为熹木寿喜烧厅；2026-07只读核验'
        )
        ON CONFLICT (store_code, source_cabinet_name) DO UPDATE SET
          target_group_code = EXCLUDED.target_group_code,
          reason = EXCLUDED.reason,
          is_active = TRUE,
          updated_at = NOW();

        COMMENT ON TABLE revenue_extra_receipts IS
          '其他收益自动明细；NC6051 电表、物业、营运收费自动写入，手工补收不再进入收益';
        COMMENT ON COLUMN revenue_extra_receipts.source_type IS
          '来源类型：NC6051 为自动同步，MANUAL 为历史手工数据';
        COMMENT ON COLUMN revenue_extra_receipts.source_detail_key IS
          '来源明细稳定唯一键；NC6051 使用 PK_DETAIL，缺失时使用业务字段 MD5';
        COMMENT ON COLUMN revenue_extra_receipts.match_method IS
          '柜位匹配方式：PHYSICAL_CABINET、BACKOFFICE_FALLBACK、UNMATCHED';
        COMMENT ON COLUMN revenue_extra_receipts.match_reason IS
          '未唯一匹配真实柜位时的原因，禁止无依据平均分摊';
        COMMENT ON TABLE revenue_nc_cabinet_alias IS
          'NC6051 摘要柜位名与富基当前柜组名不一致时的审计别名规则';
        """
    )
    op.execute(REFRESH_FUNCTION_SQL)
    op.execute(
        """
        COMMENT ON FUNCTION refresh_nc_6051_extra_receipts(DATE, DATE, VARCHAR) IS
          '刷新月份范围内 NC6051 非富基收费到 revenue_extra_receipts；建议在 NC 凭证明细同步完成后每15分钟调用';
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP FUNCTION IF EXISTS refresh_nc_6051_extra_receipts(DATE, DATE, VARCHAR)"
    )
    op.execute(
        """
        DROP INDEX IF EXISTS ix_revenue_extra_receipts_source_month;
        DROP INDEX IF EXISTS ux_revenue_extra_receipts_source_row;
        DROP TABLE IF EXISTS revenue_nc_cabinet_alias;
        ALTER TABLE revenue_extra_receipts
          DROP COLUMN IF EXISTS source_updated_at,
          DROP COLUMN IF EXISTS raw_payload,
          DROP COLUMN IF EXISTS etl_batch_id,
          DROP COLUMN IF EXISTS match_reason,
          DROP COLUMN IF EXISTS match_status,
          DROP COLUMN IF EXISTS match_method,
          DROP COLUMN IF EXISTS source_explanation,
          DROP COLUMN IF EXISTS source_department_name,
          DROP COLUMN IF EXISTS source_department_code,
          DROP COLUMN IF EXISTS source_subject_code,
          DROP COLUMN IF EXISTS source_voucher_id,
          DROP COLUMN IF EXISTS source_detail_key,
          DROP COLUMN IF EXISTS source_type;
        """
    )
