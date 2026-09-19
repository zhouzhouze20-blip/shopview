"""Human-confirmed, versioned asset membership, separate from the ERP rule link."""
import hashlib
import json
from collections import Counter
from sqlalchemy import text

def asset_key(row):
    return f"{row['coupon_type']}:{row['asset_id']}"

def scope_key(config):
    return dict(store_code=config['store_code'],start_date=str(config['start_date']),
                end_date=str(config['end_date']),coupon_types=sorted(config['coupon_types']),
                erp_activity_id=config.get('erp_activity_id') or '')

def cohort_fingerprint(config,issues):
    values=sorted((asset_key(r),str(r['issue_id']),str(r.get('valid_from') or ''),
                   str(r.get('valid_to') or ''),str(r.get('erp_period') or '')) for r in issues)
    return hashlib.sha256(json.dumps([scope_key(config),values],ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def load_ownership(db,campaign_id):
    ready=bool(db.execute(text("SELECT to_regclass('public.coupon_campaign_ownership') IS NOT NULL")).scalar())
    if not ready or not campaign_id:
        return ready,None
    row=db.execute(text("""SELECT version,snapshot,confirmed_by,confirmed_at,note
      FROM coupon_campaign_ownership WHERE campaign_id=:id ORDER BY version DESC LIMIT 1"""),{'id':campaign_id}).mappings().first()
    return ready,dict(row) if row else None

def ownership_view(config,issues,record=None,storage_ready=True):
    current={asset_key(r) for r in issues}
    snapshot=(record or {}).get('snapshot') or {}
    scope_matches=snapshot.get('scope')==scope_key(config)
    has_snapshot=bool(record) and scope_matches
    owned=set(snapshot.get('asset_keys',[])) if has_snapshot else current
    fingerprint=cohort_fingerprint(config,issues)
    confirmed=has_snapshot and snapshot.get('fingerprint')==fingerprint
    counts=Counter(str(r.get('erp_period') or '').strip() for r in issues)
    missing=sum(n for p,n in counts.items() if p in ('','0'))
    configured=config.get('erp_activity_id') or ''
    conflicts=sum(n for p,n in counts.items() if p not in ('','0',configured))
    view=dict(status='confirmed' if confirmed else ('changed' if record else 'unconfirmed'),
              status_label='已人工确认' if confirmed else ('归属数据有变化，待复核' if record else '候选范围，未人工确认'),
              version=(record or {}).get('version',0),fingerprint=fingerprint,
              storage_ready=storage_ready,can_confirm=storage_ready and bool(issues) and conflicts==0,
              candidate_assets=len(current),report_assets=len(current & owned),confirmed_assets=len(owned) if has_snapshot else 0,
              unconfirmed_added=len(current-owned) if has_snapshot else len(current),
              confirmed_missing=len(owned-current) if has_snapshot else 0,
              missing_erp_period=missing,conflicting_erp_period=conflicts,
              erp_periods=[dict(erp_period=p or '空',assets=n) for p,n in sorted(counts.items())],
              confirmed_at=(record or {}).get('confirmed_at'),confirmed_by=(record or {}).get('confirmed_by'),
              note=(record or {}).get('note') or '',
              basis='先按门店、券种及初始发券有效期选候选资产；人工确认后保存资产集合。ERP规则编号不等于券资产归属。',
              change_basis='确认范围内仅保留仍可追溯资产；新增候选不自动加入。修改ERP编号后须重新确认。')
    return view,owned
