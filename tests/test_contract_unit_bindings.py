import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

import python_app.routers.contract_unit_bindings as bindings_router


class _Result:
    def __init__(self, *, row=None, mapping=None):
        self._row = row
        self._mapping = mapping

    def fetchone(self):
        return self._row

    def mappings(self):
        return self

    def first(self):
        return self._mapping


class _FakeDb:
    def __init__(self, *, duplicate=False):
        self.duplicate = duplicate
        self.executions = []
        self.commits = 0

    def execute(self, statement, params=None):
        sql = str(statement)
        self.executions.append((sql, params or {}))
        if "SELECT id, shop_unit_id, contract_id, status, start_date, end_date" in sql:
            return _Result(
                mapping={
                    "id": 7,
                    "shop_unit_id": 10,
                    "contract_id": "80123001",
                    "status": "ACTIVE",
                    "start_date": date(2026, 1, 1),
                    "end_date": date(2026, 12, 31),
                }
            )
        if "WHERE id <> :id" in sql:
            return _Result(row=SimpleNamespace(id=99) if self.duplicate else None)
        return _Result()

    def commit(self):
        self.commits += 1


class ContractUnitBindingUpdateTest(unittest.IsolatedAsyncioTestCase):
    async def test_update_changes_existing_binding(self):
        db = _FakeDb()
        user = SimpleNamespace(user_id=1)

        with (
            patch.object(bindings_router, "require_permission"),
            patch.object(bindings_router, "_require_binding_table"),
            patch.object(bindings_router, "_require_business_unit", return_value=20),
            patch.object(bindings_router, "_contract_exists", return_value=True),
        ):
            result = await bindings_router.update_contract_unit_binding(
                7,
                {
                    "shop_unit_id": 20,
                    "contract_id": "80124001",
                    "status": "ACTIVE",
                    "start_date": "2026-02-01",
                    "end_date": "2026-12-31",
                },
                db,
                user,
            )

        update_sql, update_params = next(item for item in db.executions if item[0].lstrip().startswith("UPDATE"))
        self.assertIn("shop_unit_id = :shop_unit_id", update_sql)
        self.assertEqual(update_params["shop_unit_id"], 20)
        self.assertEqual(update_params["contract_id"], "80124001")
        self.assertEqual(db.commits, 1)
        self.assertEqual(result, {"message": "绑定更新成功", "id": 7})

    async def test_update_rejects_another_active_duplicate(self):
        db = _FakeDb(duplicate=True)
        user = SimpleNamespace(user_id=1)

        with (
            patch.object(bindings_router, "require_permission"),
            patch.object(bindings_router, "_require_binding_table"),
            patch.object(bindings_router, "_require_business_unit", return_value=20),
            patch.object(bindings_router, "_contract_exists", return_value=True),
        ):
            with self.assertRaises(HTTPException) as raised:
                await bindings_router.update_contract_unit_binding(
                    7,
                    {"shop_unit_id": 20, "contract_id": "80124001", "status": "ACTIVE"},
                    db,
                    user,
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertIn("已有其他有效绑定", raised.exception.detail)
        self.assertFalse(any(sql.lstrip().startswith("UPDATE") for sql, _ in db.executions))
        self.assertEqual(db.commits, 0)

    async def test_partial_date_update_validates_against_existing_end_date(self):
        db = _FakeDb()
        user = SimpleNamespace(user_id=1)

        with (
            patch.object(bindings_router, "require_permission"),
            patch.object(bindings_router, "_require_binding_table"),
        ):
            with self.assertRaises(HTTPException) as raised:
                await bindings_router.update_contract_unit_binding(
                    7,
                    {"start_date": "2027-01-01"},
                    db,
                    user,
                )

        self.assertEqual(raised.exception.status_code, 400)
        self.assertIn("不能晚于", raised.exception.detail)
        self.assertEqual(db.commits, 0)


if __name__ == "__main__":
    unittest.main()
