import unittest

from sync_wecom_contacts import DEFAULT_ROLE_SCOPE_RULES, WeComMember, _resolve_role_scope


class WeComSyncRoleScopeTest(unittest.TestCase):
    def member(self, *, position: str) -> WeComMember:
        return WeComMember(
            userid="2680",
            name="黄欣怡",
            mobile="",
            email="",
            status=1,
            department="江苏普灵仕集团/百货条线/中心一部(名品)",
            position=position,
            raw={},
        )

    def test_default_rules_do_not_grant_department_manager_to_regular_member(self):
        role_codes, scope_mode, scope_dimensions = _resolve_role_scope(
            self.member(position=""),
            store_id=1,
            rules=[],
            use_default_rules=True,
        )

        self.assertEqual(role_codes, [])
        self.assertEqual(scope_mode, "CUSTOM")
        self.assertIn("department", scope_dimensions)

    def test_default_rules_do_not_grant_department_manager_to_generic_manager_title(self):
        role_codes, _scope_mode, _scope_dimensions = _resolve_role_scope(
            self.member(position="客户经理"),
            store_id=1,
            rules=[],
            use_default_rules=True,
        )

        self.assertEqual(role_codes, [])

    def test_default_rules_grant_department_manager_to_manager_position(self):
        role_codes, scope_mode, scope_dimensions = _resolve_role_scope(
            self.member(position="部门经理"),
            store_id=1,
            rules=[],
            use_default_rules=True,
        )

        self.assertEqual(role_codes, ["dept_manager"])
        self.assertEqual(scope_mode, "CUSTOM")
        self.assertIn("department", scope_dimensions)


if __name__ == "__main__":
    unittest.main()
