"""Authorized insert-only repair of four historical store/date scopes via PAPI.

No source DDL/writes, target DDL/deletes/updates, or schedule enablement.
Preview customer rows are checked in memory and never saved or printed.
"""
import argparse
import json
import hashlib
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from supplement_gift_ods_20260906 import client, extract_data, query
from audit_erp_coupon_primary_20260906 import compare_daily

OUT = Path(__file__).resolve().parent / 'erp-coupon-backfill-once-20260906'
NAME = 'TKTCARDFQLOG 601/603 20260831及20260905 一次性补缺 20260906'
SCOPE = """TCFLMKT IN ('601','603') AND (
 (TCFLDATE >= DATE '2026-08-31' AND TCFLDATE < DATE '2026-09-01') OR
 (TCFLDATE >= DATE '2026-09-05' AND TCFLDATE < DATE '2026-09-06'))"""

def save(name, data):
    OUT.mkdir(exist_ok=True)
    (OUT / f'{name}.json').write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str))

def load(name):
    return json.loads((OUT / f'{name}.json').read_text())

def tasks(c):
    return extract_data(c.execute('GET', '/api/database-tasks'))

def configuration_fingerprint(t):
    # Fields changed by normal execution (watermarks/next_run_at) are excluded.
    keys = ('name','source_id','target_source_id','table_name','sql_text','field_mapping',
            'insert_mode','key_columns','enabled','schedule_enabled','schedule_type',
            'schedule_time','schedule_interval_minutes','resume_enabled')
    return {k: t.get(k) for k in keys}

def aggregate(c, label):
    result = {}
    for source, table, key in [(7, 'DBUSRPOP.TKTCARDFQLOG', 'source'), (4, 'public.tktcardfqlog', 'target')]:
        sql = f"""SELECT TCFLMKT store,TO_CHAR(TCFLDATE,'YYYY-MM-DD') business_day,
          COUNT(*) n,COUNT(DISTINCT TCFLSEQNO) unique_logs,SUM(TCFLSEQNO) key_sum,
          SUM(TCFLMONEY) signed_amount FROM {table} WHERE {SCOPE}
          GROUP BY TCFLMKT,TO_CHAR(TCFLDATE,'YYYY-MM-DD') ORDER BY 1,2"""
        result[key] = dict(source_id=source, sql=sql, checked_at=datetime.now().astimezone().isoformat(), rows=query(c,source,sql))
    result['comparison'] = compare_daily(result['source']['rows'], result['target']['rows'])
    save(label, result)
    print(json.dumps({'phase':label, **result['comparison']}, default=str), flush=True)
    return result

def prepare(c):
    ts=tasks(c)
    base=next(t for t in ts if t['id']==9)
    assert base['source_id']==7 and base['target_source_id']==4 and base['table_name']=='tktcardfqlog'
    assert ' FROM DBUSRPOP.TKTCARDFQLOG WHERE ' in base['sql_text']
    matches=[t for t in ts if t['name']==NAME]
    assert not matches, 'Existing one-off task found: inspect it, never recreate or rerun blindly'
    save('existing_task_configs', {str(t['id']):configuration_fingerprint(t) for t in ts})
    before=aggregate(c,'before')
    src=before['comparison']['source_rows'];dst=before['comparison']['target_rows']
    assert 0 < dst < src and len(before['source']['rows'])==4
    assert all(Decimal(str(r.get('N',r.get('n'))))==Decimal(str(r.get('UNIQUE_LOGS',r.get('unique_logs')))) for r in before['source']['rows'])
    cols=query(c,4,"SELECT column_name,data_type,character_maximum_length,is_nullable FROM information_schema.columns WHERE table_schema='public' AND table_name='tktcardfqlog' ORDER BY ordinal_position")
    indexes=query(c,4,"SELECT indexdef FROM pg_indexes WHERE schemaname='public' AND tablename='tktcardfqlog' AND indexdef ILIKE '%UNIQUE%'")
    assert any('(tcflseqno)' in r['indexdef'] for r in indexes)
    mapping=base['field_mapping'];mapping=json.loads(mapping) if isinstance(mapping,str) else mapping
    assert set(mapping.values())=={r['column_name'] for r in cols}
    sql=base['sql_text'].split(' WHERE ')[0]+' WHERE '+SCOPE+' ORDER BY TCFLSEQNO'
    b=dict(name=NAME,sourceId=7,targetSourceId=4,tableName='public.tktcardfqlog',sqlText=sql,
           fieldMapping=mapping,insertMode='skip',keyColumns='tcflseqno',batchSize=3000,maxRows=0,
           autoCreateTable=False,resumeEnabled=False,watermarkEnabled=False,
           enabled=False,scheduleEnabled=False,scheduleType='daily',scheduleTime='00:00',
           scheduleIntervalMinutes=1440,scheduleWeekdays='0,1,2,3,4,5,6',scheduleMonthDay=1,
           queryTimeoutSeconds=1200,dbTimeoutSeconds=1200,maxRuntimeSeconds=3600)
    save('schema',dict(columns=cols,indexes=indexes));save('planned',b)
    response=extract_data(c.execute('POST','/api/database-tasks',b,confirm_action=True))
    i=response.get('task',response)['id'];save('task_id',i)
    t=next(t for t in tasks(c) if t['id']==i);check(t,b)
    preview=extract_data(c.execute('POST',f'/api/database-tasks/{i}/preview',{}))
    assert preview['sourceRowCount']==preview['targetRowCount'] and preview['sourceRowCount']>0
    for row in preview['rows']:
        assert set(row)==set(mapping.values())
        assert str(row['tcflmkt']) in ('601','603') and str(row['tcfldate'])[:10] in ('2026-08-31','2026-09-05')
        for col in cols:
            value=row[col['column_name']]
            if col['is_nullable']=='NO': assert value is not None
            if value is not None and col['character_maximum_length']: assert len(str(value))<=col['character_maximum_length']
    save('preview',dict(passed=True,source_rows=preview['sourceRowCount'],target_rows=preview['targetRowCount'],fields=list(mapping),customer_rows_saved=False))
    print(json.dumps({'task_id':i,'prepared':True,'mode':'skip','enabled':False,'schedule_enabled':False}),flush=True)

def check(t,b):
    assert t['source_id']==7 and t['target_source_id']==4
    assert t['sql_text']==b['sqlText'] and t['table_name']==b['tableName']
    assert t['insert_mode']=='skip' and t['key_columns']=='tcflseqno'
    assert not t['enabled'] and not t['schedule_enabled'] and not t['auto_create_table']
    assert not t['watermark_enabled'] and t['max_rows']==0

def run(c):
    i=load('task_id');t=next(t for t in tasks(c) if t['id']==i);check(t,load('planned'))
    assert load('preview')['passed'] and not t['running_count']
    assert not t.get('latest_log'), 'A run already exists; inspect status instead of resubmitting'
    try:
        r=extract_data(c.execute('POST',f'/api/database-tasks/{i}/run',{},confirm_write=True))
        save('run_response',r)
    except TimeoutError:
        print('HTTP wait timed out; inspect same server run, do not resubmit',flush=True)
    status(c)

def status(c):
    t=next(t for t in tasks(c) if t['id']==load('task_id'));check(t,load('planned'))
    l=t.get('latest_log') or {};save('latest_log',l)
    result={k:t.get(k) for k in ['id','enabled','schedule_enabled','running_count','next_run_at']}
    result['log']={k:l.get(k) for k in ['id','status','stage','source_row_count','row_count','error','finished_at','trigger']}
    save('status',result);print(json.dumps(result),flush=True)

def verify_keys(c):
    """Compare every scoped log key; pack <=200 keys/group to avoid row truncation."""
    result={}
    for source,table,label in [(7,'DBUSRPOP.TKTCARDFQLOG','source'),(4,'public.tktcardfqlog','target')]:
        bounds=query(c,source,f'SELECT MIN(TCFLSEQNO) lo,MAX(TCFLSEQNO) hi FROM {table} WHERE {SCOPE}')[0]
        bounds={k.lower():v for k,v in bounds.items()}
        lo,hi=int(bounds['lo'])//200,int(bounds['hi'])//200
        assert hi-lo<5000, 'Unexpected range: inspect before expanding reads'
        all_keys=[]
        for start in range(lo,hi+1,140):
            end=min(start+140,hi+1)
            agg=("LISTAGG(TO_CHAR(TCFLSEQNO,'TM9'),',') WITHIN GROUP(ORDER BY TCFLSEQNO)" if source==7
                 else "STRING_AGG(TCFLSEQNO::text,',' ORDER BY TCFLSEQNO)")
            sql=f"SELECT TRUNC(TCFLSEQNO/200) bucket,{agg} packed_keys FROM {table} WHERE {SCOPE} AND TCFLSEQNO>={start*200} AND TCFLSEQNO<{end*200} GROUP BY TRUNC(TCFLSEQNO/200) ORDER BY 1"
            rows=query(c,source,sql)
            for raw in rows:
                row={k.lower():v for k,v in raw.items()}
                all_keys.extend(int(k) for k in row['packed_keys'].split(','))
        assert len(set(all_keys))==len(all_keys)
        result[label]=set(all_keys)
    proof=dict(passed=result['source']==result['target'],source_keys=len(result['source']),target_keys=len(result['target']),
               source_only=len(result['source']-result['target']),target_only=len(result['target']-result['source']),
               source_sha256=hashlib.sha256('\n'.join(map(str,sorted(result['source']))).encode()).hexdigest(),
               target_sha256=hashlib.sha256('\n'.join(map(str,sorted(result['target']))).encode()).hexdigest(),
               raw_keys_saved=False,checked_at=datetime.now().astimezone().isoformat())
    save('all_key_verification',proof);print(json.dumps(proof),flush=True)
    assert proof['passed']

def verify_samples(c):
    cols=load('schema')['columns'];b=load('planned');proof=[]
    source_select=b['sqlText'].split(' WHERE ')[0]
    target_select=','.join((f"TO_CHAR({x['column_name']},'YYYY-MM-DD')" if x['data_type']=='date' else x['column_name'])+' AS '+x['column_name'] for x in cols)
    for store,day,end in [('601','2026-08-31','2026-09-01'),('603','2026-08-31','2026-09-01'),('601','2026-09-05','2026-09-06'),('603','2026-09-05','2026-09-06')]:
        sql=f"SELECT * FROM ({source_select} WHERE TCFLMKT='{store}' AND TCFLDATE>=DATE '{day}' AND TCFLDATE<DATE '{end}' ORDER BY TCFLSEQNO DESC) WHERE ROWNUM<=200"
        src=query(c,7,sql);ids=','.join(str(int(r['tcflseqno'])) for r in src)
        dst=query(c,4,f'SELECT {target_select} FROM public.tktcardfqlog WHERE tcflseqno IN ({ids})')
        byid={str(r['tcflseqno']):r for r in dst};bad={};missing=0
        for row in src:
            target=byid.get(str(row['tcflseqno']))
            if target is None: missing+=1;continue
            for col in cols:
                key=col['column_name'];a,z=row[key],target[key]
                if col['data_type']=='numeric':
                    a=Decimal(str(a)) if a is not None else None
                    z=Decimal(str(z)) if z is not None else None
                if a!=z:bad[key]=bad.get(key,0)+1
        proof.append(dict(store=store,business_day=day,sampled_rows=len(src),fields=len(cols),missing=missing,
                          mismatch_counts=bad,passed=not missing and not bad,customer_rows_saved=False))
        save('field_samples',proof)
    print(json.dumps(proof),flush=True)
    assert all(p['passed'] for p in proof)

def verify(c):
    ts=tasks(c);t=next(t for t in ts if t['id']==load('task_id'));check(t,load('planned'))
    l=t['latest_log'];assert not t['running_count'] and l['status']=='success' and l['stage']=='completed'
    assert l['row_count']==l['source_row_count']
    after=aggregate(c,'after');assert after['comparison']['passed'], 'Scope remains different; do not claim complete'
    verify_keys(c)
    verify_samples(c)
    original=load('existing_task_configs')
    unchanged=all(configuration_fingerprint(t)==original[str(t['id'])] for t in ts if str(t['id']) in original)
    assert unchanged, 'Existing task configuration changed; inspect attribution'
    before=load('before')['comparison']
    result=dict(passed=True,checked_at=datetime.now().astimezone().isoformat(),task_id=t['id'],
                source_processed=l['source_row_count'],target_scope_before=before['target_rows'],
                target_scope_after=after['comparison']['target_rows'],
                target_net_added=after['comparison']['target_rows']-Decimal(str(before['target_rows'])),
                note='Net target increase; external ETL stayed active, not a per-writer insert attribution',
                existing_papi_configurations_unchanged=unchanged,source_changed=False,target_existing_rows_overwritten=False,
                schedule_enabled=False,primary_key_unique=True,aggregate_comparison=after['comparison'])
    save('verification',result);status(c)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','run','status','verify'])
    args=parser.parse_args();globals()[args.action](client())
