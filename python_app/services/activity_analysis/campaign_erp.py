"""Read approved ERP rules from a validated local ODS batch, never from live PAPI."""
import re
from datetime import date, timedelta

from sqlalchemy import text


class RuleSourceError(ValueError):
    pass


def rule_parameters(config):
    pid, market = str(config["erp_activity_id"]), str(config["store_code"])
    types = config["coupon_types"]
    if not re.fullmatch(r"[0-9]{1,20}", pid) or not re.fullmatch(r"[0-9]{3}", market):
        raise RuleSourceError("请先填写有效的 ERP 档期编码及门店")
    if not types or any(not re.fullmatch(r"[A-Z]", c) for c in types):
        raise RuleSourceError("券种格式不正确")
    start, end = date.fromisoformat(str(config["start_date"])), date.fromisoformat(str(config["end_date"]))
    if end < start:
        raise RuleSourceError("活动日期不正确")
    return dict(erp_activity_id=pid, store_code=market, coupon_types=types,
                start_date=start, end_exclusive=end + timedelta(days=1))


def rule_summary_sql(config):
    rule_parameters(config)
    return """
      SELECT r.tgyrqtype coupon_type,r.tgyrtype rule_type,r.tgyrmode rule_mode,
        r.tgyrtjje threshold_amount,r.tgyraq accept_amount,r.tgyrbq max_amount,
        TO_CHAR(r.tgyrstartdate,'YYYY-MM-DD') start_date,
        TO_CHAR(r.tgyrenddate,'YYYY-MM-DD') end_date,
        COUNT(*) rule_count,COUNT(DISTINCT r.tgyrbillno) document_count
      FROM ods.gpp_tktgoodsyqrate r
      JOIN ods.gpp_tktbgoodsfqhead h
        ON h.batch_id=r.batch_id AND h.tbfhbillno=r.tgyrbillno
      WHERE r.batch_id=:batch_id AND r.tgyrpid=:erp_activity_id
        AND h.tbfhmkt=:store_code AND h.tbfhflag='Y'
        AND r.tgyrqtype=ANY(CAST(:coupon_types AS text[]))
        AND r.tgyrstartdate < :end_exclusive AND r.tgyrenddate >= :start_date
      GROUP BY r.tgyrqtype,r.tgyrtype,r.tgyrmode,r.tgyrtjje,r.tgyraq,r.tgyrbq,
        TO_CHAR(r.tgyrstartdate,'YYYY-MM-DD'),TO_CHAR(r.tgyrenddate,'YYYY-MM-DD')
      ORDER BY coupon_type,threshold_amount,accept_amount,start_date,rule_mode
    """


def fetch_rule_summary(db, config):
    params = rule_parameters(config)
    ready = db.execute(text("""
      SELECT to_regclass('ods.campaign_rule_current') IS NOT NULL
        AND to_regclass('ods.campaign_rule_batches') IS NOT NULL
        AND to_regclass('ods.gpp_tktgoodsyqrate') IS NOT NULL
        AND to_regclass('ods.gpp_tktbgoodsfqhead') IS NOT NULL
    """)).scalar()
    if not ready:
        raise RuleSourceError("ERP 规则 ODS 尚未安装，请先执行数据库迁移；旧快照未被覆盖")
    batch = db.execute(text("""
      SELECT b.batch_id,b.source_started_at,b.published_at
      FROM ods.campaign_rule_current c
      JOIN ods.campaign_rule_batches b ON b.batch_id=c.batch_id
        AND b.store_code=c.store_code AND b.erp_activity_id=c.erp_activity_id
      WHERE c.store_code=:store_code AND c.erp_activity_id=:erp_activity_id
        AND b.status='published' AND b.validation IS NOT NULL
    """), params).mappings().first()
    if not batch:
        raise RuleSourceError("本店本档期的 ERP 规则尚未完成 PAPI 同步及校验；旧快照未被覆盖")
    params["batch_id"] = batch["batch_id"]
    rows = db.execute(text(rule_summary_sql(config)), params).mappings().all()
    return {"rows": [dict(r) for r in rows], "ods_batch_id": batch["batch_id"],
            "source_synced_at": batch["source_started_at"].isoformat(),
            "ods_published_at": batch["published_at"].isoformat()}
