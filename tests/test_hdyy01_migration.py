import importlib.util
from pathlib import Path

import sqlalchemy as sa


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = (
    ROOT
    / "python_app"
    / "alembic"
    / "versions"
    / "c7d8e9f0a1b2_create_mana_brand_hierarchy.py"
)
SOURCE_SQL_PATH = ROOT / "docs" / "sql" / "hdyy01_mana_brand_hierarchy_source.sql"


def _load_migration():
    spec = importlib.util.spec_from_file_location("hdyy01_migration", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RecordingOp:
    def __init__(self):
        self.created_table = None
        self.created_indexes = []
        self.dropped_indexes = []
        self.dropped_tables = []

    def create_table(self, name, *elements, **kwargs):
        self.created_table = (name, elements, kwargs)

    def create_index(self, name, table_name, columns, **kwargs):
        self.created_indexes.append((name, table_name, columns, kwargs))

    def drop_index(self, name, **kwargs):
        self.dropped_indexes.append((name, kwargs))

    def drop_table(self, name, **kwargs):
        self.dropped_tables.append((name, kwargs))


def test_migration_creates_hdyy01_hierarchy_dimension(monkeypatch):
    migration = _load_migration()
    recorder = RecordingOp()
    monkeypatch.setattr(migration, "op", recorder)

    assert migration.revision == "c7d8e9f0a1b2"
    assert migration.down_revision == "b3c4d5e6f7a8"

    migration.upgrade()

    table_name, elements, options = recorder.created_table
    assert table_name == "mana_brand_hierarchy"
    assert "HDYY01" in options["comment"]
    assert "BIBH.ODS_MANABRAND" in options["comment"]

    columns = {element.name: element for element in elements if isinstance(element, sa.Column)}
    expected_lengths = {
        "level1_code": 100,
        "level1_name": 100,
        "level2_code": 100,
        "level2_name": 100,
        "level3_code": 100,
        "level3_name": 100,
        "grade_code": 10,
        "grade_label": 1,
    }
    assert set(columns) == {*expected_lengths, "etl_loaded_at"}
    for name, length in expected_lengths.items():
        assert isinstance(columns[name].type, sa.String)
        assert columns[name].type.length == length

    for name in (
        "level1_code",
        "level1_name",
        "level2_code",
        "level2_name",
        "level3_code",
        "level3_name",
    ):
        assert columns[name].nullable is False
    assert columns["grade_code"].nullable is True
    assert columns["grade_label"].nullable is True
    assert columns["level3_code"].primary_key is True
    assert isinstance(columns["etl_loaded_at"].type, sa.TIMESTAMP)
    assert columns["etl_loaded_at"].nullable is False
    assert str(columns["etl_loaded_at"].server_default.arg).lower() == "now()"

    checks = [element for element in elements if isinstance(element, sa.CheckConstraint)]
    assert len(checks) == 1
    grade_check = str(checks[0].sqltext).replace(" ", "").upper()
    assert "GRADE_LABELISNULL" in grade_check
    assert "GRADE_LABELIN('A','B','C','D')" in grade_check

    assert {(name, table, tuple(columns)) for name, table, columns, _ in recorder.created_indexes} == {
        ("ix_mana_brand_hierarchy_level1_code", "mana_brand_hierarchy", ("level1_code",)),
        ("ix_mana_brand_hierarchy_level2_code", "mana_brand_hierarchy", ("level2_code",)),
    }


def test_migration_downgrade_drops_indexes_and_table(monkeypatch):
    migration = _load_migration()
    recorder = RecordingOp()
    monkeypatch.setattr(migration, "op", recorder)

    migration.downgrade()

    assert recorder.dropped_indexes == [
        ("ix_mana_brand_hierarchy_level2_code", {"table_name": "mana_brand_hierarchy"}),
        ("ix_mana_brand_hierarchy_level1_code", {"table_name": "mana_brand_hierarchy"}),
    ]
    assert recorder.dropped_tables == [("mana_brand_hierarchy", {})]


def test_source_sql_extracts_three_level_hierarchy_and_grade():
    sql = " ".join(SOURCE_SQL_PATH.read_text(encoding="utf-8").upper().split())

    assert sql.count("BIBH.ODS_MANABRAND") == 3
    assert "LEVEL3.MBPID = LEVEL2.MBID" in sql
    assert "LEVEL2.MBPID = LEVEL1.MBID" in sql
    assert "LEVEL3.MBCLASS = 3" in sql
    assert "LEVEL2.MBCLASS = 2" in sql
    assert "LEVEL1.MBCLASS = 1" in sql
    assert "CASE LEVEL3.MBSTR1 WHEN '1' THEN 'A' WHEN '2' THEN 'B' WHEN '3' THEN 'C' WHEN '4' THEN 'D' END AS GRADE_LABEL" in sql
    assert "STAGE" in sql
    assert "CONFLICTING PARENT/GRADE VALUES" in sql
    assert "REPLACE TARGET ONLY AFTER VALIDATION" in sql
