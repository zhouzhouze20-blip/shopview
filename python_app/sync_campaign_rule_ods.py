"""Operator-only PAPI full-snapshot preparation and validated publication.

No credentials in payloads; use the papi-etl skill's safe client. Prepare, preview,
obtain run approval, then run the two task IDs through PAPI. Publish never runs ETL.
No schedules, truncates, source writes, or automatic historical cleanup.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from uuid import uuid4

from sqlalchemy import text

HEAD_FIELDS = "tbfhbillno tbfhpid tbfhmkt tbfhflag tbfhstartdate tbfhenddate tbfhmode tbfhrate tbfhtype tbfhsupid tbfhmanaunit tbfhinputdate tbfhauditdate tbhqxrq".split()
RULE_FIELDS = "tgyrseqno tgyrpid tgyrmode tgyrbarcode tgyrmfid tgyrcatid tgyrppcode tgyrrate tgyrstartdate tgyrenddate tgyrstarttime tgyrendtime tgyrbillno tgyrtype tgyrqtype tgyrtcode tgyrtjje tgyraq tgyrbq tgyrbillid tgyrmanaunit tgyrspsx tgyzkmk".split()
DATES = set("tbfhstartdate tbfhenddate tbfhinputdate tbfhauditdate tbhqxrq tgyrstartdate tgyrenddate".split())
NUMBERS = set("tgyrseqno tgyrrate tgyrtjje tgyraq tgyrbq tgyzkmk tbfhrate".split())


def source_parts(kind, store, pid):
    if not re.fullmatch(r"\d{3}", store) or not re.fullmatch(r"\d{1,20}", pid):
        raise ValueError("Invalid store/activity scope")
    if kind == "head":
        return HEAD_FIELDS, "h", "tbfhbillno", (
            "DBUSRPOP.TKTBGOODSFQHEAD h "
            f"WHERE h.TBFHPID='{pid}' AND h.TBFHMKT='{store}'")
    if kind != "rule":
        raise ValueError("Invalid table kind")
    return RULE_FIELDS, "r", "tgyrseqno", (
        "DBUSRPOP.TKTGOODSYQRATE r JOIN DBUSRPOP.TKTBGOODSFQHEAD h "
        "ON h.TBFHBILLNO=r.TGYRBILLNO "
        f"WHERE r.TGYRPID='{pid}' AND h.TBFHMKT='{store}'")


def source_hash(fields, alias):
    values = []
    for name in fields:
        column = f"{alias}.{name.upper()}"
        if name in DATES:
            column = f"TO_CHAR({column},'YYYY-MM-DD HH24:MI:SS')"
        elif name in NUMBERS:
            column = f"TO_CHAR({column},'TM9','NLS_NUMERIC_CHARACTERS=''.,''')"
        # Length prefixes distinguish nulls and embedded separators.
        values.append(f"NVL(TO_CHAR(LENGTH({column})),'-1')||':'||{column}")
    return "ORA_HASH(" + "||'|'||".join(values) + ")"


def extraction_sql(kind, store, pid, batch):
    if not re.fullmatch(r"[0-9a-f-]{36}", batch):
        raise ValueError("Invalid batch")
    fields, alias, key, from_sql = source_parts(kind, store, pid)
    columns = []
    for name in fields:
        column = f"{alias}.{name.upper()}"
        if name in DATES:
            column = f"TO_CHAR({column},'YYYY-MM-DD HH24:MI:SS')"
        # Preserve unconstrained Oracle NUMBER precision across JSON/JS transport.
        elif name in NUMBERS:
            column = f"TO_CHAR({column},'TM9','NLS_NUMERIC_CHARACTERS=''.,''')"
        columns.append(f'{column} AS "{name}"')
    columns += [f"'{batch}' AS \"batch_id\"", f'{source_hash(fields, alias)} AS "source_row_hash"',
                "TO_CHAR(SYSDATE,'YYYY-MM-DD HH24:MI:SS')||' +08:00' AS \"source_loaded_at\""]
    return "SELECT " + ", ".join(columns) + " FROM " + from_sql + f" ORDER BY {alias}.{key.upper()}"


def source_stats_sql(kind, store, pid):
    fields, alias, key, from_sql = source_parts(kind, store, pid)
    return (f"SELECT COUNT(*) N,COUNT(DISTINCT {alias}.{key}) KEYS,"
            f"COALESCE(SUM({source_hash(fields, alias)}),0) HASH_SUM FROM {from_sql}")


def target_table(kind):
    return "ods.gpp_tktbgoodsfqhead" if kind == "head" else "ods.gpp_tktgoodsyqrate"


def task_body(kind, store, pid, batch, source_id, target_id):
    fields, _, key, _ = source_parts(kind, store, pid)
    mapping = {name: name for name in fields + ["batch_id", "source_row_hash", "source_loaded_at"]}
    return {"name": f"ODS活动-GPP-{store}-{pid}-{kind}-{batch[:8]}",
            "enabled": False, "sourceId": source_id, "targetSourceId": target_id,
            "sqlText": extraction_sql(kind, store, pid, batch),
                         "tableName": target_table(kind), "fieldMapping": mapping,
                         "insertMode": "insert", "keyColumns": f"batch_id,{key}",
                         "batchSize": 3000, "maxRows": 0, "autoCreateTable": False,
                         "resumeEnabled": False,
            "schedule": {"scheduleEnabled": False, "scheduleType": "daily", "scheduleTime": "02:00"},
            "queryTimeoutSeconds": 120, "dbTimeoutSeconds": 120, "maxRuntimeSeconds": 1800}


def load_client(path):
    spec = importlib.util.spec_from_file_location("papi_safe_client", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.PapiClient(os.getenv("PAPI_BASE_URL", module.DEFAULT_BASE_URL), module.find_api_key()), module.extract_data


def query(client, unwrap, source_id, sql):
    data = unwrap(client.execute("POST", f"/api/sources/{source_id}/test", {"sql": sql, "limit": 10}))
    if not data.get("ok") or data.get("truncated"):
        raise RuntimeError("Source query incomplete")
    return data["rows"]


def source_stats(client, unwrap, source_id, kind, store, pid):
    row = query(client, unwrap, source_id, source_stats_sql(kind, store, pid))[0]
    stats = {k.lower(): int(v) for k, v in row.items()}
    if stats["n"] != stats["keys"]:
        raise RuntimeError("Source key is null or duplicated")
    return stats


def prepare(conn, client, unwrap, args):
    batch = str(uuid4())
    expected = {kind: source_stats(client, unwrap, args.source_id, kind, args.store, args.pid)
                for kind in ("head", "rule")}
    # Refuse duplicate unfinished preparations; inspect/recover the previous batch.
    conn.execute(text("SELECT pg_advisory_xact_lock(862032,CAST(:s AS integer))"), {"s": args.store})
    pending = conn.execute(text("SELECT batch_id FROM ods.campaign_rule_batches WHERE store_code=:s AND erp_activity_id=:p AND status='loading'"), {"s": args.store, "p": args.pid}).scalar()
    if pending:
        raise RuntimeError(f"Unpublished batch already exists: {pending}")
    conn.execute(text("""INSERT INTO ods.campaign_rule_batches(batch_id,store_code,erp_activity_id,validation)
      VALUES(:b,:s,:p,CAST(:v AS jsonb))"""),
      {"b": batch, "s": args.store, "p": args.pid, "v": json.dumps({"expected": expected})})
    conn.commit()
    ids = {}
    for kind in ("head", "rule"):
        result = unwrap(client.execute("POST", "/api/database-tasks", task_body(kind, args.store, args.pid, batch, args.source_id, args.target_id), confirm_action=True))
        # The gateway wraps task details on some versions.
        task = result.get("task", result)
        task_id = task["id"]
        ids[kind] = task_id
        conn.execute(text(f"UPDATE ods.campaign_rule_batches SET {kind}_task_id=:t WHERE batch_id=:b"), {"t": task_id, "b": batch})
        conn.commit()
    print(json.dumps({"batch_id": batch, "expected": expected, "tasks": ids, "next": "Inspect disabled tasks, preview, obtain approval, run; then publish."}, ensure_ascii=False), flush=True)


def publish(conn, client, unwrap, args):
    batch = dict(conn.execute(text("SELECT * FROM ods.campaign_rule_batches WHERE batch_id=:b"), {"b": args.batch}).mappings().one())
    conn.execute(text("SELECT pg_advisory_xact_lock(862032,CAST(:s AS integer))"), {"s": batch["store_code"]})
    batch = dict(conn.execute(text("SELECT * FROM ods.campaign_rule_batches WHERE batch_id=:b FOR UPDATE"), {"b": args.batch}).mappings().one())
    if batch["status"] != "loading":
        raise RuntimeError("Batch already published; never reload or overwrite it")
    tasks = unwrap(client.execute("GET", "/api/database-tasks"))
    evidence = {}
    for kind in ("head", "rule"):
        task = next(t for t in tasks if t["id"] == batch[f"{kind}_task_id"])
        expected_task = task_body(kind, batch["store_code"], batch["erp_activity_id"], args.batch, args.source_id, args.target_id)
        if (task["source_id"] != args.source_id or task["target_source_id"] != args.target_id
            or task["table_name"] != target_table(kind) or task["enabled"] or task["schedule_enabled"]
            or task.get("running_count") or task["sql_text"] != expected_task["sqlText"]
            or task["field_mapping"] != expected_task["fieldMapping"]
            or task["key_columns"] != expected_task["keyColumns"]
            or task["insert_mode"] != "insert" or task["max_rows"] != 0):
            raise RuntimeError("Task scope/state changed; publication refused")
        log = task.get("latest_log") or {}
        if log.get("status") != "success" or log.get("stage") != "completed":
            raise RuntimeError(f"Task {task['id']} has no successful complete log")
        key = "tbfhbillno" if kind == "head" else "tgyrseqno"
        row = conn.execute(text(f"SELECT COUNT(*) n,COUNT(DISTINCT {key}) keys,COALESCE(SUM(source_row_hash),0) hash_sum FROM {target_table(kind)} WHERE batch_id=:b"), {"b": args.batch}).mappings().one()
        actual = {k: int(v) for k, v in row.items()}
        expected = batch["validation"]["expected"][kind]
        current = source_stats(client, unwrap, args.source_id, kind, batch["store_code"], batch["erp_activity_id"])
        if actual != expected or current != expected or int(log.get("row_count", -1)) != actual["n"]:
            raise RuntimeError(f"{kind} count/key/hash/source/log mismatch; old published batch preserved")
        evidence[kind] = {**actual, "task_id": task["id"], "log_id": log["id"], "trace_id": log.get("trace_id")}
    orphan = conn.execute(text("""SELECT COUNT(*) FROM ods.gpp_tktgoodsyqrate r
      LEFT JOIN ods.gpp_tktbgoodsfqhead h ON h.batch_id=r.batch_id AND h.tbfhbillno=r.tgyrbillno
      WHERE r.batch_id=:b AND (h.tbfhbillno IS NULL OR h.tbfhmkt<>:s OR r.tgyrpid<>:p)"""), {"b": args.batch, "s": batch["store_code"], "p": batch["erp_activity_id"]}).scalar()
    if orphan:
        raise RuntimeError("Missing or wrong-scope rule headers")
    conn.execute(text("UPDATE ods.campaign_rule_batches SET status='published',published_at=NOW(),validation=CAST(:v AS jsonb) WHERE batch_id=:b"), {"b": args.batch, "v": json.dumps(evidence)})
    conn.execute(text("""INSERT INTO ods.campaign_rule_current(store_code,erp_activity_id,batch_id) VALUES(:s,:p,:b)
      ON CONFLICT(store_code,erp_activity_id) DO UPDATE SET batch_id=EXCLUDED.batch_id"""), {"s": batch["store_code"], "p": batch["erp_activity_id"], "b": args.batch})
    conn.commit()
    print(json.dumps({"published": args.batch, "validation": evidence}, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "publish"])
    parser.add_argument("--store")
    parser.add_argument("--pid")
    parser.add_argument("--batch")
    parser.add_argument("--source-id", type=int, required=True)
    parser.add_argument("--target-id", type=int, required=True)
    parser.add_argument("--papi-client", default=str(Path.home()/".codex/skills/papi-etl/scripts/papi_cli.py"))
    parser.add_argument("--confirm-write", action="store_true")
    args = parser.parse_args()
    if not args.confirm_write:
        parser.error("Explicit authorization required: --confirm-write")
    if args.action == "prepare" and (not args.store or not args.pid):
        parser.error("prepare requires --store and --pid")
    if args.action == "publish" and not args.batch:
        parser.error("publish requires --batch")
    from models.database import engine
    client, unwrap = load_client(args.papi_client)
    sources = client.resources()["sources"]
    source = next(s for s in sources if s["id"] == args.source_id)
    target = next(s for s in sources if s["id"] == args.target_id)
    config = target["config"]
    if source["type"] != "oracle" or "GPP" not in source["name"] or target["type"] != "postgres":
        raise RuntimeError("Source/target identity mismatch")
    if (config.get("host"), int(config.get("port",5432)), config.get("database")) != (engine.url.host,engine.url.port or 5432,engine.url.database):
        raise RuntimeError("PAPI target differs from ShopView database")
    with engine.connect() as conn:
        (prepare if args.action == "prepare" else publish)(conn, client, unwrap, args)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Never print raw connection errors or gateway response bodies.
        print(f"ODS operation stopped ({type(exc).__name__}); inspect sanitized PAPI task logs. No batch published by this failed operation.", file=sys.stderr)
        raise SystemExit(1)
