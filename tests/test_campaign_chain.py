"""Ownership, current-profile ambiguity and post-period monetary boundaries."""
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import sys

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python_app'))
from services.activity_analysis.campaign_ownership import ownership_view,scope_key,cohort_fingerprint,asset_key
from services.activity_analysis.campaign_members import resolve_profiles,query_current_members,MEMBER_SQL
from services.activity_analysis.campaign_returns import summarize_returns,query_post_returns,LATE_RETURN_SQL
from services.activity_analysis.campaign import build_report,reuse_cohort,FLOWS_SQL,MISSING_ISSUES_SQL,COHORT_CTE

CONFIG=dict(id=1,name='测试',store_code='601',start_date=date(2026,8,14),end_date=date(2026,8,19),coupon_types=['B','H'],erp_activity_id='2205')
ASSET=dict(coupon_type='H',asset_id='001',issue_id='00001',erp_period='0',valid_from=date(2026,8,14),valid_to=date(2026,8,19))

def record(issues):
    return dict(version=1,snapshot=dict(scope=scope_key(CONFIG),asset_keys=[asset_key(r) for r in issues],fingerprint=cohort_fingerprint(CONFIG,issues)))

def test_erp_number_does_not_confirm_ownership_and_storage_is_required():
    view,_=ownership_view(CONFIG,[ASSET],storage_ready=False)
    assert view['status']=='unconfirmed'
    assert view['missing_erp_period']==1
    assert view['can_confirm'] is False

def test_confirmed_asset_set_never_expands_silently():
    added=dict(ASSET,asset_id='002',issue_id='00002')
    view,owned=ownership_view(CONFIG,[ASSET,added],record([ASSET]))
    assert owned=={'H:001'}
    assert view['report_assets']==1 and view['unconfirmed_added']==1
    assert view['status']=='changed'

def test_missing_confirmed_asset_and_modified_scope_are_flagged():
    view,_=ownership_view(CONFIG,[],record([ASSET]))
    assert view['confirmed_missing']==1 and not view['can_confirm']
    view,_=ownership_view(dict(CONFIG,erp_activity_id='2206'),[ASSET],record([ASSET]))
    assert view['status']=='changed'

def test_fingerprint_stable_for_reordering_and_sensitive_to_original_issue():
    rows=[ASSET,dict(ASSET,asset_id='002')]
    assert cohort_fingerprint(CONFIG,rows)==cohort_fingerprint(dict(CONFIG,coupon_types=['H','B']),rows[::-1])
    assert cohort_fingerprint(CONFIG,rows)!=cohort_fingerprint(CONFIG,[ASSET,dict(rows[1],issue_id='9')])
    assert ownership_view(CONFIG,[ASSET],record([ASSET]))[0]['status']=='confirmed'

def test_other_erp_period_blocks_confirmation():
    view,_=ownership_view(CONFIG,[dict(ASSET,erp_period='9999')])
    assert view['conflicting_erp_period']==1 and not view['can_confirm']

PROFILE=dict(member_no='TEST-001',scene_id='1',deleted=0,has_store_identity=True,level_code='01',dictionary_count=1,level_name='测试等级',admission_date=date(2026,8,1))

@pytest.mark.parametrize('updates,status',[
    ({'deleted':1},'会员主档已删除'),({'has_store_identity':False},'本店有效身份未匹配'),
    ({'level_code':None},'当前等级缺失'),({'dictionary_count':2},'等级字典缺失或重复'),
    ({'scene_id':None},'未匹配'),
])
def test_ambiguous_profiles_do_not_invent_current_grade(updates,status):
    r=resolve_profiles([dict(PROFILE,**updates)])[0]
    assert r['member_match_status']==status
    assert 'member_level' not in r
    assert r['activity_member_level']=='未接入历史等级'

def test_shared_member_duplicate_is_not_resolved_by_max_grade():
    r=resolve_profiles([PROFILE,dict(PROFILE,scene_id='2',level_name='另一个等级')])[0]
    assert r['member_match_status']=='会员号重复，待核查'
    assert 'member_level' not in r
    assert resolve_profiles([PROFILE])[0]['member_level']=='测试等级'
    assert 's.package_id=111' in MEMBER_SQL
    assert 'i.tenant_id=:tenant_id' in MEMBER_SQL

def test_missing_ods_and_607_never_fall_back_to_old_grade():
    db=Mock();db.execute.return_value.scalar.return_value=False
    for store in ['601','607']:
        rows,meta=query_current_members(db,store,['TEST-001'])
        assert rows==[] and meta['status']=='unavailable' and meta['unresolved']==1

def test_unknown_registration_is_unknown_not_false():
    r=build_report(CONFIG,[dict(member_no='TEST',coupon_type='H',amount=10,issue_date='2026-08-14',source_name='测试')],[],[])
    assert r['members'][0]['is_new_member'] is None

def test_post_returns_sum_brands_once_keep_original_period_unchanged():
    rows=[dict(billno='R1',sales=-1000),dict(billno='R1',sales=-626),dict(billno='R2',sales=-2000),dict(billno='S1',sales=500)]
    period=Decimal('10000')
    result=summarize_returns(rows,period,date(2026,9,6))
    assert period==10000 and result['return_sales']==-3626
    assert result['return_tickets']==2 and len(result['details'])==3
    assert result['reference_net_sales']==6374
    assert 'h.mkt=:store_code' in LATE_RETURN_SQL and 's.sglmarket=:store_code' in LATE_RETURN_SQL
    assert 'h.rqsj>=:end_exclusive' in LATE_RETURN_SQL

def test_post_return_lookup_deduplicates_multi_coupon_original_receipts():
    db=Mock();db.execute.return_value.mappings.return_value=[]
    query_post_returns(db,CONFIG,[dict(billno='1',ticket_kind='销售')]*2+[dict(billno='2',ticket_kind='退货')],100)
    params=db.execute.call_args.args[1]
    assert params['bills']==['1'] and params['end_exclusive']==date(2026,8,20)

def test_confirmation_requires_manage_permission_before_source_reads(monkeypatch):
    from routers import coupon_campaigns as route
    def denied(db,user,id,manage=False):
        assert manage is True
        raise HTTPException(403,'禁止')
    monkeypatch.setattr(route,'load_campaign',denied)
    db=Mock()
    with pytest.raises(HTTPException) as exc:
        route.confirm_ownership(1,route.OwnershipConfirmation(fingerprint='a'*64,expected_version=0,note='人工核对依据'),db,SimpleNamespace(user_id=1))
    assert exc.value.status_code==403
    db.execute.assert_not_called()

def setup_confirmation(monkeypatch,version=0,others=()):
    from routers import coupon_campaigns as route
    monkeypatch.setattr(route,'load_campaign',lambda *a,**kw:CONFIG)
    monkeypatch.setattr(route,'load_ownership',lambda *a:(True,dict(version=version)))
    monkeypatch.setattr(route,'limited_rows',lambda *a:[ASSET])
    db=Mock()
    result=Mock();result.mappings.return_value.one.return_value=CONFIG
    result.mappings.return_value.__iter__=Mock(return_value=iter(others))
    db.execute.return_value=result
    payload=route.OwnershipConfirmation(fingerprint=cohort_fingerprint(CONFIG,[ASSET]),expected_version=0,note='人工核对依据')
    return route,db,payload

def test_stale_version_is_rejected(monkeypatch):
    route,db,payload=setup_confirmation(monkeypatch,version=1)
    with pytest.raises(HTTPException) as exc:
        route.confirm_ownership(1,payload,db,SimpleNamespace(user_id=1))
    assert exc.value.status_code==409
    db.commit.assert_not_called()

def test_asset_change_since_preview_is_rejected(monkeypatch):
    route,db,payload=setup_confirmation(monkeypatch)
    payload.fingerprint='a'*64
    with pytest.raises(HTTPException) as exc:
        route.confirm_ownership(1,payload,db,SimpleNamespace(user_id=1))
    assert exc.value.status_code==409
    db.commit.assert_not_called()

def test_asset_cannot_belong_to_two_campaigns(monkeypatch):
    route,db,payload=setup_confirmation(monkeypatch,others=[dict(snapshot={'asset_keys':['H:001']})])
    with pytest.raises(HTTPException) as exc:
        route.confirm_ownership(1,payload,db,SimpleNamespace(user_id=1))
    assert exc.value.status_code==409
    db.commit.assert_not_called()

def test_confirmation_note_requires_real_content():
    from routers.coupon_campaigns import OwnershipConfirmation
    with pytest.raises(ValidationError):
        OwnershipConfirmation(fingerprint='a'*64,expected_version=0,note='     ')

def test_confirmation_persists_versioned_snapshot_and_actor(monkeypatch):
    import json
    route,db,payload=setup_confirmation(monkeypatch)
    db.execute.return_value.mappings.return_value.one.side_effect=[CONFIG,dict(version=1,confirmed_by=7,note=payload.note,confirmed_at='2026-09-06')]
    result=route.confirm_ownership(1,payload,db,SimpleNamespace(user_id=7))
    inserts=[call for call in db.execute.call_args_list if 'INSERT INTO coupon_campaign_ownership' in str(call.args[0])]
    assert len(inserts)==1
    params=inserts[0].args[1]
    assert params['version']==1 and params['user_id']==7
    assert json.loads(params['snapshot'])['asset_keys']==['H:001']
    assert result['version']==1
    db.commit.assert_called_once()

def test_migration_is_append_only_and_has_campaign_version_constraint(monkeypatch):
    import importlib.util
    path=Path(__file__).resolve().parents[1]/'python_app/alembic/versions/q6f7a8b9c0d1_campaign_ownership.py'
    spec=importlib.util.spec_from_file_location('qa_migration',path)
    migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
    execute=Mock();monkeypatch.setattr(migration.op,'execute',execute)
    migration.upgrade()
    sql=str(execute.call_args.args[0])
    assert 'UNIQUE(campaign_id,version)' in sql
    assert 'REFERENCES coupon_campaigns(id)' in sql
    assert 'INSERT' not in sql and 'UPDATE' not in sql
    assert migration.down_revision=='p5e6f7a8b9c0'

@pytest.mark.parametrize('source',[FLOWS_SQL,MISSING_ISSUES_SQL])
def test_reused_cohort_retains_downstream_predicates_and_exact_source_keys(source):
    row=dict(ASSET,issue_date=date(2026,8,10))
    sql,params=reuse_cohort(source,CONFIG,[row])
    assert sql.endswith(source[len(COHORT_CTE):])
    assert 'ROW_NUMBER' not in sql
    assert params['cohort_types']==['H'] and params['cohort_assets']==['001']
    assert params['cohort_issues']==['00001'] and params['cohort_dates']==[date(2026,8,10)]
    empty_sql,empty_params=reuse_cohort(source,CONFIG,[])
    assert empty_params['cohort_assets']==[]

def test_candidate_exposes_implied_end_date_lower_bound_for_existing_index():
    # start >= campaign start AND end >= start implies end >= campaign start.
    # Making that bound explicit avoids scanning all historical expiry dates.
    assert 'l.tcflenddate >= :start_date' in COHORT_CTE

def test_confirmation_database_timeout_is_not_success(monkeypatch):
    from sqlalchemy.exc import OperationalError
    from routers import coupon_campaigns as route
    def failed(*a):
        raise OperationalError('SELECT',{},Exception('timeout'))
    monkeypatch.setattr(route,'_confirm_ownership',failed)
    db=Mock()
    payload=route.OwnershipConfirmation(fingerprint='a'*64,expected_version=0,note='人工核对依据')
    with pytest.raises(HTTPException) as exc:
        route.confirm_ownership(1,payload,db,SimpleNamespace(user_id=1))
    assert exc.value.status_code==504
    db.rollback.assert_called_once()
    db.commit.assert_not_called()
