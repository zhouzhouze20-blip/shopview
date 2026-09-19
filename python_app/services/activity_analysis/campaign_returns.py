"""Post-campaign returns are a separate observation, never a rewrite of period totals."""
from collections import defaultdict
from datetime import datetime,timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
from sqlalchemy import text

LATE_RETURN_SQL="""
SELECT h.billno::text billno,h.ybillno::text original_billno,h.rqsj sale_date,
 TRIM(s.sglppcode) brand_code,TRIM(s.sglsupid) supplier_code,
 SUM(COALESCE(s.sglxssr,0)) sales,SUM(COALESCE(s.sgln2,0)) gross_profit
FROM salehead h JOIN salegoodslist s ON s.sglbillno=h.billno AND s.sglmarket=:store_code
WHERE h.mkt=:store_code AND h.ybillno=ANY(CAST(:bills AS numeric[]))
 AND h.rqsj>=:end_exclusive AND h.rqsj<:observed_exclusive
 AND COALESCE(h.djlb,'') NOT IN ('V','W','Y','Z')
GROUP BY h.billno,h.ybillno,h.rqsj,TRIM(s.sglppcode),TRIM(s.sglsupid)
"""

def summarize_returns(rows,period_sales,observed_through):
    totals=defaultdict(Decimal)
    for row in rows:
        totals[row['billno']]+=Decimal(str(row['sales'] or 0))
    valid={bill for bill,total in totals.items() if total<0}
    details=[dict(row) for row in rows if row['billno'] in valid]
    amount=sum((totals[bill] for bill in valid),Decimal(0))
    return dict(status='observed',observed_through=observed_through,return_tickets=len(valid),
                return_sales=amount,reference_net_sales=Decimal(str(period_sales))+amount,details=details,
                basis='仅追溯本档核销销售小票的活动后负净额退货单；按原单号关联，不要求同时退券。',
                caveat='单独观察，不改写活动期指标，不等于券费用或供应商应扣额；未链接原单及退货冲正链仍待核查。')

def query_post_returns(db,config,period_tickets,period_sales):
    observed=datetime.now(ZoneInfo('Asia/Shanghai')).date()
    bills=sorted({str(r['billno']) for r in period_tickets if r['ticket_kind']=='销售'})
    rows=[]
    for offset in range(0,len(bills),500):
        rows.extend(dict(r) for r in db.execute(text(LATE_RETURN_SQL),dict(store_code=config['store_code'],
          bills=bills[offset:offset+500],end_exclusive=config['end_date']+timedelta(days=1),
          observed_exclusive=observed+timedelta(days=1))).mappings())
        if len(rows)>100000:
            raise ValueError('活动后退货明细超过10万行，未生成截断报告')
    return summarize_returns(rows,period_sales,observed)
