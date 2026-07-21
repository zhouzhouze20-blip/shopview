import importlib.util
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = (
    ROOT
    / "python_app"
    / "alembic"
    / "versions"
    / "d1b3c5e7f9a2_create_jxcgoodslist.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("jxcgoodslist_migration", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_jxcgoodslist_migration_matches_papi_target_contract():
    migration = _load_migration()
    normalized = " ".join(migration.UPGRADE_SQL.lower().split())
    table_body = re.search(
        r"create table if not exists jxcgoodslist \((.*)\); comment on table",
        normalized,
    )

    assert migration.revision == "d1b3c5e7f9a2"
    assert migration.down_revision == "c1a4e7b9d2f6"
    assert table_body is not None
    columns = re.findall(
        r"(?:^|,)\s*([a-z][a-z0-9_]*) (?:varchar|char|numeric|timestamp)",
        table_body.group(1),
    )
    assert len(columns) == 124
    assert len(set(columns)) == 124
    assert "constraint pk_jxcgoodslist primary key (jglseq)" in normalized
    assert "idx_jxcgoodslist_jglfsdate" in normalized
    assert "idx_jxcgoodslist_mfid_fsdate" in normalized


def test_jxcgoodslist_downgrade_targets_only_the_sync_table(monkeypatch):
    migration = _load_migration()
    statements = []
    monkeypatch.setattr(migration.op, "execute", statements.append)

    migration.downgrade()

    assert statements == ["DROP TABLE IF EXISTS jxcgoodslist CASCADE"]
