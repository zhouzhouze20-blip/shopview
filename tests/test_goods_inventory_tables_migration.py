import importlib.util
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = (
    ROOT
    / "python_app"
    / "alembic"
    / "versions"
    / "c1a4e7b9d2f6_create_goods_stock_tables.py"
)
GOODSCAT_MIGRATION_PATH = (
    ROOT
    / "python_app"
    / "alembic"
    / "versions"
    / "9d0e1f2a3b4c_create_codebrand_goodscat.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("goods_inventory_migration", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _column_names(create_sql: str, table_name: str) -> set[str]:
    match = re.search(
        rf"CREATE TABLE {table_name}\s*\((.*?)\n\);",
        create_sql,
        flags=re.IGNORECASE | re.DOTALL,
    )
    assert match is not None
    return {
        column_match.group(1).lower()
        for line in match.group(1).splitlines()
        if (
            column_match := re.match(
                r"^\s{4}([a-z][a-z0-9_]*)\s+"
                r"(?:VARCHAR|CHAR|NUMERIC|TIMESTAMP)\b",
                line,
                flags=re.IGNORECASE,
            )
        )
    }


def test_existing_goodscat_migration_matches_supplied_structure():
    sql = GOODSCAT_MIGRATION_PATH.read_text(encoding="utf-8").lower()

    assert "create table if not exists goodscat" in sql
    assert "constraint pk_goodscat primary key (catcode)" in sql
    assert "create index if not exists idx_cat_cname" in sql
    assert "create index if not exists idx_cat_mfid" in sql
    assert "create index if not exists idx_cat_pcode" in sql
    assert "create index if not exists idx_s_catpcode" in sql


def test_goods_stock_migration_preserves_source_contract():
    migration = _load_migration()
    sql = migration.UPGRADE_SQL

    assert migration.revision == "c1a4e7b9d2f6"
    assert migration.down_revision == "b8d4e6f0a2c3"
    assert len(_column_names(sql, "goodsstock")) == 37
    assert len(_column_names(sql, "goodsstock_bak")) == 41

    normalized = " ".join(sql.lower().split())
    assert (
        "constraint pk_goodsstock primary key "
        "( gstgdid, gstmfid, gstsupid, gstwmid, gstmd, gstshelf, gstsample )"
    ) in normalized
    assert (
        "constraint pk_goodsstock_bak primary key "
        "( gstdate, gstgdid, gstmfid, gstsupid, gstwmid, gstmd, gstshelf, gstsample )"
    ) in normalized

    for default in (
        "gstmd char(1) default '1' not null",
        "gstshelf varchar(20) default '0' not null",
        "gstsample char(1) default 'n' not null",
    ):
        assert normalized.count(default) == 2

    for index_name in (
        "index_gst_market",
        "index_gst_mfcode",
        "index_gst_sup",
        "index_gstb_gstdate",
        "index_gstb_market",
        "index_gstb_mfcode",
        "index_gstb_sup",
    ):
        assert f"create index {index_name}" in normalized


def test_goods_stock_downgrade_only_removes_new_tables(monkeypatch):
    migration = _load_migration()
    statements = []
    monkeypatch.setattr(migration.op, "execute", statements.append)

    migration.downgrade()

    assert statements == [migration.DOWNGRADE_SQL]
    normalized = " ".join(migration.DOWNGRADE_SQL.lower().split())
    assert "drop table if exists goodsstock_bak" in normalized
    assert "drop table if exists goodsstock" in normalized
    assert "goodscat" not in normalized.replace("goodsstock_bak", "").replace("goodsstock", "")
