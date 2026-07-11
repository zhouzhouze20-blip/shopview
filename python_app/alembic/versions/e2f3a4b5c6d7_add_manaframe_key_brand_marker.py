"""create manaframe key brand marker table

Revision ID: e2f3a4b5c6d7
Revises: d5e6f7a8b9c0
Create Date: 2026-07-08
"""
from typing import Sequence, Union

from alembic import op


revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, Sequence[str], None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS manaframe_key_brand (
            mfcode VARCHAR(20) NOT NULL,
            is_key_brand BOOLEAN DEFAULT FALSE NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_by VARCHAR(100),
            CONSTRAINT pk_manaframe_key_brand PRIMARY KEY (mfcode)
        );

        COMMENT ON TABLE manaframe_key_brand IS '本地维护的柜组重点品牌标记';
        COMMENT ON COLUMN manaframe_key_brand.mfcode IS '柜组编码，对应 manaframe.mfcode';
        COMMENT ON COLUMN manaframe_key_brand.is_key_brand IS '是否重点品牌柜组';
        COMMENT ON COLUMN manaframe_key_brand.updated_at IS '最后更新时间';
        COMMENT ON COLUMN manaframe_key_brand.updated_by IS '最后维护人';
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS manaframe_key_brand;")
