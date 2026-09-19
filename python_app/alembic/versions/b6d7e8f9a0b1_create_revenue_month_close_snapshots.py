"""create revenue month-close snapshots

Revision ID: b6d7e8f9a0b1
Revises: a5c6d7e8f9a0
Create Date: 2026-08-06
"""
from typing import Sequence, Union

from alembic import op


revision: str = "b6d7e8f9a0b1"
down_revision: Union[str, Sequence[str], None] = "a5c6d7e8f9a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE revenue_month_closes (
          id BIGSERIAL PRIMARY KEY,
          store_id INTEGER NOT NULL REFERENCES stores(store_id),
          period_month VARCHAR(7) NOT NULL,
          period_start_date DATE NOT NULL,
          period_end_date DATE NOT NULL,
          version INTEGER NOT NULL DEFAULT 1,
          status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
          nc_amount_before_tax NUMERIC(18, 2) NOT NULL DEFAULT 0,
          accrued_tax_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
          nc_control_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
          raw_fee_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
          raw_extra_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
          close_adjustment_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
          final_fee_extra_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
          source_snapshot_id VARCHAR(120) NOT NULL,
          source_file_name VARCHAR(255),
          note TEXT,
          created_by INTEGER REFERENCES users(user_id),
          confirmed_by INTEGER REFERENCES users(user_id),
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          confirmed_at TIMESTAMPTZ,
          raw_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
          CONSTRAINT ck_revenue_month_closes_month
            CHECK (period_month ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'),
          CONSTRAINT ck_revenue_month_closes_dates
            CHECK (period_end_date >= period_start_date),
          CONSTRAINT ck_revenue_month_closes_status
            CHECK (status IN ('DRAFT', 'CONFIRMED', 'REOPENED')),
          CONSTRAINT uq_revenue_month_closes_version
            UNIQUE (store_id, period_month, version),
          CONSTRAINT uq_revenue_month_closes_snapshot
            UNIQUE (source_snapshot_id)
        );

        CREATE UNIQUE INDEX ux_revenue_month_closes_confirmed
          ON revenue_month_closes(store_id, period_start_date, period_end_date)
          WHERE status = 'CONFIRMED';

        CREATE INDEX ix_revenue_month_closes_period
          ON revenue_month_closes(period_start_date, period_end_date, status);

        CREATE TABLE revenue_month_close_adjustments (
          id BIGSERIAL PRIMARY KEY,
          month_close_id BIGINT NOT NULL
            REFERENCES revenue_month_closes(id) ON DELETE CASCADE,
          target_component VARCHAR(20) NOT NULL,
          adjustment_category VARCHAR(60) NOT NULL,
          unit_id BIGINT REFERENCES business_units(id),
          unit_code TEXT,
          source_group_code VARCHAR(50),
          source_group_name VARCHAR(200),
          source_department_code VARCHAR(50),
          source_department_name VARCHAR(200),
          source_subject_code VARCHAR(50),
          source_subject_name VARCHAR(200),
          source_business_type VARCHAR(30),
          supplier_code VARCHAR(50),
          supplier_name VARCHAR(255),
          fee_type_code VARCHAR(50),
          fee_type_name VARCHAR(200),
          raw_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
          accrued_tax_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
          adjustment_amount NUMERIC(18, 2) NOT NULL,
          final_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
          allocation_basis TEXT,
          adjustment_reason TEXT,
          source_row_key VARCHAR(160),
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          raw_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
          CONSTRAINT ck_revenue_month_close_adjustments_component
            CHECK (target_component IN ('FEE', 'EXTRA'))
        );

        CREATE INDEX ix_revenue_month_close_adjustments_close
          ON revenue_month_close_adjustments(month_close_id);
        CREATE INDEX ix_revenue_month_close_adjustments_group
          ON revenue_month_close_adjustments(month_close_id, source_group_code);
        CREATE INDEX ix_revenue_month_close_adjustments_department
          ON revenue_month_close_adjustments(
            month_close_id,
            source_department_code,
            source_subject_code
          );

        COMMENT ON TABLE revenue_month_closes IS
          '收益看板月结控制快照；已确认版本用于指定门店和期间的NC6051含计提税口径';
        COMMENT ON TABLE revenue_month_close_adjustments IS
          '月结快照的柜位或后台部门调整明细；不覆盖富基收费和NC补收原始行';
        COMMENT ON COLUMN revenue_month_closes.nc_control_amount IS
          'NC6051不含计提税金额加计提税净额后的月结控制数';
        COMMENT ON COLUMN revenue_month_closes.final_fee_extra_amount IS
          '富基收费和NC非富基收费应用月结调整后的合计，应等于NC控制数';
        COMMENT ON COLUMN revenue_month_close_adjustments.target_component IS
          '调整归属：FEE富基收费收益，EXTRA为NC非富基其他收益';
        COMMENT ON COLUMN revenue_month_close_adjustments.adjustment_amount IS
          '对原始金额的增减；原始行保持不变，看板查询时叠加';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS revenue_month_close_adjustments;
        DROP TABLE IF EXISTS revenue_month_closes;
        """
    )
