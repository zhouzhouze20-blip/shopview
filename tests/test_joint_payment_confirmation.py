from datetime import date
import inspect
from types import SimpleNamespace

from python_app.routers import erp_settlements as router
from python_app.services import erp_settlement_charge_display as charge_display
from python_app.services import joint_payment_confirmation as svc


def test_current_financial_month_period_uses_shopview_calendar():
    assert svc.current_financial_month_period(date(2026, 8, 17)) == (
        date(2026, 7, 29),
        date(2026, 8, 28),
    )
    assert svc.current_financial_month_period(date(2026, 1, 15)) == (
        date(2026, 1, 1),
        date(2026, 1, 28),
    )
    assert svc.current_financial_month_period(date(2026, 12, 31)) == (
        date(2026, 11, 29),
        date(2026, 12, 31),
    )


def test_current_financial_month_amount_uses_audit_date_and_ignores_list_date_filter(monkeypatch):
    executed: list[tuple[str, dict]] = []
    results = [
        SimpleNamespace(
            fetchone=lambda: SimpleNamespace(
                generated_count=0,
                generated_amount=0,
                audited_count=0,
                audited_amount=0,
                latest_status_date=None,
            )
        ),
        SimpleNamespace(fetchone=lambda: SimpleNamespace(audited_amount=1234.56)),
        SimpleNamespace(fetchone=lambda: SimpleNamespace(n=0)),
        SimpleNamespace(fetchall=lambda: []),
    ]

    class FakeDb:
        def execute(self, statement, params):
            executed.append((str(statement), dict(params)))
            return results[len(executed) - 1]

    monkeypatch.setattr(svc, "_table_exists", lambda *_args: True)
    monkeypatch.setattr(
        svc,
        "current_financial_month_period",
        lambda: (date(2026, 7, 29), date(2026, 8, 28)),
    )

    result = svc.query_joint_payments(
        FakeDb(),
        svc.JointPaymentFilters(date_from="2025-01-01", date_to="2025-01-31"),
        svc.BusinessScope(all_access=True),
    )

    amount_sql, amount_params = executed[1]
    assert "TRIM(h.sphflag::text) = 'Y'" in amount_sql
    assert "h.auditdate >= :joint_payment_financial_month_start" in amount_sql
    assert "h.auditdate < :joint_payment_financial_month_end + INTERVAL '1 day'" in amount_sql
    assert "joint_payment_date_from" not in amount_sql
    assert "joint_payment_date_to" not in amount_sql
    assert amount_params["joint_payment_financial_month_start"] == date(2026, 7, 29)
    assert amount_params["joint_payment_financial_month_end"] == date(2026, 8, 28)
    assert result["summary"]["current_financial_month_audited_amount"] == 1234.56
    assert result["summary"]["current_financial_month_start"] == "2026-07-29"
    assert result["summary"]["current_financial_month_end"] == "2026-08-28"


def test_query_uses_payment_bridge_for_joint_status_and_safe_amount_scope():
    cte, common_where, params = svc.build_joint_payment_query_parts(
        svc.JointPaymentFilters(
            date_from="2026-08-01",
            date_to="2026-08-17",
            market="602",
            department_code="6020101",
            group_prefix="6020101",
            keyword="PAY-001",
        ),
        svc.BusinessScope(
            group_allow=frozenset({"6020101001"}),
            group_deny=frozenset({"6020101999"}),
            department_allow=frozenset({"6020101"}),
            department_deny=frozenset({"6020199"}),
        ),
    )

    assert "TRIM(COALESCE(pb.pbwmid::text, '')) = '4'" in cte
    assert "SUM(COALESCE(pb.pbsf, 0)) AS payment_amount" in cte
    assert "suppayhead.sphwmid" not in cte
    assert "joint_payment_allow_group_0" in cte
    assert "joint_payment_deny_group_0" in cte
    assert "joint_payment_allow_department_code_0" in cte
    assert "joint_payment_allow_department_name_0" in cte
    assert "joint_payment_deny_department_code_0" in cte
    assert "joint_payment_department_code" in cte
    assert "joint_payment_group_prefix" in cte
    assert "group_mf.mfpcode" in cte
    assert "THEN h.auditdate ELSE h.inputdate END" in common_where
    assert "pb_kw.pbjsno" in common_where
    assert params["joint_payment_allow_group_0"] == "6020101001"
    assert params["joint_payment_deny_group_0"] == "6020101999"
    assert params["joint_payment_allow_department_code_0"] == "6020101"
    assert params["joint_payment_allow_department_name_0"] == "6020101"
    assert params["joint_payment_department_code"] == "6020101"
    assert params["joint_payment_group_prefix"] == "6020101%"
    assert params["joint_payment_date_from"] == "2026-08-01"
    assert params["joint_payment_date_to"] == "2026-08-17"


def test_supplier_search_keeps_code_exact_and_name_fuzzy():
    _, common_where, params = svc.build_joint_payment_query_parts(
        svc.JointPaymentFilters(
            supplier_code="00050",
            supplier_name="玉德隆",
        ),
        svc.BusinessScope(all_access=True),
    )

    assert "TRIM(UPPER(COALESCE(h.sphsupid::text, ''))) = :joint_payment_supplier_code" in common_where
    assert "COALESCE(sb.sbcname::text, '') ILIKE :joint_payment_supplier_name" in common_where
    assert params["joint_payment_supplier_code"] == "00050"
    assert params["joint_payment_supplier_name"] == "%玉德隆%"
    assert params.get("joint_payment_keyword") is None


def test_scope_without_allowed_groups_produces_empty_visible_batch():
    cte, _, _ = svc.build_joint_payment_query_parts(
        svc.JointPaymentFilters(),
        svc.BusinessScope(all_access=False),
    )
    assert "AND FALSE" in cte


def test_charge_scope_matches_allowed_and_denied_groups():
    where_sql, params = svc._visible_charge_where(
        svc.BusinessScope(
            group_allow=frozenset({"6020101001"}),
            group_deny=frozenset({"6020101999"}),
        )
    )

    assert "aa.sscmfid" in where_sql
    assert "joint_payment_charge_allow_group_0" in where_sql
    assert "joint_payment_charge_deny_group_0" in where_sql
    assert params["joint_payment_charge_allow_group_0"] == "6020101001"
    assert params["joint_payment_charge_deny_group_0"] == "6020101999"


def test_payment_detail_returns_income_invoice_and_scoped_expense_breakdown():
    source = inspect.getsource(svc.get_joint_payment_detail)

    assert 'pb.pbxssr AS sales_revenue' in source
    assert 'pb.pbkp AS invoiced_amount' in source
    assert 'query_supsetcharge_enriched' in source
    assert '_visible_charge_where(scope)' in source
    assert 'charge_pb.pbjsno' in source
    assert 'charge_pb.pbmfid' in source
    assert 'charge_pb.pbcontno' in source
    assert '"sales_revenue"' in source
    assert '"invoiced_amount"' in source
    assert '"fee_amount"' in source
    assert '"ticket_reduction_amount"' in source
    assert '"expense_amount"' in source
    assert '"ticket_reduction_detail_matches"' in source
    assert '"expense_detail_matches"' in source
    assert '"charges": charges' in source


def test_charge_display_uses_codecharge_name_dictionary(monkeypatch):
    monkeypatch.setattr(charge_display, "_table_exists", lambda *_args: True)

    extra_select, joins = charge_display._supsetcharge_enriched_sql(object())

    assert "LEFT JOIN codecharge cc" in joins
    assert "cc.cccode" in joins
    assert "cc.ccname" in extra_select
    assert "gr_kmcode" not in joins


def test_admin_scope_still_restricts_business_type_to_joint_operation():
    cte, common_where, params = svc.build_joint_payment_query_parts(
        svc.JointPaymentFilters(status="M"),
        svc.BusinessScope(all_access=True),
    )
    assert "pb.pbwmid::text" in cte
    assert "= '4'" in cte
    assert "sphflag::text" in common_where
    assert not any(key.startswith("joint_payment_allow_group") for key in params)


def test_department_only_scope_is_allowed_and_matches_code_or_name():
    cte, _, params = svc.build_joint_payment_query_parts(
        svc.JointPaymentFilters(),
        svc.BusinessScope(department_allow=frozenset({"中心一部(名品)"})),
    )
    assert "FALSE" not in cte
    assert "joint_payment_allow_department_code_0" in cte
    assert "joint_payment_allow_department_name_0" in cte
    assert params["joint_payment_allow_department_code_0"] == "中心一部(名品)"
    assert params["joint_payment_allow_department_name_0"] == "中心一部(名品)"


def test_mobile_supplier_payment_scope_reuses_query_business_scope(monkeypatch):
    user = SimpleNamespace(user_id=99)
    expected = svc.BusinessScope(
        group_allow=frozenset({"6010101001"}),
        group_deny=frozenset({"6010101999"}),
        department_allow=frozenset({"6020101"}),
        department_deny=frozenset({"6020199"}),
    )
    monkeypatch.setattr(router, "_joint_payment_scope", lambda *_args: expected)

    assert router._mobile_supplier_payment_scope(object(), user) == expected


def test_joint_payment_scope_maps_query_business_allow_and_deny_rules(monkeypatch):
    user = SimpleNamespace(user_id=101)
    monkeypatch.setattr(router, "is_admin", lambda *_args: False)
    monkeypatch.setattr(
        router,
        "load_business_scope",
        lambda *_args, **_kwargs: SimpleNamespace(
            all_access=False,
            allow={"group": {"6010101001"}, "department": {"6020101"}},
            deny={"group": {"6010101999"}, "department": {"6020199"}},
        ),
    )

    scope = router._joint_payment_scope(object(), user)

    assert scope.group_allow == frozenset({"6010101001"})
    assert scope.group_deny == frozenset({"6010101999"})
    assert scope.department_allow == frozenset({"6020101"})
    assert scope.department_deny == frozenset({"6020199"})


def test_mobile_supplier_payment_endpoints_require_dedicated_mobile_permission():
    list_source = inspect.getsource(router.list_mobile_supplier_payments)
    detail_source = inspect.getsource(router.get_mobile_supplier_payment_detail)

    assert 'require_permission(db, current_user, "mobile.supplier_payments.view")' in list_source
    assert 'require_permission(db, current_user, "mobile.supplier_payments.view")' in detail_source
    assert "_mobile_supplier_payment_scope" in list_source
    assert "_mobile_supplier_payment_scope" in detail_source
    assert "supplier_code=supplier_code" in list_source
    assert "supplier_name=supplier_name" in list_source
