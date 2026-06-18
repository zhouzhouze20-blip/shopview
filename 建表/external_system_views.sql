-- Views for external systems.
-- Re-run safely.

DROP VIEW IF EXISTS public.v_shop_unit_basic;
CREATE OR REPLACE VIEW public.v_shop_unit_basic AS
SELECT DISTINCT
    bu.id AS id,
    bu.id AS unit_id,
    COALESCE(s.store_code, fs.store_code, f.store_code) AS store_code,
    COALESCE(s.store_name, fs.store_name, f.store_code) AS store_name,
    f.floor_code AS floor_code,
    f.name AS floor_name,
    bu.unit_code AS unit_code
FROM public.business_units bu
LEFT JOIN public.floors f ON f.id = bu.floor_id
LEFT JOIN public.stores s ON s.store_id = bu.store_id
LEFT JOIN public.stores fs ON fs.store_code = f.store_code
WHERE COALESCE(TRIM(bu.unit_code), '') <> '';

COMMENT ON VIEW public.v_shop_unit_basic IS 'External view: store, floor, and shop unit code.';
COMMENT ON COLUMN public.v_shop_unit_basic.id IS '主键ID，对应柜位ID';
COMMENT ON COLUMN public.v_shop_unit_basic.unit_id IS '柜位ID';
COMMENT ON COLUMN public.v_shop_unit_basic.store_code IS '门店编码';
COMMENT ON COLUMN public.v_shop_unit_basic.store_name IS '门店名称';
COMMENT ON COLUMN public.v_shop_unit_basic.floor_code IS '楼层编码';
COMMENT ON COLUMN public.v_shop_unit_basic.floor_name IS '楼层名称';
COMMENT ON COLUMN public.v_shop_unit_basic.unit_code IS '柜位号';

DROP VIEW IF EXISTS public.v_shop_unit_contract;
CREATE OR REPLACE VIEW public.v_shop_unit_contract AS
WITH cmf_summary AS (
    SELECT
        cmf.cmfcontno,
        MIN(cmf.cmfeffdate)::date AS range_start_date,
        MAX(cmf.cmflapdate)::date AS range_end_date,
        STRING_AGG(DISTINCT NULLIF(TRIM(COALESCE(cmf.cmfmemo, '')), ''), '; ') AS scope_memos
    FROM public.contmanaframe cmf
    GROUP BY cmf.cmfcontno
)
SELECT DISTINCT
    b.id AS id,
    COALESCE(s.store_code, fs.store_code, f.store_code) AS store_code,
    COALESCE(s.store_name, fs.store_name, f.store_code) AS store_name,
    bu.unit_code AS unit_code,
    b.contract_id AS contract_id,
    COALESCE(b.start_date, cm.cmeffdate::date, cmf_summary.range_start_date) AS contract_start_date,
    COALESCE(b.end_date, cm.cmlapdate::date, cmf_summary.range_end_date) AS contract_end_date,
    CASE COALESCE(NULLIF(TRIM(bu.contract_mode), ''), 'EXCLUSIVE')
        WHEN 'SHARED' THEN '共享经营'
        WHEN 'EXCLUSIVE' THEN '独占经营'
        ELSE COALESCE(NULLIF(TRIM(bu.contract_mode), ''), '独占经营')
    END AS contract_business_restriction
FROM public.business_unit_binding b
JOIN public.business_units bu ON bu.id = b.shop_unit_id
LEFT JOIN public.floors f ON f.id = bu.floor_id
LEFT JOIN public.stores s ON s.store_id = bu.store_id
LEFT JOIN public.stores fs ON fs.store_code = f.store_code
LEFT JOIN public.contmain cm ON UPPER(TRIM(COALESCE(cm.cmcontno, ''))) = UPPER(TRIM(COALESCE(b.contract_id, '')))
LEFT JOIN cmf_summary ON UPPER(TRIM(COALESCE(cmf_summary.cmfcontno, ''))) = UPPER(TRIM(COALESCE(b.contract_id, '')))
WHERE COALESCE(TRIM(b.contract_id), '') <> ''
  AND COALESCE(TRIM(bu.unit_code), '') <> '';

COMMENT ON VIEW public.v_shop_unit_contract IS 'External view: store, shop unit, contract dates, and business restriction.';
COMMENT ON COLUMN public.v_shop_unit_contract.id IS '主键ID，对应柜位合同绑定ID';
COMMENT ON COLUMN public.v_shop_unit_contract.store_code IS '门店编码';
COMMENT ON COLUMN public.v_shop_unit_contract.store_name IS '门店名称';
COMMENT ON COLUMN public.v_shop_unit_contract.unit_code IS '柜位号';
COMMENT ON COLUMN public.v_shop_unit_contract.contract_id IS '合同号';
COMMENT ON COLUMN public.v_shop_unit_contract.contract_start_date IS '合同开始时间';
COMMENT ON COLUMN public.v_shop_unit_contract.contract_end_date IS '合同结束时间';
COMMENT ON COLUMN public.v_shop_unit_contract.contract_business_restriction IS '合同经营限制';
