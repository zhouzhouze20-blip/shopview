"""Append-only campaign asset ownership confirmations; no automatic seed."""
from alembic import op

revision='q6f7a8b9c0d1'
down_revision='p5e6f7a8b9c0'
branch_labels=None
depends_on=None

def upgrade():
    op.execute("""CREATE TABLE coupon_campaign_ownership (
      id BIGSERIAL PRIMARY KEY,
      campaign_id BIGINT NOT NULL REFERENCES coupon_campaigns(id),
      version INTEGER NOT NULL CHECK(version>0),
      snapshot JSONB NOT NULL,
      note TEXT NOT NULL,
      confirmed_by INTEGER NOT NULL,
      confirmed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      UNIQUE(campaign_id,version)
    )""")

def downgrade():
    op.execute('DROP TABLE coupon_campaign_ownership')
