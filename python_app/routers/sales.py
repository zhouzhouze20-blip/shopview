"""
销售查询 API

汇总口径优先使用 salegoodslist，缺失时回退 ods_salegoodslist。
小票详情优先使用 salehead + salegoods + salepay，缺失时回退 salegoodslist 行明细。
"""

from datetime import date
from decimal import Decimal
from typing import Any, Iterable, Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from models.database import get_db
from models.models import User
from routers.auth import get_current_user
from routers.authz import load_business_scope, require_permission, scope_allows_business
from services.department_display_order import department_display_sort_key
from services.sales_analysis import analyze_group_sales
from services.od0002_report import (
    TrustedScopeSql,
    compare_period,
    load_od0002_authorized_departments,
    load_od0002_authorized_stores,
    load_od0002_report,
)
from services.hdyy01_report import load_hdyy01_report
from services.hdyy01_excel import build_hdyy01_workbook_file
from services.hy0001_report import load_hy0001_report
from services.hy0001_excel import build_hy0001_workbook_file
from services.od0002_excel import build_od0002_workbook_file
from services.daily_followup_report import load_daily_followup_report
from services.monthly_followup_report import load_monthly_followup_report
from services.settled_gross_profit_report import load_settled_gross_profit_report
from services.settled_gross_profit_excel import (
    build_settled_gross_profit_workbook_file,
)
from services.inventory_detail_report import (
    CATEGORY_NAME_SQL,
    MAX_EXPORT_ROWS,
    build_historical_inventory_workbook_file,
    build_inventory_movement_workbook_file,
    build_inventory_workbook_file,
    load_historical_inventory_detail_report,
    load_historical_inventory_filter_options,
    load_inventory_detail_report,
    load_inventory_departments,
    load_inventory_department_summary,
    load_inventory_filter_options,
    load_inventory_movement_detail_report,
    load_inventory_movement_filter_options,
)


router = APIRouter(prefix="/api/sales", tags=["sales"])

# 小票列表默认每页展示 100 行；单次接口仍保留上限，完整导出由前端分批分页拉取。
TICKET_PAGE_SIZE = 100
TICKET_EXPORT_BATCH_SIZE = 5_000
TICKET_EXPORT_MAX_ROWS = 50_000
TICKET_EXPORT_FETCH_LIMIT = TICKET_EXPORT_MAX_ROWS + 1
SALES_SUMMARY_LONG_RANGE_TIMEOUT_SECONDS = 90

COMMODITY_DETAIL_PERMISSION = "sales.commodity_detail.view"
DAILY_FOLLOWUP_PERMISSION = "sales.od0001.view"
OD0003_PERMISSION = "sales.od0003.view"
OD0004_PERMISSION = "sales.od0004.view"
SETTLED_GROSS_PROFIT_PERMISSION = "sales.settled_gross_profit.view"
HY0001_PERMISSION = "sales.hy0001.view"


class SalesAnalysisRequest(BaseModel):
    level: str = Field("groups", description="分析层级；第一版仅支持 groups")
    start_date: str | None = Field(None, description="本期开始日期 YYYY-MM-DD")
    end_date: str | None = Field(None, description="本期结束日期 YYYY-MM-DD")
    prior_start_date: str | None = Field(None, description="同期开始日期 YYYY-MM-DD")
    prior_end_date: str | None = Field(None, description="同期结束日期 YYYY-MM-DD")
    store_id: str | None = Field(None, description="门店ID/市场号")
    department_code: str | None = Field(None, description="部门编码")
    unassigned_department: bool = Field(False, description="仅未归属部门")
    group_code: str | None = Field(None, description="柜组编码")
    keyword: str | None = Field(None, description="柜组搜索关键词")
    exclude_rental: bool = Field(False, description="是否排除租赁经营方式 sglwmid=5")
    exclude_backoffice_departments: bool = Field(False, description="是否排除后台职能部门销售")
    limit: int = Field(200, ge=1, le=1000, description="最大分析柜组数")
    include_ai: bool = Field(True, description="是否生成 AI 经营分析文案")


class ReportDepartmentOption(BaseModel):
    department_code: str
    department_name: str
    label: str


SALES_BACKOFFICE_DEPARTMENT_NAMES = (
    "中心营运部",
    "本店尾部",
    "中心财务部",
    "中心企划客服部",
    "中心物业部",
    "中心企划执行部",
    "中心物业服务部",
    "中心信息",
    "中心信息部",
    "新世纪营运部",
    "新世纪企划客服部",
    "新世纪物业服务部",
    "新世纪企划执行部",
    "新世纪物业",
    "新世纪信息",
    "新世纪信息部",
    "百货营运部",
    "集团战略信息中心",
    "集团信息部",
    "集团财务部",
    "大楼规划营运部",
    "大楼信息",
    "大楼物业",
    "书店企划部",
    "书店信息部",
    "书店物业部",
)


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _num(value: Any) -> float:
    if value is None:
        return 0
    return float(value)


def _configure_sales_summary_timeout(
    db: Session,
    *,
    start_date: str | None,
    end_date: str | None,
) -> None:
    """Keep the 30-second default for short ranges; allow cross-month summaries to finish."""
    if not start_date or not end_date:
        return
    try:
        start = date.fromisoformat(start_date.strip())
        end = date.fromisoformat(end_date.strip())
    except ValueError:
        return
    if start > end or (start.year, start.month) == (end.year, end.month):
        return
    db.execute(
        text(
            "SET LOCAL statement_timeout = "
            f"'{SALES_SUMMARY_LONG_RANGE_TIMEOUT_SECONDS}s'"
        )
    )


def _fetch_mappings(db: Session, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    rows = db.execute(text(sql), params).mappings().all()
    return [{key: _json_value(value) for key, value in row.items()} for row in rows]


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


def _column_exists(db: Session, table_name: str, column_name: str) -> bool:
    row = db.execute(
        text(
            """
            SELECT EXISTS (
              SELECT 1
              FROM information_schema.columns
              WHERE table_schema = 'public'
                AND table_name = :table_name
                AND column_name = :column_name
            ) AS ok
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    ).fetchone()
    return bool(row.ok) if row is not None else False


def _salegoodslist_table(db: Session) -> str:
    if _table_exists(db, "salegoodslist"):
        return "salegoodslist"
    if _table_exists(db, "ods_salegoodslist"):
        return "ods_salegoodslist"
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="销售汇总表未创建: salegoodslist / ods_salegoodslist",
    )


def _sql_string_list(values: Iterable[str]) -> str:
    return ", ".join("'" + value.replace("'", "''") + "'" for value in values)


def _sales_department_exclusion_sql(alias: str = "cg", *, enabled: bool = False) -> str:
    """Optionally remove sales assigned to known back-office departments.

    The dashboard includes every department by default.  This list is intentionally
    exact-name based so ordinary operating departments are never removed by a broad
    keyword match; it can be reviewed and adjusted with the business owner.
    """
    if not enabled:
        return ""
    names = _sql_string_list(SALES_BACKOFFICE_DEPARTMENT_NAMES)
    return f" AND TRIM(BOTH FROM COALESCE({alias}.department_name, '')) NOT IN ({names})"


def _sales_rental_exclusion_sql(alias: str = "s", *, enabled: bool = False) -> str:
    """Optionally remove rental fact rows while retaining blank operation modes."""
    if not enabled:
        return ""
    return f" AND TRIM(BOTH FROM COALESCE({alias}.sglwmid, '')) <> '5'"


def _manaframe_group_source_sql(alias: str = "cg") -> str:
    return f"""
    (
      SELECT
        mf.mfcode AS group_code,
        mf.mfcname AS group_name,
        dept.mfcode AS department_code,
        dept.mfcname AS department_name,
        CASE
          WHEN SUBSTRING(TRIM(BOTH FROM COALESCE(mf.mfcode, '')) FROM 1 FOR 3) ~ '^[0-9]+$'
          THEN SUBSTRING(TRIM(BOTH FROM COALESCE(mf.mfcode, '')) FROM 1 FOR 3)::integer
          ELSE NULL
        END AS store_id,
        mf.mfjyqy AS area_code,
        mf.mfjyqy AS area_name,
        mf.mfjyfs AS operation_method
      FROM manaframe mf
      LEFT JOIN manaframe dept
        ON mf.mfpcode = dept.mfcode
    ) {alias}
    """


def _counter_group_join_sql(enabled: bool, *, sales_alias: str = "s") -> str:
    if not enabled:
        return ""
    return (
        f"LEFT JOIN {_manaframe_group_source_sql('cg')} "
        f"ON {sales_alias}.sglmfid = cg.group_code"
    )


def _stores_market_join_sql(has_stores: bool) -> str:
    """将 ERP 市场号 sglmarket 对齐到 stores.store_code，与柜组 store_id 统一到同一门店主键，避免「4」与「604」拆成两行。"""
    if not has_stores:
        return ""
    return (
        "LEFT JOIN stores st_mkt ON TRIM(BOTH FROM COALESCE(st_mkt.store_code, '')) = "
        "TRIM(BOTH FROM COALESCE(s.sglmarket::varchar, ''))"
    )


def _resolved_store_id_sql(
    has_counter_groups: bool,
    *,
    has_stores: bool = False,
    sales_alias: str = "s",
) -> str:
    if has_counter_groups and has_stores:
        return (
            f"COALESCE((st_mkt.store_id)::varchar, (cg.store_id)::varchar, "
            f"{sales_alias}.sglmarket::varchar)"
        )
    if has_counter_groups:
        return f"COALESCE((cg.store_id)::varchar, {sales_alias}.sglmarket::varchar)"
    if has_stores:
        return f"COALESCE((st_mkt.store_id)::varchar, {sales_alias}.sglmarket::varchar)"
    return f"{sales_alias}.sglmarket::varchar"


def _group_scope_select_sql(enabled: bool, *, has_stores: bool = False) -> str:
    store_key = _resolved_store_id_sql(
        enabled,
        has_stores=has_stores,
    )
    if not enabled:
        return (
            f"s.sglmfid AS group_code, NULL::varchar AS group_name, "
            f"NULL::varchar AS department_code, NULL::varchar AS department_name, "
            f"{store_key} AS store_id"
        )
    return (
        "COALESCE(cg.group_code, s.sglmfid) AS group_code, "
        "cg.group_name AS group_name, "
        "cg.department_code AS department_code, "
        "cg.department_name AS department_name, "
        f"{store_key} AS store_id"
    )


def _store_scope_filter_sql(has_counter_groups: bool, has_stores: bool) -> str:
    """按门店筛选：兼容 ERP 市场号、柜组门店主键、以及市场号解析到的 stores.store_id。"""
    if has_counter_groups and has_stores:
        return (
            " AND (s.sglmarket::varchar = :store_id OR cg.store_id::varchar = :store_id OR "
            "(st_mkt.store_id IS NOT NULL AND st_mkt.store_id::varchar = :store_id))"
        )
    if has_counter_groups:
        return " AND (s.sglmarket::varchar = :store_id OR cg.store_id::varchar = :store_id)"
    if has_stores:
        return (
            " AND (s.sglmarket::varchar = :store_id OR "
            "(st_mkt.store_id IS NOT NULL AND st_mkt.store_id::varchar = :store_id))"
        )
    return " AND s.sglmarket::varchar = :store_id"


def _row_allowed(scope, row: dict[str, Any]) -> bool:
    return scope_allows_business(
        scope,
        store_id=row.get("store_id"),
        department_code=row.get("department_code"),
        department_name=row.get("department_name"),
        group_code=row.get("group_code"),
        supplier_code=row.get("supplier_code"),
        brand_code=row.get("brand_code"),
        category_code=row.get("category_code"),
    )


def _strip_scope(row: dict[str, Any]) -> dict[str, Any]:
    row.pop("store_id", None)
    return row


def _scope_match_sql(expressions: list[str], param_name: str) -> str:
    return "(" + " OR ".join(f"upper(trim(COALESCE(({expr})::varchar, ''))) = ANY(:{param_name})" for expr in expressions) + ")"


def _business_scope_filter_sql(
    scope,
    params: dict[str, Any],
    *,
    prefix: str,
    store_expr: str | None = None,
    department_code_expr: str | None = None,
    department_name_expr: str | None = None,
    group_expr: str | None = None,
    supplier_expr: str | None = None,
    brand_code_expr: str | None = None,
    brand_name_expr: str | None = None,
    category_code_expr: str | None = None,
    category_name_expr: str | None = None,
    floor_expr: str | None = None,
) -> str:
    """Translate business data scope to SQL so LIMIT is applied after permissions."""
    if "__all__" in scope.deny:
        return " AND 1=0"

    clauses: list[str] = []
    dimensions = {
        "store": [expr for expr in [store_expr] if expr],
        "department": [expr for expr in [department_code_expr, department_name_expr] if expr],
        "group": [expr for expr in [group_expr] if expr],
        "supplier": [expr for expr in [supplier_expr] if expr],
        "brand": [expr for expr in [brand_code_expr, brand_name_expr] if expr],
        "category": [expr for expr in [category_code_expr, category_name_expr] if expr],
        "floor": [expr for expr in [floor_expr] if expr],
    }

    for dimension, expressions in dimensions.items():
        denied = sorted(scope.deny.get(dimension, set()))
        if denied and expressions:
            param = f"{prefix}_deny_{dimension}"
            params[param] = denied
            clauses.append(f"AND NOT {_scope_match_sql(expressions, param)}")

    if scope.all_access:
        return " " + " ".join(clauses) if clauses else ""

    allow_clauses: list[str] = []
    for dimension, expressions in dimensions.items():
        allowed = sorted(scope.allow.get(dimension, set()))
        if allowed and expressions:
            param = f"{prefix}_allow_{dimension}"
            params[param] = allowed
            allow_clauses.append(_scope_match_sql(expressions, param))

    if not allow_clauses:
        clauses.append("AND 1=0")
    else:
        clauses.append("AND (" + " OR ".join(allow_clauses) + ")")
    return " " + " ".join(clauses)


def _scope_explicitly_rejects_store(scope, store_id: str) -> bool:
    """Preflight only explicit store constraints; other dimensions need row context."""
    if "__all__" in scope.deny:
        return True
    normalized_store = str(store_id).strip().upper()
    denied_stores = {str(value).strip().upper() for value in scope.deny.get("store", set())}
    if normalized_store in denied_stores:
        return True
    if scope.all_access:
        return False
    allowed_stores = {str(value).strip().upper() for value in scope.allow.get("store", set())}
    other_allow_dimensions = any(
        scope.allow.get(dimension, set())
        for dimension in ("department", "group", "category", "floor")
    )
    return (
        bool(allowed_stores)
        and not other_allow_dimensions
        and normalized_store not in allowed_stores
    )


def _od0002_store_id_for_code(db: Session, store_code: str) -> str | None:
    row = db.execute(
        text("""
            SELECT st.store_id::text
            FROM stores st
            WHERE st.is_active IS TRUE
              AND TRIM(BOTH FROM COALESCE(st.store_code, '')) = :store_code
            ORDER BY st.store_id
            LIMIT 1
        """),
        {"store_code": store_code},
    ).first()
    return str(row[0]) if row is not None else None


def _hdyy01_deny_resolution_guard_sql(scope: Any) -> str:
    """Fail closed when a denied HDYY01 dimension cannot be resolved."""
    if "__all__" in scope.deny:
        return ""

    guards: list[str] = []
    if scope.deny.get("store", set()):
        guards.append("AND st.store_id IS NOT NULL")
    if scope.deny.get("department", set()):
        guards.append("AND dept.normalized_mfcode IS NOT NULL")
    if scope.deny.get("group", set()):
        guards.append(
            "AND NULLIF(UPPER(TRIM(BOTH FROM COALESCE(s.sglmfid, ''))), '') "
            "IS NOT NULL"
        )
    if scope.deny.get("category", set()):
        guards.append("AND h.normalized_level3_code IS NOT NULL")
    if scope.deny.get("floor", set()):
        guards.append(
            "AND mf.normalized_mfcode IS NOT NULL "
            "AND NULLIF(TRIM(BOTH FROM COALESCE(mf.mflc, '')), '') IS NOT NULL"
        )
    return " " + " ".join(guards) if guards else ""


def _hy0001_deny_resolution_guard_sql(scope: Any) -> str:
    """Fail closed when a denied HY0001 dimension cannot be resolved."""
    if "__all__" in scope.deny:
        return ""

    guards: list[str] = []
    if scope.deny.get("store", set()):
        guards.append("AND st.store_id IS NOT NULL")
    if scope.deny.get("department", set()):
        guards.append("AND NULLIF(TRIM(BOTH FROM dept.mfcode), '') IS NOT NULL")
    if scope.deny.get("group", set()):
        guards.append("AND NULLIF(TRIM(BOTH FROM mf.mfcode), '') IS NOT NULL")
    if scope.deny.get("category", set()):
        guards.append("AND ac.category_code IS NOT NULL")
    if scope.deny.get("floor", set()):
        guards.append("AND NULLIF(TRIM(BOTH FROM mf.mflc), '') IS NOT NULL")
    return " " + " ".join(guards) if guards else ""


@router.get("/reports/hdyy01/stores")
async def hdyy01_stores(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return every store visible to HDYY01, independent of sales dates."""
    require_permission(db, current_user, "sales.hdyy01.view")
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    scope_params: dict[str, Any] = {}
    scope_filter_sql = _business_scope_filter_sql(
        scope,
        scope_params,
        prefix="hdyy01_stores",
        store_expr="st.store_id::text",
        department_code_expr="dept.mfcode",
        department_name_expr="dept.mfcname",
        group_expr="mf.mfcode",
        category_code_expr="ac.category_code",
        category_name_expr="ac.category_name",
        floor_expr="mf.mflc",
    )
    return load_od0002_authorized_stores(
        db,
        TrustedScopeSql(scope_filter_sql),
        scope_params,
    )


@router.get("/reports/hdyy01/departments")
async def hdyy01_departments(
    store_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return permission-scoped HDYY01 department options."""
    require_permission(db, current_user, "sales.hdyy01.view")
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    scope_params: dict[str, Any] = {}
    scope_filter_sql = _business_scope_filter_sql(
        scope,
        scope_params,
        prefix="hdyy01_departments",
        store_expr="st.store_id::text",
        department_code_expr="dept.mfcode",
        department_name_expr="dept.mfcname",
        group_expr="mf.mfcode",
        category_code_expr="ac.category_code",
        category_name_expr="ac.category_name",
        floor_expr="mf.mflc",
    )
    selected_store = (store_id or "").strip() or None
    return load_od0002_authorized_departments(
        db, TrustedScopeSql(scope_filter_sql), scope_params, selected_store
    )


@router.get("/reports/hdyy01")
async def hdyy01_report(
    start_date: date,
    end_date: date,
    store_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    department_id: str | None = None,
):
    """HDYY01 group operation analysis report."""
    report, _ = _load_hdyy01_for_request(
        start_date, end_date, store_id, db, current_user, department_id
    )
    return report


def _load_hdyy01_for_request(
    start_date: date,
    end_date: date,
    store_id: str | None,
    db: Session,
    current_user: User,
    department_id: str | None = None,
) -> tuple[dict[str, Any], Any]:
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date must be on or after start_date",
        )

    selected_store = (store_id or "").strip() or None
    selected_department = (department_id or "").strip() or None

    require_permission(db, current_user, "sales.hdyy01.view")
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    has_explicit_store_scope = bool(
        scope.deny.get("store", set())
        or (not scope.all_access and scope.allow.get("store", set()))
    )
    selected_scope_store_id = (
        _od0002_store_id_for_code(db, selected_store)
        if selected_store is not None and has_explicit_store_scope
        else None
    )
    if selected_store is not None and has_explicit_store_scope and (
        selected_scope_store_id is None
        or _scope_explicitly_rejects_store(scope, selected_scope_store_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无该门店数据权限",
        )

    scope_params: dict[str, Any] = {}
    scope_filter_sql = _business_scope_filter_sql(
        scope,
        scope_params,
        prefix="hdyy01",
        store_expr="st.store_id::text",
        department_code_expr="dept.mfcode",
        department_name_expr="dept.mfcname",
        group_expr="s.sglmfid",
        category_code_expr="h.level2_code",
        category_name_expr="h.level2_name",
        floor_expr="mf.mflc",
    )
    scope_filter_sql += _hdyy01_deny_resolution_guard_sql(scope)
    report = load_hdyy01_report(
        db,
        TrustedScopeSql(scope_filter_sql),
        scope_params,
        start_date=start_date,
        end_date=end_date,
        selected_store=selected_store,
        selected_department=selected_department,
    )
    return report, scope


def _load_report_store_options(
    db: Session,
    current_user: User,
    *,
    permission_code: str,
    prefix: str,
) -> list[dict[str, Any]]:
    require_permission(db, current_user, permission_code)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    scope_params: dict[str, Any] = {}
    scope_filter_sql = _business_scope_filter_sql(
        scope,
        scope_params,
        prefix=prefix,
        store_expr="st.store_id::text",
        department_code_expr="dept.mfcode",
        department_name_expr="dept.mfcname",
        group_expr="mf.mfcode",
        category_code_expr="ac.category_code",
        category_name_expr="ac.category_name",
        floor_expr="mf.mflc",
    )
    return load_od0002_authorized_stores(
        db,
        TrustedScopeSql(scope_filter_sql),
        scope_params,
    )


def _load_report_department_options(
    db: Session,
    current_user: User,
    store_id: str | None,
    *,
    permission_code: str,
    prefix: str,
) -> list[dict[str, Any]]:
    require_permission(db, current_user, permission_code)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    scope_params: dict[str, Any] = {}
    scope_filter_sql = _business_scope_filter_sql(
        scope,
        scope_params,
        prefix=prefix,
        store_expr="st.store_id::text",
        department_code_expr="dept.mfcode",
        department_name_expr="dept.mfcname",
        group_expr="mf.mfcode",
        category_code_expr="ac.category_code",
        category_name_expr="ac.category_name",
        floor_expr="mf.mflc",
    )
    selected_store = (store_id or "").strip() or None
    return load_od0002_authorized_departments(
        db, TrustedScopeSql(scope_filter_sql), scope_params, selected_store
    )


@router.get("/reports/od0002/stores")
async def od0002_stores(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return every store visible to OD0002, independent of sales dates."""
    return _load_report_store_options(
        db,
        current_user,
        permission_code="sales.od0002.view",
        prefix="od0002_stores",
    )


@router.get("/reports/od0002/departments")
async def od0002_departments(
    store_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return permission-scoped OD0002 department options."""
    return _load_report_department_options(
        db,
        current_user,
        store_id,
        permission_code="sales.od0002.view",
        prefix="od0002_departments",
    )


@router.get("/reports/daily-followup/stores")
async def daily_followup_stores(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _load_report_store_options(
        db,
        current_user,
        permission_code=DAILY_FOLLOWUP_PERMISSION,
        prefix="daily_followup_stores",
    )


@router.get("/reports/daily-followup/departments")
async def daily_followup_departments(
    store_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _load_report_department_options(
        db,
        current_user,
        store_id,
        permission_code=DAILY_FOLLOWUP_PERMISSION,
        prefix="daily_followup_departments",
    )


@router.get("/reports/od0003/stores")
async def od0003_stores(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _load_report_store_options(
        db,
        current_user,
        permission_code=OD0003_PERMISSION,
        prefix="od0003_stores",
    )


@router.get("/reports/od0003/departments")
async def od0003_departments(
    store_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _load_report_department_options(
        db,
        current_user,
        store_id,
        permission_code=OD0003_PERMISSION,
        prefix="od0003_departments",
    )


@router.get("/reports/od0004/stores")
async def od0004_stores(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _load_report_store_options(
        db,
        current_user,
        permission_code=OD0004_PERMISSION,
        prefix="od0004_stores",
    )


@router.get("/reports/od0004/departments")
async def od0004_departments(
    store_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _load_report_department_options(
        db,
        current_user,
        store_id,
        permission_code=OD0004_PERMISSION,
        prefix="od0004_departments",
    )


@router.get("/reports/hy0001/stores")
async def hy0001_stores(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _load_report_store_options(
        db,
        current_user,
        permission_code=HY0001_PERMISSION,
        prefix="hy0001_stores",
    )


@router.get("/reports/hy0001/departments")
async def hy0001_departments(
    store_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _load_report_department_options(
        db,
        current_user,
        store_id,
        permission_code=HY0001_PERMISSION,
        prefix="hy0001_departments",
    )


@router.get("/reports/settled-gross-profit/stores")
async def settled_gross_profit_stores(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _load_report_store_options(
        db,
        current_user,
        permission_code=SETTLED_GROSS_PROFIT_PERMISSION,
        prefix="settled_gross_profit_stores",
    )


@router.get("/reports/settled-gross-profit/departments")
async def settled_gross_profit_departments(
    store_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _load_report_department_options(
        db,
        current_user,
        store_id,
        permission_code=SETTLED_GROSS_PROFIT_PERMISSION,
        prefix="settled_gross_profit_departments",
    )


@router.get("/reports/od0002")
async def od0002_report(
    start_date: date,
    end_date: date,
    store_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    department_id: str | None = None,
    prior_start_date: date | None = None,
    prior_end_date: date | None = None,
):
    """OD0002 sales and gross-profit comparison report."""
    report, _ = _load_od0002_for_request(
        start_date,
        end_date,
        store_id,
        db,
        current_user,
        department_id,
        prior_start_date,
        prior_end_date,
    )
    return report


@router.get("/reports/daily-followup")
async def daily_followup_report(
    financial_year: int = Query(..., ge=2000, le=2100),
    financial_month: int = Query(..., ge=1, le=12),
    dimension: Literal["departments", "groups", "special_sales"] = Query("departments"),
    store_id: str | None = None,
    department_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permission-scoped daily sales follow-up for one financial month."""
    selected_store = (store_id or "").strip() or None
    selected_department = (department_id or "").strip() or None

    require_permission(db, current_user, DAILY_FOLLOWUP_PERMISSION)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    has_explicit_store_scope = bool(
        scope.deny.get("store", set())
        or (not scope.all_access and scope.allow.get("store", set()))
    )
    selected_scope_store_id = (
        _od0002_store_id_for_code(db, selected_store)
        if selected_store is not None and has_explicit_store_scope
        else None
    )
    if selected_store is not None and has_explicit_store_scope and (
        selected_scope_store_id is None
        or _scope_explicitly_rejects_store(scope, selected_scope_store_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无该门店数据权限",
        )

    scope_params: dict[str, Any] = {}
    scope_filter_sql = _business_scope_filter_sql(
        scope,
        scope_params,
        prefix="daily_followup",
        store_expr="st.store_id::text",
        department_code_expr="dept.mfcode",
        department_name_expr="dept.mfcname",
        group_expr="mf.mfcode",
        category_code_expr="ac.category_code",
        category_name_expr="ac.category_name",
        floor_expr="mf.mflc",
    )
    report = load_daily_followup_report(
        db,
        TrustedScopeSql(scope_filter_sql),
        scope_params,
        financial_year=financial_year,
        financial_month=financial_month,
        dimension=dimension,
        selected_store=selected_store,
        selected_department=selected_department,
        cutoff_at_yesterday=True,
    )
    report["scope_description"] = _od0002_scope_description(scope)
    return report


@router.get("/reports/od0003")
async def od0003_report(
    financial_year: int = Query(..., ge=2000, le=2100),
    financial_month: int = Query(..., ge=1, le=12),
    store_id: str | None = None,
    department_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """OD0003 center sales follow-up, returned at brand/counter-group grain."""
    selected_store = (store_id or "").strip() or None
    selected_department = (department_id or "").strip() or None

    require_permission(db, current_user, OD0003_PERMISSION)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    has_explicit_store_scope = bool(
        scope.deny.get("store", set())
        or (not scope.all_access and scope.allow.get("store", set()))
    )
    selected_scope_store_id = (
        _od0002_store_id_for_code(db, selected_store)
        if selected_store is not None and has_explicit_store_scope
        else None
    )
    if selected_store is not None and has_explicit_store_scope and (
        selected_scope_store_id is None
        or _scope_explicitly_rejects_store(scope, selected_scope_store_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无该门店数据权限",
        )

    scope_params: dict[str, Any] = {}
    scope_filter_sql = _business_scope_filter_sql(
        scope,
        scope_params,
        prefix="od0003",
        store_expr="st.store_id::text",
        department_code_expr="dept.mfcode",
        department_name_expr="dept.mfcname",
        group_expr="mf.mfcode",
        category_code_expr="ac.category_code",
        category_name_expr="ac.category_name",
        floor_expr="mf.mflc",
    )
    report = load_daily_followup_report(
        db,
        TrustedScopeSql(scope_filter_sql),
        scope_params,
        financial_year=financial_year,
        financial_month=financial_month,
        dimension="groups",
        selected_store=selected_store,
        selected_department=selected_department,
        include_ytd=True,
    )
    report["scope_description"] = _od0002_scope_description(scope)
    return report


@router.get("/reports/od0004")
async def od0004_report(
    financial_year: int = Query(..., ge=2000, le=2100),
    dimension: Literal["departments", "groups", "special_sales"] = Query("departments"),
    store_id: str | None = None,
    department_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permission-scoped monthly sales follow-up for one financial year."""
    selected_store = (store_id or "").strip() or None
    selected_department = (department_id or "").strip() or None

    require_permission(db, current_user, OD0004_PERMISSION)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    has_explicit_store_scope = bool(
        scope.deny.get("store", set())
        or (not scope.all_access and scope.allow.get("store", set()))
    )
    selected_scope_store_id = (
        _od0002_store_id_for_code(db, selected_store)
        if selected_store is not None and has_explicit_store_scope
        else None
    )
    if selected_store is not None and has_explicit_store_scope and (
        selected_scope_store_id is None
        or _scope_explicitly_rejects_store(scope, selected_scope_store_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无该门店数据权限",
        )

    scope_params: dict[str, Any] = {}
    scope_filter_sql = _business_scope_filter_sql(
        scope,
        scope_params,
        prefix="od0004",
        store_expr="st.store_id::text",
        department_code_expr="dept.mfcode",
        department_name_expr="dept.mfcname",
        group_expr="mf.mfcode",
        category_code_expr="ac.category_code",
        category_name_expr="ac.category_name",
        floor_expr="mf.mflc",
    )
    report = load_monthly_followup_report(
        db,
        TrustedScopeSql(scope_filter_sql),
        scope_params,
        financial_year=financial_year,
        dimension=dimension,
        selected_store=selected_store,
        selected_department=selected_department,
    )
    report["scope_description"] = _od0002_scope_description(scope)
    return report


def _load_hy0001_for_request(
    start_date: date,
    end_date: date,
    store_id: str,
    db: Session,
    current_user: User,
    department_id: str | None = None,
) -> tuple[dict[str, Any], Any]:
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date must be on or after start_date",
        )

    selected_store = (store_id or "").strip()
    selected_department = (department_id or "").strip() or None
    if not selected_store:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="HY0001 requires one selected store",
        )

    require_permission(db, current_user, HY0001_PERMISSION)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    selected_scope_store_id = _od0002_store_id_for_code(db, selected_store)
    if selected_scope_store_id is None or _scope_explicitly_rejects_store(
        scope, selected_scope_store_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无该门店数据权限",
        )

    scope_params: dict[str, Any] = {}
    scope_filter_sql = _business_scope_filter_sql(
        scope,
        scope_params,
        prefix="hy0001",
        store_expr="st.store_id::text",
        department_code_expr="dept.mfcode",
        department_name_expr="dept.mfcname",
        group_expr="mf.mfcode",
        category_code_expr="ac.category_code",
        category_name_expr="ac.category_name",
        floor_expr="mf.mflc",
    )
    scope_filter_sql += _hy0001_deny_resolution_guard_sql(scope)
    report = load_hy0001_report(
        db,
        TrustedScopeSql(scope_filter_sql),
        scope_params,
        start_date=start_date,
        end_date=end_date,
        selected_store=selected_store,
        selected_department=selected_department,
    )
    report["scope_description"] = _od0002_scope_description(scope)
    return report, scope


@router.get("/reports/hy0001")
async def hy0001_report(
    start_date: date,
    end_date: date,
    store_id: str = Query(..., min_length=1),
    department_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """HY0001 key-brand member consumption by member level."""
    report, _ = _load_hy0001_for_request(
        start_date, end_date, store_id, db, current_user, department_id
    )
    return report


def _load_od0002_for_request(
    start_date: date,
    end_date: date,
    store_id: str | None,
    db: Session,
    current_user: User,
    department_id: str | None = None,
    prior_start_date: date | None = None,
    prior_end_date: date | None = None,
) -> tuple[dict[str, Any], Any]:
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date must be on or after start_date",
        )
    if (prior_start_date is None) != (prior_end_date is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="prior_start_date and prior_end_date must be provided together",
        )
    if prior_start_date is None or prior_end_date is None:
        prior_start_date, prior_end_date = compare_period(start_date, end_date)
    elif prior_end_date < prior_start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="prior_end_date must be on or after prior_start_date",
        )

    selected_store = (store_id or "").strip() or None
    selected_department = (department_id or "").strip() or None

    require_permission(db, current_user, "sales.od0002.view")
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    has_explicit_store_scope = bool(
        scope.deny.get("store", set())
        or (not scope.all_access and scope.allow.get("store", set()))
    )
    selected_scope_store_id = (
        _od0002_store_id_for_code(db, selected_store)
        if selected_store is not None and has_explicit_store_scope
        else None
    )
    if selected_store is not None and has_explicit_store_scope and (
        selected_scope_store_id is None
        or _scope_explicitly_rejects_store(scope, selected_scope_store_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无该门店数据权限",
        )

    scope_params: dict[str, Any] = {}
    scope_filter_sql = _business_scope_filter_sql(
        scope,
        scope_params,
        prefix="od0002",
        store_expr="st.store_id::text",
        department_code_expr="dept.mfcode",
        department_name_expr="dept.mfcname",
        group_expr="mf.mfcode",
        category_code_expr="ac.category_code",
        category_name_expr="ac.category_name",
        floor_expr="mf.mflc",
    )
    report = load_od0002_report(
        db,
        TrustedScopeSql(scope_filter_sql),
        scope_params,
        start_date=start_date,
        end_date=end_date,
        prior_start_date=prior_start_date,
        prior_end_date=prior_end_date,
        selected_store=selected_store,
        selected_department=selected_department,
    )
    return report, scope


@router.get("/reports/settled-gross-profit")
async def settled_gross_profit_report(
    start_date: date,
    end_date: date,
    store_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    department_id: str | None = None,
):
    """Settlement-adjusted sales gross-profit detail report."""
    report, _ = _load_settled_gross_profit_for_request(
        start_date, end_date, store_id, db, current_user, department_id
    )
    return report


def _load_settled_gross_profit_for_request(
    start_date: date,
    end_date: date,
    store_id: str | None,
    db: Session,
    current_user: User,
    department_id: str | None = None,
) -> tuple[dict[str, Any], Any]:
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date must be on or after start_date",
        )

    selected_store = (store_id or "").strip() or None
    selected_department = (department_id or "").strip() or None
    require_permission(db, current_user, SETTLED_GROSS_PROFIT_PERMISSION)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    has_explicit_store_scope = bool(
        scope.deny.get("store", set())
        or (not scope.all_access and scope.allow.get("store", set()))
    )
    selected_scope_store_id = (
        _od0002_store_id_for_code(db, selected_store)
        if selected_store is not None and has_explicit_store_scope
        else None
    )
    if selected_store is not None and has_explicit_store_scope and (
        selected_scope_store_id is None
        or _scope_explicitly_rejects_store(scope, selected_scope_store_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无该门店数据权限",
        )

    scope_params: dict[str, Any] = {}
    scope_filter_sql = _business_scope_filter_sql(
        scope,
        scope_params,
        prefix="settled_gross_profit",
        store_expr="st.store_id::text",
        department_code_expr="dept.mfcode",
        department_name_expr="dept.mfcname",
        group_expr="mf.mfcode",
        category_code_expr="ac.category_code",
        category_name_expr="ac.category_name",
        floor_expr="mf.mflc",
    )
    report = load_settled_gross_profit_report(
        db,
        TrustedScopeSql(scope_filter_sql),
        scope_params,
        start_date=start_date,
        end_date=end_date,
        selected_store=selected_store,
        selected_department=selected_department,
    )
    return report, scope


def _od0002_scope_description(scope: Any) -> str:
    if scope.all_access:
        base = "全部业务数据"
    elif scope.allow:
        parts = [
            f"{dimension}=" + ",".join(sorted(values))
            for dimension, values in sorted(scope.allow.items()) if values
        ]
        base = "；".join(parts) or "无授权数据"
    else:
        base = "无授权数据"
    denied = [
        f"{dimension}=" + ",".join(sorted(values))
        for dimension, values in sorted(scope.deny.items()) if values
    ]
    if denied:
        base += "；排除 " + "；".join(denied)
    return "当前用户权限范围：" + base


class _ClosingStreamingResponse(StreamingResponse):
    """Close an export file even when ASGI sending aborts before background tasks."""

    def __init__(self, *args, close_file, **kwargs):
        super().__init__(*args, **kwargs)
        self._close_file = close_file

    async def __call__(self, scope, receive, send) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            self._close_file()


@router.get("/reports/hy0001/export")
async def hy0001_export(
    start_date: date,
    end_date: date,
    store_id: str = Query(..., min_length=1),
    department_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report, _ = _load_hy0001_for_request(
        start_date, end_date, store_id, db, current_user, department_id
    )
    export_file = await run_in_threadpool(build_hy0001_workbook_file, report)
    filename = (
        f"HY0001重点品牌会员消费情况_{store_id}_"
        f"{start_date.isoformat()}_{end_date.isoformat()}.xlsx"
    )

    def stream_chunks():
        while chunk := export_file.read(64 * 1024):
            yield chunk

    return _ClosingStreamingResponse(
        stream_chunks(),
        close_file=export_file.close,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
        background=BackgroundTask(export_file.close),
    )


@router.get("/reports/hdyy01/export")
async def hdyy01_export(
    start_date: date,
    end_date: date,
    store_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    department_id: str | None = None,
):
    report, scope = _load_hdyy01_for_request(
        start_date, end_date, store_id, db, current_user, department_id
    )
    export_report = dict(report)
    export_report["scope_description"] = _od0002_scope_description(scope)
    export_file = await run_in_threadpool(
        build_hdyy01_workbook_file, export_report
    )
    filename = (
        "HDYY01柜组经营分析表_"
        f"{start_date.isoformat()}_{end_date.isoformat()}.xlsx"
    )

    def stream_chunks():
        while chunk := export_file.read(64 * 1024):
            yield chunk

    return _ClosingStreamingResponse(
        stream_chunks(),
        close_file=export_file.close,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
        background=BackgroundTask(export_file.close),
    )


@router.get("/reports/od0002/export")
async def od0002_export(
    start_date: date,
    end_date: date,
    store_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    department_id: str | None = None,
    prior_start_date: date | None = None,
    prior_end_date: date | None = None,
):
    report, scope = _load_od0002_for_request(
        start_date,
        end_date,
        store_id,
        db,
        current_user,
        department_id,
        prior_start_date,
        prior_end_date,
    )
    export_report = dict(report)
    export_report["scope_description"] = _od0002_scope_description(scope)
    export_file = await run_in_threadpool(build_od0002_workbook_file, export_report)
    filename = f"OD0002_门店销售毛利汇总表_{start_date.isoformat()}_{end_date.isoformat()}.xlsx"

    def stream_chunks():
        while chunk := export_file.read(64 * 1024):
            yield chunk

    return StreamingResponse(
        stream_chunks(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
        background=BackgroundTask(export_file.close),
    )


@router.get("/reports/settled-gross-profit/export")
async def settled_gross_profit_export(
    start_date: date,
    end_date: date,
    store_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    department_id: str | None = None,
):
    report, scope = _load_settled_gross_profit_for_request(
        start_date, end_date, store_id, db, current_user, department_id
    )
    export_report = dict(report)
    export_report["scope_description"] = _od0002_scope_description(scope)
    export_file = await run_in_threadpool(
        build_settled_gross_profit_workbook_file,
        export_report,
    )
    filename = (
        "结算后销售毛利排行表_"
        f"{start_date.isoformat()}_{end_date.isoformat()}.xlsx"
    )

    def stream_chunks():
        while chunk := export_file.read(64 * 1024):
            yield chunk

    return _ClosingStreamingResponse(
        stream_chunks(),
        close_file=export_file.close,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
        background=BackgroundTask(export_file.close),
    )


@router.get("/reports/inventory-movement-detail")
def inventory_movement_detail_report(
    start_date: date = Query(..., description="发生开始日期 YYYY-MM-DD"),
    end_date: date = Query(..., description="发生结束日期 YYYY-MM-DD"),
    accounting_start_date: date | None = Query(None, description="记账开始日期 YYYY-MM-DD"),
    accounting_end_date: date | None = Query(None, description="记账结束日期 YYYY-MM-DD"),
    store: str | None = Query(None, description="门店编码或名称（模糊查询）"),
    group: str | None = Query(None, description="柜组编码或名称（模糊查询）"),
    supplier: str | None = Query(None, description="供应商编码或名称（模糊查询）"),
    goods_code: str | None = Query(None, description="商品代码（模糊查询）"),
    goods_name: str | None = Query(None, description="商品名称（模糊查询）"),
    barcode: str | None = Query(None, description="商品条码（模糊查询）"),
    specification: str | None = Query(None, description="商品规格（模糊查询）"),
    subinventory: str | None = Query(None, description="子库存编码（精确查询）"),
    limit: int = Query(5000, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = _inventory_movement_filters(
        start_date=start_date,
        end_date=end_date,
        accounting_start_date=accounting_start_date,
        accounting_end_date=accounting_end_date,
        store=store,
        group=group,
        supplier=supplier,
        goods_code=goods_code,
        goods_name=goods_name,
        barcode=barcode,
        specification=specification,
        subinventory=subinventory,
    )
    report, _scope = _load_inventory_movement_report_for_request(
        db=db,
        current_user=current_user,
        filters=filters,
        limit=limit,
        offset=offset,
    )
    return report


@router.get("/reports/inventory-movement-detail/export")
def inventory_movement_detail_export(
    start_date: date = Query(..., description="发生开始日期 YYYY-MM-DD"),
    end_date: date = Query(..., description="发生结束日期 YYYY-MM-DD"),
    accounting_start_date: date | None = Query(None, description="记账开始日期 YYYY-MM-DD"),
    accounting_end_date: date | None = Query(None, description="记账结束日期 YYYY-MM-DD"),
    store: str | None = Query(None, description="门店编码或名称（模糊查询）"),
    group: str | None = Query(None, description="柜组编码或名称（模糊查询）"),
    supplier: str | None = Query(None, description="供应商编码或名称（模糊查询）"),
    goods_code: str | None = Query(None, description="商品代码（模糊查询）"),
    goods_name: str | None = Query(None, description="商品名称（模糊查询）"),
    barcode: str | None = Query(None, description="商品条码（模糊查询）"),
    specification: str | None = Query(None, description="商品规格（模糊查询）"),
    subinventory: str | None = Query(None, description="子库存编码（精确查询）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = _inventory_movement_filters(
        start_date=start_date,
        end_date=end_date,
        accounting_start_date=accounting_start_date,
        accounting_end_date=accounting_end_date,
        store=store,
        group=group,
        supplier=supplier,
        goods_code=goods_code,
        goods_name=goods_name,
        barcode=barcode,
        specification=specification,
        subinventory=subinventory,
    )
    report, scope = _load_inventory_movement_report_for_request(
        db=db,
        current_user=current_user,
        filters=filters,
        limit=MAX_EXPORT_ROWS,
        offset=0,
    )
    total_count = int(report.get("summary", {}).get("total_count") or 0)
    if total_count > MAX_EXPORT_ROWS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"结果共 {total_count} 行，超过单次导出上限 {MAX_EXPORT_ROWS} 行，请缩小查询范围",
        )

    filter_labels = {
        "start_date": "发生开始日期",
        "end_date": "发生结束日期",
        "accounting_start_date": "记账开始日期",
        "accounting_end_date": "记账结束日期",
        "store": "门店",
        "group": "柜组",
        "supplier": "供应商",
        "goods_code": "商品代码",
        "goods_name": "商品名称",
        "barcode": "商品条码",
        "specification": "商品规格",
        "subinventory": "子库存",
    }
    filter_description = "；".join(
        f"{filter_labels[key]}={value.isoformat() if isinstance(value, date) else str(value).strip()}"
        for key, value in filters.items()
        if value is not None and str(value).strip()
    )
    export_file = build_inventory_movement_workbook_file(
        report,
        filter_description=filter_description,
        scope_description=_od0002_scope_description(scope),
    )
    filename = f"商品进销存明细报表_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"

    def stream_chunks():
        while chunk := export_file.read(64 * 1024):
            yield chunk

    return StreamingResponse(
        stream_chunks(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
        background=BackgroundTask(export_file.close),
    )


def _prior_year_same_period(start_date: str | None, end_date: str | None) -> tuple[str | None, str | None]:
    """将日期区间平移至上一年同日（遇 2/29 则退回 2/28），用于同期对比。"""
    if not start_date or not end_date:
        return None, None
    try:
        d0 = date.fromisoformat(start_date.strip())
        d1 = date.fromisoformat(end_date.strip())
    except ValueError:
        return None, None

    def shift_back(d: date) -> date:
        try:
            return d.replace(year=d.year - 1)
        except ValueError:
            return date(d.year - 1, 2, 28)

    return shift_back(d0).isoformat(), shift_back(d1).isoformat()


def _merge_store_summaries_same_period(
    current: list[dict[str, Any]],
    prior: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    prior_map = {str(r.get("store_id") or "").strip(): r for r in prior if r.get("store_id") is not None}
    out: list[dict[str, Any]] = []
    for row in current:
        sid = str(row.get("store_id") or "").strip()
        p = prior_map.pop(sid, None)
        spe = _num(p.get("effective_sales")) if p else 0.0
        snp = _num(p.get("net_profit")) if p else 0.0
        stc = _num(p.get("ticket_count")) if p else 0.0
        row["same_period_effective_sales"] = spe
        row["same_period_net_profit"] = snp
        row["same_period_ticket_count"] = stc
        row["same_period_margin"] = (snp / spe) if spe else 0.0
        out.append(row)
    for sid, p in prior_map.items():
        spe = _num(p.get("effective_sales"))
        snp = _num(p.get("net_profit"))
        out.append(
            {
                "store_id": sid,
                "department_count": 0,
                "group_count": 0,
                "ticket_count": 0,
                "quantity": 0,
                "gross_sales": 0.0,
                "effective_sales": 0.0,
                "net_profit": 0.0,
                "net_margin": 0.0,
                "ticket_margin": 0.0,
                "same_period_effective_sales": spe,
                "same_period_net_profit": snp,
                "same_period_ticket_count": _num(p.get("ticket_count")),
                "same_period_margin": (snp / spe) if spe else 0.0,
            }
        )
    out.sort(
        key=lambda r: max(_num(r.get("effective_sales")), _num(r.get("same_period_effective_sales"))),
        reverse=True,
    )
    return out


def _department_bucket_key(row: dict[str, Any]) -> str:
    return f"{row.get('department_code') or ''}|{row.get('department_name') or '未归属部门'}"


def _aggregate_group_rows_to_departments(
    group_rows: Iterable[dict[str, Any]],
    scope,
) -> list[dict[str, Any]]:
    departments: dict[str, dict[str, Any]] = {}
    for row in group_rows:
        if not _row_allowed(scope, row):
            continue
        key = _department_bucket_key(row)
        target = departments.setdefault(
            key,
            {
                "department_code": row.get("department_code") or "",
                "department_name": row.get("department_name") or "未归属部门",
                "group_count": 0,
                "ticket_count": 0,
                "quantity": 0,
                "gross_sales": 0,
                "effective_sales": 0,
                "net_profit": 0,
            },
        )
        target["group_count"] += 1
        target["ticket_count"] += _num(row.get("ticket_count"))
        target["quantity"] += _num(row.get("quantity"))
        target["gross_sales"] += _num(row.get("gross_sales"))
        target["effective_sales"] += _num(row.get("effective_sales"))
        target["net_profit"] += _num(row.get("net_profit"))
    result = sorted(departments.values(), key=department_display_sort_key)
    for item in result:
        eff = float(item.get("effective_sales") or 0)
        item["ticket_margin"] = (float(item.get("net_profit") or 0) / eff) if eff else 0.0
    return result


def _merge_department_summaries_same_period(
    current: list[dict[str, Any]],
    prior: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    pmap = {_department_bucket_key(r): r for r in prior}
    out: list[dict[str, Any]] = []
    for row in current:
        key = _department_bucket_key(row)
        p = pmap.pop(key, None)
        spe = _num(p.get("effective_sales")) if p else 0.0
        snp = _num(p.get("net_profit")) if p else 0.0
        stc = _num(p.get("ticket_count")) if p else 0.0
        row["same_period_effective_sales"] = spe
        row["same_period_net_profit"] = snp
        row["same_period_ticket_count"] = stc
        row["same_period_margin"] = (snp / spe) if spe else 0.0
        out.append(row)
    for _key, p in pmap.items():
        spe = _num(p.get("effective_sales"))
        snp = _num(p.get("net_profit"))
        out.append(
            {
                "department_code": p.get("department_code") or "",
                "department_name": p.get("department_name") or "未归属部门",
                "group_count": 0,
                "ticket_count": 0,
                "quantity": 0,
                "gross_sales": 0.0,
                "effective_sales": 0.0,
                "net_profit": 0.0,
                "ticket_margin": 0.0,
                "same_period_effective_sales": spe,
                "same_period_net_profit": snp,
                "same_period_ticket_count": _num(p.get("ticket_count")),
                "same_period_margin": (snp / spe) if spe else 0.0,
            }
        )
    out.sort(key=department_display_sort_key)
    return out


def _merge_group_summaries_same_period(
    current: list[dict[str, Any]],
    prior: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    pmap = {str(r.get("group_code") or "").strip(): r for r in prior if r.get("group_code")}
    out: list[dict[str, Any]] = []
    for row in current:
        gc = str(row.get("group_code") or "").strip()
        p = pmap.pop(gc, None)
        stc = _num(p.get("ticket_count")) if p else 0.0
        spe = _num(p.get("effective_sales")) if p else 0.0
        snp = _num(p.get("net_profit")) if p else 0.0
        row["same_period_ticket_count"] = stc
        row["same_period_effective_sales"] = spe
        row["same_period_net_profit"] = snp
        row["same_period_margin"] = (snp / spe) if spe else 0.0
        out.append(row)
    for _gc, p in pmap.items():
        spe = _num(p.get("effective_sales"))
        snp = _num(p.get("net_profit"))
        stc = _num(p.get("ticket_count"))
        out.append(
            {
                "group_code": p.get("group_code") or "",
                "group_name": p.get("group_name"),
                "department_code": p.get("department_code"),
                "department_name": p.get("department_name"),
                "ticket_count": 0,
                "line_count": 0,
                "quantity": 0,
                "priced_sales_amount": 0.0,
                "gross_sales": 0.0,
                "effective_sales": 0.0,
                "net_profit": 0.0,
                "net_margin": 0.0,
                "ticket_margin": 0.0,
                "same_period_ticket_count": stc,
                "same_period_effective_sales": spe,
                "same_period_net_profit": snp,
                "same_period_margin": (snp / spe) if spe else 0.0,
            }
        )
    out.sort(key=lambda r: _num(r.get("effective_sales")), reverse=True)
    return out


def _date_filter_sql(params: dict[str, Any], start_date: str | None, end_date: str | None) -> str:
    filters = []
    if start_date:
        filters.append("s.sglhsrq::date >= CAST(:start_date AS DATE)")
        params["start_date"] = start_date
    if end_date:
        filters.append("s.sglhsrq::date <= CAST(:end_date AS DATE)")
        params["end_date"] = end_date
    return (" AND " + " AND ".join(filters)) if filters else ""


def _latest_sales_accounting_date(db: Session) -> str | None:
    table_name = _salegoodslist_table(db)
    rows = _fetch_mappings(
        db,
        f"""
        SELECT MAX(s.sglhsrq) AS latest_date
        FROM {table_name} s
        WHERE s.sglhsrq <= CURRENT_DATE
        """,
        {},
    )
    return rows[0].get("latest_date") if rows and rows[0].get("latest_date") else None


def _ticket_product_filter_sql(
    params: dict[str, Any],
    *,
    goods_code: str | None,
    barcode: str | None,
    supplier_code: str | None,
) -> str:
    filters: list[str] = []
    if goods_code and goods_code.strip():
        filters.append("upper(trim(COALESCE(s.sglgdid, ''))) = upper(trim(:goods_code))")
        params["goods_code"] = goods_code.strip()
    if barcode and barcode.strip():
        filters.append("upper(trim(COALESCE(s.sglbarcode, ''))) = upper(trim(:barcode))")
        params["barcode"] = barcode.strip()
    if supplier_code and supplier_code.strip():
        filters.append("upper(trim(COALESCE(s.sglsupid, ''))) = upper(trim(:supplier_code))")
        params["supplier_code"] = supplier_code.strip()
    return (" AND " + " AND ".join(filters)) if filters else ""


def _sales_amount_sql(alias: str = "s") -> str:
    return f"COALESCE(NULLIF({alias}.sglyxssr, 0), {alias}.sglxssr, 0)"


def _cost_amount_sql(alias: str = "s") -> str:
    return f"COALESCE({alias}.sgln13, 0) + COALESCE({alias}.sgln14, 0)"


def _operation_method_label_sql(alias: str = "s") -> str:
    field = f"{alias}.sglwmid"
    return (
        "CASE "
        f"WHEN {field} = '1' THEN '经销' "
        f"WHEN {field} = '2' THEN '成本代销' "
        f"WHEN {field} = '3' THEN '扣率代销' "
        f"WHEN {field} = '4' THEN '联营' "
        f"WHEN {field} = '5' THEN '租赁' "
        f"ELSE COALESCE({field}, '') END"
    )


def _unassigned_department_filter_sql() -> str:
    """
    未归属部门：柜组未匹配，或柜组上部门编码/名称为空。
    与 department_summary 聚合桶「department_code 空 + 展示名 未归属部门」一致。
    """
    return (
        " AND (cg.group_code IS NULL OR "
        "(TRIM(BOTH FROM COALESCE(cg.department_code, '')) = '' "
        "AND TRIM(BOTH FROM COALESCE(cg.department_name, '')) = ''))"
    )


def _department_detail_filter_sql(
    params: dict[str, Any],
    *,
    store_id: str | None,
    department_code: str | None,
    unassigned_department: bool,
    has_counter_groups: bool,
    has_stores: bool,
    exclude_rental: bool = False,
    exclude_backoffice_departments: bool = False,
) -> str:
    filters = _sales_rental_exclusion_sql("s", enabled=exclude_rental)
    if store_id:
        filters += _store_scope_filter_sql(has_counter_groups, has_stores)
        params["store_id"] = store_id
    if has_counter_groups:
        filters += _sales_department_exclusion_sql(
            "cg",
            enabled=exclude_backoffice_departments,
        )
    if unassigned_department and has_counter_groups:
        filters += _unassigned_department_filter_sql()
    elif department_code and has_counter_groups:
        filters += " AND upper(trim(COALESCE(cg.department_code, ''))) = upper(trim(:department_code))"
        params["department_code"] = department_code
    return filters


def _code_name_display_sql(code_expr: str, name_expr: str) -> str:
    return (
        "CASE "
        f"WHEN NULLIF(TRIM(BOTH FROM COALESCE({code_expr}, '')), '') IS NOT NULL "
        f" AND NULLIF(TRIM(BOTH FROM COALESCE({name_expr}, '')), '') IS NOT NULL "
        f"THEN '[' || TRIM(BOTH FROM COALESCE({code_expr}, '')) || ']' || TRIM(BOTH FROM COALESCE({name_expr}, '')) "
        f"WHEN NULLIF(TRIM(BOTH FROM COALESCE({name_expr}, '')), '') IS NOT NULL "
        f"THEN TRIM(BOTH FROM COALESCE({name_expr}, '')) "
        f"WHEN NULLIF(TRIM(BOTH FROM COALESCE({code_expr}, '')), '') IS NOT NULL "
        f"THEN '[' || TRIM(BOTH FROM COALESCE({code_expr}, '')) || ']' "
        "ELSE '' END"
    )


def _inventory_filters(
    *,
    supplier: str | None,
    group: str | None,
    goods_code: str | None,
    goods_name: str | None,
    barcode: str | None,
    exact_group: str | None = None,
) -> dict[str, str | None]:
    return {
        "supplier": supplier,
        "group": group,
        "goods_code": goods_code,
        "goods_name": goods_name,
        "barcode": barcode,
        "exact_group": exact_group,
    }


def _historical_inventory_filters(
    *,
    start_date: date,
    end_date: date,
    supplier: str | None,
    group: str | None,
    goods_code: str | None,
    goods_name: str | None,
    barcode: str | None,
) -> dict[str, Any]:
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="库存开始日期不能晚于结束日期",
        )
    return {
        "start_date": start_date,
        "end_date": end_date,
        "supplier": supplier,
        "group": group,
        "goods_code": goods_code,
        "goods_name": goods_name,
        "barcode": barcode,
    }


def _inventory_movement_filters(
    *,
    start_date: date,
    end_date: date,
    accounting_start_date: date | None,
    accounting_end_date: date | None,
    store: str | None,
    group: str | None,
    supplier: str | None,
    goods_code: str | None,
    goods_name: str | None,
    barcode: str | None,
    specification: str | None,
    subinventory: str | None,
) -> dict[str, Any]:
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="发生开始日期不能晚于结束日期",
        )
    if (
        accounting_start_date
        and accounting_end_date
        and accounting_start_date > accounting_end_date
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="记账开始日期不能晚于结束日期",
        )
    return {
        "start_date": start_date,
        "end_date": end_date,
        "accounting_start_date": accounting_start_date,
        "accounting_end_date": accounting_end_date,
        "store": store,
        "group": group,
        "supplier": supplier,
        "goods_code": goods_code,
        "goods_name": goods_name,
        "barcode": barcode,
        "specification": specification,
        "subinventory": subinventory,
    }


def _inventory_request_scope(
    *,
    db: Session,
    current_user: User,
) -> tuple[Any, str, dict[str, Any]]:
    require_permission(db, current_user, "sales.inventory.view")
    required_tables = (
        "goodsstock",
        "goodsbase",
        "goodsmfprice",
        "manaframe",
        "stores",
        "supplierbase",
        "codebrand",
        "goodscat",
    )
    missing_tables = [table_name for table_name in required_tables if not _table_exists(db, table_name)]
    if missing_tables:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="库存报表依赖表未创建: " + ", ".join(missing_tables),
        )

    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    scope_params: dict[str, Any] = {}
    scope_sql = _business_scope_filter_sql(
        scope,
        scope_params,
        prefix="inventory_detail",
        store_expr="st.store_id::text",
        department_code_expr="area_node.mfcode",
        department_name_expr="area_node.mfcname",
        group_expr="gs.gstmfid",
        supplier_expr="gs.gstsupid",
        brand_code_expr="gb.gbppcode",
        brand_name_expr="cb.cbcname",
        category_code_expr="gb.gbcatcode",
        category_name_expr=CATEGORY_NAME_SQL,
        floor_expr="mf.mflc",
    )
    return scope, scope_sql, scope_params


def _load_inventory_report_for_request(
    *,
    db: Session,
    current_user: User,
    filters: dict[str, Any],
    limit: int,
    offset: int,
) -> tuple[dict[str, Any], Any]:
    scope, scope_sql, scope_params = _inventory_request_scope(
        db=db,
        current_user=current_user,
    )
    report = load_inventory_detail_report(
        db,
        filters=filters,
        scope_sql=scope_sql,
        scope_params=scope_params,
        limit=limit,
        offset=offset,
    )
    return report, scope


@router.get("/reports/inventory-lookup")
def inventory_lookup(
    exact_code: str = Query(..., min_length=1, max_length=100, description="商品条码或商品编码（精确查询）"),
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lookup_code = exact_code.strip()
    if not lookup_code:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="商品条码或商品编码不能为空",
        )
    filters: dict[str, Any] = {
        "exact_code": lookup_code,
        "include_zero": True,
        "has_goodsbarcode": _table_exists(db, "goodsbarcode"),
    }
    report, _scope = _load_inventory_report_for_request(
        db=db,
        current_user=current_user,
        filters=filters,
        limit=limit,
        offset=0,
    )
    return {**report, "query_code": lookup_code}


def _historical_inventory_request_scope(
    *,
    db: Session,
    current_user: User,
) -> tuple[Any, str, dict[str, Any]]:
    require_permission(db, current_user, "sales.inventory_history.view")
    required_tables = (
        "goodsstock_bak",
        "goodsbase",
        "goodsmfprice",
        "manaframe",
        "stores",
        "supplierbase",
        "codebrand",
        "goodscat",
    )
    missing_tables = [table_name for table_name in required_tables if not _table_exists(db, table_name)]
    if missing_tables:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="历史库存报表依赖表未创建: " + ", ".join(missing_tables),
        )

    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    scope_params: dict[str, Any] = {}
    scope_sql = _business_scope_filter_sql(
        scope,
        scope_params,
        prefix="historical_inventory_detail",
        store_expr="st.store_id::text",
        department_code_expr="area_node.mfcode",
        department_name_expr="area_node.mfcname",
        group_expr="gs.gstmfid",
        supplier_expr="gs.gstsupid",
        brand_code_expr="gb.gbppcode",
        brand_name_expr="cb.cbcname",
        category_code_expr="gb.gbcatcode",
        category_name_expr=CATEGORY_NAME_SQL,
        floor_expr="mf.mflc",
    )
    return scope, scope_sql, scope_params


def _load_historical_inventory_report_for_request(
    *,
    db: Session,
    current_user: User,
    filters: dict[str, Any],
    limit: int,
    offset: int,
) -> tuple[dict[str, Any], Any]:
    scope, scope_sql, scope_params = _historical_inventory_request_scope(
        db=db,
        current_user=current_user,
    )
    report = load_historical_inventory_detail_report(
        db,
        filters=filters,
        scope_sql=scope_sql,
        scope_params=scope_params,
        limit=limit,
        offset=offset,
    )
    return report, scope


def _inventory_movement_request_scope(
    *,
    db: Session,
    current_user: User,
) -> tuple[Any, str, dict[str, Any]]:
    require_permission(db, current_user, "sales.inventory_movement.view")
    required_tables = (
        "jxcgoodslist",
        "goodsbase",
        "manaframe",
        "stores",
        "supplierbase",
        "codebrand",
        "goodscat",
    )
    missing_tables = [table_name for table_name in required_tables if not _table_exists(db, table_name)]
    if missing_tables:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="进销存明细报表依赖表未创建: " + ", ".join(missing_tables),
        )

    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    scope_params: dict[str, Any] = {}
    scope_sql = _business_scope_filter_sql(
        scope,
        scope_params,
        prefix="inventory_movement_detail",
        store_expr="st.store_id::text",
        department_code_expr="area_node.mfcode",
        department_name_expr="area_node.mfcname",
        group_expr="j.jglmfid",
        supplier_expr="j.jglsupid",
        brand_code_expr="j.jglppcode",
        brand_name_expr="cb.cbcname",
        category_code_expr="j.jglcatid",
        category_name_expr=CATEGORY_NAME_SQL,
        floor_expr="mf.mflc",
    )
    return scope, scope_sql, scope_params


def _load_inventory_movement_report_for_request(
    *,
    db: Session,
    current_user: User,
    filters: dict[str, Any],
    limit: int,
    offset: int,
) -> tuple[dict[str, Any], Any]:
    scope, scope_sql, scope_params = _inventory_movement_request_scope(
        db=db,
        current_user=current_user,
    )
    report = load_inventory_movement_detail_report(
        db,
        filters=filters,
        scope_sql=scope_sql,
        scope_params=scope_params,
        limit=limit,
        offset=offset,
    )
    return report, scope


@router.get("/reports/inventory-movement-detail/options")
def inventory_movement_detail_filter_options(
    start_date: date = Query(..., description="发生开始日期 YYYY-MM-DD"),
    end_date: date = Query(..., description="发生结束日期 YYYY-MM-DD"),
    field: Literal["supplier", "group", "goods_code", "goods_name", "barcode"] = Query(...),
    q: str = Query(..., min_length=1, max_length=100, description="编码或名称关键词"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = _inventory_movement_filters(
        start_date=start_date,
        end_date=end_date,
        accounting_start_date=None,
        accounting_end_date=None,
        store=None,
        group=None,
        supplier=None,
        goods_code=None,
        goods_name=None,
        barcode=None,
        specification=None,
        subinventory=None,
    )
    _scope, scope_sql, scope_params = _inventory_movement_request_scope(
        db=db,
        current_user=current_user,
    )
    return {
        "options": load_inventory_movement_filter_options(
            db,
            field=field,
            query=q.strip(),
            filters=filters,
            scope_sql=scope_sql,
            scope_params=scope_params,
            limit=limit,
        )
    }


@router.get("/reports/inventory-departments")
def inventory_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _scope, scope_sql, scope_params = _inventory_request_scope(db=db, current_user=current_user)
    return {"options": load_inventory_departments(db, scope_sql=scope_sql, scope_params=scope_params)}


@router.get("/reports/inventory-department-summary")
def inventory_department_summary(
    department_code: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _scope, scope_sql, scope_params = _inventory_request_scope(db=db, current_user=current_user)
    selected_department = department_code.strip()
    if not selected_department:
        raise HTTPException(status_code=422, detail="部门编码不能为空")
    return load_inventory_department_summary(
        db,
        department_code=selected_department,
        scope_sql=scope_sql,
        scope_params=scope_params,
        limit=limit,
        offset=offset,
    )


@router.get("/reports/inventory-detail/options")
def inventory_detail_filter_options(
    field: Literal["supplier", "group", "goods_code", "goods_name", "barcode"] = Query(...),
    q: str = Query(..., min_length=1, max_length=100, description="编码或名称关键词"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _scope, scope_sql, scope_params = _inventory_request_scope(
        db=db,
        current_user=current_user,
    )
    return {
        "options": load_inventory_filter_options(
            db,
            field=field,
            query=q.strip(),
            scope_sql=scope_sql,
            scope_params=scope_params,
            limit=limit,
        )
    }


@router.get("/reports/inventory-detail")
def inventory_detail_report(
    supplier: str | None = Query(None, description="供应商编码或名称（模糊查询）"),
    group: str | None = Query(None, description="柜组编码或名称（模糊查询）"),
    goods_code: str | None = Query(None, description="商品代码（模糊查询）"),
    goods_name: str | None = Query(None, description="商品名称（模糊查询）"),
    barcode: str | None = Query(None, description="商品条码（模糊查询）"),
    exact_group: str | None = Query(None, description="柜组编码（精确查询）"),
    limit: int = Query(5000, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = _inventory_filters(
        supplier=supplier,
        group=group,
        goods_code=goods_code,
        goods_name=goods_name,
        barcode=barcode,
        exact_group=exact_group,
    )
    report, _scope = _load_inventory_report_for_request(
        db=db,
        current_user=current_user,
        filters=filters,
        limit=limit,
        offset=offset,
    )
    return report


@router.get("/reports/inventory-detail/export")
def inventory_detail_export(
    supplier: str | None = Query(None, description="供应商编码或名称（模糊查询）"),
    group: str | None = Query(None, description="柜组编码或名称（模糊查询）"),
    goods_code: str | None = Query(None, description="商品代码（模糊查询）"),
    goods_name: str | None = Query(None, description="商品名称（模糊查询）"),
    barcode: str | None = Query(None, description="商品条码（模糊查询）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = _inventory_filters(
        supplier=supplier,
        group=group,
        goods_code=goods_code,
        goods_name=goods_name,
        barcode=barcode,
    )
    report, scope = _load_inventory_report_for_request(
        db=db,
        current_user=current_user,
        filters=filters,
        limit=MAX_EXPORT_ROWS,
        offset=0,
    )
    total_count = int(report.get("summary", {}).get("total_count") or 0)
    if total_count > MAX_EXPORT_ROWS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"结果共 {total_count} 行，超过单次导出上限 {MAX_EXPORT_ROWS} 行，请缩小查询范围",
        )

    filter_labels = {
        "supplier": "供应商",
        "group": "柜组",
        "goods_code": "商品代码",
        "goods_name": "商品名称",
        "barcode": "商品条码",
    }
    filter_description = "；".join(
        f"{filter_labels[key]}={str(value).strip()}"
        for key, value in filters.items()
        if value is not None and str(value).strip()
    )
    export_file = build_inventory_workbook_file(
        report,
        filter_description=filter_description,
        scope_description=_od0002_scope_description(scope),
    )
    filename = f"实时库存查询_{date.today().strftime('%Y%m%d')}.xlsx"

    def stream_chunks():
        while chunk := export_file.read(64 * 1024):
            yield chunk

    return StreamingResponse(
        stream_chunks(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
        background=BackgroundTask(export_file.close),
    )


@router.get("/reports/historical-inventory-detail/options")
def historical_inventory_detail_filter_options(
    start_date: date = Query(..., description="库存开始日期 YYYY-MM-DD"),
    end_date: date = Query(..., description="库存结束日期 YYYY-MM-DD"),
    field: Literal["supplier", "group", "goods_code", "goods_name", "barcode"] = Query(...),
    q: str = Query(..., min_length=1, max_length=100, description="编码或名称关键词"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = _historical_inventory_filters(
        start_date=start_date,
        end_date=end_date,
        supplier=None,
        group=None,
        goods_code=None,
        goods_name=None,
        barcode=None,
    )
    _scope, scope_sql, scope_params = _historical_inventory_request_scope(
        db=db,
        current_user=current_user,
    )
    return {
        "options": load_historical_inventory_filter_options(
            db,
            field=field,
            query=q.strip(),
            filters=filters,
            scope_sql=scope_sql,
            scope_params=scope_params,
            limit=limit,
        )
    }


@router.get("/reports/historical-inventory-detail")
def historical_inventory_detail_report(
    start_date: date = Query(..., description="库存开始日期 YYYY-MM-DD"),
    end_date: date = Query(..., description="库存结束日期 YYYY-MM-DD"),
    supplier: str | None = Query(None, description="供应商编码或名称（模糊查询）"),
    group: str | None = Query(None, description="柜组编码或名称（模糊查询）"),
    goods_code: str | None = Query(None, description="商品代码（模糊查询）"),
    goods_name: str | None = Query(None, description="商品名称（模糊查询）"),
    barcode: str | None = Query(None, description="商品条码（模糊查询）"),
    limit: int = Query(5000, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = _historical_inventory_filters(
        start_date=start_date,
        end_date=end_date,
        supplier=supplier,
        group=group,
        goods_code=goods_code,
        goods_name=goods_name,
        barcode=barcode,
    )
    report, _scope = _load_historical_inventory_report_for_request(
        db=db,
        current_user=current_user,
        filters=filters,
        limit=limit,
        offset=offset,
    )
    return report


@router.get("/reports/historical-inventory-detail/export")
def historical_inventory_detail_export(
    start_date: date = Query(..., description="库存开始日期 YYYY-MM-DD"),
    end_date: date = Query(..., description="库存结束日期 YYYY-MM-DD"),
    supplier: str | None = Query(None, description="供应商编码或名称（模糊查询）"),
    group: str | None = Query(None, description="柜组编码或名称（模糊查询）"),
    goods_code: str | None = Query(None, description="商品代码（模糊查询）"),
    goods_name: str | None = Query(None, description="商品名称（模糊查询）"),
    barcode: str | None = Query(None, description="商品条码（模糊查询）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = _historical_inventory_filters(
        start_date=start_date,
        end_date=end_date,
        supplier=supplier,
        group=group,
        goods_code=goods_code,
        goods_name=goods_name,
        barcode=barcode,
    )
    report, scope = _load_historical_inventory_report_for_request(
        db=db,
        current_user=current_user,
        filters=filters,
        limit=MAX_EXPORT_ROWS,
        offset=0,
    )
    total_count = int(report.get("summary", {}).get("total_count") or 0)
    if total_count > MAX_EXPORT_ROWS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"结果共 {total_count} 行，超过单次导出上限 {MAX_EXPORT_ROWS} 行，请缩小查询范围",
        )

    filter_labels = {
        "start_date": "库存开始日期",
        "end_date": "库存结束日期",
        "supplier": "供应商",
        "group": "柜组",
        "goods_code": "商品代码",
        "goods_name": "商品名称",
        "barcode": "商品条码",
    }
    filter_description = "；".join(
        f"{filter_labels[key]}={value.isoformat() if isinstance(value, date) else str(value).strip()}"
        for key, value in filters.items()
        if value is not None and str(value).strip()
    )
    export_file = build_historical_inventory_workbook_file(
        report,
        filter_description=filter_description,
        scope_description=_od0002_scope_description(scope),
    )
    filename = f"历史库存明细报表_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"

    def stream_chunks():
        while chunk := export_file.read(64 * 1024):
            yield chunk

    return StreamingResponse(
        stream_chunks(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
        background=BackgroundTask(export_file.close),
    )


@router.get("/reports/commodity-sales-detail/departments", response_model=list[ReportDepartmentOption])
async def commodity_sales_detail_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """商品销售明细部门下拉：直接取 manaframe 的柜组上级部门主数据。"""
    require_permission(db, current_user, COMMODITY_DETAIL_PERMISSION)
    if not _table_exists(db, "manaframe"):
        return []

    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    params: dict[str, Any] = {}
    scope_filter = _business_scope_filter_sql(
        scope,
        params,
        prefix="report_csd_dept",
        store_expr="cg.store_id::varchar",
        department_code_expr="cg.department_code",
        department_name_expr="cg.department_name",
        group_expr="cg.group_code",
    )
    rows = _fetch_mappings(
        db,
        f"""
        SELECT
          TRIM(BOTH FROM COALESCE(cg.department_code, '')) AS department_code,
          TRIM(BOTH FROM COALESCE(cg.department_name, '')) AS department_name,
          {_code_name_display_sql("cg.department_code", "cg.department_name")} AS label
        FROM {_manaframe_group_source_sql("cg")}
        WHERE (
          NULLIF(TRIM(BOTH FROM COALESCE(cg.department_code, '')), '') IS NOT NULL
          OR NULLIF(TRIM(BOTH FROM COALESCE(cg.department_name, '')), '') IS NOT NULL
        )
        {_sales_department_exclusion_sql("cg")}
        {scope_filter}
        GROUP BY 1, 2, 3
        ORDER BY 1, 2
        """,
        params,
    )
    return rows


@router.get("/reports/commodity-sales-detail")
async def commodity_sales_detail_report(
    start_date: str | None = Query(None, description="发生日期起 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="发生日期止 YYYY-MM-DD"),
    account_start_date: str | None = Query(None, description="记账日期起 YYYY-MM-DD"),
    account_end_date: str | None = Query(None, description="记账日期止 YYYY-MM-DD"),
    store_id: str | None = Query(None, description="门店ID/市场号"),
    department: str | None = Query(None, description="部门编码/名称"),
    area: str | None = Query(None, description="库区/区域编码或名称"),
    supplier_code: str | None = Query(None, description="供应商编码"),
    goods_code: str | None = Query(None, description="商品编码"),
    group_code: str | None = Query(None, description="柜组编码/名称，支持模糊查询"),
    operation_method: str | None = Query(None, description="经营方式"),
    limit: int = Query(500, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ERP 633 商品销售明细：直接按 ERP SQL 口径汇总，使用 manaframe 作为柜组主数据。"""
    require_permission(db, current_user, COMMODITY_DETAIL_PERMISSION)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    table_name = _salegoodslist_table(db)
    if not _table_exists(db, "manaframe"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="柜组主数据表未创建: manaframe",
        )

    has_goodsbase = _table_exists(db, "goodsbase")
    has_sglgdname = _column_exists(db, table_name, "sglgdname")
    has_stores = _table_exists(db, "stores")
    mkt_join = (
        "LEFT JOIN stores st_mkt ON TRIM(BOTH FROM COALESCE(st_mkt.store_code, '')) = "
        "TRIM(BOTH FROM COALESCE(a.sglmarket::varchar, ''))"
        if has_stores
        else ""
    )
    goods_join = (
        "LEFT JOIN goodsbase gb ON upper(trim(COALESCE(gb.gbid, ''))) = upper(trim(COALESCE(a.sglgdid, '')))"
        if has_goodsbase
        else ""
    )
    if has_goodsbase and has_sglgdname:
        goods_name_expr = "COALESCE(NULLIF(gb.gbcname, ''), NULLIF(a.sglgdname, ''), '')"
    elif has_goodsbase:
        goods_name_expr = "COALESCE(NULLIF(gb.gbcname, ''), '')"
    elif has_sglgdname:
        goods_name_expr = "COALESCE(NULLIF(a.sglgdname, ''), '')"
    else:
        goods_name_expr = "''"

    params: dict[str, Any] = {"limit": limit}
    sale_filters = _date_filter_sql(params, start_date, end_date)
    if account_start_date:
        sale_filters += " AND s.sglhsrq >= :account_start_date"
        params["account_start_date"] = account_start_date
    if account_end_date:
        sale_filters += " AND s.sglhsrq <= :account_end_date"
        params["account_end_date"] = account_end_date
    if supplier_code:
        sale_filters += " AND upper(trim(COALESCE(s.sglsupid, ''))) = upper(trim(:supplier_code))"
        params["supplier_code"] = supplier_code.strip()
    if goods_code:
        sale_filters += " AND upper(trim(COALESCE(s.sglgdid, ''))) = upper(trim(:goods_code))"
        params["goods_code"] = goods_code.strip()
    if group_code:
        sale_filters += (
            " AND (upper(trim(COALESCE(s.sglmfid, ''))) LIKE upper(:group_like) "
            "OR EXISTS ("
            f"  SELECT 1 FROM {_manaframe_group_source_sql('cg_filter')} "
            "  WHERE upper(trim(COALESCE(cg_filter.group_code, ''))) = upper(trim(COALESCE(s.sglmfid, ''))) "
            "    AND upper(trim(COALESCE(cg_filter.group_name, ''))) LIKE upper(:group_like)"
            "))"
        )
        params["group_like"] = f"%{group_code.strip()}%"

    outer_filters = _sales_department_exclusion_sql("cg")
    if store_id:
        if has_stores:
            outer_filters += (
                " AND (a.sglmarket::varchar = :store_id OR cg.store_id::varchar = :store_id OR "
                "(st_mkt.store_id IS NOT NULL AND st_mkt.store_id::varchar = :store_id))"
            )
        else:
            outer_filters += " AND (a.sglmarket::varchar = :store_id OR cg.store_id::varchar = :store_id)"
        params["store_id"] = store_id
    if department:
        outer_filters += (
            " AND (upper(trim(COALESCE(cg.department_code, ''))) = upper(trim(:department)) "
            "OR upper(trim(COALESCE(cg.department_name, ''))) LIKE upper(:department_like))"
        )
        params["department"] = department.strip()
        params["department_like"] = f"%{department.strip()}%"
    if area:
        outer_filters += (
            " AND (upper(trim(COALESCE(cg.area_code, ''))) = upper(trim(:area)) "
            "OR upper(trim(COALESCE(cg.area_name, ''))) LIKE upper(:area_like))"
        )
        params["area"] = area.strip()
        params["area_like"] = f"%{area.strip()}%"
    if operation_method:
        outer_filters += " AND upper(trim(COALESCE(cg.operation_method, ''))) = upper(trim(:operation_method))"
        params["operation_method"] = operation_method.strip()

    floor_expr = _code_name_display_sql("cg.department_code", "cg.department_name")
    area_expr = _code_name_display_sql("cg.area_code", "cg.area_name")
    group_expr = _code_name_display_sql("COALESCE(cg.group_code, a.sglmfid)", "cg.group_name")
    store_key = (
        "COALESCE((cg.store_id)::varchar, (st_mkt.store_id)::varchar, a.sglmarket::varchar)"
        if has_stores
        else "COALESCE((cg.store_id)::varchar, a.sglmarket::varchar)"
    )
    scope_filter = _business_scope_filter_sql(
        scope,
        params,
        prefix="report_csd",
        store_expr=store_key,
        department_code_expr="cg.department_code",
        department_name_expr="cg.department_name",
        group_expr="COALESCE(cg.group_code, a.sglmfid)",
        supplier_expr="a.sglsupid",
    )
    gross_profit_expr = """
      CASE
        WHEN s.sglwmid = '1' THEN
          COALESCE(s.sglxssr, 0)
          - COALESCE(s.sgln13, 0)
          + CASE
              WHEN COALESCE(s.sglxssr, 0) = 0 AND COALESCE(s.sgln14, 0) = 0 THEN COALESCE(s.sgln2, 0)
              ELSE COALESCE(s.sgln14, 0)
            END
        ELSE COALESCE(s.sgln2, 0)
      END
    """
    agg_goods_name_select = ", MIN(s.sglgdname) AS sglgdname" if has_sglgdname else ""
    rows = _fetch_mappings(
        db,
        f"""
        WITH agg AS (
          SELECT
            s.sglmarket,
            s.sglmfid,
            s.sglsupid,
            s.sglgdid,
            s.sglbarcode,
            COALESCE(s.sglbasekl, 0) AS base_discount_rate,
            COALESCE(s.sglkl, 0) AS sales_discount_rate,
            CASE WHEN COALESCE(s.sglkl, 0) = COALESCE(s.sglbasekl, 0) THEN 0 ELSE COALESCE(s.sglkl, 0) END AS preferential_discount_rate,
            COALESCE(SUM(COALESCE(s.sglsjje, 0) * (COALESCE(s.sglbasekl, 0) - COALESCE(s.sglkl, 0))), 0) AS concession_amount,
            COALESCE(SUM(s.sglsl), 0) AS sales_qty,
            COALESCE(SUM(s.sglsjje), 0) AS priced_sales_amount,
            COALESCE(SUM(s.sglxssr), 0) AS sales_revenue,
            COALESCE(SUM({gross_profit_expr}), 0) AS gross_profit,
            COALESCE(SUM(COALESCE(s.sglxssr, 0) - COALESCE(s.sglgcert, 0) + COALESCE(s.sglsysy, 0)), 0) AS net_sales_amount,
            COALESCE(SUM(({gross_profit_expr}) - COALESCE(s.sglgcert, 0) + COALESCE(s.sglsysy, 0)), 0) AS net_gross_profit,
            COALESCE(SUM(COALESCE(s.sgln13, 0) + COALESCE(s.sgln14, 0)), 0) AS sales_cost,
            COALESCE(SUM(CASE WHEN s.sglwmid IN ('4', '5') THEN COALESCE(s.sglxssr, 0) * (1 - COALESCE(s.sglkl, 0)) ELSE COALESCE(s.sgln13, 0) + COALESCE(s.sgln14, 0) END), 0) AS net_sales_cost,
            COALESCE(SUM(s.sgltotzk), 0) AS total_discount,
            COALESCE(SUM(s.sglcustzk), 0) AS member_discount_amt,
            COALESCE(SUM(s.sglpopzk), 0) AS promo_discount_amt,
            COALESCE(SUM(s.sglgrantzk), 0) AS auth_discount_amt,
            COALESCE(SUM(COALESCE(s.sgltotzk, 0) - COALESCE(s.sglcustzk, 0) - COALESCE(s.sglpopzk, 0) - COALESCE(s.sglgrantzk, 0)), 0) AS other_discount_amt
            {agg_goods_name_select}
          FROM {table_name} s
          WHERE COALESCE(s.sglsjje, 0) <> 0 {sale_filters}
          GROUP BY
            s.sglmarket,
            s.sglmfid,
            s.sglsupid,
            s.sglgdid,
            s.sglbarcode,
            COALESCE(s.sglbasekl, 0),
            COALESCE(s.sglkl, 0),
            CASE WHEN COALESCE(s.sglkl, 0) = COALESCE(s.sglbasekl, 0) THEN 0 ELSE COALESCE(s.sglkl, 0) END
        )
        SELECT
          {floor_expr} AS floor_display,
          {area_expr} AS storage_area,
          {group_expr} AS counter_display,
          a.sglsupid AS supplier_display,
          a.sglgdid AS goods_code,
          a.sglbarcode AS barcode,
          {goods_name_expr} AS goods_name,
          a.base_discount_rate,
          a.sales_discount_rate,
          a.preferential_discount_rate,
          a.concession_amount,
          a.sales_qty,
          a.priced_sales_amount,
          a.sales_revenue,
          a.gross_profit,
          CASE WHEN a.sales_revenue = 0 THEN 0 ELSE a.gross_profit / NULLIF(a.sales_revenue, 0) END AS gross_margin_rate,
          a.net_sales_amount,
          a.net_gross_profit,
          CASE WHEN a.net_sales_amount = 0 THEN 0 ELSE a.net_gross_profit / NULLIF(a.net_sales_amount, 0) END AS net_gross_margin_rate,
          a.sales_cost,
          a.net_sales_cost,
          a.total_discount,
          a.member_discount_amt,
          a.promo_discount_amt,
          a.auth_discount_amt,
          a.other_discount_amt,
          COALESCE(cg.group_code, a.sglmfid) AS group_code,
          cg.group_name AS group_name,
          cg.department_code AS department_code,
          cg.department_name AS department_name,
          {store_key} AS store_id
        FROM agg a
        LEFT JOIN {_manaframe_group_source_sql("cg")} ON upper(trim(COALESCE(a.sglmfid, ''))) = upper(trim(COALESCE(cg.group_code, '')))
        {mkt_join}
        {goods_join}
        WHERE 1=1 {outer_filters} {scope_filter}
        ORDER BY floor_display, storage_area, counter_display, supplier_display, goods_code, barcode
        LIMIT :limit
        """,
        params,
    )
    return [_strip_scope(row) for row in rows]


def _group_level_sales_rows(
    db: Session,
    *,
    start_date: str | None,
    end_date: str | None,
    store_id: str | None,
    department_code: str | None,
    unassigned_department: bool = False,
    group_code: str | None,
    keyword: str | None,
    limit: int | None,
    unrestricted: bool = False,
    exclude_rental: bool = False,
    exclude_backoffice_departments: bool = False,
) -> list[dict[str, Any]]:
    """柜组粒度汇总（含 store_id 等 scope 字段），供柜组列表与门店聚合复用。

    unrestricted=True 时不做排序与 LIMIT，用于门店汇总，避免按销售额截断柜组导致门店不全。
    """
    table_name = _salegoodslist_table(db)
    has_counter_groups = _table_exists(db, "manaframe")
    has_stores = _table_exists(db, "stores")
    mkt_join = _stores_market_join_sql(has_stores)
    params: dict[str, Any] = {}
    date_filters = _date_filter_sql(params, start_date, end_date)
    date_filters += _sales_rental_exclusion_sql("s", enabled=exclude_rental)
    filters = ""
    if store_id:
        filters += _store_scope_filter_sql(has_counter_groups, has_stores)
        params["store_id"] = store_id
    if has_counter_groups:
        filters += _sales_department_exclusion_sql(
            "cg",
            enabled=exclude_backoffice_departments,
        )
    if unassigned_department and has_counter_groups:
        filters += _unassigned_department_filter_sql()
    elif department_code and has_counter_groups:
        filters += " AND upper(trim(COALESCE(cg.department_code, ''))) = upper(trim(:department_code))"
        params["department_code"] = department_code
    if group_code:
        filters += " AND upper(trim(COALESCE(s.sglmfid, ''))) = upper(trim(:group_code))"
        params["group_code"] = group_code
    if keyword:
        filters += (
            " AND (upper(trim(COALESCE(s.sglmfid, ''))) LIKE upper(:keyword_like)"
            + (" OR upper(trim(COALESCE(cg.group_name, ''))) LIKE upper(:keyword_like)" if has_counter_groups else "")
            + ")"
        )
        params["keyword_like"] = f"%{keyword.strip()}%"

    group_join = _counter_group_join_sql(has_counter_groups)
    scope_select = _group_scope_select_sql(has_counter_groups, has_stores=has_stores)

    if unrestricted:
        tail_sql = ""
    elif limit is None:
        params["inner_limit"] = 100000
        tail_sql = "ORDER BY effective_sales DESC LIMIT :inner_limit"
    else:
        params["limit"] = limit
        tail_sql = "ORDER BY effective_sales DESC LIMIT :limit"

    return _fetch_mappings(
        db,
        f"""
        WITH sales_agg AS (
          SELECT
            s.sglmarket,
            s.sglmfid,
            COUNT(DISTINCT s.sglbillno) AS ticket_count,
            COUNT(*) AS line_count,
            COALESCE(SUM(s.sglsl), 0) AS quantity,
            COALESCE(SUM(s.sglsjje), 0) AS priced_sales_amount,
            COALESCE(SUM(s.sglxssr), 0) AS gross_sales,
            COALESCE(SUM(s.sglxssr), 0) AS effective_sales,
            COALESCE(SUM(s.sgln2), 0) AS net_profit
          FROM {table_name} s
          WHERE 1=1 {date_filters}
          GROUP BY s.sglmarket, s.sglmfid
        )
        SELECT
          {scope_select},
          s.ticket_count,
          s.line_count,
          s.quantity,
          s.priced_sales_amount,
          s.gross_sales,
          s.effective_sales,
          s.net_profit,
          CASE
            WHEN s.effective_sales = 0 THEN 0
            ELSE s.net_profit / NULLIF(s.effective_sales, 0)
          END AS net_margin,
          CASE
            WHEN s.effective_sales = 0 THEN 0
            ELSE s.net_profit / NULLIF(s.effective_sales, 0)
          END AS ticket_margin
        FROM sales_agg s
        {group_join}
        {mkt_join}
        WHERE 1=1 {filters}
        {tail_sql}
        """,
        params,
    )


def _batch_store_display_names(db: Session, store_ids: list[str]) -> dict[str, str]:
    """将 ERP 市场号（store_code）或门店主键字符串解析为门店名称。"""
    out: dict[str, str] = {}
    if not store_ids:
        return out
    rows = _fetch_mappings(db, "SELECT store_id, store_code, store_name FROM stores", {})
    by_id = {str(r["store_id"]): str(r["store_name"]) for r in rows}
    by_code = {str(r["store_code"] or "").strip().upper(): str(r["store_name"]) for r in rows}
    for sid in store_ids:
        if sid in by_id:
            out[sid] = by_id[sid]
            continue
        k = sid.strip().upper()
        out[sid] = by_code.get(k, sid)
    return out


def _aggregate_stores_from_group_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for r in rows:
        sid_raw = r.get("store_id")
        sid = str(sid_raw).strip() if sid_raw is not None else ""
        key = sid or "__empty__"
        b = buckets.setdefault(
            key,
            {
                "store_id": sid,
                "department_keys": set(),
                "group_codes": set(),
                "ticket_count": 0.0,
                "quantity": 0.0,
                "gross_sales": 0.0,
                "effective_sales": 0.0,
                "net_profit": 0.0,
            },
        )
        dk = f"{r.get('department_code') or ''}|{r.get('department_name') or '未归属部门'}"
        b["department_keys"].add(dk)
        gc = str(r.get("group_code") or "").strip()
        if gc:
            b["group_codes"].add(gc)
        b["ticket_count"] += _num(r.get("ticket_count"))
        b["quantity"] += _num(r.get("quantity"))
        b["gross_sales"] += _num(r.get("gross_sales"))
        b["effective_sales"] += _num(r.get("effective_sales"))
        b["net_profit"] += _num(r.get("net_profit"))

    result: list[dict[str, Any]] = []
    for key, b in buckets.items():
        if key == "__empty__" and not b["store_id"]:
            continue
        eff = float(b["effective_sales"])
        net_margin = (float(b["net_profit"]) / eff) if eff else 0.0
        result.append(
            {
                "store_id": b["store_id"],
                "department_count": len(b["department_keys"]),
                "group_count": len(b["group_codes"]),
                "ticket_count": b["ticket_count"],
                "quantity": b["quantity"],
                "gross_sales": b["gross_sales"],
                "effective_sales": b["effective_sales"],
                "net_profit": b["net_profit"],
                "net_margin": net_margin,
                "ticket_margin": net_margin,
            }
        )
    return sorted(result, key=lambda x: float(x["effective_sales"]), reverse=True)


def _store_summary_rows_with_comparison(
    db: Session,
    *,
    scope: Any,
    start_date: str,
    end_date: str,
    prior_start_date: str,
    prior_end_date: str,
    limit: int,
    exclude_rental: bool = False,
    exclude_backoffice_departments: bool = False,
) -> list[dict[str, Any]]:
    """Aggregate current and prior store totals in one permission-scoped fact-table scan."""
    table_name = _salegoodslist_table(db)
    has_counter_groups = _table_exists(db, "manaframe")
    has_stores = _table_exists(db, "stores")
    group_join = _counter_group_join_sql(has_counter_groups)
    market_join = _stores_market_join_sql(has_stores)
    store_expr = _resolved_store_id_sql(
        has_counter_groups,
        has_stores=has_stores,
    )
    group_expr = "COALESCE(cg.group_code, s.sglmfid)" if has_counter_groups else "s.sglmfid"
    department_code_expr = "cg.department_code" if has_counter_groups else "NULL::varchar"
    department_name_expr = "cg.department_name" if has_counter_groups else "NULL::varchar"

    params: dict[str, Any] = {
        "current_start_date": start_date,
        "current_end_date": end_date,
        "prior_start_date": prior_start_date,
        "prior_end_date": prior_end_date,
        "limit": limit,
    }
    scope_filter = _business_scope_filter_sql(
        scope,
        params,
        prefix="store_summary",
        store_expr=store_expr,
        department_code_expr=department_code_expr if has_counter_groups else None,
        department_name_expr=department_name_expr if has_counter_groups else None,
        group_expr=group_expr,
    )
    current_period = (
        "s.sglhsrq >= CAST(:current_start_date AS DATE) "
        "AND s.sglhsrq <= CAST(:current_end_date AS DATE)"
    )
    prior_period = (
        "s.sglhsrq >= CAST(:prior_start_date AS DATE) "
        "AND s.sglhsrq <= CAST(:prior_end_date AS DATE)"
    )
    rental_filter = _sales_rental_exclusion_sql("s", enabled=exclude_rental)
    department_filter = (
        _sales_department_exclusion_sql(
            "cg",
            enabled=exclude_backoffice_departments,
        )
        if has_counter_groups
        else ""
    )

    return _fetch_mappings(
        db,
        f"""
        WITH group_period AS (
          SELECT
            {store_expr} AS store_id,
            {group_expr} AS group_code,
            {department_code_expr} AS department_code,
            {department_name_expr} AS department_name,
            COUNT(CASE WHEN {current_period} THEN 1 END) AS current_row_count,
            COUNT(DISTINCT CASE WHEN {current_period} THEN s.sglbillno END) AS current_ticket_count,
            COALESCE(SUM(CASE WHEN {current_period} THEN s.sglsl ELSE 0 END), 0) AS current_quantity,
            COALESCE(SUM(CASE WHEN {current_period} THEN s.sglxssr ELSE 0 END), 0) AS current_sales,
            COALESCE(SUM(CASE WHEN {current_period} THEN s.sgln2 ELSE 0 END), 0) AS current_profit,
            COUNT(CASE WHEN {prior_period} THEN 1 END) AS prior_row_count,
            COUNT(DISTINCT CASE WHEN {prior_period} THEN s.sglbillno END) AS prior_ticket_count,
            COALESCE(SUM(CASE WHEN {prior_period} THEN s.sglxssr ELSE 0 END), 0) AS prior_sales,
            COALESCE(SUM(CASE WHEN {prior_period} THEN s.sgln2 ELSE 0 END), 0) AS prior_profit
          FROM {table_name} s
          {group_join}
          {market_join}
          WHERE (({current_period}) OR ({prior_period}))
            {rental_filter}
            {department_filter}
            {scope_filter}
          GROUP BY 1, 2, 3, 4
        )
        SELECT
          store_id,
          COUNT(DISTINCT CASE
            WHEN current_row_count > 0
            THEN COALESCE(NULLIF(department_code, ''), '') || '|' ||
                 COALESCE(NULLIF(department_name, ''), '未归属部门')
          END) AS department_count,
          COUNT(DISTINCT CASE
            WHEN current_row_count > 0 THEN NULLIF(TRIM(BOTH FROM COALESCE(group_code, '')), '')
          END) AS group_count,
          COALESCE(SUM(current_ticket_count), 0) AS ticket_count,
          COALESCE(SUM(current_quantity), 0) AS quantity,
          COALESCE(SUM(current_sales), 0) AS gross_sales,
          COALESCE(SUM(current_sales), 0) AS effective_sales,
          COALESCE(SUM(current_profit), 0) AS net_profit,
          CASE
            WHEN COALESCE(SUM(current_sales), 0) = 0 THEN 0
            ELSE COALESCE(SUM(current_profit), 0) / NULLIF(SUM(current_sales), 0)
          END AS net_margin,
          CASE
            WHEN COALESCE(SUM(current_sales), 0) = 0 THEN 0
            ELSE COALESCE(SUM(current_profit), 0) / NULLIF(SUM(current_sales), 0)
          END AS ticket_margin,
          COALESCE(SUM(prior_sales), 0) AS same_period_effective_sales,
          COALESCE(SUM(prior_profit), 0) AS same_period_net_profit,
          COALESCE(SUM(prior_ticket_count), 0) AS same_period_ticket_count,
          CASE
            WHEN COALESCE(SUM(prior_sales), 0) = 0 THEN 0
            ELSE COALESCE(SUM(prior_profit), 0) / NULLIF(SUM(prior_sales), 0)
          END AS same_period_margin
        FROM group_period
        WHERE store_id IS NOT NULL AND TRIM(BOTH FROM store_id) <> ''
        GROUP BY store_id
        ORDER BY GREATEST(
          COALESCE(SUM(current_sales), 0),
          COALESCE(SUM(prior_sales), 0)
        ) DESC
        LIMIT :limit
        """,
        params,
    )


@router.get("/summary/latest-date")
def latest_sales_date(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "sales.view")
    return {"latest_date": _latest_sales_accounting_date(db)}


@router.get("/summary/stores")
def store_summary(
    start_date: str | None = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
    prior_start_date: str | None = Query(None, description="同期开始 YYYY-MM-DD；与 prior_end_date 同时传入时覆盖自动「上年同期」区间"),
    prior_end_date: str | None = Query(None, description="同期结束 YYYY-MM-DD"),
    exclude_rental: bool = False,
    exclude_backoffice_departments: bool = False,
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    按门店汇总销售：在柜组粒度先做数据范围过滤，再聚合为门店，与权限口径一致。
    """
    require_permission(db, current_user, "sales.view")
    _configure_sales_summary_timeout(db, start_date=start_date, end_date=end_date)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    if prior_start_date and prior_end_date:
        optimized_prior_start, optimized_prior_end = (
            prior_start_date.strip(),
            prior_end_date.strip(),
        )
    else:
        optimized_prior_start, optimized_prior_end = _prior_year_same_period(
            start_date,
            end_date,
        )
    if (
        start_date
        and end_date
        and optimized_prior_start
        and optimized_prior_end
    ):
        aggregated = _store_summary_rows_with_comparison(
            db,
            scope=scope,
            start_date=start_date.strip(),
            end_date=end_date.strip(),
            prior_start_date=optimized_prior_start,
            prior_end_date=optimized_prior_end,
            limit=limit,
            exclude_rental=exclude_rental,
            exclude_backoffice_departments=exclude_backoffice_departments,
        )
        if _table_exists(db, "stores"):
            names = _batch_store_display_names(
                db,
                [str(row["store_id"]) for row in aggregated if row.get("store_id")],
            )
            for row in aggregated:
                store_key = str(row.get("store_id") or "")
                row["store_name"] = names.get(store_key, store_key)
        else:
            for row in aggregated:
                row["store_name"] = str(row.get("store_id") or "")
        return aggregated

    raw = _group_level_sales_rows(
        db,
        start_date=start_date,
        end_date=end_date,
        store_id=None,
        department_code=None,
        unassigned_department=False,
        group_code=None,
        keyword=None,
        limit=None,
        unrestricted=True,
        exclude_rental=exclude_rental,
        exclude_backoffice_departments=exclude_backoffice_departments,
    )
    allowed = [r for r in raw if _row_allowed(scope, r)]
    aggregated = _aggregate_stores_from_group_rows(allowed)
    if prior_start_date and prior_end_date:
        py_start, py_end = prior_start_date.strip(), prior_end_date.strip()
    else:
        py_start, py_end = _prior_year_same_period(start_date, end_date)
    if py_start and py_end:
        prior_raw = _group_level_sales_rows(
            db,
            start_date=py_start,
            end_date=py_end,
            store_id=None,
            department_code=None,
            unassigned_department=False,
            group_code=None,
            keyword=None,
            limit=None,
            unrestricted=True,
            exclude_rental=exclude_rental,
            exclude_backoffice_departments=exclude_backoffice_departments,
        )
        prior_allowed = [r for r in prior_raw if _row_allowed(scope, r)]
        prior_agg = _aggregate_stores_from_group_rows(prior_allowed)
        aggregated = _merge_store_summaries_same_period(aggregated, prior_agg)
    else:
        for row in aggregated:
            row["same_period_effective_sales"] = 0.0
            row["same_period_net_profit"] = 0.0
            row["same_period_ticket_count"] = 0.0
            row["same_period_margin"] = 0.0
    if _table_exists(db, "stores"):
        names = _batch_store_display_names(db, [str(x["store_id"]) for x in aggregated if x.get("store_id")])
        for row in aggregated:
            sid = str(row.get("store_id") or "")
            row["store_name"] = names.get(sid, sid)
    else:
        for row in aggregated:
            row["store_name"] = str(row.get("store_id") or "")
    return aggregated[:limit]


@router.get("/summary/departments")
def department_summary(
    start_date: str | None = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
    prior_start_date: str | None = Query(None, description="同期开始 YYYY-MM-DD"),
    prior_end_date: str | None = Query(None, description="同期结束 YYYY-MM-DD"),
    store_id: str | None = Query(None, description="门店ID/市场号"),
    exclude_rental: bool = False,
    exclude_backoffice_departments: bool = False,
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "sales.view")
    _configure_sales_summary_timeout(db, start_date=start_date, end_date=end_date)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    table_name = _salegoodslist_table(db)
    has_counter_groups = _table_exists(db, "manaframe")
    has_stores = _table_exists(db, "stores")
    mkt_join = _stores_market_join_sql(has_stores)
    params: dict[str, Any] = {}
    filters = _date_filter_sql(params, start_date, end_date)
    filters += _sales_rental_exclusion_sql("s", enabled=exclude_rental)
    if store_id:
        filters += _store_scope_filter_sql(has_counter_groups, has_stores)
        params["store_id"] = store_id
    if has_counter_groups:
        filters += _sales_department_exclusion_sql(
            "cg",
            enabled=exclude_backoffice_departments,
        )

    group_join = _counter_group_join_sql(has_counter_groups)
    scope_select = _group_scope_select_sql(has_counter_groups, has_stores=has_stores)
    group_rows = _fetch_mappings(
        db,
        f"""
        SELECT
          {scope_select},
          COUNT(DISTINCT s.sglbillno) AS ticket_count,
          COALESCE(SUM(s.sglsl), 0) AS quantity,
          COALESCE(SUM(s.sglxssr), 0) AS gross_sales,
          COALESCE(SUM(s.sglxssr), 0) AS effective_sales,
          COALESCE(SUM(s.sgln2), 0) AS net_profit
        FROM {table_name} s
        {group_join}
        {mkt_join}
        WHERE 1=1 {filters}
        GROUP BY 1, 2, 3, 4, 5
        ORDER BY effective_sales DESC
        """,
        params,
    )
    current_list = _aggregate_group_rows_to_departments(group_rows, scope)
    if prior_start_date and prior_end_date:
        py_start, py_end = prior_start_date.strip(), prior_end_date.strip()
    else:
        py_start, py_end = _prior_year_same_period(start_date, end_date)
    if py_start and py_end:
        pparams: dict[str, Any] = {}
        pfilters = _date_filter_sql(pparams, py_start, py_end)
        pfilters += _sales_rental_exclusion_sql("s", enabled=exclude_rental)
        if store_id:
            pfilters += _store_scope_filter_sql(has_counter_groups, has_stores)
            pparams["store_id"] = store_id
        if has_counter_groups:
            pfilters += _sales_department_exclusion_sql(
                "cg",
                enabled=exclude_backoffice_departments,
            )
        prior_rows = _fetch_mappings(
            db,
            f"""
            SELECT
              {scope_select},
              COUNT(DISTINCT s.sglbillno) AS ticket_count,
              COALESCE(SUM(s.sglsl), 0) AS quantity,
              COALESCE(SUM(s.sglxssr), 0) AS gross_sales,
              COALESCE(SUM(s.sglxssr), 0) AS effective_sales,
              COALESCE(SUM(s.sgln2), 0) AS net_profit
            FROM {table_name} s
            {group_join}
            {mkt_join}
            WHERE 1=1 {pfilters}
            GROUP BY 1, 2, 3, 4, 5
            ORDER BY effective_sales DESC
            """,
            pparams,
        )
        prior_list = _aggregate_group_rows_to_departments(prior_rows, scope)
        merged = _merge_department_summaries_same_period(current_list, prior_list)
    else:
        merged = current_list
        for item in merged:
            item["same_period_effective_sales"] = 0.0
            item["same_period_net_profit"] = 0.0
            item["same_period_ticket_count"] = 0.0
            item["same_period_margin"] = 0.0
    return merged[:limit]


@router.get("/summary/groups")
def group_summary(
    start_date: str | None = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
    prior_start_date: str | None = Query(None, description="同期开始 YYYY-MM-DD"),
    prior_end_date: str | None = Query(None, description="同期结束 YYYY-MM-DD"),
    store_id: str | None = Query(None, description="门店ID/市场号"),
    department_code: str | None = Query(None, description="部门编码"),
    unassigned_department: bool = Query(False, description="仅未归属部门（无部门编码的聚合桶）"),
    group_code: str | None = Query(None, description="柜组编码"),
    keyword: str | None = Query(None, description="柜组编码/名称"),
    exclude_rental: bool = False,
    exclude_backoffice_departments: bool = False,
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "sales.view")
    _configure_sales_summary_timeout(db, start_date=start_date, end_date=end_date)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    rows = _group_level_sales_rows(
        db,
        start_date=start_date,
        end_date=end_date,
        store_id=store_id,
        department_code=department_code,
        unassigned_department=unassigned_department,
        group_code=group_code,
        keyword=keyword,
        # 先取完整本期，再按权限过滤、合并同期并截取；否则排行外的可见柜组
        # 会被同期合并误当成本期零销售（尤其是独立查询财务月同比时）。
        limit=None,
        exclude_rental=exclude_rental,
        exclude_backoffice_departments=exclude_backoffice_departments,
    )
    current = [_strip_scope(row) for row in rows if _row_allowed(scope, row)]
    if prior_start_date and prior_end_date:
        py_start, py_end = prior_start_date.strip(), prior_end_date.strip()
    else:
        py_start, py_end = _prior_year_same_period(start_date, end_date)
    if py_start and py_end:
        prior_rows = _group_level_sales_rows(
            db,
            start_date=py_start,
            end_date=py_end,
            store_id=store_id,
            department_code=department_code,
            unassigned_department=unassigned_department,
            group_code=group_code,
            keyword=keyword,
            limit=None,
            exclude_rental=exclude_rental,
            exclude_backoffice_departments=exclude_backoffice_departments,
        )
        prior_stripped = [_strip_scope(r) for r in prior_rows if _row_allowed(scope, r)]
        merged = _merge_group_summaries_same_period(current, prior_stripped)
        return merged[:limit]
    for row in current:
        row["same_period_ticket_count"] = 0.0
        row["same_period_effective_sales"] = 0.0
        row["same_period_net_profit"] = 0.0
        row["same_period_margin"] = 0.0
    return current[:limit]


@router.get("/summary/department-goods")
def department_goods_summary(
    start_date: str | None = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
    store_id: str | None = Query(None, description="门店ID/市场号"),
    department_code: str | None = Query(None, description="部门编码"),
    unassigned_department: bool = Query(False, description="仅未归属部门"),
    group_code: str | None = Query(None, description="柜组编码"),
    supplier_code: str | None = Query(None, description="供应商编码"),
    keyword: str | None = Query(None, description="商品/条码/柜组/供应商关键词"),
    exclude_rental: bool = False,
    exclude_backoffice_departments: bool = False,
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "sales.view")
    _configure_sales_summary_timeout(db, start_date=start_date, end_date=end_date)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    table_name = _salegoodslist_table(db)
    has_counter_groups = _table_exists(db, "manaframe")
    has_stores = _table_exists(db, "stores")
    has_goodsbase = _table_exists(db, "goodsbase")
    has_supplierbase = _table_exists(db, "supplierbase")
    has_goodscat = _table_exists(db, "goodscat")
    has_codebrand = _table_exists(db, "codebrand")
    has_sglgdname = _column_exists(db, table_name, "sglgdname")

    params: dict[str, Any] = {"limit": limit}
    filters = _date_filter_sql(params, start_date, end_date)
    filters += _department_detail_filter_sql(
        params,
        store_id=store_id,
        department_code=department_code,
        unassigned_department=unassigned_department,
        has_counter_groups=has_counter_groups,
        has_stores=has_stores,
        exclude_rental=exclude_rental,
        exclude_backoffice_departments=exclude_backoffice_departments,
    )
    if group_code:
        filters += " AND upper(trim(COALESCE(s.sglmfid, ''))) = upper(trim(:group_code))"
        params["group_code"] = group_code.strip()
    if supplier_code:
        filters += " AND upper(trim(COALESCE(s.sglsupid, ''))) = upper(trim(:supplier_code))"
        params["supplier_code"] = supplier_code.strip()
    if keyword:
        params["keyword_like"] = f"%{keyword.strip()}%"
        filters += (
            " AND (upper(trim(COALESCE(s.sglgdid, ''))) LIKE upper(:keyword_like) "
            "OR upper(trim(COALESCE(s.sglbarcode, ''))) LIKE upper(:keyword_like) "
            + ("OR upper(trim(COALESCE(s.sglgdname, ''))) LIKE upper(:keyword_like) " if has_sglgdname else "")
            + ("OR upper(trim(COALESCE(gb.gbcname, ''))) LIKE upper(:keyword_like) " if has_goodsbase else "")
            + ("OR upper(trim(COALESCE(cg.group_name, ''))) LIKE upper(:keyword_like) " if has_counter_groups else "")
            + ("OR upper(trim(COALESCE(sb.sbcname, ''))) LIKE upper(:keyword_like) " if has_supplierbase else "")
            + "OR upper(trim(COALESCE(s.sglsupid, ''))) LIKE upper(:keyword_like))"
        )

    group_join = _counter_group_join_sql(has_counter_groups)
    mkt_join = _stores_market_join_sql(has_stores)
    goods_join = (
        "LEFT JOIN goodsbase gb ON upper(trim(COALESCE(gb.gbid, ''))) = upper(trim(COALESCE(s.sglgdid, '')))"
        if has_goodsbase
        else ""
    )
    supplier_join = (
        "LEFT JOIN supplierbase sb ON upper(trim(COALESCE(sb.sbid, ''))) = upper(trim(COALESCE(s.sglsupid, '')))"
        if has_supplierbase
        else ""
    )
    category_join = (
        "LEFT JOIN goodscat gc ON upper(trim(COALESCE(gc.catcode, ''))) = upper(trim(COALESCE(s.sglcatid, '')))"
        if has_goodscat
        else ""
    )
    brand_join = (
        "LEFT JOIN codebrand cb ON upper(trim(COALESCE(cb.cbid, ''))) = upper(trim(COALESCE(s.sglppcode, '')))"
        if has_codebrand
        else ""
    )
    goods_name_expr = (
        "COALESCE(NULLIF(gb.gbcname, ''), NULLIF(s.sglgdname, ''), '')"
        if has_goodsbase and has_sglgdname
        else ("COALESCE(NULLIF(gb.gbcname, ''), '')" if has_goodsbase else ("COALESCE(NULLIF(s.sglgdname, ''), '')" if has_sglgdname else "''"))
    )
    group_code_expr = "COALESCE(cg.group_code, s.sglmfid)" if has_counter_groups else "s.sglmfid"
    supplier_name_expr = "COALESCE(NULLIF(sb.sbcname, ''), '')" if has_supplierbase else "''"
    category_name_expr = "COALESCE(NULLIF(gc.catcname, ''), '')" if has_goodscat else "''"
    brand_name_expr = "COALESCE(NULLIF(cb.cbcname, ''), '')" if has_codebrand else "''"
    group_name_expr = "cg.group_name" if has_counter_groups else "NULL"
    department_code_expr = "cg.department_code" if has_counter_groups else "NULL"
    department_name_expr = "cg.department_name" if has_counter_groups else "NULL"
    store_key = (
        "COALESCE((st_mkt.store_id)::varchar, (cg.store_id)::varchar, s.sglmarket::varchar)"
        if has_counter_groups and has_stores
        else ("COALESCE((cg.store_id)::varchar, s.sglmarket::varchar)" if has_counter_groups else "s.sglmarket::varchar")
    )
    scope_filter = _business_scope_filter_sql(
        scope,
        params,
        prefix="dept_goods",
        store_expr=store_key,
        department_code_expr=department_code_expr,
        department_name_expr=department_name_expr,
        group_expr=group_code_expr,
        supplier_expr="s.sglsupid",
    )

    rows = _fetch_mappings(
        db,
        f"""
        SELECT
          {group_code_expr} AS group_code,
          {group_name_expr} AS group_name,
          s.sglgdid AS goods_code,
          s.sglbarcode AS barcode,
          {goods_name_expr} AS goods_name,
          s.sglcatid AS category_code,
          {category_name_expr} AS category_name,
          s.sglppcode AS brand_code,
          {brand_name_expr} AS brand_name,
          s.sglsupid AS supplier_code,
          {supplier_name_expr} AS supplier_name,
          s.sglwmid AS operation_method_code,
          {_operation_method_label_sql("s")} AS operation_method,
          COUNT(DISTINCT s.sglbillno) AS ticket_count,
          COALESCE(SUM(s.sglsl), 0) AS sales_qty,
          COALESCE(SUM(s.sglsjje), 0) AS sales_amount,
          COALESCE(SUM(s.sglxssr), 0) AS sales_revenue,
          COALESCE(SUM(s.sgln13), 0) AS sales_cost,
          COALESCE(SUM(s.sgln14), 0) AS sales_cost_adjustment,
          COALESCE(SUM(s.sglsupzk), 0) AS supplier_discount,
          COALESCE(SUM(s.sgln2), 0) AS gross_profit,
          CASE
            WHEN COALESCE(SUM(s.sglxssr), 0) = 0 THEN 0
            ELSE COALESCE(SUM(s.sgln2), 0) / NULLIF(COALESCE(SUM(s.sglxssr), 0), 0)
          END AS gross_margin_rate,
          {store_key} AS store_id,
          {department_code_expr} AS department_code,
          {department_name_expr} AS department_name
        FROM {table_name} s
        {group_join}
        {mkt_join}
        {goods_join}
        {supplier_join}
        {category_join}
        {brand_join}
        WHERE 1=1 {filters} {scope_filter}
        GROUP BY
          {group_code_expr},
          {group_name_expr},
          s.sglgdid,
          s.sglbarcode,
          {goods_name_expr},
          s.sglcatid,
          {category_name_expr},
          s.sglppcode,
          {brand_name_expr},
          s.sglsupid,
          {supplier_name_expr},
          s.sglwmid,
          {_operation_method_label_sql("s")},
          {store_key},
          {department_code_expr},
          {department_name_expr}
        ORDER BY sales_revenue DESC, gross_profit DESC
        LIMIT :limit
        """,
        params,
    )
    return [_strip_scope(row) for row in rows]


@router.get("/summary/department-suppliers")
def department_supplier_summary(
    start_date: str | None = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
    store_id: str | None = Query(None, description="门店ID/市场号"),
    department_code: str | None = Query(None, description="部门编码"),
    unassigned_department: bool = Query(False, description="仅未归属部门"),
    keyword: str | None = Query(None, description="供应商编码/名称关键词"),
    exclude_rental: bool = False,
    exclude_backoffice_departments: bool = False,
    limit: int = Query(300, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "sales.view")
    _configure_sales_summary_timeout(db, start_date=start_date, end_date=end_date)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    table_name = _salegoodslist_table(db)
    has_counter_groups = _table_exists(db, "manaframe")
    has_stores = _table_exists(db, "stores")
    has_supplierbase = _table_exists(db, "supplierbase")

    params: dict[str, Any] = {"limit": limit}
    filters = _date_filter_sql(params, start_date, end_date)
    filters += _department_detail_filter_sql(
        params,
        store_id=store_id,
        department_code=department_code,
        unassigned_department=unassigned_department,
        has_counter_groups=has_counter_groups,
        has_stores=has_stores,
        exclude_rental=exclude_rental,
        exclude_backoffice_departments=exclude_backoffice_departments,
    )
    if keyword:
        params["keyword_like"] = f"%{keyword.strip()}%"
        filters += (
            " AND (upper(trim(COALESCE(s.sglsupid, ''))) LIKE upper(:keyword_like) "
            + ("OR upper(trim(COALESCE(sb.sbcname, ''))) LIKE upper(:keyword_like)" if has_supplierbase else "")
            + ")"
        )

    group_join = _counter_group_join_sql(has_counter_groups)
    mkt_join = _stores_market_join_sql(has_stores)
    supplier_join = (
        "LEFT JOIN supplierbase sb ON upper(trim(COALESCE(sb.sbid, ''))) = upper(trim(COALESCE(s.sglsupid, '')))"
        if has_supplierbase
        else ""
    )
    group_code_expr = "COALESCE(cg.group_code, s.sglmfid)" if has_counter_groups else "s.sglmfid"
    supplier_name_expr = "COALESCE(NULLIF(sb.sbcname, ''), '')" if has_supplierbase else "''"
    department_code_expr = "cg.department_code" if has_counter_groups else "NULL"
    department_name_expr = "cg.department_name" if has_counter_groups else "NULL"
    store_key = (
        "COALESCE((st_mkt.store_id)::varchar, (cg.store_id)::varchar, s.sglmarket::varchar)"
        if has_counter_groups and has_stores
        else ("COALESCE((cg.store_id)::varchar, s.sglmarket::varchar)" if has_counter_groups else "s.sglmarket::varchar")
    )
    scope_filter = _business_scope_filter_sql(
        scope,
        params,
        prefix="dept_suppliers",
        store_expr=store_key,
        department_code_expr=department_code_expr,
        department_name_expr=department_name_expr,
        group_expr=group_code_expr,
        supplier_expr="s.sglsupid",
    )

    rows = _fetch_mappings(
        db,
        f"""
        SELECT
          s.sglsupid AS supplier_code,
          {supplier_name_expr} AS supplier_name,
          COUNT(DISTINCT {group_code_expr}) AS group_count,
          COUNT(DISTINCT s.sglgdid) AS goods_count,
          COUNT(DISTINCT s.sglbillno) AS ticket_count,
          COALESCE(SUM(s.sglsl), 0) AS sales_qty,
          COALESCE(SUM(s.sglsjje), 0) AS sales_amount,
          COALESCE(SUM(s.sglxssr), 0) AS sales_revenue,
          COALESCE(SUM(s.sgln13), 0) AS sales_cost,
          COALESCE(SUM(s.sgln14), 0) AS sales_cost_adjustment,
          COALESCE(SUM(s.sglsupzk), 0) AS supplier_discount,
          COALESCE(SUM(s.sgln2), 0) AS gross_profit,
          CASE
            WHEN COALESCE(SUM(s.sglxssr), 0) = 0 THEN 0
            ELSE COALESCE(SUM(s.sgln2), 0) / NULLIF(COALESCE(SUM(s.sglxssr), 0), 0)
          END AS gross_margin_rate,
          {store_key} AS store_id,
          {department_code_expr} AS department_code,
          {department_name_expr} AS department_name
        FROM {table_name} s
        {group_join}
        {mkt_join}
        {supplier_join}
        WHERE 1=1 {filters} {scope_filter}
        GROUP BY
          s.sglsupid,
          {supplier_name_expr},
          {store_key},
          {department_code_expr},
          {department_name_expr}
        ORDER BY sales_revenue DESC, gross_profit DESC
        LIMIT :limit
        """,
        params,
    )
    return [_strip_scope(row) for row in rows]


@router.post("/analysis")
async def sales_analysis(
    request: SalesAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    销售规则分析。

    第一版仅支持柜组汇总分析：后端按当前用户权限和筛选条件拉取柜组数据，
    先跑规则库，再可选调用 AI 生成经营分析文案。
    """
    if request.level != "groups":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="第一版销售分析仅支持 level=groups",
        )

    require_permission(db, current_user, "sales.view")
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")

    rows = _group_level_sales_rows(
        db,
        start_date=request.start_date,
        end_date=request.end_date,
        store_id=request.store_id,
        department_code=request.department_code,
        unassigned_department=request.unassigned_department,
        group_code=request.group_code,
        keyword=request.keyword,
        limit=request.limit,
        exclude_rental=request.exclude_rental,
        exclude_backoffice_departments=request.exclude_backoffice_departments,
    )
    current = [_strip_scope(dict(row)) for row in rows if _row_allowed(scope, row)]

    if request.prior_start_date and request.prior_end_date:
        py_start, py_end = request.prior_start_date.strip(), request.prior_end_date.strip()
    else:
        py_start, py_end = _prior_year_same_period(request.start_date, request.end_date)

    if py_start and py_end:
        prior_rows = _group_level_sales_rows(
            db,
            start_date=py_start,
            end_date=py_end,
            store_id=request.store_id,
            department_code=request.department_code,
            unassigned_department=request.unassigned_department,
            group_code=request.group_code,
            keyword=request.keyword,
            limit=None,
            exclude_rental=request.exclude_rental,
            exclude_backoffice_departments=request.exclude_backoffice_departments,
        )
        prior_stripped = [_strip_scope(dict(row)) for row in prior_rows if _row_allowed(scope, row)]
        merged = _merge_group_summaries_same_period(current, prior_stripped)[: request.limit]
    else:
        merged = current
        for row in merged:
            row["same_period_ticket_count"] = 0.0
            row["same_period_effective_sales"] = 0.0
            row["same_period_net_profit"] = 0.0
            row["same_period_margin"] = 0.0

    return analyze_group_sales(
        merged,
        scope={
            "level": request.level,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "prior_start_date": py_start,
            "prior_end_date": py_end,
            "store_id": request.store_id,
            "department_code": request.department_code,
            "unassigned_department": request.unassigned_department,
            "group_code": request.group_code,
            "keyword": request.keyword,
            "exclude_rental": request.exclude_rental,
            "exclude_backoffice_departments": request.exclude_backoffice_departments,
            "limit": request.limit,
        },
        include_ai=request.include_ai,
    )


@router.get("/map/groups")
def map_group_summary(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    store_id: str | None = Query(None),
    department_code: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return group_summary(
        start_date=start_date,
        end_date=end_date,
        store_id=store_id,
        department_code=department_code,
        prior_start_date=None,
        prior_end_date=None,
        unassigned_department=False,
        group_code=None,
        keyword=None,
        exclude_rental=False,
        exclude_backoffice_departments=False,
        limit=1000,
        db=db,
        current_user=current_user,
    )


@router.get("/groups/{group_code}/tickets/summary")
def group_tickets_summary(
    group_code: str,
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    goods_code: str | None = Query(None, description="商品编码"),
    barcode: str | None = Query(None, description="商品条码"),
    supplier_code: str | None = Query(None, description="供应商编码"),
    exclude_rental: bool = False,
    exclude_backoffice_departments: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回当前筛选范围内的全部小票数量和金额汇总，不受列表分页影响。"""
    require_permission(db, current_user, "sales.view")
    _configure_sales_summary_timeout(db, start_date=start_date, end_date=end_date)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    table_name = _salegoodslist_table(db)
    has_counter_groups = _table_exists(db, "manaframe")
    has_stores = _table_exists(db, "stores")
    params: dict[str, Any] = {"group_code": group_code}
    filters = _date_filter_sql(params, start_date, end_date)
    filters += _sales_rental_exclusion_sql("s", enabled=exclude_rental)
    filters += _ticket_product_filter_sql(
        params,
        goods_code=goods_code,
        barcode=barcode,
        supplier_code=supplier_code,
    )
    if has_counter_groups:
        filters += _sales_department_exclusion_sql(
            "cg",
            enabled=exclude_backoffice_departments,
        )
    group_join = _counter_group_join_sql(has_counter_groups)
    mkt_join = _stores_market_join_sql(has_stores)
    scope_select = _group_scope_select_sql(has_counter_groups, has_stores=has_stores)
    rows = _fetch_mappings(
        db,
        f"""
        WITH base AS (
          SELECT
            {scope_select},
            s.sglbillno AS billno,
            s.sglsjje,
            s.sglxssr,
            s.sgln2
          FROM {table_name} s
          {group_join}
          {mkt_join}
          WHERE upper(trim(COALESCE(s.sglmfid, ''))) = upper(trim(:group_code)) {filters}
        ),
        ticket_rows AS (
          SELECT
            MAX(group_code) AS group_code,
            MAX(group_name) AS group_name,
            MAX(department_code) AS department_code,
            MAX(department_name) AS department_name,
            MAX(store_id) AS store_id,
            billno,
            COALESCE(SUM(sglsjje), 0) AS priced_sales_amount,
            COALESCE(SUM(sglxssr), 0) AS effective_sales,
            COALESCE(SUM(sgln2), 0) AS net_profit
          FROM base
          GROUP BY billno
        )
        SELECT
          MAX(group_code) AS group_code,
          MAX(group_name) AS group_name,
          MAX(department_code) AS department_code,
          MAX(department_name) AS department_name,
          MAX(store_id) AS store_id,
          COUNT(*) AS ticket_count,
          COALESCE(SUM(priced_sales_amount), 0) AS priced_sales_amount,
          COALESCE(SUM(effective_sales), 0) AS effective_sales,
          COALESCE(SUM(net_profit), 0) AS net_profit
        FROM ticket_rows
        """,
        params,
    )
    if not rows or not rows[0].get("ticket_count"):
        return {
            "ticket_count": 0,
            "priced_sales_amount": 0,
            "effective_sales": 0,
            "net_profit": 0,
        }
    row = rows[0]
    if not _row_allowed(scope, row):
        return {
            "ticket_count": 0,
            "priced_sales_amount": 0,
            "effective_sales": 0,
            "net_profit": 0,
        }
    return _strip_scope(row)


@router.get("/groups/{group_code}/tickets")
def group_tickets(
    group_code: str,
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    goods_code: str | None = Query(None, description="商品编码"),
    barcode: str | None = Query(None, description="商品条码"),
    supplier_code: str | None = Query(None, description="供应商编码"),
    exclude_rental: bool = False,
    exclude_backoffice_departments: bool = False,
    limit: int = Query(TICKET_PAGE_SIZE, ge=1, le=TICKET_EXPORT_FETCH_LIMIT),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    按小票汇总 salegoodslist 行：零售价=sum(sglsjje)，销售收入=sum(sglxssr)，
    毛利=sum(sgln2)，小票毛利率=sum(sgln2)/sum(sglxssr)；
    授权折扣=sum(sglgrantzk)，面值卡(MZK)=sum(sglfcard)。
    礼券(LQ)=sum(salepay.je where paycode='0500')；salehead.djlb=4 时按负数返回。
    收银机号取 salegoodslist.sglsyjid。
    交易时间优先取 salehead.rqsj，缺失时回退 salegoodslist.sglsaledate。
    附带：order_point 中消费加积分与生日月会员加积分。

    salehead 若存在 djlx 优先否则 djlb：1→销售，4→退货，其余返回原始码。

    若表为 ods_salegoodslist 且列缺失，需保证与线表结构一致。
    """
    require_permission(db, current_user, "sales.view")
    _configure_sales_summary_timeout(db, start_date=start_date, end_date=end_date)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    table_name = _salegoodslist_table(db)
    has_counter_groups = _table_exists(db, "manaframe")
    has_stores = _table_exists(db, "stores")
    mkt_join = _stores_market_join_sql(has_stores)
    params: dict[str, Any] = {"group_code": group_code, "limit": limit, "offset": offset}
    filters = _date_filter_sql(params, start_date, end_date)
    filters += _sales_rental_exclusion_sql("s", enabled=exclude_rental)
    filters += _ticket_product_filter_sql(
        params,
        goods_code=goods_code,
        barcode=barcode,
        supplier_code=supplier_code,
    )
    if has_counter_groups:
        filters += _sales_department_exclusion_sql(
            "cg",
            enabled=exclude_backoffice_departments,
        )
    group_join = _counter_group_join_sql(has_counter_groups)
    scope_select = _group_scope_select_sql(has_counter_groups, has_stores=has_stores)
    has_salehead = _table_exists(db, "salehead")
    has_salepay = _table_exists(db, "salepay")
    has_order_point = _table_exists(db, "order_point")
    has_salehead_djlb = has_salehead and _column_exists(db, "salehead", "djlb")
    has_salehead_rqsj = has_salehead and _column_exists(db, "salehead", "rqsj")
    dj_kind_col = (
        "djlx"
        if has_salehead and _column_exists(db, "salehead", "djlx")
        else "djlb"
        if has_salehead and _column_exists(db, "salehead", "djlb")
        else None
    )
    head_join = ""
    if has_salehead and (dj_kind_col or has_salehead_djlb or has_salehead_rqsj):
        head_join = """
        LEFT JOIN salehead sh ON sh.billno = tr.billno
        """
    sale_datetime_expr = (
        "COALESCE(sh.rqsj, tr.sale_datetime) AS sale_datetime"
        if has_salehead_rqsj
        else "tr.sale_datetime"
    )
    if has_salepay:
        lq_pay_join = """
        , lq_pay AS (
          SELECT
            p.billno AS billno,
            COALESCE(SUM(COALESCE(p.je, 0)), 0) AS lq_amount
          FROM salepay p
          WHERE TRIM(BOTH FROM COALESCE(p.paycode::text, '')) = '0500'
            AND p.billno IN (SELECT billno FROM ticket_rows)
          GROUP BY p.billno
        )
        """
        lq_final_join = "LEFT JOIN lq_pay lp ON lp.billno = tr.billno"
        if has_salehead_djlb:
            lq_expr = """
              CASE
                WHEN TRIM(BOTH FROM COALESCE(sh.djlb::text, '')) = '4'
                  THEN -ABS(COALESCE(lp.lq_amount, 0))
                ELSE COALESCE(lp.lq_amount, 0)
              END AS lq
            """
        else:
            lq_expr = "COALESCE(lp.lq_amount, 0) AS lq"
    else:
        lq_pay_join = ""
        lq_final_join = ""
        lq_expr = "0 AS lq"
    point_join = ""
    if has_order_point:
        has_point_remark = _column_exists(db, "order_point", "remark")
        has_point_type = _column_exists(db, "order_point", "point_type")
        point_category_expr = "''"
        if has_point_remark and has_point_type:
            point_category_expr = """
              COALESCE(
                NULLIF(TRIM(BOTH FROM remark::text), ''),
                NULLIF(TRIM(BOTH FROM point_type::text), ''),
                ''
              )
            """
        elif has_point_remark:
            point_category_expr = "TRIM(BOTH FROM COALESCE(remark::text, ''))"
        elif has_point_type:
            point_category_expr = "TRIM(BOTH FROM COALESCE(point_type::text, ''))"
        consumption_point_condition = (
            f"{point_category_expr} IN ('消费加积分', '消费获得积分', '香奈儿活动补发')"
        )
        point_join = f"""
        , op_agg AS (
          SELECT
            order_id AS order_id,
            COALESCE(SUM(point), 0) AS point,
            COALESCE(SUM(CASE WHEN {consumption_point_condition} THEN point ELSE 0 END), 0) AS consumption_point,
            COALESCE(SUM(CASE WHEN {point_category_expr} LIKE '生日月%' THEN point ELSE 0 END), 0) AS birthday_month_member_point
          FROM order_point
          WHERE order_id IN (SELECT billno::text FROM ticket_rows)
          GROUP BY order_id
        )
        """
        point_expr = "COALESCE(op.point, 0) AS point"
        consumption_point_expr = "COALESCE(op.consumption_point, 0) AS consumption_point"
        birthday_month_member_point_expr = "COALESCE(op.birthday_month_member_point, 0) AS birthday_month_member_point"
        point_final_join = "LEFT JOIN op_agg op ON op.order_id = tr.billno::text"
    else:
        point_join = ""
        point_expr = "0 AS point"
        consumption_point_expr = "0 AS consumption_point"
        birthday_month_member_point_expr = "0 AS birthday_month_member_point"
        point_final_join = ""
    if has_salehead and dj_kind_col:
        txn_expr = f"""
          CASE TRIM(BOTH FROM COALESCE(sh.{dj_kind_col}::text, ''))
            WHEN '1' THEN '销售'
            WHEN '4' THEN '退货'
            ELSE NULLIF(TRIM(BOTH FROM COALESCE(sh.{dj_kind_col}::text, '')), '')
          END AS transaction_type
        """
    else:
        txn_expr = "NULL::varchar AS transaction_type"

    rows = _fetch_mappings(
        db,
        f"""
        WITH base AS (
          SELECT
            {scope_select},
            s.sglbillno AS billno,
            s.sgldate AS sale_date,
            s.sglsaledate AS sale_datetime,
            s.sglsyjid AS cash_register_no,
            s.sglinvno AS invoice_no,
            s.sglsl,
            s.sglsjje,
            s.sglxssr,
            s.sgln2,
            s.sglgrantzk,
            s.sglfcard
          FROM {table_name} s
          {group_join}
          {mkt_join}
          WHERE upper(trim(COALESCE(s.sglmfid, ''))) = upper(trim(:group_code)) {filters}
        ),
        ticket_rows AS (
          SELECT
            MAX(group_code) AS group_code,
            MAX(group_name) AS group_name,
            MAX(department_code) AS department_code,
            MAX(department_name) AS department_name,
            MAX(store_id) AS store_id,
            billno,
            MIN(sale_date) AS sale_date,
            MIN(sale_datetime) AS sale_datetime,
            MIN(cash_register_no) AS cash_register_no,
            MIN(invoice_no) AS invoice_no,
            COUNT(*) AS line_count,
            COALESCE(SUM(sglsl), 0) AS quantity,
            COALESCE(SUM(sglsjje), 0) AS priced_sales_amount,
            COALESCE(SUM(sglxssr), 0) AS effective_sales,
            COALESCE(SUM(sgln2), 0) AS net_profit,
            CASE
              WHEN COALESCE(SUM(sglxssr), 0) = 0 THEN 0
              ELSE COALESCE(SUM(sgln2), 0) / NULLIF(COALESCE(SUM(sglxssr), 0), 0)
            END AS ticket_margin,
            COALESCE(SUM(sglgrantzk), 0) AS authorized_discount,
            COALESCE(SUM(sglfcard), 0) AS mzk
          FROM base
          GROUP BY billno
          ORDER BY sale_date DESC, billno DESC
          LIMIT :limit OFFSET :offset
        )
        {lq_pay_join}
        {point_join}
        SELECT
          tr.group_code,
          tr.group_name,
          tr.department_code,
          tr.department_name,
          tr.store_id,
          TRIM(BOTH FROM tr.billno::text) AS billno,
          tr.sale_date,
          {sale_datetime_expr},
          tr.cash_register_no,
          tr.invoice_no,
          tr.line_count,
          tr.quantity,
          tr.priced_sales_amount,
          tr.effective_sales,
          tr.net_profit,
          tr.ticket_margin,
          tr.authorized_discount,
          tr.mzk,
          {lq_expr},
          {point_expr},
          {consumption_point_expr},
          {birthday_month_member_point_expr},
          {txn_expr}
        FROM ticket_rows tr
        {head_join}
        {lq_final_join}
        {point_final_join}
        ORDER BY tr.sale_date DESC, tr.billno DESC
        """,
        params,
    )
    return [_strip_scope(row) for row in rows if _row_allowed(scope, row)]


@router.get("/tickets/{billno}")
def ticket_detail(
    billno: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "sales.view")
    normalized_billno = billno.strip()
    if (
        not normalized_billno
        or not normalized_billno.isascii()
        or not normalized_billno.isdigit()
        or len(normalized_billno) > 18
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="小票号格式无效")
    billno_value = Decimal(normalized_billno)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    has_salehead = _table_exists(db, "salehead")
    has_salegoods = _table_exists(db, "salegoods")
    has_salepay = _table_exists(db, "salepay")
    has_paymode = _table_exists(db, "paymode")
    has_counter_groups = _table_exists(db, "manaframe")
    has_stores = _table_exists(db, "stores")
    has_goodsbase = _table_exists(db, "goodsbase")

    if has_salehead and has_salegoods:
        goods_scope_join = (
            f"LEFT JOIN {_manaframe_group_source_sql('cg')} ON upper(trim(COALESCE(g.gz, ''))) = upper(trim(COALESCE(cg.group_code, '')))"
            if has_counter_groups
            else ""
        )
        goods_store_join = (
            "LEFT JOIN stores st_mkt ON TRIM(BOTH FROM COALESCE(st_mkt.store_code, '')) = "
            "TRIM(BOTH FROM COALESCE(g.mkt::varchar, ''))"
            if has_stores
            else ""
        )
        if has_counter_groups and has_stores:
            pos_store_expr = "COALESCE((st_mkt.store_id)::varchar, (cg.store_id)::varchar, g.mkt::varchar)"
        elif has_counter_groups:
            pos_store_expr = "COALESCE((cg.store_id)::varchar, g.mkt::varchar)"
        elif has_stores:
            pos_store_expr = "COALESCE((st_mkt.store_id)::varchar, g.mkt::varchar)"
        else:
            pos_store_expr = "g.mkt::varchar"
        goodsbase_join = (
            """
            LEFT JOIN LATERAL (
              SELECT gb.gbcname
              FROM goodsbase gb
              WHERE upper(trim(COALESCE(gb.gbid, ''))) = upper(trim(COALESCE(g.code, '')))
                 OR upper(trim(COALESCE(gb.gbbarcode, ''))) = upper(trim(COALESCE(g.barcode, '')))
              ORDER BY CASE
                WHEN upper(trim(COALESCE(gb.gbid, ''))) = upper(trim(COALESCE(g.code, ''))) THEN 0
                ELSE 1
              END
              LIMIT 1
            ) gb ON TRUE
            """
            if has_goodsbase
            else ""
        )
        pos_goods_name_expr = (
            "COALESCE(NULLIF(g.name, ''), NULLIF(gb.gbcname, ''), g.name)"
            if has_goodsbase
            else "g.name"
        )
        scope_rows = _fetch_mappings(
            db,
            f"""
            SELECT
              COALESCE(g.gz, '') AS group_code,
              {("cg.group_name, cg.department_code, cg.department_name" if has_counter_groups else "NULL::varchar AS group_name, NULL::varchar AS department_code, NULL::varchar AS department_name")},
              {pos_store_expr} AS store_id
            FROM salegoods g
            {goods_scope_join}
            {goods_store_join}
            WHERE g.billno = :billno
            {(_sales_department_exclusion_sql("cg") if has_counter_groups else "")}
            GROUP BY 1, 2, 3, 4, 5
            """,
            {"billno": billno_value},
        )
        if scope_rows and not any(_row_allowed(scope, row) for row in scope_rows):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无该小票数据权限")

        head = _fetch_mappings(
            db,
            """
            SELECT
              billno, mkt, syjh, fphm, djlb, bc, rqsj, syyh, hykh,
              ysje, sjfk, zl, hjzje, hjzsl, hjzke, hyzke, yhzke, lszke,
              status, custtype, hhflag, ybillno, ysyjh, yfphm, channel,
              sendrqsj, sswr_sysy, fk_sysy, str2, str3
            FROM salehead
            WHERE billno = :billno
            LIMIT 1
            """,
            {"billno": billno_value},
        )
        goods = _fetch_mappings(
            db,
            f"""
            SELECT
              g.rowno, g.mkt, g.yyyh, g.barcode, g.code, g.sptype, g.gz AS group_code,
              g.catid, g.ppcode, {pos_goods_name_expr} AS name, g.unit, g.sl, g.lsj, g.jg, g.hjje, g.hjzk,
              g.hyzke, g.yhzke, g.lszke, g.flag, g.rqsj
            FROM salegoods g
            {goodsbase_join}
            WHERE g.billno = :billno
            ORDER BY g.rowno
            """,
            {"billno": billno_value},
        )
        if has_salepay:
            paymode_join = (
                "LEFT JOIN paymode pm ON upper(trim(COALESCE(pm.pmcode, ''))) = upper(trim(COALESCE(p.paycode, '')))"
                if has_paymode
                else ""
            )
            payname_expr = (
                "COALESCE(NULLIF(pm.pmname, ''), NULLIF(p.payname, ''), p.payname)"
                if has_paymode
                else "p.payname"
            )
            pays = _fetch_mappings(
                db,
                f"""
                SELECT
                  p.rowno, p.paycode, {payname_expr} AS payname, p.flag, p.ybje, p.hl, p.je,
                  p.payno, p.paytype, p.paymemo, p.rqsj
                FROM salepay p
                {paymode_join}
                WHERE p.billno = :billno
                ORDER BY p.rowno
                """,
                {"billno": billno_value},
            )
        else:
            pays = []
        return {"source": "pos", "head": head[0] if head else None, "goods": goods, "payments": pays}

    table_name = _salegoodslist_table(db)
    has_counter_groups = _table_exists(db, "manaframe")
    has_stores = _table_exists(db, "stores")
    mkt_join = _stores_market_join_sql(has_stores)
    goods_name_expr = "s.sglgdname" if _column_exists(db, table_name, "sglgdname") else "NULL::varchar"
    sales_amount = _sales_amount_sql("s")
    cost_amount = _cost_amount_sql("s")
    group_join = _counter_group_join_sql(has_counter_groups)
    scope_select = _group_scope_select_sql(has_counter_groups, has_stores=has_stores)
    rows = _fetch_mappings(
        db,
        f"""
        SELECT
          {scope_select},
          s.sglbillno AS billno,
          s.sglrowno AS rowno,
          s.sgldate AS sale_date,
          s.sglsaledate AS sale_datetime,
          s.sglinvno AS invoice_no,
          s.sglchecker AS cashier,
          s.sglgdid AS goods_code,
          s.sglbarcode AS barcode,
          {goods_name_expr} AS goods_name,
          s.sglsl AS quantity,
          s.sglsj AS unit_price,
          {sales_amount} AS effective_sales,
          {cost_amount} AS cost_amount,
          s.sglnetml AS net_profit
        FROM {table_name} s
        {group_join}
        {mkt_join}
        WHERE s.sglbillno = :billno
        {(_sales_department_exclusion_sql("cg") if has_counter_groups else "")}
        ORDER BY s.sglrowno
        """,
        {"billno": billno_value},
    )
    allowed_rows = [_strip_scope(row) for row in rows if _row_allowed(scope, row)]
    if rows and not allowed_rows:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无该小票数据权限")
    return {"source": table_name, "head": None, "goods": allowed_rows, "payments": []}
