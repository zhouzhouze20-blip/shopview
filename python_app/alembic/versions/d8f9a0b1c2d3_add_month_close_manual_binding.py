"""add manual binding state for revenue month-close differences

Revision ID: d8f9a0b1c2d3
Revises: c7e8f9a0b1c2
Create Date: 2026-08-07
"""
from typing import Sequence, Union

from alembic import op


revision: str = "d8f9a0b1c2d3"
down_revision: Union[str, Sequence[str], None] = "c7e8f9a0b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE revenue_month_close_adjustments
          ADD COLUMN binding_status VARCHAR(20) NOT NULL DEFAULT 'BOUND',
          ADD COLUMN bound_by INTEGER REFERENCES users(user_id),
          ADD COLUMN bound_at TIMESTAMPTZ,
          ADD COLUMN binding_note TEXT,
          ADD COLUMN parent_adjustment_id BIGINT
            REFERENCES revenue_month_close_adjustments(id),
          ADD CONSTRAINT ck_revenue_month_close_adjustments_binding_status
            CHECK (binding_status IN ('PENDING', 'BOUND'));

        CREATE INDEX ix_revenue_month_close_adjustments_pending
          ON revenue_month_close_adjustments(month_close_id, binding_status, id);

        COMMENT ON COLUMN revenue_month_close_adjustments.binding_status IS
          'PENDING待人工绑定柜位；BOUND已确认归属并叠加到收益看板';
        COMMENT ON COLUMN revenue_month_close_adjustments.binding_note IS
          '人工绑定时填写的核对说明；不覆盖NC或富基来源明细';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS ix_revenue_month_close_adjustments_pending;
        ALTER TABLE revenue_month_close_adjustments
          DROP CONSTRAINT IF EXISTS ck_revenue_month_close_adjustments_binding_status,
          DROP COLUMN IF EXISTS binding_note,
          DROP COLUMN IF EXISTS parent_adjustment_id,
          DROP COLUMN IF EXISTS bound_at,
          DROP COLUMN IF EXISTS bound_by,
          DROP COLUMN IF EXISTS binding_status;
        """
    )
