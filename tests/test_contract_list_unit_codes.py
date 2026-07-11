import unittest
from types import SimpleNamespace
from unittest.mock import patch

import python_app.routers.contracts as contracts_router


class _FakeMappingsResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows


class _FakeDb:
    def __init__(self):
        self.sql = []
        self.params = []

    def execute(self, statement, _params=None):
        sql = str(statement)
        self.sql.append(sql)
        self.params.append(_params or {})
        return _FakeMappingsResult(
            [
                {
                    "cmcontno": "80197002",
                    "cmstatus": "Y",
                    "cmtype": None,
                    "contract_type_name": None,
                    "cmsupid": "80197",
                    "supplier_name": "南京陈风破浪餐饮管理有限公司常州北大街路分公司",
                    "cmwmid": "1",
                    "cmtitle": None,
                    "cmobject": None,
                    "cmppname": None,
                    "cmcatname": None,
                    "cmeffdate": "2026-12-01",
                    "cmlapdate": "2028-11-30",
                    "cmmoney": None,
                    "cmpaycode": "#",
                    "cmyfkmode": None,
                    "cmsetmode": None,
                    "cmjsmkt": None,
                    "cminputor": None,
                    "cminputdate": None,
                    "cmauditor": None,
                    "cmauditdate": None,
                    "cmchar9": None,
                    "unit_codes": "A118,B6-4A",
                    "group_codes": "6030116007",
                    "group_names": "马记永厅",
                    "department_codes": "6030116",
                    "department_names": "新世纪十部(特业)",
                    "scope_entries": "",
                    "range_brands": None,
                    "range_start_date": None,
                    "range_end_date": None,
                    "contract_area": None,
                    "is_clear": None,
                    "clear_flags": None,
                    "bottom_amount": None,
                    "bottom_profit": None,
                    "scope_group_code": None,
                    "scope_department_code": None,
                    "scope_department_name": None,
                    "scope_store_id": None,
                }
            ]
        )


class ContractListUnitCodesTest(unittest.TestCase):
    def test_contract_list_selects_bound_counter_numbers(self):
        db = _FakeDb()
        scope = SimpleNamespace(all_access=True, allow={}, deny={})

        with patch.object(contracts_router, "_table_exists", return_value=True):
            items = contracts_router._load_contract_list_items(db, scope, limit=100)

        sql = "\n".join(db.sql).lower()
        self.assertIn("business_unit_binding", sql)
        self.assertIn("business_units", sql)
        self.assertIn("unit_codes", sql)
        self.assertEqual(items[0]["unit_codes"], "A118,B6-4A")

    def test_contract_list_filters_by_department_code(self):
        db = _FakeDb()
        scope = SimpleNamespace(all_access=True, allow={}, deny={})

        with patch.object(contracts_router, "_table_exists", return_value=True):
            contracts_router._load_contract_list_items(db, scope, department_code="6030116", limit=100)

        sql = "\n".join(db.sql).lower()
        params = db.params[-1]
        self.assertIn("department_code", sql)
        self.assertIn("department_code", params)
        self.assertEqual(params["department_code"], "6030116")

    def test_contract_list_orders_current_and_shared_contracts_before_expired(self):
        db = _FakeDb()
        scope = SimpleNamespace(all_access=True, allow={}, deny={})

        with patch.object(contracts_router, "_table_exists", return_value=True):
            contracts_router._load_contract_list_items(db, scope, limit=100)

        sql = "\n".join(db.sql).lower()
        self.assertIn("is_current_contract", sql)
        self.assertIn("is_shared_contract", sql)
        self.assertIn("is_expired_contract", sql)
        self.assertLess(sql.index("is_current_contract"), sql.index("is_expired_contract"))

    def test_contract_cycle_item_name_comes_from_codecharge(self):
        join_sql = contracts_router._charge_item_join_sql(True, "ccl.cclitemid").lower()
        select_sql = contracts_router._charge_item_name_select_sql(True).lower()

        self.assertIn("codecharge", join_sql)
        self.assertIn("cccode", join_sql)
        self.assertIn("ccname as cclitemname", select_sql)


if __name__ == "__main__":
    unittest.main()
