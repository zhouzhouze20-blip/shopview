"""
活动分析 API

一期口径：只分析卡券使用。活动由 tktpopinfo 定义，卡券日志取 tktcardfqlog，
卡券付款取 salepay 中 0500/0580，销售、成本、毛利取 salegoodslist。
"""

from decimal import Decimal
from typing import Any, Iterable

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from models.database import get_db
from models.models import User
from routers.auth import get_current_user
from routers.authz import load_business_scope, require_permission
from services.sales_analysis.ai_report import generate_ai_report


router = APIRouter(prefix="/api/activity-analysis", tags=["activity-analysis"])
ACTIVITY_ANALYSIS_PERMISSION = "activity_analysis.view"
STAR_DIAMOND_ANALYSIS_PERMISSION = "activity_analysis.star_diamond.view"

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


def _sql_string_list(values: Iterable[str]) -> str:
    return ", ".join("'" + value.replace("'", "''") + "'" for value in values)


def _sales_department_exclusion_sql(alias: str = "cg") -> str:
    names = _sql_string_list(SALES_EXCLUDED_DEPARTMENT_NAMES)
    return f" AND TRIM(BOTH FROM COALESCE({alias}.department_name, '')) NOT IN ({names})"

ACTION_LABELS = {
    "L": "扣券补现",
    "m": "前台买券",
    "Q": "后台赠券",
    "n": "前台退买券",
    "w": "前台买券冲正",
    "z": "前台退券冲正",
    "B": "券补录",
    "I": "后台券新增",
    "K": "返券扣回",
    "M": "后台买券",
    "N": "退买券",
    "Z": "支票返券生效",
    "A": "券增减",
    "F": "返券",
    "O": "券消费",
    "P": "券退货",
    "U": "券消费冲正",
    "V": "券退货冲正",
    "C": "券转移",
    "9": "券延期",
    "D": "券作废",
    "b": "返订金券",
    "l": "扣券补现冲正",
    "X": "面值券",
}

SOURCE_LABELS = {
    "1": "销售返券",
    "2": "前台买券",
    "3": "银行追送",
    "4": "退货返券",
    "5": "券转入",
    "7": "后台手工新增",
    "8": "后台买券",
}

ACTIVITY_STORE_RULES = (
    ("新世纪", 3, "603", "常州新世纪商城"),
    ("大楼", 2, "602", "常州百货大楼"),
    ("中心", 1, "601", "常州购物中心"),
)

ACTION_AMOUNT_SQL = (
    "CASE "
    "WHEN l.tcflzy IN ('F', 'O') THEN ABS(COALESCE(l.tcflmoney, 0)) "
    "WHEN l.tcflzy = 'U' THEN -ABS(COALESCE(l.tcflmoney, 0)) "
    "ELSE COALESCE(l.tcflmoney, 0) "
    "END"
)


def _issued_amount_sql(alias: str = "") -> str:
    prefix = f"{alias}." if alias else ""
    action = f"{prefix}tcflzy"
    amount = f"COALESCE({prefix}tcflmoney, 0)"
    return (
        "CASE "
        f"WHEN {action} IN ('F', 'm', 'M', 'Q', 'I', 'B', 'Z', 'b', 'X') THEN ABS({amount}) "
        f"WHEN {action} IN ('n', 'N', 'w') THEN -ABS({amount}) "
        f"WHEN {action} = 'A' THEN {amount} "
        "ELSE 0 "
        "END"
    )


def _case_expr(column: str, labels: dict[str, str], fallback: str) -> str:
    parts = [f"WHEN {column} = '{code}' THEN '{label}'" for code, label in labels.items()]
    return "CASE " + " ".join(parts) + f" ELSE {fallback} END"


def _code_name_display_sql(code_expr: str, name_expr: str) -> str:
    code = f"NULLIF(TRIM(BOTH FROM COALESCE({code_expr}, '')), '')"
    name = f"NULLIF(TRIM(BOTH FROM COALESCE({name_expr}, '')), '')"
    return (
        "CASE "
        f"WHEN {code} IS NOT NULL AND {name} IS NOT NULL THEN {code} || ' ' || {name} "
        f"WHEN {code} IS NOT NULL THEN {code} "
        f"WHEN {name} IS NOT NULL THEN {name} "
        "ELSE '未标识' "
        "END"
    )


def _brand_join_sql(alias: str = "s", brand_alias: str = "cb") -> str:
    return (
        f"LEFT JOIN codebrand {brand_alias} "
        f"ON UPPER(TRIM(COALESCE({brand_alias}.cbid, ''))) = UPPER(TRIM(COALESCE({alias}.sglppcode, '')))"
    )


def _category_join_sql(alias: str = "s", category_alias: str = "gc") -> str:
    return (
        f"LEFT JOIN goodscat {category_alias} "
        f"ON UPPER(TRIM(COALESCE({category_alias}.catcode, ''))) = UPPER(TRIM(COALESCE({alias}.sglcatid, '')))"
    )


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _activity_store_case_sql(field_expr: str, value_index: int, else_sql: str = "NULL") -> str:
    parts = [
        f"WHEN {field_expr} LIKE '%{keyword}%' THEN {repr(value) if isinstance(value, str) else value}"
        for keyword, *values in ACTIVITY_STORE_RULES
        for value in [values[value_index]]
    ]
    return "CASE " + " ".join(parts) + f" ELSE {else_sql} END"


def _activity_store_id_sql(alias: str = "p") -> str:
    return _activity_store_case_sql(f"COALESCE({alias}.tpiname, '')", 0, "NULL")


def _activity_store_code_sql(alias: str = "p") -> str:
    return _activity_store_case_sql(f"COALESCE({alias}.tpiname, '')", 1, "NULL")


def _activity_store_name_sql(alias: str = "p") -> str:
    return _activity_store_case_sql(f"COALESCE({alias}.tpiname, '')", 2, "NULL")


def _rows(db: Session, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    rows = db.execute(text(sql), params).mappings().all()
    return [{key: _json_value(value) for key, value in row.items()} for row in rows]


def _one(db: Session, sql: str, params: dict[str, Any]) -> dict[str, Any]:
    row = db.execute(text(sql), params).mappings().first()
    if row is None:
        return {}
    return {key: _json_value(value) for key, value in row.items()}


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


def _ensure_required_tables(db: Session) -> None:
    missing = [
        table
        for table in [
            "tktpopinfo",
            "tktcardfqlog",
            "salehead",
            "salepay",
            "salegoodslist",
            "fj_dw_member_dim",
        ]
        if not _table_exists(db, table)
    ]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"活动分析所需数据表未创建: {', '.join(missing)}",
        )


def _activity_store_scope_values(db: Session, scope) -> tuple[set[str], set[str]]:
    if getattr(scope, "all_access", False):
        return set(), set()

    store_ids: set[str] = set()
    store_codes: set[str] = set()
    store_rows = []
    if _table_exists(db, "stores"):
        store_rows = db.execute(text("SELECT store_id, store_code FROM stores")).mappings().all()

    raw_store_values = {str(value).strip().upper() for value in scope.allow.get("store", set()) if str(value).strip()}
    for value in raw_store_values:
        matched = False
        for row in store_rows:
            sid = str(row["store_id"]) if row["store_id"] is not None else ""
            scode = str(row["store_code"] or "").strip().upper()
            if value in {sid.upper(), scode}:
                if sid:
                    store_ids.add(sid)
                if scode:
                    store_codes.add(scode)
                matched = True
        if not matched:
            if value.isdigit() and len(value) == 3:
                store_codes.add(value)
            else:
                store_ids.add(value)

    allowed_departments = scope.allow.get("department", set())
    allowed_groups = scope.allow.get("group", set())
    if (allowed_departments or allowed_groups) and _table_exists(db, "manaframe"):
        params = {
            "department_values": sorted(allowed_departments) or ["__none__"],
            "group_values": sorted(allowed_groups) or ["__none__"],
        }
        rows = db.execute(
            text(
                """
                WITH manaframe_groups AS (
                  SELECT
                    mf.mfcode AS group_code,
                    dept.mfcode AS department_code,
                    dept.mfcname AS department_name
                  FROM manaframe mf
                  LEFT JOIN manaframe dept
                    ON UPPER(TRIM(COALESCE(mf.mfpcode, ''))) = UPPER(TRIM(COALESCE(dept.mfcode, '')))
                )
                SELECT DISTINCT SUBSTRING(TRIM(BOTH FROM COALESCE(group_code, '')) FROM 1 FOR 3) AS store_code
                FROM manaframe_groups
                WHERE UPPER(TRIM(COALESCE(group_code, ''))) = ANY(:group_values)
                   OR UPPER(TRIM(COALESCE(department_code, ''))) = ANY(:department_values)
                   OR UPPER(TRIM(COALESCE(department_name, ''))) = ANY(:department_values)
                """
            ),
            params,
        ).mappings().all()
        for row in rows:
            code = str(row["store_code"] or "").strip().upper()
            if code:
                store_codes.add(code)
                for store in store_rows:
                    if str(store["store_code"] or "").strip().upper() == code and store["store_id"] is not None:
                        store_ids.add(str(store["store_id"]))

    return store_ids, store_codes


def _activity_scope_filter_sql(db: Session, scope, params: dict[str, Any], *, alias: str = "p", prefix: str = "activity_scope") -> str:
    if "__all__" in scope.deny:
        return " AND 1=0"

    if getattr(scope, "all_access", False):
        return ""

    store_ids, store_codes = _activity_store_scope_values(db, scope)
    if not store_ids and not store_codes:
        return " AND 1=0"

    clauses: list[str] = []
    if store_ids:
        key = f"{prefix}_store_ids"
        params[key] = sorted(store_ids)
        clauses.append(f"{_activity_store_id_sql(alias)}::varchar = ANY(:{key})")
    if store_codes:
        key = f"{prefix}_store_codes"
        params[key] = sorted(store_codes)
        clauses.append(f"{_activity_store_code_sql(alias)} = ANY(:{key})")

    denied_store_ids, denied_store_codes = set(), set()
    deny_scope = type("DenyScope", (), {"allow": {"store": scope.deny.get("store", set())}, "all_access": False})()
    if scope.deny.get("store"):
        denied_store_ids, denied_store_codes = _activity_store_scope_values(db, deny_scope)
    deny_sql = ""
    if denied_store_ids or denied_store_codes:
        deny_clauses: list[str] = []
        if denied_store_ids:
            key = f"{prefix}_deny_store_ids"
            params[key] = sorted(denied_store_ids)
            deny_clauses.append(f"{_activity_store_id_sql(alias)}::varchar = ANY(:{key})")
        if denied_store_codes:
            key = f"{prefix}_deny_store_codes"
            params[key] = sorted(denied_store_codes)
            deny_clauses.append(f"{_activity_store_code_sql(alias)} = ANY(:{key})")
        deny_sql = " AND NOT (" + " OR ".join(deny_clauses) + ")"

    return " AND (" + " OR ".join(clauses) + ")" + deny_sql


def _require_center_store_scope(db: Session, user: User) -> None:
    scope = load_business_scope(db, user, fallback_resource_code="sales")
    if getattr(scope, "all_access", False):
        return
    store_ids, store_codes = _activity_store_scope_values(db, scope)
    if "1" in store_ids or "601" in store_codes:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无常州购物中心星钻会员分析权限")


def _star_diamond_member_where(alias: str = "m") -> str:
    value = f"UPPER(TRIM(COALESCE({alias}.is_star_diamond_member, '')))"
    return f"{value} <> '' AND {value} NOT IN ('0', 'N', 'NO', 'FALSE', '否', '不是', '非')"


def _activity_filter(
    activity_id: str | None,
    start_date: str | None,
    end_date: str | None,
    scope: str = "activity",
    activity_scope_sql: str = "",
) -> tuple[str, dict[str, Any]]:
    params: dict[str, Any] = {}
    clauses: list[str] = []
    if activity_id:
        clauses.append("l.tcflpopid = :activity_id")
        params["activity_id"] = activity_id.strip()
    else:
        if scope == "standalone":
            clauses.append(
                "(COALESCE(l.tcflpopid, '') IN ('', '0') OR NOT EXISTS (SELECT 1 FROM tktpopinfo p WHERE p.tpiid = l.tcflpopid))"
            )
        elif scope == "all":
            clauses.append("1=1")
        else:
            clauses.append(
                "COALESCE(l.tcflpopid, '') NOT IN ('', '0') AND EXISTS (SELECT 1 FROM tktpopinfo p WHERE p.tpiid = l.tcflpopid)"
            )
    if activity_scope_sql:
        clauses.append(f"EXISTS (SELECT 1 FROM tktpopinfo p WHERE p.tpiid = l.tcflpopid {activity_scope_sql})")
    if start_date:
        clauses.append("l.tcfldate >= :start_date")
        params["start_date"] = start_date
    if end_date:
        clauses.append("l.tcfldate <= :end_date")
        params["end_date"] = end_date
    return " AND ".join(clauses), params


def _period_filter(activity_id: str | None, start_date: str | None, end_date: str | None) -> tuple[str, dict[str, Any]]:
    params: dict[str, Any] = {}
    if activity_id:
        params["activity_id"] = activity_id.strip()
        params["start_date"] = start_date
        params["end_date"] = end_date
        return (
            """
            h.rqsj::date BETWEEN
              COALESCE(CAST(:start_date AS date), (SELECT tpistartdate FROM tktpopinfo WHERE tpiid = :activity_id), DATE '1900-01-01')
              AND
              COALESCE(CAST(:end_date AS date), (SELECT tpienddate FROM tktpopinfo WHERE tpiid = :activity_id), DATE '2999-12-31')
            """,
            params,
        )
    clauses: list[str] = ["1=1"]
    if start_date:
        clauses.append("h.rqsj::date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        clauses.append("h.rqsj::date <= :end_date")
        params["end_date"] = end_date
    return " AND ".join(clauses), params


def _coupon_type_filter(coupon_type: str | None, alias: str = "l") -> tuple[str, dict[str, Any]]:
    if not coupon_type:
        return "", {}
    return f" AND COALESCE({alias}.tcfljetype, '') = :coupon_type", {"coupon_type": coupon_type.strip()}


def _supplier_discount_cte(extra_where: str = "") -> str:
    return f"""
        supplier_discount AS (
          SELECT
            sgpbillno AS billno,
            sgpmfid AS group_code,
            SUM(COALESCE(sgpjglpayzk, 0)) AS pay_discount_amount,
            SUM(COALESCE(sgpjglsupzk, 0)) AS supplier_discount_amount,
            SUM(COALESCE(sgpjglshopzk, 0)) AS shop_discount_amount
          FROM supgoodspayzkdet
          WHERE sgppmcode IN ('0500', '0580')
            {extra_where}
          GROUP BY sgpbillno, sgpmfid
        )
    """


@router.get("/star-diamond/overview")
async def star_diamond_overview(
    start_date: str = Query(..., description="消费日期起 YYYY-MM-DD"),
    end_date: str = Query(..., description="消费日期止 YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, STAR_DIAMOND_ANALYSIS_PERMISSION)
    _ensure_required_tables(db)
    _require_center_store_scope(db, current_user)

    params = {"start_date": start_date, "end_date": end_date}
    member_where = _star_diamond_member_where("m")
    summary = _one(
        db,
        f"""
        WITH star_members AS (
          SELECT
            UPPER(TRIM(COALESCE(customer_no, ''))) AS member_no,
            customer_name,
            telephone,
            customer_level,
            admission_date,
            is_star_diamond_member
          FROM fj_dw_member_dim m
          WHERE COALESCE(customer_no, '') <> ''
            AND {member_where}
        ),
        tickets AS (
          SELECT
            h.billno,
            UPPER(TRIM(COALESCE(h.hykh, ''))) AS member_no,
            MIN(h.rqsj) AS sale_time,
            SUM(COALESCE(s.sglxssr, 0)) AS sales_amount,
            SUM(COALESCE(s.sglnetml, s.sgln2, 0)) AS net_profit,
            SUM(COALESCE(s.sglsl, 0)) AS quantity,
            SUM(COALESCE(s.sglsqje, 0)) AS coupon_amount
          FROM salehead h
          JOIN star_members sm ON sm.member_no = UPPER(TRIM(COALESCE(h.hykh, '')))
          JOIN salegoodslist s ON s.sglbillno = h.billno
          WHERE h.mkt::varchar = '601'
            AND h.rqsj::date BETWEEN :start_date AND :end_date
          GROUP BY h.billno, UPPER(TRIM(COALESCE(h.hykh, '')))
        ),
        member_sales AS (
          SELECT
            sm.member_no,
            COUNT(DISTINCT t.billno) AS ticket_count,
            COALESCE(SUM(t.sales_amount), 0) AS sales_amount,
            COALESCE(SUM(t.net_profit), 0) AS net_profit,
            MAX(t.sale_time) AS last_sale_time
          FROM star_members sm
          LEFT JOIN tickets t ON t.member_no = sm.member_no
          GROUP BY sm.member_no
        )
        SELECT
          COUNT(*) AS star_member_count,
          COUNT(*) FILTER (WHERE ticket_count > 0) AS active_member_count,
          COALESCE(SUM(ticket_count), 0) AS ticket_count,
          COALESCE(SUM(sales_amount), 0) AS sales_amount,
          COALESCE(SUM(net_profit), 0) AS net_profit,
          CASE WHEN COALESCE(SUM(ticket_count), 0) > 0 THEN COALESCE(SUM(sales_amount), 0) / SUM(ticket_count) ELSE 0 END AS avg_ticket_amount,
          CASE WHEN COUNT(*) FILTER (WHERE ticket_count > 0) > 0 THEN COALESCE(SUM(sales_amount), 0) / COUNT(*) FILTER (WHERE ticket_count > 0) ELSE 0 END AS avg_member_amount,
          COUNT(*) FILTER (WHERE ticket_count >= 2) AS repeat_member_count,
          COUNT(*) FILTER (WHERE ticket_count = 0) AS silent_member_count,
          COUNT(*) FILTER (WHERE ticket_count > 0 AND sales_amount >= 10000) AS high_value_member_count,
          COUNT(*) FILTER (WHERE ticket_count > 0 AND sales_amount < 10000) AS nurture_member_count
        FROM member_sales
        """,
        params,
    )

    category_rows = _rows(
        db,
        f"""
        WITH star_members AS (
          SELECT UPPER(TRIM(COALESCE(customer_no, ''))) AS member_no
          FROM fj_dw_member_dim m
          WHERE COALESCE(customer_no, '') <> ''
            AND {member_where}
        )
        SELECT
          COALESCE(NULLIF(s.sglcatid, ''), '未标识') AS category_code,
          COALESCE(NULLIF(gc.catcname, ''), '') AS category_name,
          {_code_name_display_sql("s.sglcatid", "gc.catcname")} AS category_display,
          COUNT(DISTINCT h.hykh) AS member_count,
          COUNT(DISTINCT h.billno) AS ticket_count,
          SUM(COALESCE(s.sglxssr, 0)) AS sales_amount
        FROM salehead h
        JOIN star_members sm ON sm.member_no = UPPER(TRIM(COALESCE(h.hykh, '')))
        JOIN salegoodslist s ON s.sglbillno = h.billno
        {_category_join_sql("s", "gc")}
        WHERE h.mkt::varchar = '601'
          AND h.rqsj::date BETWEEN :start_date AND :end_date
        GROUP BY 1, 2, 3
        ORDER BY sales_amount DESC
        LIMIT 10
        """,
        params,
    )

    service_segments = _rows(
        db,
        f"""
        WITH star_members AS (
          SELECT UPPER(TRIM(COALESCE(customer_no, ''))) AS member_no
          FROM fj_dw_member_dim m
          WHERE COALESCE(customer_no, '') <> ''
            AND {member_where}
        ),
        member_sales AS (
          SELECT
            sm.member_no,
            COUNT(DISTINCT h.billno) AS ticket_count,
            COALESCE(SUM(s.sglxssr), 0) AS sales_amount,
            MAX(h.rqsj) AS last_sale_time
          FROM star_members sm
          LEFT JOIN salehead h
            ON sm.member_no = UPPER(TRIM(COALESCE(h.hykh, '')))
           AND h.mkt::varchar = '601'
           AND h.rqsj::date BETWEEN :start_date AND :end_date
          LEFT JOIN salegoodslist s ON s.sglbillno = h.billno
          GROUP BY sm.member_no
        )
        SELECT
          segment,
          COUNT(*) AS member_count,
          SUM(sales_amount) AS sales_amount,
          service_action
        FROM (
          SELECT
            member_no,
            sales_amount,
            CASE
              WHEN ticket_count = 0 THEN '待唤醒'
              WHEN sales_amount >= 10000 THEN '高价值维护'
              WHEN ticket_count >= 2 THEN '高频互动'
              ELSE '潜力培育'
            END AS segment,
            CASE
              WHEN ticket_count = 0 THEN '专属顾问一对一回访，提供新品预览、生日礼遇或到店预约。'
              WHEN sales_amount >= 10000 THEN '安排专属接待、重点品牌私享会、预留爆款和售后跟进。'
              WHEN ticket_count >= 2 THEN '推送跨品类搭配权益，邀请参加会员日和积分加速活动。'
              ELSE '根据最近购买品类推荐同楼层品牌券包，提升二次到店。'
            END AS service_action
          FROM member_sales
        ) x
        GROUP BY segment, service_action
        ORDER BY sales_amount DESC NULLS LAST, member_count DESC
        """,
        params,
    )

    return {"summary": summary, "top_categories": category_rows, "service_segments": service_segments}


@router.get("/star-diamond/members")
async def star_diamond_members(
    start_date: str = Query(...),
    end_date: str = Query(...),
    keyword: str | None = Query(None, description="会员号/姓名/手机号"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, STAR_DIAMOND_ANALYSIS_PERMISSION)
    _ensure_required_tables(db)
    _require_center_store_scope(db, current_user)

    params: dict[str, Any] = {"start_date": start_date, "end_date": end_date, "limit": limit}
    keyword_sql = ""
    if keyword:
        params["keyword"] = f"%{keyword.strip()}%"
        keyword_sql = "AND (m.customer_no ILIKE :keyword OR m.customer_name ILIKE :keyword OR m.telephone ILIKE :keyword)"

    return _rows(
        db,
        f"""
        WITH star_members AS (
          SELECT
            UPPER(TRIM(COALESCE(customer_no, ''))) AS member_no,
            customer_name,
            telephone,
            customer_level,
            admission_date,
            is_star_diamond_member
          FROM fj_dw_member_dim m
          WHERE COALESCE(customer_no, '') <> ''
            AND {_star_diamond_member_where("m")}
            {keyword_sql}
        ),
        member_sales AS (
          SELECT
            sm.member_no,
            COUNT(DISTINCT h.billno) AS ticket_count,
            COALESCE(SUM(s.sglxssr), 0) AS sales_amount,
            COALESCE(SUM(s.sglnetml), 0) AS net_profit,
            MAX(h.rqsj) AS last_sale_time,
            STRING_AGG(DISTINCT {_code_name_display_sql("s.sglcatid", "gc.catcname")}, ', ')
              FILTER (WHERE s.sglbillno IS NOT NULL) AS categories,
            STRING_AGG(DISTINCT {_code_name_display_sql("s.sglppcode", "cb.cbcname")}, ', ')
              FILTER (WHERE s.sglbillno IS NOT NULL) AS brands
          FROM star_members sm
          LEFT JOIN salehead h
            ON sm.member_no = UPPER(TRIM(COALESCE(h.hykh, '')))
           AND h.mkt::varchar = '601'
           AND h.rqsj::date BETWEEN :start_date AND :end_date
          LEFT JOIN salegoodslist s ON s.sglbillno = h.billno
          {_category_join_sql("s", "gc")}
          {_brand_join_sql("s", "cb")}
          GROUP BY sm.member_no
        )
        SELECT
          sm.member_no,
          sm.customer_name,
          sm.telephone,
          sm.customer_level,
          sm.admission_date,
          sm.is_star_diamond_member,
          COALESCE(ms.ticket_count, 0) AS ticket_count,
          COALESCE(ms.sales_amount, 0) AS sales_amount,
          COALESCE(ms.net_profit, 0) AS net_profit,
          CASE WHEN COALESCE(ms.ticket_count, 0) > 0 THEN COALESCE(ms.sales_amount, 0) / ms.ticket_count ELSE 0 END AS avg_ticket_amount,
          ms.last_sale_time,
          COALESCE(ms.categories, '') AS categories,
          COALESCE(ms.brands, '') AS brands,
          CASE
            WHEN COALESCE(ms.ticket_count, 0) = 0 THEN '待唤醒'
            WHEN COALESCE(ms.sales_amount, 0) >= 10000 THEN '高价值维护'
            WHEN COALESCE(ms.ticket_count, 0) >= 2 THEN '高频互动'
            ELSE '潜力培育'
          END AS service_segment
        FROM star_members sm
        LEFT JOIN member_sales ms ON ms.member_no = sm.member_no
        ORDER BY sales_amount DESC, ticket_count DESC, sm.member_no
        LIMIT :limit
        """,
        params,
    )


@router.get("/star-diamond/trails")
async def star_diamond_trails(
    start_date: str = Query(...),
    end_date: str = Query(...),
    member_no: str | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, STAR_DIAMOND_ANALYSIS_PERMISSION)
    _ensure_required_tables(db)
    _require_center_store_scope(db, current_user)

    params: dict[str, Any] = {"start_date": start_date, "end_date": end_date, "limit": limit}
    member_filter = ""
    if member_no:
        params["member_no"] = member_no.strip().upper()
        member_filter = "AND UPPER(TRIM(COALESCE(h.hykh, ''))) = :member_no"

    return _rows(
        db,
        f"""
        WITH star_members AS (
          SELECT UPPER(TRIM(COALESCE(customer_no, ''))) AS member_no, customer_name, telephone
          FROM fj_dw_member_dim m
          WHERE COALESCE(customer_no, '') <> ''
            AND {_star_diamond_member_where("m")}
        ),
        manaframe_groups AS (
          SELECT
            mf.mfcode AS group_code,
            mf.mfcname AS group_name,
            dept.mfcode AS department_code,
            dept.mfcname AS department_name
          FROM manaframe mf
          LEFT JOIN manaframe dept
            ON UPPER(TRIM(COALESCE(mf.mfpcode, ''))) = UPPER(TRIM(COALESCE(dept.mfcode, '')))
        )
        SELECT
          h.rqsj AS sale_time,
          h.billno,
          h.hykh AS member_no,
          sm.customer_name,
          sm.telephone,
          COUNT(*) AS sku_count,
          SUM(COALESCE(s.sglsl, 0)) AS quantity,
          SUM(COALESCE(s.sglxssr, 0)) AS sales_amount,
          SUM(COALESCE(s.sglnetml, s.sgln2, 0)) AS net_profit,
          STRING_AGG(DISTINCT {_code_name_display_sql("cg.department_code", "cg.department_name")}, ', ')
            FILTER (WHERE s.sglbillno IS NOT NULL) AS departments,
          STRING_AGG(DISTINCT {_code_name_display_sql("COALESCE(cg.group_code, s.sglmfid)", "cg.group_name")}, ', ')
            FILTER (WHERE s.sglbillno IS NOT NULL) AS groups,
          STRING_AGG(DISTINCT {_code_name_display_sql("s.sglcatid", "gc.catcname")}, ', ')
            FILTER (WHERE s.sglbillno IS NOT NULL) AS categories,
          STRING_AGG(DISTINCT {_code_name_display_sql("s.sglppcode", "cb.cbcname")}, ', ')
            FILTER (WHERE s.sglbillno IS NOT NULL) AS brands
        FROM salehead h
        JOIN star_members sm ON sm.member_no = UPPER(TRIM(COALESCE(h.hykh, '')))
        JOIN salegoodslist s ON s.sglbillno = h.billno
        LEFT JOIN manaframe_groups cg ON UPPER(TRIM(COALESCE(cg.group_code, ''))) = UPPER(TRIM(COALESCE(s.sglmfid, '')))
        {_category_join_sql("s", "gc")}
        {_brand_join_sql("s", "cb")}
        WHERE h.mkt::varchar = '601'
          AND h.rqsj::date BETWEEN :start_date AND :end_date
          {member_filter}
        GROUP BY h.rqsj, h.billno, h.hykh, sm.customer_name, sm.telephone
        ORDER BY h.rqsj DESC, h.billno DESC
        LIMIT :limit
        """,
        params,
    )


@router.post("/star-diamond/member-analysis")
async def star_diamond_member_analysis(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, STAR_DIAMOND_ANALYSIS_PERMISSION)
    _ensure_required_tables(db)
    _require_center_store_scope(db, current_user)

    member_no = str(payload.get("member_no") or "").strip().upper()
    start_date = str(payload.get("start_date") or "").strip()
    end_date = str(payload.get("end_date") or "").strip()
    if not member_no or not start_date or not end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="member_no/start_date/end_date 不能为空")

    params = {"member_no": member_no, "start_date": start_date, "end_date": end_date}
    member = _one(
        db,
        f"""
        SELECT
          customer_no AS member_no,
          customer_name,
          telephone,
          customer_level,
          admission_date,
          regist_channel,
          customer_status,
          is_star_diamond_member
        FROM fj_dw_member_dim m
        WHERE UPPER(TRIM(COALESCE(customer_no, ''))) = :member_no
          AND {_star_diamond_member_where("m")}
        """,
        params,
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="星钻会员不存在")

    summary = _one(
        db,
        """
        WITH tickets AS (
          SELECT
            h.billno,
            MIN(h.rqsj) AS sale_time,
            SUM(COALESCE(s.sglxssr, 0)) AS sales_amount,
            SUM(COALESCE(s.sglnetml, s.sgln2, 0)) AS net_profit,
            SUM(COALESCE(s.sglsl, 0)) AS quantity,
            COUNT(DISTINCT NULLIF(s.sglcatid, '')) AS category_count,
            COUNT(DISTINCT NULLIF(s.sglppcode, '')) AS brand_count
          FROM salehead h
          JOIN salegoodslist s ON s.sglbillno = h.billno
          WHERE h.mkt::varchar = '601'
            AND UPPER(TRIM(COALESCE(h.hykh, ''))) = :member_no
            AND h.rqsj::date BETWEEN :start_date AND :end_date
          GROUP BY h.billno
        )
        SELECT
          COUNT(*) AS ticket_count,
          COALESCE(SUM(sales_amount), 0) AS sales_amount,
          COALESCE(SUM(net_profit), 0) AS net_profit,
          COALESCE(SUM(quantity), 0) AS quantity,
          CASE WHEN COUNT(*) > 0 THEN COALESCE(SUM(sales_amount), 0) / COUNT(*) ELSE 0 END AS avg_ticket_amount,
          MAX(sale_time) AS last_sale_time,
          MIN(sale_time) AS first_sale_time,
          COALESCE(SUM(category_count), 0) AS category_touch_count,
          COALESCE(SUM(brand_count), 0) AS brand_touch_count
        FROM tickets
        """,
        params,
    )
    categories = _rows(
        db,
        f"""
        SELECT
          COALESCE(NULLIF(s.sglcatid, ''), '未标识') AS category_code,
          COALESCE(NULLIF(gc.catcname, ''), '') AS category_name,
          {_code_name_display_sql("s.sglcatid", "gc.catcname")} AS category_display,
          COUNT(DISTINCT h.billno) AS ticket_count,
          SUM(COALESCE(s.sglxssr, 0)) AS sales_amount
        FROM salehead h
        JOIN salegoodslist s ON s.sglbillno = h.billno
        {_category_join_sql("s", "gc")}
        WHERE h.mkt::varchar = '601'
          AND UPPER(TRIM(COALESCE(h.hykh, ''))) = :member_no
          AND h.rqsj::date BETWEEN :start_date AND :end_date
        GROUP BY 1, 2, 3
        ORDER BY sales_amount DESC
        LIMIT 8
        """,
        params,
    )
    trails = await star_diamond_trails(start_date, end_date, member_no, 20, db, current_user)

    rule_notes: list[str] = []
    sales_amount = float(summary.get("sales_amount") or 0)
    ticket_count = float(summary.get("ticket_count") or 0)
    if ticket_count == 0:
        rule_notes.append("期间未在中心消费，优先做一对一唤醒和到店预约。")
    elif sales_amount >= 10000:
        rule_notes.append("期间消费高，建议专属接待、重点品牌私享会和售后跟进。")
    if ticket_count >= 2:
        rule_notes.append("期间有复购，可围绕偏好品类做跨品牌组合权益。")
    if not rule_notes:
        rule_notes.append("期间有消费但频次不高，建议用同楼层品牌券包促进二次到店。")

    ai = generate_ai_report(
        {
            "member": member,
            "period": {"start_date": start_date, "end_date": end_date, "store": "常州购物中心"},
            "summary": summary,
            "top_categories": categories,
            "recent_trails": trails,
            "rule_notes": rule_notes,
        },
        instructions=(
            "你是百货商场高端会员运营顾问。"
            "基于提供的星钻会员消费、品类、购物轨迹，输出针对单个会员的服务建议。"
            "不要编造未提供的信息，不要输出思考过程。"
            "输出结构：会员画像、消费特征、服务机会、下一步动作。"
            "动作要具体到导购/客服可执行，控制在 400 字以内。"
        ),
    )
    return {
        "member": member,
        "summary": summary,
        "top_categories": categories,
        "recent_trails": trails,
        "rule_notes": rule_notes,
        "ai": ai,
    }


@router.post("/star-diamond/overall-analysis")
async def star_diamond_overall_analysis(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, STAR_DIAMOND_ANALYSIS_PERMISSION)
    _ensure_required_tables(db)
    _require_center_store_scope(db, current_user)

    start_date = str(payload.get("start_date") or "").strip()
    end_date = str(payload.get("end_date") or "").strip()
    if not start_date or not end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_date/end_date 不能为空")

    params = {"start_date": start_date, "end_date": end_date}
    member_where = _star_diamond_member_where("m")
    overview_data = await star_diamond_overview(start_date, end_date, db, current_user)
    top_members = await star_diamond_members(start_date, end_date, None, 30, db, current_user)
    recent_trails = await star_diamond_trails(start_date, end_date, None, 50, db, current_user)

    top_brands = _rows(
        db,
        f"""
        WITH star_members AS (
          SELECT UPPER(TRIM(COALESCE(customer_no, ''))) AS member_no
          FROM fj_dw_member_dim m
          WHERE COALESCE(customer_no, '') <> ''
            AND {member_where}
        )
        SELECT
          COALESCE(NULLIF(s.sglppcode, ''), '未标识') AS brand_code,
          COALESCE(NULLIF(cb.cbcname, ''), '') AS brand_name,
          {_code_name_display_sql("s.sglppcode", "cb.cbcname")} AS brand_display,
          COUNT(DISTINCT h.hykh) AS member_count,
          COUNT(DISTINCT h.billno) AS ticket_count,
          SUM(COALESCE(s.sglxssr, 0)) AS sales_amount
        FROM salehead h
        JOIN star_members sm ON sm.member_no = UPPER(TRIM(COALESCE(h.hykh, '')))
        JOIN salegoodslist s ON s.sglbillno = h.billno
        {_brand_join_sql("s", "cb")}
        WHERE h.mkt::varchar = '601'
          AND h.rqsj::date BETWEEN :start_date AND :end_date
        GROUP BY 1, 2, 3
        ORDER BY sales_amount DESC
        LIMIT 10
        """,
        params,
    )
    top_departments = _rows(
        db,
        f"""
        WITH star_members AS (
          SELECT UPPER(TRIM(COALESCE(customer_no, ''))) AS member_no
          FROM fj_dw_member_dim m
          WHERE COALESCE(customer_no, '') <> ''
            AND {member_where}
        ),
        manaframe_groups AS (
          SELECT
            mf.mfcode AS group_code,
            mf.mfcname AS group_name,
            dept.mfcode AS department_code,
            dept.mfcname AS department_name
          FROM manaframe mf
          LEFT JOIN manaframe dept
            ON UPPER(TRIM(COALESCE(mf.mfpcode, ''))) = UPPER(TRIM(COALESCE(dept.mfcode, '')))
        )
        SELECT
          COALESCE(NULLIF(cg.department_code, ''), '未归属') AS department_code,
          COALESCE(NULLIF(cg.department_name, ''), '未归属部门') AS department_name,
          {_code_name_display_sql("cg.department_code", "cg.department_name")} AS department_display,
          COUNT(DISTINCT h.hykh) AS member_count,
          COUNT(DISTINCT h.billno) AS ticket_count,
          SUM(COALESCE(s.sglxssr, 0)) AS sales_amount
        FROM salehead h
        JOIN star_members sm ON sm.member_no = UPPER(TRIM(COALESCE(h.hykh, '')))
        JOIN salegoodslist s ON s.sglbillno = h.billno
        LEFT JOIN manaframe_groups cg ON UPPER(TRIM(COALESCE(cg.group_code, ''))) = UPPER(TRIM(COALESCE(s.sglmfid, '')))
        WHERE h.mkt::varchar = '601'
          AND h.rqsj::date BETWEEN :start_date AND :end_date
        GROUP BY 1, 2, 3
        ORDER BY sales_amount DESC
        LIMIT 10
        """,
        params,
    )

    summary = overview_data.get("summary") or {}
    star_member_count = float(summary.get("star_member_count") or 0)
    active_member_count = float(summary.get("active_member_count") or 0)
    silent_member_count = float(summary.get("silent_member_count") or 0)
    repeat_member_count = float(summary.get("repeat_member_count") or 0)
    active_rate = active_member_count / star_member_count if star_member_count else 0
    repeat_rate = repeat_member_count / active_member_count if active_member_count else 0
    silent_rate = silent_member_count / star_member_count if star_member_count else 0
    rule_notes = [
        f"星钻会员消费覆盖率约 {active_rate:.1%}，需要同时管理高贡献人群与未消费人群。",
        f"活跃星钻会员复购率约 {repeat_rate:.1%}，可按复购人群设计专属二次到店权益。",
        f"未消费星钻会员占比约 {silent_rate:.1%}，建议形成顾问回访和预约到店清单。",
        "品牌、品类和部门建议优先使用销售贡献与消费会员数共同判断，避免只看单笔高客单。",
    ]

    ai_payload = {
        "period": {"start_date": start_date, "end_date": end_date, "store": "常州购物中心"},
        "summary": summary,
        "service_segments": overview_data.get("service_segments") or [],
        "top_categories": overview_data.get("top_categories") or [],
        "top_brands": top_brands,
        "top_departments": top_departments,
        "top_members": top_members,
        "recent_trails": recent_trails,
        "rule_notes": rule_notes,
    }
    ai = generate_ai_report(
        ai_payload,
        instructions=(
            "你是百货商场高端会员运营负责人。"
            "基于所选时间段内全部星钻会员销售明细、分层、品类、品牌、部门和购物轨迹样本，"
            "输出面向门店管理层和会员运营团队的整体经营分析与服务方案。"
            "不要编造未提供的信息，不要输出思考过程。"
            "输出结构：1. 核心判断 2. 会员分层动作 3. 品类/品牌/部门机会 4. 重点会员服务打法 5. 未来7天执行清单。"
            "建议要可执行，说明哪些人群优先、由谁跟进、跟进什么内容，控制在 800 字以内。"
        ),
    )
    return {
        **ai_payload,
        "ai": ai,
    }


@router.get("/activities")
async def activities(
    start_date: str | None = Query(None, description="活动开始日期下限 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="活动结束日期上限 YYYY-MM-DD"),
    keyword: str | None = Query(None, description="活动编码/主题"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, ACTIVITY_ANALYSIS_PERMISSION)
    _ensure_required_tables(db)

    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    params: dict[str, Any] = {"limit": limit}
    filters: list[str] = ["1=1"]
    if start_date:
        filters.append("p.tpienddate >= :start_date")
        params["start_date"] = start_date
    if end_date:
        filters.append("p.tpistartdate <= :end_date")
        params["end_date"] = end_date
    if keyword:
        filters.append("(p.tpiid ILIKE :keyword OR p.tpiname ILIKE :keyword)")
        params["keyword"] = f"%{keyword.strip()}%"
    activity_scope_sql = _activity_scope_filter_sql(db, scope, params, alias="p", prefix="activities")
    if activity_scope_sql:
        filters.append(activity_scope_sql.removeprefix(" AND "))

    return _rows(
        db,
        f"""
        WITH log_bill AS (
          SELECT
            l.tcflpopid AS activity_id,
            h.billno,
            SUM({ACTION_AMOUNT_SQL}) AS log_amount,
            SUM({_issued_amount_sql("l")}) AS issued_log_amount,
            SUM(CASE WHEN l.tcflzy = 'O' THEN ABS(COALESCE(l.tcflmoney, 0)) WHEN l.tcflzy = 'U' THEN -ABS(COALESCE(l.tcflmoney, 0)) ELSE 0 END) AS consumed_log_amount,
            COUNT(*) AS log_count
          FROM tktcardfqlog l
          JOIN salehead h
            ON l.tcflmkt = h.mkt
           AND l.tcflsyjid = h.syjh
           AND l.tcflinvno ~ '^[0-9]+$'
           AND h.fphm = l.tcflinvno::numeric
          WHERE COALESCE(l.tcflpopid, '') <> '0'
          GROUP BY l.tcflpopid, h.billno
        ),
        pay_bill AS (
          SELECT
            lb.activity_id,
            p.billno,
            SUM(COALESCE(p.je, 0)) AS coupon_pay_amount
          FROM salepay p
          JOIN log_bill lb
            ON lb.billno = p.billno
          JOIN tktcardfqlog l
            ON l.tcflpopid = lb.activity_id
           AND l.tcflzy = 'O'
           AND p.batch = l.tcflsyjtrace::varchar
          WHERE p.paycode IN ('0500', '0580')
          GROUP BY lb.activity_id, p.billno
        )
        SELECT
          p.tpiid AS activity_id,
          p.tpiname AS activity_name,
          {_activity_store_id_sql("p")} AS store_id,
          {_activity_store_code_sql("p")} AS store_code,
          {_activity_store_name_sql("p")} AS store_name,
          p.tpistartdate AS start_date,
          p.tpienddate AS end_date,
          COALESCE(COUNT(DISTINCT lb.billno), 0) AS ticket_count,
          COALESCE(SUM(lb.log_amount), 0) AS card_log_amount,
          COALESCE(SUM(lb.issued_log_amount), 0) AS issued_log_amount,
          COALESCE(SUM(lb.consumed_log_amount), 0) AS consumed_log_amount,
          COALESCE(SUM(pb.coupon_pay_amount), 0) AS coupon_pay_amount
        FROM tktpopinfo p
        LEFT JOIN log_bill lb ON lb.activity_id = p.tpiid
        LEFT JOIN pay_bill pb ON pb.activity_id = p.tpiid AND pb.billno = lb.billno
        WHERE {" AND ".join(filters)}
        GROUP BY p.tpiid, p.tpiname, p.tpistartdate, p.tpienddate
        ORDER BY p.tpistartdate DESC NULLS LAST, p.tpiid DESC
        LIMIT :limit
        """,
        params,
    )


@router.get("/overview")
async def overview(
    activity_id: str | None = Query(None, description="活动档期编码 tktpopinfo.tpiid"),
    scope: str = Query("activity", pattern="^(activity|standalone|all)$", description="activity 活动档期券；standalone 非档期券；all 全部卡券"),
    start_date: str | None = Query(None, description="日志日期起 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="日志日期止 YYYY-MM-DD"),
    limit: int = Query(20, ge=5, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, ACTIVITY_ANALYSIS_PERMISSION)
    _ensure_required_tables(db)

    business_scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    activity_scope_params: dict[str, Any] = {}
    activity_scope_sql = _activity_scope_filter_sql(db, business_scope, activity_scope_params, alias="p", prefix="overview")
    log_filter, log_params = _activity_filter(activity_id, start_date, end_date, scope, activity_scope_sql)
    period_filter, period_params = _period_filter(activity_id, start_date, end_date)
    params = {**activity_scope_params, **log_params, **period_params, "limit": limit}
    params.setdefault("activity_id", None)

    activity = None
    if activity_id:
        activity = _one(
            db,
            f"""
            SELECT
              p.tpiid AS activity_id,
              p.tpiname AS activity_name,
              {_activity_store_id_sql("p")} AS store_id,
              {_activity_store_code_sql("p")} AS store_code,
              {_activity_store_name_sql("p")} AS store_name,
              tpistartdate AS start_date,
              tpienddate AS end_date,
              tpiyqstartdate AS coupon_start_date,
              tpiyqenddate AS coupon_end_date,
              tpmemo AS memo
            FROM tktpopinfo p
            WHERE p.tpiid = :activity_id
              {activity_scope_sql}
            """,
            params,
        )
        if not activity:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="活动不存在或无数据权限")

    summary = _one(
        db,
        f"""
        WITH raw_logs AS (
          SELECT l.*
               , {ACTION_AMOUNT_SQL} AS action_amount
          FROM tktcardfqlog l
          WHERE {log_filter}
        ),
        matched_logs AS (
          SELECT
            l.*,
            h.billno,
            h.hykh,
            h.hycid,
            h.rqsj AS sale_time,
            h.ybillno,
            h.ysyjh,
            h.yfphm
          FROM raw_logs l
          JOIN salehead h
            ON l.tcflmkt = h.mkt
           AND l.tcflsyjid = h.syjh
           AND l.tcflinvno ~ '^[0-9]+$'
           AND h.fphm = l.tcflinvno::numeric
        ),
        pay_trace AS (
          SELECT DISTINCT billno, tcflsyjtrace
          FROM matched_logs
          WHERE tcflzy = 'O' AND tcflsyjtrace IS NOT NULL
        ),
        log_bill AS (
          SELECT
            billno,
            MIN(hykh) AS member_no,
            COUNT(*) AS log_count,
            SUM(COALESCE(tcflmoney, 0)) AS raw_card_log_amount,
            SUM(action_amount) AS card_log_amount,
            SUM({_issued_amount_sql()}) AS issued_log_amount,
            SUM(CASE WHEN tcflzy = 'O' THEN ABS(COALESCE(tcflmoney, 0)) WHEN tcflzy = 'U' THEN -ABS(COALESCE(tcflmoney, 0)) ELSE 0 END) AS consumed_log_amount,
            SUM(CASE WHEN tcflzy NOT IN ('F', 'O', 'U') THEN COALESCE(tcflmoney, 0) ELSE 0 END) AS other_log_amount
          FROM matched_logs
          GROUP BY billno
        ),
        pay_bill AS (
          SELECT
            p.billno,
            SUM(CASE WHEN p.paycode = '0500' THEN COALESCE(p.je, 0) ELSE 0 END) AS pay_0500_amount,
            SUM(CASE WHEN p.paycode = '0580' THEN COALESCE(p.je, 0) ELSE 0 END) AS pay_0580_amount,
            SUM(COALESCE(p.je, 0)) AS coupon_pay_amount,
            COUNT(*) AS coupon_pay_count
          FROM salepay p
          JOIN pay_trace pt
            ON pt.billno = p.billno
           AND p.batch = pt.tcflsyjtrace::varchar
          WHERE p.paycode IN ('0500', '0580')
          GROUP BY p.billno
        ),
        sales_bill AS (
          SELECT
            s.sglbillno AS billno,
            SUM(COALESCE(s.sglxssr, 0)) AS sales_amount,
            SUM(COALESCE(s.sgln13, 0)) AS sales_cost,
            SUM(COALESCE(s.sgln2, 0)) AS gross_profit,
            SUM(COALESCE(s.sglnetml, s.sgln2, 0)) AS net_profit,
            SUM(COALESCE(s.sglsqje, 0)) AS received_coupon_amount,
            SUM(COALESCE(s.sglfqje, 0)) AS issued_coupon_amount,
            SUM(COALESCE(s.sglthss, 0)) AS return_loss,
            SUM(COALESCE(s.sglsl, 0)) AS quantity
          FROM salegoodslist s
          JOIN log_bill lb ON lb.billno = s.sglbillno
          GROUP BY s.sglbillno
        ),
        member_dim AS (
          SELECT
            UPPER(TRIM(COALESCE(customer_no, ''))) AS member_no_key,
            MIN(admission_date) AS admission_date
          FROM fj_dw_member_dim
          WHERE COALESCE(customer_no, '') <> ''
          GROUP BY 1
        ),
        new_member_bill AS (
          SELECT
            lb.billno,
            lb.member_no,
            COALESCE(sb.sales_amount, 0) AS sales_amount
          FROM log_bill lb
          JOIN member_dim m
            ON m.member_no_key = UPPER(TRIM(COALESCE(lb.member_no, '')))
          LEFT JOIN sales_bill sb ON sb.billno = lb.billno
          WHERE lb.member_no IS NOT NULL
            AND COALESCE(lb.member_no, '') <> ''
            AND :activity_id IS NOT NULL
            AND m.admission_date BETWEEN
              COALESCE((SELECT tpistartdate FROM tktpopinfo WHERE tpiid = :activity_id), DATE '1900-01-01')
              AND
              COALESCE((SELECT tpienddate FROM tktpopinfo WHERE tpiid = :activity_id), DATE '2999-12-31')
        ),
        period_pay AS (
          SELECT
            COUNT(*) AS period_coupon_pay_count,
            SUM(COALESCE(p.je, 0)) AS period_coupon_pay_amount
          FROM salepay p
          JOIN salehead h ON h.billno = p.billno
          WHERE p.paycode IN ('0500', '0580')
            AND {period_filter}
        )
        SELECT
          COUNT(DISTINCT lb.billno) AS ticket_count,
          COUNT(DISTINCT NULLIF(lb.member_no, '')) AS member_count,
          COALESCE(SUM(lb.log_count), 0) AS card_log_count,
          COALESCE(SUM(lb.raw_card_log_amount), 0) AS raw_card_log_amount,
          COALESCE(SUM(lb.card_log_amount), 0) AS card_log_amount,
          COALESCE(SUM(lb.issued_log_amount), 0) AS issued_log_amount,
          COALESCE(SUM(lb.consumed_log_amount), 0) AS consumed_log_amount,
          COALESCE(SUM(lb.other_log_amount), 0) AS other_log_amount,
          COALESCE(SUM(pb.coupon_pay_count), 0) AS coupon_pay_count,
          COALESCE(SUM(pb.coupon_pay_amount), 0) AS coupon_pay_amount,
          COALESCE(SUM(pb.pay_0500_amount), 0) AS pay_0500_amount,
          COALESCE(SUM(pb.pay_0580_amount), 0) AS pay_0580_amount,
          COALESCE(SUM(sb.sales_amount), 0) AS sales_amount,
          COALESCE(SUM(sb.sales_cost), 0) AS sales_cost,
          COALESCE(SUM(sb.gross_profit), 0) AS gross_profit,
          COALESCE(SUM(sb.net_profit), 0) AS net_profit,
          COALESCE(SUM(sb.received_coupon_amount), 0) AS received_coupon_amount,
          COALESCE(SUM(sb.issued_coupon_amount), 0) AS issued_coupon_amount,
          COALESCE(SUM(sb.return_loss), 0) AS return_loss,
          COALESCE(SUM(sb.quantity), 0) AS quantity,
          COALESCE((SELECT COUNT(DISTINCT member_no) FROM new_member_bill), 0) AS new_member_count,
          COALESCE((SELECT SUM(sales_amount) FROM new_member_bill), 0) AS new_member_sales_amount,
          MAX(pp.period_coupon_pay_count) AS period_coupon_pay_count,
          MAX(pp.period_coupon_pay_amount) AS period_coupon_pay_amount
        FROM log_bill lb
        LEFT JOIN pay_bill pb ON pb.billno = lb.billno
        LEFT JOIN sales_bill sb ON sb.billno = lb.billno
        CROSS JOIN period_pay pp
        """,
        params,
    )

    payment_methods = _rows(
        db,
        f"""
        WITH matched_logs AS (
          SELECT
            h.billno,
            l.tcflzy,
            l.tcflmoney,
            l.tcflsyjtrace,
            COALESCE(NULLIF(l.tcfljetype, ''), '未标识') AS coupon_type
          FROM tktcardfqlog l
          JOIN salehead h
            ON l.tcflmkt = h.mkt
           AND l.tcflsyjid = h.syjh
           AND l.tcflinvno ~ '^[0-9]+$'
           AND h.fphm = l.tcflinvno::numeric
          WHERE {log_filter}
        ),
        coupon_logs AS (
          SELECT
            coupon_type,
            COUNT(*) AS log_count,
            SUM({_issued_amount_sql()}) AS issued_log_amount,
            SUM(CASE WHEN tcflzy = 'O' THEN ABS(COALESCE(tcflmoney, 0)) WHEN tcflzy = 'U' THEN -ABS(COALESCE(tcflmoney, 0)) ELSE 0 END) AS consumed_log_amount
          FROM matched_logs
          GROUP BY coupon_type
        ),
        pay_trace AS (
          SELECT DISTINCT billno, tcflsyjtrace, coupon_type
          FROM matched_logs
          WHERE tcflzy = 'O' AND tcflsyjtrace IS NOT NULL
        )
        SELECT
          p.paycode,
          COALESCE(NULLIF(p.payname, ''), '未命名') AS payname,
          pt.coupon_type,
          COUNT(*) AS payment_count,
          SUM(COALESCE(p.je, 0)) AS payment_amount,
          COALESCE(MAX(cl.log_count), 0) AS coupon_log_count,
          COALESCE(MAX(cl.issued_log_amount), 0) AS issued_log_amount,
          COALESCE(MAX(cl.consumed_log_amount), 0) AS consumed_log_amount
        FROM salepay p
        JOIN pay_trace pt
          ON pt.billno = p.billno
         AND p.batch = pt.tcflsyjtrace::varchar
        LEFT JOIN coupon_logs cl ON cl.coupon_type = pt.coupon_type
        WHERE p.paycode IN ('0500', '0580')
        GROUP BY p.paycode, COALESCE(NULLIF(p.payname, ''), '未命名'), pt.coupon_type
        ORDER BY payment_amount DESC
        LIMIT :limit
        """,
        params,
    )

    departments = _rows(
        db,
        f"""
        WITH matched_bills AS (
          SELECT DISTINCT h.billno
          FROM tktcardfqlog l
          JOIN salehead h
            ON l.tcflmkt = h.mkt
           AND l.tcflsyjid = h.syjh
           AND l.tcflinvno ~ '^[0-9]+$'
           AND h.fphm = l.tcflinvno::numeric
          WHERE {log_filter}
        ),
        matched_logs AS (
          SELECT
            h.billno,
            l.tcflzy,
            l.tcflmoney,
            l.tcflsyjtrace
          FROM tktcardfqlog l
          JOIN salehead h
            ON l.tcflmkt = h.mkt
           AND l.tcflsyjid = h.syjh
           AND l.tcflinvno ~ '^[0-9]+$'
           AND h.fphm = l.tcflinvno::numeric
          WHERE {log_filter}
        ),
        pay_bill AS (
          SELECT
            p.billno,
            SUM(COALESCE(p.je, 0)) AS coupon_pay_amount
          FROM salepay p
          JOIN matched_logs ml
            ON ml.billno = p.billno
           AND ml.tcflzy = 'O'
           AND p.batch = ml.tcflsyjtrace::varchar
          WHERE p.paycode IN ('0500', '0580')
          GROUP BY p.billno
        ),
        log_bill AS (
          SELECT
            billno,
            SUM({_issued_amount_sql()}) AS issued_log_amount,
            SUM(CASE WHEN tcflzy = 'O' THEN ABS(COALESCE(tcflmoney, 0)) WHEN tcflzy = 'U' THEN -ABS(COALESCE(tcflmoney, 0)) ELSE 0 END) AS consumed_log_amount
          FROM matched_logs
          GROUP BY billno
        ),
        {_supplier_discount_cte()},
        manaframe_groups AS (
          SELECT
            mf.mfcode AS group_code,
            mf.mfcname AS group_name,
            dept.mfcode AS department_code,
            dept.mfcname AS department_name
          FROM manaframe mf
          LEFT JOIN manaframe dept
            ON UPPER(TRIM(COALESCE(mf.mfpcode, ''))) = UPPER(TRIM(COALESCE(dept.mfcode, '')))
        ),
        sales_group AS (
          SELECT
            s.sglbillno AS billno,
            COALESCE(NULLIF(cg.department_code, ''), '未归属') AS department_code,
            COALESCE(NULLIF(cg.department_name, ''), '未归属部门') AS department_name,
            COALESCE(NULLIF(cg.group_code, ''), COALESCE(NULLIF(s.sglmfid, ''), '未归属')) AS group_code,
            COALESCE(NULLIF(cg.group_name, ''), COALESCE(NULLIF(s.sglmfid, ''), '未归属柜组')) AS group_name,
            SUM(COALESCE(s.sglxssr, 0)) AS sales_amount,
            SUM(COALESCE(s.sgln13, 0)) AS sales_cost,
            SUM(COALESCE(s.sgln2, 0)) AS gross_profit,
            SUM(COALESCE(s.sglnetml, s.sgln2, 0)) AS net_profit,
            SUM(COALESCE(s.sglsqje, 0)) AS received_coupon_amount,
            SUM(COALESCE(s.sglfqje, 0)) AS issued_coupon_amount,
            SUM(COALESCE(s.sglthss, 0)) AS return_loss,
            COALESCE(MAX(sd.pay_discount_amount), 0) AS pay_discount_amount,
            COALESCE(MAX(sd.supplier_discount_amount), 0) AS supplier_discount_amount,
            COALESCE(MAX(sd.shop_discount_amount), 0) AS shop_discount_amount
          FROM salegoodslist s
          JOIN matched_bills mb ON mb.billno = s.sglbillno
          LEFT JOIN manaframe_groups cg ON UPPER(TRIM(COALESCE(cg.group_code, ''))) = UPPER(TRIM(COALESCE(s.sglmfid, '')))
          LEFT JOIN supplier_discount sd ON sd.billno = s.sglbillno AND UPPER(TRIM(COALESCE(sd.group_code, ''))) = UPPER(TRIM(COALESCE(s.sglmfid, '')))
          WHERE 1=1 {_sales_department_exclusion_sql("cg")}
          GROUP BY 1, 2, 3, 4, 5
        ),
        bill_totals AS (
          SELECT
            billno,
            SUM(sales_amount) AS bill_sales_amount,
            COUNT(DISTINCT department_code) AS bill_department_count,
            COUNT(DISTINCT group_code) AS bill_group_count
          FROM sales_group
          GROUP BY billno
        ),
        allocated AS (
          SELECT
            sg.*,
            CASE
              WHEN COALESCE(bt.bill_sales_amount, 0) <> 0 THEN sg.sales_amount / bt.bill_sales_amount
              ELSE 0
            END AS allocation_ratio,
            COALESCE(pb.coupon_pay_amount, 0) AS bill_coupon_pay_amount,
            COALESCE(lb.issued_log_amount, 0) AS bill_issued_log_amount,
            COALESCE(lb.consumed_log_amount, 0) AS bill_consumed_log_amount,
            bt.bill_department_count,
            bt.bill_group_count
          FROM sales_group sg
          JOIN bill_totals bt ON bt.billno = sg.billno
          LEFT JOIN pay_bill pb ON pb.billno = sg.billno
          LEFT JOIN log_bill lb ON lb.billno = sg.billno
        )
        SELECT
          department_code,
          department_name,
          {_code_name_display_sql("department_code", "department_name")} AS department_display,
          group_code,
          group_name,
          {_code_name_display_sql("group_code", "group_name")} AS group_display,
          COUNT(DISTINCT billno) AS ticket_count,
          COUNT(DISTINCT CASE WHEN bill_department_count > 1 THEN billno END) AS cross_department_ticket_count,
          COUNT(DISTINCT CASE WHEN bill_group_count > 1 THEN billno END) AS cross_group_ticket_count,
          SUM(sales_amount) AS sales_amount,
          SUM(sales_cost) AS sales_cost,
          SUM(gross_profit) AS gross_profit,
          SUM(net_profit) AS net_profit,
          SUM(received_coupon_amount) AS received_coupon_amount,
          SUM(issued_coupon_amount) AS issued_coupon_amount,
          SUM(return_loss) AS return_loss,
          SUM(pay_discount_amount) AS pay_discount_amount,
          SUM(supplier_discount_amount) AS supplier_discount_amount,
          SUM(shop_discount_amount) AS shop_discount_amount,
          SUM(bill_coupon_pay_amount * allocation_ratio) AS allocated_coupon_pay_amount,
          SUM(bill_issued_log_amount * allocation_ratio) AS allocated_issued_log_amount,
          SUM(bill_consumed_log_amount * allocation_ratio) AS allocated_consumed_log_amount
        FROM allocated
        GROUP BY 1, 2, 3, 4, 5, 6
        ORDER BY allocated_coupon_pay_amount DESC, sales_amount DESC
        LIMIT :limit
        """,
        params,
    )

    products = _rows(
        db,
        f"""
        WITH matched_bills AS (
          SELECT DISTINCT h.billno
          FROM tktcardfqlog l
          JOIN salehead h
            ON l.tcflmkt = h.mkt
           AND l.tcflsyjid = h.syjh
           AND l.tcflinvno ~ '^[0-9]+$'
           AND h.fphm = l.tcflinvno::numeric
          WHERE {log_filter}
        )
        SELECT
          s.sglgdid AS goods_code,
          COALESCE(NULLIF(gb.gbcname, ''), s.sglgdid) AS goods_name,
          s.sglppcode AS brand_code,
          COALESCE(NULLIF(cb.cbcname, ''), '') AS brand_name,
          {_code_name_display_sql("s.sglppcode", "cb.cbcname")} AS brand_display,
          s.sglcatid AS category_code,
          COALESCE(NULLIF(gc.catcname, ''), '') AS category_name,
          {_code_name_display_sql("s.sglcatid", "gc.catcname")} AS category_display,
          COUNT(DISTINCT s.sglbillno) AS ticket_count,
          SUM(COALESCE(s.sglsl, 0)) AS quantity,
          SUM(COALESCE(s.sglxssr, 0)) AS sales_amount,
          SUM(COALESCE(s.sgln2, 0)) AS gross_profit,
          SUM(COALESCE(s.sglnetml, s.sgln2, 0)) AS net_profit,
          SUM(COALESCE(s.sglsqje, 0)) AS received_coupon_amount
        FROM salegoodslist s
        JOIN matched_bills mb ON mb.billno = s.sglbillno
        LEFT JOIN goodsbase gb ON UPPER(TRIM(COALESCE(gb.gbid, ''))) = UPPER(TRIM(COALESCE(s.sglgdid, '')))
        {_brand_join_sql("s", "cb")}
        {_category_join_sql("s", "gc")}
        GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
        ORDER BY sales_amount DESC
        LIMIT :limit
        """,
        params,
    )

    members = _rows(
        db,
        f"""
        WITH matched_bills AS (
          SELECT DISTINCT h.billno, NULLIF(h.hykh, '') AS member_no
          FROM tktcardfqlog l
          JOIN salehead h
            ON l.tcflmkt = h.mkt
           AND l.tcflsyjid = h.syjh
           AND l.tcflinvno ~ '^[0-9]+$'
           AND h.fphm = l.tcflinvno::numeric
          WHERE {log_filter}
        ),
        sales_bill AS (
          SELECT
            s.sglbillno AS billno,
            SUM(COALESCE(s.sglxssr, 0)) AS sales_amount,
            SUM(COALESCE(s.sgln2, 0)) AS gross_profit,
            SUM(COALESCE(s.sglnetml, s.sgln2, 0)) AS net_profit
          FROM salegoodslist s
          JOIN matched_bills mb ON mb.billno = s.sglbillno
          GROUP BY s.sglbillno
        )
        SELECT
          COALESCE(NULLIF(m.customer_level, ''), '未识别') AS customer_level,
          COALESCE(NULLIF(m.regist_channel, ''), '未知') AS regist_channel,
          COALESCE(NULLIF(m.customer_status, ''), '未知') AS customer_status,
          COUNT(DISTINCT mb.member_no) AS member_count,
          COUNT(DISTINCT mb.billno) AS ticket_count,
          SUM(COALESCE(sb.sales_amount, 0)) AS sales_amount,
          SUM(COALESCE(sb.gross_profit, 0)) AS gross_profit,
          SUM(COALESCE(sb.net_profit, 0)) AS net_profit
        FROM matched_bills mb
        LEFT JOIN sales_bill sb ON sb.billno = mb.billno
        LEFT JOIN fj_dw_member_dim m ON UPPER(TRIM(COALESCE(m.customer_no, ''))) = UPPER(TRIM(COALESCE(mb.member_no, '')))
        GROUP BY 1, 2, 3
        ORDER BY sales_amount DESC
        LIMIT :limit
        """,
        params,
    )

    quality = _one(
        db,
        f"""
        WITH raw_logs AS (
          SELECT l.*
          FROM tktcardfqlog l
          WHERE {log_filter}
        ),
        matched_logs AS (
          SELECT l.tcflseqno, l.tcflzy, l.tcflsyjtrace, h.billno
          FROM raw_logs l
          JOIN salehead h
            ON l.tcflmkt = h.mkt
           AND l.tcflsyjid = h.syjh
           AND l.tcflinvno ~ '^[0-9]+$'
           AND h.fphm = l.tcflinvno::numeric
        ),
        period_pay AS (
          SELECT p.billno, p.rowno, p.batch
          FROM salepay p
          JOIN salehead h ON h.billno = p.billno
          WHERE p.paycode IN ('0500', '0580')
            AND {period_filter}
        ),
        period_coupon_logs AS (
          SELECT l.tcflvipno, l.tcflsyjtrace
          FROM tktcardfqlog l
          WHERE l.tcflsyjtrace IS NOT NULL
        )
        SELECT
          (SELECT COUNT(*) FROM raw_logs) AS raw_log_count,
          (SELECT COUNT(*) FROM matched_logs) AS matched_log_count,
          (SELECT COUNT(*) FROM raw_logs) - (SELECT COUNT(*) FROM matched_logs) AS unmatched_log_count,
          (SELECT COUNT(*) FROM period_pay) AS period_coupon_payment_count,
          (
            SELECT COUNT(*)
            FROM period_pay pp
            WHERE NOT EXISTS (
              SELECT 1
              FROM period_coupon_logs pcl
              WHERE pp.batch = pcl.tcflsyjtrace::varchar
            )
          ) AS period_payment_without_log_count
        """,
        params,
    )

    return {
        "activity": activity,
        "summary": summary,
        "payment_methods": payment_methods,
        "departments": departments,
        "products": products,
        "members": members,
        "quality": quality,
    }


@router.get("/coupon-type-departments")
async def coupon_type_departments(
    activity_id: str | None = Query(None),
    scope: str = Query("activity", pattern="^(activity|standalone|all)$"),
    coupon_type: str = Query(...),
    department_code: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, ACTIVITY_ANALYSIS_PERMISSION)
    _ensure_required_tables(db)

    business_scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    params: dict[str, Any] = {}
    activity_scope_sql = _activity_scope_filter_sql(db, business_scope, params, alias="p", prefix="coupon_depts")
    log_filter, log_params = _activity_filter(activity_id, start_date, end_date, scope, activity_scope_sql)
    params.update(log_params)
    coupon_filter, coupon_params = _coupon_type_filter(coupon_type)
    params.update(coupon_params)
    params.update({"department_code": department_code, "limit": limit})
    level_filter = "AND a.department_code = :department_code" if department_code else ""
    group_select = (
        f"a.group_code, a.group_name, {_code_name_display_sql('a.group_code', 'a.group_name')} AS group_display,"
        if department_code
        else "NULL::varchar AS group_code, NULL::varchar AS group_name, NULL::varchar AS group_display,"
    )
    group_by = "1, 2, 3, 4, 5, 6" if department_code else "1, 2, 3"

    return _rows(
        db,
        f"""
        WITH matched_logs AS (
          SELECT
            h.billno,
            l.tcflzy,
            l.tcflmoney,
            l.tcflsyjtrace
          FROM tktcardfqlog l
          JOIN salehead h
            ON l.tcflmkt = h.mkt
           AND l.tcflsyjid = h.syjh
           AND l.tcflinvno ~ '^[0-9]+$'
           AND h.fphm = l.tcflinvno::numeric
          WHERE {log_filter}
            {coupon_filter}
        ),
        pay_bill AS (
          SELECT
            p.billno,
            SUM(COALESCE(p.je, 0)) AS coupon_pay_amount
          FROM salepay p
          JOIN matched_logs ml
            ON ml.billno = p.billno
           AND ml.tcflzy = 'O'
           AND p.batch = ml.tcflsyjtrace::varchar
          WHERE p.paycode IN ('0500', '0580')
          GROUP BY p.billno
        ),
        log_bill AS (
          SELECT
            billno,
            SUM({_issued_amount_sql()}) AS issued_log_amount,
            SUM(CASE WHEN tcflzy = 'O' THEN ABS(COALESCE(tcflmoney, 0)) WHEN tcflzy = 'U' THEN -ABS(COALESCE(tcflmoney, 0)) ELSE 0 END) AS consumed_log_amount
          FROM matched_logs
          GROUP BY billno
        ),
        {_supplier_discount_cte("AND COALESCE(sgpqtype, '') = :coupon_type")},
        manaframe_groups AS (
          SELECT
            mf.mfcode AS group_code,
            mf.mfcname AS group_name,
            dept.mfcode AS department_code,
            dept.mfcname AS department_name
          FROM manaframe mf
          LEFT JOIN manaframe dept
            ON UPPER(TRIM(COALESCE(mf.mfpcode, ''))) = UPPER(TRIM(COALESCE(dept.mfcode, '')))
        ),
        sales_group AS (
          SELECT
            s.sglbillno AS billno,
            COALESCE(NULLIF(cg.department_code, ''), '未归属') AS department_code,
            COALESCE(NULLIF(cg.department_name, ''), '未归属部门') AS department_name,
            COALESCE(NULLIF(cg.group_code, ''), COALESCE(NULLIF(s.sglmfid, ''), '未归属')) AS group_code,
            COALESCE(NULLIF(cg.group_name, ''), COALESCE(NULLIF(s.sglmfid, ''), '未归属柜组')) AS group_name,
            SUM(COALESCE(s.sglxssr, 0)) AS sales_amount,
            SUM(COALESCE(s.sgln13, 0)) AS sales_cost,
            SUM(COALESCE(s.sgln2, 0)) AS gross_profit,
            SUM(COALESCE(s.sglnetml, s.sgln2, 0)) AS net_profit,
            SUM(COALESCE(s.sglsqje, 0)) AS received_coupon_amount,
            SUM(COALESCE(s.sglfqje, 0)) AS issued_coupon_amount,
            SUM(COALESCE(s.sglthss, 0)) AS return_loss,
            COALESCE(MAX(sd.pay_discount_amount), 0) AS pay_discount_amount,
            COALESCE(MAX(sd.supplier_discount_amount), 0) AS supplier_discount_amount,
            COALESCE(MAX(sd.shop_discount_amount), 0) AS shop_discount_amount
          FROM salegoodslist s
          JOIN (SELECT DISTINCT billno FROM matched_logs) mb ON mb.billno = s.sglbillno
          LEFT JOIN manaframe_groups cg ON UPPER(TRIM(COALESCE(cg.group_code, ''))) = UPPER(TRIM(COALESCE(s.sglmfid, '')))
          LEFT JOIN supplier_discount sd ON sd.billno = s.sglbillno AND UPPER(TRIM(COALESCE(sd.group_code, ''))) = UPPER(TRIM(COALESCE(s.sglmfid, '')))
          WHERE 1=1 {_sales_department_exclusion_sql("cg")}
          GROUP BY 1, 2, 3, 4, 5
        ),
        bill_totals AS (
          SELECT
            billno,
            SUM(sales_amount) AS bill_sales_amount,
            COUNT(DISTINCT department_code) AS bill_department_count,
            COUNT(DISTINCT group_code) AS bill_group_count
          FROM sales_group
          GROUP BY billno
        ),
        allocated AS (
          SELECT
            sg.*,
            CASE
              WHEN COALESCE(bt.bill_sales_amount, 0) <> 0 THEN sg.sales_amount / bt.bill_sales_amount
              ELSE 0
            END AS allocation_ratio,
            COALESCE(pb.coupon_pay_amount, 0) AS bill_coupon_pay_amount,
            COALESCE(lb.issued_log_amount, 0) AS bill_issued_log_amount,
            COALESCE(lb.consumed_log_amount, 0) AS bill_consumed_log_amount,
            bt.bill_department_count,
            bt.bill_group_count
          FROM sales_group sg
          JOIN bill_totals bt ON bt.billno = sg.billno
          LEFT JOIN pay_bill pb ON pb.billno = sg.billno
          LEFT JOIN log_bill lb ON lb.billno = sg.billno
        )
        SELECT
          a.department_code,
          a.department_name,
          {_code_name_display_sql("a.department_code", "a.department_name")} AS department_display,
          {group_select}
          COUNT(DISTINCT a.billno) AS ticket_count,
          COUNT(DISTINCT CASE WHEN a.bill_department_count > 1 THEN a.billno END) AS cross_department_ticket_count,
          COUNT(DISTINCT CASE WHEN a.bill_group_count > 1 THEN a.billno END) AS cross_group_ticket_count,
          SUM(a.sales_amount) AS sales_amount,
          SUM(a.sales_cost) AS sales_cost,
          SUM(a.gross_profit) AS gross_profit,
          SUM(a.net_profit) AS net_profit,
          SUM(a.received_coupon_amount) AS received_coupon_amount,
          SUM(a.issued_coupon_amount) AS issued_coupon_amount,
          SUM(a.return_loss) AS return_loss,
          SUM(a.pay_discount_amount) AS pay_discount_amount,
          SUM(a.supplier_discount_amount) AS supplier_discount_amount,
          SUM(a.shop_discount_amount) AS shop_discount_amount,
          SUM(a.bill_coupon_pay_amount * a.allocation_ratio) AS allocated_coupon_pay_amount,
          SUM(a.bill_issued_log_amount * a.allocation_ratio) AS allocated_issued_log_amount,
          SUM(a.bill_consumed_log_amount * a.allocation_ratio) AS allocated_consumed_log_amount
        FROM allocated a
        WHERE 1=1 {level_filter}
        GROUP BY {group_by}
        ORDER BY allocated_coupon_pay_amount DESC, sales_amount DESC
        LIMIT :limit
        """,
        params,
    )


@router.get("/department-tickets")
async def department_tickets(
    activity_id: str | None = Query(None),
    scope: str = Query("activity", pattern="^(activity|standalone|all)$"),
    department_code: str = Query(...),
    group_code: str = Query(...),
    coupon_type: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, ACTIVITY_ANALYSIS_PERMISSION)
    _ensure_required_tables(db)

    business_scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    params: dict[str, Any] = {}
    activity_scope_sql = _activity_scope_filter_sql(db, business_scope, params, alias="p", prefix="dept_tickets")
    log_filter, log_params = _activity_filter(activity_id, start_date, end_date, scope, activity_scope_sql)
    params.update(log_params)
    coupon_filter, coupon_params = _coupon_type_filter(coupon_type)
    params.update(coupon_params)
    params.setdefault("coupon_type", None)
    params.update({"department_code": department_code, "group_code": group_code, "limit": limit})

    return _rows(
        db,
        f"""
        WITH matched_logs AS (
          SELECT
            h.billno,
            l.tcflzy,
            l.tcflmoney,
            l.tcflsyjtrace
          FROM tktcardfqlog l
          JOIN salehead h
            ON l.tcflmkt = h.mkt
           AND l.tcflsyjid = h.syjh
           AND l.tcflinvno ~ '^[0-9]+$'
           AND h.fphm = l.tcflinvno::numeric
          WHERE {log_filter}
            {coupon_filter}
        ),
        pay_bill AS (
          SELECT
            p.billno,
            SUM(COALESCE(p.je, 0)) AS coupon_pay_amount
          FROM salepay p
          JOIN matched_logs ml
            ON ml.billno = p.billno
           AND ml.tcflzy = 'O'
           AND p.batch = ml.tcflsyjtrace::varchar
          WHERE p.paycode IN ('0500', '0580')
          GROUP BY p.billno
        ),
        log_bill AS (
          SELECT
            billno,
            SUM({_issued_amount_sql()}) AS issued_log_amount,
            SUM(CASE WHEN tcflzy = 'O' THEN ABS(COALESCE(tcflmoney, 0)) WHEN tcflzy = 'U' THEN -ABS(COALESCE(tcflmoney, 0)) ELSE 0 END) AS consumed_log_amount
          FROM matched_logs
          GROUP BY billno
        ),
        {_supplier_discount_cte("AND (:coupon_type IS NULL OR COALESCE(sgpqtype, '') = :coupon_type)")},
        manaframe_groups AS (
          SELECT
            mf.mfcode AS group_code,
            mf.mfcname AS group_name,
            dept.mfcode AS department_code,
            dept.mfcname AS department_name
          FROM manaframe mf
          LEFT JOIN manaframe dept
            ON UPPER(TRIM(COALESCE(mf.mfpcode, ''))) = UPPER(TRIM(COALESCE(dept.mfcode, '')))
        ),
        sales_group AS (
          SELECT
            s.sglbillno AS billno,
            COALESCE(NULLIF(cg.department_code, ''), '未归属') AS department_code,
            COALESCE(NULLIF(cg.department_name, ''), '未归属部门') AS department_name,
            COALESCE(NULLIF(cg.group_code, ''), COALESCE(NULLIF(s.sglmfid, ''), '未归属')) AS group_code,
            COALESCE(NULLIF(cg.group_name, ''), COALESCE(NULLIF(s.sglmfid, ''), '未归属柜组')) AS group_name,
            SUM(COALESCE(s.sglxssr, 0)) AS sales_amount,
            SUM(COALESCE(s.sgln13, 0)) AS sales_cost,
            SUM(COALESCE(s.sgln2, 0)) AS gross_profit,
            SUM(COALESCE(s.sglnetml, s.sgln2, 0)) AS net_profit,
            SUM(COALESCE(s.sglsqje, 0)) AS received_coupon_amount,
            SUM(COALESCE(s.sglfqje, 0)) AS issued_coupon_amount,
            SUM(COALESCE(s.sglthss, 0)) AS return_loss,
            COALESCE(MAX(sd.pay_discount_amount), 0) AS pay_discount_amount,
            COALESCE(MAX(sd.supplier_discount_amount), 0) AS supplier_discount_amount,
            COALESCE(MAX(sd.shop_discount_amount), 0) AS shop_discount_amount
          FROM salegoodslist s
          JOIN (SELECT DISTINCT billno FROM matched_logs) mb ON mb.billno = s.sglbillno
          LEFT JOIN manaframe_groups cg ON UPPER(TRIM(COALESCE(cg.group_code, ''))) = UPPER(TRIM(COALESCE(s.sglmfid, '')))
          LEFT JOIN supplier_discount sd ON sd.billno = s.sglbillno AND UPPER(TRIM(COALESCE(sd.group_code, ''))) = UPPER(TRIM(COALESCE(s.sglmfid, '')))
          WHERE 1=1 {_sales_department_exclusion_sql("cg")}
          GROUP BY 1, 2, 3, 4, 5
        ),
        bill_totals AS (
          SELECT
            billno,
            SUM(sales_amount) AS bill_sales_amount,
            COUNT(DISTINCT department_code) AS bill_department_count,
            COUNT(DISTINCT group_code) AS bill_group_count
          FROM sales_group
          GROUP BY billno
        ),
        allocated AS (
          SELECT
            sg.*,
            CASE
              WHEN COALESCE(bt.bill_sales_amount, 0) <> 0 THEN sg.sales_amount / bt.bill_sales_amount
              ELSE 0
            END AS allocation_ratio,
            COALESCE(pb.coupon_pay_amount, 0) AS bill_coupon_pay_amount,
            COALESCE(lb.issued_log_amount, 0) AS bill_issued_log_amount,
            COALESCE(lb.consumed_log_amount, 0) AS bill_consumed_log_amount,
            bt.bill_sales_amount,
            bt.bill_department_count,
            bt.bill_group_count
          FROM sales_group sg
          JOIN bill_totals bt ON bt.billno = sg.billno
          LEFT JOIN pay_bill pb ON pb.billno = sg.billno
          LEFT JOIN log_bill lb ON lb.billno = sg.billno
        )
        SELECT
          h.billno,
          h.rqsj AS sale_time,
          h.mkt AS market_code,
          h.syjh AS cashier_no,
          h.fphm AS invoice_no,
          h.hykh AS member_no,
          a.department_code,
          a.department_name,
          a.group_code,
          a.group_name,
          a.sales_amount,
          a.sales_cost,
          a.gross_profit,
          a.net_profit,
          a.received_coupon_amount,
          a.issued_coupon_amount,
          a.return_loss,
          a.pay_discount_amount,
          a.supplier_discount_amount,
          a.shop_discount_amount,
          a.bill_coupon_pay_amount * a.allocation_ratio AS allocated_coupon_pay_amount,
          a.bill_issued_log_amount * a.allocation_ratio AS allocated_issued_log_amount,
          a.bill_consumed_log_amount * a.allocation_ratio AS allocated_consumed_log_amount,
          a.allocation_ratio,
          a.bill_sales_amount,
          a.bill_department_count,
          a.bill_group_count
        FROM allocated a
        JOIN salehead h ON h.billno = a.billno
        WHERE a.department_code = :department_code
          AND a.group_code = :group_code
        ORDER BY h.rqsj DESC, h.billno DESC
        LIMIT :limit
        """,
        params,
    )


@router.get("/coupon-summary")
async def coupon_summary(
    activity_id: str | None = Query(None, description="活动档期编码 tktpopinfo.tpiid"),
    scope: str = Query("activity", pattern="^(activity|standalone|all)$", description="activity 活动档期券；standalone 非档期券；all 全部卡券"),
    start_date: str | None = Query(None, description="日志日期起 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="日志日期止 YYYY-MM-DD"),
    limit: int = Query(100, ge=1, le=300),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, ACTIVITY_ANALYSIS_PERMISSION)
    _ensure_required_tables(db)

    business_scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    params: dict[str, Any] = {"limit": limit}
    activity_scope_sql = _activity_scope_filter_sql(db, business_scope, params, alias="p", prefix="coupon_summary")
    log_filter, log_params = _activity_filter(activity_id, start_date, end_date, scope, activity_scope_sql)
    params.update(log_params)

    return _rows(
        db,
        f"""
        WITH coupon_pay AS (
          SELECT
            billno,
            batch,
            SUM(COALESCE(je, 0)) AS coupon_pay_amount
          FROM salepay
          WHERE paycode IN ('0500', '0580')
          GROUP BY billno, batch
        ),
        log_rows AS (
          SELECT
            l.tcflseqno AS flow_id,
            l.tcfldate AS flow_date,
            l.tcflzy AS action_code,
            {_case_expr("l.tcflzy", ACTION_LABELS, "'未知动作'")} AS action_name,
            l.tcflsource AS source_code,
            {_case_expr("l.tcflsource", SOURCE_LABELS, "'未知来源'")} AS source_name,
            COALESCE(NULLIF(l.tcfljetype, ''), '未标识') AS coupon_type,
            l.tcflvipno AS member_no,
            l.tcflqno AS coupon_no,
            l.tcflmoney AS raw_flow_amount,
            {ACTION_AMOUNT_SQL} AS flow_amount,
            {_issued_amount_sql("l")} AS issued_log_amount,
            CASE
              WHEN l.tcflzy = 'O' THEN ABS(COALESCE(l.tcflmoney, 0))
              WHEN l.tcflzy = 'U' THEN -ABS(COALESCE(l.tcflmoney, 0))
              ELSE 0
            END AS consumed_log_amount,
            h.billno,
            cp.coupon_pay_amount
          FROM tktcardfqlog l
          LEFT JOIN salehead h
            ON l.tcflmkt = h.mkt
           AND l.tcflsyjid = h.syjh
           AND l.tcflinvno ~ '^[0-9]+$'
           AND h.fphm = l.tcflinvno::numeric
          LEFT JOIN coupon_pay cp
            ON cp.billno = h.billno
           AND cp.batch = l.tcflsyjtrace::varchar
          WHERE {log_filter}
        )
        SELECT
          action_code,
          action_name,
          source_code,
          source_name,
          coupon_type,
          MIN(flow_date) AS first_flow_date,
          MAX(flow_date) AS last_flow_date,
          COUNT(*) AS flow_count,
          COUNT(DISTINCT NULLIF(member_no, '')) AS member_count,
          COUNT(DISTINCT NULLIF(coupon_no, '')) AS coupon_count,
          COUNT(DISTINCT billno) AS ticket_count,
          SUM(COALESCE(raw_flow_amount, 0)) AS raw_flow_amount,
          SUM(COALESCE(flow_amount, 0)) AS flow_amount,
          SUM(COALESCE(issued_log_amount, 0)) AS issued_log_amount,
          SUM(COALESCE(consumed_log_amount, 0)) AS consumed_log_amount,
          SUM(CASE WHEN action_code = 'O' THEN COALESCE(coupon_pay_amount, 0) ELSE 0 END) AS coupon_pay_amount
        FROM log_rows
        GROUP BY action_code, action_name, source_code, source_name, coupon_type
        ORDER BY
          CASE
            WHEN action_code = 'F' THEN 1
            WHEN action_code = 'O' THEN 2
            WHEN action_code = 'U' THEN 3
            WHEN action_code IN ('P', 'K', 'V') THEN 4
            ELSE 9
          END,
          ABS(SUM(COALESCE(flow_amount, 0))) DESC,
          action_code,
          coupon_type
        LIMIT :limit
        """,
        params,
    )


@router.get("/coupon-flows")
async def coupon_flows(
    activity_id: str | None = Query(None, description="活动档期编码 tktpopinfo.tpiid"),
    scope: str = Query("activity", pattern="^(activity|standalone|all)$", description="activity 活动档期券；standalone 非档期券；all 全部卡券"),
    start_date: str | None = Query(None, description="日志日期起 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="日志日期止 YYYY-MM-DD"),
    keyword: str | None = Query(None, description="券号/会员/小票/流水搜索"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, ACTIVITY_ANALYSIS_PERMISSION)
    _ensure_required_tables(db)

    business_scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    params: dict[str, Any] = {}
    activity_scope_sql = _activity_scope_filter_sql(db, business_scope, params, alias="p", prefix="flows")
    log_filter, log_params = _activity_filter(activity_id, start_date, end_date, scope, activity_scope_sql)
    params.update(log_params)
    params.update({"limit": limit, "offset": offset})
    keyword_filter = ""
    if keyword:
        params["keyword"] = f"%{keyword.strip()}%"
        keyword_filter = """
          AND (
            l.tcflvipno ILIKE :keyword
            OR l.tcflqno ILIKE :keyword
            OR l.tcflinvno ILIKE :keyword
            OR h.billno::varchar ILIKE :keyword
            OR h.hykh ILIKE :keyword
          )
        """

    return _rows(
        db,
        f"""
        WITH coupon_pay AS (
          SELECT
            billno,
            batch,
            SUM(COALESCE(je, 0)) AS coupon_pay_amount,
            STRING_AGG(DISTINCT COALESCE(NULLIF(payname, ''), paycode), '、') AS coupon_pay_names
          FROM salepay
          WHERE paycode IN ('0500', '0580')
          GROUP BY billno, batch
        ),
        sale_bill AS (
          SELECT
            sglbillno AS billno,
            SUM(COALESCE(sglxssr, 0)) AS sales_amount,
            SUM(COALESCE(sgln2, 0)) AS gross_profit,
            SUM(COALESCE(sglnetml, sgln2, 0)) AS net_profit
          FROM salegoodslist
          GROUP BY sglbillno
        )
        SELECT
          l.tcflseqno AS flow_id,
          l.tcfldate AS flow_date,
          l.tcflzy AS action_code,
          {_case_expr("l.tcflzy", ACTION_LABELS, "'未知动作'")} AS action_name,
          l.tcflsource AS source_code,
          {_case_expr("l.tcflsource", SOURCE_LABELS, "'未知来源'")} AS source_name,
          l.tcflpopid AS activity_id,
          p.tpiname AS activity_name,
          l.tcflvipno AS member_no,
          l.tcflqno AS coupon_no,
          l.tcflmoney AS raw_flow_amount,
          {ACTION_AMOUNT_SQL} AS flow_amount,
          l.tcflye AS balance_amount,
          l.tcflmkt AS market_code,
          l.tcflsyjid AS cashier_no,
          l.tcflinvno AS invoice_no,
          l.tcflsyjtrace AS trace_no,
          h.billno,
          h.rqsj AS sale_time,
          h.hykh AS sale_member_no,
          COALESCE(cp.coupon_pay_amount, 0) AS coupon_pay_amount,
          COALESCE(cp.coupon_pay_names, '') AS coupon_pay_names,
          COALESCE(sb.sales_amount, 0) AS sales_amount,
          COALESCE(sb.gross_profit, 0) AS gross_profit,
          COALESCE(sb.net_profit, 0) AS net_profit
        FROM tktcardfqlog l
        LEFT JOIN tktpopinfo p ON p.tpiid = l.tcflpopid
        LEFT JOIN salehead h
          ON l.tcflmkt = h.mkt
         AND l.tcflsyjid = h.syjh
         AND l.tcflinvno ~ '^[0-9]+$'
         AND h.fphm = l.tcflinvno::numeric
        LEFT JOIN coupon_pay cp
          ON cp.billno = h.billno
         AND cp.batch = l.tcflsyjtrace::varchar
        LEFT JOIN sale_bill sb ON sb.billno = h.billno
        WHERE {log_filter}
          {keyword_filter}
        ORDER BY l.tcfldate DESC, l.tcflseqno DESC
        LIMIT :limit OFFSET :offset
        """,
        params,
    )


@router.get("/quality-issues")
async def quality_issues(
    activity_id: str | None = Query(None, description="活动档期编码 tktpopinfo.tpiid"),
    scope: str = Query("activity", pattern="^(activity|standalone|all)$", description="activity 活动档期券；standalone 非档期券；all 全部卡券"),
    start_date: str | None = Query(None, description="日志/销售日期起 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="日志/销售日期止 YYYY-MM-DD"),
    issue_type: str = Query("unmatched_logs", description="unmatched_logs/payments_without_logs/amount_mismatch/missing_member/unassigned_activity"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, ACTIVITY_ANALYSIS_PERMISSION)
    _ensure_required_tables(db)

    business_scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    activity_scope_params: dict[str, Any] = {}
    activity_scope_sql = _activity_scope_filter_sql(db, business_scope, activity_scope_params, alias="p", prefix="quality")
    log_filter, log_params = _activity_filter(activity_id, start_date, end_date, scope, activity_scope_sql)
    period_filter, period_params = _period_filter(activity_id, start_date, end_date)
    params = {**activity_scope_params, **log_params, **period_params, "limit": limit}

    if issue_type == "unmatched_logs":
        return _rows(
            db,
            f"""
            SELECT
              l.tcflseqno AS flow_id,
              l.tcfldate AS flow_date,
              l.tcflpopid AS activity_id,
              l.tcflvipno AS member_no,
              l.tcflqno AS coupon_no,
              l.tcflmoney AS flow_amount,
              l.tcflmkt AS market_code,
              l.tcflsyjid AS cashier_no,
              l.tcflinvno AS invoice_no,
              l.tcflsyjtrace AS trace_no,
              '卡券日志无法关联小票' AS issue
            FROM tktcardfqlog l
            WHERE {log_filter}
              AND NOT EXISTS (
                SELECT 1
                FROM salehead h
                WHERE l.tcflmkt = h.mkt
                  AND l.tcflsyjid = h.syjh
                  AND l.tcflinvno ~ '^[0-9]+$'
                  AND h.fphm = l.tcflinvno::numeric
              )
            ORDER BY l.tcfldate DESC, l.tcflseqno DESC
            LIMIT :limit
            """,
            params,
        )

    if issue_type == "unassigned_activity":
        return _rows(
            db,
            f"""
            SELECT
              l.tcflseqno AS flow_id,
              l.tcfldate AS flow_date,
              l.tcflpopid AS activity_id,
              l.tcflvipno AS member_no,
              l.tcflqno AS coupon_no,
              l.tcflzy AS action_code,
              {_case_expr("l.tcflzy", ACTION_LABELS, "'未知动作'")} AS action_name,
              l.tcflsource AS source_code,
              {_case_expr("l.tcflsource", SOURCE_LABELS, "'未知来源'")} AS source_name,
              l.tcflmoney AS raw_flow_amount,
              {ACTION_AMOUNT_SQL} AS flow_amount,
              l.tcflmkt AS market_code,
              l.tcflsyjid AS cashier_no,
              l.tcflinvno AS invoice_no,
              l.tcflsyjtrace AS trace_no,
              '卡券日志无活动档期归属' AS issue
            FROM tktcardfqlog l
            WHERE (COALESCE(l.tcflpopid, '') IN ('', '0') OR NOT EXISTS (SELECT 1 FROM tktpopinfo p WHERE p.tpiid = l.tcflpopid))
              { "AND l.tcfldate >= :start_date" if start_date else "" }
              { "AND l.tcfldate <= :end_date" if end_date else "" }
            ORDER BY l.tcfldate DESC, l.tcflseqno DESC
            LIMIT :limit
            """,
            params,
        )

    if issue_type == "payments_without_logs":
        return _rows(
            db,
            f"""
            SELECT
              p.billno,
              h.rqsj AS sale_time,
              h.mkt AS market_code,
              h.syjh AS cashier_no,
              h.fphm AS invoice_no,
              h.hykh AS member_no,
              p.rowno AS payment_rowno,
              p.paycode,
              COALESCE(NULLIF(p.payname, ''), p.paycode) AS payname,
              p.payno,
              p.batch,
              p.je AS payment_amount,
              '0500/0580付款未匹配卡券流水' AS issue
            FROM salepay p
            JOIN salehead h ON h.billno = p.billno
            WHERE p.paycode IN ('0500', '0580')
              AND {period_filter}
              AND NOT EXISTS (
                SELECT 1
                FROM tktcardfqlog l
                WHERE p.batch = l.tcflsyjtrace::varchar
              )
            ORDER BY h.rqsj DESC, p.billno DESC
            LIMIT :limit
            """,
            params,
        )

    if issue_type == "amount_mismatch":
        return _rows(
            db,
            f"""
            WITH log_bill AS (
              SELECT
                h.billno,
                MIN(h.rqsj) AS sale_time,
                MIN(h.hykh) AS member_no,
                SUM(CASE WHEN l.tcflzy = 'O' THEN ABS(COALESCE(l.tcflmoney, 0)) WHEN l.tcflzy = 'U' THEN -ABS(COALESCE(l.tcflmoney, 0)) ELSE 0 END) AS log_amount
              FROM tktcardfqlog l
              JOIN salehead h
                ON l.tcflmkt = h.mkt
               AND l.tcflsyjid = h.syjh
               AND l.tcflinvno ~ '^[0-9]+$'
               AND h.fphm = l.tcflinvno::numeric
              WHERE {log_filter}
              GROUP BY h.billno
            ),
            pay_bill AS (
              SELECT p.billno, SUM(COALESCE(p.je, 0)) AS payment_amount
              FROM salepay p
              JOIN tktcardfqlog l
                ON p.batch = l.tcflsyjtrace::varchar
               AND l.tcflzy = 'O'
              JOIN salehead h
                ON l.tcflmkt = h.mkt
               AND l.tcflsyjid = h.syjh
               AND l.tcflinvno ~ '^[0-9]+$'
               AND h.fphm = l.tcflinvno::numeric
               AND h.billno = p.billno
              WHERE p.paycode IN ('0500', '0580')
                AND {log_filter}
              GROUP BY p.billno
            )
            SELECT
              lb.billno,
              lb.sale_time,
              lb.member_no,
              lb.log_amount,
              COALESCE(pb.payment_amount, 0) AS payment_amount,
              COALESCE(pb.payment_amount, 0) - lb.log_amount AS difference_amount,
              '卡券日志金额与付款金额不一致' AS issue
            FROM log_bill lb
            LEFT JOIN pay_bill pb ON pb.billno = lb.billno
            WHERE lb.log_amount <> 0
              AND ABS(COALESCE(pb.payment_amount, 0) - lb.log_amount) > 0.01
            ORDER BY ABS(COALESCE(pb.payment_amount, 0) - lb.log_amount) DESC
            LIMIT :limit
            """,
            params,
        )

    if issue_type == "missing_member":
        return _rows(
            db,
            f"""
            SELECT DISTINCT
              h.billno,
              h.rqsj AS sale_time,
              h.mkt AS market_code,
              h.syjh AS cashier_no,
              h.fphm AS invoice_no,
              h.hykh AS member_no,
              SUM(COALESCE(l.tcflmoney, 0)) AS log_amount,
              '小票无会员号' AS issue
            FROM tktcardfqlog l
            JOIN salehead h
              ON l.tcflmkt = h.mkt
             AND l.tcflsyjid = h.syjh
             AND l.tcflinvno ~ '^[0-9]+$'
             AND h.fphm = l.tcflinvno::numeric
            WHERE {log_filter}
              AND NULLIF(h.hykh, '') IS NULL
            GROUP BY h.billno, h.rqsj, h.mkt, h.syjh, h.fphm, h.hykh
            ORDER BY h.rqsj DESC, h.billno DESC
            LIMIT :limit
            """,
            params,
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="issue_type 仅支持 unmatched_logs/payments_without_logs/amount_mismatch/missing_member/unassigned_activity",
    )
