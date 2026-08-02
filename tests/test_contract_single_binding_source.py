import inspect
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

import python_app.routers.contract_unit_bindings as bindings_router
import python_app.routers.contracts as contracts_router


class _Result:
    def __init__(self, *, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def mappings(self):
        return self

    def all(self):
        return self._rows


class _UnitContractsDb:
    def __init__(self):
        self.sql = []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.sql.append(sql)
        if "FROM business_units bu" in sql and "WHERE bu.id = :unit_id" in sql:
            return _Result(
                row=SimpleNamespace(
                    id=3036,
                    floor_id=88,
                    unit_code="B1-22A",
                    status="ACTIVE",
                    contract_mode="EXCLUSIVE",
                    manual_area=None,
                    store_code="603",
                    store_id="603",
                    building_code="603-01",
                    floor_code="1F",
                    floor_name="一楼",
                )
            )
        return _Result(rows=[])


class ContractSingleBindingSourceTest(unittest.IsolatedAsyncioTestCase):
    async def test_unit_contracts_match_active_contract_unit_binding_only(self):
        db = _UnitContractsDb()
        user = SimpleNamespace(user_id=1)

        with (
            patch.object(contracts_router, "require_permission"),
            patch.object(contracts_router, "load_business_scope", return_value=SimpleNamespace(all_access=True)),
            patch.object(contracts_router, "_require_contract_tables"),
            patch.object(contracts_router, "_table_exists", return_value=True),
            patch.object(contracts_router, "_get_table_columns", return_value={"contract_mode"}),
        ):
            await contracts_router.get_contracts_by_unit(3036, db, user)

        matching_sql = db.sql[-1]
        self.assertIn("FROM business_unit_binding b", matching_sql)
        self.assertIn("= 'ACTIVE'", matching_sql)
        self.assertNotIn("IN ('ACTIVE', 'HISTORY')", matching_sql)
        self.assertNotIn("WHERE upper(trim(COALESCE(cm.cmchar9, ''))) = upper(trim(:unit_code))", matching_sql)
        self.assertNotIn("WHERE upper(trim(COALESCE(cmf.cmfmfid, ''))) = upper(trim(:unit_code))", matching_sql)

    def test_contract_list_aggregates_active_bindings_only(self):
        source = inspect.getsource(contracts_router._load_contract_list_items)
        self.assertIn("COALESCE(b.status, 'ACTIVE'))) = 'ACTIVE'", source)
        self.assertNotIn("COALESCE(b.status, 'ACTIVE'))) IN ('ACTIVE', 'HISTORY')", source)

    def test_one_contract_accepts_at_most_one_current_unit(self):
        with self.assertRaises(HTTPException) as raised:
            bindings_router._normalize_shop_unit_ids([20, 10])

        self.assertEqual(raised.exception.status_code, 400)
        self.assertIn("一个柜位", raised.exception.detail)


if __name__ == "__main__":
    unittest.main()
