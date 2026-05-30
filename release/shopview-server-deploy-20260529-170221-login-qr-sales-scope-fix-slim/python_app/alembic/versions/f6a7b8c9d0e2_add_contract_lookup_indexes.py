"""add contract lookup indexes

Revision ID: f6a7b8c9d0e2
Revises: e5f6a7b8c9d1
Create Date: 2026-05-27

"""
from typing import Sequence, Union

from alembic import op


revision: str = "f6a7b8c9d0e2"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_contmain_cmchar9_norm
          ON contmain (upper(trim(COALESCE(cmchar9, ''))));

        CREATE INDEX IF NOT EXISTS idx_contmain_cmcontno_norm
          ON contmain (upper(trim(COALESCE(cmcontno, ''))));

        CREATE INDEX IF NOT EXISTS idx_contmanaframe_cmfmfid_norm
          ON contmanaframe (upper(trim(COALESCE(cmfmfid, ''))));

        CREATE INDEX IF NOT EXISTS idx_contmanaframe_cmfcontno_norm
          ON contmanaframe (upper(trim(COALESCE(cmfcontno, ''))));

        CREATE INDEX IF NOT EXISTS idx_contmanaframe_contno_mfid_norm
          ON contmanaframe (
            upper(trim(COALESCE(cmfcontno, ''))),
            upper(trim(COALESCE(cmfmfid, '')))
          );

        CREATE INDEX IF NOT EXISTS idx_bub_shop_unit_status_contract
          ON business_unit_binding (
            shop_unit_id,
            upper(trim(COALESCE(status, ''))),
            upper(trim(COALESCE(contract_id, '')))
          )
          WHERE COALESCE(trim(contract_id), '') <> '';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS idx_bub_shop_unit_status_contract;
        DROP INDEX IF EXISTS idx_contmanaframe_contno_mfid_norm;
        DROP INDEX IF EXISTS idx_contmanaframe_cmfcontno_norm;
        DROP INDEX IF EXISTS idx_contmanaframe_cmfmfid_norm;
        DROP INDEX IF EXISTS idx_contmain_cmcontno_norm;
        DROP INDEX IF EXISTS idx_contmain_cmchar9_norm;
        """
    )
