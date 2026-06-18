import sys
from pathlib import Path
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_app"))

from routers.authz import DEFAULT_VIEW_ONLY_ROLE_CODES, is_view_permission_code


class DefaultRoleViewPermissionTest(unittest.TestCase):
    def test_default_business_roles_are_marked_as_view_only(self):
        self.assertEqual(
            DEFAULT_VIEW_ONLY_ROLE_CODES,
            {
                "store_admin",
                "dept_manager",
                "group_manager",
                "finance",
                "viewer",
                "contract_viewer",
            },
        )

    def test_only_dot_view_permissions_are_considered_view_permissions(self):
        self.assertTrue(is_view_permission_code("revenue.view"))
        self.assertTrue(is_view_permission_code("system.audit_log.view"))
        self.assertTrue(is_view_permission_code("decoration.todo.view"))
        self.assertFalse(is_view_permission_code("revenue.export"))
        self.assertFalse(is_view_permission_code("revenue.recalculate"))
        self.assertFalse(is_view_permission_code("merchant_planning.manage"))
        self.assertFalse(is_view_permission_code("contract.edit"))


if __name__ == "__main__":
    unittest.main()
