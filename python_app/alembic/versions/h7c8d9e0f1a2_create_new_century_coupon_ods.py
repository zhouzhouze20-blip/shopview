"""Create local ODS tables for New Century CRM coupons.

Revision ID: h7c8d9e0f1a2
Revises: g6b7c8d9e0f1
"""

from typing import Sequence, Union

from alembic import op


revision: str = "h7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "g6b7c8d9e0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ods")
    op.execute(
        """
        CREATE TABLE ods.crm_coupon_template_603 (
          id BIGINT PRIMARY KEY,
          name TEXT,
          money NUMERIC(20, 4),
          coupon_type VARCHAR(40),
          min_money NUMERIC(20, 4),
          rule SMALLINT,
          start_date_time TIMESTAMP,
          end_date_time TIMESTAMP,
          use_time_type SMALLINT,
          use_start_time TIMESTAMP,
          use_end_time TIMESTAMP,
          status SMALLINT,
          channel TEXT,
          discount NUMERIC(20, 4),
          discount_rate NUMERIC(20, 8),
          exchange_point BIGINT,
          third_party_id BIGINT,
          third_party_no TEXT,
          issue_limit BIGINT,
          issue_limit_per_member BIGINT,
          issued_count BIGINT,
          redeemed_count BIGINT,
          dept_ids TEXT,
          dept_names TEXT,
          tenant_id BIGINT NOT NULL,
          source_create_time TIMESTAMP,
          source_update_time TIMESTAMP,
          deleted SMALLINT,
          source_dt TIMESTAMP,
          source_loaded_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_crm_coupon_template_603_type "
        "ON ods.crm_coupon_template_603 (coupon_type, deleted)"
    )
    op.execute(
        "CREATE INDEX ix_crm_coupon_template_603_updated "
        "ON ods.crm_coupon_template_603 (source_update_time, id)"
    )

    op.execute(
        """
        CREATE TABLE ods.crm_coupon_record_603 (
          coupon_code BIGINT PRIMARY KEY,
          template_id BIGINT NOT NULL,
          use_start_time TIMESTAMP,
          use_end_time TIMESTAMP,
          rule_id BIGINT,
          scene_code TEXT,
          status SMALLINT,
          used_status SMALLINT,
          used_date_time TIMESTAMP,
          used_channel SMALLINT,
          used_order TEXT,
          used_order_money NUMERIC(20, 4),
          used_order_coupon_money NUMERIC(20, 4),
          used_order_discount NUMERIC(20, 4),
          mem_id BIGINT,
          mem_mobile VARCHAR(64),
          mem_name TEXT,
          level_code VARCHAR(40),
          coupon_money NUMERIC(20, 4),
          coupon_money_left NUMERIC(20, 4),
          third_cno BIGINT,
          tenant_id BIGINT NOT NULL,
          source_create_time TIMESTAMP,
          source_update_time TIMESTAMP,
          deleted SMALLINT,
          source_dt TIMESTAMP,
          source_loaded_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_crm_coupon_record_603_used "
        "ON ods.crm_coupon_record_603 (used_date_time, template_id)"
    )
    op.execute(
        "CREATE INDEX ix_crm_coupon_record_603_member_used "
        "ON ods.crm_coupon_record_603 (mem_mobile, used_date_time)"
    )
    op.execute(
        "CREATE INDEX ix_crm_coupon_record_603_updated "
        "ON ods.crm_coupon_record_603 (source_update_time, coupon_code)"
    )

    op.execute(
        "COMMENT ON TABLE ods.crm_coupon_template_603 IS "
        "'PAPI source 8 ods_crm.ods_coupon_template rows for tenant 603'"
    )
    op.execute(
        "COMMENT ON TABLE ods.crm_coupon_record_603 IS "
        "'PAPI source 8 ods_crm.ods_coupon_record_603 coupon lifecycle rows'"
    )
    op.execute(
        "COMMENT ON COLUMN ods.crm_coupon_record_603.mem_mobile IS "
        "'CRM member mobile; restricted activity analysis join key and masked in UI'"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ods.crm_coupon_record_603")
    op.execute("DROP TABLE IF EXISTS ods.crm_coupon_template_603")
