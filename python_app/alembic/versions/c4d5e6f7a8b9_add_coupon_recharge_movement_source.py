"""add coupon recharge movement source

Revision ID: c4d5e6f7a8b9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-22
"""
from typing import Sequence, Union

from alembic import op


revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_SQL = r"""
ALTER TABLE activity_coupon_revenue_movement
    ADD COLUMN IF NOT EXISTS source_type VARCHAR(30) NOT NULL DEFAULT 'VOUCHER_MATCH',
    ADD COLUMN IF NOT EXISTS source_key VARCHAR(120);

UPDATE activity_coupon_revenue_movement
SET source_type = 'VOUCHER_MATCH',
    source_key = 'voucher_match:' || voucher_match_id::text
WHERE source_key IS NULL
  AND voucher_match_id IS NOT NULL;

ALTER TABLE activity_coupon_revenue_movement
    ALTER COLUMN voucher_match_id DROP NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_activity_coupon_revenue_movement_source_type'
    ) THEN
        ALTER TABLE activity_coupon_revenue_movement
            ADD CONSTRAINT ck_activity_coupon_revenue_movement_source_type
            CHECK (source_type IN ('VOUCHER_MATCH', 'COUPON_RECHARGE'));
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS ux_activity_coupon_revenue_movement_source
    ON activity_coupon_revenue_movement (source_type, source_key);

COMMENT ON COLUMN activity_coupon_revenue_movement.source_type IS '变动来源：VOUCHER_MATCH 已确认凭证匹配，COUPON_RECHARGE 原始买券充值流水';
COMMENT ON COLUMN activity_coupon_revenue_movement.source_key IS '来源稳定键，用于重建去重';
"""


DOWNGRADE_SQL = r"""
DROP INDEX IF EXISTS ux_activity_coupon_revenue_movement_source;

ALTER TABLE activity_coupon_revenue_movement
    DROP CONSTRAINT IF EXISTS ck_activity_coupon_revenue_movement_source_type;

DELETE FROM activity_coupon_revenue_movement
WHERE source_type = 'COUPON_RECHARGE';

ALTER TABLE activity_coupon_revenue_movement
    ALTER COLUMN voucher_match_id SET NOT NULL;

ALTER TABLE activity_coupon_revenue_movement
    DROP COLUMN IF EXISTS source_key,
    DROP COLUMN IF EXISTS source_type;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
