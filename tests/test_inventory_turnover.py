from datetime import date
from decimal import Decimal
from types import SimpleNamespace
import os

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from python_app.routers import inventory_turnover as api
from python_app.services.monthly_followup_report import financial_month_period


def test_filters_bind_values_and_validate_month():
    params = {}
    sql = api.filter_where(' WHERE 1=1', params, "603' OR 1=1--", '6030101', '2026-08')
    assert "603' OR" not in sql
    assert params['store_code'] == "603' OR 1=1--"
    with pytest.raises(HTTPException): api.filter_where('', {}, financial_month='2026-13')


def test_permission_and_brand_scope_fail_closed(monkeypatch):
    def deny(*args): raise HTTPException(403, 'denied')
    monkeypatch.setattr(api, 'require_permission', deny)
    with pytest.raises(HTTPException): api.scoped_where(None, None)
    monkeypatch.setattr(api, 'require_permission', lambda *args: None)
    monkeypatch.setattr(api, 'load_business_scope', lambda *a, **kw: SimpleNamespace(all_access=True, allow={}, deny={'brand': {'secret'}}))
    with pytest.raises(HTTPException): api.scoped_where(None, None)


def test_scope_applies_all_supported_dimensions(monkeypatch):
    monkeypatch.setattr(api, 'require_permission', lambda *args: None)
    monkeypatch.setattr(api, 'load_business_scope', lambda *a, **kw: SimpleNamespace(all_access=False,
        allow={'store': {'3'}}, deny={'supplier': {'00062'}, 'department': {'6030102'}}))
    sql, params = api.scoped_where(None, None)
    assert 'r.store_id::text' in sql and 'r.supplier_code' in sql and 'r.department_code' in sql
    assert params['turnover_allow_store'] == ['3']
    assert params['turnover_deny_supplier'] == ['00062']


@pytest.fixture
def isolated_db():
    if os.getenv('SHOPVIEW_TEST_DATABASE') != '1': pytest.skip('requires explicit database integration test')
    from python_app.models.database import engine
    with engine.connect() as conn:
        transaction = conn.begin()
        try:
            conn.execute(text("SET LOCAL statement_timeout='120s'"))
            for table in ['salegoodslist', 'goodsstock_bak', 'stores', 'manaframe', 'supplierbase', 'area_category', 'inventory_turnover_monthly']:
                conn.execute(text(f'CREATE TEMP TABLE {table} ON COMMIT DROP AS SELECT * FROM public.{table} WITH NO DATA'))
            conn.execute(text("INSERT INTO stores(store_id,store_code,store_name) VALUES(3,'603','测试门店')"))
            conn.execute(text("INSERT INTO manaframe(mfcode,mfcname,mfpcode) VALUES('g','测试柜组','d'),('d','测试部门',NULL)"))
            conn.execute(text("""INSERT INTO salegoodslist(sglmarket,sglmfid,sglsupid,sglwmid,sglhsrq,sglsl,sglxssr,sgln13,sgljjtax)
              SELECT '603','g','new','1',d,0,0,NULL,0.13 FROM generate_series('2026-07-29'::date,'2026-08-28'::date,'1 day') d"""))
            conn.execute(text("""INSERT INTO salegoodslist(sglmarket,sglmfid,sglsupid,sglwmid,sglhsrq,sglsl,sglxssr,sgln13,sgljjtax)
              VALUES('603','g','new','1','2026-08-28',10,150,113,0.13),('603','g','new','1','2026-08-28',10,150,109,0.09),
              ('603','g','new','1','2026-08-28',-2,-30,-22.6,0.13)"""))
            conn.execute(text("""INSERT INTO goodsstock_bak(gstdate,gstmarket,gstmfid,gstsupid,gstwmid,gstkcsl,gstkcbhsjjje)
              SELECT d,'603','g','new','1',31,310 FROM generate_series('2026-07-29'::date,'2026-08-28'::date,'1 day') d
              UNION ALL SELECT d,'603','g','old','1',0,-0.0001 FROM generate_series('2026-07-29'::date,'2026-08-28'::date,'1 day') d"""))
            yield conn
        finally: transaction.rollback()


def rows(db, year=2026, month=8, cutoff='2026-08-28'):
    return list(db.execute(text('SELECT * FROM public.inventory_turnover_rows(:y,:m,CAST(:d AS date))'), dict(y=year,m=month,d=cutoff)).mappings())


def test_financial_amounts_supplier_grain_returns_and_tax(isolated_db):
    result = {r['supplier_code']: r for r in rows(isolated_db)}
    old, new = result['old'], result['new']
    assert old['sales_quantity'] == old['sales_revenue'] == 0
    assert old['ending_quantity'] == 0 and old['turnover_rate'] is None
    assert new['sales_quantity'] == 18 and new['sales_revenue'] == 270
    assert new['sales_cost_ex_tax'] == 180  # 113/1.13 + 109/1.09 - 22.6/1.13
    assert new['average_cost_ex_tax'] == new['ending_cost_ex_tax'] == 310
    assert abs(new['turnover_days']*new['turnover_rate']-31) < Decimal('0.00000001')
    assert abs(new['stock_sales_ratio']-Decimal(310)/180) < Decimal('0.00000001')
    assert new['data_status'] == '正常'


def test_missing_snapshot_and_tax_never_turn_into_valid_ratios(isolated_db):
    isolated_db.execute(text("DELETE FROM goodsstock_bak WHERE gstdate='2026-08-01'"))
    result = rows(isolated_db)
    assert all(r['average_cost_ex_tax'] is None and r['turnover_rate'] is None for r in result)
    assert all('库存快照缺日' in r['data_status'] for r in result)
    isolated_db.execute(text("UPDATE salegoodslist SET sgljjtax=NULL WHERE sgln13<>0"))
    new = next(r for r in rows(isolated_db) if r['supplier_code']=='new')
    assert new['sales_cost_ex_tax'] is None and new['stock_sales_ratio'] is None


def test_period_boundaries_match_existing_system(isolated_db):
    # Seed an old snapshot key so even empty synthetic months produce a diagnostic row.
    for year, month in [(2026,1),(2026,2),(2026,3),(2024,3),(2026,12)]:
        start, end = financial_month_period(year,month)
        isolated_db.execute(text("INSERT INTO inventory_turnover_monthly(financial_month,store_code,group_code,supplier_code,operation_method) VALUES(:p,'603','g','old','1')"), {'p':f'{year}-{month:02}'})
        row = rows(isolated_db,year,month,str(end))[0]
        assert (row['period_start'],row['period_end'])==(start,end)
        assert row['elapsed_days']==(end-start).days+1


def test_midmonth_uses_elapsed_days_and_removed_keys_are_zeroed(isolated_db):
    new = next(r for r in rows(isolated_db,cutoff='2026-08-05') if r['supplier_code']=='new')
    assert new['elapsed_days']==8 and new['average_cost_ex_tax']==310
    isolated_db.execute(text("INSERT INTO inventory_turnover_monthly(financial_month,store_code,group_code,supplier_code,operation_method) VALUES('2026-08','603','g','removed','1')"))
    removed = next(r for r in rows(isolated_db) if r['supplier_code']=='removed')
    assert removed['sales_quantity']==removed['ending_quantity']==removed['average_cost_ex_tax']==0


def brand_member(supplier, cost, average, ending, **overrides):
    row = dict(store_code='603', department_code='d', financial_month='2026-08', group_code='g',
               supplier_code=supplier, operation_method='1', period_start=date(2026, 7, 29),
               period_end=date(2026, 8, 28), as_of_date=date(2026, 8, 28), elapsed_days=31,
               inventory_days=31, sales_days=31, updated_at=date(2026, 9, 16),
               sales_quantity=Decimal(1), sales_revenue=Decimal(100), ending_quantity=Decimal(2),
               sales_cost_ex_tax=Decimal(cost), average_cost_ex_tax=Decimal(average),
               ending_cost_ex_tax=Decimal(ending), data_status='正常')
    return {**row, **overrides}


def test_brand_weighted_ratios_and_supplier_separation():
    members = [brand_member('a', '100', '50', '100'), brand_member('b', '20', '100', '200')]
    row, = api.summarize_brands(members)
    assert row['turnover_rate'] == Decimal('0.8')  # not average of 2 and 0.2
    assert row['turnover_days'] == Decimal('38.75')
    assert row['stock_sales_ratio'] == Decimal('2.5')
    assert row['supplier_count'] == 2 and row['exception_count'] == 0
    assert len(api.summarize_brands(members + [brand_member('c', '1', '2', '3', group_code='other')])) == 2


def test_brand_missing_amount_and_dates_do_not_become_zero():
    good = brand_member('a', '100', '50', '100')
    missing = brand_member('b', '20', '100', '200', average_cost_ex_tax=None, data_status='库存快照缺日')
    row, = api.summarize_brands([good, missing])
    assert row['average_cost_ex_tax'] is None and row['turnover_rate'] is None
    assert row['exception_count'] == 1 and '库存快照缺日' in row['data_status']
    row, = api.summarize_brands([good, {**missing, 'sales_cost_ex_tax': None}])
    assert row['stock_sales_ratio'] is None and row['sales_cost_ex_tax'] is None
    row, = api.summarize_brands([good, {**good, 'as_of_date': date(2026, 8, 27)}])
    assert row['turnover_days'] is None and row['stock_sales_ratio'] is None
    assert '统计期间不一致' in row['data_status']


def test_brand_negative_supplier_tail_preserved():
    row, = api.summarize_brands([brand_member('old', '0', '-0.0001', '-0.0001', data_status='平均库存非正'),
                               brand_member('new', '100', '200', '300')])
    assert row['average_cost_ex_tax'] == Decimal('199.9999')
    assert row['stock_sales_ratio'] == Decimal('2.999999')
    assert row['exception_count'] == 1
