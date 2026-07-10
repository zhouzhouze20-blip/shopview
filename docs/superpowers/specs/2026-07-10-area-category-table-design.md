# Area Category ETL Table Design

## Goal

Create a PostgreSQL table named `area_category` through Alembic. The table is an ETL landing table for the area-to-category relationship extracted from `BIBH.ODS_MANABRAND`.

## Table structure

The table contains exactly four nullable columns:

| Column | Type | Description |
| --- | --- | --- |
| `area_code` | `VARCHAR(100)` | 区域编码 |
| `area_name` | `VARCHAR(100)` | 区域名称 |
| `category_code` | `VARCHAR(100)` | 品类编码 |
| `category_name` | `VARCHAR(100)` | 品类名称 |

No primary key, unique constraint, index, audit column, or SQLAlchemy model is required. This avoids rejecting duplicate or temporarily incomplete source rows during ETL loading.

## Migration behavior

- The migration follows the current Alembic head `a2b3c4d5e6f7`.
- `upgrade()` creates `area_category` and adds Chinese comments for the table and its columns.
- `downgrade()` drops `area_category`.
- The migration must remain reversible and must not modify unrelated tables or application code.

## ETL source query

The executable form of the provided source query is:

```sql
SELECT
    s1.MBID AS area_code,
    s1.MBCNAME AS area_name,
    s2.MBID AS category_code,
    s2.MBCNAME AS category_name
FROM (
    SELECT MBID, MBCNAME
    FROM BIBH."ODS_MANABRAND"
    WHERE BIBH."ODS_MANABRAND"."MBCLASS" = 1
) AS s1
INNER JOIN (
    SELECT MBID, MBCNAME, MBPID
    FROM BIBH."ODS_MANABRAND"
    WHERE BIBH."ODS_MANABRAND"."MBCLASS" = 2
) AS s2
    ON s1.MBID = s2.MBPID;
```

## Verification

- Verify that Alembic reports a single head with the new revision.
- Run a migration-structure test that checks the table name, four column names and types, predecessor revision, and downgrade operation.
- Run a Python syntax check on the migration file.
