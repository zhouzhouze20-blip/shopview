"""Versioned GPP coupon-rule ODS; only validated batches become visible."""
from alembic import op

revision = "m2b3c4d5e6f7"
down_revision = "l1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
      CREATE SCHEMA IF NOT EXISTS ods;
      CREATE TABLE ods.campaign_rule_batches (
        batch_id VARCHAR(36) PRIMARY KEY,
        store_code VARCHAR(3) NOT NULL,
        erp_activity_id VARCHAR(20) NOT NULL,
        status VARCHAR(16) NOT NULL DEFAULT 'loading' CHECK(status IN ('loading','published')),
        source_started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        published_at TIMESTAMPTZ,
        validation JSONB,
        head_task_id INTEGER,
        rule_task_id INTEGER
      );
      CREATE TABLE ods.gpp_tktbgoodsfqhead (
        batch_id VARCHAR(36) NOT NULL REFERENCES ods.campaign_rule_batches(batch_id),
        tbfhbillno VARCHAR(20) NOT NULL,
        tbfhpid VARCHAR(20) NOT NULL,
        tbfhmkt VARCHAR(20) NOT NULL,
        tbfhflag VARCHAR(1) NOT NULL,
        tbfhstartdate TIMESTAMP NOT NULL,
        tbfhenddate TIMESTAMP NOT NULL,
        tbfhmode VARCHAR(1),
        tbfhrate NUMERIC(5,4),
        tbfhtype VARCHAR(1),
        tbfhsupid VARCHAR(20),
        tbfhmanaunit VARCHAR(20) NOT NULL,
        tbfhinputdate TIMESTAMP NOT NULL,
        tbfhauditdate TIMESTAMP,
        tbhqxrq TIMESTAMP,
        source_row_hash NUMERIC(10,0) NOT NULL,
        source_loaded_at TIMESTAMPTZ NOT NULL,
        PRIMARY KEY(batch_id,tbfhbillno)
      );
      CREATE TABLE ods.gpp_tktgoodsyqrate (
        batch_id VARCHAR(36) NOT NULL REFERENCES ods.campaign_rule_batches(batch_id),
        tgyrseqno NUMERIC NOT NULL,
        tgyrpid VARCHAR(10) NOT NULL,
        tgyrmode VARCHAR(1) NOT NULL,
        tgyrbarcode VARCHAR(20) NOT NULL,
        tgyrmfid VARCHAR(20),
        tgyrcatid VARCHAR(10),
        tgyrppcode VARCHAR(20),
        tgyrrate NUMERIC(5,4) NOT NULL,
        tgyrstartdate TIMESTAMP NOT NULL,
        tgyrenddate TIMESTAMP NOT NULL,
        tgyrstarttime VARCHAR(5) NOT NULL,
        tgyrendtime VARCHAR(5) NOT NULL,
        tgyrbillno VARCHAR(20),
        tgyrtype VARCHAR(1),
        tgyrqtype VARCHAR(1),
        tgyrtcode VARCHAR(20),
        tgyrtjje NUMERIC,
        tgyraq NUMERIC,
        tgyrbq NUMERIC,
        tgyrbillid VARCHAR(20) NOT NULL,
        tgyrmanaunit VARCHAR(20) NOT NULL,
        tgyrspsx VARCHAR(10),
        tgyzkmk NUMERIC,
        source_row_hash NUMERIC(10,0) NOT NULL,
        source_loaded_at TIMESTAMPTZ NOT NULL,
        PRIMARY KEY(batch_id,tgyrseqno)
      );
      CREATE INDEX ix_campaign_ods_rule_scope
        ON ods.gpp_tktgoodsyqrate(batch_id,tgyrpid,tgyrqtype,tgyrstartdate);
      CREATE TABLE ods.campaign_rule_current (
        store_code VARCHAR(3) NOT NULL,
        erp_activity_id VARCHAR(20) NOT NULL,
        batch_id VARCHAR(36) NOT NULL REFERENCES ods.campaign_rule_batches(batch_id),
        PRIMARY KEY(store_code,erp_activity_id)
      );
      COMMENT ON TABLE ods.campaign_rule_current IS
        'Atomic pointer to a fully validated PAPI batch; never use max loaded_at to select a partial batch';
      COMMENT ON TABLE ods.gpp_tktgoodsyqrate IS
        'DBUSRPOP.TKTGOODSYQRATE full snapshot per store and ERP activity, retained by batch for cancellation safety';
    """)


def downgrade():
    op.execute("""
      DROP TABLE ods.campaign_rule_current;
      DROP TABLE ods.gpp_tktgoodsyqrate;
      DROP TABLE ods.gpp_tktbgoodsfqhead;
      DROP TABLE ods.campaign_rule_batches;
    """)
