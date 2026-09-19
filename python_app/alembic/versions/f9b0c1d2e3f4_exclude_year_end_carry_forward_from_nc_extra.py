"""Exclude year-end carry-forward rows from NC6051 extra receipts.

Revision ID: f9b0c1d2e3f4
Revises: e9a0b1c2d3e4
"""

from typing import Sequence, Union

from alembic import op


revision: str = "f9b0c1d2e3f4"
down_revision: Union[str, Sequence[str], None] = "e9a0b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        r"""
        DO $migration$
        DECLARE
          function_definition TEXT;
          old_filter CONSTANT TEXT := 'AND NOT (explanation ~ ''计提.*(销项)?税|电费收入结转销项税'')';
          new_filter CONSTANT TEXT := 'AND NOT (explanation ~ ''计提.*(销项)?税|电费收入结转销项税'' OR (account_period::INTEGER = 12 AND BTRIM(explanation) = ''期间结转''))';
        BEGIN
          SELECT pg_get_functiondef(proc.oid)
            INTO function_definition
          FROM pg_proc proc
          JOIN pg_namespace namespace ON namespace.oid = proc.pronamespace
          WHERE namespace.nspname = 'public'
            AND proc.proname = 'refresh_nc_6051_extra_receipts'
            AND proc.pronargs = 3;

          IF function_definition IS NULL THEN
            RAISE EXCEPTION 'refresh_nc_6051_extra_receipts(date,date,varchar) does not exist';
          END IF;
          IF POSITION(old_filter IN function_definition) = 0 THEN
            RAISE EXCEPTION 'Expected NC6051 tax filter was not found';
          END IF;

          EXECUTE REPLACE(function_definition, old_filter, new_filter);
        END
        $migration$;
        """
    )


def downgrade() -> None:
    op.execute(
        r"""
        DO $migration$
        DECLARE
          function_definition TEXT;
          old_filter CONSTANT TEXT := 'AND NOT (explanation ~ ''计提.*(销项)?税|电费收入结转销项税'' OR (account_period::INTEGER = 12 AND BTRIM(explanation) = ''期间结转''))';
          new_filter CONSTANT TEXT := 'AND NOT (explanation ~ ''计提.*(销项)?税|电费收入结转销项税'')';
        BEGIN
          SELECT pg_get_functiondef(proc.oid)
            INTO function_definition
          FROM pg_proc proc
          JOIN pg_namespace namespace ON namespace.oid = proc.pronamespace
          WHERE namespace.nspname = 'public'
            AND proc.proname = 'refresh_nc_6051_extra_receipts'
            AND proc.pronargs = 3;

          IF function_definition IS NULL THEN
            RAISE EXCEPTION 'refresh_nc_6051_extra_receipts(date,date,varchar) does not exist';
          END IF;

          EXECUTE REPLACE(function_definition, old_filter, new_filter);
        END
        $migration$;
        """
    )
