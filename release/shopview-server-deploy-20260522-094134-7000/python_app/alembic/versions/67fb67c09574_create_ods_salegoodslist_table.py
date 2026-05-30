"""create_ods_salegoodslist_table

Revision ID: 67fb67c09574
Revises: 33ee1d968ad9
Create Date: 2025-09-16 15:29:42.595436

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '67fb67c09574'
down_revision: Union[str, Sequence[str], None] = '33ee1d968ad9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 创建ODS_SALEGOODSLIST表
    op.create_table(
        'ods_salegoodslist',
        sa.Column('sgldate', sa.Date(), nullable=False, comment='销售日期'),
        sa.Column('sgltpid', sa.CHAR(2), nullable=False, comment='终端ID'),
        sa.Column('sglsummary', sa.VARCHAR(10), nullable=False, comment='汇总码'),
        sa.Column('sglmarket', sa.VARCHAR(20), nullable=False, comment='市场'),
        sa.Column('sglmfid', sa.VARCHAR(20), nullable=False, comment='厂商ID'),
        sa.Column('sglgdid', sa.VARCHAR(20), nullable=False, comment='商品ID'),
        sa.Column('sglbarcode', sa.VARCHAR(20), nullable=False, comment='条码'),
        sa.Column('sglgdtype', sa.CHAR(1), nullable=False, comment='商品类型'),
        sa.Column('sglcatid', sa.VARCHAR(10), nullable=False, comment='类别ID'),
        sa.Column('sgltaxtype', sa.CHAR(1), nullable=False, comment='税种类型'),
        sa.Column('sglxstax', sa.Numeric(8, 4), nullable=False, comment='销售税率'),
        sa.Column('sglxftax', sa.Numeric(8, 4), nullable=False, comment='消费税率'),
        sa.Column('sglppcode', sa.VARCHAR(10), nullable=False, comment='促销代码'),
        sa.Column('sgluid', sa.VARCHAR(6), nullable=False, default='00', comment='用户ID'),
        sa.Column('sglhsrq', sa.Date(), nullable=False, comment='核算日期'),
        sa.Column('sglbatchno', sa.VARCHAR(20), nullable=False, default='0', comment='批次号'),
        sa.Column('sglsupid', sa.VARCHAR(20), nullable=False, comment='供应商ID'),
        sa.Column('sglanalcode', sa.VARCHAR(20), nullable=True, comment='分析代码'),
        sa.Column('sglsj', sa.Numeric(16, 4), nullable=False, comment='售价'),
        sa.Column('sglkl', sa.Numeric(5, 4), nullable=False, comment='扣率'),
        sa.Column('sgljs', sa.Numeric(16, 4), nullable=False, comment='结算价'),
        sa.Column('sglsl', sa.Numeric(16, 4), nullable=False, comment='数量'),
        sa.Column('sglsjje', sa.Numeric(16, 4), nullable=False, comment='售价金额'),
        sa.Column('sglxssr', sa.Numeric(16, 4), nullable=False, comment='销售收入'),
        sa.Column('sglxsse', sa.Numeric(16, 4), nullable=False, comment='销售税额'),
        sa.Column('sglxfse', sa.Numeric(16, 4), nullable=False, comment='消费税额'),
        sa.Column('sglqtsr', sa.Numeric(16, 4), nullable=False, comment='其他收入'),
        sa.Column('sglsysy', sa.Numeric(16, 4), nullable=False, comment='损益收入'),
        sa.Column('sglpopsr', sa.Numeric(16, 4), nullable=False, comment='POP收入'),
        sa.Column('sglcustsr', sa.Numeric(16, 4), nullable=False, comment='客户收入'),
        sa.Column('sglfcdsr', sa.Numeric(16, 4), nullable=False, comment='返厂单收入'),
        sa.Column('sglpfsr', sa.Numeric(16, 4), nullable=False, comment='批发收入'),
        sa.Column('sglyxssr', sa.Numeric(16, 4), nullable=False, comment='有效销售收入'),
        sa.Column('sgltotzk', sa.Numeric(16, 4), nullable=False, comment='总折扣'),
        sa.Column('sglsupzk', sa.Numeric(16, 4), nullable=False, comment='供应商折扣'),
        sa.Column('sglpopzk', sa.Numeric(16, 4), nullable=False, comment='POP折扣'),
        sa.Column('sglcustzk', sa.Numeric(16, 4), nullable=False, comment='客户折扣'),
        sa.Column('sglfcdzk', sa.Numeric(16, 4), nullable=False, comment='返厂单折扣'),
        sa.Column('sglpfzk', sa.Numeric(16, 4), nullable=False, comment='批发折扣'),
        sa.Column('sglgrantzk', sa.Numeric(16, 4), nullable=False, comment='授权折扣'),
        sa.Column('sglyjhx', sa.Numeric(16, 4), nullable=False, comment='优惠活动'),
        sa.Column('sglzszk', sa.Numeric(16, 4), nullable=False, comment='赠送折扣'),
        sa.Column('sglthss', sa.Numeric(16, 4), nullable=False, comment='退货损失'),
        sa.Column('sgladjustzk', sa.Numeric(16, 4), nullable=False, comment='调整折扣'),
        sa.Column('sglcash', sa.Numeric(16, 4), nullable=False, comment='现金'),
        sa.Column('sglcheck', sa.Numeric(16, 4), nullable=False, comment='支票'),
        sa.Column('sglccard', sa.Numeric(16, 4), nullable=False, comment='信用卡'),
        sa.Column('sglfcard', sa.Numeric(16, 4), nullable=False, comment='储值卡'),
        sa.Column('sglgcert', sa.Numeric(16, 4), nullable=False, comment='购物券'),
        sa.Column('sglgzje', sa.Numeric(16, 4), nullable=False, comment='购物券金额'),
        sa.Column('sglopay', sa.Numeric(16, 4), nullable=False, comment='其他支付'),
        sa.Column('sgltimes', sa.Numeric(16, 4), nullable=True, comment='次数'),
        sa.Column('sgln1', sa.Numeric(16, 4), nullable=True, comment='数值1'),
        sa.Column('sgln2', sa.Numeric(16, 4), nullable=True, comment='数值2'),
        sa.Column('sgln3', sa.Numeric(16, 4), nullable=True, comment='数值3'),
        sa.Column('sgln4', sa.Numeric(16, 4), nullable=True, comment='数值4'),
        sa.Column('sgln5', sa.Numeric(16, 4), nullable=True, comment='数值5'),
        sa.Column('sglvc1', sa.VARCHAR(20), nullable=True, comment='字符1'),
        sa.Column('sglvc2', sa.VARCHAR(20), nullable=True, comment='字符2'),
        sa.Column('sglvc3', sa.VARCHAR(64), nullable=True, comment='字符3'),
        sa.Column('sglwmid', sa.CHAR(1), nullable=False, default='1', comment='仓库ID'),
        sa.Column('sglfqje', sa.Numeric(16, 4), nullable=True, default=0, comment='分期金额'),
        sa.Column('sglsqje', sa.Numeric(16, 4), nullable=True, default=0, comment='申请金额'),
        sa.Column('sglqxssr', sa.Numeric(16, 4), nullable=True, default=0, comment='取消销售收入'),
        sa.Column('sgln6', sa.Numeric(16, 4), nullable=True, comment='数值6'),
        sa.Column('sgln7', sa.Numeric(16, 4), nullable=True, comment='数值7'),
        sa.Column('sgln8', sa.Numeric(16, 4), nullable=True, comment='数值8'),
        sa.Column('sgln9', sa.Numeric(16, 4), nullable=True, comment='数值9'),
        sa.Column('sgln10', sa.Numeric(16, 4), nullable=True, comment='数值10'),
        sa.Column('sglxyksr1', sa.Numeric(16, 4), nullable=True, default=0, comment='信用卡收入1'),
        sa.Column('sglxyksr2', sa.Numeric(16, 4), nullable=True, default=0, comment='信用卡收入2'),
        sa.Column('sglxyksr3', sa.Numeric(16, 4), nullable=True, default=0, comment='信用卡收入3'),
        sa.Column('sglxyksr4', sa.Numeric(16, 4), nullable=True, default=0, comment='信用卡收入4'),
        sa.Column('sglxyksr5', sa.Numeric(16, 4), nullable=True, default=0, comment='信用卡收入5'),
        sa.Column('sglxyksr6', sa.Numeric(16, 4), nullable=True, default=0, comment='信用卡收入6'),
        sa.Column('sglxyksr7', sa.Numeric(16, 4), nullable=True, default=0, comment='信用卡收入7'),
        sa.Column('sglxyksr8', sa.Numeric(16, 4), nullable=True, default=0, comment='信用卡收入8'),
        sa.Column('sglxyksr9', sa.Numeric(16, 4), nullable=True, default=0, comment='信用卡收入9'),
        sa.Column('sglxyksr10', sa.Numeric(16, 4), nullable=True, default=0, comment='信用卡收入10'),
        sa.Column('sglbillno', sa.Numeric(), nullable=False, comment='单据号'),
        sa.Column('sglrowno', sa.Numeric(), nullable=False, comment='行号'),
        sa.Column('sglbasekl', sa.Numeric(5, 4), nullable=True, comment='基础扣率'),
        sa.Column('sgln11', sa.Numeric(), nullable=True, comment='数值11'),
        sa.Column('sgln12', sa.Numeric(), nullable=True, comment='数值12'),
        sa.Column('sgln13', sa.Numeric(), nullable=True, comment='数值13'),
        sa.Column('sgln14', sa.Numeric(), nullable=True, comment='数值14'),
        sa.Column('sgln15', sa.Numeric(), nullable=True, comment='数值15'),
        sa.Column('sgln16', sa.Numeric(), nullable=True, comment='数值16'),
        sa.Column('sgln17', sa.Numeric(), nullable=True, comment='数值17'),
        sa.Column('sgln18', sa.Numeric(), nullable=True, comment='数值18'),
        sa.Column('sgln19', sa.Numeric(), nullable=True, comment='数值19'),
        sa.Column('sgln20', sa.Numeric(), nullable=True, comment='数值20'),
        sa.Column('sgln21', sa.Numeric(), nullable=True, comment='数值21'),
        sa.Column('sgln22', sa.Numeric(), nullable=True, comment='数值22'),
        sa.Column('sgln23', sa.Numeric(), nullable=True, comment='数值23'),
        sa.Column('sgln24', sa.Numeric(), nullable=True, comment='数值24'),
        sa.Column('sgln25', sa.Numeric(), nullable=True, comment='数值25'),
        sa.Column('sglvc4', sa.VARCHAR(20), nullable=True, comment='字符4'),
        sa.Column('sglvc5', sa.VARCHAR(20), nullable=True, comment='字符5'),
        sa.Column('sglvc6', sa.VARCHAR(20), nullable=True, comment='字符6'),
        sa.Column('sglvc7', sa.VARCHAR(20), nullable=True, comment='字符7'),
        sa.Column('sglvc8', sa.VARCHAR(20), nullable=True, comment='字符8'),
        sa.Column('sglvc9', sa.VARCHAR(20), nullable=True, comment='字符9'),
        sa.Column('sglvc10', sa.VARCHAR(20), nullable=True, comment='字符10'),
        sa.Column('sglvc11', sa.VARCHAR(20), nullable=True, comment='字符11'),
        sa.Column('sglvc12', sa.VARCHAR(20), nullable=True, comment='字符12'),
        sa.Column('sglvc13', sa.VARCHAR(20), nullable=True, comment='字符13'),
        sa.Column('sglvc14', sa.VARCHAR(20), nullable=True, comment='字符14'),
        sa.Column('sglvc15', sa.VARCHAR(20), nullable=True, comment='字符15'),
        sa.Column('sglsaledate', sa.Date(), nullable=True, comment='销售日期'),
        sa.Column('sglnetml', sa.Numeric(), nullable=True, comment='网络毛利'),
        sa.Column('sglcardtype', sa.VARCHAR(10), nullable=True, comment='卡类型'),
        sa.Column('sglyjid', sa.VARCHAR(20), nullable=True, comment='业务员ID'),
        sa.Column('sglinvno', sa.Numeric(), nullable=True, comment='发票号'),
        sa.Column('sglchecker', sa.VARCHAR(20), nullable=True, comment='审核人'),
        sa.Column('sglposcls', sa.CHAR(1), nullable=True, comment='POS分类'),
        sa.Column('sglshdate', sa.Date(), nullable=True, comment='审核日期'),
        sa.Column('sgltmtype', sa.CHAR(1), nullable=True, default='0', comment='终端类型'),
        sa.Column('sglmd', sa.CHAR(1), nullable=True, default='1', comment='模式'),
        sa.Column('sglfysl', sa.Numeric(16, 4), nullable=True, comment='返佣数量'),
        sa.Column('sglvip1sr', sa.Numeric(16, 4), nullable=True, comment='VIP1收入'),
        sa.Column('sglvip2sr', sa.Numeric(16, 4), nullable=True, comment='VIP2收入'),
        sa.Column('sglvip3sr', sa.Numeric(16, 4), nullable=True, comment='VIP3收入'),
        sa.Column('sglvip4sr', sa.Numeric(16, 4), nullable=True, comment='VIP4收入'),
        sa.Column('sglvip5sr', sa.Numeric(16, 4), nullable=True, comment='VIP5收入'),
        sa.Column('sglxykfy1', sa.Numeric(), nullable=True, comment='信用卡费用1'),
        sa.Column('sglxykfy2', sa.Numeric(), nullable=True, comment='信用卡费用2'),
        sa.Column('sglxykfy3', sa.Numeric(), nullable=True, comment='信用卡费用3'),
        sa.Column('sglxykfy4', sa.Numeric(), nullable=True, comment='信用卡费用4'),
        sa.Column('sglxykfy5', sa.Numeric(), nullable=True, comment='信用卡费用5'),
        sa.Column('sglxykfy6', sa.Numeric(), nullable=True, comment='信用卡费用6'),
        sa.Column('sglxykfy7', sa.Numeric(), nullable=True, comment='信用卡费用7'),
        sa.Column('sglxykfy8', sa.Numeric(), nullable=True, comment='信用卡费用8'),
        sa.Column('sglxykfy9', sa.Numeric(), nullable=True, comment='信用卡费用9'),
        sa.Column('sglxykfy10', sa.Numeric(), nullable=True, comment='信用卡费用10'),
        sa.Column('sglspsx', sa.VARCHAR(20), nullable=True, default='0', comment='商品属性'),
        sa.Column('sgljjtax', sa.Numeric(8, 4), nullable=True, comment='基金税'),
        sa.Column('sgln26', sa.Numeric(), nullable=True, comment='数值26'),
        sa.Column('sgln27', sa.Numeric(), nullable=True, comment='数值27'),
        sa.Column('sgln28', sa.Numeric(), nullable=True, comment='数值28'),
        sa.Column('sgln29', sa.Numeric(), nullable=True, comment='数值29'),
        comment='销售商品清单表'
    )
    
    # 添加复合主键约束
    op.create_primary_key(
        'pk_ods_salegoodslist',
        'ods_salegoodslist',
        ['sgldate', 'sgltpid', 'sglsummary', 'sglmarket', 
         'sglmfid', 'sglgdid', 'sglbarcode', 'sglbillno', 'sglrowno']
    )


def downgrade() -> None:
    """Downgrade schema."""
    # 删除ODS_SALEGOODSLIST表
    op.drop_table('ods_salegoodslist')
