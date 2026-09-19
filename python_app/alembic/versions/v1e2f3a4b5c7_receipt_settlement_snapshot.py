"""Local atomic ERP receipt settlement snapshots, published by scheduled PAPI ETL."""
from pathlib import Path
from alembic import op
revision='v1e2f3a4b5c7'
down_revision='u0d1e2f3a4b5'
branch_labels=None
depends_on=None

def upgrade():
    op.execute((Path(__file__).parents[2]/'sql'/'cosmetics_receipt_settlement.sql').read_text())

def downgrade():
    op.execute('DROP TABLE public.cosmetics_receipt_settlement_stage')
    op.execute('DROP FUNCTION public.publish_cosmetics_receipt_settlement()')
    op.execute('DROP TABLE public.cosmetics_receipt_settlement_state')
    op.execute('DROP TABLE public.cosmetics_receipt_settlement_sync')
