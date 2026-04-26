"""
百货柜位管理系统 - ERP 合同查询 API

按经营单元读取从 ERP 合同表同步过来的合同信息：
- business_units.unit_code 对应 contmanaframe.cmfmfid
- 同时兼容 contmain.cmchar9 作为经营单元编码
- contmanaframe.cmfcontno 对应 contmain.cmcontno
"""

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from models.database import get_db


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


@router.get("/by-unit/{unit_id}")
async def get_contracts_by_unit(
    unit_id: int,
    db: Session = Depends(get_db),
):
    """按经营单元 ID 查询关联的 ERP 合同。"""
    try:
        _require_contract_tables(db)
        has_supplierbase = _table_exists(db, "supplierbase")

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
        rows = db.execute(
            text(
                f"""
                WITH matched_contracts AS (
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
                    (
                      cm.cmstatus = 'Y'
                      AND CURRENT_DATE BETWEEN cm.cmeffdate::date AND cm.cmlapdate::date
                    ) AS is_current_effective
                  FROM contmain cm
                  LEFT JOIN contmanaframe cmf
                    ON cm.cmcontno = cmf.cmfcontno
                   AND upper(trim(COALESCE(cmf.cmfmfid, ''))) = upper(trim(:unit_code))
                  {_supplier_join_sql(has_supplierbase)}
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
                    (
                      cm.cmstatus = 'Y'
                      AND CURRENT_DATE BETWEEN cm.cmeffdate::date AND cm.cmlapdate::date
                    ) AS is_current_effective
                  FROM contmanaframe cmf
                  LEFT JOIN contmain cm ON cm.cmcontno = cmf.cmfcontno
                  {_supplier_join_sql(has_supplierbase)}
                  WHERE upper(trim(COALESCE(cmf.cmfmfid, ''))) = upper(trim(:unit_code))
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
            {"unit_code": unit_code},
        ).mappings().all()

        contracts = []
        for row in rows:
            data = {key: _json_value(value) for key, value in row.items()}
            data["status_label"] = CONTRACT_STATUS_LABELS.get(
                data.get("cmstatus"),
                data.get("cmstatus") or "未知",
            )
            data["is_current_effective"] = bool(data.get("is_current_effective"))
            contracts.append(data)

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
):
    """按合同号查询主表及 4 个合同分表明细。"""
    try:
        normalized_contract_no = (contract_no or "").strip()
        if not normalized_contract_no:
            raise HTTPException(status_code=400, detail="contract_no 不能为空")

        table_names = ("contmain", "contmanaframe", "contbd", "contcyclist", "contsupcharge")
        existing_tables = {name for name in table_names if _table_exists(db, name)}
        has_supplierbase = _table_exists(db, "supplierbase")
        has_manaframe = _table_exists(db, "manaframe")
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
                  cmseqno
                FROM contmain cm
                {_supplier_join_sql(has_supplierbase)}
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
                  cmfmemo
                FROM contmanaframe cmf
                {_manaframe_join_sql(has_manaframe, "cmf.cmfmfid")}
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
                  cbcontno,
                  cbseqno,
                  cbmkt,
                  cbmfid,
                  {_manaframe_name_select_sql(has_manaframe)}
                  cbeffdate,
                  cblapdate,
                  cbsum,
                  cbrate,
                  cbsum1,
                  cbrate1,
                  cbsum2,
                  cbrate2,
                  cbsum3,
                  cbrate3,
                  cbsum4,
                  cbrate4,
                  cbsum5,
                  cbrate5,
                  cbsum6,
                  cbrate6,
                  cbprofit,
                  cbsettype,
                  cbrentunit,
                  cbmanaunit,
                  cbpopunit,
                  cbrentprice,
                  cbnamaprice,
                  cbpopprice,
                  cbiscalcrent,
                  cbsalekh,
                  cbsalerate
                FROM contbd cb
                {_manaframe_join_sql(has_manaframe, "cb.cbmfid")}
                WHERE upper(trim(cbcontno)) = upper(trim(:contract_no))
                ORDER BY cbseqno ASC
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
                  cclpchflag
                FROM contcyclist ccl
                {_manaframe_join_sql(has_manaframe, "ccl.cclmfid")}
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
                  cscpeakvalues
                FROM contsupcharge csc
                {_manaframe_join_sql(has_manaframe, "csc.cscmfid")}
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
