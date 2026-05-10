"""
结算单「表头」展示：对齐 ERP 视图（suppayhead + paybatch + supsettlehead + 维表）。

Oracle 参考：
  suppayhead / paybatch 聚合 / supsettlehead / supsetcharge 按 sscpaybillno 汇总费用 /
  supplierbase / manaframe / paymode / privateinfo（缺表时降级）。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.erp_settlement_charge_display import query_supsetcharge_enriched
from services.erp_settlement_service import _row_dict, _table_exists


def fetch_settlement_header_display(db: Session, sshbillno: str) -> dict[str, Any] | None:
    """
    按结算单号 sshbillno（sshbillno）取一行表头展示字段。
    关联路径：paybatch.pbbillno = supsettlehead.sshbillno，
    paybatch.pbpaybillno = suppayhead.sphbillno；
    若无 paybatch，则尝试 supsettlehead.sshpayno = suppayhead.sphbillno。
    """
    bill = (sshbillno or "").strip()
    if not bill:
        return None

    if not _table_exists(db, "supsettlehead"):
        return None

    has_pb = _table_exists(db, "paybatch")
    has_aa = _table_exists(db, "suppayhead")
    has_sc = _table_exists(db, "supsetcharge")
    has_sup = _table_exists(db, "supplierbase")
    has_mf = _table_exists(db, "manaframe")
    has_pm = _table_exists(db, "paymode")
    has_priv = _table_exists(db, "privateinfo")

    if not has_aa:
        return _header_fallback_supsettlehead_only(db, bill)

    gg_join = ""
    if has_pb:
        gg_join = """
        LEFT JOIN (
            SELECT
              pbpaybillno,
              pbbillno,
              MIN(pbjssdate) - INTERVAL '1 day' AS bgdate,
              MAX(pbjsedate) AS eddate,
              SUM(COALESCE(pbxssr, 0)) AS xssr,
              SUM(COALESCE(pbkp, 0)) AS kp
            FROM paybatch
            GROUP BY pbpaybillno, pbbillno
        ) gg ON TRIM(gg.pbbillno) = TRIM(hh.sshbillno)
        """

    if has_pb:
        aa_join = "LEFT JOIN suppayhead aa ON TRIM(aa.sphbillno) = TRIM(gg.pbpaybillno)"
    else:
        aa_join = "LEFT JOIN suppayhead aa ON TRIM(aa.sphbillno) = TRIM(hh.sshpayno)"

    ff_join = ""
    if has_sc:
        ff_join = """
        LEFT JOIN (
            SELECT sscpaybillno, SUM(COALESCE(sscmoney, 0)) AS fy
            FROM supsetcharge
            WHERE sscpaybillno IS NOT NULL AND TRIM(sscpaybillno) <> ''
            GROUP BY sscpaybillno
        ) ff ON TRIM(ff.sscpaybillno) = TRIM(aa.sphbillno)
        """

    cc_join = ""
    if has_sup:
        cc_join = "LEFT JOIN supplierbase cc ON TRIM(cc.sbid) = TRIM(aa.sphsupid)"
        sup_sel = (
            "CASE WHEN cc.sbid IS NOT NULL THEN '[' || TRIM(cc.sbid::text) || '] ' || COALESCE(cc.sbcname::text, '') "
            "ELSE NULL END"
        )
    else:
        sup_sel = (
            "CASE WHEN aa.sphsupid IS NOT NULL THEN '[' || TRIM(aa.sphsupid::text) || ']' ELSE NULL END"
        )

    bb_join = ""
    if has_mf:
        bb_join = "LEFT JOIN manaframe bb ON TRIM(bb.mfcode) = TRIM(aa.sphmfid)"
        dept_sel = (
            "CASE WHEN aa.sphmfid IS NOT NULL THEN TRIM(aa.sphmfid::text) || ' ' || COALESCE(bb.mfcname::text, '') "
            "ELSE NULL END"
        )
    else:
        dept_sel = "CASE WHEN aa.sphmfid IS NOT NULL THEN TRIM(aa.sphmfid::text) ELSE NULL END"

    dd_join = ""
    paymode_sel = "TRIM(COALESCE(aa.sphvc1::text, ''))"
    if has_pm:
        dd_join = "LEFT JOIN paymode dd ON TRIM(dd.pmcode) = TRIM(aa.sphvc1)"
        paymode_sel = (
            "TRIM(COALESCE(aa.sphvc1::text, '')) || ' ' || COALESCE(dd.pmname::text, '')"
        )

    ii_join = ""
    if has_priv:
        ii_join = """
        LEFT JOIN (
            SELECT pimkt,
              MAX(CASE WHEN piname = '商场名称' THEN pivalue END) AS mktname,
              MAX(CASE WHEN piname = '商场地址' THEN pivalue END) AS mktads,
              MAX(CASE WHEN piname = '联系电话' THEN pivalue END) AS telph
            FROM privateinfo
            WHERE piname IN ('商场名称', '商场地址', '联系电话')
            GROUP BY pimkt
        ) ii ON TRIM(ii.pimkt) = TRIM(aa.sphmkt)
        """
        ii_sel = "ii.mktname, ii.mktads, ii.telph"
    else:
        ii_sel = "NULL::text AS mktname, NULL::text AS mktads, NULL::text AS telph"

    xssr_sel = "COALESCE(gg.xssr, 0)" if has_pb else "NULL::numeric"
    kp_sel = "COALESCE(gg.kp, 0)" if has_pb else "NULL::numeric"
    fee_sel = "COALESCE(ff.fy, 0)" if has_sc else "NULL::numeric"

    if has_pb:
        gg_col_sql = """
      gg.bgdate AS bgdate,
      gg.eddate AS eddate,
      gg.pbpaybillno AS pb_paybillno,
      gg.pbbillno AS pb_billno,
      gg.xssr AS pb_xssr_raw,
      gg.kp AS pb_kp_raw,
        """
    else:
        gg_col_sql = """
      NULL::date AS bgdate,
      NULL::date AS eddate,
      NULL::varchar AS pb_paybillno,
      NULL::varchar AS pb_billno,
      NULL::numeric AS pb_xssr_raw,
      NULL::numeric AS pb_kp_raw,
        """

    sql = f"""
    SELECT
      hh.sshbillno AS sshbillno,
      aa.sphbillno AS sphbillno,
      {gg_col_sql}
      {sup_sel} AS supplier_display,
      {dept_sel} AS dept_display,
      CASE TRIM(COALESCE(aa.sphwmid::text, ''))
        WHEN '4' THEN '联营'
        WHEN '1' THEN '经销'
        WHEN '2' THEN '成本代销'
        WHEN '3' THEN '扣率代销'
        WHEN '5' THEN '租赁'
        ELSE COALESCE(aa.sphwmid::text, '')
      END AS operation_mode_label,
      aa.sphtaxno AS sphtaxno,
      aa.sphbank AS sphbank,
      aa.sphaccntno AS sphaccntno,
      {xssr_sel} AS xssr,
      {kp_sel} AS kp_amount,
      {fee_sel} AS fee_amount,
      aa.sphmoney AS sphmoney,
      aa.sphmoneyupper AS sphmoneyupper,
      hh.sshlastye AS sshlastye,
      hh.sshthisye AS sshthisye,
      hh.sshsetadj AS sshsetadj,
      hh.sshyfkje AS sshyfkje,
      {ii_sel},
      aa.sphmktbank AS sphmktbank,
      aa.sphmktaccntno AS sphmktaccntno,
      aa.sphmkttaxno AS sphmkttaxno,
      aa.sphpaydate AS sphpaydate,
      hh.sshplanpaydate AS sshplanpaydate,
      CASE TRIM(COALESCE(aa.sphflag::text, ''))
        WHEN 'Y' THEN '付款'
        WHEN 'M' THEN '生成'
        ELSE COALESCE(aa.sphflag::text, '')
      END AS payment_flag_label,
      aa.inputor AS inputor_code,
      aa.inputdate AS inputdate,
      aa.auditor AS auditor_code,
      aa.auditdate AS auditdate,
      {paymode_sel} AS paymode_display
    FROM supsettlehead hh
    {gg_join}
    {aa_join}
    {ff_join}
    {cc_join}
    {bb_join}
    {dd_join}
    {ii_join}
    WHERE TRIM(hh.sshbillno) = :bill
    LIMIT 1
    """

    row = db.execute(text(sql), {"bill": bill}).fetchone()
    if row is None:
        return None
    return _row_dict(row)


def _header_fallback_supsettlehead_only(db: Session, bill: str) -> dict[str, Any] | None:
    row = db.execute(
        text(
            """
            SELECT
              hh.sshbillno AS sshbillno,
              NULL::varchar AS sphbillno,
              NULL::date AS bgdate,
              NULL::date AS eddate,
              NULL::varchar AS pb_paybillno,
              NULL::varchar AS pb_billno,
              NULL::numeric AS pb_xssr_raw,
              NULL::numeric AS pb_kp_raw,
              NULL::text AS supplier_display,
              NULL::text AS dept_display,
              CASE TRIM(COALESCE(hh.sshwmid::text, ''))
                WHEN '4' THEN '联营'
                WHEN '1' THEN '经销'
                WHEN '2' THEN '成本代销'
                WHEN '3' THEN '扣率代销'
                WHEN '5' THEN '租赁'
                ELSE COALESCE(hh.sshwmid::text, '')
              END AS operation_mode_label,
              hh.sshtaxno AS sphtaxno,
              hh.sshbank AS sphbank,
              hh.sshaccntno AS sphaccntno,
              NULL::numeric AS xssr,
              NULL::numeric AS kp_amount,
              NULL::numeric AS fee_amount,
              NULL::numeric AS sphmoney,
              NULL::varchar AS sphmoneyupper,
              hh.sshlastye AS sshlastye,
              hh.sshthisye AS sshthisye,
              hh.sshsetadj AS sshsetadj,
              hh.sshyfkje AS sshyfkje,
              NULL::text AS mktname,
              NULL::text AS mktads,
              NULL::text AS telph,
              NULL::varchar AS sphmktbank,
              NULL::varchar AS sphmktaccntno,
              NULL::varchar AS sphmkttaxno,
              NULL::date AS sphpaydate,
              hh.sshplanpaydate AS sshplanpaydate,
              CASE TRIM(COALESCE(hh.sshpayflag::text, ''))
                WHEN 'Y' THEN '已付款'
                WHEN 'N' THEN '未付款'
                ELSE COALESCE(hh.sshpayflag::text, '')
              END AS payment_flag_label,
              hh.inputor AS inputor_code,
              hh.inputdate AS inputdate,
              hh.auditor AS auditor_code,
              hh.auditdate AS auditdate,
              NULL::text AS paymode_display
            FROM supsettlehead hh
            WHERE TRIM(hh.sshbillno) = :bill
            LIMIT 1
            """
        ),
        {"bill": bill},
    ).fetchone()
    if row is None:
        return None
    out = _row_dict(row)
    out["erp_header_fallback"] = True
    return out


def fetch_charges_by_payment_bill(
    db: Session, sphbillno: str | None,
) -> list[dict[str, Any]]:
    """费用明细：按付款单号 sscpaybillno（与表头 ff 汇总一致）。"""
    if not sphbillno or not _table_exists(db, "supsetcharge"):
        return []
    b = sphbillno.strip()
    if not b:
        return []
    return query_supsetcharge_enriched(
        db,
        where_sql="TRIM(aa.sscpaybillno) = :b",
        params={"b": b},
    )
