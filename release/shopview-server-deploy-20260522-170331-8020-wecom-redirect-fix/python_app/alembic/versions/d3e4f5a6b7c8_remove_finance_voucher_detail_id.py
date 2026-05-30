"""remove finance voucher detail synthetic id

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-05-19
"""
from typing import Sequence, Union

from alembic import op


revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, Sequence[str], None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_SQL = r"""
ALTER TABLE activity_coupon_voucher_match
    DROP CONSTRAINT IF EXISTS activity_coupon_voucher_match_voucher_detail_id_fkey;

ALTER TABLE activity_coupon_voucher_match
    DROP CONSTRAINT IF EXISTS ux_activity_coupon_voucher_match_business_voucher;

TRUNCATE TABLE activity_coupon_voucher_match RESTART IDENTITY;
TRUNCATE TABLE bh_dw_gl_detail_fact2;

ALTER TABLE bh_dw_gl_detail_fact2
    DROP CONSTRAINT IF EXISTS pk_bh_dw_gl_detail_fact2;

ALTER TABLE bh_dw_gl_detail_fact2
    DROP COLUMN IF EXISTS id;

ALTER TABLE activity_coupon_voucher_match
    ALTER COLUMN voucher_detail_id TYPE VARCHAR(32);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ux_activity_coupon_voucher_match_business_voucher'
    ) THEN
        ALTER TABLE activity_coupon_voucher_match
            ADD CONSTRAINT ux_activity_coupon_voucher_match_business_voucher
            UNIQUE (business_date, business_store_code, coupon_type, match_type, voucher_detail_id);
    END IF;
END $$;

COMMENT ON COLUMN activity_coupon_voucher_match.voucher_detail_id IS
    '按 bh_dw_gl_detail_fact2 凭证明细业务字段拼接后 md5 生成的稳定匹配键';
"""


DOWNGRADE_SQL = r"""
ALTER TABLE activity_coupon_voucher_match
    DROP CONSTRAINT IF EXISTS ux_activity_coupon_voucher_match_business_voucher;

TRUNCATE TABLE activity_coupon_voucher_match RESTART IDENTITY;

ALTER TABLE bh_dw_gl_detail_fact2
    ADD COLUMN IF NOT EXISTS id VARCHAR(50) NOT NULL DEFAULT md5(random()::text);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'pk_bh_dw_gl_detail_fact2'
    ) THEN
        ALTER TABLE bh_dw_gl_detail_fact2
            ADD CONSTRAINT pk_bh_dw_gl_detail_fact2 PRIMARY KEY (id);
    END IF;
END $$;

ALTER TABLE activity_coupon_voucher_match
    ALTER COLUMN voucher_detail_id TYPE VARCHAR(50);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'activity_coupon_voucher_match_voucher_detail_id_fkey'
    ) THEN
        ALTER TABLE activity_coupon_voucher_match
            ADD CONSTRAINT activity_coupon_voucher_match_voucher_detail_id_fkey
            FOREIGN KEY (voucher_detail_id) REFERENCES bh_dw_gl_detail_fact2(id) ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ux_activity_coupon_voucher_match_business_voucher'
    ) THEN
        ALTER TABLE activity_coupon_voucher_match
            ADD CONSTRAINT ux_activity_coupon_voucher_match_business_voucher
            UNIQUE (business_date, business_store_code, coupon_type, match_type, voucher_detail_id);
    END IF;
END $$;

COMMENT ON COLUMN activity_coupon_voucher_match.voucher_detail_id IS
    'bh_dw_gl_detail_fact2.id，使用本系统同步记录ID而非可能重复的pk_detail';
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
