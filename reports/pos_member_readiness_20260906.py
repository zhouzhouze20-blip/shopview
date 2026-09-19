"""Read-only POS/member readiness audit; persist aggregate evidence only."""
import json
import sys
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from supplement_gift_ods_20260906 import client, extract_data
from papi_cli import ensure_read_only_sql

OUT=Path(__file__).resolve().parent/'pos-member-readiness-20260906'
OLD=Path(__file__).resolve().parent/'coupon-data-audit-20260905'

def run(label,sid,sql):
    ensure_read_only_sql(sql)
    item={'label':label,'source_id':sid,'sql':sql,'started_at':datetime.now().astimezone().isoformat()}
    try:
        r=extract_data(client().execute('POST',f'/api/sources/{sid}/test',{'sql':sql,'limit':200}))
        if not r.get('ok') or r.get('truncated'): raise RuntimeError('Incomplete/truncated result')
        item['rows']=r['rows']; item['duration_ms']=r.get('durationMs')
    except Exception as e: item['error']={'type':type(e).__name__,'message':str(e)[:500]}
    item['finished_at']=datetime.now().astimezone().isoformat();OUT.mkdir(exist_ok=True)
    (OUT/(label+'.json')).write_text(json.dumps(item,ensure_ascii=False,indent=2,default=str))
    print(json.dumps(item,ensure_ascii=False,default=str),flush=True)
    return item

def prior(name,sid): return name,sid,json.loads((OLD/(name+'.json')).read_text())['sql']

def first():
    jobs=[prior(n,s) for n,s in [('bi_qixi_link',14),('bi_qixi_member_history_compat',14),('bi_history_gap_context',14),('pg_qixi_ticket_link',4),('pg_qixi_supplier_lines',4),('pg_qixi_late_returns',4),('pg_campaign_inventory',4)]]
    jobs.extend([
        ('crm603_pos_templates',14,"SELECT id,name,money,third_party_no,DATE_FORMAT(start_date_time,'%Y-%m-%d') issue_start,DATE_FORMAT(end_date_time,'%Y-%m-%d') issue_end,DATE_FORMAT(use_start_time,'%Y-%m-%d') valid_start,DATE_FORMAT(use_end_time,'%Y-%m-%d') valid_end,use_time_type,ff_num,hx_num,CAST(deleted AS UNSIGNED) deleted FROM ferry_wadge.coupon_template WHERE tenant_id=603 AND type='pos' AND (start_date_time>='2026-08-01' OR (use_start_time<'2026-09-07' AND use_end_time>='2026-08-01')) AND deleted=0 ORDER BY ff_num DESC,id LIMIT 40"),
        ('member_history_schema',14,"SELECT table_name,column_name,column_type,column_key,column_comment FROM information_schema.columns WHERE table_schema='ferry_wadge' AND table_name IN ('member','member_scenes','member_level_track') AND column_name IN ('id','tenant_id','member_scenes_id','mem_scenes_id','member_no','third_party_no','register_time','create_time','update_time','start_date','end_date','level_code','before_level_code','after_level_code','deleted') ORDER BY table_name,ordinal_position"),
        ('pos_volume',14,"SELECT '601' store,COUNT(*) records,COUNT(DISTINCT r.coupon_code) unique_codes,COUNT(DISTINCT r.template_id) templates,COUNT(DISTINCT r.mem_id) members,SUM(r.third_cno IS NULL OR r.third_cno=0) no_erp_asset,SUM(r.mem_id IS NULL OR r.mem_id=0) no_member,MAX(r.update_time) max_updated FROM ferry_wadge.coupon_record_601 r JOIN ferry_wadge.coupon_template t ON t.id=r.template_id AND t.tenant_id=r.tenant_id WHERE r.tenant_id=601 AND t.type='pos' AND (r.create_time>='2026-08-01' OR r.update_time>='2026-08-01' OR r.used_date_time>='2026-08-01') UNION ALL SELECT '603',COUNT(*),COUNT(DISTINCT r.coupon_code),COUNT(DISTINCT r.template_id),COUNT(DISTINCT r.mem_id),SUM(r.third_cno IS NULL OR r.third_cno=0),SUM(r.mem_id IS NULL OR r.mem_id=0),MAX(r.update_time) FROM ferry_wadge.coupon_record_603 r JOIN ferry_wadge.coupon_template t ON t.id=r.template_id AND t.tenant_id=r.tenant_id WHERE r.tenant_id=603 AND t.type='pos' AND (r.create_time>='2026-08-01' OR r.update_time>='2026-08-01' OR r.used_date_time>='2026-08-01')")])
    with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda a:run(*a),jobs))

if __name__=='__main__':
    if sys.argv[1:] == ['first']:first()
    else:run(sys.argv[1],int(sys.argv[2]),sys.argv[3])
