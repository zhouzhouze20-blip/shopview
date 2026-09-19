"""Reproducible analysis for the 2026-08-14 to 2026-08-19 B/E/H/M coupon campaign.

The campaign cohort is identified by store, coupon type and coupon validity
window.  This is deliberate: the source promotion id is zero on the relevant
coupon logs and 36% of the coupons were issued before the campaign opened.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text


STORE_ID = "601"
START_DATE = "2026-08-14"
END_DATE = "2026-08-19"
COUPON_TYPES = ("B", "E", "H", "M")


COUPON_KPI_SQL = r"""
WITH cfg(coupon_type, coupon_name, face_value, threshold_amount) AS (
  VALUES ('B','会员专属券',50::numeric,600::numeric),
         ('E','中心专享券',100::numeric,1000::numeric),
         ('H','品类券（穿着）',200::numeric,2000::numeric),
         ('M','中心福利券',20::numeric,100::numeric)
), issue AS MATERIALIZED (
  SELECT UPPER(TRIM(l.tcfljetype)) coupon_type,
         COUNT(*) issue_count,
         COUNT(DISTINCT UPPER(TRIM(l.tcflvipno))) issued_members,
         SUM(ABS(COALESCE(l.tcflmoney,0))) issued_amount,
         COUNT(*) FILTER (WHERE l.tcfldate::date < CAST(:start_date AS date)) prelaunch_issue_count
  FROM tktcardfqlog l
  WHERE TRIM(l.tcflmkt)=:store_id
    AND UPPER(TRIM(l.tcfljetype)) IN ('B','E','H','M')
    AND l.tcflzy='M'
    AND l.tcflstartdate::date=CAST(:start_date AS date)
    AND l.tcflenddate::date=CAST(:end_date AS date)
    AND l.tcfldate::date <= CAST(:end_date AS date)
  GROUP BY 1
), member_flow AS MATERIALIZED (
  SELECT UPPER(TRIM(l.tcfljetype)) coupon_type,
         UPPER(TRIM(l.tcflvipno)) member_no,
         BOOL_OR(l.tcflzy='O') used,
         SUM(CASE WHEN l.tcflzy='O' THEN ABS(COALESCE(l.tcflmoney,0))
                  WHEN l.tcflzy='P' THEN -ABS(COALESCE(l.tcflmoney,0)) ELSE 0 END) net_amount
  FROM tktcardfqlog l
  WHERE TRIM(l.tcflmkt)=:store_id
    AND UPPER(TRIM(l.tcfljetype)) IN ('B','E','H','M')
    AND l.tcflzy IN ('O','P')
    AND l.tcflstartdate::date=CAST(:start_date AS date)
    AND l.tcflenddate::date=CAST(:end_date AS date)
    AND l.tcfldate::date BETWEEN CAST(:start_date AS date) AND CAST(:end_date AS date)
  GROUP BY 1,2
), used_member AS MATERIALIZED (
  SELECT coupon_type, member_no
  FROM member_flow WHERE used
), prior_active AS MATERIALIZED (
  SELECT DISTINCT UPPER(TRIM(h.hykh)) member_no
  FROM salehead h
  JOIN (SELECT DISTINCT member_no FROM used_member) u
    ON UPPER(TRIM(COALESCE(h.hykh,'')))=u.member_no
  WHERE h.mkt=:store_id
    AND h.rqsj::date >= CAST(:start_date AS date)-INTERVAL '90 day'
    AND h.rqsj::date < CAST(:start_date AS date)
), member_stats AS (
  SELECT u.coupon_type,
         COUNT(*) used_members,
         COUNT(*) FILTER (WHERE m.admission_date::date BETWEEN CAST(:start_date AS date) AND CAST(:end_date AS date)) new_used_members,
         COUNT(*) FILTER (WHERE COALESCE(TRIM(m.is_star_diamond_member),'')='星钻会员') star_used_members,
         COUNT(*) FILTER (WHERE p.member_no IS NOT NULL) prior_90d_active_members
  FROM used_member u
  LEFT JOIN fj_dw_member_dim m ON UPPER(TRIM(m.customer_no))=u.member_no
  LEFT JOIN prior_active p ON p.member_no=u.member_no
  GROUP BY 1
), log_bill_type AS MATERIALIZED (
  SELECT UPPER(TRIM(l.tcfljetype)) coupon_type, l.tcflzy action_code,
         h.billno, SUM(ABS(COALESCE(l.tcflmoney,0))) coupon_amount
  FROM tktcardfqlog l
  JOIN salehead h ON h.mkt=TRIM(l.tcflmkt)
                 AND h.syjh=l.tcflsyjid
                 AND l.tcflinvno ~ '^[0-9]+$'
                 AND h.fphm=l.tcflinvno::numeric
                 AND h.rqsj::date=l.tcfldate::date
  WHERE TRIM(l.tcflmkt)=:store_id
    AND UPPER(TRIM(l.tcfljetype)) IN ('B','E','H','M')
    AND l.tcflzy IN ('O','P')
    AND l.tcflstartdate::date=CAST(:start_date AS date)
    AND l.tcflenddate::date=CAST(:end_date AS date)
    AND l.tcfldate::date BETWEEN CAST(:start_date AS date) AND CAST(:end_date AS date)
  GROUP BY 1,2,3
), allocation AS (
  SELECT *, coupon_amount/NULLIF(SUM(coupon_amount) OVER(PARTITION BY billno,action_code),0) share
  FROM log_bill_type
), line_alloc AS (
  SELECT a.coupon_type,a.action_code,a.billno,
         COALESCE(s.sglxssr,0)*a.share sales_amount,
         COALESCE(s.sgln2,0)*a.share gross_profit
  FROM allocation a JOIN salegoodslist s ON s.sglbillno=a.billno
), sales_stats AS (
  SELECT coupon_type,
         SUM(sales_amount) FILTER (WHERE action_code='O') gross_linked_sales,
         SUM(sales_amount) FILTER (WHERE action_code='P') linked_return_sales,
         SUM(sales_amount) net_linked_sales,
         SUM(gross_profit) net_linked_gross_profit
  FROM line_alloc GROUP BY 1
), flow_stats AS (
  SELECT c.coupon_type,
         COUNT(DISTINCT l.billno) FILTER (WHERE l.action_code='O') use_tickets,
         COUNT(DISTINCT l.billno) FILTER (WHERE l.action_code='P') return_tickets,
         SUM(l.coupon_amount) FILTER (WHERE l.action_code='O') gross_coupon_amount,
         SUM(l.coupon_amount) FILTER (WHERE l.action_code='P') returned_coupon_amount
  FROM cfg c LEFT JOIN log_bill_type l ON l.coupon_type=c.coupon_type
  GROUP BY 1
), ticket_values AS (
  SELECT l.coupon_type,l.billno,h.ysje,
         SUM(COALESCE(s.sglxssr,0)) full_ticket_sales
  FROM log_bill_type l
  JOIN salehead h ON h.billno=l.billno
  JOIN salegoodslist s ON s.sglbillno=l.billno
  WHERE l.action_code='O'
  GROUP BY 1,2,3
), ticket_stats AS (
  SELECT t.coupon_type,
         AVG(t.full_ticket_sales) avg_full_ticket_sales,
         PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY t.full_ticket_sales) median_full_ticket_sales,
         COUNT(*) FILTER (WHERE t.ysje < c.threshold_amount) below_threshold_tickets
  FROM ticket_values t JOIN cfg c USING(coupon_type)
  GROUP BY 1
)
SELECT c.coupon_type,c.coupon_name,c.face_value,c.threshold_amount,
       i.issue_count,i.issued_members,i.issued_amount,i.prelaunch_issue_count,
       f.use_tickets,f.return_tickets,
       ROUND((COALESCE(f.gross_coupon_amount,0)/c.face_value)::numeric,0) gross_used_units,
       ROUND((COALESCE(f.returned_coupon_amount,0)/c.face_value)::numeric,0) returned_units,
       ROUND(((COALESCE(f.gross_coupon_amount,0)-COALESCE(f.returned_coupon_amount,0))/c.face_value)::numeric,0) net_used_units,
       COALESCE(f.gross_coupon_amount,0) gross_coupon_amount,
       COALESCE(f.returned_coupon_amount,0) returned_coupon_amount,
       COALESCE(f.gross_coupon_amount,0)-COALESCE(f.returned_coupon_amount,0) net_coupon_amount,
       ms.used_members,
       ROUND(100.0*ms.used_members/NULLIF(i.issued_members,0),2) member_redemption_rate_pct,
       ms.new_used_members,ms.prior_90d_active_members,ms.star_used_members,
       s.gross_linked_sales,s.linked_return_sales,s.net_linked_sales,s.net_linked_gross_profit,
       ROUND(100.0*(COALESCE(f.gross_coupon_amount,0)-COALESCE(f.returned_coupon_amount,0))/NULLIF(s.net_linked_sales,0),2) coupon_to_sales_pct,
       t.avg_full_ticket_sales,t.median_full_ticket_sales,t.below_threshold_tickets
FROM cfg c
LEFT JOIN issue i USING(coupon_type)
LEFT JOIN flow_stats f USING(coupon_type)
LEFT JOIN member_stats ms USING(coupon_type)
LEFT JOIN sales_stats s USING(coupon_type)
LEFT JOIN ticket_stats t USING(coupon_type)
ORDER BY c.coupon_type
"""


MEMBER_LEVEL_SQL = r"""
WITH issued AS MATERIALIZED (
  SELECT DISTINCT UPPER(TRIM(l.tcflvipno)) member_no
  FROM tktcardfqlog l
  WHERE TRIM(l.tcflmkt)=:store_id
    AND UPPER(TRIM(l.tcfljetype)) IN ('B','E','H','M') AND l.tcflzy='M'
    AND l.tcflstartdate::date=CAST(:start_date AS date)
    AND l.tcflenddate::date=CAST(:end_date AS date)
    AND l.tcfldate::date <= CAST(:end_date AS date)
), used AS MATERIALIZED (
  SELECT DISTINCT UPPER(TRIM(l.tcflvipno)) member_no
  FROM tktcardfqlog l
  WHERE TRIM(l.tcflmkt)=:store_id
    AND UPPER(TRIM(l.tcfljetype)) IN ('B','E','H','M') AND l.tcflzy='O'
    AND l.tcflstartdate::date=CAST(:start_date AS date)
    AND l.tcflenddate::date=CAST(:end_date AS date)
    AND l.tcfldate::date BETWEEN CAST(:start_date AS date) AND CAST(:end_date AS date)
), log_bill_holder AS MATERIALIZED (
  SELECT UPPER(TRIM(l.tcflvipno)) member_no,l.tcflzy action_code,h.billno,
         SUM(ABS(COALESCE(l.tcflmoney,0))) coupon_amount
  FROM tktcardfqlog l
  JOIN salehead h ON h.mkt=TRIM(l.tcflmkt) AND h.syjh=l.tcflsyjid
                 AND l.tcflinvno ~ '^[0-9]+$' AND h.fphm=l.tcflinvno::numeric
                 AND h.rqsj::date=l.tcfldate::date
  WHERE TRIM(l.tcflmkt)=:store_id
    AND UPPER(TRIM(l.tcfljetype)) IN ('B','E','H','M') AND l.tcflzy IN ('O','P')
    AND l.tcflstartdate::date=CAST(:start_date AS date)
    AND l.tcflenddate::date=CAST(:end_date AS date)
    AND l.tcfldate::date BETWEEN CAST(:start_date AS date) AND CAST(:end_date AS date)
  GROUP BY 1,2,3
), alloc AS (
  SELECT *,coupon_amount/NULLIF(SUM(coupon_amount) OVER(PARTITION BY billno,action_code),0) share
  FROM log_bill_holder
), member_sales AS (
  SELECT a.member_no,SUM(COALESCE(s.sglxssr,0)*a.share) net_linked_sales
  FROM alloc a JOIN salegoodslist s ON s.sglbillno=a.billno GROUP BY 1
), prior_active AS MATERIALIZED (
  SELECT DISTINCT UPPER(TRIM(h.hykh)) member_no
  FROM salehead h JOIN used u ON UPPER(TRIM(COALESCE(h.hykh,'')))=u.member_no
  WHERE h.mkt=:store_id
    AND h.rqsj::date >= CAST(:start_date AS date)-INTERVAL '90 day'
    AND h.rqsj::date < CAST(:start_date AS date)
), member_base AS (
  SELECT i.member_no,
         COALESCE(NULLIF(TRIM(m.customer_level),''),'未识别') customer_level,
         m.admission_date::date admission_date,
         COALESCE(TRIM(m.is_star_diamond_member),'') is_star,
         (u.member_no IS NOT NULL) used,
         COALESCE(ms.net_linked_sales,0) net_linked_sales,
         (p.member_no IS NOT NULL) prior_active
  FROM issued i
  LEFT JOIN fj_dw_member_dim m ON UPPER(TRIM(m.customer_no))=i.member_no
  LEFT JOIN used u USING(member_no)
  LEFT JOIN member_sales ms USING(member_no)
  LEFT JOIN prior_active p USING(member_no)
)
SELECT customer_level,COUNT(*) issued_members,COUNT(*) FILTER(WHERE used) used_members,
       ROUND(100.0*COUNT(*) FILTER(WHERE used)/NULLIF(COUNT(*),0),2) member_redemption_rate_pct,
       SUM(net_linked_sales) net_linked_sales,
       SUM(net_linked_sales)/NULLIF(COUNT(*) FILTER(WHERE used),0) sales_per_used_member,
       COUNT(*) FILTER(WHERE used AND admission_date BETWEEN CAST(:start_date AS date) AND CAST(:end_date AS date)) new_used_members,
       COUNT(*) FILTER(WHERE used AND prior_active) prior_90d_active_members,
       COUNT(*) FILTER(WHERE used AND is_star='星钻会员') star_used_members
FROM member_base GROUP BY 1
ORDER BY member_redemption_rate_pct DESC,customer_level
"""


CROSS_SALES_SQL = r"""
WITH manaframe_groups AS (
  SELECT mf.mfcode group_code,mf.mfcname group_name,
         dept.mfcode department_code,dept.mfcname department_name
  FROM manaframe mf LEFT JOIN manaframe dept
    ON UPPER(TRIM(COALESCE(mf.mfpcode,'')))=UPPER(TRIM(COALESCE(dept.mfcode,'')))
), log_bill_type AS MATERIALIZED (
  SELECT UPPER(TRIM(l.tcfljetype)) coupon_type,l.tcflzy action_code,h.billno,
         SUM(ABS(COALESCE(l.tcflmoney,0))) coupon_amount
  FROM tktcardfqlog l JOIN salehead h
    ON h.mkt=TRIM(l.tcflmkt) AND h.syjh=l.tcflsyjid
   AND l.tcflinvno ~ '^[0-9]+$' AND h.fphm=l.tcflinvno::numeric
   AND h.rqsj::date=l.tcfldate::date
  WHERE TRIM(l.tcflmkt)=:store_id
    AND UPPER(TRIM(l.tcfljetype)) IN ('B','E','H','M') AND l.tcflzy IN ('O','P')
    AND l.tcflstartdate::date=CAST(:start_date AS date)
    AND l.tcflenddate::date=CAST(:end_date AS date)
    AND l.tcfldate::date BETWEEN CAST(:start_date AS date) AND CAST(:end_date AS date)
  GROUP BY 1,2,3
), allocation AS (
  SELECT *,coupon_amount/NULLIF(SUM(coupon_amount) OVER(PARTITION BY billno,action_code),0) share
  FROM log_bill_type
), line_alloc AS (
  SELECT a.coupon_type,a.billno,
         COALESCE(NULLIF(TRIM(s.sglppcode),''),'未标识') brand_code,
         COALESCE(NULLIF(TRIM(cb.cbcname),''),'未标识品牌') brand_name,
         COALESCE(NULLIF(TRIM(s.sglcatid),''),'未标识') category_code,
         COALESCE(NULLIF(TRIM(gc.catcname),''),'未标识品类') category_name,
         COALESCE(NULLIF(TRIM(mg.department_code),''),'未归属') department_code,
         COALESCE(NULLIF(TRIM(mg.department_name),''),'未归属部门') department_name,
         COALESCE(s.sglxssr,0)*a.share sales_amount,
         COALESCE(s.sgln2,0)*a.share gross_profit
  FROM allocation a JOIN salegoodslist s ON s.sglbillno=a.billno
  LEFT JOIN codebrand cb ON UPPER(TRIM(COALESCE(cb.cbid,'')))=UPPER(TRIM(COALESCE(s.sglppcode,'')))
  LEFT JOIN goodscat gc ON UPPER(TRIM(COALESCE(gc.catcode,'')))=UPPER(TRIM(COALESCE(s.sglcatid,'')))
  LEFT JOIN manaframe_groups mg ON UPPER(TRIM(COALESCE(mg.group_code,'')))=UPPER(TRIM(COALESCE(s.sglmfid,'')))
), dims AS (
  SELECT coupon_type,'品牌' dimension_type,brand_code dimension_code,brand_name dimension_name,billno,sales_amount,gross_profit FROM line_alloc
  UNION ALL SELECT coupon_type,'品类',category_code,category_name,billno,sales_amount,gross_profit FROM line_alloc
  UNION ALL SELECT coupon_type,'部门',department_code,department_name,billno,sales_amount,gross_profit FROM line_alloc
), agg AS (
  SELECT coupon_type,dimension_type,dimension_code,dimension_name,COUNT(DISTINCT billno) tickets,
         SUM(sales_amount) net_sales,SUM(gross_profit) net_gross_profit
  FROM dims GROUP BY 1,2,3,4
), ranked AS (
  SELECT *,SUM(net_sales) OVER(PARTITION BY coupon_type,dimension_type) coupon_total_sales,
         DENSE_RANK() OVER(PARTITION BY coupon_type,dimension_type ORDER BY net_sales DESC) rank_in_coupon
  FROM agg
)
SELECT coupon_type,dimension_type,dimension_code,dimension_name,tickets,net_sales,net_gross_profit,
       100.0*net_sales/NULLIF(coupon_total_sales,0) sales_share_pct,rank_in_coupon
FROM ranked WHERE rank_in_coupon<=10
ORDER BY dimension_type,coupon_type,rank_in_coupon,dimension_code
"""


QUALITY_SQL = r"""
WITH issue AS (
  SELECT * FROM tktcardfqlog l
  WHERE TRIM(l.tcflmkt)=:store_id AND UPPER(TRIM(l.tcfljetype)) IN ('B','E','H','M') AND l.tcflzy='M'
    AND l.tcflstartdate::date=CAST(:start_date AS date) AND l.tcflenddate::date=CAST(:end_date AS date)
    AND l.tcfldate::date<=CAST(:end_date AS date)
), flow AS (
  SELECT l.*,h.billno,h.hykh buyer_member
  FROM tktcardfqlog l LEFT JOIN salehead h
    ON h.mkt=TRIM(l.tcflmkt) AND h.syjh=l.tcflsyjid
   AND l.tcflinvno ~ '^[0-9]+$' AND h.fphm=l.tcflinvno::numeric
   AND h.rqsj::date=l.tcfldate::date
  WHERE TRIM(l.tcflmkt)=:store_id AND UPPER(TRIM(l.tcfljetype)) IN ('B','E','H','M') AND l.tcflzy IN ('O','P')
    AND l.tcflstartdate::date=CAST(:start_date AS date) AND l.tcflenddate::date=CAST(:end_date AS date)
    AND l.tcfldate::date BETWEEN CAST(:start_date AS date) AND CAST(:end_date AS date)
), used_bill AS (
  SELECT billno,COUNT(DISTINCT UPPER(TRIM(tcfljetype))) coupon_type_count
  FROM flow WHERE tcflzy='O' GROUP BY 1
), used_member AS (
  SELECT DISTINCT UPPER(TRIM(tcflvipno)) member_no FROM flow WHERE tcflzy='O'
), issued_member AS (
  SELECT DISTINCT UPPER(TRIM(tcflvipno)) member_no FROM issue
)
SELECT COUNT(*) FROM issue
"""


def _quality_frame(connection: Any, params: dict[str, str]) -> pd.DataFrame:
    """Quality checks kept as small independently auditable queries."""
    q = {
        "full_issue_count": """SELECT COUNT(*) FROM tktcardfqlog WHERE TRIM(tcflmkt)=:store_id AND UPPER(TRIM(tcfljetype)) IN ('B','E','H','M') AND tcflzy='M' AND tcflstartdate::date=CAST(:start_date AS date) AND tcflenddate::date=CAST(:end_date AS date) AND tcfldate::date<=CAST(:end_date AS date)""",
        "in_period_issue_count": """SELECT COUNT(*) FROM tktcardfqlog WHERE TRIM(tcflmkt)=:store_id AND UPPER(TRIM(tcfljetype)) IN ('B','E','H','M') AND tcflzy='M' AND tcflstartdate::date=CAST(:start_date AS date) AND tcflenddate::date=CAST(:end_date AS date) AND tcfldate::date BETWEEN CAST(:start_date AS date) AND CAST(:end_date AS date)""",
        "use_tickets": """SELECT COUNT(DISTINCT h.billno) FROM tktcardfqlog l JOIN salehead h ON h.mkt=TRIM(l.tcflmkt) AND h.syjh=l.tcflsyjid AND l.tcflinvno~'^[0-9]+$' AND h.fphm=l.tcflinvno::numeric AND h.rqsj::date=l.tcfldate::date WHERE TRIM(l.tcflmkt)=:store_id AND UPPER(TRIM(l.tcfljetype)) IN ('B','E','H','M') AND l.tcflzy='O' AND l.tcflstartdate::date=CAST(:start_date AS date) AND l.tcflenddate::date=CAST(:end_date AS date) AND l.tcfldate::date BETWEEN CAST(:start_date AS date) AND CAST(:end_date AS date)""",
        "return_tickets": """SELECT COUNT(DISTINCT h.billno) FROM tktcardfqlog l JOIN salehead h ON h.mkt=TRIM(l.tcflmkt) AND h.syjh=l.tcflsyjid AND l.tcflinvno~'^[0-9]+$' AND h.fphm=l.tcflinvno::numeric AND h.rqsj::date=l.tcfldate::date WHERE TRIM(l.tcflmkt)=:store_id AND UPPER(TRIM(l.tcfljetype)) IN ('B','E','H','M') AND l.tcflzy='P' AND l.tcflstartdate::date=CAST(:start_date AS date) AND l.tcflenddate::date=CAST(:end_date AS date) AND l.tcfldate::date BETWEEN CAST(:start_date AS date) AND CAST(:end_date AS date)""",
        "multi_coupon_type_tickets": """WITH x AS (SELECT h.billno,COUNT(DISTINCT UPPER(TRIM(l.tcfljetype))) n FROM tktcardfqlog l JOIN salehead h ON h.mkt=TRIM(l.tcflmkt) AND h.syjh=l.tcflsyjid AND l.tcflinvno~'^[0-9]+$' AND h.fphm=l.tcflinvno::numeric AND h.rqsj::date=l.tcfldate::date WHERE TRIM(l.tcflmkt)=:store_id AND UPPER(TRIM(l.tcfljetype)) IN ('B','E','H','M') AND l.tcflzy='O' AND l.tcflstartdate::date=CAST(:start_date AS date) AND l.tcflenddate::date=CAST(:end_date AS date) AND l.tcfldate::date BETWEEN CAST(:start_date AS date) AND CAST(:end_date AS date) GROUP BY 1) SELECT COUNT(*) FROM x WHERE n>1""",
        "holder_buyer_mismatch_tickets": """SELECT COUNT(DISTINCT h.billno) FROM tktcardfqlog l JOIN salehead h ON h.mkt=TRIM(l.tcflmkt) AND h.syjh=l.tcflsyjid AND l.tcflinvno~'^[0-9]+$' AND h.fphm=l.tcflinvno::numeric AND h.rqsj::date=l.tcfldate::date WHERE TRIM(l.tcflmkt)=:store_id AND UPPER(TRIM(l.tcfljetype)) IN ('B','E','H','M') AND l.tcflzy='O' AND l.tcflstartdate::date=CAST(:start_date AS date) AND l.tcflenddate::date=CAST(:end_date AS date) AND l.tcfldate::date BETWEEN CAST(:start_date AS date) AND CAST(:end_date AS date) AND UPPER(TRIM(COALESCE(l.tcflvipno,'')))<>UPPER(TRIM(COALESCE(h.hykh,'')))""",
        "use_members_not_issued": """WITH i AS (SELECT DISTINCT UPPER(TRIM(tcflvipno)) m FROM tktcardfqlog WHERE TRIM(tcflmkt)=:store_id AND UPPER(TRIM(tcfljetype)) IN ('B','E','H','M') AND tcflzy='M' AND tcflstartdate::date=CAST(:start_date AS date) AND tcflenddate::date=CAST(:end_date AS date)),u AS (SELECT DISTINCT UPPER(TRIM(tcflvipno)) m FROM tktcardfqlog WHERE TRIM(tcflmkt)=:store_id AND UPPER(TRIM(tcfljetype)) IN ('B','E','H','M') AND tcflzy='O' AND tcflstartdate::date=CAST(:start_date AS date) AND tcflenddate::date=CAST(:end_date AS date) AND tcfldate::date BETWEEN CAST(:start_date AS date) AND CAST(:end_date AS date)) SELECT COUNT(*) FROM u LEFT JOIN i USING(m) WHERE i.m IS NULL""",
    }
    values = {name: connection.execute(text(sql), params).scalar_one() for name, sql in q.items()}
    values["prelaunch_issue_count"] = values["full_issue_count"] - values["in_period_issue_count"]
    values["prelaunch_issue_share_pct"] = 100.0 * values["prelaunch_issue_count"] / values["full_issue_count"]
    return pd.DataFrame([values])


def load_frames(database_url: str | None = None) -> dict[str, pd.DataFrame]:
    """Load all report datasets from the current ShopView datasource."""
    url = database_url or os.getenv("DATABASE_URL")
    if not url:
        repo_root = Path(__file__).resolve().parents[1]
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        from python_app.models.database import DATABASE_URL as configured_url

        url = configured_url
    params = {"store_id": STORE_ID, "start_date": START_DATE, "end_date": END_DATE}
    engine = create_engine(url)
    with engine.connect() as connection:
        frames = {
            "coupon_kpis": pd.read_sql(text(COUPON_KPI_SQL), connection, params=params),
            "member_levels": pd.read_sql(text(MEMBER_LEVEL_SQL), connection, params=params),
            "cross_sales": pd.read_sql(text(CROSS_SALES_SQL), connection, params=params),
            "quality": _quality_frame(connection, params),
        }
    for frame in frames.values():
        for column in frame.columns:
            if frame[column].dtype == object:
                try:
                    frame[column] = pd.to_numeric(frame[column])
                except (TypeError, ValueError):
                    pass
    return frames


def validate_frames(frames: dict[str, pd.DataFrame]) -> None:
    """Fail fast if core totals drift from the independently reconciled values."""
    kpi = frames["coupon_kpis"].set_index("coupon_type")
    quality = frames["quality"].iloc[0]
    assert list(kpi.index) == ["B", "E", "H", "M"]
    assert int(kpi["issue_count"].sum()) == 1925
    assert round(float(kpi["net_coupon_amount"].sum()), 2) == 71590.00
    assert round(float(kpi["net_linked_sales"].sum()), 2) == 1030178.98
    assert int(quality["use_tickets"]) == 671
    assert int(quality["prelaunch_issue_count"]) == 694
    assert int(quality["use_members_not_issued"]) == 0


if __name__ == "__main__":
    result = load_frames()
    validate_frames(result)
    for name, frame in result.items():
        print(f"\n[{name}]\n{frame.to_string(index=False)}")
