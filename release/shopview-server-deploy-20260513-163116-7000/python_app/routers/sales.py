"""
销售查询 API

汇总口径优先使用 salegoodslist，缺失时回退 ods_salegoodslist。
小票详情优先使用 salehead + salegoods + salepay，缺失时回退 salegoodslist 行明细。
"""

from datetime import date
from decimal import Decimal
from typing import Any, Iterable

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from models.database import get_db
from models.models import User
from routers.auth import get_current_user
from routers.authz import load_business_scope, require_permission, scope_allows_business
from services.sales_analysis import analyze_group_sales


router = APIRouter(prefix="/api/sales", tags=["sales"])


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
    limit: int = Field(200, ge=1, le=1000, description="最大分析柜组数")
    include_ai: bool = Field(True, description="是否生成 AI 经营分析文案")


class ReportDepartmentOption(BaseModel):
    department_code: str
    department_name: str
    label: str


SALES_EXCLUDED_DEPARTMENT_NAMES = (
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
    "半山租赁部",
    "华山租赁部",
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


def _sales_department_exclusion_sql(alias: str = "cg") -> str:
    names = _sql_string_list(SALES_EXCLUDED_DEPARTMENT_NAMES)
    return f" AND TRIM(BOTH FROM COALESCE({alias}.department_name, '')) NOT IN ({names})"


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
        ON upper(trim(COALESCE(mf.mfpcode, ''))) = upper(trim(COALESCE(dept.mfcode, '')))
    ) {alias}
    """


def _counter_group_join_sql(enabled: bool, *, sales_alias: str = "s") -> str:
    if not enabled:
        return ""
    return (
        f"LEFT JOIN {_manaframe_group_source_sql('cg')} "
        f"ON upper(trim(COALESCE({sales_alias}.sglmfid, ''))) = upper(trim(COALESCE(cg.group_code, '')))"
    )


def _stores_market_join_sql(has_stores: bool) -> str:
    """将 ERP 市场号 sglmarket 对齐到 stores.store_code，与柜组 store_id 统一到同一门店主键，避免「4」与「604」拆成两行。"""
    if not has_stores:
        return ""
    return (
        "LEFT JOIN stores st_mkt ON TRIM(BOTH FROM COALESCE(st_mkt.store_code, '')) = "
        "TRIM(BOTH FROM COALESCE(s.sglmarket::varchar, ''))"
    )


def _group_scope_select_sql(enabled: bool, *, has_stores: bool = False) -> str:
    if not enabled:
        if has_stores:
            store_key = "COALESCE((st_mkt.store_id)::varchar, s.sglmarket::varchar)"
        else:
            store_key = "s.sglmarket::varchar"
        return (
            f"s.sglmfid AS group_code, NULL::varchar AS group_name, "
            f"NULL::varchar AS department_code, NULL::varchar AS department_name, "
            f"{store_key} AS store_id"
        )
    if has_stores:
        store_key = "COALESCE((cg.store_id)::varchar, (st_mkt.store_id)::varchar, s.sglmarket::varchar)"
    else:
        store_key = "COALESCE((cg.store_id)::varchar, s.sglmarket::varchar)"
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


def _department_display_sort_key(row: dict[str, Any]) -> tuple[int, int, str, str]:
    name = str(row.get("department_name") or "")
    code = str(row.get("department_code") or "")
    if "超市" in name:
        return (0, 0, name, code)
    if "生鲜" in name:
        return (0, 1, name, code)

    cn_order = {
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
    }
    for cn, order in cn_order.items():
        if f"{cn}部" in name:
            return (1, order, name, code)
    return (2, 999, name, code)


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
    result = sorted(departments.values(), key=_department_display_sort_key)
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
    out.sort(key=_department_display_sort_key)
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
        filters.append("s.sgldate >= :start_date")
        params["start_date"] = start_date
    if end_date:
        filters.append("s.sgldate <= :end_date")
        params["end_date"] = end_date
    return (" AND " + " AND ".join(filters)) if filters else ""


def _sales_amount_sql(alias: str = "s") -> str:
    return f"COALESCE(NULLIF({alias}.sglyxssr, 0), {alias}.sglxssr, 0)"


def _cost_amount_sql(alias: str = "s") -> str:
    return f"COALESCE({alias}.sgln13, 0) + COALESCE({alias}.sgln14, 0)"


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


@router.get("/reports/commodity-sales-detail/departments", response_model=list[ReportDepartmentOption])
async def commodity_sales_detail_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """商品销售明细部门下拉：直接取 manaframe 的柜组上级部门主数据。"""
    require_permission(db, current_user, "sales.view")
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
    require_permission(db, current_user, "sales.view")
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
) -> list[dict[str, Any]]:
    """柜组粒度汇总（含 store_id 等 scope 字段），供柜组列表与门店聚合复用。

    unrestricted=True 时不做排序与 LIMIT，用于门店汇总，避免按销售额截断柜组导致门店不全。
    """
    table_name = _salegoodslist_table(db)
    has_counter_groups = _table_exists(db, "manaframe")
    has_stores = _table_exists(db, "stores")
    mkt_join = _stores_market_join_sql(has_stores)
    params: dict[str, Any] = {}
    filters = _date_filter_sql(params, start_date, end_date)
    if store_id:
        filters += _store_scope_filter_sql(has_counter_groups, has_stores)
        params["store_id"] = store_id
    if has_counter_groups:
        filters += _sales_department_exclusion_sql("cg")
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
        SELECT
          {scope_select},
          COUNT(DISTINCT s.sglbillno) AS ticket_count,
          COUNT(*) AS line_count,
          COALESCE(SUM(s.sglsl), 0) AS quantity,
          COALESCE(SUM(s.sglxssr), 0) AS gross_sales,
          COALESCE(SUM(s.sglxssr), 0) AS effective_sales,
          COALESCE(SUM(s.sgln2), 0) AS net_profit,
          CASE
            WHEN COALESCE(SUM(s.sglxssr), 0) = 0 THEN 0
            ELSE COALESCE(SUM(s.sgln2), 0) / NULLIF(COALESCE(SUM(s.sglxssr), 0), 0)
          END AS net_margin,
          CASE
            WHEN COALESCE(SUM(s.sglxssr), 0) = 0 THEN 0
            ELSE COALESCE(SUM(s.sgln2), 0) / NULLIF(COALESCE(SUM(s.sglxssr), 0), 0)
          END AS ticket_margin
        FROM {table_name} s
        {group_join}
        {mkt_join}
        WHERE 1=1 {filters}
        GROUP BY 1, 2, 3, 4, 5
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


@router.get("/summary/stores")
async def store_summary(
    start_date: str | None = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
    prior_start_date: str | None = Query(None, description="同期开始 YYYY-MM-DD；与 prior_end_date 同时传入时覆盖自动「上年同期」区间"),
    prior_end_date: str | None = Query(None, description="同期结束 YYYY-MM-DD"),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    按门店汇总销售：在柜组粒度先做数据范围过滤，再聚合为门店，与权限口径一致。
    """
    require_permission(db, current_user, "sales.view")
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
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
async def department_summary(
    start_date: str | None = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
    prior_start_date: str | None = Query(None, description="同期开始 YYYY-MM-DD"),
    prior_end_date: str | None = Query(None, description="同期结束 YYYY-MM-DD"),
    store_id: str | None = Query(None, description="门店ID/市场号"),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "sales.view")
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    table_name = _salegoodslist_table(db)
    has_counter_groups = _table_exists(db, "manaframe")
    has_stores = _table_exists(db, "stores")
    mkt_join = _stores_market_join_sql(has_stores)
    params: dict[str, Any] = {}
    filters = _date_filter_sql(params, start_date, end_date)
    if store_id:
        filters += _store_scope_filter_sql(has_counter_groups, has_stores)
        params["store_id"] = store_id
    if has_counter_groups:
        filters += _sales_department_exclusion_sql("cg")

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
        if store_id:
            pfilters += _store_scope_filter_sql(has_counter_groups, has_stores)
            pparams["store_id"] = store_id
        if has_counter_groups:
            pfilters += _sales_department_exclusion_sql("cg")
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
async def group_summary(
    start_date: str | None = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
    prior_start_date: str | None = Query(None, description="同期开始 YYYY-MM-DD"),
    prior_end_date: str | None = Query(None, description="同期结束 YYYY-MM-DD"),
    store_id: str | None = Query(None, description="门店ID/市场号"),
    department_code: str | None = Query(None, description="部门编码"),
    unassigned_department: bool = Query(False, description="仅未归属部门（无部门编码的聚合桶）"),
    group_code: str | None = Query(None, description="柜组编码"),
    keyword: str | None = Query(None, description="柜组编码/名称"),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "sales.view")
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
        limit=limit,
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
        )
        prior_stripped = [_strip_scope(r) for r in prior_rows if _row_allowed(scope, r)]
        merged = _merge_group_summaries_same_period(current, prior_stripped)
        return merged[:limit]
    for row in current:
        row["same_period_ticket_count"] = 0.0
        row["same_period_effective_sales"] = 0.0
        row["same_period_net_profit"] = 0.0
        row["same_period_margin"] = 0.0
    return current


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
            "limit": request.limit,
        },
        include_ai=request.include_ai,
    )


@router.get("/map/groups")
async def map_group_summary(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    store_id: str | None = Query(None),
    department_code: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await group_summary(
        start_date=start_date,
        end_date=end_date,
        store_id=store_id,
        department_code=department_code,
        group_code=None,
        keyword=None,
        limit=1000,
        db=db,
        current_user=current_user,
    )


@router.get("/groups/{group_code}/tickets")
async def group_tickets(
    group_code: str,
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    按小票汇总 salegoodslist 行：销售收入=sum(sglxssr)，毛利=sum(sgln2)，小票毛利率=sum(sgln2)/sum(sglxssr)；
    授权折扣=sum(sglgrantzk)，面值卡(MZK)=sum(sglfcard)，礼券(LQ)=sum(sglgcert)-sum(sgltimes)。
    附带：order_point 中消费加积分与生日月会员加积分。

    salehead 若存在 djlx 优先否则 djlb：1→销售，4→退货，其余返回原始码。

    若表为 ods_salegoodslist 且列缺失，需保证与线表结构一致。
    """
    require_permission(db, current_user, "sales.view")
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    table_name = _salegoodslist_table(db)
    has_counter_groups = _table_exists(db, "manaframe")
    has_stores = _table_exists(db, "stores")
    mkt_join = _stores_market_join_sql(has_stores)
    params: dict[str, Any] = {"group_code": group_code, "limit": limit}
    filters = _date_filter_sql(params, start_date, end_date)
    if has_counter_groups:
        filters += _sales_department_exclusion_sql("cg")
    group_join = _counter_group_join_sql(has_counter_groups)
    scope_select = _group_scope_select_sql(has_counter_groups, has_stores=has_stores)
    has_salehead = _table_exists(db, "salehead")
    has_order_point = _table_exists(db, "order_point")
    dj_kind_col = (
        "djlx"
        if has_salehead and _column_exists(db, "salehead", "djlx")
        else "djlb"
        if has_salehead and _column_exists(db, "salehead", "djlb")
        else None
    )
    head_join = ""
    if has_salehead and dj_kind_col:
        head_join = f"""
        LEFT JOIN salehead sh ON sh.billno::text = TRIM(BOTH FROM s.sglbillno::text)
        """
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
            f"{point_category_expr} IN ('消费加积分', '消费获得积分')"
        )
        point_join = f"""
        LEFT JOIN (
          SELECT
            TRIM(BOTH FROM order_id::text) AS order_id,
            COALESCE(SUM(point), 0) AS point,
            COALESCE(SUM(CASE WHEN {consumption_point_condition} THEN point ELSE 0 END), 0) AS consumption_point,
            COALESCE(SUM(CASE WHEN {point_category_expr} LIKE '生日月%' THEN point ELSE 0 END), 0) AS birthday_month_member_point
          FROM order_point
          GROUP BY TRIM(BOTH FROM order_id::text)
        ) op ON op.order_id = TRIM(BOTH FROM s.sglbillno::text)
        """
        point_expr = "COALESCE(MAX(op.point), 0) AS point"
        consumption_point_expr = "COALESCE(MAX(op.consumption_point), 0) AS consumption_point"
        birthday_month_member_point_expr = "COALESCE(MAX(op.birthday_month_member_point), 0) AS birthday_month_member_point"
    else:
        point_expr = "0 AS point"
        consumption_point_expr = "0 AS consumption_point"
        birthday_month_member_point_expr = "0 AS birthday_month_member_point"
    if has_salehead and dj_kind_col:
        txn_expr = f"""
          MAX(
            CASE TRIM(BOTH FROM COALESCE(sh.{dj_kind_col}::text, ''))
              WHEN '1' THEN '销售'
              WHEN '4' THEN '退货'
              ELSE NULLIF(TRIM(BOTH FROM COALESCE(sh.{dj_kind_col}::text, '')), '')
            END
          ) AS transaction_type
        """
    else:
        txn_expr = "NULL::varchar AS transaction_type"

    rows = _fetch_mappings(
        db,
        f"""
        SELECT
          {scope_select},
          s.sglbillno AS billno,
          MIN(s.sgldate) AS sale_date,
          MIN(s.sglsaledate) AS sale_datetime,
          MIN(s.sglinvno) AS invoice_no,
          MIN(s.sglchecker) AS cashier,
          COUNT(*) AS line_count,
          COALESCE(SUM(s.sglsl), 0) AS quantity,
          COALESCE(SUM(s.sglxssr), 0) AS effective_sales,
          COALESCE(SUM(s.sgln2), 0) AS net_profit,
          CASE
            WHEN COALESCE(SUM(s.sglxssr), 0) = 0 THEN 0
            ELSE COALESCE(SUM(s.sgln2), 0) / NULLIF(COALESCE(SUM(s.sglxssr), 0), 0)
          END AS ticket_margin,
          COALESCE(SUM(s.sglgrantzk), 0) AS authorized_discount,
          COALESCE(SUM(s.sglfcard), 0) AS mzk,
          COALESCE(SUM(s.sglgcert), 0) - COALESCE(SUM(s.sgltimes), 0) AS lq,
          {point_expr},
          {consumption_point_expr},
          {birthday_month_member_point_expr},
          {txn_expr}
        FROM {table_name} s
        {group_join}
        {mkt_join}
        {head_join}
        {point_join}
        WHERE upper(trim(COALESCE(s.sglmfid, ''))) = upper(trim(:group_code)) {filters}
        GROUP BY 1, 2, 3, 4, 5, s.sglbillno
        ORDER BY sale_date DESC, billno DESC
        LIMIT :limit
        """,
        params,
    )
    return [_strip_scope(row) for row in rows if _row_allowed(scope, row)]


@router.get("/tickets/{billno}")
async def ticket_detail(
    billno: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "sales.view")
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    has_salehead = _table_exists(db, "salehead")
    has_salegoods = _table_exists(db, "salegoods")
    has_salepay = _table_exists(db, "salepay")
    has_counter_groups = _table_exists(db, "manaframe")

    if has_salehead and has_salegoods:
        goods_scope_join = (
            f"LEFT JOIN {_manaframe_group_source_sql('cg')} ON upper(trim(COALESCE(g.gz, ''))) = upper(trim(COALESCE(cg.group_code, '')))"
            if has_counter_groups
            else ""
        )
        scope_rows = _fetch_mappings(
            db,
            f"""
            SELECT
              COALESCE(g.gz, '') AS group_code,
              {("cg.group_name, cg.department_code, cg.department_name, (cg.store_id)::varchar AS store_id" if has_counter_groups else "NULL::varchar AS group_name, NULL::varchar AS department_code, NULL::varchar AS department_name, g.mkt::varchar AS store_id")}
            FROM salegoods g
            {goods_scope_join}
            WHERE g.billno::varchar = :billno
            {(_sales_department_exclusion_sql("cg") if has_counter_groups else "")}
            GROUP BY 1, 2, 3, 4, 5
            """,
            {"billno": billno},
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
            WHERE billno::varchar = :billno
            LIMIT 1
            """,
            {"billno": billno},
        )
        goods = _fetch_mappings(
            db,
            """
            SELECT
              rowno, mkt, yyyh, barcode, code, sptype, gz AS group_code,
              catid, ppcode, name, unit, sl, lsj, jg, hjje, hjzk,
              hyzke, yhzke, lszke, flag, rqsj
            FROM salegoods
            WHERE billno::varchar = :billno
            ORDER BY rowno
            """,
            {"billno": billno},
        )
        pays = (
            _fetch_mappings(
                db,
                """
                SELECT rowno, paycode, payname, flag, ybje, hl, je, payno, paytype, paymemo, rqsj
                FROM salepay
                WHERE billno::varchar = :billno
                ORDER BY rowno
                """,
                {"billno": billno},
            )
            if has_salepay
            else []
        )
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
        WHERE s.sglbillno::varchar = :billno
        {(_sales_department_exclusion_sql("cg") if has_counter_groups else "")}
        ORDER BY s.sglrowno
        """,
        {"billno": billno},
    )
    allowed_rows = [_strip_scope(row) for row in rows if _row_allowed(scope, row)]
    if rows and not allowed_rows:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无该小票数据权限")
    return {"source": table_name, "head": None, "goods": allowed_rows, "payments": []}
