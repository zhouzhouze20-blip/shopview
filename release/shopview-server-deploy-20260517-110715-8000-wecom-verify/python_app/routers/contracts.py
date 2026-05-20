"""
百货柜位管理系统 - ERP 合同查询 API

按经营单元读取从 ERP 合同表同步过来的合同信息：
- business_units.unit_code 对应 contmanaframe.cmfmfid
- 同时兼容 contmain.cmchar9 作为经营单元编码
- contmanaframe.cmfcontno 对应 contmain.cmcontno
"""

import calendar
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from models.database import get_db
from models.models import User
from routers.auth import get_current_user
from routers.authz import load_business_scope, require_permission, scope_allows_business


router = APIRouter(
    prefix="/api/contracts",
    tags=["contracts"],
)


CONTRACT_STATUS_LABELS = {
    "B": "未生效",
    "Y": "已生效",
    "S": "停用",
    "N": "终止",
    "A": "已审批",
    "Q": "过期",
}


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _table_exists(db: Session, table_name: str) -> bool:
    row = db.execute(
        text(
            """
            SELECT EXISTS (
              SELECT 1
              FROM information_schema.tables
              WHERE table_schema = 'public' AND table_name = :table_name
            ) AS ok
            """
        ),
        {"table_name": table_name},
    ).fetchone()
    return bool(row.ok) if row is not None else False


def _require_contract_tables(db: Session) -> None:
    missing = [
        table_name
        for table_name in ("contmain", "contmanaframe")
        if not _table_exists(db, table_name)
    ]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"合同表未创建: {', '.join(missing)}",
        )


def _fetch_mappings(db: Session, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    rows = db.execute(text(sql), params).mappings().all()
    return [{key: _json_value(value) for key, value in row.items()} for row in rows]


def _supplier_join_sql(enabled: bool, contract_alias: str = "cm") -> str:
    if not enabled:
        return ""
    return (
        "LEFT JOIN supplierbase sb "
        f"ON upper(trim(COALESCE({contract_alias}.cmsupid, ''))) = upper(trim(COALESCE(sb.sbid, '')))"
    )


def _supplier_name_select_sql(enabled: bool) -> str:
    if not enabled:
        return "NULL::varchar AS supplier_name,"
    return "sb.sbcname AS supplier_name,"


def _manaframe_join_sql(enabled: bool, code_expr: str, alias: str = "mf") -> str:
    if not enabled:
        return ""
    return (
        f"LEFT JOIN manaframe {alias} "
        f"ON upper(trim(COALESCE({code_expr}, ''))) = upper(trim(COALESCE({alias}.mfcode, '')))"
    )


def _manaframe_name_select_sql(enabled: bool, alias: str = "mf") -> str:
    if not enabled:
        return "NULL::varchar AS group_name,"
    return f"{alias}.mfcname AS group_name,"


def _contract_type_join_sql(enabled: bool, contract_alias: str = "cm") -> str:
    if not enabled:
        return ""
    return (
        "LEFT JOIN contmaintype cmt "
        f"ON upper(trim(COALESCE({contract_alias}.cmtype, ''))) = upper(trim(COALESCE(cmt.cmtypecode, '')))"
    )


def _contract_type_name_select_sql(enabled: bool) -> str:
    if not enabled:
        return "NULL::varchar AS contract_type_name,"
    return "cmt.cmtypename AS contract_type_name,"


def _counter_group_scope_join_sql(enabled: bool, code_expr: str, alias: str = "cg") -> str:
    if not enabled:
        return ""
    return (
        f"""
        LEFT JOIN (
          SELECT
            mf.mfcode AS group_code,
            mf.mfcname AS group_name,
            dept.mfcode AS department_code,
            dept.mfcname AS department_name,
            CASE
              WHEN SUBSTRING(TRIM(BOTH FROM COALESCE(mf.mfcode, '')) FROM 1 FOR 3) ~ '^[0-9]+$'
              THEN SUBSTRING(TRIM(BOTH FROM COALESCE(mf.mfcode, '')) FROM 1 FOR 3)::integer
              ELSE NULL
            END AS store_id
          FROM manaframe mf
          LEFT JOIN manaframe dept
            ON upper(trim(COALESCE(mf.mfpcode, ''))) = upper(trim(COALESCE(dept.mfcode, '')))
        ) {alias}
        """
        f"ON upper(trim(COALESCE({code_expr}, ''))) = upper(trim(COALESCE({alias}.group_code, '')))"
    )


def _counter_group_scope_select_sql(enabled: bool, code_expr: str, alias: str = "cg") -> str:
    if not enabled:
        return f"{code_expr} AS scope_group_code, NULL::varchar AS scope_department_code, NULL::varchar AS scope_department_name, NULL::varchar AS scope_store_id"
    return (
        f"COALESCE({alias}.group_code, {code_expr}) AS scope_group_code, "
        f"{alias}.department_code AS scope_department_code, "
        f"{alias}.department_name AS scope_department_name, "
        f"({alias}.store_id)::varchar AS scope_store_id"
    )


def _contbd_xs_xssr_select_sql(enabled: bool) -> str:
    """contbd_xs 中 xssr 为区间完成销售收入；无表或 JOIN 未命中时为 NULL。"""
    return "xs.xssr AS xssr" if enabled else "NULL::numeric AS xssr"


def _contbd_xs_join_sql(enabled: bool) -> str:
    if not enabled:
        return ""
    return (
        "LEFT JOIN contbd_xs xs "
        "ON upper(btrim(cb.cbcontno)) = upper(btrim(xs.cbcontno)) "
        "AND btrim(coalesce(cb.cbmkt, '')) = btrim(coalesce(xs.cbmkt, '')) "
        "AND btrim(coalesce(cb.cbmfid, '')) = btrim(coalesce(xs.cbmfid, '')) "
        "AND (cb.cbeffdate::date) = xs.cbeffdate "
        "AND (cb.cblapdate::date) = xs.cblapdate "
    )


def _contract_row_allowed(scope, row: dict[str, Any]) -> bool:
    return scope_allows_business(
        scope,
        store_id=row.get("scope_store_id"),
        department_code=row.get("scope_department_code"),
        department_name=row.get("scope_department_name"),
        group_code=row.get("scope_group_code") or row.get("cmfmfid") or row.get("cmchar9"),
    )


def _strip_scope_fields(row: dict[str, Any]) -> dict[str, Any]:
    row.pop("scope_group_code", None)
    row.pop("scope_department_code", None)
    row.pop("scope_department_name", None)
    row.pop("scope_store_id", None)
    row.pop("scope_entries", None)
    return row


def _split_codes(value: object) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item and item.strip()]


def _contract_list_row_allowed(scope, row: dict[str, Any]) -> bool:
    scope_entries = [item for item in str(row.get("scope_entries") or "").split(";;") if item]
    if scope_entries:
        for entry in scope_entries:
            store_id, department_code, department_name, group_code = (entry.split("|") + ["", "", "", ""])[:4]
            if scope_allows_business(
                scope,
                store_id=store_id or None,
                department_code=department_code or None,
                department_name=department_name or None,
                group_code=group_code or None,
            ):
                return True
        return False

    group_codes = _split_codes(row.get("group_codes"))
    if not group_codes:
        return _contract_row_allowed(scope, row)
    return any(
        scope_allows_business(
            scope,
            store_id=row.get("scope_store_id"),
            department_code=row.get("scope_department_code"),
            department_name=row.get("scope_department_name"),
            group_code=group_code,
        )
        for group_code in group_codes
    )


def _append_contract_scope_filter(sql: str, params: dict[str, Any], scope, has_counter_groups: bool) -> str:
    if scope.all_access:
        return sql

    allowed_groups = sorted(scope.allow.get("group", set()))
    allowed_departments = sorted(scope.allow.get("department", set()))
    allowed_stores = sorted(scope.allow.get("store", set()))

    clauses = []
    if allowed_groups:
        params["scope_group_values"] = allowed_groups
        clauses.append(
            """
            upper(trim(COALESCE(cmf_scope_filter.cmfmfid, cm.cmchar9, ''))) = ANY(:scope_group_values)
            """
        )

    if has_counter_groups and allowed_departments:
        params["scope_department_values"] = allowed_departments
        clauses.append("upper(trim(COALESCE(cg_scope_filter.department_code, ''))) = ANY(:scope_department_values)")

    if has_counter_groups and allowed_stores:
        params["scope_store_values"] = allowed_stores
        clauses.append("(cg_scope_filter.store_id)::varchar = ANY(:scope_store_values)")

    if not clauses:
        return f"{sql} AND 1=0"

    return f"""
        {sql}
        AND EXISTS (
          SELECT 1
          FROM contmanaframe cmf_scope_filter
          {_counter_group_scope_join_sql(has_counter_groups, "cmf_scope_filter.cmfmfid", "cg_scope_filter")}
          WHERE cmf_scope_filter.cmfcontno = cm.cmcontno
            AND ({" OR ".join(clauses)})
        )
    """


def _parse_date_field(value: Any) -> date | None:
    """将合同日期字段规范为 date，供驾驶舱统计使用。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text_val = str(value).strip()
    if not text_val:
        return None
    try:
        return date.fromisoformat(text_val[:10])
    except ValueError:
        return None


def _contract_key(data: dict[str, Any]) -> str:
    """合同主键规范化，避免供应商/柜组等 JOIN 重复导致同一合同重复展示。"""
    return str(data.get("cmcontno") or data.get("cmfcontno") or "").strip().upper()


def _contract_dashboard_stats_from_items(items: list[dict[str, Any]]) -> dict[str, int]:
    """
    在营：cmstatus 为已生效 (Y) 且当前日期落在 [cmeffdate, cmlapdate]。
    本月新增：录入日期 cminputdate 落在本月。
    本月将到期：在营且失效日期 cmlapdate 落在本月内。
    """
    today = date.today()
    month_start = date(today.year, today.month, 1)
    month_end = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
    active_in_operation = 0
    new_this_month = 0
    expiring_this_month = 0
    for data in items:
        st = str(data.get("cmstatus") or "").strip().upper()
        eff = _parse_date_field(data.get("cmeffdate"))
        lap = _parse_date_field(data.get("cmlapdate"))
        inp = _parse_date_field(data.get("cminputdate"))
        is_active = bool(
            st == "Y" and eff is not None and lap is not None and eff <= today <= lap,
        )
        if is_active:
            active_in_operation += 1
        if inp is not None and inp.year == today.year and inp.month == today.month:
            new_this_month += 1
        if is_active and lap is not None and month_start <= lap <= month_end:
            expiring_this_month += 1
    return {
        "active_in_operation": active_in_operation,
        "new_this_month": new_this_month,
        "expiring_this_month": expiring_this_month,
    }


def _filter_expiring_this_month_contracts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """与驾驶舱「本月将到期」同一口径：在营且失效日落在本月；按失效日升序。"""
    today = date.today()
    month_start = date(today.year, today.month, 1)
    month_end = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
    out: list[dict[str, Any]] = []
    seen_contracts: set[str] = set()
    for data in items:
        contract_key = _contract_key(data)
        if contract_key and contract_key in seen_contracts:
            continue
        st = str(data.get("cmstatus") or "").strip().upper()
        eff = _parse_date_field(data.get("cmeffdate"))
        lap = _parse_date_field(data.get("cmlapdate"))
        is_active = bool(
            st == "Y" and eff is not None and lap is not None and eff <= today <= lap,
        )
        if is_active and lap is not None and month_start <= lap <= month_end:
            if contract_key:
                seen_contracts.add(contract_key)
            out.append(data)

    def sort_key(row: dict[str, Any]) -> tuple[date, str]:
        lap = _parse_date_field(row.get("cmlapdate"))
        return (lap or date.max, str(row.get("cmcontno") or ""))

    out.sort(key=sort_key)
    return out


def _load_contract_list_items(
    db: Session,
    contract_scope,
    *,
    keyword: str | None = None,
    status_filter: str | None = None,
    group_code: str | None = None,
    supplier_code: str | None = None,
    skip: int = 0,
    limit: int | None = 100,
) -> list[dict[str, Any]]:
    """
    与合同台账列表相同的数据源与行级数据范围过滤。
    limit 为 None 时不分页（用于驾驶舱统计，数据量大时请谨慎）。
    """
    _require_contract_tables(db)
    has_supplierbase = _table_exists(db, "supplierbase")
    has_manaframe = _table_exists(db, "manaframe")
    has_counter_groups = _table_exists(db, "manaframe")
    has_contbd = _table_exists(db, "contbd")
    has_contmaintype = _table_exists(db, "contmaintype")

    supplier_join = _supplier_join_sql(has_supplierbase)
    supplier_select = _supplier_name_select_sql(has_supplierbase)
    contract_type_join = _contract_type_join_sql(has_contmaintype)
    contract_type_select = _contract_type_name_select_sql(has_contmaintype)
    cmf_name_join = _manaframe_join_sql(has_manaframe, "cmf.cmfmfid")
    cmf_name_expr = "COALESCE(mf.mfcname, '')" if has_manaframe else "''"
    cg_join = _counter_group_scope_join_sql(has_counter_groups, "cmf_primary.cmfmfid", "cg")
    cmf_scope_join = _counter_group_scope_join_sql(has_counter_groups, "cmf.cmfmfid", "cg_scope")
    scope_entry_expr = (
        "concat_ws('|', COALESCE((cg_scope.store_id)::varchar, ''), COALESCE(cg_scope.department_code, ''), "
        "COALESCE(cg_scope.department_name, ''), COALESCE(cmf.cmfmfid, ''))"
        if has_counter_groups
        else "concat_ws('|', '', '', '', COALESCE(cmf.cmfmfid, ''))"
    )

    bd_cte = (
        """
            , bd_summary AS (
              SELECT
                cbcontno,
                bool_or(upper(trim(COALESCE(cbisrunqs, ''))) IN ('Y','1','T','是')) AS is_clear,
                string_agg(DISTINCT NULLIF(trim(COALESCE(cbisrunqs, '')), ''), ',' ORDER BY NULLIF(trim(COALESCE(cbisrunqs, '')), '')) AS clear_flags,
                COALESCE(SUM(cbsum), 0) AS bottom_amount,
                COALESCE(SUM(cbprofit), 0) AS bottom_profit
              FROM contbd
              GROUP BY cbcontno
            )
            """
        if has_contbd
        else """
            , bd_summary AS (
              SELECT
                NULL::varchar AS cbcontno,
                NULL::boolean AS is_clear,
                NULL::text AS clear_flags,
                NULL::numeric AS bottom_amount,
                NULL::numeric AS bottom_profit
              WHERE false
            )
            """
    )

    sql = f"""
            WITH cmf_summary AS (
              SELECT
                cmf.cmfcontno,
                string_agg(DISTINCT NULLIF(trim(COALESCE(cmf.cmfmfid, '')), ''), ',' ORDER BY NULLIF(trim(COALESCE(cmf.cmfmfid, '')), '')) AS group_codes,
                string_agg(DISTINCT NULLIF(trim({cmf_name_expr}), ''), ',' ORDER BY NULLIF(trim({cmf_name_expr}), '')) AS group_names,
                string_agg(DISTINCT {scope_entry_expr}, ';;' ORDER BY {scope_entry_expr}) AS scope_entries,
                string_agg(DISTINCT NULLIF(trim(COALESCE(cmf.cmfbrand, '')), ''), ',' ORDER BY NULLIF(trim(COALESCE(cmf.cmfbrand, '')), '')) AS range_brands,
                MIN(cmf.cmfeffdate) AS range_start_date,
                MAX(cmf.cmflapdate) AS range_end_date,
                COALESCE(SUM(cmf.cmfjzmj), 0) AS contract_area
              FROM contmanaframe cmf
              {cmf_name_join}
              {cmf_scope_join}
              GROUP BY cmf.cmfcontno
            ),
            cmf_primary AS (
              SELECT DISTINCT ON (cmfcontno)
                cmfcontno,
                cmfmfid
              FROM contmanaframe
              ORDER BY cmfcontno, cmfeffdate DESC NULLS LAST, cmfmfid ASC
            )
            {bd_cte}
            SELECT
              cm.cmcontno,
              cm.cmstatus,
              cm.cmtype,
              {contract_type_select}
              cm.cmsupid,
              {supplier_select}
              cm.cmwmid,
              cm.cmtitle,
              cm.cmobject,
              cm.cmppname,
              cm.cmcatname,
              cm.cmeffdate,
              cm.cmlapdate,
              cm.cmmoney,
              cm.cmpaycode,
              cm.cmyfkmode,
              cm.cmsetmode,
              cm.cmjsmkt,
              cm.cminputor,
              cm.cminputdate,
              cm.cmauditor,
              cm.cmauditdate,
              cm.cmchar9,
              cmf_summary.group_codes,
              cmf_summary.group_names,
              cmf_summary.scope_entries,
              cmf_summary.range_brands,
              cmf_summary.range_start_date,
              cmf_summary.range_end_date,
              cmf_summary.contract_area,
              bd_summary.is_clear,
              bd_summary.clear_flags,
              bd_summary.bottom_amount,
              bd_summary.bottom_profit,
              {_counter_group_scope_select_sql(has_counter_groups, "COALESCE(cmf_primary.cmfmfid, cm.cmchar9)", "cg")}
            FROM contmain cm
            LEFT JOIN cmf_summary ON cmf_summary.cmfcontno = cm.cmcontno
            LEFT JOIN cmf_primary ON cmf_primary.cmfcontno = cm.cmcontno
            LEFT JOIN bd_summary ON bd_summary.cbcontno = cm.cmcontno
            {supplier_join}
            {contract_type_join}
            {cg_join}
            WHERE 1=1
        """
    params: dict[str, Any] = {}
    if limit is not None:
        params["skip"] = skip
        params["limit"] = limit
    sql = _append_contract_scope_filter(sql, params, contract_scope, has_counter_groups)

    normalized_keyword = (keyword or "").strip()
    if normalized_keyword:
        sql += """
              AND (
                upper(trim(COALESCE(cm.cmcontno, ''))) LIKE upper(:keyword)
                OR upper(trim(COALESCE(cm.cmtitle, ''))) LIKE upper(:keyword)
                OR upper(trim(COALESCE(cm.cmobject, ''))) LIKE upper(:keyword)
                OR upper(trim(COALESCE(cm.cmppname, ''))) LIKE upper(:keyword)
                OR upper(trim(COALESCE(cm.cmsupid, ''))) LIKE upper(:keyword)
                OR upper(trim(COALESCE(cmf_summary.group_codes, ''))) LIKE upper(:keyword)
                OR upper(trim(COALESCE(cmf_summary.group_names, ''))) LIKE upper(:keyword)
              )
            """
        params["keyword"] = f"%{normalized_keyword}%"

    normalized_status = (status_filter or "").strip()
    if normalized_status and normalized_status != "ALL":
        sql += " AND upper(trim(COALESCE(cm.cmstatus, ''))) = upper(:status)"
        params["status"] = normalized_status

    normalized_group = (group_code or "").strip()
    if normalized_group:
        sql += """
              AND EXISTS (
                SELECT 1
                FROM contmanaframe cmf_filter
                WHERE cmf_filter.cmfcontno = cm.cmcontno
                  AND upper(trim(COALESCE(cmf_filter.cmfmfid, ''))) = upper(trim(:group_code))
              )
            """
        params["group_code"] = normalized_group

    normalized_supplier = (supplier_code or "").strip()
    if normalized_supplier:
        sql += " AND upper(trim(COALESCE(cm.cmsupid, ''))) = upper(trim(:supplier_code))"
        params["supplier_code"] = normalized_supplier

    sql += " ORDER BY cm.cmeffdate DESC NULLS LAST, cm.cmcontno DESC"
    if limit is not None:
        sql += " LIMIT :limit OFFSET :skip"

    rows = db.execute(text(sql), params).mappings().all()
    items: list[dict[str, Any]] = []
    seen_contracts: set[str] = set()
    for row in rows:
        data = {key: _json_value(value) for key, value in row.items()}
        if not _contract_list_row_allowed(contract_scope, data):
            continue
        contract_key = _contract_key(data)
        if contract_key and contract_key in seen_contracts:
            continue
        if contract_key:
            seen_contracts.add(contract_key)
        data["status_label"] = CONTRACT_STATUS_LABELS.get(
            data.get("cmstatus"),
            data.get("cmstatus") or "未知",
        )
        data["is_clear"] = bool(data.get("is_clear")) if data.get("is_clear") is not None else None
        items.append(_strip_scope_fields(data))
    return items


@router.get("/")
async def list_contracts(
    keyword: str | None = Query(None, description="合同号/主题/供应商/品牌/柜组搜索"),
    status_filter: str | None = Query(None, alias="status", description="合同状态"),
    group_code: str | None = Query(None, description="柜组编码"),
    supplier_code: str | None = Query(None, description="供应商编码"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """合同台账列表：按 ERP 合同主表聚合所属柜组、保底清算信息。"""
    try:
        require_permission(db, current_user, "contract.view")
        contract_scope = load_business_scope(db, current_user, fallback_resource_code="contract")
        items = _load_contract_list_items(
            db,
            contract_scope,
            keyword=keyword,
            status_filter=status_filter,
            group_code=group_code,
            supplier_code=supplier_code,
            skip=skip,
            limit=limit,
        )
        return {
            "items": items,
            "count": len(items),
            "skip": skip,
            "limit": limit,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取合同台账失败: {str(e)}",
        )


@router.get("/dashboard-summary")
async def contract_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    驾驶舱合同指标：在营份数、本月新增（按录入日）、本月将到期（在营且失效日在本月）。
    数据范围与合同台账列表一致。
    """
    try:
        require_permission(db, current_user, "contract.view")
        contract_scope = load_business_scope(db, current_user, fallback_resource_code="contract")
        items = _load_contract_list_items(db, contract_scope, limit=None)
        stats = _contract_dashboard_stats_from_items(items)
        return {
            **stats,
            "as_of_date": date.today().isoformat(),
            "definitions": {
                "active_in_operation": "状态为已生效且当前日期在 [生效日, 失效日] 内",
                "new_this_month": "录入日期 cminputdate 落在本月",
                "expiring_this_month": "在营且失效日 cmlapdate 落在本月",
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取合同驾驶舱指标失败: {str(e)}",
        )


@router.get("/expiring-this-month")
async def list_expiring_contracts_this_month(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    本月即将到期合同明细：在营且失效日 cmlapdate 落在本月，与驾驶舱「本月将到期」计数口径一致。
    """
    try:
        require_permission(db, current_user, "contract.view")
        contract_scope = load_business_scope(db, current_user, fallback_resource_code="contract")
        items = _load_contract_list_items(db, contract_scope, limit=None)
        filtered = _filter_expiring_this_month_contracts(items)
        return {"items": filtered, "count": len(filtered)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取本月到期合同列表失败: {str(e)}",
        )


@router.get("/by-unit/{unit_id}")
async def get_contracts_by_unit(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """按经营单元 ID 查询关联的 ERP 合同。"""
    try:
        require_permission(db, current_user, "contract.view")
        contract_scope = load_business_scope(db, current_user, fallback_resource_code="contract")
        _require_contract_tables(db)
        has_supplierbase = _table_exists(db, "supplierbase")
        has_counter_groups = _table_exists(db, "manaframe")
        has_contmaintype = _table_exists(db, "contmaintype")
        has_business_unit_binding = _table_exists(db, "business_unit_binding")

        unit = db.execute(
            text(
                """
                SELECT
                  bu.id,
                  bu.floor_id,
                  bu.unit_code,
                  bu.status,
                  bu.manual_area,
                  f.store_code,
                  sf.store_id,
                  COALESCE(f.building_code, sf.building_code) AS building_code,
                  COALESCE(f.floor_code, sf.floor_code) AS floor_code,
                  COALESCE(f.name, sf.name) AS floor_name
                FROM business_units bu
                LEFT JOIN floors f ON f.id = bu.floor_id
                LEFT JOIN store_floors sf ON sf.id = bu.floor_id
                WHERE bu.id = :unit_id
                """
            ),
            {"unit_id": unit_id},
        ).fetchone()
        if not unit:
            raise HTTPException(status_code=404, detail=f"经营单元不存在: {unit_id}")

        unit_code = (unit.unit_code or "").strip()
        binding_matches_cte = (
            """
                binding_matches AS (
                  SELECT
                    b.contract_id,
                    NULL::varchar AS group_code
                  FROM business_unit_binding b
                  WHERE b.shop_unit_id = :unit_id
                    AND upper(trim(COALESCE(b.status, 'ACTIVE'))) IN ('ACTIVE', 'HISTORY')
                    AND COALESCE(trim(b.contract_id), '') <> ''
                ),
            """
            if has_business_unit_binding
            else """
                binding_matches AS (
                  SELECT NULL::varchar AS contract_id, NULL::varchar AS group_code
                  WHERE false
                ),
            """
        )
        rows = db.execute(
            text(
                f"""
                WITH
                {binding_matches_cte}
                matched_contracts AS (
                  SELECT
                    COALESCE(cmf.cmfcontno, cm.cmcontno) AS cmfcontno,
                    COALESCE(cmf.cmfmfid, cm.cmchar9) AS cmfmfid,
                    cmf.cmfmarket,
                    cmf.cmfeffdate,
                    cmf.cmflapdate,
                    cmf.cmfjzmj,
                    cmf.cmfsymj,
                    cmf.cmfavgsyf,
                    cmf.cmftotsyf,
                    cmf.cmfcharter,
                    cmf.cmfmemo,
                    cmf.cmfbrand,
                    cmf.cmfaddr,
                    cmf.cmfarea,
                    cmf.cmfismaster,
                    cmf.cmfzjmj,
                    cm.cmcontno,
                    cm.cmstatus,
                    cm.cmtype,
                    {_contract_type_name_select_sql(has_contmaintype)}
                    cm.cmmfid,
                    cm.cmsupid,
                    {_supplier_name_select_sql(has_supplierbase)}
                    cm.cmwmid,
                    cm.cmtitle,
                    cm.cmobject,
                    cm.cmppname,
                    cm.cmcatname,
                    cm.cmeffdate,
                    cm.cmlapdate,
                    cm.cmmoney,
                    cm.cmpaycode,
                    cm.cmbysettle,
                    cm.cmyfkmode,
                    cm.cmsetmode,
                    cm.cmjsmkt,
                    cm.cmkl,
                    cm.cminputor,
                    cm.cminputdate,
                    cm.cmauditor,
                    cm.cmauditdate,
                    cm.cmannulor,
                    cm.cmannuldate,
                    cm.cmmemo,
                    cm.cmmasterno,
                    cm.cmseqno,
                    cm.cmcontact,
                    cm.cmadd,
                    cm.cmtel,
                    cm.cmfax,
                    cm.cmemail,
                    cm.cmchar9,
                    cm.cmsptype,
                    cm.signdate,
                    cm.deliverydate,
                    cm.tackbackdate,
                    cm.sjcgdate,
                    cm.effectdate,
                    cm.zxqsrq,
                    cm.zxjzrq,
                    {_counter_group_scope_select_sql(has_counter_groups, "COALESCE(cmf.cmfmfid, cm.cmchar9)")},
                    FALSE AS matched_by_unit_binding,
                    (
                      cm.cmstatus = 'Y'
                      AND CURRENT_DATE BETWEEN cm.cmeffdate::date AND cm.cmlapdate::date
                    ) AS is_current_effective
                  FROM contmain cm
                  LEFT JOIN contmanaframe cmf
                    ON cm.cmcontno = cmf.cmfcontno
                   AND upper(trim(COALESCE(cmf.cmfmfid, ''))) = upper(trim(:unit_code))
                  {_supplier_join_sql(has_supplierbase)}
                  {_contract_type_join_sql(has_contmaintype)}
                  {_counter_group_scope_join_sql(has_counter_groups, "COALESCE(cmf.cmfmfid, cm.cmchar9)")}
                  WHERE upper(trim(COALESCE(cm.cmchar9, ''))) = upper(trim(:unit_code))

                  UNION

                  SELECT
                    COALESCE(cmf.cmfcontno, cm.cmcontno) AS cmfcontno,
                    COALESCE(cmf.cmfmfid, cm.cmchar9) AS cmfmfid,
                    cmf.cmfmarket,
                    cmf.cmfeffdate,
                    cmf.cmflapdate,
                    cmf.cmfjzmj,
                    cmf.cmfsymj,
                    cmf.cmfavgsyf,
                    cmf.cmftotsyf,
                    cmf.cmfcharter,
                    cmf.cmfmemo,
                    cmf.cmfbrand,
                    cmf.cmfaddr,
                    cmf.cmfarea,
                    cmf.cmfismaster,
                    cmf.cmfzjmj,
                    cm.cmcontno,
                    cm.cmstatus,
                    cm.cmtype,
                    {_contract_type_name_select_sql(has_contmaintype)}
                    cm.cmmfid,
                    cm.cmsupid,
                    {_supplier_name_select_sql(has_supplierbase)}
                    cm.cmwmid,
                    cm.cmtitle,
                    cm.cmobject,
                    cm.cmppname,
                    cm.cmcatname,
                    cm.cmeffdate,
                    cm.cmlapdate,
                    cm.cmmoney,
                    cm.cmpaycode,
                    cm.cmbysettle,
                    cm.cmyfkmode,
                    cm.cmsetmode,
                    cm.cmjsmkt,
                    cm.cmkl,
                    cm.cminputor,
                    cm.cminputdate,
                    cm.cmauditor,
                    cm.cmauditdate,
                    cm.cmannulor,
                    cm.cmannuldate,
                    cm.cmmemo,
                    cm.cmmasterno,
                    cm.cmseqno,
                    cm.cmcontact,
                    cm.cmadd,
                    cm.cmtel,
                    cm.cmfax,
                    cm.cmemail,
                    cm.cmchar9,
                    cm.cmsptype,
                    cm.signdate,
                    cm.deliverydate,
                    cm.tackbackdate,
                    cm.sjcgdate,
                    cm.effectdate,
                    cm.zxqsrq,
                    cm.zxjzrq,
                    {_counter_group_scope_select_sql(has_counter_groups, "COALESCE(cmf.cmfmfid, cm.cmchar9)")},
                    FALSE AS matched_by_unit_binding,
                    (
                      cm.cmstatus = 'Y'
                      AND CURRENT_DATE BETWEEN cm.cmeffdate::date AND cm.cmlapdate::date
                    ) AS is_current_effective
                  FROM contmanaframe cmf
                  LEFT JOIN contmain cm ON cm.cmcontno = cmf.cmfcontno
                  {_supplier_join_sql(has_supplierbase)}
                  {_contract_type_join_sql(has_contmaintype)}
                  {_counter_group_scope_join_sql(has_counter_groups, "COALESCE(cmf.cmfmfid, cm.cmchar9)")}
                  WHERE upper(trim(COALESCE(cmf.cmfmfid, ''))) = upper(trim(:unit_code))

                  UNION

                  SELECT
                    COALESCE(cmf.cmfcontno, cm.cmcontno, bm.contract_id) AS cmfcontno,
                    COALESCE(cmf.cmfmfid, bm.group_code, cm.cmchar9) AS cmfmfid,
                    cmf.cmfmarket,
                    cmf.cmfeffdate,
                    cmf.cmflapdate,
                    cmf.cmfjzmj,
                    cmf.cmfsymj,
                    cmf.cmfavgsyf,
                    cmf.cmftotsyf,
                    cmf.cmfcharter,
                    cmf.cmfmemo,
                    cmf.cmfbrand,
                    cmf.cmfaddr,
                    cmf.cmfarea,
                    cmf.cmfismaster,
                    cmf.cmfzjmj,
                    COALESCE(cm.cmcontno, bm.contract_id) AS cmcontno,
                    cm.cmstatus,
                    cm.cmtype,
                    {_contract_type_name_select_sql(has_contmaintype)}
                    cm.cmmfid,
                    cm.cmsupid,
                    {_supplier_name_select_sql(has_supplierbase)}
                    cm.cmwmid,
                    cm.cmtitle,
                    cm.cmobject,
                    cm.cmppname,
                    cm.cmcatname,
                    cm.cmeffdate,
                    cm.cmlapdate,
                    cm.cmmoney,
                    cm.cmpaycode,
                    cm.cmbysettle,
                    cm.cmyfkmode,
                    cm.cmsetmode,
                    cm.cmjsmkt,
                    cm.cmkl,
                    cm.cminputor,
                    cm.cminputdate,
                    cm.cmauditor,
                    cm.cmauditdate,
                    cm.cmannulor,
                    cm.cmannuldate,
                    cm.cmmemo,
                    cm.cmmasterno,
                    cm.cmseqno,
                    cm.cmcontact,
                    cm.cmadd,
                    cm.cmtel,
                    cm.cmfax,
                    cm.cmemail,
                    cm.cmchar9,
                    cm.cmsptype,
                    cm.signdate,
                    cm.deliverydate,
                    cm.tackbackdate,
                    cm.sjcgdate,
                    cm.effectdate,
                    cm.zxqsrq,
                    cm.zxjzrq,
                    {_counter_group_scope_select_sql(has_counter_groups, "COALESCE(cmf.cmfmfid, bm.group_code, cm.cmchar9)")},
                    TRUE AS matched_by_unit_binding,
                    (
                      cm.cmstatus = 'Y'
                      AND CURRENT_DATE BETWEEN cm.cmeffdate::date AND cm.cmlapdate::date
                    ) AS is_current_effective
                  FROM binding_matches bm
                  LEFT JOIN contmain cm
                    ON upper(trim(COALESCE(cm.cmcontno, ''))) = upper(trim(COALESCE(bm.contract_id, '')))
                  LEFT JOIN contmanaframe cmf
                    ON upper(trim(COALESCE(cmf.cmfcontno, ''))) = upper(trim(COALESCE(bm.contract_id, '')))
                   AND (
                     bm.group_code IS NULL
                     OR upper(trim(COALESCE(cmf.cmfmfid, ''))) = upper(trim(COALESCE(bm.group_code, '')))
                   )
                  {_supplier_join_sql(has_supplierbase)}
                  {_contract_type_join_sql(has_contmaintype)}
                  {_counter_group_scope_join_sql(has_counter_groups, "COALESCE(cmf.cmfmfid, bm.group_code, cm.cmchar9)")}
                  WHERE COALESCE(trim(bm.contract_id), '') <> ''
                )
                SELECT *
                FROM matched_contracts
                ORDER BY
                  CASE
                    WHEN cmstatus = 'Y'
                     AND CURRENT_DATE BETWEEN cmeffdate::date AND cmlapdate::date
                    THEN 0
                    ELSE 1
                  END,
                  cmeffdate DESC NULLS LAST,
                  cmfeffdate DESC NULLS LAST,
                  cmfcontno DESC
                """
            ),
            {"unit_code": unit_code, "unit_id": unit_id},
        ).mappings().all()

        contracts = []
        seen_contract_numbers: set[str] = set()
        for row in rows:
            data = {key: _json_value(value) for key, value in row.items()}
            if not data.get("matched_by_unit_binding") and not _contract_row_allowed(contract_scope, data):
                continue
            contract_number = str(data.get("cmcontno") or data.get("cmfcontno") or "").strip().upper()
            if contract_number and contract_number in seen_contract_numbers:
                continue
            if contract_number:
                seen_contract_numbers.add(contract_number)
            data.pop("matched_by_unit_binding", None)
            data["status_label"] = CONTRACT_STATUS_LABELS.get(
                data.get("cmstatus"),
                data.get("cmstatus") or "未知",
            )
            data["is_current_effective"] = bool(data.get("is_current_effective"))
            contracts.append(_strip_scope_fields(data))

        active_contracts = [item for item in contracts if item["is_current_effective"]]
        return {
            "unit": {
                "id": unit.id,
                "floor_id": unit.floor_id,
                "unit_code": unit.unit_code,
                "status": unit.status,
                "manual_area": _json_value(unit.manual_area),
                "store_code": unit.store_code,
                "store_id": unit.store_id,
                "building_code": unit.building_code,
                "floor_code": unit.floor_code,
                "floor_name": unit.floor_name,
            },
            "active_contract": active_contracts[0] if active_contracts else None,
            "active_contract_count": len(active_contracts),
            "contracts": contracts,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取合同数据失败: {str(e)}",
        )


@router.get("/detail/{contract_no}")
async def get_contract_detail(
    contract_no: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """按合同号查询主表及 4 个合同分表明细。"""
    try:
        require_permission(db, current_user, "contract.view")
        contract_scope = load_business_scope(db, current_user, fallback_resource_code="contract")
        normalized_contract_no = (contract_no or "").strip()
        if not normalized_contract_no:
            raise HTTPException(status_code=400, detail="contract_no 不能为空")

        table_names = ("contmain", "contmanaframe", "contbd", "contcyclist", "contsupcharge")
        existing_tables = {name for name in table_names if _table_exists(db, name)}
        has_supplierbase = _table_exists(db, "supplierbase")
        has_manaframe = _table_exists(db, "manaframe")
        has_counter_groups = _table_exists(db, "manaframe")
        has_contmaintype = _table_exists(db, "contmaintype")
        has_contbd_xs = _table_exists(db, "contbd_xs")
        if "contmain" not in existing_tables and "contmanaframe" not in existing_tables:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="合同主表未创建",
            )

        contmain_rows = (
            _fetch_mappings(
                db,
                f"""
                SELECT
                  cmcontno,
                  cmstatus,
                  cmtype,
                  {_contract_type_name_select_sql(has_contmaintype)}
                  cmmfid,
                  cmsupid,
                  {_supplier_name_select_sql(has_supplierbase)}
                  cmwmid,
                  cmtitle,
                  cmobject,
                  cmppname,
                  cmcatname,
                  cmeffdate,
                  cmlapdate,
                  cmmoney,
                  cmpaycode,
                  cmbysettle,
                  cmyfkmode,
                  cmsetmode,
                  cmjsmkt,
                  cmchar9,
                  cmsptype,
                  signdate,
                  deliverydate,
                  tackbackdate,
                  sjcgdate,
                  effectdate,
                  zxqsrq,
                  zxjzrq,
                  cmcontact,
                  cmadd,
                  cmtel,
                  cmemail,
                  cmmemo,
                  cmmasterno,
                  cmseqno,
                  {_counter_group_scope_select_sql(has_counter_groups, "cm.cmchar9")}
                FROM contmain cm
                {_supplier_join_sql(has_supplierbase)}
                {_contract_type_join_sql(has_contmaintype)}
                {_counter_group_scope_join_sql(has_counter_groups, "cm.cmchar9")}
                WHERE upper(trim(cmcontno)) = upper(trim(:contract_no))
                LIMIT 1
                """,
                {"contract_no": normalized_contract_no},
            )
            if "contmain" in existing_tables
            else []
        )
        contmain = contmain_rows[0] if contmain_rows else None
        if contmain:
            contmain["status_label"] = CONTRACT_STATUS_LABELS.get(
                contmain.get("cmstatus"),
                contmain.get("cmstatus") or "未知",
            )

        contmanaframe = (
            _fetch_mappings(
                db,
                f"""
                SELECT
                  cmfcontno,
                  cmfmfid,
                  {_manaframe_name_select_sql(has_manaframe)}
                  cmfmarket,
                  cmfeffdate,
                  cmflapdate,
                  cmfjzmj,
                  cmfsymj,
                  cmfzjmj,
                  cmfavgsyf,
                  cmftotsyf,
                  cmfcharter,
                  cmfnum1,
                  cmfnum2,
                  cmfnum3,
                  cmfnum4,
                  cmfnum5,
                  cmfbrand,
                  cmfaddr,
                  cmfarea,
                  cmfismaster,
                  cmfmemo,
                  {_counter_group_scope_select_sql(has_counter_groups, "cmf.cmfmfid")}
                FROM contmanaframe cmf
                {_manaframe_join_sql(has_manaframe, "cmf.cmfmfid")}
                {_counter_group_scope_join_sql(has_counter_groups, "cmf.cmfmfid")}
                WHERE upper(trim(cmfcontno)) = upper(trim(:contract_no))
                ORDER BY cmfeffdate DESC NULLS LAST, cmfmfid ASC, cmfbrand ASC
                """,
                {"contract_no": normalized_contract_no},
            )
            if "contmanaframe" in existing_tables
            else []
        )

        contbd = (
            _fetch_mappings(
                db,
                f"""
                SELECT
                  cb.cbcontno,
                  cb.cbseqno,
                  cb.cbmkt,
                  cb.cbmfid,
                  {_manaframe_name_select_sql(has_manaframe)}
                  cb.cbeffdate,
                  cb.cblapdate,
                  cb.cbisrunbd,
                  cb.cbisrunqs,
                  cb.cbsum,
                  cb.cbrate,
                  cb.cbsum1,
                  cb.cbrate1,
                  cb.cbsum2,
                  cb.cbrate2,
                  cb.cbsum3,
                  cb.cbrate3,
                  cb.cbsum4,
                  cb.cbrate4,
                  cb.cbsum5,
                  cb.cbrate5,
                  cb.cbsum6,
                  cb.cbrate6,
                  cb.cbprofit,
                  cb.cbsettype,
                  cb.cbrentunit,
                  cb.cbmanaunit,
                  cb.cbpopunit,
                  cb.cbrentprice,
                  cb.cbnamaprice,
                  cb.cbpopprice,
                  cb.cbiscalcrent,
                  cb.cbsalekh,
                  cb.cbsalerate,
                  {_contbd_xs_xssr_select_sql(has_contbd_xs)},
                  {_counter_group_scope_select_sql(has_counter_groups, "cb.cbmfid")}
                FROM contbd cb
                {_contbd_xs_join_sql(has_contbd_xs)}
                {_manaframe_join_sql(has_manaframe, "cb.cbmfid")}
                {_counter_group_scope_join_sql(has_counter_groups, "cb.cbmfid")}
                WHERE upper(trim(cb.cbcontno)) = upper(trim(:contract_no))
                ORDER BY cb.cbseqno ASC
                """,
                {"contract_no": normalized_contract_no},
            )
            if "contbd" in existing_tables
            else []
        )

        contcyclist = (
            _fetch_mappings(
                db,
                f"""
                SELECT
                  cclcontno,
                  cclseqno,
                  cclmkt,
                  cclmfid,
                  {_manaframe_name_select_sql(has_manaframe)}
                  ccleffdate,
                  ccllapdate,
                  cclitemid,
                  cclitemunit,
                  cclitemprice,
                  cclsumamount,
                  cclystype,
                  cclysnum,
                  cclisfree,
                  cclflag,
                  cclpchflag,
                  {_counter_group_scope_select_sql(has_counter_groups, "ccl.cclmfid")}
                FROM contcyclist ccl
                {_manaframe_join_sql(has_manaframe, "ccl.cclmfid")}
                {_counter_group_scope_join_sql(has_counter_groups, "ccl.cclmfid")}
                WHERE upper(trim(cclcontno)) = upper(trim(:contract_no))
                ORDER BY cclseqno ASC
                """,
                {"contract_no": normalized_contract_no},
            )
            if "contcyclist" in existing_tables
            else []
        )

        contsupcharge = (
            _fetch_mappings(
                db,
                f"""
                SELECT
                  csccontno,
                  cscrowno,
                  cscispub,
                  cscmfid,
                  {_manaframe_name_select_sql(has_manaframe)}
                  cscmarket,
                  cscchargecode,
                  cscchargename,
                  csceffdate,
                  csclapdate,
                  cscsetmon,
                  cscismcjs,
                  cscvalue,
                  csctotal,
                  cscisdeduct,
                  cscflag,
                  cscjsbillno,
                  cscmemo,
                  cscnum1,
                  cscnum2,
                  cscnum3,
                  cscisret,
                  cscretdate,
                  cscbottomvalues,
                  cscpeakvalues,
                  {_counter_group_scope_select_sql(has_counter_groups, "csc.cscmfid")}
                FROM contsupcharge csc
                {_manaframe_join_sql(has_manaframe, "csc.cscmfid")}
                {_counter_group_scope_join_sql(has_counter_groups, "csc.cscmfid")}
                WHERE upper(trim(csccontno)) = upper(trim(:contract_no))
                ORDER BY cscrowno ASC
                """,
                {"contract_no": normalized_contract_no},
            )
            if "contsupcharge" in existing_tables
            else []
        )

        if not any([contmain, contmanaframe, contbd, contcyclist, contsupcharge]):
            raise HTTPException(status_code=404, detail=f"未找到合同: {normalized_contract_no}")

        scope_rows = []
        if contmain:
            scope_rows.append(contmain)
        scope_rows.extend(contmanaframe)
        if not any(_contract_row_allowed(contract_scope, row) for row in scope_rows):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看该合同")

        if contmain:
            contmain = _strip_scope_fields(contmain)
        contmanaframe = [_strip_scope_fields(row) for row in contmanaframe if _contract_row_allowed(contract_scope, row)]
        contbd = [_strip_scope_fields(row) for row in contbd if _contract_row_allowed(contract_scope, row)]
        contcyclist = [_strip_scope_fields(row) for row in contcyclist if _contract_row_allowed(contract_scope, row)]
        contsupcharge = [_strip_scope_fields(row) for row in contsupcharge if _contract_row_allowed(contract_scope, row)]

        return {
            "contract_no": normalized_contract_no,
            "contmain": contmain,
            "contmanaframe": contmanaframe,
            "contbd": contbd,
            "contcyclist": contcyclist,
            "contsupcharge": contsupcharge,
            "counts": {
                "contmanaframe": len(contmanaframe),
                "contbd": len(contbd),
                "contcyclist": len(contcyclist),
                "contsupcharge": len(contsupcharge),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取合同明细失败: {str(e)}",
        )
