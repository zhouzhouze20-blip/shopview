import importlib.util
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "python_app"
    / "alembic"
    / "versions"
    / "g5b6c7d8e9f0_add_store_backoffice_revenue_units.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("backoffice_revenue_units_migration", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_backoffice_revenue_migration_is_one_per_operating_store(monkeypatch):
    migration = _load_migration()
    statements: list[str] = []
    monkeypatch.setattr(migration.op, "execute", statements.append)

    migration.upgrade()

    assert migration.revision == "g5b6c7d8e9f0"
    assert migration.down_revision == "f4a5b6c7d8e9"
    assert len(statements) == 2
    floor_sql = " ".join(statements[0].split())
    unit_sql = " ".join(statements[1].split())
    assert "EXISTS ( SELECT 1 FROM floors existing_floor" in floor_sql
    assert "ON CONFLICT (store_code, building_code, floor_code)" in floor_sql
    assert "'后台部门收益'" in unit_sql
    assert "ON CONFLICT (floor_id, unit_code)" in unit_sql


def test_backoffice_revenue_downgrade_preserves_bound_units(monkeypatch):
    migration = _load_migration()
    statements: list[str] = []
    monkeypatch.setattr(migration.op, "execute", statements.append)

    migration.downgrade()

    assert len(statements) == 2
    assert "business_unit_binding" in statements[0]
    assert "geo_elements" in statements[0]
    assert "NOT EXISTS" in statements[1]
