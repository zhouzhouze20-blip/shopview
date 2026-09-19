"""Compare bounded source/target aggregates; never save personal row data."""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from supplement_gift_ods_20260906 import client, query
from prepare_member_ods_four_stores_20260906 import OUT, save

def fingerprint(sql, fields, postgres=False):
    cast = 'text' if postgres else 'CHAR'
    vals=', '.join(f"COALESCE(CAST(x.{col} AS {cast}), '~')" for col in fields)
    md=f"MD5(CONCAT_WS('|', {vals}))"
    if postgres:
        hashes=[f"COALESCE(SUM(('x'||SUBSTRING({md}, {pos}, 8))::bit(32)::bigint),0) AS hash{pos}" for pos in (1,9)]
    else:
        hashes=[f"COALESCE(SUM(CAST(CONV(SUBSTRING({md}, {pos}, 8),16,10) AS DECIMAL(20,0))),0) AS hash{pos}" for pos in (1,9)]
    return 'SELECT COUNT(*) n,COALESCE(SUM(x.id),0) sum_id,'+', '.join(hashes)+f' FROM ({sql}) x'

def verify(kind, retry_failed=False):
    plans=json.loads((OUT/'prepared.json').read_text())
    b=next(b for b in plans.values() if b['tableName']==f'ods.crm_member_{kind}')
    base=b['sqlText'].replace('{{PAPI_WATERMARK}}','0').rsplit(' ORDER BY ',1)[0]
    fields=[c for c in b['fieldMapping'] if c!='source_loaded_at']
    alias={'identity':'m','scenes':'s','level':'l'}[kind]
    c=client()
    bounds=query(c,4,f"SELECT MIN(id) lo,MAX(id) hi,COUNT(*) n FROM {b['tableName']}")[0]
    assert int(bounds['n'])>0
    # Include IDs beyond the initial target maximum to detect new source rows.
    source_bounds=query(c,14,f'SELECT MIN(id) lo,MAX(id) hi FROM ({base}) z')[0]
    lo=min(int(bounds['lo']),int(source_bounds['lo']));hi=max(int(bounds['hi']),int(source_bounds['hi']))
    step=100000
    assert (hi-lo)//step<300, 'Unexpected ID range; choose keyset partitioning instead'
    ranges=[(x,min(hi+1,x+step)) for x in range(lo,hi+1,step)]
    def part(pair):
        low,high=pair
        cached=OUT/f'fingerprint_{kind}_{low}.json'
        if retry_failed and cached.exists():
            previous=json.loads(cached.read_text())
            if previous['equal'] and previous['range']==list(pair):
                return previous
        ssql=fingerprint(base+f' AND {alias}.id>={low} AND {alias}.id<{high}',fields)
        psql=fingerprint(f"SELECT {', '.join(fields)} FROM {b['tableName']} WHERE id>={low} AND id<{high}",fields,True)
        source=query(client(),14,ssql)[0];target=query(client(),4,psql)[0]
        equal={k:int(v) for k,v in source.items()}=={k:int(v) for k,v in target.items()}
        result={'range':[low,high],'source':source,'target':target,'equal':equal,'source_sql':ssql,'target_sql':psql,'checked_at':datetime.now().astimezone().isoformat()}
        save(f'fingerprint_{kind}_{low}',result)
        print(json.dumps({'kind':kind,'range':[low,high],'source_rows':source['n'],'target_rows':target['n'],'equal':equal}),flush=True)
        return result
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(part,ranges))
    report={'kind':kind,'passed':all(r['equal'] for r in results),'source_rows':sum(int(r['source']['n']) for r in results),'target_rows':sum(int(r['target']['n']) for r in results),'fields':fields,'partitions':len(results),'earliest_partition_check':min(r['checked_at'] for r in results),'latest_partition_check':max(r['checked_at'] for r in results),'note':'Sequential partition checks, not a cross-database atomic snapshot','checked_at':datetime.now().astimezone().isoformat()}
    save(f'verification_{kind}',report);print(json.dumps(report,ensure_ascii=False),flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('kind',choices=['identity','scenes','level']);p.add_argument('--retry-failed',action='store_true');a=p.parse_args();verify(a.kind,a.retry_failed)
