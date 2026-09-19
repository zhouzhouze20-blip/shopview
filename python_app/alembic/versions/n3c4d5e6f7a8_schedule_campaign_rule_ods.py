"""Atomic publication of a complete scheduled PAPI rule snapshot."""
from alembic import op

revision = "n3c4d5e6f7a8"
down_revision = "m2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
      CREATE TABLE ods.campaign_rule_stage AS
      SELECT CAST(NULL AS VARCHAR(36)) batch_id,CAST(NULL AS VARCHAR(3)) store_code,
        CAST(NULL AS VARCHAR(20)) erp_activity_id,CAST(NULL AS VARCHAR(10)) row_kind,
        CAST(NULL AS TEXT) source_key,CAST(NULL AS NUMERIC(10,0)) source_row_hash,
        CAST(NULL AS TIMESTAMPTZ) source_loaded_at,
        CAST(NULL AS BIGINT) expected_heads,CAST(NULL AS BIGINT) expected_rules,
        CAST(NULL AS NUMERIC) expected_head_hash,CAST(NULL AS NUMERIC) expected_rule_hash,
        h.tbfhbillno,h.tbfhpid,h.tbfhmkt,h.tbfhflag,h.tbfhstartdate,h.tbfhenddate,h.tbfhmode,h.tbfhrate,h.tbfhtype,h.tbfhsupid,h.tbfhmanaunit,h.tbfhinputdate,h.tbfhauditdate,h.tbhqxrq,r.tgyrseqno,r.tgyrpid,r.tgyrmode,r.tgyrbarcode,r.tgyrmfid,r.tgyrcatid,r.tgyrppcode,r.tgyrrate,r.tgyrstartdate,r.tgyrenddate,r.tgyrstarttime,r.tgyrendtime,r.tgyrbillno,r.tgyrtype,r.tgyrqtype,r.tgyrtcode,r.tgyrtjje,r.tgyraq,r.tgyrbq,r.tgyrbillid,r.tgyrmanaunit,r.tgyrspsx,r.tgyzkmk
      FROM ods.gpp_tktbgoodsfqhead h CROSS JOIN ods.gpp_tktgoodsyqrate r WITH NO DATA;
      ALTER TABLE ods.campaign_rule_stage
        ADD PRIMARY KEY(batch_id,row_kind,source_key),
        ALTER COLUMN store_code SET NOT NULL,
        ALTER COLUMN erp_activity_id SET NOT NULL,
        ALTER COLUMN source_loaded_at SET NOT NULL,
        ALTER COLUMN source_row_hash SET NOT NULL,
        ADD CHECK(row_kind IN ('head','rule','manifest')),
        ADD CHECK(row_kind<>'manifest' OR (
          source_key='-' AND expected_heads IS NOT NULL AND expected_heads>=0
          AND expected_rules IS NOT NULL AND expected_rules>=0
          AND expected_head_hash IS NOT NULL AND expected_rule_hash IS NOT NULL));
      COMMENT ON TABLE ods.campaign_rule_stage IS
        'PAPI single Oracle statement: source tables then final manifest. Complete batches only are atomically published; no schedules run in the application.';

      CREATE FUNCTION ods.publish_campaign_rule_stage()
      RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,ods AS $$
      DECLARE
        m RECORD;
        v_heads BIGINT;
        v_rules BIGINT;
        v_hhash NUMERIC;
        v_rhash NUMERIC;
      BEGIN
        FOR m IN SELECT * FROM new_rows WHERE row_kind='manifest' LOOP
          PERFORM pg_advisory_xact_lock(862032,m.store_code::INTEGER);
          IF EXISTS(SELECT 1 FROM ods.campaign_rule_batches WHERE batch_id=m.batch_id) THEN
            RAISE EXCEPTION 'Campaign ODS batch already exists';
          END IF;
          SELECT COUNT(*) FILTER(WHERE row_kind='head'),COUNT(*) FILTER(WHERE row_kind='rule'),
            COALESCE(SUM(source_row_hash) FILTER(WHERE row_kind='head'),0),
            COALESCE(SUM(source_row_hash) FILTER(WHERE row_kind='rule'),0)
          INTO v_heads,v_rules,v_hhash,v_rhash
          FROM ods.campaign_rule_stage WHERE batch_id=m.batch_id;
          IF v_heads<>m.expected_heads OR v_rules<>m.expected_rules
            OR v_hhash<>m.expected_head_hash OR v_rhash<>m.expected_rule_hash THEN
            RAISE EXCEPTION 'Campaign ODS incomplete or checksum mismatch';
          END IF;
          IF EXISTS(SELECT 1 FROM ods.campaign_rule_stage s WHERE s.batch_id=m.batch_id AND (
            s.store_code<>m.store_code OR s.erp_activity_id<>m.erp_activity_id
            OR s.source_loaded_at<>m.source_loaded_at
            OR (s.row_kind='head' AND (s.tbfhmkt IS DISTINCT FROM m.store_code
              OR s.tbfhpid IS DISTINCT FROM m.erp_activity_id OR s.source_key IS DISTINCT FROM s.tbfhbillno))
            OR (s.row_kind='rule' AND (s.tgyrpid IS DISTINCT FROM m.erp_activity_id
              OR s.source_key IS DISTINCT FROM s.tgyrseqno::TEXT))
          )) THEN
            RAISE EXCEPTION 'Campaign ODS mixed source snapshot or scope/key mismatch';
          END IF;
          IF EXISTS(SELECT 1 FROM ods.campaign_rule_stage r
            LEFT JOIN ods.campaign_rule_stage h ON h.batch_id=r.batch_id
              AND h.row_kind='head' AND h.tbfhbillno=r.tgyrbillno
            WHERE r.batch_id=m.batch_id AND r.row_kind='rule' AND h.source_key IS NULL) THEN
            RAISE EXCEPTION 'Campaign ODS rule is missing its scoped header';
          END IF;
          INSERT INTO ods.campaign_rule_batches(batch_id,store_code,erp_activity_id,source_started_at)
            VALUES(m.batch_id,m.store_code,m.erp_activity_id,m.source_loaded_at);
          INSERT INTO ods.gpp_tktbgoodsfqhead(batch_id,tbfhbillno,tbfhpid,tbfhmkt,tbfhflag,tbfhstartdate,tbfhenddate,tbfhmode,tbfhrate,tbfhtype,tbfhsupid,tbfhmanaunit,tbfhinputdate,tbfhauditdate,tbhqxrq,source_row_hash,source_loaded_at)
            SELECT batch_id,tbfhbillno,tbfhpid,tbfhmkt,tbfhflag,tbfhstartdate,tbfhenddate,tbfhmode,tbfhrate,tbfhtype,tbfhsupid,tbfhmanaunit,tbfhinputdate,tbfhauditdate,tbhqxrq,source_row_hash,source_loaded_at
            FROM ods.campaign_rule_stage WHERE batch_id=m.batch_id AND row_kind='head';
          INSERT INTO ods.gpp_tktgoodsyqrate(batch_id,tgyrseqno,tgyrpid,tgyrmode,tgyrbarcode,tgyrmfid,tgyrcatid,tgyrppcode,tgyrrate,tgyrstartdate,tgyrenddate,tgyrstarttime,tgyrendtime,tgyrbillno,tgyrtype,tgyrqtype,tgyrtcode,tgyrtjje,tgyraq,tgyrbq,tgyrbillid,tgyrmanaunit,tgyrspsx,tgyzkmk,source_row_hash,source_loaded_at)
            SELECT batch_id,tgyrseqno,tgyrpid,tgyrmode,tgyrbarcode,tgyrmfid,tgyrcatid,tgyrppcode,tgyrrate,tgyrstartdate,tgyrenddate,tgyrstarttime,tgyrendtime,tgyrbillno,tgyrtype,tgyrqtype,tgyrtcode,tgyrtjje,tgyraq,tgyrbq,tgyrbillid,tgyrmanaunit,tgyrspsx,tgyzkmk,source_row_hash,source_loaded_at
            FROM ods.campaign_rule_stage WHERE batch_id=m.batch_id AND row_kind='rule';
          UPDATE ods.campaign_rule_batches SET status='published',published_at=NOW(),
            validation=jsonb_build_object(
              'mode','single_oracle_statement_manifest',
              'head',jsonb_build_object('n',v_heads,'keys',v_heads,'hash_sum',v_hhash),
              'rule',jsonb_build_object('n',v_rules,'keys',v_rules,'hash_sum',v_rhash))
            WHERE batch_id=m.batch_id;
          INSERT INTO ods.campaign_rule_current(store_code,erp_activity_id,batch_id)
            VALUES(m.store_code,m.erp_activity_id,m.batch_id)
            ON CONFLICT(store_code,erp_activity_id) DO UPDATE SET batch_id=EXCLUDED.batch_id
            WHERE (SELECT b.source_started_at FROM ods.campaign_rule_batches b
                   WHERE b.batch_id=ods.campaign_rule_current.batch_id)<m.source_loaded_at;
        END LOOP;
        RETURN NULL;
      END;
      $$;
      CREATE TRIGGER campaign_rule_stage_publish
        AFTER INSERT ON ods.campaign_rule_stage REFERENCING NEW TABLE AS new_rows
        FOR EACH STATEMENT EXECUTE FUNCTION ods.publish_campaign_rule_stage();
    """)


def downgrade():
    op.execute("""
      DROP TRIGGER campaign_rule_stage_publish ON ods.campaign_rule_stage;
      DROP FUNCTION ods.publish_campaign_rule_stage();
      DROP TABLE ods.campaign_rule_stage;
    """)
