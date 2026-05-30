"""replace floors with floor dict table

将原 floors（门店楼层）重命名为 store_floors，新建 floors 楼层字典表。

Revision ID: replace_floors
Revises: 2e35e9cb681f
Create Date: 2026-02-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "replace_floors"
down_revision: Union[str, Sequence[str], None] = "2e35e9cb681f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 删除引用 floors 的外键（PostgreSQL 约束名一般为 表名_列名_fkey）
    # 说明：不同历史库里外键约束名可能不一致；使用 IF EXISTS 保证幂等/可迁移
    op.execute("ALTER TABLE counters DROP CONSTRAINT IF EXISTS counters_floor_id_fkey")
    op.execute("ALTER TABLE halls DROP CONSTRAINT IF EXISTS halls_floor_id_fkey")

    # 2. 原 floors 表重命名为 store_floors
    op.rename_table("floors", "store_floors")

    # 2.1 旧表上的唯一约束/索引名仍可能叫 uq_floors_building_floor，会占用新表要用的名字
    # 不同库里它可能是 constraint，也可能只是 index。这里直接“释放名字”即可：
    op.execute("ALTER TABLE store_floors DROP CONSTRAINT IF EXISTS uq_floors_building_floor")
    op.execute("DROP INDEX IF EXISTS uq_floors_building_floor")

    # 3. 新建楼层字典表 floors
    op.create_table(
        "floors",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("building_code", sa.Text(), nullable=False, server_default="DEFAULT"),
        sa.Column("floor_code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("sort_no", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("building_code", "floor_code", name="uq_floors_building_floor"),
    )
    op.execute("COMMENT ON TABLE floors IS '楼层字典表：统一管理楼层编码、名称与排序'")
    op.execute("COMMENT ON COLUMN floors.id IS '楼层ID，系统主键'")
    op.execute("COMMENT ON COLUMN floors.building_code IS '建筑/项目编码（如百货名称，预留多项目）'")
    op.execute("COMMENT ON COLUMN floors.floor_code IS '楼层编码，如 B1 / 1F / 2F'")
    op.execute("COMMENT ON COLUMN floors.name IS '楼层显示名称'")
    op.execute("COMMENT ON COLUMN floors.sort_no IS '楼层排序号，用于前端展示排序'")
    op.execute("COMMENT ON COLUMN floors.created_at IS '创建时间'")

    # 4. counters / halls 的 floor_id 改引用 store_floors.floor_id
    # 兼容性处理：有的历史库 store_floors 并没有 floor_id 列（可能叫 id），此时跳过外键重建
    op.execute(
        """
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name='counters' AND column_name='floor_id'
  )
  AND EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name='store_floors' AND column_name='floor_id'
  ) THEN
    EXECUTE 'ALTER TABLE counters ADD CONSTRAINT counters_floor_id_fkey FOREIGN KEY(floor_id) REFERENCES store_floors (floor_id)';
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name='halls' AND column_name='floor_id'
  )
  AND EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name='store_floors' AND column_name='floor_id'
  ) THEN
    EXECUTE 'ALTER TABLE halls ADD CONSTRAINT halls_floor_id_fkey FOREIGN KEY(floor_id) REFERENCES store_floors (floor_id)';
  END IF;
END $$;
        """
    )

    # 5. store_floors 增加关联字典表（可选，用于后续按字典展示）
    op.add_column(
        "store_floors",
        sa.Column("floor_dict_id", sa.BigInteger(), sa.ForeignKey("floors.id"), nullable=True, comment="关联楼层字典ID"),
    )


def downgrade() -> None:
    op.drop_column("store_floors", "floor_dict_id")
    op.execute("ALTER TABLE counters DROP CONSTRAINT IF EXISTS counters_floor_id_fkey")
    op.execute("ALTER TABLE halls DROP CONSTRAINT IF EXISTS halls_floor_id_fkey")
    op.drop_table("floors")
    op.rename_table("store_floors", "floors")
    op.create_foreign_key(
        "counters_floor_id_fkey", "counters", "floors", ["floor_id"], ["floor_id"]
    )
    op.create_foreign_key(
        "halls_floor_id_fkey", "halls", "floors", ["floor_id"], ["floor_id"]
    )
