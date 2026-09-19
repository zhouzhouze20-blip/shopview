"""Read-only, bounded coupon data audit. Persists aggregate evidence, never credentials.

Usage: .venv/bin/python reports/coupon_data_audit_20260905.py LABEL SOURCE SQL
SOURCE=pg uses the application's configured database; integers use discovered PAPI IDs.
SQL must be SELECT or read-only WITH. Run only aggregate/metadata queries: no member PII.
"""
import json
import sys
import hashlib
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, '/Users/zhou/.codex/skills/papi-etl/scripts')
from papi_cli import PapiClient, find_api_key, ensure_read_only_sql, extract_data, redact


def run(label, source, sql):
    ensure_read_only_sql(sql)
    started = datetime.now().astimezone().isoformat()
    try:
        if source == 'pg':
            sys.path.insert(0, str(ROOT / 'python_app'))
            from models.database import engine
            from sqlalchemy import text
            with engine.connect() as conn:
                with conn.begin():
                    conn.execute(text('SET TRANSACTION READ ONLY'))
                    conn.execute(text("SET LOCAL statement_timeout = '20000'"))
                    rows = conn.execute(text(sql)).mappings().fetchmany(501)
                    if len(rows) > 500:
                        raise ValueError('More than 500 rows; narrow the metadata/aggregate query')
                    result = {'rows': [dict(r) for r in rows], 'row_count':len(rows)}
        else:
            doc_root = Path('/Users/zhou/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/zhouzeze2011_6ba3/msg/file')
            key_docs = list(doc_root.glob('2026-*/papi-ai-integration*.md'))
            client = PapiClient('http://192.168.0.5:3030', find_api_key(search_roots=key_docs), 45)
            result = extract_data(client.execute('POST', f'/api/sources/{int(source)}/test', {'sql':sql,'limit':500}))
        record = {'label':label,'source':source,'started_at':started,'finished_at':datetime.now().astimezone().isoformat(),'sql':sql,'result':redact(result)}
    except Exception as exc:
        # Do not log SQLAlchemy connection strings or raw connection exceptions.
        record = {'label':label,'source':source,'started_at':started,'sql':sql,'error_type':type(exc).__name__}
        if source == 'pg':
            record['sqlstate'] = getattr(getattr(exc, 'orig', None), 'pgcode', None)
            message = str(exc).lower()
            record['error_hint'] = next((hint for hint in ('connection refused','timeout expired','statement timeout','no route to host','network is unreachable','server closed') if hint in message),'unclassified database error')
        if source != 'pg':
            record['error'] = str(exc)[:800]
    dest = ROOT / 'reports' / 'coupon-data-audit-20260905'
    dest.mkdir(exist_ok=True)
    (dest / f'{label}.json').write_text(json.dumps(record, ensure_ascii=False, indent=2, default=str))
    print(json.dumps(record, ensure_ascii=False, default=str))


def crosscheck():
    """Compare all Qixi asset keys in memory; persist only counts and set digests."""
    doc_root = Path('/Users/zhou/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/zhouzeze2011_6ba3/msg/file')
    client = PapiClient('http://192.168.0.5:3030', find_api_key(search_roots=list(doc_root.glob('2026-*/papi-ai-integration*.md'))),45)
    base_sql = "SELECT r.coupon_code,r.third_cno,t.third_party_no FROM ferry_wadge.coupon_record_601 r JOIN ferry_wadge.coupon_template t ON t.id=r.template_id AND t.tenant_id=r.tenant_id WHERE r.template_id IN (532623,532624,532625,532626) AND r.deleted=0 ORDER BY r.coupon_code"
    crm_rows=[]
    pages=0
    for offset in range(0, 2200, 200):
        sql=base_sql+f' LIMIT 200 OFFSET {offset}'
        ensure_read_only_sql(sql)
        result=extract_data(client.execute('POST','/api/sources/14/test',{'sql':sql,'limit':200}))
        if result.get('truncated'):
            raise ValueError('Unexpected truncated CRM page')
        rows=result['rows']; crm_rows.extend(rows); pages+=1
        if len(rows)<200: break
    else: raise ValueError('CRM cohort exceeded audit bound')
    sys.path.insert(0,str(ROOT/'python_app'))
    from models.database import engine
    from sqlalchemy import text
    pg_sql="SELECT DISTINCT tcfljetype,tcflvipseq FROM tktcardfqlog WHERE tcflmkt='601' AND tcfljetype IN ('B','E','H','M') AND tcflstartdate=DATE '2026-08-14' AND tcflenddate=DATE '2026-08-19' AND tcflzy='M' AND tcfldate<DATE '2026-08-20'"
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text('SET TRANSACTION READ ONLY'))
            pg_rows=list(conn.execute(text(pg_sql)).mappings())
    crm_keys={f"{r['third_party_no']}:{int(r['third_cno'])}" for r in crm_rows}
    pg_keys={f"{r['tcfljetype']}:{int(r['tcflvipseq'])}" for r in pg_rows}
    digest=lambda s:hashlib.sha256('\n'.join(sorted(s)).encode()).hexdigest()
    record={'label':'cross_source_asset_keys','checked_at':datetime.now().astimezone().isoformat(), 'sql':{'crm':base_sql,'postgres':pg_sql},'pages':pages,'crm_record_rows':len(crm_rows),'crm_unique_codes':len({r['coupon_code'] for r in crm_rows}),'crm_unique_asset_keys':len(crm_keys),'pg_unique_asset_keys':len(pg_keys),'intersection':len(crm_keys & pg_keys),'crm_only':len(crm_keys-pg_keys),'pg_only':len(pg_keys-crm_keys),'crm_set_sha256':digest(crm_keys),'pg_set_sha256':digest(pg_keys)}
    (ROOT/'reports/coupon-data-audit-20260905/cross_source_asset_keys.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
    print(json.dumps(record,ensure_ascii=False))


if __name__ == '__main__':
    if sys.argv[1:] == ['--crosscheck']:
        crosscheck()
    else:
        run(*sys.argv[1:])
