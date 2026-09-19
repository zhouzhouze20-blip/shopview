"""Read-only ERP-primary rollout checks. Persist aggregates, never customer rows."""
import json
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from supplement_gift_ods_20260906 import client, query, extract_data

OUT = Path(__file__).resolve().parent / 'erp-coupon-primary-20260906'

def save(name, value):
    OUT.mkdir(exist_ok=True)
    (OUT / f'{name}.json').write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str))

def run(name, source, sql):
    started = datetime.now().astimezone().isoformat()
    try:
        rows = query(client(), source, sql)
        result = dict(source=source, sql=sql, started_at=started,
                      finished_at=datetime.now().astimezone().isoformat(), rows=rows)
    except Exception as exc:
        result = dict(source=source, sql=sql, started_at=started, error_type=type(exc).__name__)
    save(name, result)
    print(name, json.dumps({'row_count': len(result.get('rows', [])),
                           'error_type': result.get('error_type')}, ensure_ascii=False), flush=True)

def compare_daily(source_rows, target_rows):
    """Compare exact numeric aggregates; do not label a partial probe full parity."""
    fields = ('n', 'unique_logs', 'key_sum', 'signed_amount')
    def normalize(rows):
        result = {}
        for raw in rows:
            row = {k.lower(): v for k, v in raw.items()}
            key = (str(row['store']), row.get('business_day', row.get('day')))
            if key in result:
                raise ValueError('Duplicate store/day aggregate')
            result[key] = {k: Decimal(str(row[k] or 0)) for k in fields}
        return result
    src, dst = normalize(source_rows), normalize(target_rows)
    differences = []
    for key in sorted(set(src) | set(dst)):
        if src.get(key) != dst.get(key):
            differences.append(dict(store=key[0], business_day=key[1], source=src.get(key),
                                    target=dst.get(key), count_gap=src.get(key, {}).get('n', 0)-dst.get(key, {}).get('n', 0)))
    return dict(passed=not differences, groups=len(set(src) | set(dst)), differences=differences,
                source_rows=sum(r['n'] for r in src.values()), target_rows=sum(r['n'] for r in dst.values()),
                checked_fields=list(fields), note='Sequential reads; aggregate reconciliation, not full-row equality')

def main():
    scope = "tcflmkt IN ('601','603') AND tcfldate>=DATE '2026-08-01' AND tcfldate<DATE '2026-09-06'"
    group = "tcflmkt,TO_CHAR(tcfldate,'YYYY-MM-DD')"
    for source, table, name in [(7,'DBUSRPOP.TKTCARDFQLOG','erp_daily'),(4,'tktcardfqlog','ods_daily')]:
        run(name,source,f"SELECT tcflmkt store,TO_CHAR(tcfldate,'YYYY-MM-DD') business_day,COUNT(*) n,COUNT(DISTINCT tcflseqno) unique_logs,SUM(tcflseqno) key_sum,SUM(tcflmoney) signed_amount FROM {table} WHERE {scope} GROUP BY {group} ORDER BY {group}")
    daily = [json.loads((OUT / f'{name}_daily.json').read_text()) for name in ('erp', 'ods')]
    if all('rows' in r for r in daily):
        save('daily_reconciliation', compare_daily(daily[0]['rows'], daily[1]['rows']))
    for source,table,name in [(7,'DBUSRPOP.TKTCARDFQLOG','erp_recent'),(4,'tktcardfqlog','ods_recent')]:
        run(name,source,f"SELECT tcflmkt store,TO_CHAR(MAX(tcfldate),'YYYY-MM-DD HH24:MI:SS') latest_business_time,MAX(tcflseqno) max_log,COUNT(*) n FROM {table} WHERE tcflmkt IN ('601','603') AND tcfldate>=DATE '2026-09-05' GROUP BY tcflmkt ORDER BY tcflmkt")
    run('qixi_ownership',4,"SELECT tcflzy action,COALESCE(NULLIF(TRIM(tcflpopid),''),'(empty)') erp_period,COUNT(*) n,COUNT(DISTINCT (tcfljetype,tcflvipseq)) assets FROM tktcardfqlog WHERE tcflmkt='601' AND tcfljetype IN ('B','E','H','M') AND tcflstartdate=DATE '2026-08-14' AND tcflenddate=DATE '2026-08-19' GROUP BY 1,2 ORDER BY 1,2")
    # Existing pilot queries are bounded aggregate evidence, safe to rerun unchanged.
    base=OUT.parent/'pos-member-readiness-20260906'
    for name in ['pg_qixi_ticket_link','pg_qixi_supplier_lines_fixed','pg_qixi_late_returns_fixed']:
        old=json.loads((base/f'{name}.json').read_text())
        run(name,4,old['sql'])
    run('member_bridge',4,"""WITH members AS MATERIALIZED (
      SELECT DISTINCT TRIM(tcflvipno) member_no FROM tktcardfqlog
      WHERE tcflmkt='601' AND tcfljetype IN ('B','E','H','M')
      AND tcflstartdate=DATE '2026-08-14' AND tcflenddate=DATE '2026-08-19' AND tcflzy='M'
    ), matched AS (
      SELECT m.member_no,COUNT(s.id) n,COUNT(s.id) FILTER(WHERE s.deleted=0) active_n,
        COUNT(s.id) FILTER(WHERE EXISTS(SELECT 1 FROM ods.crm_member_identity i
          WHERE i.member_scenes_id=s.id AND i.tenant_id=601 AND i.deleted=0)) in_store,
        COUNT(s.id) FILTER(WHERE NULLIF(TRIM(s.level_code),'') IS NULL) no_level
      FROM members m LEFT JOIN ods.crm_member_scenes s ON s.mem_no=m.member_no AND s.package_id=111
      GROUP BY m.member_no
    ) SELECT COUNT(*) members,COUNT(*) FILTER(WHERE n=1 AND active_n=1 AND in_store=1) unique_active_match,
      COUNT(*) FILTER(WHERE n=0) unmatched,COUNT(*) FILTER(WHERE n>1) ambiguous,
      SUM(no_level) no_level FROM matched""")
    c=client()
    tasks=extract_data(c.execute('GET','/api/database-tasks'))
    save('task_inventory',[{k:t.get(k) for k in ['id','name','source_id','target_source_id','table_name','enabled','schedule_enabled','schedule_type','next_run_at']}
      for t in tasks if 'tktcardfqlog' in str(t.get('sql_text','')).lower() or 'tktcardfqlog' in str(t.get('table_name','')).lower()])

if __name__=='__main__': main()
