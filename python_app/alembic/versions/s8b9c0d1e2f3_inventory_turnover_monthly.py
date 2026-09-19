"""Persist monthly inventory turnover snapshots and register read permission."""
from pathlib import Path
from alembic import op

revision = 's8b9c0d1e2f3'
down_revision = 'r7a8b9c0d1e2'
branch_labels = None
depends_on = None


def upgrade():
    op.execute((Path(__file__).parents[2] / 'sql' / 'inventory_turnover.sql').read_text())


def downgrade():
    op.execute('DROP FUNCTION IF EXISTS inventory_turnover_rows(integer,integer,date)')
    op.execute('DROP TABLE IF EXISTS inventory_turnover_monthly')
    op.execute("DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE permission_code='sales.inventory_turnover.view')")
    op.execute("DELETE FROM permissions WHERE permission_code='sales.inventory_turnover.view'")
