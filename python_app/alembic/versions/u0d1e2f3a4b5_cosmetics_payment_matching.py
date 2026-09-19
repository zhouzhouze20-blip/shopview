"""Whole-document cosmetics payment matching with globally unique source locks."""
from alembic import op
revision='u0d1e2f3a4b5'
down_revision='t9c0d1e2f3a4'
branch_labels=None
depends_on=None


def upgrade():
    # Posted purchases are a small subset of the movement ledger. Build without
    # blocking ERP synchronization writes during the index scan.
    with op.get_context().autocommit_block():
        op.execute("""CREATE INDEX CONCURRENTLY IF NOT EXISTS cosmetics_receipt_lookup_idx
          ON jxcgoodslist(jglmarket,jglsupid,jglbillno)
          WHERE jgltran='1' AND jglbillid='404'""")
    op.execute('''CREATE TABLE IF NOT EXISTS cosmetics_payment_matches (
      number varchar(40) PRIMARY KEY,
      store_code varchar(3) NOT NULL CHECK(store_code IN ('601','602','603')),
      supplier_code text NOT NULL, payment_month varchar(7) NOT NULL
        CHECK(payment_month ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'),
      invoice_amount numeric NOT NULL CHECK(invoice_amount>0),
      receipt_amount numeric NOT NULL CHECK(receipt_amount>0),
      difference numeric NOT NULL CHECK(abs(difference)<=1),
      created_by integer NOT NULL REFERENCES users(user_id),
      created_at timestamptz NOT NULL DEFAULT now(),
      CHECK(difference=invoice_amount-receipt_amount)
    )''')
    op.execute('''CREATE TABLE IF NOT EXISTS cosmetics_payment_match_lines (
      id bigserial PRIMARY KEY,
      match_number varchar(40) NOT NULL REFERENCES cosmetics_payment_matches(number),
      kind varchar(10) NOT NULL CHECK(kind IN ('invoice','receipt')),
      source_key text NOT NULL, document_number text NOT NULL,
      amount numeric NOT NULL CHECK(amount>0), snapshot jsonb NOT NULL,
      UNIQUE(kind,source_key)
    )''')
    op.execute('CREATE INDEX IF NOT EXISTS cosmetics_match_lines_header_idx ON cosmetics_payment_match_lines(match_number)')
    op.execute('CREATE INDEX IF NOT EXISTS cosmetics_matches_filter_idx ON cosmetics_payment_matches(store_code,supplier_code,payment_month)')
    op.execute("""INSERT INTO permissions(permission_code,permission_name,module_code,action_code)
      VALUES ('settlement.cosmetics_matching.view','查看化妆品付款配票','settlement','cosmetics_matching_view'),
      ('settlement.cosmetics_matching.create','生成化妆品付款配票','settlement','cosmetics_matching_create')
      ON CONFLICT(permission_code) DO NOTHING""")


def downgrade():
    op.execute('DROP INDEX IF EXISTS cosmetics_receipt_lookup_idx')
    op.execute('DROP TABLE cosmetics_payment_match_lines')
    op.execute('DROP TABLE cosmetics_payment_matches')
    op.execute("DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE permission_code LIKE 'settlement.cosmetics_matching.%')")
    op.execute("DELETE FROM permissions WHERE permission_code LIKE 'settlement.cosmetics_matching.%'")
