from pathlib import Path


MIGRATION = Path(__file__).resolve().parents[1] / "python_app" / "alembic" / "versions" / "a2b3c4d5e6f7_add_mall_planning_role.py"


def test_mall_planning_role_migration_has_required_permissions_and_scope():
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "mall_planning" in sql
    assert "购物中心企划" in sql
    assert "俞陈" in sql
    assert "白海燕" in sql
    assert "activity_analysis.points.view" in sql
    assert "activity_analysis.star_diamond.view" in sql
    assert "俞陈 购物中心全部权限" in sql
    assert "白海燕 四门店全部权限" in sql
    assert "('俞陈', 'mall_planning:yuchen:store:1', '俞陈 购物中心全部权限', '1')" in sql
    assert "('白海燕', 'mall_planning:baihaiyan:stores:1-4', '白海燕 四门店全部权限', '1')" in sql
    assert "('白海燕', 'mall_planning:baihaiyan:stores:1-4', '白海燕 四门店全部权限', '2')" in sql
    assert "('白海燕', 'mall_planning:baihaiyan:stores:1-4', '白海燕 四门店全部权限', '3')" in sql
    assert "('白海燕', 'mall_planning:baihaiyan:stores:1-4', '白海燕 四门店全部权限', '4')" in sql
