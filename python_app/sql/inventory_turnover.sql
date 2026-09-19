CREATE TABLE IF NOT EXISTS inventory_turnover_monthly (
  financial_month varchar(7) NOT NULL,
  store_code varchar(20) NOT NULL,
  group_code varchar(20) NOT NULL,
  supplier_code varchar(20) NOT NULL,
  operation_method varchar(1) NOT NULL,
  store_id integer,
  store_name text,
  department_code varchar(20),
  department_name text,
  group_name text,
  supplier_name text,
  category_code text,
  category_name text,
  floor_code text,
  period_start date NOT NULL,
  period_end date NOT NULL,
  as_of_date date NOT NULL,
  elapsed_days integer NOT NULL,
  inventory_days integer NOT NULL,
  sales_days integer NOT NULL,
  sales_quantity numeric,
  sales_revenue numeric,
  sales_cost_ex_tax numeric,
  ending_quantity numeric,
  ending_cost_ex_tax numeric,
  average_cost_ex_tax numeric,
  turnover_days numeric,
  turnover_rate numeric,
  stock_sales_ratio numeric,
  stock_cover_days numeric,
  data_status text NOT NULL,
  updated_at timestamptz NOT NULL,
  PRIMARY KEY(financial_month,store_code,group_code,supplier_code,operation_method)
);
CREATE INDEX IF NOT EXISTS idx_inventory_turnover_filter
 ON inventory_turnover_monthly(store_code,department_code,financial_month);
COMMENT ON TABLE inventory_turnover_monthly IS '商品周转月报：最新月度快照，每日重算本月及上月；存销比使用期末成本，周转率使用平均成本';
COMMENT ON COLUMN inventory_turnover_monthly.financial_month IS '财务年月YYYY-MM；沿用系统1月1-28、12月11/29-12/31，其余上月29日至当月28日规则';
COMMENT ON COLUMN inventory_turnover_monthly.sales_cost_ex_tax IS '逐行sgln13/NULLIF(1+sgljjtax,0)，不统一假定13%税率；缺税率时为空';
COMMENT ON COLUMN inventory_turnover_monthly.average_cost_ex_tax IS '期间每天库存不含税进价金额之和/已统计自然日；门店快照缺日时为空';
COMMENT ON COLUMN inventory_turnover_monthly.stock_sales_ratio IS '期末不含税库存成本/期间不含税销售成本';

CREATE OR REPLACE FUNCTION inventory_turnover_rows(p_year integer,p_month integer,p_as_of date)
RETURNS SETOF inventory_turnover_monthly LANGUAGE sql STABLE AS $fn$
WITH bounds AS (
 SELECT make_date(p_year,p_month,1) AS month_start,
        to_char(make_date(p_year,p_month,1),'YYYY-MM') AS financial_month
), period AS (
 SELECT financial_month,
   CASE WHEN p_month=1 THEN month_start
        ELSE LEAST((month_start-interval '1 month'+interval '28 days')::date,month_start) END AS start_date,
   CASE WHEN p_month=12 THEN make_date(p_year,12,31) ELSE make_date(p_year,p_month,28) END AS end_date
 FROM bounds
), period_window AS (
 SELECT *, LEAST(p_as_of,end_date) AS cutoff,
        LEAST(p_as_of,end_date)-start_date+1 AS days FROM period
 WHERE p_as_of>=start_date
), sale_rows AS MATERIALIZED (
 SELECT s.* FROM salegoodslist s CROSS JOIN period_window p
 WHERE s.sglhsrq>=p.start_date AND s.sglhsrq<p.cutoff+1
), sale_coverage AS (
 SELECT sglmarket AS store_code,count(DISTINCT sglhsrq::date)::integer AS days
 FROM sale_rows GROUP BY sglmarket
), sales AS (
 SELECT sglmarket AS store_code,sglmfid AS group_code,sglsupid AS supplier_code,sglwmid AS operation_method,
   SUM(sglsl) AS quantity,SUM(sglxssr) AS revenue,
   SUM(CASE WHEN sgln13=0 OR (sgln13 IS NULL AND sglsl=0 AND sglxssr=0) THEN 0 ELSE sgln13/NULLIF(1+sgljjtax,0) END) AS cost,
   count(*) FILTER(WHERE (sgln13 IS NULL AND (coalesce(sglsl,0)<>0 OR coalesce(sglxssr,0)<>0)) OR (coalesce(sgln13,0)<>0 AND (sgljjtax IS NULL OR sgljjtax<0 OR sgljjtax>1))) AS invalid_cost
 FROM sale_rows WHERE sglwmid IN ('1','2')
 GROUP BY sglmarket,sglmfid,sglsupid,sglwmid
), stock_rows AS MATERIALIZED (
 SELECT s.* FROM goodsstock_bak s CROSS JOIN period_window p
 WHERE s.gstdate>=p.start_date AND s.gstdate<p.cutoff+1
), stock_coverage AS (
 SELECT gstmarket AS store_code,count(DISTINCT gstdate::date)::integer AS days,
        bool_or(gstdate::date=p.cutoff) AS has_end
 FROM stock_rows CROSS JOIN period_window p GROUP BY gstmarket
), stocks AS (
 SELECT gstmarket AS store_code,gstmfid AS group_code,gstsupid AS supplier_code,gstwmid AS operation_method,
   sum(gstkcbhsjjje) AS cost_sum,
   sum(gstkcsl) FILTER(WHERE gstdate::date=p.cutoff) AS end_quantity,
   sum(gstkcbhsjjje) FILTER(WHERE gstdate::date=p.cutoff) AS end_cost
 FROM stock_rows CROSS JOIN period_window p WHERE gstwmid IN ('1','2')
 GROUP BY gstmarket,gstmfid,gstsupid,gstwmid
), keys AS (
 SELECT store_code,group_code,supplier_code,operation_method FROM sales
 UNION SELECT store_code,group_code,supplier_code,operation_method FROM stocks
 -- Re-emit former keys with zero values after upstream deletions/corrections.
 UNION SELECT r.store_code,r.group_code,r.supplier_code,r.operation_method
 FROM inventory_turnover_monthly r JOIN period_window p USING(financial_month)
), amounts AS (
 SELECT k.*,p.financial_month,p.start_date,p.end_date,p.cutoff,p.days,
   coalesce(sc.days,0) AS inventory_days,coalesce(vc.days,0) AS sales_days,
   coalesce(s.quantity,0) AS quantity,coalesce(s.revenue,0) AS revenue,
   CASE WHEN coalesce(s.invalid_cost,0)=0 THEN coalesce(s.cost,0) END AS cost,
   CASE WHEN sc.has_end THEN coalesce(i.end_quantity,0) END AS end_quantity,
   CASE WHEN sc.has_end THEN coalesce(i.end_cost,0) END AS end_cost,
   CASE WHEN sc.days=p.days THEN coalesce(i.cost_sum,0)/p.days END AS average_cost,
   coalesce(s.invalid_cost,0) AS invalid_cost
 FROM keys k CROSS JOIN period_window p
 LEFT JOIN sales s USING(store_code,group_code,supplier_code,operation_method)
 LEFT JOIN stocks i USING(store_code,group_code,supplier_code,operation_method)
 LEFT JOIN stock_coverage sc USING(store_code)
 LEFT JOIN sale_coverage vc USING(store_code)
)
SELECT a.financial_month,a.store_code,a.group_code,a.supplier_code,a.operation_method,
 st.store_id,st.store_name,coalesce(mf.mfpcode,''),coalesce(dept.mfcname,'未匹配部门'),
 mf.mfcname,sb.sbcname,mf.mfchr1,ac.category_name,mf.mflc,
 a.start_date,a.end_date,a.cutoff,a.days,a.inventory_days,a.sales_days,
 a.quantity,a.revenue,a.cost,a.end_quantity,a.end_cost,a.average_cost,
 CASE WHEN a.sales_days=a.days AND a.average_cost>0 AND a.cost>0 THEN a.average_cost/a.cost*a.days END,
 CASE WHEN a.sales_days=a.days AND a.average_cost>0 AND a.cost>0 THEN a.cost/a.average_cost END,
 CASE WHEN a.sales_days=a.days AND a.end_cost>=0 AND a.cost>0 THEN a.end_cost/a.cost END,
 CASE WHEN a.sales_days=a.days AND a.end_cost>=0 AND a.cost>0 THEN a.end_cost/a.cost*a.days END,
 coalesce(nullif(concat_ws('；',
   CASE WHEN a.inventory_days<a.days THEN '库存快照缺日' END,
   CASE WHEN a.sales_days<a.days THEN '门店销售日期不完整' END,
   CASE WHEN a.invalid_cost>0 THEN '销售成本或进项税率缺失/异常' END,
   CASE WHEN a.average_cost<=0 THEN '平均库存非正' END,
   CASE WHEN a.end_cost<0 THEN '期末库存成本为负' END,
   CASE WHEN a.cost<=0 THEN '销售成本非正' END,
   CASE WHEN st.store_id IS NULL OR dept.mfcode IS NULL THEN '门店或部门未匹配' END
 ),''),'正常'),current_timestamp
FROM amounts a
LEFT JOIN stores st ON st.store_code=a.store_code
LEFT JOIN manaframe mf ON mf.mfcode=a.group_code
LEFT JOIN manaframe dept ON dept.mfcode=mf.mfpcode
LEFT JOIN supplierbase sb ON sb.sbid=a.supplier_code
LEFT JOIN LATERAL (
 SELECT category_name FROM area_category
 WHERE upper(trim(category_code))=upper(trim(mf.mfchr1)) ORDER BY area_code,category_name LIMIT 1
) ac ON true
$fn$;

INSERT INTO permissions(permission_code,permission_name,module_code,action_code)
VALUES('sales.inventory_turnover.view','查看商品周转财务月报','sales','inventory_turnover_view')
ON CONFLICT(permission_code) DO NOTHING;
