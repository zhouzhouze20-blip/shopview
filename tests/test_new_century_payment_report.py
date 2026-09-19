from datetime import date
from decimal import Decimal
from types import SimpleNamespace
import os

import pytest
from fastapi import HTTPException
from openpyxl import load_workbook
from sqlalchemy import text

from python_app.routers import new_century_payment_report as router
from python_app.services.new_century_payment_report import build_query, build_workbook, load_report, NOTE
from python_app.services.od0002_report import TrustedScopeSql


def kwargs(**overrides):
    return dict(start_date=date(2026, 7, 29), end_date=date(2026, 8, 28),
                scope_filter_sql=TrustedScopeSql(''), **overrides)


def test_dates_payment_validation_and_bound_parameters():
    sql, params = build_query(**kwargs(department_id="x' OR 1=1--"))
    assert params['end_exclusive'] == date(2026, 8, 29)
    assert "x' OR" not in sql
    assert params['department_id'] == "x' OR 1=1--"
    with pytest.raises(ValueError): build_query(**kwargs(pay_codes=['9999']))
    with pytest.raises(ValueError): build_query(**kwargs(pay_codes=[]))
    with pytest.raises(ValueError):
        build_query(start_date=date(2026, 8, 29), end_date=date(2026, 8, 28))


def test_workbook_keeps_codes_rates_nulls_and_all_rows():
    report = dict(start_date=date(2026, 7, 29), end_date=date(2026, 8, 28), note=NOTE,
        rows=[dict(rq=date(2026, 7, 29), mkt='603', bmname='部门', gz='6030101',
                   gzname='=1+1', paycode='0328', pname='支付', money=Decimal('-8.20'),
                   bl=Decimal('0.1234'), ml=None, xssr=Decimal('20'))],
        totals=dict(money=Decimal('-8.20'), ml=0, xssr=20))
    ws = load_workbook(build_workbook(report)).active
    assert ws['F5'].value == '0328'
    assert ws['E5'].data_type == 's'
    assert ws['I5'].value == .1234
    assert ws['I5'].number_format == '0.0000'
    assert ws['J5'].value is None
    assert ws['H6'].value == -8.2
    assert ws.freeze_panes == 'E5'


def test_module_permission_required_before_loading(monkeypatch):
    def deny(*a): raise HTTPException(403, 'denied')
    monkeypatch.setattr(router, 'require_permission', deny)
    with pytest.raises(HTTPException) as exc:
        router.report_for_request(date(2026,7,29), date(2026,8,28), None,None,None,None,None)
    assert exc.value.status_code == 403


def test_store_deny_blocks_report_and_export(monkeypatch):
    monkeypatch.setattr(router, 'require_permission', lambda *a: None)
    monkeypatch.setattr(router, 'load_business_scope', lambda *a, **k: SimpleNamespace(all_access=True, deny={'store': {'3'}}, allow={}))
    monkeypatch.setattr(router, '_od0002_store_id_for_code', lambda *a: '3')
    for endpoint in (router.get_report, router.export_report):
        with pytest.raises(HTTPException) as exc:
            endpoint(date(2026,7,29),date(2026,8,28),None,None,None,None,None)
        assert exc.value.status_code == 403


@pytest.mark.skipif(os.environ.get('SHOPVIEW_TEST_TEMP_DB') != '1', reason='Explicit temporary PostgreSQL fixture opt-in required')
def test_postgres_source_grain_and_permissions():
    # Temporary tables shadow public relations on this connection only; all work rolls back.
    from python_app.models.database import engine
    from sqlalchemy.orm import Session
    with engine.connect() as c:
        tx = c.begin()
        try:
            for ddl in [
                'salepay (billno numeric, rqsj timestamp, mkt text, paycode text, payname text, je numeric)',
                'salehead (billno numeric, djlb text)',
                'salegoods (billno numeric, gz text, rqsj timestamp)',
                'salegoodslist (sglbillno numeric, sgldate date, sgln2 numeric, sglxssr numeric)',
                'manaframe (mfcode text PRIMARY KEY, mfpcode text, mfcname text, mfchr1 text, mflc text)',
                'paymode (pmcode text PRIMARY KEY, pmname text, pmrevrate numeric)',
                'stores (store_id int, store_code text)',
                'area_category (category_code text, category_name text)',
            ]: c.execute(text('CREATE TEMP TABLE '+ddl+' ON COMMIT DROP'))
            c.execute(text("INSERT INTO stores VALUES (3,'603')"))
            c.execute(text("INSERT INTO manaframe VALUES ('60301',NULL,'部门',NULL,NULL), ('A','60301','柜A','C','1'), ('B','60301','柜B','C','1')"))
            # Duplicate category records must not multiply monetary results.
            c.execute(text("INSERT INTO area_category VALUES ('C','品类'),('C','品类')"))
            c.execute(text("INSERT INTO paymode VALUES ('0328','支付一',0.123456),('0329','支付二',1)"))
            c.execute(text("INSERT INTO salehead VALUES (1,'1'),(2,'4'),(3,NULL),(4,'1'),(5,'1'),(6,'1'),(7,'1'),(8,'1')"))
            c.execute(text("INSERT INTO salegoods VALUES (1,'A','2026-07-29'),(1,'B','2026-07-29'),(1,'Z','2026-05-31'),(2,'A','2026-08-28'),(3,'A','2026-08-28'),(4,'A','2026-08-29'),(5,'A','2026-07-29'),(6,'A','2026-05-31'),(7,'A','2026-07-29'),(8,'A','2026-07-29')"))
            c.execute(text("INSERT INTO salegoodslist VALUES (1,'2026-01-01',20,100),(1,'2025-12-31',999,999),(2,'2026-07-29',-4,-20),(3,'2026-07-29',2,10),(4,'2026-07-29',10,50),(5,'2026-07-29',10,50),(6,'2026-07-29',10,50),(7,'2025-12-31',10,50)"))
            c.execute(text("""INSERT INTO salepay VALUES
              (1,'2026-07-29','603','0328','旧名',30),
              (1,'2026-07-29','603','0328','旧名',10),
              (1,'2026-07-29','603','0328','新名',5),
              (1,'2026-07-29','603','0329','支付二',60),
              (2,'2026-08-28 23:59:59','603','0328','旧名',20),
              (3,'2026-08-28','603','0328','旧名',5),
              (4,'2026-08-29','603','0328','旧名',50),
              (5,'2026-07-29','601','0328','旧名',50),
              (6,'2026-07-29','603','0328','旧名',50),
              (7,'2026-07-29','603','0328','旧名',50),
              (8,'2026-07-29','603','0328','旧名',50)"""))
            db = Session(bind=c)
            report = load_report(db, **kwargs())
            rows = report['rows']
            assert len(rows) == 4  # payname remains a grouping dimension even though hidden in original SELECT.
            first = next(r for r in rows if r['payname']=='旧名' and r['gz']=='B')
            assert (first['money'], first['ml'], first['xssr'], first['bl']) == (40,40,200,Decimal('.1235'))
            assert report['totals'] == dict(money=80, ml=78, xssr=390)
            assert all(r['gz'] != 'Z' for r in rows)
            only_b = load_report(db, **kwargs(group_code='B'))
            assert only_b['totals']['money'] == 105
            denied = load_report(db, start_date=date(2026,7,29),end_date=date(2026,8,28),
                                 scope_filter_sql=TrustedScopeSql('AND 1=0'))
            assert denied['rows'] == []
            department = load_report(db, start_date=date(2026,7,29),end_date=date(2026,8,28),
                                     scope_filter_sql=TrustedScopeSql('AND dept.mfcode = :allowed'),scope_params={'allowed':'60301'})
            assert department['totals'] == report['totals']
        finally:
            tx.rollback()


def test_unscoped_user_remains_denied(monkeypatch):
    monkeypatch.setattr(router, 'require_permission', lambda *a: None)
    monkeypatch.setattr(router, 'load_business_scope', lambda *a, **k: SimpleNamespace(all_access=False, deny={}, allow={}))
    captured = {}
    def capture(db, **kw):
        captured.update(kw)
        return {}
    monkeypatch.setattr(router, 'load_report', capture)
    monkeypatch.setattr(router, '_od0002_scope_description', lambda scope: '')
    router.report_for_request(date(2026,7,29),date(2026,8,28),None,None,None,None,None)
    assert '1=0' in captured['scope_filter_sql'].value.replace(' ', '')
