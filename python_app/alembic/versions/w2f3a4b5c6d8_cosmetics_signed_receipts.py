"""Allow signed receipt lines while keeping invoices and payment totals positive."""
from alembic import op

revision = 'w2f3a4b5c6d8'
down_revision = 'v1e2f3a4b5c7'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('ALTER TABLE cosmetics_payment_match_lines DROP CONSTRAINT cosmetics_payment_match_lines_amount_check')
    op.execute('''ALTER TABLE cosmetics_payment_match_lines ADD CONSTRAINT cosmetics_payment_match_lines_amount_check
        CHECK ((kind='invoice' AND amount>0) OR (kind='receipt' AND amount<>0))''')
    with op.get_context().autocommit_block():
        op.execute('''CREATE INDEX CONCURRENTLY IF NOT EXISTS cosmetics_return_lookup_idx
            ON jxcgoodslist(jglmarket,jglsupid,jglbillno)
            WHERE jgltran='2' AND jglbillid='409' ''')


def downgrade():
    # Existing signed matches must be retained. Refuse downgrade if they exist.
    op.execute('ALTER TABLE cosmetics_payment_match_lines DROP CONSTRAINT cosmetics_payment_match_lines_amount_check')
    op.execute('ALTER TABLE cosmetics_payment_match_lines ADD CONSTRAINT cosmetics_payment_match_lines_amount_check CHECK(amount>0)')
    op.execute('DROP INDEX IF EXISTS cosmetics_return_lookup_idx')
