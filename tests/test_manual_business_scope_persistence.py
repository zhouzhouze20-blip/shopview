import asyncio
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from models.database import Base
from models.models import CounterGroup, DataPolicy, DataPolicyItem, Department, Role, Store, User, UserRole
from python_app.routers import system_management
from services.wecom_department_scope import AUTO_SCOPE_EXTERNAL_PREFIX, refresh_auto_department_scope


def test_manual_business_scope_survives_wecom_login_refresh():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Store.__table__,
            User.__table__,
            Role.__table__,
            UserRole.__table__,
            Department.__table__,
            CounterGroup.__table__,
            DataPolicy.__table__,
            DataPolicyItem.__table__,
        ],
    )
    Session = sessionmaker(bind=engine)
    next_policy_id = 2
    next_item_id = 2
    next_user_role_id = 1

    @event.listens_for(Session, "before_flush")
    def assign_sqlite_bigint_ids(session, _flush_context, _instances):
        nonlocal next_policy_id, next_item_id, next_user_role_id
        for obj in session.new:
            if isinstance(obj, DataPolicy) and obj.id is None:
                obj.id = next_policy_id
                next_policy_id += 1
            if isinstance(obj, DataPolicyItem) and obj.id is None:
                obj.id = next_item_id
                next_item_id += 1
            if isinstance(obj, UserRole) and obj.id is None:
                obj.id = next_user_role_id
                next_user_role_id += 1

    db = Session()
    try:
        db.add(Store(store_id=603, store_code="603", store_name="常州新世纪商城", is_active=True))
        db.add(User(
            user_id=627,
            username="1708",
            password_hash="x",
            real_name="赵佳",
            is_active=True,
            status="ACTIVE",
        ))
        db.add(Role(
            id=1,
            role_code=system_management.DEPARTMENT_MANAGER_ROLE_CODE,
            role_name="部门经理",
            role_level=700,
            is_system=True,
            is_active=True,
        ))
        db.add(Department(
            id=1,
            store_id=603,
            dept_code="6030103",
            dept_name="新世纪六部(男装)",
            is_active=True,
        ))
        db.add(Department(
            id=2,
            store_id=603,
            dept_code="6030114",
            dept_name="新世纪五部(运休)",
            is_active=True,
        ))
        db.add(DataPolicy(
            id=1,
            subject_type="USER",
            subject_id=627,
            resource_code="business_scope",
            action_code="view",
            scope_mode="CUSTOM",
            effect="ALLOW",
            priority=55,
            is_active=True,
            source_type="WECOM",
            source_system="wecom",
            external_scope_id=f"{AUTO_SCOPE_EXTERNAL_PREFIX}:627",
            external_scope_name="赵佳 企业微信自动部门范围",
        ))
        db.add(DataPolicyItem(
            id=1,
            policy_id=1,
            dimension_type="department",
            dimension_value="6030103",
            include_children=False,
        ))
        db.commit()

        with patch.object(system_management, "_require_system_permission", lambda *_args: None):
            asyncio.run(system_management.update_contract_permission(
                627,
                {
                    "enabled": True,
                    "scope_mode": "CUSTOM",
                    "store_values": [],
                    "department_values": ["6030103", "6030114"],
                    "group_values": [],
                },
                db=db,
                current_user=SimpleNamespace(user_id=1),
            ))

        policies = db.query(DataPolicy).order_by(DataPolicy.id.asc()).all()
        assert [(policy.source_type, policy.source_system) for policy in policies] == [
            ("WECOM", "wecom"),
            ("MANUAL", "shopview"),
        ]
        assert policies[1].external_scope_id == "manual-business-scope:627"

        refresh_auto_department_scope(
            db,
            user=db.query(User).filter(User.user_id == 627).one(),
            wecom_user_id="1708",
            department_path="江苏普灵仕集团/百货条线/新世纪六部(男装)",
        )
        db.commit()

        manual_policy = db.query(DataPolicy).filter(
            DataPolicy.subject_id == 627,
            DataPolicy.source_type == "MANUAL",
            DataPolicy.source_system == "shopview",
        ).one()
        manual_values = {
            item.dimension_value
            for item in db.query(DataPolicyItem).filter(DataPolicyItem.policy_id == manual_policy.id).all()
        }
        assert manual_values == {"6030103", "6030114"}

        effective_scope = system_management._contract_scope_for_user(db, 627)
        assert set(effective_scope["department_values"]) == {"6030103", "6030114"}
        assert effective_scope["manual_scope_count"] == 1
    finally:
        db.close()
        Base.metadata.drop_all(
            engine,
            tables=[
                DataPolicyItem.__table__,
                DataPolicy.__table__,
                CounterGroup.__table__,
                Department.__table__,
                UserRole.__table__,
                Role.__table__,
                User.__table__,
                Store.__table__,
            ],
        )
        engine.dispose()
