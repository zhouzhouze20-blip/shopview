"""Business coupon campaigns. No source ERP writes or automatic campaign seeding."""
from alembic import op

revision = "l1a2b3c4d5e6"
down_revision = "k0f1a2b3c4d5"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
      CREATE TABLE coupon_campaigns (
        id BIGSERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        store_code VARCHAR(3) NOT NULL,
        start_date DATE NOT NULL,
        end_date DATE NOT NULL CHECK(end_date>=start_date AND end_date-start_date<=365),
        coupon_types TEXT[] NOT NULL CHECK(cardinality(coupon_types)>0),
        erp_activity_id VARCHAR(20) NOT NULL DEFAULT '',
        notes TEXT NOT NULL DEFAULT '',
        rule_snapshot JSONB,
        created_by INTEGER NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      );
      CREATE INDEX ix_coupon_campaign_store_period ON coupon_campaigns(store_code,start_date,end_date);
      INSERT INTO permissions(permission_code,permission_name,module_code,action_code) VALUES
        ('activity_analysis.campaign.view','查看活动建档分析','activity_analysis','campaign_view'),
        ('activity_analysis.campaign.manage','维护活动建档及规则快照','activity_analysis','campaign_manage')
      ON CONFLICT(permission_code) DO NOTHING;
      INSERT INTO role_permissions(role_id,permission_id,created_at)
      SELECT DISTINCT rp.role_id,target.id,NOW() FROM role_permissions rp
      JOIN permissions source ON source.id=rp.permission_id AND source.permission_code='activity_analysis.view'
      CROSS JOIN permissions target WHERE target.permission_code='activity_analysis.campaign.view'
      ON CONFLICT DO NOTHING;
    """)


def downgrade():
    op.execute("""
      DROP TABLE coupon_campaigns;
      DELETE FROM role_permissions WHERE permission_id IN
        (SELECT id FROM permissions WHERE permission_code IN ('activity_analysis.campaign.view','activity_analysis.campaign.manage'));
      DELETE FROM permissions WHERE permission_code IN ('activity_analysis.campaign.view','activity_analysis.campaign.manage');
    """)
