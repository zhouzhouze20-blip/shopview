-- Physical brand-counter summary; maintained in the same transaction as detail writes.
CREATE TABLE IF NOT EXISTS public.inventory_turnover_brand_monthly (
 financial_month varchar(7) NOT NULL, store_code varchar(20) NOT NULL,
 department_code varchar(20) NOT NULL, group_code varchar(20) NOT NULL,
 store_id integer, store_name text, department_name text, group_name text,
 category_code text, category_name text, floor_code text,
 period_start date, period_end date, as_of_date date, elapsed_days integer,
 inventory_days integer, sales_days integer,
 supplier_count integer, detail_count integer, exception_count integer,
 sales_quantity numeric, sales_revenue numeric, sales_cost_ex_tax numeric,
 ending_quantity numeric, ending_cost_ex_tax numeric, average_cost_ex_tax numeric,
 turnover_days numeric, turnover_rate numeric, stock_sales_ratio numeric, stock_cover_days numeric,
 data_status text NOT NULL, updated_at timestamptz NOT NULL, refreshed_at timestamptz NOT NULL,
 PRIMARY KEY(financial_month,store_code,department_code,group_code)
);
CREATE INDEX IF NOT EXISTS idx_inventory_turnover_brand_filter
 ON public.inventory_turnover_brand_monthly(store_code,department_code,financial_month);
COMMENT ON TABLE public.inventory_turnover_brand_monthly IS
 '品牌柜组周转实体汇总表：明细写入后事务内同步；同柜组供应商合并，非商品档案品牌口径；金额不含税';
COMMENT ON COLUMN public.inventory_turnover_brand_monthly.updated_at IS '所含明细最早更新时间';
COMMENT ON COLUMN public.inventory_turnover_brand_monthly.refreshed_at IS '本汇总行实际刷新时间';
COMMENT ON COLUMN public.inventory_turnover_brand_monthly.group_code IS '品牌柜组编码，非商品品牌编码';
COMMENT ON COLUMN public.inventory_turnover_brand_monthly.stock_sales_ratio IS '期末不含税成本/期间不含税销售成本';

CREATE OR REPLACE FUNCTION public.inventory_turnover_brand_rows(p_month text)
RETURNS SETOF public.inventory_turnover_brand_monthly LANGUAGE sql STABLE AS $fn$
 WITH aggregates AS (
 SELECT financial_month,store_code,coalesce(department_code,'') AS department_code,group_code,
 min(store_id) AS store_id,min(store_name) AS store_name,min(department_name) AS department_name,
 min(group_name) AS group_name,min(category_code) AS category_code,min(category_name) AS category_name,min(floor_code) AS floor_code,
 min(period_start) AS period_start,min(period_end) AS period_end,min(as_of_date) AS as_of_date,
 min(elapsed_days) AS elapsed_days,min(inventory_days) AS inventory_days,min(sales_days) AS sales_days,
 count(DISTINCT supplier_code)::integer AS supplier_count,count(*)::integer AS detail_count,
 count(*) FILTER(WHERE data_status<>'正常')::integer AS exception_count,
 CASE WHEN count(sales_quantity)=count(*) THEN sum(sales_quantity) END AS sales_quantity,
 CASE WHEN count(sales_revenue)=count(*) THEN sum(sales_revenue) END AS sales_revenue,
 CASE WHEN count(sales_cost_ex_tax)=count(*) THEN sum(sales_cost_ex_tax) END AS sales_cost_ex_tax,
 CASE WHEN count(ending_quantity)=count(*) THEN sum(ending_quantity) END AS ending_quantity,
 CASE WHEN count(ending_cost_ex_tax)=count(*) THEN sum(ending_cost_ex_tax) END AS ending_cost_ex_tax,
 CASE WHEN count(average_cost_ex_tax)=count(*) THEN sum(average_cost_ex_tax) END AS average_cost_ex_tax,
 count(DISTINCT (period_start,period_end,as_of_date,elapsed_days))=1 AS aligned,
 string_agg(DISTINCT data_status,'；' ORDER BY data_status) FILTER(WHERE data_status<>'正常') AS statuses,
 min(updated_at) AS updated_at
 FROM public.inventory_turnover_monthly WHERE financial_month=p_month
 GROUP BY financial_month,store_code,coalesce(department_code,''),group_code
 ), valid AS (
 SELECT *,aligned AND sales_days=elapsed_days AND sales_cost_ex_tax>0 AS sales_valid
 FROM aggregates
 )
 SELECT financial_month,store_code,department_code,group_code,
 store_id,store_name,department_name,group_name,category_code,category_name,floor_code,
 period_start,period_end,as_of_date,elapsed_days,inventory_days,sales_days,
 supplier_count,detail_count,exception_count,
 sales_quantity,sales_revenue,sales_cost_ex_tax,ending_quantity,ending_cost_ex_tax,
 CASE WHEN aligned THEN average_cost_ex_tax END,
 CASE WHEN sales_valid AND average_cost_ex_tax>0 THEN average_cost_ex_tax/sales_cost_ex_tax*elapsed_days END,
 CASE WHEN sales_valid AND average_cost_ex_tax>0 THEN sales_cost_ex_tax/average_cost_ex_tax END,
 CASE WHEN sales_valid AND ending_cost_ex_tax>=0 THEN ending_cost_ex_tax/sales_cost_ex_tax END,
 CASE WHEN sales_valid AND ending_cost_ex_tax>=0 THEN ending_cost_ex_tax/sales_cost_ex_tax*elapsed_days END,
 CASE WHEN statuses IS NULL AND aligned THEN '正常'
 ELSE '明细异常：'||concat_ws('；',statuses,CASE WHEN NOT aligned THEN '明细统计期间不一致' END) END,
 updated_at,current_timestamp
 FROM valid
$fn$;

CREATE OR REPLACE FUNCTION public.refresh_inventory_turnover_brand(p_month text)
RETURNS void LANGUAGE plpgsql AS $fn$
BEGIN
 -- Serialize concurrent refreshes of the same financial month.
 PERFORM pg_advisory_xact_lock(hashtextextended('inventory_turnover_brand:'||p_month,0));
 DELETE FROM public.inventory_turnover_brand_monthly WHERE financial_month=p_month;
 INSERT INTO public.inventory_turnover_brand_monthly
 SELECT * FROM public.inventory_turnover_brand_rows(p_month);
END
$fn$;

CREATE OR REPLACE FUNCTION public.sync_inventory_turnover_brand()
RETURNS trigger LANGUAGE plpgsql AS $fn$
DECLARE month_value text;
BEGIN
 IF TG_OP='INSERT' THEN
   FOR month_value IN SELECT DISTINCT financial_month FROM new_rows ORDER BY financial_month LOOP
     PERFORM public.refresh_inventory_turnover_brand(month_value);
   END LOOP;
 ELSIF TG_OP='DELETE' THEN
   FOR month_value IN SELECT DISTINCT financial_month FROM old_rows ORDER BY financial_month LOOP
     PERFORM public.refresh_inventory_turnover_brand(month_value);
   END LOOP;
 ELSE
   FOR month_value IN SELECT financial_month FROM new_rows UNION SELECT financial_month FROM old_rows ORDER BY financial_month LOOP
     PERFORM public.refresh_inventory_turnover_brand(month_value);
   END LOOP;
 END IF;
 RETURN NULL;
END
$fn$;

DROP TRIGGER IF EXISTS turnover_brand_insert ON public.inventory_turnover_monthly;
CREATE TRIGGER turnover_brand_insert AFTER INSERT ON public.inventory_turnover_monthly
 REFERENCING NEW TABLE AS new_rows FOR EACH STATEMENT EXECUTE FUNCTION public.sync_inventory_turnover_brand();
DROP TRIGGER IF EXISTS turnover_brand_update ON public.inventory_turnover_monthly;
CREATE TRIGGER turnover_brand_update AFTER UPDATE ON public.inventory_turnover_monthly
 REFERENCING OLD TABLE AS old_rows NEW TABLE AS new_rows FOR EACH STATEMENT EXECUTE FUNCTION public.sync_inventory_turnover_brand();
DROP TRIGGER IF EXISTS turnover_brand_delete ON public.inventory_turnover_monthly;
CREATE TRIGGER turnover_brand_delete AFTER DELETE ON public.inventory_turnover_monthly
 REFERENCING OLD TABLE AS old_rows FOR EACH STATEMENT EXECUTE FUNCTION public.sync_inventory_turnover_brand();

-- Seed all already saved months; repeatable when applying the migration later.
DO $seed$
DECLARE month_value text;
BEGIN
 FOR month_value IN SELECT DISTINCT financial_month FROM public.inventory_turnover_monthly ORDER BY financial_month LOOP
   PERFORM public.refresh_inventory_turnover_brand(month_value);
 END LOOP;
END
$seed$;
