"""Prepare disabled PAPI tasks for four-store CURRENT member data.

No task runs, scheduling enablement or target DDL here. Preview never saves
customer rows. PAPI run authorization follows reviewed scope/schema/preview.
"""
import json
from pathlib import Path
from supplement_gift_ods_20260906 import client, extract_data

OUT = Path(__file__).resolve().parent / 'member-ods-four-stores-20260906'
STORES = '601,602,603,604'

def save(name, obj):
    OUT.mkdir(exist_ok=True)
    (OUT / (name + '.json')).write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str))

def columns(alias, plain, dates):
    result = [f'{alias}.{name}' for name in plain]
    result += [f"DATE_FORMAT({alias}.{src}, '%Y-%m-%d %H:%i:%s') AS {dst}" for src,dst in dates]
    result += [f'CAST({alias}.deleted AS UNSIGNED) AS deleted',
               f'UNIX_TIMESTAMP({alias}.update_time) AS source_watermark',
               "CONCAT(DATE_FORMAT(NOW(), '%Y-%m-%d %H:%i:%s'), ' +08:00') AS source_loaded_at"]
    names = plain + [dst for _,dst in dates] + ['deleted','source_watermark','source_loaded_at']
    return ', '.join(result), {n:n for n in names}

def plans():
    common_dates = [('create_time','source_create_time'),('update_time','source_update_time')]
    definitions = [
        ('identity', '门店身份映射', 'm', 'ferry_wadge.member m', f'm.tenant_id IN ({STORES})',
         ['id','member_scenes_id','tenant_id','mem_no','status'], [('register_time','register_time')]+common_dates),
        ('scenes', '共享会员当前等级', 's', 'ferry_wadge.member_scenes s',
         f's.package_id=111 AND EXISTS (SELECT 1 FROM ferry_wadge.member m WHERE m.member_scenes_id=s.id AND m.tenant_id IN ({STORES}))',
         ['id','mem_no','level_code','status','corp_code','package_id'],
         [('level_start_time','level_start_time'),('expiration_date','expiration_date'),('register_time','register_time')]+common_dates),
        ('level', '等级字典', 'l', 'ferry_wadge.member_level l', f'l.tenant_id IN ({STORES})',
         ['id','tenant_id','level_code','level_name','status'], common_dates),
    ]
    result=[]
    for kind,title,a,table,scope,plain,dates in definitions:
        select,mapping=columns(a,plain,dates)
        # Inclusive overlap protects equal timestamps and interrupted batches.
        # Retains source soft-deletion values; it must not filter deleted=0.
        change = f'{a}.update_time >= FROM_UNIXTIME(GREATEST(0, {{{{PAPI_WATERMARK}}}} - 3600))'
        sql = f'SELECT {select} FROM {table} WHERE {scope} AND {change} ORDER BY {a}.update_time, {a}.id'
        result.append({'name':f'ODS会员-601至604-{title}-5分钟增量',
            'sourceId':14,'targetSourceId':4,'sqlText':sql,
            'tableName':f'ods.crm_member_{kind}','fieldMapping':mapping,
            'insertMode':'update','keyColumns':'id','batchSize':3000,'maxRows':0,
            'autoCreateTable':False,'resumeEnabled':True,
            'watermarkEnabled':True,'watermarkColumn':'source_watermark',
            'watermarkType':'number','watermarkValue':0,
            'queryTimeoutSeconds':1200,'dbTimeoutSeconds':1200,'maxRuntimeSeconds':7200,
            'enabled':False,'scheduleEnabled':False,'scheduleType':'interval',
            'scheduleIntervalMinutes':5,'scheduleTime':'00:00',
            'scheduleWeekdays':'0,1,2,3,4,5,6','scheduleMonthDay':1})
    return result

def main():
    c=client()
    existing=extract_data(c.execute('GET','/api/database-tasks'))
    planned=plans();save('planned',planned)
    prepared={}
    for b in planned:
        matches=[t for t in existing if t['table_name']==b['tableName'] or t['name']==b['name']]
        if matches:
            assert len(matches)==1, 'Conflicting existing task'
            t=matches[0]
            assert t['sql_text']==b['sqlText'] and not t['enabled'] and not t['schedule_enabled'], 'Existing config differs; do not overwrite'
            i=t['id']
        else:
            r=extract_data(c.execute('POST','/api/database-tasks',b,confirm_action=True))
            i=r.get('task',r)['id']
        prepared[str(i)]=b;save('prepared',prepared)
    live={str(t['id']):t for t in extract_data(c.execute('GET','/api/database-tasks'))}
    previews={}
    for i,b in prepared.items():
        t=live[i]
        assert t['source_id']==14 and t['target_source_id']==4
        assert t['sql_text']==b['sqlText'] and t['key_columns']=='id'
        assert not t['enabled'] and not t['schedule_enabled'] and not t['auto_create_table']
        assert t['schedule_interval_minutes']==5 and t['watermark_enabled']
        r=extract_data(c.execute('POST',f'/api/database-tasks/{i}/preview',{}))
        assert r['sourceRowCount']==r['targetRowCount']
        assert all(set(row)==set(b['fieldMapping'].values()) for row in r['rows'])
        # Test the exclusion using in-memory preview, never output identities/card numbers.
        if b['tableName']=='ods.crm_member_scenes':
            assert all(str(row['package_id'])=='111' for row in r['rows'])
        else:
            assert all(str(row['tenant_id']) in STORES.split(',') for row in r['rows'])
        previews[i]={'name':b['name'],'target':b['tableName'],
            'sourceRowCount':r['sourceRowCount'],'targetRowCount':r['targetRowCount'],
            'columns':list(b['fieldMapping']),'scope_passed':True,'enabled':False,'scheduleEnabled':False}
        save('preview',previews)
        print(json.dumps({'id':i,**previews[i]},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
