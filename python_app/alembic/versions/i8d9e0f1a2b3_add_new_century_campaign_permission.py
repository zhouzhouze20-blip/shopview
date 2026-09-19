"""Add New Century campaign dashboard permission.

Revision ID: i8d9e0f1a2b3
Revises: h7c8d9e0f1a2
"""

from typing import Sequence, Union

from alembic import op


revision: str = "i8d9e0f1a2b3"
down_revision: Union[str, Sequence[str], None] = "h7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO permissions (permission_code, permission_name, module_code, action_code)
        VALUES (
          'activity_analysis.new_century_campaign.view',
          '查看新世纪活动分析',
          'activity_analysis',
          'new_century_campaign_view'
        )
        ON CONFLICT (permission_code) DO UPDATE SET
          permission_name = EXCLUDED.permission_name,
          module_code = EXCLUDED.module_code,
          action_code = EXCLUDED.action_code;

        INSERT INTO role_permissions (role_id, permission_id, created_at)
        SELECT existing.role_id, target.id, NOW()
        FROM role_permissions existing
        JOIN permissions source ON source.id = existing.permission_id
          AND source.permission_code = 'activity_analysis.view'
        CROSS JOIN permissions target
        WHERE target.permission_code = 'activity_analysis.new_century_campaign.view'
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions WHERE permission_id = (
          SELECT id FROM permissions WHERE permission_code = 'activity_analysis.new_century_campaign.view'
        );
        DELETE FROM permissions WHERE permission_code = 'activity_analysis.new_century_campaign.view';
        """
    )
