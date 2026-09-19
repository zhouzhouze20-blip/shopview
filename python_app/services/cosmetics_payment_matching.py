"""Whole-invoice / whole-receipt payment matching; all amounts are Decimal.

404 receipts and 409 supplier returns retain their signed ERP movement amounts.
A receipt is offered only when every source line is visible and it has one supplier.
The two stores sharing a buyer tax number also share one global invoice lock.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from sqlalchemy import text
from services.receipt_settlement_status import unassociated_receipt_numbers

STORES = {
    '601': ('常州购物中心', '913204001347930261'),
    '602': ('常州百货大楼', '913204001347930261'),
    '603': ('常州新世纪商城', '913204001371533745'),
}
LIMIT = 1000


def amount(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError('单据金额无效，请核实源数据') from None
    if not result.is_finite():
        raise ValueError('单据金额无效，请核实源数据')
    return result


def totals(invoices, receipts):
    if not invoices or not receipts:
        raise ValueError('请同时勾选发票和验收单')
    left = sum((amount(row['amount']) for row in invoices), Decimal(0))
    right = sum((amount(row['amount']) for row in receipts), Decimal(0))
    if left <= 0 or right <= 0:
        raise ValueError('配票金额必须大于零')
    if abs(left - right) > Decimal('1.00'):
        raise ValueError('发票与验收单金额差额超过1元，不能生成配票单')
    return left, right, left - right


def stamp(row):
    result = dict(row)
    result['amount'] = str(amount(result['amount']))
    for key, value in list(result.items()):
        if hasattr(value, 'isoformat'):
            result[key] = value.isoformat()
    result['version'] = hashlib.sha256(json.dumps(result, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()
    return result


def ensure_ready(db):
    if not db.execute(text("SELECT to_regclass('cosmetics_payment_matches')")).scalar():
        raise ValueError('配票模块数据表尚未初始化，请先执行数据库迁移')


def receipt_query(scope_sql):
    # Scope is evaluated per source line, before a complete document can be exposed.
    # Filtering by group happens AFTER aggregation, so it never changes the amount.
    return f"""
    WITH docs AS (
      SELECT j.jglmarket AS store_code, j.jglbillno AS number,
        j.jglmarket || ':' || j.jglbillid || ':' || j.jglbillno AS source_key,
        j.jglbillid AS document_type,
        CASE WHEN j.jglbillid='409' THEN '退厂单'
             WHEN SUM(j.jglhsjjje)<0 THEN '负数验收单' ELSE '验收单' END AS document_type_name,
        MIN(j.jglsupid) AS supplier_code, MIN(sb.sbcname) AS supplier_name,
        MIN(j.jglfsdate)::date AS date,
        SUM(j.jglhsjjje)::text AS amount,
        ARRAY_AGG(DISTINCT j.jglmfid ORDER BY j.jglmfid) AS groups,
        STRING_AGG(DISTINCT j.jglmfid || ' ' || COALESCE(mf.mfcname,''), '、') AS group_names,
        MD5(STRING_AGG(j.jglseq::text || ':' || COALESCE(j.jglhsjjje::text,'NULL'), ',' ORDER BY j.jglseq)) AS source_revision
      FROM jxcgoodslist j
      LEFT JOIN stores st ON st.store_code=j.jglmarket
      LEFT JOIN supplierbase sb ON sb.sbid=j.jglsupid
      LEFT JOIN manaframe mf ON mf.mfcode=j.jglmfid
      LEFT JOIN manaframe dept ON dept.mfcode=mf.mfpcode
      LEFT JOIN codebrand cb ON cb.cbid=j.jglppcode
      LEFT JOIN goodscat gc ON gc.catcode=j.jglcatid
      WHERE j.jglmarket=:store AND ((j.jgltran='1' AND j.jglbillid='404') OR (j.jgltran='2' AND j.jglbillid='409'))
        AND NULLIF(TRIM(j.jglbillno),'') IS NOT NULL
        AND (:supplier='' OR (j.jglbillid,j.jglbillno) IN (
          SELECT p.jglbillid,p.jglbillno FROM jxcgoodslist p
          WHERE p.jglmarket=:store AND ((p.jgltran='1' AND p.jglbillid='404') OR (p.jgltran='2' AND p.jglbillid='409'))
            AND p.jglsupid=:supplier))
        AND (:keys_empty OR (j.jglmarket || ':' || j.jglbillid || ':' || j.jglbillno)=ANY(:keys))
      GROUP BY j.jglmarket,j.jglbillid,j.jglbillno
      HAVING COUNT(DISTINCT j.jglsupid)=1
        AND COUNT(*)=COUNT(j.jglsupid) AND COUNT(*)=COUNT(j.jglhsjjje)
        AND COUNT(*)=COUNT(j.jglfsdate)
        AND BOOL_AND(COALESCE((j.jglbillid='404' AND j.jgldac='D') OR
                              (j.jglbillid='409' AND j.jgldac='C'),FALSE))
        AND SUM(j.jglhsjjje)<>0
        AND BOOL_AND(COALESCE((TRUE {scope_sql}), FALSE))
    ) SELECT * FROM docs d WHERE (:supplier='' OR d.supplier_code=:supplier)
      AND (:group_code='' OR :group_code=ANY(d.groups))
      AND (CAST(:date_from AS date) IS NULL OR d.date>=CAST(:date_from AS date))
      AND (CAST(:date_to AS date) IS NULL OR d.date<=CAST(:date_to AS date))
      AND (:include_bound OR NOT EXISTS (
        SELECT 1 FROM cosmetics_payment_match_lines l
        WHERE l.kind='receipt' AND l.source_key=d.source_key))
    ORDER BY d.date,d.number LIMIT 1001
    """


def receipts(db, store, supplier, scope_sql, scope_params, *, group_code='', date_from=None,
             date_to=None, keys=None, include_bound=False, require_fresh=False):
    params = dict(scope_params, store=store, supplier=supplier, group_code=group_code,
                  date_from=date_from, date_to=date_to, keys_empty=keys is None,
                  keys=keys or [], include_bound=include_bound)
    sql = receipt_query(scope_sql)
    if keys is not None:
        sql = sql.replace('LIMIT 1001', '')
    rows = db.execute(text(sql), params).mappings().all()
    if keys is None and len(rows) > LIMIT:
        raise ValueError('验收单超过1000张，请缩小单据日期范围或选择柜组')
    if not include_bound and rows:
        eligible = unassociated_receipt_numbers(db, store, supplier, [r['number'] for r in rows], require_fresh=require_fresh)
        rows = [dict(r, settlement_status='未关联结算单') for r in rows if r['number'] in eligible]
    return [stamp(row) for row in rows]


def supplier_options(db, store, scope_sql, scope_params, keyword=''):
    # Reuse exactly the complete-document visibility predicate; no supplier names leak.
    base = receipt_query(scope_sql).split(') SELECT * FROM docs d WHERE')[0]
    sql = base + """ ) SELECT DISTINCT d.supplier_code AS code,d.supplier_name AS name
      FROM docs d WHERE (d.supplier_code ILIKE :keyword OR d.supplier_name ILIKE :keyword)
      ORDER BY name,code LIMIT 101"""
    rows = db.execute(text(sql), dict(scope_params, store=store, keys_empty=True, keys=[],
                                    supplier='', keyword='%'+keyword+'%')).mappings().all()
    return {'items': [dict(r) for r in rows[:100]], 'has_more': len(rows)>100}


def invoices(db, store, supplier, *, keys=None, date_from=None, date_to=None):
    tax = db.execute(text('SELECT NULLIF(UPPER(TRIM(sbtaxno)),\'\') FROM supplierbase WHERE sbid=:supplier'), {'supplier':supplier}).scalar()
    if not tax:
        raise ValueError('供应商缺少税号，无法准确匹配发票，请先维护供应商税号')
    # Deduplicate imported records by the legal invoice identity. Reject conflicting copies.
    rows = db.execute(text("""
      WITH normalized AS (
        SELECT COALESCE(NULLIF(TRIM(invoiceno),''),NULLIF(TRIM(qdzphm),'')) AS number,
          COALESCE(TRIM(invoicecode),'') AS code, UPPER(TRIM(buyertaxno)) AS buyer_tax,
          UPPER(TRIM(salertaxno)) AS seller_tax, TRIM(invoicestatus) AS status,
          NULLIF(TRIM(use_billno),'') AS used_bill,
          CASE WHEN TRIM(totalamount) ~ '^[+-]?[0-9]+([.][0-9]+)?$'
            THEN TRIM(totalamount)::numeric END AS value,
          LEFT(invoicedate,10) AS date, salername AS supplier_name, NULLIF(TRIM(remark),'') AS remark
        FROM br_income_normal_inv_main
        WHERE UPPER(TRIM(buyertaxno))=:buyer AND UPPER(TRIM(salertaxno))=:seller
      ), docs AS (
        SELECT buyer_tax || ':' || seller_tax || ':' || code || ':' || number AS source_key,
          number,code,MIN(date) AS date,MIN(supplier_name) AS supplier_name,
          MIN(value)::text AS amount, COALESCE(STRING_AGG(DISTINCT remark, E'\n' ORDER BY remark),'') AS remark
        FROM normalized WHERE number IS NOT NULL
        GROUP BY buyer_tax,seller_tax,code,number
        HAVING BOOL_AND(COALESCE(status IN ('0','正常'),FALSE))
          AND BOOL_AND(used_bill IS NULL) AND COUNT(*)=COUNT(value)
          AND COUNT(DISTINCT value)=1 AND MIN(value)>0
          AND COUNT(DISTINCT date)=1
      ) SELECT * FROM docs d
      WHERE (:keys_empty OR d.source_key=ANY(:keys))
        AND (CAST(:date_from AS date) IS NULL OR d.date>=CAST(:date_from AS text))
        AND (CAST(:date_to AS date) IS NULL OR d.date<=CAST(:date_to AS text))
        AND NOT EXISTS (SELECT 1 FROM cosmetics_payment_match_lines l
          WHERE l.kind='invoice' AND l.source_key=d.source_key)
      ORDER BY d.date,d.number LIMIT 1001
    """),dict(buyer=STORES[store][1],seller=tax, keys_empty=keys is None,keys=keys or [],
              date_from=date_from,date_to=date_to)).mappings().all()
    if len(rows)>LIMIT:
        raise ValueError('发票超过1000张，请缩小单据日期范围')
    return [stamp(row) for row in rows]


def validate_selection(requested, actual):
    expected = {x.source_key:x.version for x in requested}
    if len(expected)!=len(requested):
        raise ValueError('不能重复勾选同一张单据')
    if set(expected)!={x['source_key'] for x in actual}:
        raise ValueError('单据已被绑定、状态已改变或超出权限，请刷新后重新勾选')
    if any(expected[x['source_key']]!=x['version'] for x in actual):
        raise ValueError('单据金额或明细已变化，请刷新核对后重新勾选')


def create_match(db, payload, user_id, scope_sql, scope_params):
    if not re.fullmatch(r'[0-9]{4}-(0[1-9]|1[0-2])',payload.payment_month):
        raise ValueError('付款月份格式应为YYYY-MM')
    # Deterministic global locks serialize overlapping submissions even across stores.
    lock_keys=sorted({('invoice:'+x.source_key) for x in payload.invoices} |
                     {('receipt:'+x.source_key) for x in payload.receipts})
    for key in lock_keys:
        db.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),{'key':key})
    right=receipts(db,payload.store,payload.supplier,scope_sql,scope_params,
                   keys=[x.source_key for x in payload.receipts], require_fresh=True)
    validate_selection(payload.receipts,right)
    left=invoices(db,payload.store,payload.supplier,keys=[x.source_key for x in payload.invoices])
    validate_selection(payload.invoices,left)
    a,b,diff=totals(left,right)
    number='PP'+payload.payment_month.replace('-','')+'-'+uuid4().hex[:16].upper()
    db.execute(text("""INSERT INTO cosmetics_payment_matches
      (number,store_code,supplier_code,payment_month,invoice_amount,receipt_amount,difference,created_by)
      VALUES (:number,:store,:supplier,:month,:a,:b,:diff,:actor)"""),
      dict(number=number,store=payload.store,supplier=payload.supplier,month=payload.payment_month,
           a=a,b=b,diff=diff,actor=user_id))
    for kind,rows in [('invoice',left),('receipt',right)]:
        for row in rows:
            db.execute(text("""INSERT INTO cosmetics_payment_match_lines
              (match_number,kind,source_key,document_number,amount,snapshot)
              VALUES (:number,:kind,:key,:document,:amount,CAST(:snapshot AS jsonb))"""),
              dict(number=number,kind=kind,key=row['source_key'],document=row['number'],
                   amount=amount(row['amount']),snapshot=json.dumps(row,ensure_ascii=False)))
    return dict(number=number,invoice_amount=str(a),receipt_amount=str(b),difference=str(diff),
                invoices=left,receipts=right)
