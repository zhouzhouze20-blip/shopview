import asyncio
import unittest
from types import SimpleNamespace

from routers.counter_groups import get_counter_groups
from routers import manaframe


class _Result:
    def __init__(self, rows=None, one=None):
        self._rows = rows or []
        self._one = one

    def fetchone(self):
        return self._one

    def mappings(self):
        return self

    def all(self):
        return self._rows


class _FakeDb:
    def __init__(self, existing_tables=None):
        self.executed = []
        self.committed = False
        self.existing_tables = set(existing_tables or {"manaframe", "manaframe_key_brand"})

    def execute(self, sql, params=None):
        sql_text = str(sql)
        self.executed.append((sql_text, params or {}))
        if "information_schema.tables" in sql_text:
            return _Result(one=SimpleNamespace(ok=(params or {}).get("table_name") in self.existing_tables))
        if "CREATE TABLE IF NOT EXISTS manaframe_key_brand" in sql_text:
            self.existing_tables.add("manaframe_key_brand")
            return SimpleNamespace(rowcount=0)
        if "FROM manaframe" in sql_text and "WHERE upper(trim(COALESCE(mfcode" in sql_text:
            return _Result(rows=[{"mfcode": (params or {}).get("group_code")}])
        if "INSERT INTO manaframe_key_brand" in sql_text:
            return SimpleNamespace(rowcount=1)
        return _Result(rows=[])

    def commit(self):
        self.committed = True


class ManaframeKeyBrandTest(unittest.TestCase):
    def test_manaframe_list_selects_key_brand_marker(self):
        db = _FakeDb()

        asyncio.run(
            manaframe.list_manaframe(
                keyword=None,
                store_id=None,
                group_code=None,
                group_name=None,
                status_filter=None,
                db=db,
            )
        )

        list_sql = db.executed[-1][0].lower()
        self.assertIn("is_key_brand", list_sql)
        self.assertIn("left join manaframe_key_brand", list_sql)
        self.assertIn("kb.is_key_brand", list_sql)

    def test_manaframe_list_creates_key_brand_table_when_missing(self):
        db = _FakeDb(existing_tables={"manaframe"})

        asyncio.run(
            manaframe.list_manaframe(
                keyword=None,
                store_id=None,
                group_code=None,
                group_name=None,
                status_filter=None,
                db=db,
            )
        )

        executed_sql = "\n".join(sql for sql, _params in db.executed)
        self.assertIn("CREATE TABLE IF NOT EXISTS manaframe_key_brand", executed_sql)
        self.assertIn("LEFT JOIN manaframe_key_brand", executed_sql)

    def test_counter_groups_selects_key_brand_marker(self):
        db = _FakeDb()

        asyncio.run(get_counter_groups(search="6030102209", store_id=603, db=db))

        list_sql = db.executed[-1][0].lower()
        self.assertIn("is_key_brand", list_sql)
        self.assertIn("left join manaframe_key_brand", list_sql)
        self.assertIn("kb.is_key_brand", list_sql)

    def test_update_manaframe_key_brand_upserts_local_marker_by_group_code(self):
        db = _FakeDb()

        update_manaframe_key_brand = getattr(manaframe, "update_manaframe_key_brand")

        result = asyncio.run(
            update_manaframe_key_brand(
                "6030102209",
                manaframe.ManaframeKeyBrandUpdate(is_key_brand=True),
                db=db,
            )
        )

        update_sql, params = db.executed[-1]
        self.assertIn("INSERT INTO manaframe_key_brand", update_sql)
        self.assertIn("ON CONFLICT", update_sql)
        self.assertNotIn("UPDATE manaframe", update_sql)
        self.assertEqual(params["group_code"], "6030102209")
        self.assertEqual(params["is_key_brand"], True)
        self.assertTrue(db.committed)
        self.assertEqual(result["is_key_brand"], True)


if __name__ == "__main__":
    unittest.main()
