import importlib.util
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "python_app"
    / "alembic"
    / "versions"
    / "j8e9f0a1b2c3_add_zhaojia_manual_sports_scope.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("zhaojia_manual_scope_migration", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_upgrade_adds_idempotent_manual_department_scope(monkeypatch):
    migration = _load_migration()
    statements: list[str] = []
    monkeypatch.setattr(migration.op, "execute", statements.append)

    migration.upgrade()

    assert migration.revision == "j8e9f0a1b2c3"
    assert migration.down_revision == "i7d8e9f0a1b2"
    assert len(statements) == 2
    policy_sql = " ".join(statements[0].split())
    item_sql = " ".join(statements[1].split())
    assert "u.username = '1708'" in policy_sql
    assert "u.real_name = '赵佳'" in policy_sql
    assert "'MANUAL'" in policy_sql
    assert "'shopview'" in policy_sql
    assert "manual-business-scope" in policy_sql
    assert "NOT EXISTS" in policy_sql
    assert "'6030114'" in item_sql
    assert "NOT EXISTS" in item_sql


def test_downgrade_removes_only_the_targeted_manual_scope(monkeypatch):
    migration = _load_migration()
    statements: list[str] = []
    monkeypatch.setattr(migration.op, "execute", statements.append)

    migration.downgrade()

    assert len(statements) == 2
    assert all("manual-business-scope" in statement for statement in statements)
    assert "'6030114'" in statements[0]
    assert "NOT EXISTS" in statements[1]
