"""Bounded operator workflow for the user-authorized 601/603 gift coupon reload.

Only CRM gift records created/updated/redeemed since 2026-08-01, plus their
templates and templates changed since that date. No source writes or schedules.
Preview data is not persisted (contains customer information).
"""
import argparse
import json
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/gift-ods-supplement-20260906'
sys.path.insert(0, '/Users/zhou/.codex/skills/papi-etl/scripts')
from papi_cli import PapiClient, find_api_key, extract_data


def client():
    root = Path('/Users/zhou/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/zhouzeze2011_6ba3/msg/file')
    return PapiClient('http://192.168.0.5:3030', find_api_key(search_roots=list(root.glob('2026-*/papi-ai-integration*.md'))), 55)


def save(name, value):
    OUT.mkdir(exist_ok=True)
    (OUT / (name + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def query(c, source, sql):
    result = extract_data(c.execute('POST', f'/api/sources/{source}/test', {'sql': sql, 'limit': 200}))
    if not result.get('ok') or result.get('truncated'):
        raise ValueError('Incomplete query')
    return result['rows']


def scope(alias='r', target=False):
    prefix = 'source_' if target else ''
    return '(' + ' OR '.join(f"{alias}.{col} >= '2026-08-01 00:00:00'" for col in (prefix+'create_time', prefix+'update_time', 'used_date_time')) + ')'


def record_from(store):
    return f"ferry_wadge.coupon_record_{store} r JOIN ferry_wadge.coupon_template t ON t.id=r.template_id AND t.tenant_id=r.tenant_id WHERE r.tenant_id={store} AND t.type='gift' AND {scope()}"


def template_filter(store):
    return (f"tenant_id = {store} AND type = 'gift' AND (create_time >= '2026-08-01' OR update_time >= '2026-08-01' "
            f"OR id IN (SELECT r.template_id FROM ferry_wadge.coupon_record_{store} r WHERE r.tenant_id={store} AND {scope()}))")


def payloads(c):
    tasks = extract_data(c.execute('GET', '/api/database-tasks'))
    base_t = next(t for t in tasks if t['id'] == 43)
    base_r = next(t for t in tasks if t['id'] == 44)
    assert base_t['source_id'] == base_r['source_id'] == 14
    assert base_t['target_source_id'] == base_r['target_source_id'] == 4
    assert base_t['table_name'] == 'ods.crm_coupon_template_603'
    assert base_r['table_name'] == 'ods.crm_coupon_record_603'
    result = []
    for store in (601, 603):
        for kind, base in (('template', base_t), ('record', base_r)):
            if kind == 'template':
                sql = base['sql_text'].split(' WHERE ')[0] + ' WHERE ' + template_filter(store) + ' ORDER BY id'
            else:
                sql = base['sql_text'].split(' FROM ')[0] + ' FROM ' + record_from(store) + ' ORDER BY r.coupon_code'
            mapping = base['field_mapping']
            if isinstance(mapping, str):
                mapping = json.loads(mapping)
            result.append({'name': f'ODS礼品券-{store}-{kind}-20260801起补齐', 'enabled': False,
                'sourceId': 14, 'targetSourceId': 4, 'sqlText': sql,
                'tableName': f'ods.crm_coupon_{kind}_{store}', 'fieldMapping': mapping,
                'insertMode': 'update', 'keyColumns': 'id' if kind == 'template' else 'coupon_code',
                'batchSize': 3000, 'maxRows': 0, 'autoCreateTable': False, 'resumeEnabled': False,
                'schedule': {'scheduleEnabled': False, 'scheduleType': 'daily', 'scheduleTime': '02:00'},
                'queryTimeoutSeconds': 1200, 'dbTimeoutSeconds': 1200, 'maxRuntimeSeconds': 3600})
    return tasks, result


def prepare(c):
    _, bodies = payloads(c)
    evidence = {}
    for store in (601, 603):
        evidence[str(store)] = {
            'record': query(c, 14, 'SELECT COUNT(*) n,COUNT(DISTINCT r.coupon_code) keys_n,SUM(r.coupon_code IS NULL) null_keys FROM ' + record_from(store)),
            'template': query(c, 14, 'SELECT COUNT(*) n,COUNT(DISTINCT id) keys_n FROM ferry_wadge.coupon_template WHERE ' + template_filter(store))}
        for row in evidence[str(store)].values():
            assert row[0]['n'] == row[0]['keys_n']
    save('source_before', evidence)
    save('payloads', bodies)
    print(json.dumps(evidence, ensure_ascii=False), flush=True)


def create(c):
    # The live app database is the same registered destination as source 4.
    sys.path.insert(0, str(ROOT / 'python_app'))
    from models.database import engine
    from sqlalchemy import text
    assert (engine.url.host, engine.url.database) == ('192.168.98.80', 'sales_db')
    with engine.begin() as conn:
        conn.execute(text("SET LOCAL lock_timeout='5s'"))
        for kind in ('template', 'record'):
            conn.execute(text(f'CREATE TABLE IF NOT EXISTS ods.crm_coupon_{kind}_601 (LIKE ods.crm_coupon_{kind}_603 INCLUDING ALL)'))
            conn.execute(text(f"COMMENT ON TABLE ods.crm_coupon_{kind}_601 IS 'PAPI source 14 ferry_wadge CRM gift coupons tenant 601; 2026-08-01 onward changes and related templates'"))
    tasks, bodies = payloads(c)
    ids = []
    for body in bodies:
        matches = [t for t in tasks if t['name'] == body['name']]
        if matches:
            assert len(matches) == 1
            task = matches[0]
            assert not task['enabled'] and not task['schedule_enabled'] and not task['running_count']
            assert task['sql_text'] == body['sqlText'] and task['table_name'] == body['tableName']
            task_id = task['id']
        else:
            result = extract_data(c.execute('POST', '/api/database-tasks', body, confirm_action=True))
            task_id = result.get('task', result)['id']
        ids.append(task_id)
        save('task_ids', ids)
        print('prepared', task_id, body['tableName'], flush=True)


def preview(c):
    ids = json.loads((OUT / 'task_ids.json').read_text())
    summaries = []
    for task_id in ids:
        result = extract_data(c.execute('POST', f'/api/database-tasks/{task_id}/preview', {}))
        # Record metadata only, not issued codes, names, phone numbers or rows.
        summary = {'task_id': task_id, 'response_keys': list(result),
                   'metadata': {k: result[k] for k in ('ok','sourceRowCount','targetRowCount','rowCount','totalRows','columns','targetColumns') if k in result},
                   'sample_row_keys': list(result['rows'][0]) if result.get('rows') else []}
        assert result.get('sourceRowCount', 0) > 0 and result.get('targetRowCount', 0) > 0
        summaries.append(summary)
        print(json.dumps(summary, ensure_ascii=False), flush=True)
    save('previews', summaries)


def run(c, task_id):
    ids = json.loads((OUT / 'task_ids.json').read_text())
    assert task_id in ids
    previews = json.loads((OUT / 'previews.json').read_text())
    assert any(p['task_id'] == task_id and p['metadata'].get('targetRowCount',0) > 0 for p in previews)
    tasks = extract_data(c.execute('GET','/api/database-tasks'))
    task = next(t for t in tasks if t['id'] == task_id)
    body = next(b for b in json.loads((OUT / 'payloads.json').read_text()) if b['name'] == task['name'])
    assert task['source_id'] == 14 and task['target_source_id'] == 4
    assert task['sql_text'] == body['sqlText'] and task['table_name'] == body['tableName']
    assert task['insert_mode'] == 'update' and task['key_columns'] == body['keyColumns']
    assert not task['enabled'] and not task['schedule_enabled'] and not task['running_count']
    result = extract_data(c.execute('POST', f'/api/database-tasks/{task_id}/run', {}, confirm_write=True))
    save(f'run_{task_id}', result)
    print(json.dumps(result, ensure_ascii=False), flush=True)


def status(c):
    ids = json.loads((OUT / 'task_ids.json').read_text())
    tasks = extract_data(c.execute('GET', '/api/database-tasks'))
    rows = []
    for t in tasks:
        if t['id'] not in ids:
            continue
        log = t.get('latest_log') or {}
        save(f'log_{t["id"]}', log)
        rows.append({'task_id': t['id'], 'enabled': t['enabled'], 'schedule_enabled': t['schedule_enabled'], 'running':t.get('running_count'),
            'log': {k:log.get(k) for k in ('id','status','stage','row_count','source_row_count','mapped_row_count','result','error','finished_at','trace_id')}})
    print(json.dumps(rows, ensure_ascii=False), flush=True)


def verify(c, stores=(601,603)):
    evidence = {}
    for store in stores:
        cols = ('r.template_id,r.status,r.used_status,r.deleted,COUNT(*) n,COUNT(DISTINCT r.coupon_code) keys_n,'
            'SUM(CAST(r.coupon_code AS DECIMAL(40,0))) key_sum,'
            'COALESCE(SUM(r.coupon_money),0) coupon_money,COALESCE(SUM(r.coupon_money_left),0) money_left,'
            'COALESCE(SUM(r.used_order_money),0) order_money,COALESCE(SUM(r.used_order_coupon_money),0) order_coupon_money')
        group=' GROUP BY r.template_id,r.status,r.used_status,r.deleted ORDER BY r.template_id,r.status,r.used_status,r.deleted'
        src = query(c,14,'SELECT '+cols.replace('r.deleted,','CAST(r.deleted AS UNSIGNED) deleted,',1)+' FROM '+record_from(store)+group)
        dst = query(c,4,'SELECT '+cols+f' FROM ods.crm_coupon_record_{store} r WHERE r.tenant_id={store} AND '+scope(target=True)+group)
        def norm(rows):
            return sorted([tuple(None if r[k] is None else Decimal(str(r[k])) for k in r) for r in rows],key=str)
        checks = {'aggregates_equal': norm(src)==norm(dst), 'source_rows':sum(int(r['n']) for r in src), 'target_scope_rows':sum(int(r['n']) for r in dst)}
        orphan=query(c,4,f"SELECT COUNT(*) missing_templates FROM ods.crm_coupon_record_{store} r LEFT JOIN ods.crm_coupon_template_{store} t ON t.id=r.template_id AND t.tenant_id=r.tenant_id WHERE {scope(target=True)} AND t.id IS NULL")
        checks['missing_templates']=int(orphan[0]['missing_templates'])
        st=query(c,14,'SELECT id,name,money,type coupon_type,ff_num issued_count,hx_num redeemed_count,tenant_id,CAST(deleted AS UNSIGNED) deleted FROM ferry_wadge.coupon_template WHERE '+template_filter(store)+' ORDER BY id')
        ids=','.join(str(int(r['id'])) for r in st)
        dt=query(c,4,f'SELECT id,name,money,coupon_type,issued_count,redeemed_count,tenant_id,deleted FROM ods.crm_coupon_template_{store} WHERE id IN ({ids}) ORDER BY id')
        def template_norm(rows):
            return [tuple(r[k] if k in ('name','coupon_type') or r[k] is None else Decimal(str(r[k])) for k in r) for r in rows]
        checks['template_fields_equal']=template_norm(st)==template_norm(dt)
        checks['scope_templates']=len(st)
        evidence[str(store)]={'checks':checks,'source_groups':src,'target_groups':dst}
        print(store,json.dumps(checks),flush=True)
    save('verification' if len(stores)==2 else 'verification_'+str(stores[0]),{'checked_at':datetime.now().astimezone().isoformat(),'stores':evidence})
    assert all(v['checks']['aggregates_equal'] and v['checks']['template_fields_equal'] and not v['checks']['missing_templates'] for v in evidence.values())


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','create','preview','run','status','verify']);p.add_argument('--task-id',type=int)
    args=p.parse_args(); c=client()
    if args.action=='run': run(c,args.task_id)
    else: globals()[args.action](c)
