from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "python_app"
    / "alembic"
    / "versions"
    / "b3c4d5e6f7a8_create_area_category_table.py"
)


def test_area_category_migration_contract():
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert 'revision: str = "b3c4d5e6f7a8"' in sql
    assert 'down_revision: union[str, sequence[str], none] = "a2b3c4d5e6f7"' in sql
    assert "create table area_category" in sql
    assert "area_code varchar(100)" in sql
    assert "area_name varchar(100)" in sql
    assert "category_code varchar(100)" in sql
    assert "category_name varchar(100)" in sql
    assert "comment on table area_category" in sql
    assert "comment on column area_category.area_code" in sql
    assert "comment on column area_category.area_name" in sql
    assert "comment on column area_category.category_code" in sql
    assert "comment on column area_category.category_name" in sql
    assert "primary key" not in sql
    assert "unique" not in sql
    assert 'op.drop_table("area_category")' in sql
