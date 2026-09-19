from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from models.database import get_db
from models.models import User
from routers.auth import get_current_user
from routers.authz import load_business_scope, require_permission
from routers.sales import (_business_scope_filter_sql, _od0002_store_id_for_code,
                           _scope_explicitly_rejects_store, _od0002_scope_description)
from services.od0002_report import TrustedScopeSql
from services.new_century_payment_report import PAY_CODES, load_report, build_workbook

router = APIRouter(prefix='/api/sales/reports/new-century-payments', tags=['sales'])
PERMISSION_CODE = 'sales.new_century_payments.view'


def report_for_request(start_date, end_date, department_id, group_code, pay_codes, db, current_user):
    require_permission(db, current_user, PERMISSION_CODE)
    scope = load_business_scope(db, current_user, fallback_resource_code='sales')
    if scope.deny.get('store') or (not scope.all_access and scope.allow.get('store')):
        store_id = _od0002_store_id_for_code(db, '603')
        if store_id is None or _scope_explicitly_rejects_store(scope, store_id):
            raise HTTPException(403, '无新世纪门店数据权限')
    params = {}
    scope_sql = _business_scope_filter_sql(
        scope, params, prefix='new_century_payments', store_expr='st.store_id::text',
        department_code_expr='dept.mfcode', department_name_expr='dept.mfcname',
        group_expr='r.gz', category_code_expr='ac.category_code',
        category_name_expr='ac.category_name', floor_expr='mf.mflc')
    try:
        report = load_report(
            db, start_date=start_date, end_date=end_date, department_id=department_id,
            group_code=group_code, pay_codes=pay_codes if pay_codes is not None else PAY_CODES,
            scope_filter_sql=TrustedScopeSql(scope_sql), scope_params=params)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except OperationalError as exc:
        db.rollback()
        if getattr(exc.orig, 'pgcode', None) == '57014' or 'statement timeout' in str(exc).lower():
            raise HTTPException(504, '报表查询超时，请缩短日期范围后重试') from exc
        raise
    report['scope_description'] = _od0002_scope_description(scope)
    return report


@router.get('')
def get_report(start_date: date = Query(...), end_date: date = Query(...),
               department_id: str | None = None, group_code: str | None = None,
               pay_codes: list[str] | None = Query(None), db: Session = Depends(get_db),
               current_user: User = Depends(get_current_user)):
    return report_for_request(start_date, end_date, department_id, group_code, pay_codes, db, current_user)


@router.get('/export')
def export_report(start_date: date = Query(...), end_date: date = Query(...),
                  department_id: str | None = None, group_code: str | None = None,
                  pay_codes: list[str] | None = Query(None), db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    report = report_for_request(start_date, end_date, department_id, group_code, pay_codes, db, current_user)
    name = quote(f'新世纪支付方式销售毛利_{start_date}_{end_date}.xlsx')
    return StreamingResponse(build_workbook(report),
                             media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                             headers={'Content-Disposition': f"attachment; filename*=UTF-8''{name}"})
