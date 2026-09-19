"""Nightly same-scope compensation. No source mutations or target deletes."""
import argparse
import json
import sys
from pathlib import Path
from supplement_gift_ods_20260906 import client,extract_data,query
from prepare_member_ods_four_stores_20260906 import OUT,save
from schedule_gift_ods_20260906 import body

def guard(c):
    ts=extract_data(c.execute('GET','/api/database-tasks'))
    assert not any(t['running_count'] for t in ts if t['id'] in (54,55,56))
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python_app'))
    from models.database import engine
    from sqlalchemy import text
    assert (engine.url.host,engine.url.database)==('192.168.98.80','sales_db')
    with engine.begin() as con:
        con.execute(text("SET LOCAL lock_timeout='5s'"))
        con.execute(text((OUT/'protect_newer_rows.sql').read_text()))
    with engine.connect() as con:
        txn=con.begin()
        try:
            # Test both rejection and acceptance inside one rollback-only transaction.
            old=con.execute(text('SELECT id,level_code,source_update_time FROM ods.crm_member_level ORDER BY id LIMIT 1')).mappings().one()
            rejected=con.execute(text("UPDATE ods.crm_member_level SET level_code='ETL_ROLLBACK_TEST',source_update_time=source_update_time-INTERVAL '1 second' WHERE id=:id RETURNING id"),{'id':old['id']}).fetchall()
            assert rejected==[]
            rejected_equal=con.execute(text("UPDATE ods.crm_member_level SET level_code='ETL_ROLLBACK_TEST',source_loaded_at=source_loaded_at-INTERVAL '1 second' WHERE id=:id RETURNING id"),{'id':old['id']}).fetchall()
            assert rejected_equal==[]
            accepted=con.execute(text("UPDATE ods.crm_member_level SET source_update_time=source_update_time+INTERVAL '1 second' WHERE id=:id RETURNING id"),{'id':old['id']}).fetchall()
            assert len(accepted)==1
        finally:txn.rollback()
        restored=con.execute(text('SELECT level_code,source_update_time FROM ods.crm_member_level WHERE id=:id'),{'id':old['id']}).mappings().one()
        assert restored['level_code']==old['level_code'] and restored['source_update_time']==old['source_update_time']
    save('guard_validation',{'passed':True,'older_source_rejected':True,'older_equal_timestamp_snapshot_rejected':True,'newer_source_accepted':True,'all_test_changes_rolled_back':True})
    print('Installed guards and passed rollback-only regression checks',flush=True)

def prepare(c):
    assert json.loads((OUT/'guard_validation.json').read_text())['passed']
    ts=extract_data(c.execute('GET','/api/database-tasks'));prepared={}
    for initial,time in [(54,'03:00'),(55,'03:20'),(56,'03:25')]:
        t=next(t for t in ts if t['id']==initial)
        b=body(t)
        b.update(name=t['name'].replace('5分钟增量','每日全量补偿'),sqlText=t['sql_text'].replace('{{PAPI_WATERMARK}}','0'),watermarkEnabled=False,watermarkValue=None,resumeEnabled=False,scheduleType='daily',scheduleTime=time,scheduleIntervalMinutes=1440)
        matches=[x for x in ts if x['name']==b['name']]
        if matches:
            assert len(matches)==1 and matches[0]['sql_text']==b['sqlText'] and not matches[0]['enabled']
            i=matches[0]['id']
        else:
            r=extract_data(c.execute('POST','/api/database-tasks',b,confirm_action=True));i=r.get('task',r)['id']
        prepared[str(i)]=b;save('compensation_prepared',prepared)
        r=extract_data(c.execute('POST',f'/api/database-tasks/{i}/preview',{}))
        assert r['sourceRowCount']==r['targetRowCount']
        assert all(set(row)==set(b['fieldMapping'].values()) for row in r['rows'])
        print(json.dumps({'id':i,'name':b['name'],'preview_rows':r['targetRowCount'],'schedule_time':time,'enabled':False},ensure_ascii=False),flush=True)

def run(c,i):
    configs=json.loads((OUT/'compensation_prepared.json').read_text());assert str(i) in configs
    t=next(t for t in extract_data(c.execute('GET','/api/database-tasks')) if t['id']==i)
    assert not t['running_count'] and not t['enabled'] and not t['schedule_enabled']
    try:
        r=extract_data(c.execute('POST',f'/api/database-tasks/{i}/run',{},confirm_write=True));save(f'compensation_run_{i}',r);print(json.dumps({'id':i,'response':r}),flush=True)
    except TimeoutError: print(json.dumps({'id':i,'request_timeout':True,'next':'Inspect same server run, do not resubmit'}),flush=True)

def status(c):
    ids=json.loads((OUT/'compensation_prepared.json').read_text());proof={}
    for t in extract_data(c.execute('GET','/api/database-tasks')):
        if str(t['id']) not in ids:continue
        l=t.get('latest_log') or {};save(f'compensation_log_{t["id"]}',l)
        proof[str(t['id'])]={k:t.get(k) for k in ['enabled','schedule_enabled','schedule_time','next_run_at','running_count']}
        proof[str(t['id'])]['log']={k:l.get(k) for k in ['status','stage','row_count','source_row_count','error','finished_at']}
    save('compensation_status',proof);print(json.dumps(proof),flush=True)

def enable(c):
    assert json.loads((OUT/'validation.json').read_text())['passed']
    configs=json.loads((OUT/'compensation_prepared.json').read_text())
    ts=extract_data(c.execute('GET','/api/database-tasks'))
    for i,b in configs.items():
        t=next(t for t in ts if str(t['id'])==i);l=t['latest_log']
        assert not t['running_count'] and l['status']=='success' and l['stage']=='completed'
        assert l['sql_text']==b['sqlText'] and l['source_row_count']==l['row_count']
        active=body(t);active.update(enabled=True,scheduleEnabled=True)
        extract_data(c.execute('PUT',f'/api/database-tasks/{i}',active,confirm_action=True))
    status(c)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['guard','prepare','run','status','enable']);p.add_argument('--task-id',type=int);a=p.parse_args();c=client()
    if a.action=='run':run(c,a.task_id)
    else:globals()[a.action](c)
