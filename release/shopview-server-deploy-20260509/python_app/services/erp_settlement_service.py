"""
ERP 联营结算单（supsettlehead 及关联表）查询。
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def _table_exists(db: Session, table_name: str) -> bool:
    row = db.execute(
        text(
            """
            SELECT EXISTS (
              SELECT 1 FROM information_schema.tables
              WHERE table_schema = 'public' AND table_name = :table_name
            ) AS ok
            """
        ),
        {"table_name": table_name},
    ).fetchone()
    return bool(row.ok) if row is not None else False


def _json_cell(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _row_dict(row: Any) -> dict[str, Any]:
    m = row._mapping
    return {k: _json_cell(m[k]) for k in m.keys()}


def _sql_expr_in_binds(
    expr_sql: str,
    values: list[str],
    param_prefix: str,
) -> tuple[str, dict[str, Any]]:
    """
    生成 expr IN (:p_0, :p_1, ...)，避免 PostgreSQL 下 ANY(:array) 与 SQLAlchemy 绑定类型不匹配。
    """
    if not values:
        return "FALSE", {}
    keys: list[str] = []
    params: dict[str, Any] = {}
    for i, v in enumerate(values):
        key = f"{param_prefix}_{i}"
        keys.append(f":{key}")
        params[key] = v
    return f"{expr_sql} IN ({', '.join(keys)})", params


def effective_settlement_group_norm(db: Session, sshbillno: str) -> str:
    """
    用于数据权限的柜组编码（大写去空格）：
    优先 supsettlehead.sshmfid，其次付款单头 suppayhead.sphmfid（经 paybatch.pbpaybillno，
    或与 sshpayno 直连）。
    """
    bill = (sshbillno or "").strip()
    if not bill or not _table_exists(db, "supsettlehead"):
        return ""

    has_sph = _table_exists(db, "suppayhead")
    has_pb = _table_exists(db, "paybatch")

    lateral_pb = ""
    if has_sph and has_pb:
        lateral_pb = """
        LEFT JOIN LATERAL (
          SELECT TRIM(aa.sphmfid::text) AS mfid
          FROM paybatch pb
          INNER JOIN suppayhead aa ON TRIM(aa.sphbillno) = TRIM(pb.pbpaybillno)
          WHERE TRIM(pb.pbjsno) = TRIM(h.sshbillno)
          ORDER BY CASE WHEN TRIM(pb.pbbilltype) = 'J' THEN 0 ELSE 1 END, pb.pbseq DESC NULLS LAST
          LIMIT 1
        ) sph_pb ON TRUE"""
    lateral_ssh = ""
    if has_sph:
        lateral_ssh = """
        LEFT JOIN LATERAL (
          SELECT TRIM(aa.sphmfid::text) AS mfid
          FROM suppayhead aa
          WHERE TRIM(aa.sphbillno) = TRIM(h.sshpayno)
          LIMIT 1
        ) sph_ssh ON TRUE"""

    parts = ["NULLIF(TRIM(h.sshmfid::text), '')"]
    if has_sph and has_pb:
        parts.append("NULLIF(TRIM(sph_pb.mfid::text), '')")
    if has_sph:
        parts.append("NULLIF(TRIM(sph_ssh.mfid::text), '')")

    eff = "TRIM(UPPER(COALESCE(" + ", ".join(parts) + ")))"
    sql = f"""
    SELECT {eff} AS g
    FROM supsettlehead h
    {lateral_pb}
    {lateral_ssh}
    WHERE TRIM(h.sshbillno) = :b
    LIMIT 1
    """
    row = db.execute(text(sql), {"b": bill}).fetchone()
    if row is None:
        return ""
    g = row._mapping.get("g")
    if g is None:
        return ""
    s = str(g).strip()
    return s


def list_joint_settlements(
    db: Session,
    *,
    page: int,
    page_size: int,
    wmid: str | None,
    mkt: str | None,
    date_from: str | None,
    date_to: str | None,
    keyword: str | None,
    scope_all_access: bool = False,
    scope_group_allow: frozenset[str] | None = None,
    scope_group_deny: frozenset[str] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """
    联营结算单分页列表。
    - wmid: 经营方式过滤；常见联营单字符码，空字符串表示不过滤。
    - 柜组数据权限：scope_all_access 为 True 时不按柜组过滤；否则仅 dimension「group」允许的 ERP 柜组编码；
      deny 优先。非管理员且无允许柜组时应由路由提前返回空列表。
    """
    if not _table_exists(db, "supsettlehead"):
        return [], 0

    if (
        not scope_all_access
        and scope_group_allow is not None
        and len(scope_group_allow) == 0
    ):
        return [], 0

    conds: list[str] = ["1=1"]
    params: dict[str, Any] = {}

    if wmid is not None and wmid != "":
        conds.append("h.sshwmid = :wmid")
        params["wmid"] = wmid

    if mkt:
        conds.append("h.sshmkt ILIKE :mkt")
        params["mkt"] = f"%{mkt.strip()}%"

    if date_from:
        conds.append("h.sshdate >= CAST(:date_from AS date)")
        params["date_from"] = date_from
    if date_to:
        conds.append("h.sshdate <= CAST(:date_to AS date)")
        params["date_to"] = date_to

    has_paybatch = _table_exists(db, "paybatch")
    has_sph = _table_exists(db, "suppayhead")

    if keyword and keyword.strip():
        kw = f"%{keyword.strip()}%"
        kw_expr = [
            "h.sshbillno ILIKE :kw",
            "h.sshcontno ILIKE :kw",
            "h.sshsupid ILIKE :kw",
        ]
        if has_paybatch:
            kw_expr.append(
                "EXISTS ("
                "SELECT 1 FROM paybatch pbk "
                "WHERE TRIM(pbk.pbjsno) = TRIM(h.sshbillno) "
                "AND ("
                "TRIM(COALESCE(pbk.pbbillno, '')) ILIKE :kw "
                "OR TRIM(COALESCE(pbk.pbpaybillno, '')) ILIKE :kw"
                ")"
                ")"
            )
        if has_sph:
            kw_expr.append(
                "EXISTS ("
                "SELECT 1 FROM suppayhead sph "
                "WHERE TRIM(sph.sphbillno) = TRIM(h.sshpayno) "
                "AND TRIM(COALESCE(sph.sphbillno, '')) ILIKE :kw"
                ")"
            )
        conds.append("(" + " OR ".join(kw_expr) + ")")
        params["kw"] = kw

    has_mf = _table_exists(db, "manaframe")

    lateral_pb = ""
    if has_sph and has_paybatch:
        lateral_pb = """
        LEFT JOIN LATERAL (
          SELECT TRIM(aa.sphmfid::text) AS mfid
          FROM paybatch pb
          INNER JOIN suppayhead aa ON TRIM(aa.sphbillno) = TRIM(pb.pbpaybillno)
          WHERE TRIM(pb.pbjsno) = TRIM(h.sshbillno)
          ORDER BY CASE WHEN TRIM(pb.pbbilltype) = 'J' THEN 0 ELSE 1 END, pb.pbseq DESC NULLS LAST
          LIMIT 1
        ) sph_pb ON TRUE"""

    lateral_ssh = ""
    if has_sph:
        lateral_ssh = """
        LEFT JOIN LATERAL (
          SELECT TRIM(aa.sphmfid::text) AS mfid
          FROM suppayhead aa
          WHERE TRIM(aa.sphbillno) = TRIM(h.sshpayno)
          LIMIT 1
        ) sph_ssh ON TRUE"""

    eff_parts = ["NULLIF(TRIM(h.sshmfid::text), '')"]
    if has_sph and has_paybatch:
        eff_parts.append("NULLIF(TRIM(sph_pb.mfid::text), '')")
    if has_sph:
        eff_parts.append("NULLIF(TRIM(sph_ssh.mfid::text), '')")
    effective_upper_sql = "TRIM(UPPER(COALESCE(" + ", ".join(eff_parts) + ")))"

    mf_join = ""
    sphmfid_select = "NULL::varchar AS sphmfid"
    sphmf_disp_select = "NULL::varchar AS sphmf_department_display"

    if has_sph:
        sp_parts: list[str] = []
        if has_paybatch:
            sp_parts.append("NULLIF(TRIM(sph_pb.mfid::text), '')")
        sp_parts.append("NULLIF(TRIM(sph_ssh.mfid::text), '')")
        sphmfid_select = "TRIM(COALESCE(" + ", ".join(sp_parts) + ")) AS sphmfid"
        coalesce_sph_mf = (
            "COALESCE(NULLIF(TRIM(sph_pb.mfid::text), ''), NULLIF(TRIM(sph_ssh.mfid::text), ''))"
            if has_paybatch
            else "NULLIF(TRIM(sph_ssh.mfid::text), '')"
        )
        if has_mf:
            mf_join = f"""
            LEFT JOIN manaframe mf_sph ON TRIM(mf_sph.mfcode) = TRIM({coalesce_sph_mf})
            """
            sphmf_disp_select = f"""
            CASE WHEN mf_sph.mfcode IS NOT NULL THEN
              TRIM({coalesce_sph_mf}::text) || ' ' || COALESCE(mf_sph.mfcname::text, '')
            ELSE TRIM({coalesce_sph_mf})
            END AS sphmf_department_display
            """
        else:
            sphmf_disp_select = f"TRIM({coalesce_sph_mf}) AS sphmf_department_display"

    scope_sql = ""
    scope_bind: dict[str, Any] = {}
    if not scope_all_access and scope_group_allow is not None:
        allow_vals = sorted(scope_group_allow)
        allow_in, allow_p = _sql_expr_in_binds(effective_upper_sql, allow_vals, "sc_allow")
        scope_sql += (
            f" AND LENGTH({effective_upper_sql}) > 0 AND ({allow_in})"
        )
        scope_bind.update(allow_p)
    if not scope_all_access and scope_group_deny:
        deny_vals = sorted(scope_group_deny)
        deny_in, deny_p = _sql_expr_in_binds(effective_upper_sql, deny_vals, "sc_deny")
        scope_sql += f" AND NOT ({deny_in})"
        scope_bind.update(deny_p)

    params = {**params, **scope_bind}

    where_sql = " AND ".join(conds)

    join_fee = ""
    join_sales = ""
    select_sales = "0::numeric AS sales_revenue_sum"
    select_fee = "0::numeric AS fee_sum"
    has_det = _table_exists(db, "supsettledettot")
    has_chg = _table_exists(db, "supsetcharge")
    if has_det:
        join_sales = """
            LEFT JOIN (
              SELECT sdtbillno, SUM(sdtxssr) AS sum_xssr
              FROM supsettledettot
              GROUP BY sdtbillno
            ) s ON s.sdtbillno = h.sshbillno"""
        select_sales = "COALESCE(s.sum_xssr, 0) AS sales_revenue_sum"
    if has_chg:
        join_fee = """
            LEFT JOIN (
              SELECT sscjsno, SUM(sscmoney) AS sum_fee
              FROM supsetcharge
              WHERE sscjsno IS NOT NULL AND sscjsno <> ''
              GROUP BY sscjsno
            ) f ON f.sscjsno = h.sshbillno"""
        select_fee = "COALESCE(f.sum_fee, 0) AS fee_sum"

    pb_join = ""
    pb_select = "NULL::varchar AS pbbillno"
    if has_paybatch:
        pb_join = """
            LEFT JOIN LATERAL (
              SELECT TRIM(pb.pbbillno) AS pbbillno
              FROM paybatch pb
              WHERE TRIM(pb.pbjsno) = TRIM(h.sshbillno)
              ORDER BY CASE WHEN TRIM(pb.pbbilltype) = 'J' THEN 0 ELSE 1 END,
                       pb.pbseq DESC NULLS LAST
              LIMIT 1
            ) pb_hdr ON TRUE"""
        pb_select = "pb_hdr.pbbillno"

    base_from = f"""
            FROM supsettlehead h
            {pb_join}
            {join_sales}
            {join_fee}
            {lateral_pb}
            {lateral_ssh}
            {mf_join}
    """

    # COUNT：仅扫描 supsettlehead + 关键词 EXISTS；柜组权限需要 lateral 解析 effective mf。
    # 去掉聚合子查询与 manaframe，显著减轻全表统计成本。
    count_from = "FROM supsettlehead h"
    if scope_sql:
        count_from += lateral_pb + lateral_ssh

    count_row = db.execute(
        text(f"SELECT COUNT(*) AS n {count_from} WHERE {where_sql}{scope_sql}"),
        params,
    ).fetchone()
    total = int(count_row.n) if count_row is not None else 0

    params["limit"] = page_size
    params["offset"] = (page - 1) * page_size

    rows = db.execute(
        text(
            f"""
            SELECT
              h.sshbillno,
              {pb_select},
              h.sshmkt,
              h.sshflag,
              h.sshpayflag,
              h.sshcontno,
              h.sshsupid,
              h.sshwmid,
              h.sshdate,
              h.sshlastdate,
              h.sshthisdate,
              h.sshenddate,
              h.inputor,
              h.auditor,
              h.auditdate,
              h.sshsjfkje,
              h.sshvc3,
              h.sshtotkk,
              h.sshsetje,
              h.sshinvno,
              {select_sales},
              {select_fee},
              {sphmfid_select},
              {sphmf_disp_select}
            {base_from}
            WHERE {where_sql}{scope_sql}
            ORDER BY h.sshdate DESC NULLS LAST, h.sshbillno DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).fetchall()

    out: list[dict[str, Any]] = []
    for r in rows:
        d = _row_dict(r)
        out.append(d)

    return out, total


def get_settlement_detail(db: Session, sshbillno: str) -> dict[str, Any] | None:
    """结算单明细：头表 + supsettledettot + supsetcharge。"""
    if not _table_exists(db, "supsettlehead"):
        return None

    bill = (sshbillno or "").strip()
    if not bill:
        return None

    head = db.execute(
        text("SELECT * FROM supsettlehead WHERE TRIM(sshbillno) = :b LIMIT 1"),
        {"b": bill},
    ).fetchone()
    if head is None:
        return None

    head_dict = _row_dict(head)

    lines: list[dict[str, Any]] = []
    if _table_exists(db, "supsettledettot"):
        lr = db.execute(
            text(
                """
                SELECT * FROM supsettledettot
                WHERE TRIM(sdtbillno) = :b
                ORDER BY sdtrowno ASC
                """
            ),
            {"b": bill},
        ).fetchall()
        lines = [_row_dict(x) for x in lr]

    charges: list[dict[str, Any]] = []
    if _table_exists(db, "supsetcharge"):
        from services.erp_settlement_charge_display import query_supsetcharge_enriched

        charges = query_supsetcharge_enriched(
            db,
            where_sql="aa.sscjsno IS NOT NULL AND TRIM(aa.sscjsno) = :b",
            params={"b": bill},
            order_by="aa.sscrowno ASC NULLS LAST",
        )

    paybatch_rows: list[dict[str, Any]] = []
    if _table_exists(db, "paybatch"):
        pr = db.execute(
            text(
                """
                SELECT * FROM paybatch
                WHERE TRIM(pbjsno) = :b
                ORDER BY pbseq ASC NULLS LAST, pbbillno ASC
                """
            ),
            {"b": bill},
        ).fetchall()
        paybatch_rows = [_row_dict(x) for x in pr]

    from services.erp_settlement_paybatch_sales import fetch_paybatch_settlement_sales

    paybatch_sales = fetch_paybatch_settlement_sales(db, bill)

    from services.erp_settlement_header_display import (
        fetch_charges_by_payment_bill,
        fetch_settlement_header_display,
    )

    header_display = fetch_settlement_header_display(db, bill)
    sph = None
    if isinstance(header_display, dict):
        sph = header_display.get("sphbillno")
        if sph is not None:
            sph = str(sph).strip() or None
    charges_by_payment_bill = fetch_charges_by_payment_bill(db, sph)

    return {
        "head": head_dict,
        "header_display": header_display,
        "charges_by_payment_bill": charges_by_payment_bill,
        "paybatch": paybatch_rows,
        "paybatch_sales": paybatch_sales,
        "lines": lines,
        "charges": charges,
    }
