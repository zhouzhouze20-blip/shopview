"""set month close business-unit foreign key to SET NULL

Revision ID: j9e0f1a2b3c4
Revises: i8d9e0f1a2b3
Create Date: 2026-08-20
"""

from alembic import op


revision = "j9e0f1a2b3c4"
down_revision = "i8d9e0f1a2b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE revenue_month_close_adjustments
          DROP CONSTRAINT IF EXISTS revenue_month_close_adjustments_unit_id_fkey;

        ALTER TABLE revenue_month_close_adjustments
          ADD CONSTRAINT revenue_month_close_adjustments_unit_id_fkey
          FOREIGN KEY (unit_id)
          REFERENCES business_units(id)
          ON DELETE SET NULL;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE revenue_month_close_adjustments
          DROP CONSTRAINT IF EXISTS revenue_month_close_adjustments_unit_id_fkey;

        ALTER TABLE revenue_month_close_adjustments
          ADD CONSTRAINT revenue_month_close_adjustments_unit_id_fkey
          FOREIGN KEY (unit_id)
          REFERENCES business_units(id);
        """
    )
