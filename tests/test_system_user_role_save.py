import asyncio
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import CheckConstraint, Integer, MetaData, create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_app"))
from models.models import Role, User, UserRole
from routers import system_management as router
from schemas.schemas import SystemUserCreate, SystemUserUpdate


class SystemUserRoleSaveTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        metadata = MetaData()
        for model in (User, Role, UserRole):
            table = model.__table__.to_metadata(metadata)
            for column in table.primary_key:
                column.type = Integer()
            # Only these three tables are needed for the role-save behavior.
            for constraint in list(table.foreign_key_constraints):
                table.constraints.remove(constraint)
            table.foreign_keys.clear()
        metadata.tables["users"].append_constraint(CheckConstraint("length(role) <= 20"))
        metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.db.add_all([
            Role(id=27, role_code="category_coupon_followup_manager", role_name="跟进主管"),
            Role(id=28, role_code="category_supplier_payment_viewer", role_name="付款主管"),
            Role(id=30, role_code="ppy", role_name="配票员"),
            User(user_id=1086, username="5385", password_hash="unused", role="user"),
        ])
        self.db.commit()
        for name in ("_require_system_permission", "_upsert_password_identity", "_sync_user_department_posts"):
            patcher = patch.object(router, name)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(router, "_serialize_users", side_effect=lambda db, users: [{"user_id": u.user_id} for u in users])
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_update_long_first_role_preserves_scope_and_expiry(self):
        expiry = datetime(2030, 1, 1)
        self.db.add(UserRole(user_id=1086, role_id=28, store_id=1, expires_at=expiry))
        self.db.commit()
        asyncio.run(router.update_system_user(1086, SystemUserUpdate(role_ids=[28, 30, 30]), self.db, None))
        self.assertEqual(self.db.get(User, 1086).role, "user")
        assignments = self.db.query(UserRole).filter_by(user_id=1086).all()
        self.assertEqual(len(assignments), 2)
        retained = next(a for a in assignments if a.role_id == 28)
        self.assertEqual((retained.store_id, retained.expires_at), (1, expiry))

    def test_create_accepts_long_first_role(self):
        result = asyncio.run(router.create_system_user(SystemUserCreate(
            username="new-user", password="test-only", role_ids=[28, 30]
        ), self.db, None))
        self.assertEqual(self.db.get(User, result["user_id"]).role, "user")
        self.assertEqual(self.db.query(UserRole).filter_by(user_id=result["user_id"]).count(), 2)

    def test_role_removal_and_empty_selection(self):
        self.db.add_all([UserRole(user_id=1086, role_id=27), UserRole(user_id=1086, role_id=28)])
        self.db.commit()
        asyncio.run(router.update_system_user(1086, SystemUserUpdate(role_ids=[28]), self.db, None))
        self.assertEqual([r.role_id for r in self.db.query(UserRole).all()], [28])
        asyncio.run(router.update_system_user(1086, SystemUserUpdate(role_ids=[]), self.db, None))
        self.assertEqual(self.db.query(UserRole).count(), 0)

    def test_omitted_roles_preserve_assignments(self):
        self.db.add(UserRole(user_id=1086, role_id=28, store_id=1))
        self.db.commit()
        asyncio.run(router.update_system_user(1086, SystemUserUpdate(real_name="测试"), self.db, None))
        self.assertEqual(self.db.query(UserRole).one().store_id, 1)


if __name__ == "__main__":
    unittest.main()
