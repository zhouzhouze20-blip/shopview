"""Opt-in, rolled-back integration checks against migrated ODS tables."""
import os
from pathlib import Path
import sys
from uuid import uuid4

import pytest
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_app"))
from services.activity_analysis.campaign_erp import fetch_rule_summary, RuleSourceError

pytestmark = pytest.mark.skipif(os.getenv("SHOPVIEW_TEST_ODS_DATABASE") != "1", reason="Explicit rollback-only DB test opt-in required")


def test_local_batch_scope_cancellation_and_partial_load_are_isolated():
    from models.database import engine
    cfg = dict(store_code="990", erp_activity_id="909090", coupon_types=["B"], start_date="2026-08-14", end_date="2026-08-19")
    old, new = str(uuid4()), str(uuid4())
    with engine.connect() as conn:
        tx=conn.begin()
        try:
            assert conn.execute(text("SELECT COUNT(*) FROM ods.campaign_rule_current WHERE store_code='990' AND erp_activity_id='909090'")).scalar()==0
            for batch in (old,new):
                conn.execute(text("""INSERT INTO ods.campaign_rule_batches(batch_id,store_code,erp_activity_id,status,published_at,validation)
                  VALUES(:b,'990','909090','loading',NOW(),'{}')"""), {"b":batch})
                conn.execute(text("""INSERT INTO ods.gpp_tktbgoodsfqhead
                  (batch_id,tbfhbillno,tbfhpid,tbfhmkt,tbfhflag,tbfhstartdate,tbfhenddate,tbfhmanaunit,tbfhinputdate,source_row_hash,source_loaded_at)
                  SELECT :b,'QA-'||v.id,'909090',v.store,v.flag,'2026-08-14','2026-08-19','002',NOW(),1,NOW()
                  FROM (VALUES('good','990','Y'),('canceled','990','Q'),('other-store','991','Y')) v(id,store,flag)"""),{"b":batch})
                conn.execute(text("""INSERT INTO ods.gpp_tktgoodsyqrate
                  (batch_id,tgyrseqno,tgyrpid,tgyrmode,tgyrbarcode,tgyrrate,tgyrstartdate,tgyrenddate,tgyrstarttime,tgyrendtime,tgyrbillno,tgyrtype,tgyrqtype,tgyrtjje,tgyraq,tgyrbillid,tgyrmanaunit,source_row_hash,source_loaded_at)
                  SELECT :b,v.id,'909090','2','ALL',0,'2026-08-14','2026-08-19','00:00','23:59','QA-'||v.head,'6',v.coupon,600,v.amount,'QS6','002',1,NOW()
                  FROM (VALUES(1,'good','B',50),(2,'canceled','B',500),(3,'other-store','B',5000),(4,'good','E',100)) v(id,head,coupon,amount)"""),{"b":batch})
            conn.execute(text("INSERT INTO ods.campaign_rule_current VALUES('990','909090',:b)"),{"b":old})
            with pytest.raises(RuleSourceError,match="尚未完成"):
                fetch_rule_summary(conn,cfg)
            conn.execute(text("UPDATE ods.campaign_rule_batches SET status='published' WHERE batch_id=:b"),{"b":old})
            result=fetch_rule_summary(conn,cfg)
            assert result["ods_batch_id"]==old and len(result["rows"])==1
            assert result["rows"][0]["rule_count"]==1 and result["rows"][0]["accept_amount"]==50
            # A new loading batch does not contaminate the old published result.
            conn.execute(text("UPDATE ods.gpp_tktgoodsyqrate SET tgyraq=9000 WHERE batch_id=:b"),{"b":new})
            assert fetch_rule_summary(conn,cfg)["rows"][0]["accept_amount"]==50
            # Canceled rules are absent after a complete new batch is selected;
            # no historical rows need to be deleted to stop counting them.
            conn.execute(text("UPDATE ods.gpp_tktbgoodsfqhead SET tbfhflag='Q' WHERE batch_id=:b"),{"b":new})
            conn.execute(text("UPDATE ods.campaign_rule_batches SET status='published' WHERE batch_id=:b"),{"b":new})
            conn.execute(text("UPDATE ods.campaign_rule_current SET batch_id=:b WHERE store_code='990' AND erp_activity_id='909090'"),{"b":new})
            assert fetch_rule_summary(conn,cfg)["rows"]==[]
            assert conn.execute(text("SELECT COUNT(*) FROM ods.gpp_tktgoodsyqrate WHERE batch_id=:b"),{"b":old}).scalar()==4
        finally:
            tx.rollback()
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM ods.campaign_rule_batches WHERE batch_id IN (:a,:b)"),{"a":old,"b":new}).scalar()==0
