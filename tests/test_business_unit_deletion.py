import inspect
import unittest
from pathlib import Path

import python_app.routers.business_units as business_units_router


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = (
    ROOT
    / "python_app"
    / "alembic"
    / "versions"
    / "j9e0f1a2b3c4_set_month_close_unit_fk_on_delete.py"
)


class _Result:
    def __init__(self, rowcount=0):
        self.rowcount = rowcount


class _Db:
    def __init__(self):
        self.calls = []

    def execute(self, statement, params=None):
        self.calls.append((str(statement), params or {}))
        return _Result(rowcount=21)


class BusinessUnitDeletionTest(unittest.TestCase):
    def test_month_close_detach_keeps_snapshot_code_and_clears_only_unit_id(self):
        db = _Db()

        detached = business_units_router._detach_month_close_adjustments(
            db,
            unit_id=3019,
            unit_code="A1-1B",
        )

        self.assertEqual(detached, 21)
        sql, params = db.calls[0]
        self.assertIn("UPDATE revenue_month_close_adjustments", sql)
        self.assertIn("unit_id = NULL", sql)
        self.assertIn("unit_code = COALESCE", sql)
        self.assertNotIn("adjustment_amount", sql)
        self.assertEqual(params, {"id": 3019, "unit_code": "A1-1B"})

    def test_delete_endpoint_reports_detached_month_close_rows(self):
        source = inspect.getsource(business_units_router.delete_business_unit)

        self.assertIn("_detach_month_close_adjustments", source)
        self.assertIn('"detached_month_close_adjustments"', source)

    def test_database_fk_uses_set_null_for_future_deletes(self):
        source = MIGRATION_PATH.read_text(encoding="utf-8")

        self.assertIn("revenue_month_close_adjustments_unit_id_fkey", source)
        self.assertIn("ON DELETE SET NULL", source)


if __name__ == "__main__":
    unittest.main()
