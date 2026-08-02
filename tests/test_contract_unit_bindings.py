import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import call, patch

from fastapi import HTTPException

import python_app.routers.contract_unit_bindings as bindings_router


class _Result:
    def __init__(self, *, row=None, mapping=None, rows=None, rowcount=0):
        self._row = row
        self._mapping = mapping
        self._rows = rows or []
        self.rowcount = rowcount

    def fetchone(self):
        return self._row

    def mappings(self):
        return self

    def first(self):
        return self._mapping

    def all(self):
        return self._rows


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
        self.assertIn("已有其他有效柜位", raised.exception.detail)
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


class _ReplaceFakeDb:
    def __init__(self):
        self.executions = []
        self.added = []
        self.commits = 0
        self.rollbacks = 0

    def execute(self, statement, params=None):
        sql = str(statement)
        params = params or {}
        self.executions.append((sql, params))
        if "SELECT bu.id, bu.unit_code, f.store_code" in sql:
            return _Result(rows=[{"id": 20, "unit_code": "C505", "store_code": "601"}])
        if "SELECT b.id, b.shop_unit_id, b.status, bu.unit_code" in sql:
            return _Result(
                rows=[{"id": 7, "shop_unit_id": 10, "status": "ACTIVE", "unit_code": "C501"}]
            )
        if "SET status = 'INACTIVE'" in sql:
            return _Result(rowcount=1)
        return _Result()

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class ContractLedgerBindingReplaceTest(unittest.IsolatedAsyncioTestCase):
    def test_normalize_shop_unit_ids_deduplicates_one_selected_unit(self):
        self.assertEqual(bindings_router._normalize_shop_unit_ids([20, "20", 20]), [20])

    async def test_replace_uses_dedicated_permission_and_writes_audit_log(self):
        db = _ReplaceFakeDb()
        user = SimpleNamespace(user_id=3)

        with (
            patch.object(bindings_router, "require_permission") as require_permission,
            patch.object(bindings_router, "_require_binding_table"),
            patch.object(bindings_router, "load_business_scope", return_value=SimpleNamespace()),
            patch.object(
                bindings_router,
                "_load_contract_list_items",
                return_value=[
                    {
                        "cmcontno": "80355001",
                        "store_codes": "601",
                        "cmwmid": "5",
                        "cmeffdate": date(2026, 1, 1),
                        "cmlapdate": date(2026, 12, 31),
                        "sjcgdate": date(2026, 6, 30),
                    }
                ],
            ),
        ):
            result = await bindings_router.replace_contract_unit_bindings(
                "80355001",
                {"shop_unit_ids": [20]},
                db,
                user,
            )

        self.assertEqual(
            require_permission.call_args_list,
            [
                call(db, user, "contract.view"),
                call(db, user, "contract.unit_binding.edit"),
            ],
        )
        insert_params = next(
            params for sql, params in db.executions if "INSERT INTO business_unit_binding" in sql
        )
        self.assertEqual(insert_params["shop_unit_id"], 20)
        self.assertEqual(insert_params["business_type"], "租赁")
        self.assertEqual(insert_params["end_date"], date(2026, 6, 30))
        self.assertEqual(result["unit_codes"], ["C505"])
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["disabled"], 1)
        self.assertEqual(db.commits, 1)
        self.assertEqual(db.rollbacks, 0)
        self.assertEqual(len(db.added), 1)
        self.assertEqual(db.added[0].action_code, "unit_binding_edit")
        self.assertEqual(db.added[0].detail["before_unit_codes"], ["C501"])
        self.assertEqual(db.added[0].detail["after_unit_codes"], ["C505"])

    async def test_replace_with_empty_selection_disables_binding_and_keeps_audit_history(self):
        db = _ReplaceFakeDb()
        user = SimpleNamespace(user_id=3)

        with (
            patch.object(bindings_router, "require_permission"),
            patch.object(bindings_router, "_require_binding_table"),
            patch.object(bindings_router, "load_business_scope", return_value=SimpleNamespace()),
            patch.object(
                bindings_router,
                "_load_contract_list_items",
                return_value=[
                    {
                        "cmcontno": "00059012",
                        "store_codes": "603",
                        "cmwmid": "1",
                        "cmeffdate": date(2025, 8, 29),
                        "cmlapdate": date(2026, 8, 28),
                    }
                ],
            ),
        ):
            result = await bindings_router.replace_contract_unit_bindings(
                "00059012",
                {"shop_unit_ids": []},
                db,
                user,
            )

        self.assertEqual(result["unit_codes"], [])
        self.assertEqual(result["disabled"], 1)
        self.assertEqual(result["created"], 0)
        self.assertEqual(result["reactivated"], 0)
        self.assertEqual(db.commits, 1)
        self.assertEqual(db.rollbacks, 0)
        self.assertFalse(any("SELECT bu.id, bu.unit_code, f.store_code" in sql for sql, _ in db.executions))
        self.assertEqual(len(db.added), 1)
        self.assertEqual(db.added[0].detail["before_unit_codes"], ["C501"])
        self.assertEqual(db.added[0].detail["after_unit_codes"], [])

if __name__ == "__main__":
    unittest.main()
