from datetime import date
from decimal import Decimal
from types import SimpleNamespace
import importlib.util
import os

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from python_app.services import cosmetics_payment_matching as svc
from python_app.routers import cosmetics_payment_matching as api


def selected(rows):
    return [SimpleNamespace(source_key=r['source_key'],version=r['version']) for r in rows]


@pytest.mark.parametrize('difference,accepted', [('0',True),('1',True),('-1',True),('1.0001',False),('-1.01',False)])
def test_exact_one_yuan_boundary(difference,accepted):
    left=[{'amount':str(Decimal('100')+Decimal(difference))}]
    right=[{'amount':'100'}]
    if accepted:
        assert svc.totals(left,right)[2]==Decimal(difference)
    else:
        with pytest.raises(ValueError,match='超过1元'): svc.totals(left,right)


@pytest.mark.parametrize('value',['NaN','Infinity',None,'abc'])
def test_invalid_money(value):
    with pytest.raises(ValueError): svc.amount(value)


def test_selection_fails_closed_for_changed_missing_duplicate_documents():
    row=svc.stamp(dict(source_key='a',amount='10',number='1'))
    with pytest.raises(ValueError,match='重复'): svc.validate_selection(selected([row,row]),[row])
    with pytest.raises(ValueError,match='权限'): svc.validate_selection(selected([row]),[])
    with pytest.raises(ValueError,match='变化'): svc.validate_selection(selected([row]),[svc.stamp(dict(source_key='a',amount='11',number='1'))])


def test_permissions_before_data(monkeypatch):
    calls=[]
    def require(db,user,code):
        calls.append(code)
        raise HTTPException(403,'denied')
    monkeypatch.setattr(api,'require_permission',require)
    with pytest.raises(HTTPException): api.access(None,None,True)
    assert calls==['settlement.cosmetics_matching.view']


def test_create_requires_separate_permission(monkeypatch):
    def require(db,user,code):
        if code.endswith('.create'): raise HTTPException(403,'denied')
    monkeypatch.setattr(api,'require_permission',require)
    with pytest.raises(HTTPException): api.access(None,None,True)


@pytest.fixture
def pg(monkeypatch):
    """Opt-in: PostgreSQL TEMP tables, no persistent source or business rows touched."""
    if os.environ.get('COSMETICS_PG_TEST')!='1': pytest.skip('set COSMETICS_PG_TEST=1 for rollback-only PostgreSQL checks')
    monkeypatch.setattr(svc, 'unassociated_receipt_numbers', lambda db, store, supplier, numbers, **kw: set(numbers))
    from python_app.models.database import engine
    with engine.connect() as connection:
        tx=connection.begin()
        db=Session(bind=connection)
        schemas={
            'users':'user_id integer primary key',
            'stores':'store_id integer, store_code text',
            'supplierbase':'sbid text,sbcname text,sbtaxno text',
            'manaframe':'mfcode text,mfcname text,mfpcode text,mflc text',
            'codebrand':'cbid text,cbcname text',
            'goodscat':'catcode text,catcname text',
            'jxcgoodslist':'''jglseq bigint,jglmarket text,jglbillno text,jglsupid text,
              jglfsdate date,jglhsjjje numeric,jglmfid text,jglppcode text,jglcatid text,
              jgltran text,jglbillid text,jgldac text''',
            'br_income_normal_inv_main':'''invoiceno text,qdzphm text,invoicecode text,
              buyertaxno text,salertaxno text,invoicestatus text,use_billno text,
              totalamount text,invoicedate text,salername text,remark text''',
        }
        for name,columns in schemas.items():
            db.execute(text(f'CREATE TEMP TABLE {name} ({columns}) ON COMMIT DROP'))
        db.execute(text('INSERT INTO users VALUES (1)'))
        db.execute(text("INSERT INTO stores VALUES (1,'601'),(2,'602'),(3,'603')"))
        db.execute(text("INSERT INTO supplierbase VALUES ('S1','测试供应商','TAX1')"))
        path='python_app/alembic/versions/u0d1e2f3a4b5_cosmetics_payment_matching.py'
        spec=importlib.util.spec_from_file_location('matching_migration',path)
        migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
        from contextlib import nullcontext
        class Op:
            def get_context(self): return self
            def autocommit_block(self): return nullcontext()
            def execute(self,sql):
                if sql.startswith('CREATE TABLE'):
                    db.execute(text(sql.replace('CREATE TABLE','CREATE TEMP TABLE',1)))
        migration.op=Op();migration.upgrade()
        signed_spec=importlib.util.spec_from_file_location('signed_migration','python_app/alembic/versions/w2f3a4b5c6d8_cosmetics_signed_receipts.py')
        signed=importlib.util.module_from_spec(signed_spec);signed_spec.loader.exec_module(signed)
        class SignedOp(Op):
            def execute(self,sql):
                if sql.startswith('ALTER TABLE'): db.execute(text(sql))
        signed.op=SignedOp();signed.upgrade()
        try: yield db
        finally:
            db.close();tx.rollback()


def seed(db,invoice_count=10,receipt_count=5,store='601'):
    for i in range(invoice_count):
        db.execute(text('''INSERT INTO br_income_normal_inv_main VALUES
          (:no,NULL,'','913204001347930261','TAX1','0',NULL,:amount,'2026-07-02','测试供应商')'''),
          {'no':f'INV{i}','amount':str(Decimal(1100)/invoice_count)})
    for i in range(receipt_count):
        db.execute(text('''INSERT INTO jxcgoodslist VALUES
          (:seq,:store,:no,'S1','2026-06-03',:amount,'G1',NULL,NULL,'1','404','D')'''),
          {'seq':i,'store':store,'no':f'RC{i}','amount':Decimal(1100)/receipt_count})


def payload(db,store='601'):
    left=svc.invoices(db,store,'S1')
    right=svc.receipts(db,store,'S1','',{})
    return SimpleNamespace(store=store,supplier='S1',payment_month='2026-08',invoices=selected(left),receipts=selected(right))


@pytest.mark.parametrize('invoice_count,receipt_count',[(10,5),(11,2)])
def test_many_to_many_cross_month_save_and_snapshot(pg,invoice_count,receipt_count):
    seed(pg,invoice_count,receipt_count)
    result=svc.create_match(pg,payload(pg),1,'',{})
    assert result['difference']=='0'
    assert len(result['invoices'])==invoice_count and len(result['receipts'])==receipt_count
    assert pg.execute(text('SELECT payment_month FROM cosmetics_payment_matches')).scalar()=='2026-08'
    assert svc.invoices(pg,'601','S1')==[]
    assert svc.receipts(pg,'601','S1','',{})==[]
    assert pg.execute(text('SELECT count(*) FROM cosmetics_payment_match_lines')).scalar()==invoice_count+receipt_count


def test_shared_buyer_invoice_cannot_be_reused_across_stores(pg):
    seed(pg)
    assert len(svc.invoices(pg,'602','S1'))==10
    svc.create_match(pg,payload(pg),1,'',{})
    assert svc.invoices(pg,'602','S1')==[]
    assert svc.invoices(pg,'603','S1')==[]


def test_scope_cannot_expose_partial_receipt(pg):
    seed(pg,1,1)
    pg.execute(text("INSERT INTO jxcgoodslist VALUES (90,'601','RC0','S1','2026-06-03',5,'DENIED',NULL,NULL,'1','404','D')"))
    assert svc.receipts(pg,'601','S1'," AND j.jglmfid='G1'",{})==[]
    rows=svc.receipts(pg,'601','S1','',{},group_code='G1')
    assert len(rows)==1 and Decimal(rows[0]['amount'])==1105
    assert svc.supplier_options(pg,'601'," AND j.jglmfid='G1'",{})['items']==[]


def test_invoice_status_conflicting_duplicate_and_dates(pg):
    seed(pg,1,1)
    assert svc.invoices(pg,'601','S1',date_from=date(2026,8,1))==[]
    pg.execute(text("UPDATE br_income_normal_inv_main SET invoicestatus='8'"))
    assert svc.invoices(pg,'601','S1')==[]
    pg.execute(text("UPDATE br_income_normal_inv_main SET invoicestatus='0'"))
    pg.execute(text('INSERT INTO br_income_normal_inv_main SELECT * FROM br_income_normal_inv_main'))
    assert len(svc.invoices(pg,'601','S1'))==1
    pg.execute(text("INSERT INTO br_income_normal_inv_main SELECT invoiceno,qdzphm,invoicecode,buyertaxno,salertaxno,invoicestatus,use_billno,'9',invoicedate,salername FROM br_income_normal_inv_main LIMIT 1"))
    assert svc.invoices(pg,'601','S1')==[]


def test_stale_submission_writes_nothing(pg):
    seed(pg)
    request=payload(pg)
    pg.execute(text("UPDATE jxcgoodslist SET jglhsjjje=jglhsjjje+1 WHERE jglseq=0"))
    with pytest.raises(ValueError,match='变化'):svc.create_match(pg,request,1,'',{})
    assert pg.execute(text('SELECT count(*) FROM cosmetics_payment_matches')).scalar()==0


def test_database_constraints_block_duplicate_source(pg):
    from sqlalchemy.exc import IntegrityError
    seed(pg)
    svc.create_match(pg,payload(pg),1,'',{})
    with pytest.raises(IntegrityError):
        with pg.begin_nested():
            pg.execute(text("""INSERT INTO cosmetics_payment_match_lines(match_number,kind,source_key,document_number,amount,snapshot)
              SELECT match_number,kind,source_key,document_number,amount,snapshot FROM cosmetics_payment_match_lines LIMIT 1"""))


def test_api_history_reuses_whole_document_scope(pg,monkeypatch):
    seed(pg,11,2)
    request=payload(pg)
    monkeypatch.setattr(api,'access',lambda *a,**k:('',{}))
    result=api.create(request,pg,SimpleNamespace(user_id=1))
    history=api.history('601','S1','2026-08',pg,SimpleNamespace(user_id=1))
    assert history['items'][0]['number']==result['number']
    assert len(history['items'][0]['invoices'])==11
    monkeypatch.setattr(api,'access',lambda *a,**k:(" AND j.jglmfid='OTHER'",{}))
    assert api.history('601','S1','2026-08',pg,SimpleNamespace(user_id=1))=={'items':[]}


def test_denied_store_supplier_and_group_scopes(pg):
    seed(pg,1,1)
    for sql,params in [
        (" AND st.store_id::text=ANY(:stores)",{'stores':['2']}),
        (" AND j.jglsupid<>:denied",{'denied':'S1'}),
        (" AND j.jglmfid=ANY(:groups)",{'groups':['OTHER']})]:
        assert svc.receipts(pg,'601','S1',sql,params)==[]
        assert svc.supplier_options(pg,'601',sql,params)['items']==[]


def test_associated_receipts_excluded_and_submit_rechecked(pg,monkeypatch):
    seed(pg,11,2)
    request=payload(pg)
    monkeypatch.setattr(svc,'unassociated_receipt_numbers',lambda db,store,supplier,numbers,**kw:{'RC1'})
    assert [r['number'] for r in svc.receipts(pg,'601','S1','',{})]==['RC1']
    with pytest.raises(ValueError,match='状态已改变'):
        svc.create_match(pg,request,1,'',{})
    assert pg.execute(text('SELECT count(*) FROM cosmetics_payment_matches')).scalar()==0
    # History visibility must not disappear after a previously matched receipt settles.
    assert len(svc.receipts(pg,'601','S1','',{},include_bound=True))==2



def test_local_status_filter_and_staleness(pg):
    from python_app.services import receipt_settlement_status as status
    pg.execute(text("CREATE TEMP TABLE cosmetics_receipt_settlement_sync (singleton boolean,source_at timestamptz,published_at timestamptz,row_count bigint) ON COMMIT DROP"))
    pg.execute(text("CREATE TEMP TABLE cosmetics_receipt_settlement_state (store_code text,supplier_code text,receipt_number text,linked_rows bigint) ON COMMIT DROP"))
    with pytest.raises(status.SettlementStatusUnavailable,match='首次同步'):
        status.sync_status(pg)
    pg.execute(text("INSERT INTO cosmetics_receipt_settlement_sync VALUES(true,now(),now(),3)"))
    pg.execute(text("INSERT INTO cosmetics_receipt_settlement_state VALUES ('601','S1','A',0),('601','S1','B',1),('602','S1','C',0)"))
    assert status.unassociated_receipt_numbers(pg,'601','S1',['A','B','C','MISSING'])=={'A'}
    pg.execute(text("UPDATE cosmetics_receipt_settlement_sync SET source_at=now()-interval '2 hours'"))
    assert status.sync_status(pg)['stale'] is True
    assert status.unassociated_receipt_numbers(pg,'601','S1',['A'])=={'A'}
    with pytest.raises(status.SettlementStatusUnavailable,match='超过1小时'):
        status.unassociated_receipt_numbers(pg,'601','S1',['A'],require_fresh=True)


def test_atomic_snapshot_publication(pg):
    from pathlib import Path
    from uuid import uuid4
    from sqlalchemy.exc import DBAPIError
    schema='receipt_test_'+uuid4().hex
    pg.execute(text('CREATE SCHEMA '+schema))
    sql=Path('python_app/sql/cosmetics_receipt_settlement.sql').read_text().replace('public.',schema+'.').replace('pg_catalog,public','pg_catalog,'+schema)
    pg.execute(text(sql))
    stage=schema+'.cosmetics_receipt_settlement_stage'
    state=schema+'.cosmetics_receipt_settlement_state'
    def data(batch,number,linked,age):
        pg.execute(text(f"""INSERT INTO {stage}(batch_id,row_kind,source_key,source_at,source_hash,store_code,supplier_code,receipt_number,batch_rows,linked_rows)
            VALUES(:b,'data','601:S1:'||:n,now()+make_interval(secs=>:age),10,'601','S1',:n,1,:linked)"""),dict(b=batch,n=number,linked=linked,age=age))
    def manifest(batch,count,age):
        pg.execute(text(f"""INSERT INTO {stage}(batch_id,row_kind,source_key,source_at,source_hash,expected_rows,expected_hash)
            VALUES(:b,'manifest','-',now()+make_interval(secs=>:age),0,:n,:h)"""),dict(b=batch,n=count,h=count*10,age=age))
    data('one','A',1,0);data('one','B',0,0);manifest('one',2,0)
    assert pg.execute(text('SELECT count(*) FROM '+state)).scalar()==2
    data('two','A',0,1)
    # Incomplete transfer cannot replace the previously published version.
    with pytest.raises(DBAPIError):
        with pg.begin_nested():manifest('two',2,1)
    assert pg.execute(text("SELECT linked_rows FROM "+state+" WHERE receipt_number='A'")).scalar()==1
    manifest('two',1,1)
    # Unlinking and source deletion are both reflected by full replacement.
    assert pg.execute(text('SELECT receipt_number,linked_rows FROM '+state)).all()==[('A',0)]
    assert pg.execute(text('SELECT count(*) FROM '+stage)).scalar()==0


def test_invoice_remark_keeps_all_duplicate_copy_notes(pg):
    seed(pg, invoice_count=1, receipt_count=1)
    pg.execute(text("UPDATE br_income_normal_inv_main SET remark='迪奥七月'"))
    pg.execute(text('INSERT INTO br_income_normal_inv_main SELECT * FROM br_income_normal_inv_main'))
    pg.execute(text("UPDATE br_income_normal_inv_main SET remark='补充备注' WHERE ctid=(SELECT max(ctid) FROM br_income_normal_inv_main)"))
    rows=svc.invoices(pg,'601','S1')
    assert len(rows)==1
    assert '迪奥七月' in rows[0]['remark'] and '补充备注' in rows[0]['remark']
    assert Decimal(rows[0]['amount'])==Decimal('1100')


def test_signed_receipt_matching_save_and_locks(pg):
    seed(pg,1,1)
    pg.execute(text("UPDATE jxcgoodslist SET jglhsjjje=1400"))
    pg.execute(text("""INSERT INTO jxcgoodslist VALUES
      (100,'601','RC0','S1','2026-06-04',-200,'G1',NULL,NULL,'2','409','C'),
      (101,'601','NEG','S1','2026-06-04',-100,'G1',NULL,NULL,'1','404','D'),
      (102,'601','ZERO','S1','2026-06-04',0,'G1',NULL,NULL,'1','404','D'),
      (103,'601','ADJ','S1','2026-06-04',-999,'G1',NULL,NULL,'W','409','C')"""))
    rows=svc.receipts(pg,'601','S1','',{})
    assert {r['source_key'] for r in rows}=={'601:404:RC0','601:409:RC0','601:404:NEG'}
    assert {r['document_type_name'] for r in rows}=={'验收单','负数验收单','退厂单'}
    result=svc.create_match(pg,payload(pg),1,'',{})
    assert Decimal(result['receipt_amount'])==1100
    assert Decimal(result['difference'])==0
    assert pg.execute(text("SELECT count(*) FROM cosmetics_payment_match_lines WHERE amount<0")).scalar()==2
    assert svc.receipts(pg,'601','S1','',{})==[]


def test_return_scope_and_settlement_filter(pg,monkeypatch):
    pg.execute(text("""INSERT INTO jxcgoodslist VALUES
      (100,'601','RETURN','S1','2026-06-04',-200,'G1',NULL,NULL,'2','409','C'),
      (101,'601','RETURN','S1','2026-06-04',-100,'DENIED',NULL,NULL,'2','409','C')"""))
    assert svc.receipts(pg,'601','S1'," AND j.jglmfid='G1'",{})==[]
    assert Decimal(svc.receipts(pg,'601','S1','',{})[0]['amount'])==-300
    monkeypatch.setattr(svc,'unassociated_receipt_numbers',lambda *args,**kwargs:set())
    assert svc.receipts(pg,'601','S1','',{})==[]


def test_negative_net_total_still_rejected():
    with pytest.raises(ValueError,match='大于零'):
        svc.totals([{'amount':'100'}],[{'amount':'100'},{'amount':'-200'}])
