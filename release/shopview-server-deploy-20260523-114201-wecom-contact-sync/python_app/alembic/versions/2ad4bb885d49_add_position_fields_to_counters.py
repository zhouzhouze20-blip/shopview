"""add_position_fields_to_counters

Revision ID: 2ad4bb885d49
Revises: create_geometry_tables
Create Date: 2025-09-09 17:00:10.776651

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2ad4bb885d49'
down_revision: Union[str, Sequence[str], None] = 'create_geometry_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add position and size fields to counters table."""
    # 添加位置和尺寸字段到counters表
    op.add_column('counters', sa.Column('position_x', sa.Numeric(10, 2), nullable=True, comment='X坐标位置'))
    op.add_column('counters', sa.Column('position_y', sa.Numeric(10, 2), nullable=True, comment='Y坐标位置'))
    op.add_column('counters', sa.Column('width', sa.Numeric(10, 2), nullable=True, comment='宽度'))
    op.add_column('counters', sa.Column('height', sa.Numeric(10, 2), nullable=True, comment='高度'))
    
    # 为现有数据设置默认值
    op.execute("UPDATE counters SET position_x = 0 WHERE position_x IS NULL")
    op.execute("UPDATE counters SET position_y = 0 WHERE position_y IS NULL")
    op.execute("UPDATE counters SET width = 10 WHERE width IS NULL")
    op.execute("UPDATE counters SET height = 10 WHERE height IS NULL")


def downgrade() -> None:
    """Remove position and size fields from counters table."""
    op.drop_column('counters', 'height')
    op.drop_column('counters', 'width')
    op.drop_column('counters', 'position_y')
    op.drop_column('counters', 'position_x')
