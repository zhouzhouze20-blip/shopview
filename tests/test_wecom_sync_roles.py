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

    def half_mountain_member(self, *, userid: str, name: str, department: str) -> WeComMember:
        return WeComMember(
            userid=userid,
            name=name,
            mobile="",
            email="",
            status=1,
            department=f"江苏普灵仕集团/百货条线/百货总经理室/半山生活/{department}",
            position="品类部副经理",
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

    def test_default_rules_grant_store_scope_to_director_position(self):
        role_codes, scope_mode, scope_dimensions = _resolve_role_scope(
            self.member(position="营运总监"),
            store_id=1,
            rules=[],
            use_default_rules=True,
        )

        self.assertEqual(role_codes, ["store_director"])
        self.assertEqual(scope_mode, "CUSTOM")
        self.assertEqual(scope_dimensions, {"store": ["1"]})

    def test_default_rules_grant_half_mountain_store_scope_to_selected_category_deputies(self):
        members = [
            self.half_mountain_member(userid="300519", name="吴奕雯", department="半山运营管理部"),
            self.half_mountain_member(userid="500621", name="潘荣燕", department="半山图书采购部"),
        ]

        for member in members:
            with self.subTest(userid=member.userid):
                role_codes, scope_mode, scope_dimensions = _resolve_role_scope(
                    member,
                    store_id=1,
                    rules=[],
                    use_default_rules=True,
                )

                self.assertEqual(role_codes, ["dept_manager"])
                self.assertEqual(scope_mode, "CUSTOM")
                self.assertEqual(scope_dimensions, {"store": ["4"]})

    def test_store_scope_rule_overrides_later_department_scope_rule(self):
        rules = [
            {
                "userids": ["300519", "500621"],
                "role_codes": ["dept_manager"],
                "scope_mode": "CUSTOM",
                "scope_dimensions": {"store": ["4"]},
            },
            {
                "position_keywords": ["副经理"],
                "role_codes": ["dept_manager"],
                "scope_mode": "CUSTOM",
                "scope_dimensions": {"department": ["$department"]},
            },
        ]

        role_codes, scope_mode, scope_dimensions = _resolve_role_scope(
            self.half_mountain_member(userid="300519", name="吴奕雯", department="半山运营管理部"),
            store_id=1,
            rules=rules,
            use_default_rules=False,
        )

        self.assertEqual(role_codes, ["dept_manager"])
        self.assertEqual(scope_mode, "CUSTOM")
        self.assertEqual(scope_dimensions, {"store": ["4"]})


if __name__ == "__main__":
    unittest.main()
