"""为 floors 楼层字典表增加门店编码 store_code（601/602/603/604）

Revision ID: add_store_code_floors
Revises: replace_floors
Create Date: 2026-02-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_store_code_floors"
down_revision: Union[str, Sequence[str], None] = "replace_floors"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 添加门店编码列（可空，便于已有数据迁移）
    op.add_column(
        "floors",
        sa.Column("store_code", sa.String(10), nullable=True, comment="门店编码：601/602/603/604"),
    )
    op.execute("COMMENT ON COLUMN floors.store_code IS '门店编码：601/602/603/604'")

    # 2. 删除原唯一约束，改为按 门店+栋号+楼层 唯一
    op.drop_constraint("uq_floors_building_floor", "floors", type_="unique")
    op.create_unique_constraint(
        "uq_floors_store_building_floor",
        "floors",
        ["store_code", "building_code", "floor_code"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_floors_store_building_floor", "floors", type_="unique")
    op.create_unique_constraint(
        "uq_floors_building_floor",
        "floors",
        ["building_code", "floor_code"],
    )
    op.drop_column("floors", "store_code")
