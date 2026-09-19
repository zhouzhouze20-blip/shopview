"""Persist brand-counter summaries and refresh after detail writes."""
from pathlib import Path
from alembic import op

revision = 't9c0d1e2f3a4'
down_revision = 's8b9c0d1e2f3'
branch_labels = None
depends_on = None


def upgrade():
    op.execute((Path(__file__).parents[2] / 'sql' / 'inventory_turnover_brand.sql').read_text())


def downgrade():
    for action in ('insert', 'update', 'delete'):
        op.execute(f'DROP TRIGGER IF EXISTS turnover_brand_{action} ON public.inventory_turnover_monthly')
    op.execute('DROP FUNCTION IF EXISTS public.sync_inventory_turnover_brand()')
    op.execute('DROP FUNCTION IF EXISTS public.refresh_inventory_turnover_brand(text)')
    op.execute('DROP FUNCTION IF EXISTS public.inventory_turnover_brand_rows(text)')
    op.execute('DROP TABLE IF EXISTS public.inventory_turnover_brand_monthly')
