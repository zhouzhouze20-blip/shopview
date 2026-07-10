# Area Category ETL Table Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reversible Alembic migration that creates the four-column `area_category` ETL landing table.

**Architecture:** A single Alembic revision follows current head `a2b3c4d5e6f7` and uses explicit PostgreSQL DDL for the table and comments. A focused source-level test verifies the revision link, exact four-column schema, comments, absence of extra constraints, and downgrade behavior without requiring a live database.

**Tech Stack:** Python 3, Alembic, PostgreSQL DDL, pytest

---

## File structure

- Create `test/test_area_category_migration.py`: focused contract test for the migration source.
- Create `python_app/alembic/versions/b3c4d5e6f7a8_create_area_category_table.py`: reversible DDL migration for `area_category`.

### Task 1: Add the migration contract test

**Files:**
- Create: `test/test_area_category_migration.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python_app/.venv/bin/pytest test/test_area_category_migration.py -q`

Expected: FAIL with `FileNotFoundError` because the migration has not been created.

- [ ] **Step 3: Commit the failing test**

```bash
git add test/test_area_category_migration.py
git commit -m "test: define area category migration contract"
```

### Task 2: Create the Alembic migration

**Files:**
- Create: `python_app/alembic/versions/b3c4d5e6f7a8_create_area_category_table.py`

- [ ] **Step 1: Write the minimal migration**

```python
"""create area category table

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-07-10
"""
from typing import Sequence, Union

from alembic import op


revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_SQL = r"""
CREATE TABLE area_category (
    area_code VARCHAR(100),
    area_name VARCHAR(100),
    category_code VARCHAR(100),
    category_name VARCHAR(100)
);

COMMENT ON TABLE area_category IS '区域与品类关系';
COMMENT ON COLUMN area_category.area_code IS '区域编码';
COMMENT ON COLUMN area_category.area_name IS '区域名称';
COMMENT ON COLUMN area_category.category_code IS '品类编码';
COMMENT ON COLUMN area_category.category_name IS '品类名称';
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.drop_table("area_category")
```

- [ ] **Step 2: Run the focused test**

Run: `python_app/.venv/bin/pytest test/test_area_category_migration.py -q`

Expected: `1 passed`.

- [ ] **Step 3: Verify Python syntax**

Run: `python_app/.venv/bin/python -m py_compile python_app/alembic/versions/b3c4d5e6f7a8_create_area_category_table.py`

Expected: exit code 0 with no output.

- [ ] **Step 4: Verify the Alembic revision graph**

Run: `python_app/.venv/bin/alembic -c python_app/alembic.ini heads`

Expected: `b3c4d5e6f7a8 (head)`.

- [ ] **Step 5: Check the migration diff for whitespace errors**

Run: `git diff --check -- test/test_area_category_migration.py python_app/alembic/versions/b3c4d5e6f7a8_create_area_category_table.py`

Expected: exit code 0 with no output.

- [ ] **Step 6: Commit the migration**

```bash
git add python_app/alembic/versions/b3c4d5e6f7a8_create_area_category_table.py
git commit -m "feat: create area category ETL table"
```
