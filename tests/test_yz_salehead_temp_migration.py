from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "python_app"
    / "alembic"
    / "versions"
    / "b8d4e6f0a2c3_create_yz_salehead_temp.py"
)


def _load_migration():
    spec = spec_from_file_location("yz_salehead_temp_migration", MIGRATION_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_yz_salehead_temp_uses_exact_numeric_amount_columns():
    migration = _load_migration()
    sql = migration.CREATE_YZ_SALEHEAD_TEMP_SQL.upper()

    assert "L_PRICE NUMERIC(18, 4)" in sql
    assert "L_TOTAL_FEE NUMERIC(18, 4)" in sql
    assert "L_BY4 NUMERIC(18, 4)" in sql
    assert "DOUBLE PRECISION" not in sql


def test_yz_salehead_temp_reconciles_existing_amount_column_types():
    migration = _load_migration()
    sql = migration.CREATE_YZ_SALEHEAD_TEMP_SQL.upper()

    assert "ALTER TABLE PUBLIC.YZ_SALEHEAD_TEMP" in sql
    assert "ALTER COLUMN L_PRICE TYPE NUMERIC(18, 4)" in sql
    assert "ALTER COLUMN L_TOTAL_FEE TYPE NUMERIC(18, 4)" in sql
    assert "ALTER COLUMN L_BY4 TYPE NUMERIC(18, 4)" in sql
