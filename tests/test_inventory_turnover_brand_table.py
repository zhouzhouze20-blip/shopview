"""DDL, aggregation and trigger tests isolated in a rollback-only schema."""
import os
from pathlib import Path
from uuid import uuid4
from decimal import Decimal
import pytest
from sqlalchemy import text
from python_app.models.database import engine
from python_app.routers.inventory_turnover import summarize_brands


def test_brand_table_matches_frontend_and_tracks_detail_mutations():
    if os.getenv('SHOPVIEW_TEST_DATABASE') != '1':
        pytest.skip('requires explicit database integration test')
    schema = 'test_turnover_' + uuid4().hex
    ddl = Path('python_app/sql/inventory_turnover_brand.sql').read_text().replace('public.', schema + '.')
    with engine.connect() as conn:
        tx = conn.begin()
        try:
            conn.execute(text("SET LOCAL statement_timeout='120s'"))
            conn.execute(text(f'CREATE SCHEMA {schema}'))
            conn.execute(text(f'CREATE TABLE {schema}.inventory_turnover_monthly (LIKE public.inventory_turnover_monthly INCLUDING ALL)'))
            conn.execute(text(f'INSERT INTO {schema}.inventory_turnover_monthly SELECT * FROM public.inventory_turnover_monthly'))
            conn.exec_driver_sql(ddl)
            source = [dict(r) for r in conn.execute(text(f'SELECT * FROM {schema}.inventory_turnover_monthly ORDER BY department_code,group_code,supplier_code,operation_method')).mappings()]
            actual = [dict(r) for r in conn.execute(text(f'SELECT * FROM {schema}.inventory_turnover_brand_monthly')).mappings()]
            assert source, 'test needs seeded detail data'
            key = lambda r: (r['financial_month'],r['store_code'],r['department_code'] or '',r['group_code'])
            indexed = {key(r): r for r in actual}
            expected = summarize_brands(source)
            assert len(expected) == len(actual)
            for row in expected:
                target = indexed[key(row)]
                for field in ['sales_quantity','sales_revenue','sales_cost_ex_tax','ending_quantity',
                              'ending_cost_ex_tax','average_cost_ex_tax','turnover_rate','turnover_days',
                              'stock_sales_ratio','stock_cover_days','supplier_count','exception_count']:
                    if row[field] is None: assert target[field] is None
                    else: assert abs(Decimal(row[field])-Decimal(target[field])) < Decimal('0.00000001'), (key(row),field)
            where = "financial_month='2026-08' AND store_code='603' AND group_code='6030101036'"
            def summary():
                return conn.execute(text(f'SELECT * FROM {schema}.inventory_turnover_brand_monthly WHERE '+where)).mappings().one()
            initial = dict(summary())
            assert initial['supplier_count'] == 2
            # A null source amount must propagate through the physical aggregate.
            conn.execute(text(f"UPDATE {schema}.inventory_turnover_monthly SET average_cost_ex_tax=NULL WHERE {where} AND supplier_code='00062'"))
            assert summary()['average_cost_ex_tax'] is None and summary()['turnover_rate'] is None
            conn.execute(text(f"DELETE FROM {schema}.inventory_turnover_monthly WHERE {where} AND supplier_code='00062'"))
            assert summary()['supplier_count'] == 1 and summary()['turnover_rate'] is not None
            conn.execute(text(f"INSERT INTO {schema}.inventory_turnover_monthly SELECT * FROM public.inventory_turnover_monthly WHERE {where} AND supplier_code='00062'"))
            assert summary()['supplier_count'] == 2
            assert summary()['sales_revenue'] == initial['sales_revenue']
            conn.execute(text(f'DELETE FROM {schema}.inventory_turnover_monthly WHERE {where}'))
            assert conn.execute(text(f'SELECT count(*) FROM {schema}.inventory_turnover_brand_monthly WHERE {where}')).scalar() == 0
        finally:
            tx.rollback()
