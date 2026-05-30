"""add_sglgdname_field_to_ods_salegoodslist

Revision ID: 2e35e9cb681f
Revises: 67fb67c09574
Create Date: 2025-09-17 14:08:09.907493

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e35e9cb681f'
down_revision: Union[str, Sequence[str], None] = '67fb67c09574'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 为 ods_salegoodslist 表添加 sglgdname 字段
    op.add_column('ods_salegoodslist', 
                  sa.Column('sglgdname', sa.VARCHAR(255), nullable=True, comment='商品名称'))


def downgrade() -> None:
    """Downgrade schema."""
    # 删除 sglgdname 字段
    op.drop_column('ods_salegoodslist', 'sglgdname')
