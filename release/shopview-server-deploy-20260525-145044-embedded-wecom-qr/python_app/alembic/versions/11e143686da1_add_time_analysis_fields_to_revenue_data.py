"""add_time_analysis_fields_to_revenue_data

Revision ID: 11e143686da1
Revises: 2ad4bb885d49
Create Date: 2025-09-15 11:24:03.987685

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '11e143686da1'
down_revision: Union[str, Sequence[str], None] = '2ad4bb885d49'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 为revenue_data表添加时间分析字段
    op.add_column('revenue_data', sa.Column('year', sa.Integer(), nullable=True, comment='年份'))
    op.add_column('revenue_data', sa.Column('month', sa.Integer(), nullable=True, comment='月份'))
    op.add_column('revenue_data', sa.Column('day', sa.Integer(), nullable=True, comment='日期'))
    op.add_column('revenue_data', sa.Column('date', sa.Date(), nullable=True, comment='完整日期'))
    
    # 添加同期对比字段
    op.add_column('revenue_data', sa.Column('same_period_sales', sa.Numeric(precision=10, scale=2), nullable=True, comment='同期销售'))
    op.add_column('revenue_data', sa.Column('same_period_date', sa.Date(), nullable=True, comment='同期日期'))
    op.add_column('revenue_data', sa.Column('same_period_revenue', sa.Numeric(precision=10, scale=2), nullable=True, comment='同期收益'))
    op.add_column('revenue_data', sa.Column('year_over_year', sa.Numeric(precision=5, scale=2), nullable=True, comment='同比（百分比）'))
    
    # 添加索引以提高查询性能
    op.create_index('idx_revenue_data_year_month', 'revenue_data', ['year', 'month'])
    op.create_index('idx_revenue_data_date', 'revenue_data', ['date'])
    op.create_index('idx_revenue_data_same_period_date', 'revenue_data', ['same_period_date'])


def downgrade() -> None:
    """Downgrade schema."""
    # 删除索引
    op.drop_index('idx_revenue_data_same_period_date', table_name='revenue_data')
    op.drop_index('idx_revenue_data_date', table_name='revenue_data')
    op.drop_index('idx_revenue_data_year_month', table_name='revenue_data')
    
    # 删除字段
    op.drop_column('revenue_data', 'year_over_year')
    op.drop_column('revenue_data', 'same_period_revenue')
    op.drop_column('revenue_data', 'same_period_date')
    op.drop_column('revenue_data', 'same_period_sales')
    op.drop_column('revenue_data', 'date')
    op.drop_column('revenue_data', 'day')
    op.drop_column('revenue_data', 'month')
    op.drop_column('revenue_data', 'year')
