"""
结算单销售（paybatch × supsettledet 聚合）：对齐 ERP Oracle 视图。

Oracle：
  paybatch LEFT JOIN (
    SELECT ssdbillno, ssdn80, ssdvc6, SUM(ssdn74) sl
    FROM supsettledet GROUP BY ssdbillno, ssdn80, ssdvc6
  ) ON pbbillno = ssdbillno

无 supsettledet 表时仍返回 paybatch 行，明细数量/税率/考核类型列为空。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.erp_settlement_service import _row_dict, _table_exists


def fetch_paybatch_settlement_sales(db: Session, sshbillno: str) -> list[dict[str, Any]]:
    """按结算单号 pbjsno 筛选 paybatch，并按单据号关联 supsettledet 汇总行（可能一对多）。"""
    bill = (sshbillno or "").strip()
    if not bill or not _table_exists(db, "paybatch"):
        return []

    has_ssd = _table_exists(db, "supsettledet")

    if has_ssd:
        sql = """
        SELECT
          pb.*,
          CASE TRIM(COALESCE(det.ssdvc6::text, ''))
            WHEN '0' THEN '正常销售'
            WHEN '7' THEN '核算点考核'
            WHEN '8' THEN '平衡点考核'
            ELSE NULLIF(TRIM(COALESCE(det.ssdvc6::text, '')), '')
          END AS ssdvc6_label,
          det.ssdvc6 AS ssdvc6,
          det.sl AS sl,
          det.ssdn80 AS ssdn80
        FROM paybatch pb
        LEFT JOIN (
          SELECT
            ssdbillno,
            ssdn80,
            ssdvc6,
            SUM(COALESCE(ssdn74, 0)) AS sl
          FROM supsettledet
          GROUP BY ssdbillno, ssdn80, ssdvc6
        ) det ON TRIM(det.ssdbillno) = TRIM(pb.pbbillno)
        WHERE TRIM(pb.pbjsno) = :b
        ORDER BY pb.pbseq ASC NULLS LAST, pb.pbbillno ASC,
          det.ssdn80 ASC NULLS LAST, det.ssdvc6 ASC NULLS LAST
        """
    else:
        sql = """
        SELECT
          pb.*,
          NULL::text AS ssdvc6_label,
          NULL::varchar AS ssdvc6,
          NULL::numeric AS sl,
          NULL::numeric AS ssdn80
        FROM paybatch pb
        WHERE TRIM(pb.pbjsno) = :b
        ORDER BY pb.pbseq ASC NULLS LAST, pb.pbbillno ASC
        """

    rows = db.execute(text(sql), {"b": bill}).fetchall()
    return [_row_dict(r) for r in rows]
