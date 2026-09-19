from datetime import datetime, timezone, timedelta
import csv
import io
import os
from pathlib import Path
import sys
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"python_app"))
from services.activity_analysis.campaign_rule_schedule import scheduled_sql, scheduled_task, STAGE_FIELDS
from services.activity_analysis.campaign_erp import fetch_rule_summary


def test_schedule_has_single_query_manifest_last_and_no_moving_watermark():
    sql=scheduled_sql("601","2205")
    assert sql.count("UNION ALL")==2
    assert "'manifest' row_kind" in sql and "SUM(CASE WHEN row_kind='rule'" in sql
    assert "ORDER BY CASE row_kind WHEN 'head' THEN 0 WHEN 'rule' THEN 1 ELSE 2 END,source_key" in sql
    assert "h.TBFHMKT='601'" in sql and "r.TGYRPID='2205'" in sql
    assert "PAPI_WATERMARK" not in sql
    task=scheduled_task("601","2205",7,4)
    assert task["scheduleTime"]=="02:10" and "schedule" not in task
    assert task["enabled"] is False and task["scheduleEnabled"] is False
    assert scheduled_task("601","2205",7,4,enabled=True)["scheduleEnabled"] is True
    assert task["maxRows"]==0 and task["insertMode"]=="insert" and task["resumeEnabled"] is False
    assert set(task["fieldMapping"])==set(STAGE_FIELDS)
    with pytest.raises(ValueError): scheduled_sql("601 OR 1=1","2205")


@pytest.mark.skipif(os.getenv("SHOPVIEW_TEST_ODS_DATABASE")!="1",reason="Opt-in rollback-only DB checks")
def test_manifest_publication_is_atomic_with_copy_and_rejects_partial_or_stale():
    from models.database import engine
    now=datetime.now(timezone.utc)
    batch=str(uuid4()); newer=str(uuid4()); stale=str(uuid4())
    cfg=dict(store_code="990",erp_activity_id="909091",coupon_types=["B"],start_date="2026-08-14",end_date="2026-08-19")
    common=dict(batch_id=batch,store_code="990",erp_activity_id="909091",source_loaded_at=now)
    head={**common,"row_kind":"head","source_key":"head","source_row_hash":1,"tbfhbillno":"head","tbfhpid":"909091","tbfhmkt":"990","tbfhflag":"Y","tbfhstartdate":"2026-08-14","tbfhenddate":"2026-08-19","tbfhmanaunit":"002","tbfhinputdate":"2026-08-13"}
    rule={**common,"row_kind":"rule","source_key":"1","source_row_hash":2,"tgyrseqno":1,"tgyrpid":"909091","tgyrmode":"2","tgyrbarcode":"ALL","tgyrrate":0,"tgyrstartdate":"2026-08-14","tgyrenddate":"2026-08-19","tgyrstarttime":"00:00","tgyrendtime":"23:59","tgyrbillno":"head","tgyrtype":"6","tgyrqtype":"B","tgyrtjje":600,"tgyraq":50,"tgyrbillid":"QS6","tgyrmanaunit":"002"}
    manifest={**common,"row_kind":"manifest","source_key":"-","source_row_hash":0,"expected_heads":1,"expected_rules":1,"expected_head_hash":1,"expected_rule_hash":2}
    with engine.connect() as conn:
        tx=conn.begin()
        def insert(row):
            conn.execute(text("INSERT INTO ods.campaign_rule_stage ("+",".join(row)+") VALUES ("+",".join(":"+k for k in row)+")"),row)
        def current():
            return conn.execute(text("SELECT batch_id FROM ods.campaign_rule_current WHERE store_code='990' AND erp_activity_id='909091'")).scalar()
        try:
            assert current() is None
            insert(head)
            assert current() is None
            with pytest.raises(DBAPIError,match="incomplete"):
                with conn.begin_nested():insert(manifest)
            assert current() is None
            insert(rule)
            with pytest.raises(DBAPIError,match="checksum"):
                with conn.begin_nested():insert({**manifest,"expected_rule_hash":999})
            # PAPI's target uses COPY; verify statement transition tables fire here.
            buffer=io.StringIO();csv.writer(buffer).writerow(manifest.values());buffer.seek(0)
            with conn.connection.cursor() as cursor:
                cursor.copy_expert("COPY ods.campaign_rule_stage ("+",".join(manifest)+") FROM STDIN WITH CSV",buffer)
            assert current()==batch
            report=fetch_rule_summary(conn,cfg)
            assert report["rows"][0]["accept_amount"]==50 and report["rows"][0]["rule_count"]==1
            # A zero-source snapshot really replaces old rules (source deletion).
            empty={**manifest,"batch_id":newer,"source_loaded_at":now+timedelta(seconds=2),"expected_heads":0,"expected_rules":0,"expected_head_hash":0,"expected_rule_hash":0}
            insert(empty)
            assert current()==newer and fetch_rule_summary(conn,cfg)["rows"]==[]
            insert({**empty,"batch_id":stale,"source_loaded_at":now-timedelta(seconds=1)})
            assert current()==newer  # An older run cannot roll the pointer backwards.
        finally:
            tx.rollback()
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM ods.campaign_rule_stage WHERE batch_id IN (:a,:b,:c)"),{"a":batch,"b":newer,"c":stale}).scalar()==0
