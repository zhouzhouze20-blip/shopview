import unittest
from types import SimpleNamespace

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from models.database import Base
from models.models import CounterGroup, DataPolicy, DataPolicyItem, Department, Role, Store, User, UserRole
from routers.authz import load_business_scope
from services.wecom_department_scope import (
    AUTO_SCOPE_EXTERNAL_PREFIX,
    department_leaf_names,
    normalize_department_name,
    refresh_auto_department_scope,
    refresh_auto_department_scope_from_known_assignment,
    resolve_business_department,
)


class WeComDepartmentScopeTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(
            self.engine,
            tables=[
                Store.__table__,
                CounterGroup.__table__,
                Department.__table__,
                DataPolicy.__table__,
                DataPolicyItem.__table__,
                User.__table__,
                Role.__table__,
                UserRole.__table__,
            ],
        )
        self.Session = sessionmaker(bind=self.engine)
        self.next_policy_id = 3
        self.next_item_id = 3

        @event.listens_for(self.Session, "before_flush")
        def assign_sqlite_bigint_ids(session, _flush_context, _instances):
            for obj in session.new:
                if isinstance(obj, DataPolicy) and obj.id is None:
                    obj.id = self.next_policy_id
                    self.next_policy_id += 1
                if isinstance(obj, DataPolicyItem) and obj.id is None:
                    obj.id = self.next_item_id
                    self.next_item_id += 1

        self.db = self.Session()
        self.db.add(Store(store_id=1, store_code="601", store_name="测试门店", is_active=True))
        self.db.flush()
        self.next_department_id = 1

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(
            self.engine,
            tables=[
                Store.__table__,
                CounterGroup.__table__,
                Department.__table__,
                DataPolicy.__table__,
                DataPolicyItem.__table__,
                User.__table__,
                Role.__table__,
                UserRole.__table__,
            ],
        )
        self.engine.dispose()

    def add_department(self, dept_code, dept_name):
        department = Department(
            id=self.next_department_id,
            store_id=1,
            dept_code=dept_code,
            dept_name=dept_name,
            is_active=True,
        )
        self.next_department_id += 1
        self.db.add(department)
        self.db.flush()
        return department

    def add_counter_group_department(self, dept_code, dept_name, is_active=True):
        group = CounterGroup(
            group_id=self.next_department_id + 1000,
            group_code=f"{dept_code}001",
            group_name=f"{dept_name}测试柜组",
            store_id=1,
            department_code=dept_code,
            department_name=dept_name,
            is_active=is_active,
        )
        self.next_department_id += 1
        self.db.add(group)
        self.db.flush()
        return group

    def test_normalize_department_name_handles_full_width_parentheses(self):
        self.assertEqual(normalize_department_name(" 中心四部（男装） "), "中心四部(男装)")

    def test_department_leaf_names_returns_unique_leaf_names(self):
        self.assertEqual(
            department_leaf_names("江苏普灵仕集团/百货条线/中心四部（男装）"),
            ["中心四部(男装)"],
        )

    def test_resolve_business_department_uses_alias(self):
        self.add_department("6010118", "中心五部(运休)")

        department = resolve_business_department(self.db, "江苏普灵仕集团/百货条线/中心五部(运动)")

        self.assertEqual(department.dept_code, "6010118")
        self.assertEqual(department.dept_name, "中心五部(运休)")

    def test_resolve_business_department_uses_exact_normalized_name(self):
        self.add_department("6010102", "中心四部(男装)")

        department = resolve_business_department(self.db, "江苏普灵仕集团/百货条线/中心四部（男装）")

        self.assertEqual(department.dept_code, "6010102")

    def test_resolve_business_department_falls_back_to_counter_groups(self):
        self.add_department("6010102", "中心四部(男装)").is_active = False
        self.add_counter_group_department("6010102", "中心四部(男装)", is_active=False)

        department = resolve_business_department(self.db, "江苏普灵仕集团/百货条线/中心四部（男装）")

        self.assertEqual(department.dept_code, "6010102")
        self.assertEqual(department.dept_name, "中心四部(男装)")

    def test_refresh_auto_department_scope_replaces_only_auto_policy(self):
        user = SimpleNamespace(user_id=963, real_name="蒋佳卫")
        auto_policy = DataPolicy(
            id=1,
            subject_type="USER",
            subject_id=963,
            resource_code="business_scope",
            action_code="view",
            scope_mode="CUSTOM",
            effect="ALLOW",
            source_type="WECOM",
            source_system="wecom",
            external_scope_id=f"{AUTO_SCOPE_EXTERNAL_PREFIX}:963",
            external_scope_name="旧自动范围",
            is_active=True,
        )
        manual_policy = DataPolicy(
            id=2,
            subject_type="USER",
            subject_id=963,
            resource_code="business_scope",
            action_code="view",
            scope_mode="CUSTOM",
            effect="ALLOW",
            source_type="MANUAL",
            source_system="shopview",
            external_scope_id="manual-extra:963",
            external_scope_name="手工追加范围",
            is_active=True,
        )
        self.add_department("6010102", "中心四部(男装)")
        self.db.add(auto_policy)
        self.db.add(manual_policy)
        self.db.add(DataPolicyItem(id=1, policy_id=1, dimension_type="department", dimension_value="old"))
        self.db.add(DataPolicyItem(id=2, policy_id=2, dimension_type="department", dimension_value="6010117"))
        self.db.flush()

        result = refresh_auto_department_scope(
            self.db,
            user=user,
            wecom_user_id="4476",
            department_path="江苏普灵仕集团/百货条线/中心四部(男装)",
        )

        self.assertTrue(result.updated)
        self.assertEqual(result.department_code, "6010102")
        policies = self.db.query(DataPolicy).order_by(DataPolicy.id.asc()).all()
        self.assertEqual([policy.external_scope_id for policy in policies], ["manual-extra:963", f"{AUTO_SCOPE_EXTERNAL_PREFIX}:963"])
        items = self.db.query(DataPolicyItem).order_by(DataPolicyItem.id.asc()).all()
        self.assertEqual(
            [(item.policy_id, item.dimension_type, item.dimension_value) for item in items],
            [(2, "department", "6010117"), (3, "department", "6010102")],
        )

    def test_refresh_auto_department_scope_uses_known_assignment_fallback(self):
        user = SimpleNamespace(user_id=734, username="2269", real_name="于云")
        self.add_counter_group_department("6010113", "中心二部(女装)", is_active=False)

        result = refresh_auto_department_scope_from_known_assignment(
            self.db,
            user=user,
            wecom_user_id="2269",
        )

        self.assertTrue(result.updated)
        self.assertEqual(result.department_code, "6010113")
        item = self.db.query(DataPolicyItem).one()
        self.assertEqual(item.dimension_type, "department")
        self.assertEqual(item.dimension_value, "6010113")

    def test_refresh_auto_department_scope_skips_ambiguous_known_assignment(self):
        user = SimpleNamespace(user_id=788, username="2746", real_name="谈菲")
        self.add_counter_group_department("6010118", "中心五部(运休)", is_active=False)
        self.add_counter_group_department("6010103", "中心六部(儿童)", is_active=False)

        result = refresh_auto_department_scope_from_known_assignment(
            self.db,
            user=user,
            wecom_user_id="2746",
        )

        self.assertFalse(result.updated)
        self.assertEqual(result.reason, "known_department_ambiguous")
        self.assertEqual(self.db.query(DataPolicy).count(), 0)

    def test_load_business_scope_includes_manual_user_policy(self):
        user = User(
            user_id=963,
            username="4476",
            password_hash="x",
            real_name="蒋佳卫",
            is_active=True,
            status="ACTIVE",
        )
        self.db.add(user)
        self.db.add(DataPolicy(
            id=10,
            subject_type="USER",
            subject_id=963,
            resource_code="business_scope",
            action_code="view",
            scope_mode="CUSTOM",
            effect="ALLOW",
            source_type="WECOM",
            source_system="wecom",
            external_scope_id=f"{AUTO_SCOPE_EXTERNAL_PREFIX}:963",
            external_scope_name="自动范围",
            is_active=True,
        ))
        self.db.add(DataPolicyItem(id=10, policy_id=10, dimension_type="department", dimension_value="6010102"))
        self.db.add(DataPolicy(
            id=11,
            subject_type="USER",
            subject_id=963,
            resource_code="business_scope",
            action_code="view",
            scope_mode="CUSTOM",
            effect="ALLOW",
            source_type="MANUAL",
            source_system="shopview",
            external_scope_id="manual-extra:963",
            external_scope_name="手工追加范围",
            is_active=True,
        ))
        self.db.add(DataPolicyItem(id=11, policy_id=11, dimension_type="department", dimension_value="6010117"))
        self.db.flush()

        scope = load_business_scope(self.db, user)

        self.assertEqual(scope.allow["department"], {"6010102", "6010117"})


if __name__ == "__main__":
    unittest.main()
