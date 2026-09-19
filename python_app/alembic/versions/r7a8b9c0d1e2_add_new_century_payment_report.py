"""Register New Century payment report permission (assignable through role management)."""
from alembic import op
revision = 'r7a8b9c0d1e2'
down_revision = 'q6f7a8b9c0d1'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""INSERT INTO permissions (permission_code, permission_name, module_code, action_code)
    VALUES ('sales.new_century_payments.view', '查看新世纪支付方式销售毛利报表', 'sales', 'new_century_payments_view')
    ON CONFLICT (permission_code) DO NOTHING""")


def downgrade():
    op.execute("""DELETE FROM role_permissions WHERE permission_id IN
    (SELECT id FROM permissions WHERE permission_code = 'sales.new_century_payments.view')""")
    op.execute("DELETE FROM permissions WHERE permission_code = 'sales.new_century_payments.view'")
