"""Permission-checked API for cross-month cosmetics payment matching."""
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from models.database import get_db
from models.models import User
from routers.auth import get_current_user
from routers.authz import load_business_scope, require_permission
from routers.sales import _business_scope_filter_sql
from services import cosmetics_payment_matching as service
from services.receipt_settlement_status import SettlementStatusUnavailable, sync_status

router=APIRouter(prefix='/api/cosmetics-payment-matching',tags=['settlement'])
StoreCode=Literal['601','602','603']


class SelectedDocument(BaseModel):
    source_key: str = Field(min_length=1,max_length=500)
    version: str = Field(pattern=r'^[0-9a-f]{64}$')


class MatchRequest(BaseModel):
    store: StoreCode
    supplier: str = Field(min_length=1,max_length=80)
    payment_month: str = Field(pattern=r'^[0-9]{4}-(0[1-9]|1[0-2])$')
    invoices: list[SelectedDocument] = Field(min_length=1,max_length=1000)
    receipts: list[SelectedDocument] = Field(min_length=1,max_length=1000)


def access(db,user,create=False):
    require_permission(db,user,'settlement.cosmetics_matching.view')
    if create:
        require_permission(db,user,'settlement.cosmetics_matching.create')
    scope=load_business_scope(db,user,fallback_resource_code='settlement')
    params={}
    sql=_business_scope_filter_sql(scope,params,prefix='cosmetics',store_expr='st.store_id::text',
        department_code_expr='dept.mfcode',department_name_expr='dept.mfcname',
        group_expr='j.jglmfid',supplier_expr='j.jglsupid',brand_code_expr='j.jglppcode',
        brand_name_expr='cb.cbcname',category_code_expr='j.jglcatid',category_name_expr='gc.catcname',
        floor_expr='mf.mflc')
    service.ensure_ready(db)
    return sql,params


def run(db,fn):
    try:
        return fn()
    except SettlementStatusUnavailable as exc:
        db.rollback()
        raise HTTPException(503,str(exc)) from None
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422,str(exc)) from None
    except IntegrityError:
        db.rollback()
        raise HTTPException(409,'单据已被其他配票单绑定，请刷新后重新选择') from None
    except OperationalError as exc:
        db.rollback()
        if getattr(exc.orig,'pgcode',None)=='57014':
            raise HTTPException(504,'配票查询超时，请缩小单据范围后重试') from None
        raise


@router.get('/suppliers')
def suppliers(store:StoreCode,keyword:str=Query('',max_length=100),
              db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    def query():
        sql,params=access(db,current_user)
        return service.supplier_options(db,store,sql,params,keyword)
    return run(db,query)


@router.get('/candidates')
def candidates(store:StoreCode,supplier:str=Query(...,min_length=1,max_length=80),
               group_code:str=Query('',max_length=80),date_from:date|None=None,date_to:date|None=None,
               db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    def query():
        sql,params=access(db,current_user)
        if date_from and date_to and date_from>date_to:
            raise ValueError('单据开始日期不能晚于结束日期')
        # A supplier's invoice pool is visible only if a complete receipt is visible.
        visible=service.receipts(db,store,supplier,sql,params,include_bound=True,
                                 date_from=date_from,date_to=date_to)
        if not visible:
            raise HTTPException(403,'没有该门店供应商的完整验收单数据权限或可用进货数据')
        right=service.receipts(db,store,supplier,sql,params,group_code=group_code,
                               date_from=date_from,date_to=date_to)
        left=service.invoices(db,store,supplier,date_from=date_from,date_to=date_to)
        groups={code for row in visible for code in row['groups']}
        names=dict(db.execute(text("SELECT mfcode,MAX(NULLIF(TRIM(mfcname),'')) FROM manaframe WHERE mfcode=ANY(:codes) GROUP BY mfcode"), {'codes':list(groups)}).all())
        group_options=[dict(code=code,name=names.get(code) or '') for code in sorted(groups)]
        return dict(invoices=left,receipts=right,groups=sorted(groups),group_options=group_options,settlement_sync=sync_status(db),
                    buyer_name='常州新世纪商城有限公司' if store=='603' else '常州百货大楼股份有限公司',
                    note='发票按购方及供应商税号匹配；购物中心与百货大楼共用发票池。验收/退厂单包含已记账验收单、负数验收单和退厂单，按原始正负含税金额整单汇总抵减。仅显示未关联结算单、非零金额且未绑定的单据。')
    return run(db,query)


@router.post('')
def create(payload:MatchRequest,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    def save():
        sql,params=access(db,current_user,True)
        result=service.create_match(db,payload,current_user.user_id,sql,params)
        db.commit()
        return result
    return run(db,save)


@router.get('/history')
def history(store:StoreCode,supplier:str=Query(...,min_length=1,max_length=80),
            payment_month:str=Query(...,pattern=r'^[0-9]{4}-(0[1-9]|1[0-2])$'),
            db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    def query():
        sql,params=access(db,current_user)
        heads=db.execute(text('''SELECT * FROM cosmetics_payment_matches
          WHERE store_code=:store AND supplier_code=:supplier AND payment_month=:month
          ORDER BY created_at DESC,number DESC'''),dict(store=store,supplier=supplier,month=payment_month)).mappings().all()
        if not heads:
            return {'items':[]}
        lines=db.execute(text('''SELECT * FROM cosmetics_payment_match_lines
          WHERE match_number=ANY(:numbers) ORDER BY id'''),{'numbers':[h['number'] for h in heads]}).mappings().all()
        keys=[l['source_key'] for l in lines if l['kind']=='receipt']
        visible={r['source_key'] for r in service.receipts(db,store,supplier,sql,params,keys=keys,include_bound=True)}
        items=[]
        for head in heads:
            children=[l for l in lines if l['match_number']==head['number']]
            required={l['source_key'] for l in children if l['kind']=='receipt'}
            if not required or not required.issubset(visible):
                continue
            record=dict(head)
            for name in ('invoice_amount','receipt_amount','difference'):
                record[name]=str(record[name])
            record['invoices']=[l['snapshot'] for l in children if l['kind']=='invoice']
            record['receipts']=[l['snapshot'] for l in children if l['kind']=='receipt']
            items.append(record)
        return {'items':items}
    return run(db,query)
