import importlib.util
import inspect
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_app"))
from routers import stores


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "python_app"
    / "alembic"
    / "versions"
    / "i7d8e9f0a1b2_add_store_multi_business_units.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("multi_business_units_migration", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_multi_business_migration_is_one_per_operating_store(monkeypatch):
    migration = _load_migration()
    statements: list[str] = []
    monkeypatch.setattr(migration.op, "execute", statements.append)

    migration.upgrade()

    assert migration.revision == "i7d8e9f0a1b2"
    assert migration.down_revision == "h6c7d8e9f0a1"
    assert len(statements) == 2
    floor_sql = " ".join(statements[0].split())
    unit_sql = " ".join(statements[1].split())
    assert "existing_floor.store_code = s.store_code" in floor_sql
    assert "existing_floor.floor_code = 'BO'" in floor_sql
    assert "ON CONFLICT (store_code, building_code, floor_code)" in floor_sql
    assert "'多经'" in unit_sql
    assert "ON CONFLICT (floor_id, unit_code)" in unit_sql


def test_multi_business_downgrade_preserves_bound_units(monkeypatch):
    migration = _load_migration()
    statements: list[str] = []
    monkeypatch.setattr(migration.op, "execute", statements.append)

    migration.downgrade()

    assert len(statements) == 1
    assert "business_unit_binding" in statements[0]
    assert "geo_elements" in statements[0]


def test_new_store_creation_ensures_store_logical_units():
    helper_source = inspect.getsource(stores._ensure_store_logical_units)
    create_source = inspect.getsource(stores.create_store)

    assert stores.STORE_LOGICAL_UNIT_CODES == ("后台部门收益", "多经")
    assert "STORE_LOGICAL_UNIT_CODES" in helper_source
    assert "ON CONFLICT (floor_id, unit_code)" in helper_source
    assert "db.flush()" in create_source
    assert "_ensure_store_logical_units(db, db_store.store_code)" in create_source
