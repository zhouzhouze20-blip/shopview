import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_app"))

from assign_department_scopes_from_image import _build_user_departments


class AssignDepartmentScopesFromImageTest(unittest.TestCase):
    def test_center_cosmetics_and_luxury_users_share_department_scope(self):
        departments = _build_user_departments()

        expected = ["中心一部(化妆)", "中心一部(名品)"]
        self.assertCountEqual(departments["陈晓楠"], expected)
        self.assertCountEqual(departments["薛涌"], expected)
        self.assertCountEqual(departments["花玲"], expected)
        self.assertCountEqual(departments["黄欣怡"], expected)


if __name__ == "__main__":
    unittest.main()
