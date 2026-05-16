"""
结算单费用明细展示：对齐 ERP Oracle 视图（supsetcharge + manaframe + gr_kmcode）。

Oracle 参考：
  person1 → 票减/非票减；sscflag → 录入/已生成结算单/…；
  柜组：sscmfid || mfcname；费用名称：[sscid] + gr_kmcode.name（无科目表时用 sscname）。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.erp_settlement_service import _row_dict, _table_exists


def _supsetcharge_enriched_sql(db: Session) -> tuple[str, str]:
    """返回 (附加 SELECT 列表达式, JOIN 片段（含换行前缀）)。"""
    has_mf = _table_exists(db, "manaframe")
    has_km = _table_exists(db, "gr_kmcode")

    bb_join = ""
    counter_sql = "TRIM(COALESCE(aa.sscmfid::text, ''))"
    if has_mf:
        bb_join = "LEFT JOIN manaframe bb ON TRIM(bb.mfcode) = TRIM(aa.sscmfid)"
        counter_sql = (
            "CASE WHEN bb.mfcode IS NOT NULL THEN "
            "TRIM(aa.sscmfid::text) || ' ' || COALESCE(bb.mfcname::text, '') "
            "ELSE TRIM(COALESCE(aa.sscmfid::text, '')) END"
        )

    cc_join = ""
    if has_km:
        cc_join = "LEFT JOIN gr_kmcode cc ON TRIM(aa.sscid::text) = TRIM(cc.id::text)"
        expense_sql = (
            "CASE WHEN cc.id IS NOT NULL THEN "
            "'[' || TRIM(aa.sscid::text) || '] ' || COALESCE(cc.name::text, '') "
            "ELSE '[' || TRIM(COALESCE(aa.sscid::text, '')) || '] ' || COALESCE(aa.sscname::text, '') END"
        )
    else:
        expense_sql = (
            "'[' || TRIM(COALESCE(aa.sscid::text, '')) || '] ' || COALESCE(aa.sscname::text, '')"
        )

    extra_select = f"""
      CASE TRIM(COALESCE(aa.person1::text, ''))
        WHEN 'Y' THEN '票减'
        WHEN 'N' THEN '非票减'
        ELSE TRIM(COALESCE(aa.person1::text, ''))
      END AS person1_label,
      CASE TRIM(COALESCE(aa.sscflag::text, ''))
        WHEN 'N' THEN '录入'
        WHEN 'M' THEN '已生成结算单'
        WHEN 'Y' THEN '结算审核'
        WHEN 'S' THEN '费用审核'
        WHEN 'G' THEN '已收款'
        ELSE TRIM(COALESCE(aa.sscflag::text, ''))
      END AS sscflag_label,
      {counter_sql} AS counter_display,
      {expense_sql} AS expense_name_display
    """

    joins = f"{bb_join}\n{cc_join}".strip()
    if joins:
        joins = "\n" + joins
    return extra_select, joins


def query_supsetcharge_enriched(
    db: Session,
    *,
    where_sql: str,
    params: dict[str, Any],
    order_by: str = "aa.sscrowno ASC NULLS LAST",
) -> list[dict[str, Any]]:
    """
    查询 supsetcharge，附带 ERP 展示字段。where_sql 须使用别名 aa（例：TRIM(aa.sscjsno) = :b）。
    """
    if not _table_exists(db, "supsetcharge"):
        return []

    extra_select, joins = _supsetcharge_enriched_sql(db)
    sql = f"""
    SELECT aa.*,
    {extra_select}
    FROM supsetcharge aa
    {joins}
    WHERE {where_sql}
    ORDER BY {order_by}
    """
    rows = db.execute(text(sql), params).fetchall()
    return [_row_dict(r) for r in rows]
