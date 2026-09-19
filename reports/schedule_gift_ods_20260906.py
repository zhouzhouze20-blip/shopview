"""Configure the user-requested PAPI schedules; never use local cron.

Stages: prepare disabled -> preview -> authorized trial -> verify -> enable.
Raw /api/database-tasks uses flat schedule fields (not the nested AI creation DTO).
"""
import argparse
import json
from copy import deepcopy
from pathlib import Path
from supplement_gift_ods_20260906 import client, extract_data, query, scope

OUT=Path(__file__).resolve().parent/'gift-ods-schedule-20260906'

def save(name,obj):
    OUT.mkdir(exist_ok=True)
    (OUT/(name+'.json')).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str))

def body(t):
    pairs={'sourceId':'source_id','targetSourceId':'target_source_id','sqlText':'sql_text','tableName':'table_name',
        'fieldMapping':'field_mapping','insertMode':'insert_mode','keyColumns':'key_columns','batchSize':'batch_size',
        'maxRows':'max_rows','autoCreateTable':'auto_create_table','resumeEnabled':'resume_enabled',
        'queryTimeoutSeconds':'query_timeout_seconds','dbTimeoutSeconds':'db_timeout_seconds','maxRuntimeSeconds':'max_runtime_seconds',
        'watermarkEnabled':'watermark_enabled','watermarkColumn':'watermark_column','watermarkType':'watermark_type',
        'watermarkValue':'watermark_value','priority':'priority','scheduleType':'schedule_type',
        'scheduleIntervalMinutes':'schedule_interval_minutes','scheduleTime':'schedule_time',
        'scheduleWeekdays':'schedule_weekdays','scheduleMonthDay':'schedule_month_day'}
    b={k:t[v] for k,v in pairs.items() if v in t}
    if isinstance(b['fieldMapping'],str): b['fieldMapping']=json.loads(b['fieldMapping'])
    b.update(name=t['name'],enabled=False,scheduleEnabled=False)
    return b

def check(t,b,enabled=False):
    assert t['source_id']==b['sourceId']==14 and t['target_source_id']==b['targetSourceId']==4
    assert t['sql_text']==b['sqlText'] and t['table_name']==b['tableName']
    mapping=t['field_mapping'];mapping=json.loads(mapping) if isinstance(mapping,str) else mapping
    assert mapping==b['fieldMapping'] and t['key_columns']==b['keyColumns'] and t['insert_mode']=='update'
    assert bool(t['enabled'])==enabled and bool(t['schedule_enabled'])==enabled
    assert t['schedule_type']==b['scheduleType']
    if b['scheduleType']=='interval': assert t['schedule_interval_minutes']==b['scheduleIntervalMinutes']
    else: assert t['schedule_time']==b['scheduleTime']
    assert t['max_rows']==0 and not t['auto_create_table']

def plan(c):
    tasks=extract_data(c.execute('GET','/api/database-tasks')); ts={t['id']:t for t in tasks}
    for i in (43,45,49,50,51,52):
        assert ts[i]['source_id']==14 and ts[i]['target_source_id']==4 and not ts[i]['running_count']
    save('before', [ts[i] for i in (43,45,49,50,51,52)])
    result={}
    for i,m in ((49,601),(43,603)):
        b=body(ts[i]);b.update(name=f'ODS礼品券-{m}-模板-8月起15分钟同步',scheduleType='interval',scheduleIntervalMinutes=15)
        if m==603: b['sqlText']=ts[51]['sql_text']
        result[str(i)]=b
    for i,m,time in ((50,601,'03:30'),(52,603,'03:40')):
        b=body(ts[i]);b.update(name=f'ODS礼品券-{m}-8月起每日补偿',scheduleType='daily',scheduleTime=time,scheduleIntervalMinutes=1440)
        result[str(i)]=b
    for i,m in ((None,601),(45,603)):
        b=body(ts[45]);base=ts[50 if m==601 else 52]['sql_text'].split(' ORDER BY ')[0]
        recent='('+ ' OR '.join(f'r.{f} >= DATE_SUB(NOW(), INTERVAL 3 DAY)' for f in ('create_time','update_time','used_date_time')) +')'
        b.update(name=f'ODS礼品券-{m}-最近3天变更-15分钟增量',sqlText=base+' AND '+recent+' ORDER BY r.coupon_code',
            tableName=f'ods.crm_coupon_record_{m}',scheduleType='interval',scheduleIntervalMinutes=15)
        key=str(i) if i else 'new601'
        if not i:
            matches=[t for t in tasks if t['name']==b['name']]
            if matches: assert len(matches)==1; key=str(matches[0]['id'])
        result[key]=b
    save('planned',result)
    print(json.dumps({i:{k:b[k] for k in ('name','tableName','scheduleType','scheduleIntervalMinutes','scheduleTime')} for i,b in result.items()},ensure_ascii=False))

def prepare(c):
    planned=json.loads((OUT/'planned.json').read_text()); ids={}
    for key,b in planned.items():
        if key=='new601':
            res=extract_data(c.execute('POST','/api/database-tasks',b,confirm_action=True));i=res.get('task',res)['id']
        else:
            i=int(key);t=next(t for t in extract_data(c.execute('GET','/api/database-tasks')) if t['id']==i)
            assert not t['running_count']
            extract_data(c.execute('PUT',f'/api/database-tasks/{i}',b,confirm_action=True))
        ids[str(i)]=b;save('prepared',ids)
    current={str(t['id']):t for t in extract_data(c.execute('GET','/api/database-tasks'))}
    for i,b in ids.items():check(current[i],b)
    print('disabled_configs_verified',list(ids))

def preview(c):
    configs=json.loads((OUT/'prepared.json').read_text()); proof={}
    for i,b in configs.items():
        r=extract_data(c.execute('POST',f'/api/database-tasks/{i}/preview',{}))
        assert r['sourceRowCount']==r['targetRowCount']
        assert all(set(row)==set(b['fieldMapping'].values()) for row in r['rows'])
        proof[i]={k:r[k] for k in ('sourceRowCount','targetRowCount')};print(i,proof[i],flush=True)
    save('preview',proof)

def run(c,i):
    configs=json.loads((OUT/'prepared.json').read_text());b=configs[str(i)]
    assert str(i) in json.loads((OUT/'preview.json').read_text())
    t=next(t for t in extract_data(c.execute('GET','/api/database-tasks')) if t['id']==i);check(t,b);assert not t['running_count']
    try:
        r=extract_data(c.execute('POST',f'/api/database-tasks/{i}/run',{},confirm_write=True))
        save('trial_'+str(i),r);print(json.dumps(r),flush=True)
    except TimeoutError:
        save('trial_'+str(i),{'request_timed_out':True,'action':'Inspect the same server task. Do not automatically rerun.'})
        print('Request timed out; check existing server task',i,flush=True)

def status(c):
    configs=json.loads((OUT/'prepared.json').read_text());proof={}
    for t in extract_data(c.execute('GET','/api/database-tasks')):
        i=str(t['id'])
        if i not in configs:continue
        log=t.get('latest_log') or {};save('log_'+i,log)
        proof[i]={k:t.get(k) for k in ('name','enabled','schedule_enabled','schedule_type','schedule_interval_minutes','schedule_time','next_run_at','schedule_state','running_count','schedule_failure_count','last_schedule_error')}
        proof[i]['log']={k:log.get(k) for k in ('id','status','stage','row_count','source_row_count','error','finished_at','trigger','trace_id')}
    save('status',proof);print(json.dumps(proof,ensure_ascii=False),flush=True)

def enable(c):
    configs=json.loads((OUT/'prepared.json').read_text())
    ts={str(t['id']):t for t in extract_data(c.execute('GET','/api/database-tasks'))}
    # Full scope validation is required separately before this operator command.
    assert json.loads((OUT/'validation.json').read_text())['passed']
    for i,b in configs.items():
        t=ts[i];check(t,b);assert not t['running_count']
        l=t.get('latest_log') or {};assert l.get('status')=='success' and l.get('stage')=='completed'
        assert l['sql_text']==b['sqlText'] and l['source_row_count']==l['row_count']
        active=deepcopy(b);active.update(enabled=True,scheduleEnabled=True)
        extract_data(c.execute('PUT',f'/api/database-tasks/{i}',active,confirm_action=True))
    ts={str(t['id']):t for t in extract_data(c.execute('GET','/api/database-tasks'))}
    for i,b in configs.items():
        check(ts[i],b,True);assert ts[i]['next_run_at'] and not ts[i].get('last_schedule_error')
    status(c)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['plan','prepare','preview','run','status','enable']);p.add_argument('--task-id',type=int)
    a=p.parse_args();c=client()
    if a.action=='run':run(c,a.task_id)
    else:globals()[a.action](c)
