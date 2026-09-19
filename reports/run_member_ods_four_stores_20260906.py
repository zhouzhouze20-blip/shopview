"""Authorized four-store member ODS rollout. No CRM writes or source DDL."""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from supplement_gift_ods_20260906 import client, extract_data, query
from prepare_member_ods_four_stores_20260906 import OUT, save
from schedule_gift_ods_20260906 import body

IDS=(54,55,56)
def current(c):
    return {t['id']:t for t in extract_data(c.execute('GET','/api/database-tasks')) if t['id'] in IDS}

def check(t):
    b=json.loads((OUT/'prepared.json').read_text())[str(t['id'])]
    assert t['source_id']==14 and t['target_source_id']==4
    assert t['sql_text']==b['sqlText'] and t['table_name']==b['tableName']
    assert t['key_columns']=='id' and t['insert_mode']=='update' and not t['auto_create_table']
    assert t['watermark_enabled'] and t['watermark_column']=='source_watermark'
    assert not t['running_count']

def schema(c):
    ts=current(c)
    assert len(ts)==3
    for t in ts.values():
        check(t); assert not t['enabled'] and not t['schedule_enabled']
    existing=query(c,4,"SELECT table_name FROM information_schema.tables WHERE table_schema='ods' AND table_name IN ('crm_member_identity','crm_member_scenes','crm_member_level')")
    assert existing==[], 'Existing tables require separate schema review; never overwrite'
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python_app'))
    from models.database import engine
    from sqlalchemy import text
    assert (engine.url.host,engine.url.database)==('192.168.98.80','sales_db')
    with engine.begin() as con:
        con.execute(text("SET LOCAL lock_timeout='5s'"))
        con.execute(text((OUT/'schema.sql').read_text()))
    cols=query(c,4,"SELECT table_name,column_name,data_type,is_nullable FROM information_schema.columns WHERE table_schema='ods' AND table_name IN ('crm_member_identity','crm_member_scenes','crm_member_level') ORDER BY table_name,ordinal_position")
    for t in ts.values():
        mapping=t['field_mapping']; mapping=json.loads(mapping) if isinstance(mapping,str) else mapping
        assert set(mapping.values())=={r['column_name'] for r in cols if r['table_name']==t['table_name'].split('.')[1]}
    save('schema_verified',{'checked_at':datetime.now().astimezone().isoformat(),'columns':cols})
    print('Created and verified three new ODS tables; existing member dimension unchanged',flush=True)

def run(c,i):
    assert i in IDS and (OUT/'schema_verified.json').exists()
    t=current(c)[i]; check(t)
    assert not t['enabled'] and not t['schedule_enabled']
    assert str(i) in json.loads((OUT/'preview.json').read_text())
    try:
        r=extract_data(c.execute('POST',f'/api/database-tasks/{i}/run',{},confirm_write=True))
        # Run responses are server execution metadata, not preview customer rows.
        save(f'run_response_{i}',r)
        print(json.dumps({'id':i,'response':r},ensure_ascii=False),flush=True)
    except TimeoutError:
        print(json.dumps({'id':i,'request_timeout':True,'next':'Inspect same server task; do not resubmit'}),flush=True)

def status(c):
    result={}
    for i,t in current(c).items():
        l=t.get('latest_log') or {}
        save(f'latest_log_{i}',l)
        result[str(i)]={k:t.get(k) for k in ['name','enabled','schedule_enabled','schedule_interval_minutes','running_count','resume_enabled','watermark_value','watermark_checkpoint_value','next_run_at','schedule_failure_count','last_schedule_error']}
        result[str(i)]['log']={k:l.get(k) for k in ['id','status','stage','row_count','source_row_count','error','started_at','finished_at','trigger','trace_id']}
    save('status',result);print(json.dumps(result,ensure_ascii=False),flush=True)

def resume(c,i):
    assert i in IDS
    t=current(c)[i];check(t)
    l=t['latest_log'];assert l['status']=='success' and l['stage']=='completed'
    assert l['source_row_count']==l['row_count']
    target=query(c,4,f"SELECT COUNT(*) n,MAX(source_watermark) wm FROM {t['table_name']}")[0]
    # Seeding is allowed only after the complete initial stream committed.
    if not t['resume_enabled']:
        assert int(target['n'])==int(l['row_count'])
    seed=max(int(target['wm']),int(t['watermark_value'] or 0))
    save(f'initial_full_log_{i}',l)
    b=body(t);b.update(resumeEnabled=True,watermarkValue=seed)
    extract_data(c.execute('PUT',f'/api/database-tasks/{i}',b,confirm_action=True))
    after=current(c)[i]
    assert after['resume_enabled'] and int(after['watermark_value'])==seed
    assert int(after['watermark_checkpoint_value'])==seed
    save(f'resume_seed_{i}',{'source':'MAX source_watermark in fully committed target','seed':seed,'initial_count':int(target['n'])})
    print(json.dumps({'id':i,'resume_enabled':True,'verified_seed':seed,'initial_count':int(target['n'])}),flush=True)

def enable(c):
    assert json.loads((OUT/'validation.json').read_text())['passed']
    for i,t in current(c).items():
        check(t)
        l=t['latest_log'];assert l['status']=='success' and l['stage']=='completed'
        # Execution logs contain the SQL after PAPI substituted its watermark.
        snapshot=json.loads(l['task_snapshot'])
        assert snapshot['sql_text']==t['sql_text'] and l['source_row_count']==l['row_count']
        assert t['resume_enabled']
        assert float(t['watermark_value'])>0
        # GET returns 0/1; this PAPI endpoint requires a JSON boolean for resume.
        b=body(t);b.update(enabled=True,scheduleEnabled=True,resumeEnabled=True)
        # Preserve the LIVE watermark, never reset it to the prepared initial zero.
        extract_data(c.execute('PUT',f'/api/database-tasks/{i}',b,confirm_action=True))
    for t in current(c).values():
        assert t['enabled'] and t['schedule_enabled'] and t['schedule_interval_minutes']==5
        assert t['resume_enabled']
        assert t['next_run_at'] and float(t['watermark_value'])>0
    status(c)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['schema','run','status','enable','resume']);p.add_argument('--task-id',type=int)
    a=p.parse_args();c=client()
    if a.action in ('run','resume'):globals()[a.action](c,a.task_id)
    else:globals()[a.action](c)
