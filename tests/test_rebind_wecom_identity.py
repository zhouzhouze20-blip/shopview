from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from python_app.models.database import Base
from python_app.models.models import User, UserIdentity
from python_app.rebind_wecom_identity import RebindError, rebind_wecom_identity


def _session():
    engine = create_engine("sqlite:///:memory:")
    User.__table__.create(engine)
    UserIdentity.__table__.create(engine)
    return sessionmaker(bind=engine)()


def _add_user_with_identity(db, *, user_id: int, username: str, wecom_user_id: str, corp_id: str = "corp"):
    db.add(User(
        user_id=user_id,
        username=username,
        password_hash="hash",
        employee_no=username,
        real_name="测试用户",
        is_active=True,
    ))
    db.add(UserIdentity(
        id=user_id,
        user_id=user_id,
        identity_type="wecom",
        identifier=f"{corp_id}:{wecom_user_id}",
        corp_id=corp_id,
        wecom_user_id=wecom_user_id,
        is_primary=False,
    ))
    db.commit()


def test_dry_run_does_not_change_identity():
    db = _session()
    _add_user_with_identity(db, user_id=1, username="300653", wecom_user_id="300653")

    result = rebind_wecom_identity(
        db,
        username="300653",
        corp_id="corp",
        old_wecom_user_id="300653",
        new_wecom_user_id="6136",
        apply=False,
    )

    identity = db.query(UserIdentity).one()
    assert result.changed is False
    assert identity.wecom_user_id == "300653"
    assert identity.identifier == "corp:300653"


def test_apply_changes_only_wecom_identity():
    db = _session()
    _add_user_with_identity(db, user_id=1, username="300653", wecom_user_id="300653")

    result = rebind_wecom_identity(
        db,
        username="300653",
        corp_id="corp",
        old_wecom_user_id="300653",
        new_wecom_user_id="6136",
        apply=True,
    )

    user = db.query(User).one()
    identity = db.query(UserIdentity).one()
    assert result.changed is True
    assert user.username == "300653"
    assert user.employee_no == "300653"
    assert identity.user_id == user.user_id
    assert identity.wecom_user_id == "6136"
    assert identity.identifier == "corp:6136"


def test_refuses_target_userid_bound_to_another_user():
    db = _session()
    _add_user_with_identity(db, user_id=1, username="300653", wecom_user_id="300653")
    _add_user_with_identity(db, user_id=2, username="other", wecom_user_id="6136")

    try:
        rebind_wecom_identity(
            db,
            username="300653",
            corp_id="corp",
            old_wecom_user_id="300653",
            new_wecom_user_id="6136",
            apply=True,
        )
    except RebindError as exc:
        assert "已绑定其他" in str(exc)
    else:
        raise AssertionError("expected RebindError")

    identities = {row.user_id: row.wecom_user_id for row in db.query(UserIdentity).all()}
    assert identities == {1: "300653", 2: "6136"}
