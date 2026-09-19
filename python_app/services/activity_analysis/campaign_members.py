"""Current four-store CRM profile. Never infer historical levels or resolve conflicts by MAX."""
from collections import defaultdict
from sqlalchemy import text

MEMBER_SQL = """
WITH requested AS (SELECT UNNEST(CAST(:members AS text[])) member_no)
SELECT r.member_no,s.id::text scene_id,s.level_code,s.register_time admission_date,
 s.source_update_time,s.source_loaded_at,s.deleted,
 EXISTS(SELECT 1 FROM ods.crm_member_identity i WHERE i.member_scenes_id=s.id
   AND i.tenant_id=:tenant_id AND i.deleted=0) has_store_identity,
 d.n dictionary_count,d.level_name
FROM requested r LEFT JOIN ods.crm_member_scenes s ON s.mem_no=r.member_no AND s.package_id=111
LEFT JOIN LATERAL (
 SELECT COUNT(*) n,MIN(level_name) level_name FROM ods.crm_member_level
 WHERE tenant_id=:tenant_id AND level_code=s.level_code AND deleted=0
) d ON true
"""

def resolve_profiles(rows):
    grouped=defaultdict(list)
    for row in rows:
        grouped[row['member_no']].append(dict(row))
    result=[]
    for member_no,candidates in grouped.items():
        present=[r for r in candidates if r.get('scene_id')]
        status='未匹配'
        profile={}
        if len(present)>1:
            status='会员号重复，待核查'
        elif len(present)==1:
            row=present[0]
            if row.get('deleted')!=0:
                status='会员主档已删除'
            elif not row.get('has_store_identity'):
                status='本店有效身份未匹配'
            else:
                profile={k:row.get(k) for k in ('scene_id','admission_date','source_update_time','source_loaded_at')}
                if not row.get('level_code'):
                    status='当前等级缺失'
                elif row.get('dictionary_count')!=1 or not row.get('level_name'):
                    status='等级字典缺失或重复'
                else:
                    status='已匹配'
                    profile.update(member_level=row['level_name'],member_level_code=row['level_code'])
        result.append(dict(member_no=member_no,member_match_status=status,
                           activity_member_level='未接入历史等级',**profile))
    return result

def query_current_members(db,store_code,member_ids):
    metadata=dict(source='CRM当前会员ODS（601—604，共享体系111）',status='ready',
                  history_basis='当前等级不是活动时等级；历史等级尚未接入',matched=0,unresolved=len(member_ids))
    if str(store_code) not in ('601','602','603','604'):
        return [],dict(metadata,status='unavailable',reason='当前会员ODS仅覆盖601—604，未使用607或旧维表代替')
    ready=db.execute(text("""SELECT to_regclass('ods.crm_member_scenes') IS NOT NULL
      AND to_regclass('ods.crm_member_identity') IS NOT NULL
      AND to_regclass('ods.crm_member_level') IS NOT NULL""")).scalar()
    if not ready:
        return [],dict(metadata,status='unavailable',reason='当前会员ODS尚未安装，未回退到旧会员等级')
    rows=[]
    for offset in range(0,len(member_ids),500):
        rows.extend(db.execute(text(MEMBER_SQL),dict(members=member_ids[offset:offset+500],tenant_id=int(store_code))).mappings())
    profiles=resolve_profiles(rows)
    metadata['matched']=sum(r['member_match_status']=='已匹配' for r in profiles)
    metadata['unresolved']=len(profiles)-metadata['matched']
    return profiles,metadata
