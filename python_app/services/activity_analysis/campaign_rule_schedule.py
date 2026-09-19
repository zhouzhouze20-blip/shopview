"""One Oracle statement emits both source tables and an end-of-stream manifest.

Oracle SYSDATE is statement-stable. A second-level run key is sufficient because
PAPI serializes this task; a same-second retry fails its staging PK, not overwrites.
No moving watermark or per-page SELECT: this requires Oracle ResultSet streaming.
"""
import re

from sync_campaign_rule_ods import HEAD_FIELDS, RULE_FIELDS, DATES, NUMBERS, source_hash, source_parts

STAGE_FIELDS = ["batch_id", "store_code", "erp_activity_id", "row_kind", "source_key",
                "source_row_hash", "source_loaded_at", "expected_heads", "expected_rules",
                "expected_head_hash", "expected_rule_hash"] + HEAD_FIELDS + RULE_FIELDS


def scheduled_sql(store, pid):
    if not re.fullmatch(r"[0-9]{3}", store) or not re.fullmatch(r"[0-9]{1,10}", pid):
        raise ValueError("Invalid scheduled scope")
    branches = []
    fields = HEAD_FIELDS + RULE_FIELDS
    for kind in ("head", "rule", "manifest"):
        if kind == "manifest":
            own, alias, key, source = [], "", "", "DUAL"
            expressions = ["'manifest' row_kind", "'-' source_key", "0 source_row_hash"]
        else:
            own, alias, key, source = source_parts(kind, store, pid)
            expressions = [f"'{kind}' row_kind", f"TO_CHAR({alias}.{key}) source_key" if kind == "rule" else f"{alias}.{key} source_key", f"{source_hash(own,alias)} source_row_hash"]
        for name in fields:
            value = "CAST(NULL AS VARCHAR2(100))"
            if name in own:
                value = f"{alias}.{name}"
                if name in DATES:
                    value = f"TO_CHAR({value},'YYYY-MM-DD HH24:MI:SS')"
                elif name in NUMBERS:
                    value = f"TO_CHAR({value},'TM9','NLS_NUMERIC_CHARACTERS=''.,''')"
            expressions.append(f'{value} "{name}"')
        branches.append("SELECT " + ",".join(expressions) + " FROM " + source)
    union = "\nUNION ALL\n".join(branches)
    return f"""WITH data_rows AS ({union})
      SELECT '{store}-{pid}-'||TO_CHAR(SYSDATE,'YYYYMMDDHH24MISS') AS "batch_id",
        '{store}' AS "store_code",'{pid}' AS "erp_activity_id",
        row_kind AS "row_kind",source_key AS "source_key",source_row_hash AS "source_row_hash",
        TO_CHAR(SYSDATE,'YYYY-MM-DD HH24:MI:SS')||' +08:00' AS "source_loaded_at",
        CASE WHEN row_kind='manifest' THEN SUM(CASE WHEN row_kind='head' THEN 1 ELSE 0 END) OVER() END AS "expected_heads",
        CASE WHEN row_kind='manifest' THEN SUM(CASE WHEN row_kind='rule' THEN 1 ELSE 0 END) OVER() END AS "expected_rules",
        CASE WHEN row_kind='manifest' THEN SUM(CASE WHEN row_kind='head' THEN source_row_hash ELSE 0 END) OVER() END AS "expected_head_hash",
        CASE WHEN row_kind='manifest' THEN SUM(CASE WHEN row_kind='rule' THEN source_row_hash ELSE 0 END) OVER() END AS "expected_rule_hash",
        {','.join('"'+f+'"' for f in fields)}
      FROM data_rows
      ORDER BY CASE row_kind WHEN 'head' THEN 0 WHEN 'rule' THEN 1 ELSE 2 END,source_key"""


def scheduled_task(store, pid, source_id, target_id, *, enabled=False):
    return dict(name=f"ODS活动-GPP-{store}-{pid}-每日完整规则同步",
                sourceId=source_id,targetSourceId=target_id,
                sqlText=scheduled_sql(store,pid),tableName="ods.campaign_rule_stage",
                fieldMapping={field:field for field in STAGE_FIELDS},
                insertMode="insert",keyColumns="batch_id,row_kind,source_key",
                batchSize=3000,maxRows=0,autoCreateTable=False,resumeEnabled=False,
                queryTimeoutSeconds=120,dbTimeoutSeconds=120,maxRuntimeSeconds=1800,
                enabled=enabled,scheduleEnabled=enabled,scheduleType="daily",
                scheduleTime="02:10",scheduleIntervalMinutes=1440,
                scheduleWeekdays="0,1,2,3,4,5,6",scheduleMonthDay=1)
