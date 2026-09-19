import inspect
import sys
from datetime import date
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_app"))

from routers import revenue
from routers.authz import DataScope


def test_revenue_sales_financial_period_uses_sglhsrq_everywhere():
    live_sales_sql = " ".join(
        revenue._live_sales_ctes(
            "s.sglhsrq BETWEEN :start_date AND :end_date",
            "AND TRIM(s.sglmarket) = :store_code",
        ).split()
    )
    monthly_source = inspect.getsource(revenue.monthly_revenue)
    detail_source = inspect.getsource(revenue.unit_revenue_detail)
    recalculate_source = inspect.getsource(revenue.recalculate_revenue)

    assert "s.sglhsrq::date AS revenue_date" in live_sales_sql
    assert "GROUP BY s.sglhsrq" in live_sales_sql
    assert 'sales_date_filter = "s.sglhsrq BETWEEN :start_date AND :end_date"' in monthly_source
    assert 'sales_date_filter = "s.sglhsrq = :revenue_date"' in monthly_source
    assert "s.sglhsrq >= to_date(:revenue_month || '-01', 'YYYY-MM-DD')" in monthly_source
    assert "s.sglhsrq >= to_date(:revenue_month || '-01', 'YYYY-MM-DD')" in detail_source
    assert 'sales_date_filter = "s.sglhsrq BETWEEN :start_date AND :end_date"' in detail_source
    assert '_live_sales_ctes("s.sglhsrq BETWEEN :start_date AND :end_date")' in recalculate_source
    assert "FROM live_sales live" in recalculate_source


def test_revenue_fees_exclude_ticket_reductions_deposits_and_payment_on_behalf():
    fee_sql = " ".join(
        revenue._live_fees_cte(
            "payment_ref.payment_date BETWEEN :start_date AND :end_date",
            date_basis="payment",
        ).split()
    )

    assert "ticket_reduction_fee_keys AS MATERIALIZED" in fee_sql
    assert "charge.person1" in fee_sql
    assert "TRIM(COALESCE(fee.fee_type_code, '')) NOT IN ('37', '61', '69')" in fee_sql
    assert "TRIM(COALESCE(fee.fee_type_name, '')) NOT LIKE '%保证金%'" in fee_sql


def test_revenue_fees_deduplicate_all_exact_source_rows():
    fee_sql = " ".join(
        revenue._live_fees_cte(
            "payment_ref.payment_date BETWEEN :start_date AND :end_date",
            date_basis="payment",
        ).split()
    )

    assert "AS exact_duplicate_rank" in fee_sql
    assert "WHERE fee.exact_duplicate_rank = 1" in fee_sql
    assert "NOT (TRIM(COALESCE(fee.fee_type_name, '')) LIKE '损失承担%') OR fee.exact_duplicate_rank = 1" not in fee_sql


def test_revenue_recalculation_deduplicates_all_exact_fee_source_rows():
    recalculate_source = " ".join(
        inspect.getsource(revenue.recalculate_revenue).split()
    )

    assert "AS exact_duplicate_rank" in recalculate_source
    assert "FROM fee_source_rows fee WHERE fee.exact_duplicate_rank = 1" in recalculate_source


def test_revenue_dashboard_uses_natural_month_for_rental_payments():
    period = revenue._dashboard_financial_period(
        start_date=date(2026, 6, 29),
        end_date=date(2026, 7, 28),
        financial_year=2026,
        financial_month=7,
    )
    dashboard_source = inspect.getsource(revenue.revenue_dashboard)
    detail_source = inspect.getsource(revenue.revenue_dashboard_group_details)

    assert "payment_ref.source_kind = 'RENTAL'" in period["fee_filter"]
    normalized_fee_filter = " ".join(period["fee_filter"].split())
    assert "TO_DATE( :period_month_start || '-01', 'YYYY-MM-DD' )" in normalized_fee_filter
    assert "TO_DATE( :period_month_end || '-01', 'YYYY-MM-DD' ) + INTERVAL '1 month'" in normalized_fee_filter
    assert "payment_ref.source_kind = 'JOINT'" in period["fee_filter"]
    assert "payment_ref.payment_date BETWEEN :start_date AND :end_date" in period["fee_filter"]
    assert 'period["fee_filter"]' in dashboard_source
    assert detail_source.count('period["fee_filter"]') == 2
    assert "联营收费按财务月付款日期、租赁收费按自然月付款日期统计" in dashboard_source


def test_revenue_dashboard_separates_raw_components_from_month_close_adjustment():
    endpoint_source = inspect.getsource(revenue.revenue_dashboard)
    nc_6051_source = inspect.getsource(revenue._load_nc_6051_dashboard_summary)
    page_source = (
        Path(__file__).resolve().parents[1]
        / "client"
        / "src"
        / "pages"
        / "revenue-dashboard.tsx"
    ).read_text(encoding="utf-8")

    assert "target.sales += row.raw_sales_gross_profit_amount" in page_source
    assert "target.fee += row.raw_fee_amount" in page_source
    assert "target.extra += row.raw_extra_amount" in page_source
    assert 'title="富基收费（调整前）"' in page_source
    assert 'title="NC非富基（调整前）"' in page_source
    assert '<Bar dataKey="adjustment" name="月结调整"' in page_source
    assert '<Bar dataKey="tax" name="税"' in page_source
    assert "月结调整（不含税）仅汇总待人工处理的非税差额" in page_source
    assert "销售收益" in page_source
    assert "其他业务收入" in page_source
    assert ">其他业务收入合计</TableHead>" in page_source
    assert "其他业务收入合计（NC6051含税）" not in page_source
    assert '<TableHead className="text-right whitespace-nowrap">税</TableHead>' in page_source
    assert "row.fee + row.extra + row.adjustment" not in page_source
    assert "nc_6051_amount" in page_source
    assert "nc_6051_tax_amount" in nc_6051_source
    assert "tax_close.status = 'CONFIRMED'" in nc_6051_source
    assert "tax_close.period_month" in nc_6051_source
    assert '"tax_period_basis": "confirmed_month_close_only"' in nc_6051_source
    assert "计提.*(销项)?税" in nc_6051_source
    assert '"fully_closed_store_ids": sorted(fully_closed_store_ids)' in endpoint_source
    assert '"tax_adjustment_amount": _money(row.get("tax_adjustment_amount"))' in endpoint_source
    assert "money(otherBusinessIncomeTotal(row))" not in page_source
    assert "金额单位：万元" in page_source
    assert "tenThousandMoney(row.sales)" in page_source
    assert "tenThousandMoney(row.fee)" in page_source
    assert "tenThousandMoney(row.extra)" in page_source
    assert "tenThousandMoney(row.total)" in page_source
    assert "tenThousandMoney(otherBusinessIncomeTotal(row))" in page_source
    assert 'Table className="table-fixed text-xs [&_td]:px-2 [&_td]:py-3 [&_th]:h-9 [&_th]:px-2 lg:text-sm"' in page_source
    assert "<colgroup>" in page_source
    assert 'Table className="min-w-[1280px]"' not in page_source
    assert "TRIM(f.subject_code) LIKE '6051%'" in nc_6051_source
    assert "localcreditamount" in nc_6051_source
    assert "localdebitamount" in nc_6051_source
    assert '"nc_6051_summary": nc_6051_summary' in endpoint_source
    assert 'lg:grid-cols-[12rem_minmax(0,1fr)]' in page_source
    assert '<SelectTrigger id="revenue-dashboard-year" className="w-full">' in page_source
    assert "closedStoreIds.has(row.key)" in page_source
    assert "closedStoreIds.has(selectedStoreKey)" in page_source
    assert "截至{latestClosedPeriodLabel}月结" in page_source
    assert "fullyClosedStoreIds.has(row.key) ? (nc6051?.tax_amount ?? 0) : null" not in page_source


def test_revenue_dashboard_non_tax_adjustment_excludes_tax_only_rows():
    row = {
        "sales_adjustment_amount": 0,
        "fee_adjustment_amount": -29440.98,
        "extra_adjustment_amount": 0,
        "tax_adjustment_amount": -29440.98,
    }

    assert revenue._dashboard_non_tax_adjustment(row) == 0.0


def test_revenue_dashboard_does_not_subtract_nc_tax_from_non_tax_adjustment_twice():
    page_source = (
        Path(__file__).resolve().parents[1]
        / "client"
        / "src"
        / "pages"
        / "revenue-dashboard.tsx"
    ).read_text(encoding="utf-8")

    assert "row.adjustment - tax" not in page_source
    assert "row.adjustment - (row.tax ?? 0)" not in page_source
    assert "pendingAdjustmentByStore.get(row.key)" in page_source
    assert "pendingAdjustmentByDepartment.get" in page_source
    assert "pendingAdjustmentByGroup.get" in page_source
    assert "item.adjustment_amount" in page_source


def test_electricity_transfer_output_tax_is_classified_as_accrued_tax_for_all_stores():
    root = Path(__file__).resolve().parents[1]
    nc_6051_source = inspect.getsource(revenue._load_nc_6051_dashboard_summary)
    side_detail_source = inspect.getsource(revenue._load_month_close_side_details)
    builder_source = (
        root
        / "work"
        / "reconcile-new-century-july-2026"
        / "build_july_department_fee_reconciliation.mjs"
    ).read_text(encoding="utf-8")
    migration_source = (
        root
        / "python_app"
        / "alembic"
        / "versions"
        / "e9a0b1c2d3e4_classify_electricity_output_tax.py"
    ).read_text(encoding="utf-8")

    for source in (nc_6051_source, side_detail_source, builder_source, migration_source):
        assert "电费收入结转销项税" in source
    assert "refresh_nc_6051_extra_receipts" in migration_source
    assert "pg_get_functiondef" in migration_source


def test_monthly_revenue_uses_indexable_store_filter_and_safe_error_detail():
    monthly_source = inspect.getsource(revenue.monthly_revenue)
    detail_source = inspect.getsource(revenue.unit_revenue_detail)

    for source in (monthly_source, detail_source):
        assert 'sales_store_filter = "AND s.sglmarket = :store_code"' in source
        assert 'sales_store_filter = "AND TRIM(s.sglmarket) = :store_code"' not in source
    assert 'detail="获取收益汇总失败，请稍后重试"' in monthly_source
    assert 'detail=f"获取收益汇总失败: {exc}"' not in monthly_source


def test_revenue_map_loads_store_revenue_once_and_filters_floor_in_browser():
    page_source = (
        Path(__file__).resolve().parents[1] / "client" / "src" / "pages" / "revenue-map.tsx"
    ).read_text(encoding="utf-8")

    assert page_source.count("useRevenueMonthly({") == 1
    assert "enabled: hasQueried && selectedStoreIdValue != null" in page_source
    assert "row.floor_id === floorId" in page_source
    assert "monthlyQuery.refetch()" not in page_source


def test_revenue_map_waits_for_query_and_places_period_on_second_row():
    page_source = (
        Path(__file__).resolve().parents[1] / "client" / "src" / "pages" / "revenue-map.tsx"
    ).read_text(encoding="utf-8")
    hook_source = (
        Path(__file__).resolve().parents[1] / "client" / "src" / "hooks" / "useRevenue.ts"
    ).read_text(encoding="utf-8")

    assert "const [hasQueried, setHasQueried] = useState(false)" in page_source
    assert "const revenueResultsReady = hasQueried && !revenueDataFetching && monthlyQuery.data != null" in page_source
    assert "setHasQueried(true)" in page_source
    assert 'data-testid="revenue-map-primary-filters"' in page_source
    assert 'data-testid="revenue-map-period-filters"' in page_source
    assert 'data-testid="revenue-map-results"' in page_source
    assert "请先选择查询条件并点击“查询”" in page_source
    assert "enabled: hasQueried" in page_source
    assert "enabled?: boolean" in hook_source
    assert "enabled: params.enabled ?? true" in hook_source


def test_revenue_map_shows_query_status_while_filters_refresh_data():
    page_source = (
        Path(__file__).resolve().parents[1] / "client" / "src" / "pages" / "revenue-map.tsx"
    ).read_text(encoding="utf-8")

    assert "const revenueDataFetching =" in page_source
    assert "monthlyQuery.isFetching" in page_source
    assert "extraQuery.isFetching" in page_source
    assert 'data-testid="revenue-query-status"' in page_source
    assert 'role="progressbar"' in page_source
    assert "正在查询最新收益数据…" in page_source
    assert "完成后自动更新卡片和地图" in page_source


def test_revenue_map_returns_group_names_and_uses_soft_map_labels():
    source_sql = " ".join(
        revenue._live_revenue_source_ctes(
            "s.sglhsrq BETWEEN :start_date AND :end_date",
            "fee.revenue_date BETWEEN :start_date AND :end_date",
            "extra.revenue_date BETWEEN :start_date AND :end_date",
            "AND s.sglmarket = :store_code",
        ).split()
    )
    monthly_source = inspect.getsource(revenue.monthly_revenue)
    normalized_monthly_source = " ".join(monthly_source.split())
    page_source = (
        Path(__file__).resolve().parents[1] / "client" / "src" / "pages" / "revenue-map.tsx"
    ).read_text(encoding="utf-8")
    hook_source = (
        Path(__file__).resolve().parents[1] / "client" / "src" / "hooks" / "useRevenue.ts"
    ).read_text(encoding="utf-8")
    assert "source_group_code" in source_sql
    assert "source_group_name" in source_sql
    assert "STRING_AGG( DISTINCT NULLIF(TRIM(src.source_group_name), '')" in normalized_monthly_source
    assert '"source_group_names": row.source_group_names' in monthly_source
    assert "source_group_names?: string | null;" in hook_source
    assert "compactRevenueMapLabel" in page_source
    assert "REVENUE_MAP_PALETTE" in page_source
    assert "revenueMoney" in page_source
    assert "<TableHead>柜组名称</TableHead>" in page_source
    assert 'row.source_group_names || "—"' in page_source


def test_revenue_recalculation_reuses_unique_live_binding_resolution():
    recalculate_source = inspect.getsource(revenue.recalculate_revenue)

    assert '_live_sales_ctes("s.sglhsrq BETWEEN :start_date AND :end_date")' in recalculate_source
    assert "FROM live_sales live" in recalculate_source
    assert "JOIN counter_groups cg" not in recalculate_source
    assert "SELECT b.*" not in recalculate_source
    assert "LEFT JOIN LATERAL (" in recalculate_source


def test_live_revenue_source_reads_sales_directly_and_keeps_other_sources():
    sql = " ".join(
        revenue._live_revenue_source_ctes(
            "s.sglhsrq BETWEEN :start_date AND :end_date",
            "fee.revenue_date BETWEEN :start_date AND :end_date",
            "extra.revenue_date BETWEEN :start_date AND :end_date",
            "AND TRIM(s.sglmarket) = :store_code",
        ).split()
    )

    assert "FROM salegoodslist s" in sql
    assert "FROM unit_revenue_fee_detail fee" in sql
    assert "FROM revenue_extra_receipts extra" in sql
    assert "extra.status = 'CONFIRMED'" in sql
    assert "extra.source_type = 'NC6051'" in sql
    assert "unit_daily_revenue_summary" not in sql
    assert "unit_revenue_sales_detail" not in sql
    assert "JOIN manaframe mf" in sql
    assert "UPPER(TRIM(COALESCE(mf.mfstatus, ''))) = 'Y'" in sql
    assert "JOIN counter_groups cg" not in sql
    assert "TRIM(unit_floor.store_code) AS store_code" in sql
    assert "sales_by_group.store_code" in sql
    assert "FROM live_fees fee" in sql
    assert "candidate.contract_code_norm = UPPER(TRIM(fee.contract_code))" in sql
    assert "candidate.source_group_code_norm = UPPER(TRIM(fee.source_group_code))" in sql
    assert "candidate.contract_start_date <= fee.revenue_date" in sql
    assert "candidate.contract_end_date >= fee.revenue_date" in sql
    assert "PARTITION BY fee.id" in sql
    assert "resolved.resolution_rank = 1" in sql


def test_nc_6051_extra_receipts_are_automatic_traceable_and_cabinet_aware():
    root = Path(__file__).resolve().parents[1]
    migration_source = (
        root
        / "python_app"
        / "alembic"
        / "versions"
        / "a5c6d7e8f9a0_automate_nc_6051_extra_receipts.py"
    ).read_text(encoding="utf-8")
    page_source = (root / "client" / "src" / "pages" / "revenue-map.tsx").read_text(
        encoding="utf-8"
    )
    recalculate_source = inspect.getsource(revenue.recalculate_revenue)
    create_source = inspect.getsource(revenue.create_extra_receipt)

    assert "refresh_nc_6051_extra_receipts" in migration_source
    assert "PARTITION BY COALESCE(" in migration_source
    assert "BTRIM(subject_code) IN ('605108', '605112')" in migration_source
    assert "LIKE '%微信电费%'" in migration_source
    assert "LIKE '%物业%'" in migration_source
    assert "LIKE '%运营%'" in migration_source
    assert "NOT (explanation ~ '计提.*(销项)?税')" in migration_source
    assert "PHYSICAL_CABINET" in migration_source
    assert "BACKOFFICE_FALLBACK" in migration_source
    assert "后台部门收益" in migration_source
    assert "revenue_nc_cabinet_alias" in migration_source
    assert "熹木和牛" in migration_source
    assert "6030116065" in migration_source
    assert "JOIN contmanaframe contract_group" in migration_source
    assert "WHEN alias.id IS NOT NULL THEN 0" in migration_source
    assert "source_detail_key" in migration_source
    assert "raw_payload" in migration_source
    assert "FROM refresh_nc_6051_extra_receipts" in recalculate_source
    assert "AND source_type = 'NC6051'" in recalculate_source
    assert "HTTP_410_GONE" in create_source
    assert "新增补收" not in page_source
    assert "保存草稿" not in page_source
    assert "6051 电表、物业、营运收费由后台自动同步" not in page_source
    assert "富基收费" in page_source
    assert "6051非富基收费" in page_source


def test_live_sales_follow_unit_contract_group_relationship_and_remove_sales_tax():
    sql = " ".join(
        revenue._live_sales_ctes(
            "s.sglhsrq BETWEEN :start_date AND :end_date",
            "AND TRIM(s.sglmarket) = :store_code",
        ).split()
    )

    assert "contract_group_bindings AS MATERIALIZED" in sql
    assert "FROM business_unit_binding b" in sql
    assert "JOIN contmain cm" in sql
    assert "JOIN contmanaframe cmf" in sql
    assert "b.shop_unit_id IS NOT NULL" in sql
    assert "NULLIF(TRIM(b.contract_id), '') IS NOT NULL" in sql
    assert "UPPER(TRIM(cmf.cmfmfid)) AS source_group_code_norm" in sql
    assert "candidate.contract_start_date <= sales_by_group.revenue_date" in sql
    assert "candidate.contract_end_date >= sales_by_group.revenue_date" in sql
    assert "candidate.source_group_code_norm = UPPER(TRIM(sales_by_group.source_group_code))" in sql
    assert "candidate.contract_supplier_code_norm = UPPER(TRIM(sales_by_group.source_supplier_code))" in sql
    assert "candidate.contract_operation_mode_norm = TRIM(sales_by_group.source_operation_mode)" in sql
    assert "NULLIF(TRIM(s.sglsupid), '') AS source_supplier_code" in sql
    assert "NULLIF(TRIM(s.sglwmid), '') AS source_operation_mode" in sql
    assert "NULLIF(sales_by_group.source_operation_mode, '')" in sql
    assert "NULLIF(candidate.contract_operation_mode, '')" in sql
    assert "NULLIF(mf.mfjyfs, '')" in sql
    assert sql.index("NULLIF(sales_by_group.source_operation_mode, '')") < sql.index(
        "NULLIF(mf.mfjyfs, '')"
    )
    assert "b.counter_group_id = cg.group_id" not in sql
    assert (
        "(COALESCE(s.sglxssr, 0) + COALESCE(s.sglpfsr, 0)) "
        "/ NULLIF(1 + COALESCE(s.sglxstax, 0), 0)"
        in sql
    )
    assert "COALESCE(SUM(s.sglxssr), 0)::numeric(18,2) AS sales_amount" not in sql
    assert "COALESCE(s.sgln2, 0) / NULLIF(1 + COALESCE(s.sglxstax, 0), 0)" in sql
    assert "COALESCE(SUM(s.sgln2), 0)::numeric AS front_gross_profit_amount" in sql
    assert ")::numeric AS gross_profit_amount" in sql
    assert ")::numeric(18,2) AS gross_profit_amount" not in sql
    assert "JOIN contract_group_bindings candidate" in sql
    assert "ROW_NUMBER() OVER" in sql
    assert (
        "PARTITION BY sales_by_group.revenue_date, "
        "sales_by_group.store_code, sales_by_group.source_group_code, "
        "sales_by_group.source_supplier_code, sales_by_group.source_operation_mode"
        in sql
    )
    assert "COALESCE(candidate.is_primary, false) DESC" in sql
    assert "candidate.binding_id ASC" in sql
    assert "ranked.resolution_rank = 1" in sql
    assert "JOIN LATERAL" not in sql
    assert "cm.cmstatus" not in sql


def test_revenue_recalculation_keeps_supplier_mode_key_and_corrected_amounts():
    source = inspect.getsource(revenue.recalculate_revenue)
    detail_source = inspect.getsource(revenue.unit_revenue_detail)

    assert "matched.sales_amount" in source
    assert "matched.gross_profit_amount" in source
    assert "matched.front_gross_profit_amount" in source
    assert "matched.source_supplier_code" in source
    assert "matched.source_operation_mode" in source
    assert "source_supplier_code', matched.source_supplier_code" in source
    assert "source_operation_mode', matched.source_operation_mode" in source
    assert "live_sales.source_supplier_code" in detail_source
    assert "live_sales.source_operation_mode" in detail_source


def test_unmatched_reasons_use_erp_group_master_and_separate_contract_from_unit():
    sql = " ".join(
        revenue._unmatched_sales_ctes(
            "s.sglhsrq BETWEEN :start_date AND :end_date",
            "AND s.sglmarket = :store_code",
        ).split()
    )
    endpoint_source = inspect.getsource(revenue.unmatched_revenue_details)

    assert "FROM manaframe mf" in sql
    assert "FROM counter_groups" not in sql
    assert "THEN 'GROUP_MASTER_NOT_FOUND'" in sql
    assert "THEN 'GROUP_MASTER_INACTIVE'" in sql
    assert "THEN 'NO_EFFECTIVE_CONTRACT'" in sql
    assert "THEN 'NO_UNIT_BINDING'" in sql
    assert "AS contract_codes" in sql
    assert "cardinality(effective_contracts.contract_codes)" in sql
    assert "TRIM(cm.cmsupid) = source.source_supplier_code" in sql
    assert "TRIM(cm.cmwmid) = source.source_operation_mode" in sql
    assert '"NO_EFFECTIVE_CONTRACT": "销售日无有效合同"' in endpoint_source
    assert '"NO_UNIT_BINDING": "有效合同未绑定柜位"' in endpoint_source


def test_loss_bearing_fee_is_deduplicated_removed_from_tax_and_moved_to_profit():
    sql = " ".join(
        revenue._live_revenue_source_ctes(
            "s.sglhsrq BETWEEN :start_date AND :end_date",
            "fee.revenue_date BETWEEN :start_date AND :end_date",
            "extra.revenue_date BETWEEN :start_date AND :end_date",
        ).split()
    )
    loss_condition = "TRIM(COALESCE(fee.fee_type_name, '')) LIKE '损失承担%'"

    assert revenue.LOSS_BEARING_FEE_NAME_PREFIX == "损失承担"
    assert revenue.LOSS_BEARING_TAX_DIVISOR == "1.13"
    assert "fee_source_rows AS MATERIALIZED" in sql
    assert "AS exact_duplicate_rank" in sql
    assert "NULLIF(TRIM(fee.source_doc_no), '') IS NOT NULL" in sql
    assert "NULLIF(TRIM(fee.source_row_key), '') IS NOT NULL" in sql
    assert "ELSE fee.id" in sql
    assert "WHERE fee.exact_duplicate_rank = 1" in sql
    assert (
        f"WHEN {loss_condition} THEN "
        "fee.tax_excluded_amount / 1.13 "
        in sql
    )
    assert (
        f"CASE WHEN {loss_condition} THEN fee.tax_excluded_amount ELSE 0::numeric END"
        in sql
    )
    assert (
        f"CASE WHEN {loss_condition} THEN 0::numeric ELSE fee.tax_excluded_amount END"
        in sql
    )
    assert f"CASE WHEN {loss_condition} THEN 1::integer ELSE 0::integer END" in sql
    assert f"CASE WHEN {loss_condition} THEN 0::integer ELSE 1::integer END" in sql


def test_fee_tax_excluded_amount_uses_fee_code_tax_rate():
    sql = " ".join(
        revenue._live_fees_cte(
            "fee.revenue_date BETWEEN :start_date AND :end_date"
        ).split()
    )

    assert revenue.FEE_TAX_RATE_FALLBACKS["01"] == "0.05"
    assert revenue.FEE_TAX_RATE_FALLBACKS["02"] == "0.06"
    assert revenue.FEE_TAX_RATE_FALLBACKS["10"] == "0.06"
    assert revenue.FEE_TAX_RATE_FALLBACKS["43"] == "0.13"
    assert revenue.FEE_TAX_RATE_FALLBACKS["73"] == "0.06"
    assert "reference_fee_tax_rates(fee_type_code, tax_rate) AS" in sql
    assert "LEFT JOIN codecharge charge" in sql
    assert "WHEN charge.ccnum3 BETWEEN 0 AND 0.20 THEN charge.ccnum3" in sql
    assert "fee.tax_included_amount / (1 + fee.reference_tax_rate)" in sql
    assert "THEN ROUND(" in sql


def test_revenue_dashboard_paid_fee_basis_uses_settlement_and_rental_payment_dates():
    sql = " ".join(
        revenue._live_fees_cte(
            "payment_ref.payment_date BETWEEN :start_date AND :end_date",
            date_basis="payment",
        ).split()
    )
    dashboard_source = inspect.getsource(revenue.revenue_dashboard)
    detail_source = inspect.getsource(revenue.revenue_dashboard_group_details)

    assert "fee_payment_references AS" in sql
    assert "FROM paybatch pb" in sql
    assert "JOIN supsettlehead ssh" in sql
    assert "ssh.paydate::date AS payment_date" in sql
    assert "FROM mallsuppayhead mph" in sql
    assert "mph.sphpaydate::date AS payment_date" in sql
    assert "payment_ref.payment_date BETWEEN :start_date AND :end_date" in sql
    assert "fee.resolved_payment_date AS effective_revenue_date" in sql
    assert "fee.revenue_date AS occurrence_date" in sql
    assert "candidate.contract_start_date <= fee.occurrence_date" in sql
    assert "candidate.contract_end_date >= fee.occurrence_date" in sql
    assert 'fee_date_basis="payment"' in dashboard_source
    assert 'fee_date_basis="payment"' in detail_source


def test_unit_detail_separates_loss_bearing_from_fee_details():
    source = inspect.getsource(revenue.unit_revenue_detail)

    assert '"loss_bearing_details"' in source
    assert "AND NOT ({loss_bearing_fee_condition})" in source
    assert "AND {loss_bearing_fee_condition}" in source

    page_source = (
        Path(__file__).resolve().parents[1] / "client" / "src" / "pages" / "revenue-map.tsx"
    ).read_text(encoding="utf-8")
    assert "损失承担（已计入销售毛利）" in page_source
    assert "detailQuery.data.loss_bearing_details" in page_source


def test_sales_detail_formats_operation_mode_as_chinese_label():
    page_source = (
        Path(__file__).resolve().parents[1] / "client" / "src" / "pages" / "revenue-map.tsx"
    ).read_text(encoding="utf-8")
    formatter_source = (
        Path(__file__).resolve().parents[1] / "client" / "src" / "lib" / "operation-method.ts"
    ).read_text(encoding="utf-8")

    assert 'import { formatOperationMethod } from "@/lib/operation-method"' in page_source
    assert "formatOperationMethod(row.operation_mode)" in page_source
    assert '"5": "租赁"' in formatter_source


def test_revenue_map_detail_sections_are_collapsed_by_default():
    page_source = (
        Path(__file__).resolve().parents[1] / "client" / "src" / "pages" / "revenue-map.tsx"
    ).read_text(encoding="utf-8")

    assert "salesDetailsOpen" in page_source
    assert "feeDetailsOpen" in page_source
    assert "nonFujiDetailsOpen" in page_source
    assert "<CollapsibleContent" in page_source
    assert "[selectedUnit?.unit_id]" in page_source
    assert "销售毛利明细" in page_source
    assert "富基收费明细" in page_source
    assert "6051非富基收费明细" in page_source


def test_map_queries_do_not_depend_on_recalculated_sales_tables():
    monthly_source = inspect.getsource(revenue.monthly_revenue)
    unmatched_detail_source = inspect.getsource(revenue.unmatched_revenue_details)
    detail_source = inspect.getsource(revenue.unit_revenue_detail)

    assert "_live_revenue_source_ctes" in monthly_source
    assert "_unmatched_sales_ctes" in monthly_source
    assert "unit_daily_revenue_summary" not in monthly_source
    assert "unmatched_revenue_items" not in monthly_source
    assert "_unmatched_sales_ctes" in unmatched_detail_source
    assert "unmatched_revenue_items" not in unmatched_detail_source
    assert "_live_revenue_source_ctes" in detail_source
    assert "_live_sales_ctes" in detail_source
    assert "unit_daily_revenue_summary" not in detail_source
    assert "unit_revenue_sales_detail" not in detail_source


def test_unmatched_summary_and_detail_share_one_live_sales_set():
    unmatched_sql = " ".join(
        revenue._unmatched_sales_ctes(
            "s.sglhsrq BETWEEN :start_date AND :end_date",
            "AND s.sglmarket = :store_code",
        ).split()
    )
    monthly_source = inspect.getsource(revenue.monthly_revenue)
    detail_source = inspect.getsource(revenue.unmatched_revenue_details)
    page_source = (
        Path(__file__).resolve().parents[1] / "client" / "src" / "pages" / "revenue-map.tsx"
    ).read_text(encoding="utf-8")
    hook_source = (
        Path(__file__).resolve().parents[1] / "client" / "src" / "hooks" / "useRevenue.ts"
    ).read_text(encoding="utf-8")
    binding_page_source = (
        Path(__file__).resolve().parents[1] / "client" / "src" / "pages" / "contract-unit-bindings.tsx"
    ).read_text(encoding="utf-8")

    assert "unmatched_sales AS" in unmatched_sql
    assert "FROM sales_by_group source" in unmatched_sql
    assert "FROM live_sales mapped" not in unmatched_sql
    assert "candidate.contract_supplier_code_norm = UPPER(TRIM(source.source_supplier_code))" in unmatched_sql
    assert "candidate.contract_operation_mode_norm = TRIM(source.source_operation_mode)" in unmatched_sql
    assert "master_group.mfcode IS NULL" in unmatched_sql
    assert "GROUP_MASTER_NOT_FOUND" in unmatched_sql
    assert "GROUP_MASTER_INACTIVE" in unmatched_sql
    assert "NO_EFFECTIVE_CONTRACT" in unmatched_sql
    assert "NO_UNIT_BINDING" in unmatched_sql
    assert "MATCHING_RULE_GAP" in unmatched_sql
    assert "FROM contmanaframe cmf JOIN contmain cm" in unmatched_sql
    assert "FROM contract_group_bindings candidate" in unmatched_sql
    assert "_unmatched_sales_ctes(sales_date_filter, sales_store_filter)" in monthly_source
    assert "FROM unmatched_sales" in monthly_source
    assert "_unmatched_sales_ctes(" in detail_source
    assert "COUNT(*) OVER ()::bigint AS total_count" in detail_source
    assert "SUM(gross_profit_amount) OVER ()" in detail_source
    assert '"contract_codes"' in detail_source
    assert '"source_supplier_code"' in detail_source
    assert '"source_operation_mode"' in detail_source
    assert "useRevenueUnmatchedDetails" in hook_source
    assert "/api/revenue-map/unmatched-details" in hook_source
    assert 'aria-label="查看未匹配收益明细"' in page_source
    assert "renderUnmatchedDetailsSheet" in page_source
    assert "导出明细" in page_source
    assert ">合同号</TableHead>" in page_source
    assert "openContractBinding" in page_source
    assert "去绑定" in page_source
    assert "contract_codes: string[]" in hook_source
    assert "source_supplier_code?: string | null" in hook_source
    assert "source_operation_mode?: string | null" in hook_source
    assert 'get("contract_id")' in binding_page_source
    assert "useState(initialContractNo)" in binding_page_source
    assert "门店级" in page_source
    assert '"GROUP_MASTER_NOT_FOUND"' in hook_source
    assert '"NO_EFFECTIVE_CONTRACT"' in hook_source
    assert '"NO_UNIT_BINDING"' in hook_source


def test_revenue_map_page_has_no_manual_recalculation_action():
    page_source = (
        Path(__file__).resolve().parents[1] / "client" / "src" / "pages" / "revenue-map.tsx"
    ).read_text(encoding="utf-8")

    assert "useRecalculateRevenue" not in page_source
    assert "handleRecalculate" not in page_source
    assert ">重算<" not in page_source.replace(" ", "")


def test_revenue_dashboard_uses_shared_business_scope_at_cabinet_grain():
    endpoint_source = inspect.getsource(revenue.revenue_dashboard)
    helper_source = inspect.getsource(revenue._dashboard_row_allowed)

    assert 'require_permission(db, current_user, "revenue.dashboard.view")' in endpoint_source
    assert 'load_business_scope(db, current_user, fallback_resource_code="revenue")' in endpoint_source
    assert "scope_allows_business(" in helper_source
    assert 'group_code=row.get("group_code")' in helper_source
    assert 'department_code=row.get("department_code")' in helper_source
    assert 'store_id=row.get("store_id")' in helper_source

    group_scope = DataScope(allow={"group": {"6010112051"}})
    allowed = {
        "store_id": 1,
        "department_code": "60101",
        "department_name": "服饰部",
        "group_code": "6010112051",
    }
    denied = {**allowed, "group_code": "6010112052"}
    assert revenue._dashboard_row_allowed(group_scope, allowed)
    assert not revenue._dashboard_row_allowed(group_scope, denied)


def test_revenue_dashboard_keeps_map_metric_sources_and_hierarchy_labels():
    endpoint_source = inspect.getsource(revenue.revenue_dashboard)
    page_source = (
        Path(__file__).resolve().parents[1] / "client" / "src" / "pages" / "revenue-dashboard.tsx"
    ).read_text(encoding="utf-8")

    assert "_live_revenue_source_ctes(" in endpoint_source
    assert "sales_gross_profit_amount" in endpoint_source
    assert "fee_amount" in endpoint_source
    assert "extra_amount" in endpoint_source
    assert "fee_breakdown_rows AS" in endpoint_source
    assert "JSONB_AGG(" in endpoint_source
    assert '"fee_breakdown"' in endpoint_source
    assert "tax_excluded_amount" in endpoint_source
    assert '\"grain\": \"门店-部门-柜位\"' in endpoint_source
    assert "数据范围以当前账号权限为准" in page_source
    assert "门店" in page_source
    assert "部门" in page_source
    assert "柜位" in page_source


def test_revenue_dashboard_uses_indexable_department_hierarchy_join():
    endpoint_source = inspect.getsource(revenue.revenue_dashboard)

    assert "ON dept.mfcode = group_mf.mfpcode" in endpoint_source
    assert "ON UPPER(TRIM(dept.mfcode)) = UPPER(TRIM(group_mf.mfpcode))" not in endpoint_source


def test_revenue_dashboard_group_detail_reconciles_daily_profit_and_fee_documents():
    endpoint_source = inspect.getsource(revenue.revenue_dashboard_group_details)
    page_source = (
        Path(__file__).resolve().parents[1] / "client" / "src" / "pages" / "revenue-dashboard.tsx"
    ).read_text(encoding="utf-8")

    assert 'require_permission(db, current_user, "revenue.dashboard.view")' in endpoint_source
    assert "_dashboard_row_allowed(scope, scope_subject)" in endpoint_source
    assert "_live_revenue_source_ctes(" in endpoint_source
    assert "SUM(src.sales_amount)" in endpoint_source
    assert "GROUP BY src.revenue_date" in endpoint_source
    assert "fee.payment_no" in endpoint_source
    assert "AS payment_no" in endpoint_source
    assert "fee.settlement_no" in endpoint_source
    assert "fee.fee_type_name" in endpoint_source
    assert "fee.tax_included_amount" in endpoint_source
    assert "fee.tax_excluded_amount" in endpoint_source
    assert "AND NOT ({loss_bearing_fee_condition})" in endpoint_source
    assert "WHEN month_close.id IS NOT NULL THEN fee.tax_included_amount" in endpoint_source
    assert "fee.tax_excluded_amount" in endpoint_source
    assert "revenue_month_close_adjustments" in endpoint_source
    assert '"month_close_adjustments": adjustment_items' in endpoint_source

    assert 'openDetail(row, "gross-profit")' in page_source
    assert 'openDetail(row, "fees")' in page_source
    assert "每日毛利明细" in page_source
    assert "收益日期" in page_source
    assert "付款单号" in page_source
    assert "结算单号" in page_source
    assert "费用项目" in page_source
    assert "不含税金额" in page_source
    assert "付款日期" in page_source
    assert "收费按付款日期统计，剔除票减及保证金，仅包含已关联付款记录的数据" in page_source


def test_revenue_dashboard_extra_detail_drills_to_nc_subjects_and_explanations():
    endpoint_source = inspect.getsource(revenue.revenue_dashboard_extra_details)
    subject_cte_source = inspect.getsource(revenue._nc_6051_extra_detail_ctes)
    export_endpoint_source = inspect.getsource(revenue.revenue_dashboard_extra_export_details)
    dashboard_source = inspect.getsource(revenue.revenue_dashboard)
    live_source_sql = revenue._live_revenue_source_ctes(
        "s.sglhsrq BETWEEN :start_date AND :end_date",
        "payment_ref.payment_date BETWEEN :start_date AND :end_date",
        "extra.revenue_date BETWEEN :start_date AND :end_date",
    )
    page_source = (
        Path(__file__).resolve().parents[1] / "client" / "src" / "pages" / "revenue-dashboard.tsx"
    ).read_text(encoding="utf-8")

    assert 'require_permission(db, current_user, "revenue.dashboard.view")' in endpoint_source
    assert "FROM ods.nc_bd_accsubj" in subject_cte_source
    assert "finance.pk_detail = extra.source_detail_key" in subject_cte_source
    assert "acc.pk_accsubj = finance_subject.pk_accsubj" in subject_cte_source
    assert "source_subject_code" in endpoint_source
    assert "source_explanation" in endpoint_source
    assert "voucher_no" in endpoint_source
    assert "COUNT(*)::bigint AS detail_count" in endpoint_source
    assert "SUM(amount) OVER ()" in endpoint_source
    assert "extra_adjustment_rows" in endpoint_source
    assert "adjustment.target_component = 'EXTRA'" in endpoint_source
    assert '"month_close_adjustments": adjustment_items' in endpoint_source
    assert "_dashboard_row_allowed(scope, scope_subject)" in endpoint_source
    assert "extra.source_department_code" in live_source_sql
    assert "extra.source_department_name" in live_source_sql
    assert "src.source_department_code" in dashboard_source
    assert "src.source_department_name" in dashboard_source
    assert 'require_permission(db, current_user, "revenue.dashboard.view")' in export_endpoint_source
    assert "_nc_6051_extra_detail_ctes(date_filter_sql=period[\"extra_filter\"])" in export_endpoint_source
    assert "_dashboard_row_allowed(" in export_endpoint_source
    assert '"source_detail_key"' in export_endpoint_source
    assert 'openDetail(row, "extras")' in page_source
    assert "/api/revenue-map/dashboard/extra-details" in page_source
    assert "其他收益科目及摘要明细" in page_source
    assert "科目明细" in page_source
    assert "摘要明细" in page_source
    assert "NC凭证" in page_source
    assert 'row.group_code || `unit:${row.unit_codes || "未绑定"}:name:${row.group_name}`' in page_source


def test_revenue_dashboard_exports_group_grain_with_month_close_columns():
    page_source = (
        Path(__file__).resolve().parents[1] / "client" / "src" / "pages" / "revenue-dashboard.tsx"
    ).read_text(encoding="utf-8")
    export_source = (
        Path(__file__).resolve().parents[1]
        / "client"
        / "src"
        / "lib"
        / "revenue-dashboard-export.ts"
    ).read_text(encoding="utf-8")

    assert "exportRevenueDashboardExcel(" in page_source
    assert "导出最明细" in page_source
    assert "门店编码" in export_source
    assert "部门编码" in export_source
    assert "柜组编码" in export_source
    assert "销售毛利（不含税）" in export_source
    assert "富基收费（调整前）" in export_source
    assert "富基收费对应月结调整" in export_source
    assert "富基收费（调整后）" in export_source
    assert "NC非富基收费（调整前）" in export_source
    assert "NC非富基对应月结调整" in export_source
    assert "月结调整合计" in export_source
    assert "feeColumns.map" in export_source
    assert "收费分类校验差额" in export_source
    assert "其他收益科目汇总" in export_source
    assert "其他收益摘要明细" in export_source
    assert "科目编码" in export_source
    assert "NC凭证" in export_source
    assert "来源明细键" in export_source
    assert "/api/revenue-map/dashboard/extra-export-details" in page_source
    assert "正在整理科目" in page_source
    assert "销售毛利按财务日期；收费按付款日期且剔除票减及保证金；其他收益按财务期间" in export_source
    assert "未关联结算付款日期或租赁付款日期的收费不进入本次导出" in export_source


def test_revenue_dashboard_overlays_confirmed_month_close_without_overwriting_sources():
    overlay_sql = " ".join(revenue._revenue_month_close_overlay_ctes().split())
    endpoint_source = inspect.getsource(revenue.revenue_dashboard)
    migration_source = (
        Path(__file__).resolve().parents[1]
        / "python_app"
        / "alembic"
        / "versions"
        / "b6d7e8f9a0b1_create_revenue_month_close_snapshots.py"
    ).read_text(encoding="utf-8")

    assert "confirmed_month_closes AS MATERIALIZED" in overlay_sql
    assert "close.period_start_date = :start_date" in overlay_sql
    assert "close.period_end_date = :end_date" in overlay_sql
    assert "src.close_basis_fee_amount" in overlay_sql
    assert "adjustment.target_component = 'FEE'" in overlay_sql
    assert "adjustment.target_component = 'EXTRA'" in overlay_sql
    assert "adjustment.binding_status = 'BOUND'" in overlay_sql
    assert "adjustment.binding_status = 'PENDING'" in overlay_sql
    assert "manual_binding_source_line_key" in overlay_sql
    assert "dashboard_pending_adjustment_rows AS" in overlay_sql
    assert "待人工绑定" in overlay_sql
    assert (
        "ROUND( COALESCE(adjustment.adjustment_amount, 0) - "
        "COALESCE(adjustment.accrued_tax_amount, 0), 2 ) <> 0"
        in overlay_sql
    )
    assert "dashboard_source_rows AS" in overlay_sql
    assert "dashboard_snapshot_bridge_rows AS" not in overlay_sql
    assert "MONTH_CLOSE_PERIOD" not in overlay_sql
    assert "PERIOD_BRIDGE" not in endpoint_source
    assert "close.raw_fee_amount - totals.live_fee_amount" not in endpoint_source
    assert "FROM dashboard_source_rows src" in endpoint_source
    assert '"accounting_basis": accounting_basis' in endpoint_source
    assert '"month_closes": month_closes' in endpoint_source
    assert "CREATE TABLE revenue_month_closes" in migration_source
    assert "CREATE TABLE revenue_month_close_adjustments" in migration_source
    assert "created_by INTEGER REFERENCES users(user_id)" in migration_source
    assert "confirmed_by INTEGER REFERENCES users(user_id)" in migration_source
    assert "REFERENCES users(id)" not in migration_source
    assert "不覆盖富基收费和NC补收原始行" in migration_source


def test_revenue_month_close_difference_requires_manual_cabinet_binding():
    list_source = inspect.getsource(revenue.revenue_month_close_pending_bindings)
    side_detail_source = inspect.getsource(revenue._load_month_close_side_details)
    bind_source = inspect.getsource(revenue.bind_revenue_month_close_difference)
    request_source = inspect.getsource(revenue.RevenueMonthCloseBindingRequest)
    page_source = (
        Path(__file__).resolve().parents[1]
        / "client"
        / "src"
        / "pages"
        / "revenue-dashboard.tsx"
    ).read_text(encoding="utf-8")
    builder_source = (
        Path(__file__).resolve().parents[1]
        / "work"
        / "month-close-new-century-july-2026"
        / "build_month_close_trial.mjs"
    ).read_text(encoding="utf-8")

    assert "adjustment.binding_status = 'PENDING'" in list_source
    assert "adjustment.source_group_code" in list_source
    assert "adjustment.source_group_name" in list_source
    assert "AND adjustment.source_business_type = 'NC_EXTRA_DIFFERENCE'" not in list_source
    assert "difference_direction" in list_source
    assert '"direction_summary": direction_summary' in list_source
    assert "_load_month_close_side_details" in list_source
    assert "_month_close_unbound_source_details" in list_source
    assert '"nc_details": unbound_details_by_adjustment' in list_source
    assert '"fuji_details": unbound_details_by_adjustment' in list_source
    assert "_reconcile_month_close_detail_rows" in list_source
    assert '"auto_matched_count": auto_matched_count' in list_source
    assert "JOIN bh_dw_gl_detail_fact2 f" in side_detail_source
    assert "JOIN dw.revenue_fee_unified u" in side_detail_source
    assert "joint_payment.auditdate >= close.period_start_date" in side_detail_source
    assert "close.period_month || '-01'" in side_detail_source
    assert "rental_payment.auditdate >= close.period_start_date" not in side_detail_source
    assert "WHEN u.business_type = 'JOINT' THEN joint_payment.auditdate" in side_detail_source
    assert "ELSE rental_payment.auditdate" in side_detail_source
    assert "inputdate AS audit_date" not in side_detail_source
    assert revenue.REVENUE_SUBJECT_FEE_CODES["605111"] == ("19", "20", "22")
    assert revenue.REVENUE_SUBJECT_FEE_CODES["60515009"] == ("26",)
    assert "floor.name AS floor_name" in list_source
    assert "business_unit_binding binding" in list_source
    assert "JOIN contmain contract" in list_source
    assert "JOIN contmanaframe contract_group" in list_source
    assert "LEFT JOIN manaframe group_frame" in list_source
    assert "contract_group.cmfmfid" in list_source
    assert "contract_group.cmflapdate" not in list_source
    assert "COALESCE(contract.cmlapdate::date, DATE '2999-12-31') >= :start_date" in list_source
    assert "counter_group.is_active" not in list_source
    assert '"group_options": []' in list_source
    assert '"binding_lines": _month_close_binding_lines' in list_source
    assert 'require_permission(db, current_user, "revenue.recalculate")' in bind_source
    assert "AND adjustment.source_business_type = 'NC_EXTRA_DIFFERENCE'" not in bind_source
    assert "只能绑定到同一门店的柜位" in bind_source
    assert "所选柜组不是该柜位在本月有效的对应柜组" in bind_source
    assert "JOIN contmain contract" in bind_source
    assert "JOIN contmanaframe contract_group" in bind_source
    assert "contract_group.cmfmfid" in bind_source
    assert "contract_group.cmflapdate" not in bind_source
    assert "COALESCE(contract.cmlapdate::date, DATE '2999-12-31') >= :period_start_date" in bind_source
    assert "counter_group.is_active" not in bind_source
    assert "manual_binding_source_line_key" in bind_source
    assert "manual_binding_target_component" in bind_source
    assert '"target_component": body.target_component' in bind_source
    assert "target_component: str = Field" in request_source
    assert "^(FEE|EXTRA)$" in request_source
    assert "manual_binding_counter_group_id" in bind_source
    assert "remaining_bindable_amount" in bind_source
    assert "计提税不参与柜位绑定" in bind_source
    assert "manual_binding_tax_only_remainder" in bind_source
    assert "binding_status = 'BOUND'" in bind_source
    assert "不分摊；人工确认柜位后生效" in builder_source
    assert "正向收费金额占比" not in builder_source
    assert "已逐笔匹配一致的收费不会出现在本表" in builder_source
    assert 'new Set(["18", "38", "61", "69", "94", "95"])' in builder_source
    assert 'feeCode.startsWith("00")' in builder_source
    assert "/保证金|质保金|代扣代缴保险费|旅通|瑞祥/" in builder_source
    assert "const excludedFujiFeeRows = allFeeRows.filter" in builder_source
    assert "const feeRows = allFeeRows.filter" in builder_source
    assert builder_source.index("const excludedFujiFeeRows") < builder_source.index("function aggregateFeeRows")
    assert "销售、保证金、质保金、代扣保险和旅通/瑞祥卡已在匹配前逐行剔除" in builder_source
    assert 'MONTH_CLOSE_STORE_CODE || "603"' in builder_source
    assert 'storeName: "百货大楼", storeCode: "602", storeId: 2' in builder_source
    assert 'storeName: "购物中心", storeCode: "601", storeId: 1' in builder_source

    reconciliation_builder_source = (
        Path(__file__).resolve().parents[1]
        / "work"
        / "reconcile-new-century-july-2026"
        / "build_july_department_fee_reconciliation.mjs"
    ).read_text(encoding="utf-8")
    assert 'storeName: "百货大楼", storeCode: "602"' in reconciliation_builder_source
    assert '["6020101", "2217"]' in reconciliation_builder_source
    assert '["6020105", "2212"]' in reconciliation_builder_source
    assert '["6020110", "2220"]' in reconciliation_builder_source
    assert 'groupDepartmentOverrides: [' in reconciliation_builder_source
    assert '["6030104082", "3137"]' in reconciliation_builder_source
    assert '["6030104101", "3137"]' in reconciliation_builder_source
    assert '["6030104096", "3137"]' in reconciliation_builder_source
    assert '["6030104095", "3137"]' in reconciliation_builder_source
    assert "groupDepartmentOverride.get(text(row.source_group_code))" in reconciliation_builder_source
    assert '["60515007", ["25", "29", "76", "79"]]' in reconciliation_builder_source
    assert '["60515009", ["26"]]' in reconciliation_builder_source
    assert "const excludedCardFeeRows = fee.filter" in reconciliation_builder_source
    assert 'worksheets.add("6051口径排除")' in reconciliation_builder_source
    assert "u.business_type='JOINT' AND j.auditdate >= TIMESTAMP '${financialStartDate}'" in reconciliation_builder_source
    assert "u.business_type='RENTAL' AND r.auditdate >= TIMESTAMP '${calendarStartDate}'" in reconciliation_builder_source
    assert "RECON_MONTH || \"7\"" in reconciliation_builder_source
    assert "const financialStartDate" in reconciliation_builder_source
    assert "const calendarEndExclusive" in reconciliation_builder_source
    assert "r.auditdate < TIMESTAMP '${calendarEndExclusive}'" in reconciliation_builder_source
    assert "r.auditdate < TIMESTAMP '${financialEndExclusive}'" not in reconciliation_builder_source
    assert "月结双向核对及待人工绑定明细" in page_source
    assert "待双向核对" in page_source
    assert "pendingBindingStoreSummaries" in page_source
    assert "待核对 {summary.pending_count} 条" in page_source
    assert "displayedPendingBindingItems" in page_source
    assert "NC有、富基无" in page_source
    assert "富基有、NC无" in page_source
    assert "双方金额不一致" in page_source
    assert "富基费用未匹配" in page_source
    assert "NC费用未匹配" in page_source
    assert "计提税" in page_source
    assert "FujiSideDetails" in page_source
    assert "NcSideDetails" in page_source
    assert "系统已自动核对隐藏" in page_source
    assert "富基未匹配明细" in page_source
    assert "剩余明细按同部门、同科目、同供应商汇总后再与NC匹配" in page_source
    assert '审核日期 {shortDate(detail.audit_date)}' in page_source
    assert "NC 未匹配明细" in page_source
    assert "计提税不参与待核对和柜位绑定" in page_source
    assert "计提税明细" not in page_source
    assert "TaxSideDetails" not in page_source
    assert "/dashboard/month-close-bindings/" in page_source
    assert "按来源明细人工绑定" in page_source
    assert "关联柜组" in page_source
    assert "NC非税目标金额" in page_source
    assert "待绑定非税差额" in page_source
    assert "group_options" in page_source
    assert "value={group.group_code}" in page_source
    assert "sourceLineKey" in page_source
    assert "计入富基收费" in page_source
    assert "计入NC非富基收费" in page_source
    assert "target_component: targetComponent" in page_source
    assert "确认绑定" in page_source
    assert 'type="always"' in page_source
    assert "horizontal" in page_source
    assert 'containerClassName="overflow-visible pb-3 pr-3"' in page_source


def test_month_close_binding_lines_allocate_the_pending_amount_per_source_row():
    row = {
        "id": 101,
        "difference_direction": "NC_ONLY",
        "adjustment_amount": 200566.08,
    }
    reconciled = {
        "nc_details": [
            {"detail_id": "NC-1", "voucher_id": "V-1", "amount": 205400},
            {"detail_id": "NC-2", "voucher_id": "V-2", "amount": 7200},
        ],
        "fuji_details": [],
    }

    lines = revenue._month_close_binding_lines(row, reconciled)

    assert len(lines) == 2
    assert [line["source_type"] for line in lines] == ["NC", "NC"]
    assert [line["source_detail_id"] for line in lines] == ["NC-1", "NC-2"]
    assert round(sum(line["suggested_binding_amount"] for line in lines), 2) == 200566.08
    assert all(line["suggested_binding_amount"] > 0 for line in lines)

    remaining_row = {
        **row,
        "adjustment_amount": lines[1]["suggested_binding_amount"],
    }
    remaining_lines = revenue._month_close_binding_lines(
        remaining_row,
        reconciled,
        {lines[0]["source_line_key"]},
    )

    assert len(remaining_lines) == 1
    assert remaining_lines[0]["source_detail_id"] == "NC-2"
    assert remaining_lines[0]["suggested_binding_amount"] == lines[1]["suggested_binding_amount"]


def test_month_close_bound_source_line_is_removed_from_pending_details():
    reconciled = {
        "nc_details": [
            {"detail_id": "NC-1", "voucher_id": "V-1", "amount": 205400},
            {"detail_id": "NC-2", "voucher_id": "V-2", "amount": 7200},
        ],
        "fuji_details": [],
        "tax_details": [],
        "tax_detail_count": 0,
        "tax_detail_amount": 0,
        "auto_matched_count": 0,
        "auto_matched_amount": 0,
        "auto_matches": [],
    }
    bound_key = revenue._month_close_binding_line_key(
        "NC",
        reconciled["nc_details"][0],
        0,
    )

    unbound = revenue._month_close_unbound_source_details(reconciled, {bound_key})

    assert [detail["detail_id"] for detail in unbound["nc_details"]] == ["NC-2"]
    assert reconciled["nc_details"][0]["detail_id"] == "NC-1"


def test_month_close_manual_binding_excludes_accrued_tax_from_the_bindable_difference():
    amount_difference = {
        "id": 201,
        "difference_direction": "AMOUNT_DIFFERENCE",
        "raw_amount": 900,
        "accrued_tax_amount": -52.64,
        "adjustment_amount": -22.64,
        "final_amount": 877.36,
    }
    nc_only = {
        "id": 202,
        "difference_direction": "NC_ONLY",
        "raw_amount": 0,
        "accrued_tax_amount": -12033.92,
        "adjustment_amount": 200566.08,
        "final_amount": 200566.08,
    }

    assert revenue._month_close_bindable_amount(amount_difference) == 30.0
    assert revenue._month_close_binding_target_amount(amount_difference) == 930.0
    assert revenue._month_close_bindable_amount(nc_only) == 212600.0
    assert revenue._month_close_binding_target_amount(nc_only) == 212600.0

    lines = revenue._month_close_binding_lines(
        nc_only,
        {
            "nc_details": [
                {"detail_id": "NC-1", "voucher_id": "V-1", "amount": 205400},
                {"detail_id": "NC-2", "voucher_id": "V-2", "amount": 7200},
            ],
            "fuji_details": [],
        },
    )
    assert round(sum(line["suggested_binding_amount"] for line in lines), 2) == 212600.0


def test_month_close_pending_rows_are_summarized_by_store():
    visible_rows = [
        {
            "id": 1,
            "store_id": 2,
            "store_code": "602",
            "store_name": "常州百货大楼",
            "difference_direction": "NC_ONLY",
            "adjustment_amount": 100,
        },
        {
            "id": 2,
            "store_id": 2,
            "store_code": "602",
            "store_name": "常州百货大楼",
            "difference_direction": "AMOUNT_DIFFERENCE",
            "adjustment_amount": -20,
        },
        {
            "id": 3,
            "store_id": 3,
            "store_code": "603",
            "store_name": "常州新世纪商城",
            "difference_direction": "FUJI_ONLY",
            "adjustment_amount": 50,
        },
    ]
    allowed_rows = [
        *visible_rows,
        {
            "id": 4,
            "store_id": 2,
            "store_code": "602",
            "store_name": "常州百货大楼",
            "difference_direction": "OTHER",
            "adjustment_amount": 0,
        },
    ]
    reconciled = {
        1: {"auto_matched_count": 1, "auto_matched_amount": 100},
        2: {"auto_matched_count": 0, "auto_matched_amount": 0},
        3: {"auto_matched_count": 2, "auto_matched_amount": 50},
        4: {"auto_matched_count": 3, "auto_matched_amount": 300},
    }

    summaries = revenue._month_close_store_summaries(
        visible_rows,
        allowed_rows,
        reconciled,
    )

    assert [summary["store_code"] for summary in summaries] == ["602", "603"]
    assert summaries[0]["pending_count"] == 2
    assert summaries[0]["pending_amount"] == 80.0
    assert summaries[0]["direction_summary"]["NC_ONLY"]["count"] == 1
    assert summaries[0]["auto_matched_count"] == 4
    assert summaries[0]["auto_matched_amount"] == 400.0
    assert summaries[1]["pending_count"] == 1
    assert summaries[1]["direction_summary"]["FUJI_ONLY"]["count"] == 1


def test_month_close_detail_reconciliation_hides_only_exact_supplier_amount_pairs():
    nc_details = [
        {
            "detail_id": "NC-1383",
            "voucher_id": "V-1",
            "explanation": "20260701-20260731营运一部宁波鸿岚服饰有限公司能耗服务费",
            "amount": 1383.00,
            "is_accrued_tax": False,
        },
        {
            "detail_id": "NC-928",
            "voucher_id": "V-2",
            "explanation": "20260701-20260731营运一部苏州宅惠影贸易有限公司能耗服务费",
            "amount": 928.01,
            "is_accrued_tax": False,
        },
        {
            "detail_id": "NC-TAX",
            "voucher_id": "V-3",
            "explanation": "计提销项税 宁波鸿岚服饰有限公司",
            "amount": 1383.00,
            "is_accrued_tax": True,
        },
    ]
    fuji_details = [
        {
            "source_bill_no": "F-1383",
            "source_row_no": "5",
            "source_group_code": "6020102056",
            "supplier_name": "宁波鸿岚服饰有限公司",
            "fee_type_name": "能耗服务费（周期）",
            "amount": 1383.00,
        },
        {
            "source_bill_no": "F-928",
            "source_row_no": "6",
            "source_group_code": "6020110024",
            "supplier_name": "苏州宅惠影贸易有限公司",
            "fee_type_name": "能耗服务费（周期）",
            "amount": 928.00,
        },
    ]

    result = revenue._reconcile_month_close_detail_rows(nc_details, fuji_details)

    assert result["auto_matched_count"] == 1
    assert result["auto_matched_amount"] == 1383.00
    assert result["nc_details"] == [nc_details[1]]
    assert result["fuji_details"] == fuji_details[1:]
    assert result["tax_details"] == [nc_details[2]]
    assert result["tax_detail_count"] == 1
    assert result["tax_detail_amount"] == 1383.00
    assert result["auto_matches"] == [
        {
            "amount": 1383.00,
            "supplier_name": "宁波鸿岚服饰有限公司",
            "nc_detail_id": "NC-1383",
            "nc_voucher_id": "V-1",
            "fuji_source_bill_no": "F-1383",
            "fuji_source_row_no": "5",
            "source_group_code": "6020102056",
        }
    ]


def test_month_close_detail_reconciliation_does_not_match_amount_only():
    nc_details = [
        {
            "detail_id": "NC-1",
            "explanation": "营运一部甲供应商广告服务费",
            "amount": 1000.00,
            "is_accrued_tax": False,
        }
    ]
    fuji_details = [
        {
            "source_bill_no": "F-1",
            "supplier_name": "乙供应商",
            "fee_type_name": "广告服务费",
            "amount": 1000.00,
        }
    ]

    result = revenue._reconcile_month_close_detail_rows(nc_details, fuji_details)

    assert result["auto_matched_count"] == 0
    assert result["nc_details"] == nc_details
    assert result["fuji_details"] == fuji_details


def test_month_close_reconciliation_offsets_fuji_reversals_before_nc_matching():
    nc_details = [
        {
            "detail_id": "NC-88950",
            "voucher_id": "V-88950",
            "explanation": "20260709新世纪七部钟楼区荷花池美因子家居用品商行能耗服务费",
            "amount": 889.50,
            "is_accrued_tax": False,
        },
        {
            "detail_id": "NC-100",
            "voucher_id": "V-100",
            "explanation": "20260709新世纪七部钟楼区荷花池美因子家居用品商行能耗服务费",
            "amount": 100.00,
            "is_accrued_tax": False,
        }
    ]
    shared_fuji_fields = {
        "business_type": "RENTAL",
        "source_bill_no": "26070960310000000024",
        "source_group_code": "6030106119",
        "supplier_code": "80171",
        "supplier_name": "钟楼区荷花池美因子家居用品商行",
        "fee_type_code": "73",
        "fee_type_name": "能耗服务费（周期）",
        "audit_date": "2026-07-09",
    }
    fuji_details = [
        {**shared_fuji_fields, "source_row_no": "13", "amount": -889.50},
        {**shared_fuji_fields, "source_row_no": "14", "amount": 889.50},
        {**shared_fuji_fields, "source_row_no": "15", "amount": 100.00},
    ]

    result = revenue._reconcile_month_close_detail_rows(nc_details, fuji_details)

    assert result["nc_details"] == [nc_details[0]]
    assert result["fuji_details"] == []
    assert result["auto_matched_count"] == 2
    assert result["auto_matched_amount"] == 100.00
    assert result["fuji_offset_count"] == 1
    assert result["fuji_offset_amount"] == 0.00
    assert result["auto_matches"][0] == {
        "match_type": "FUJI_OFFSET",
        "amount": 0.00,
        "supplier_name": "钟楼区荷花池美因子家居用品商行",
        "nc_detail_id": None,
        "nc_voucher_id": None,
        "fuji_source_bill_no": "26070960310000000024,26070960310000000024",
        "fuji_source_row_no": "13,14",
        "source_group_code": "6030106119",
    }


def test_month_close_reconciliation_does_not_offset_different_fuji_scopes():
    shared_fuji_fields = {
        "business_type": "RENTAL",
        "source_bill_no": "26070960310000000024",
        "source_group_code": "6030106119",
        "supplier_code": "80171",
        "supplier_name": "钟楼区荷花池美因子家居用品商行",
        "fee_type_code": "73",
        "fee_type_name": "能耗服务费（周期）",
        "audit_date": "2026-07-09",
    }
    fuji_details = [
        {**shared_fuji_fields, "source_row_no": "13", "amount": -889.50},
        {
            **shared_fuji_fields,
            "source_row_no": "14",
            "source_group_code": "6030106120",
            "amount": 889.50,
        },
    ]

    result = revenue._reconcile_month_close_detail_rows([], fuji_details)

    assert result["fuji_details"] == fuji_details
    assert result["auto_matched_count"] == 0
    assert result["fuji_offset_count"] == 0


def test_month_close_detail_reconciliation_matches_parent_and_branch_company_names():
    nc_details = [
        {
            "detail_id": "NC-16866",
            "voucher_id": "V-1",
            "explanation": "20260501-20260531芜湖市丰宜科技有限公司",
            "amount": 168.66,
            "is_accrued_tax": False,
        },
        {
            "detail_id": "NC-807",
            "voucher_id": "V-2",
            "explanation": "20260601-20260630芜湖市丰宜科技有限公司",
            "amount": 8.07,
            "is_accrued_tax": False,
        },
    ]
    fuji_details = [
        {
            "source_bill_no": "F-16866",
            "source_row_no": "1",
            "source_group_code": "6020105017",
            "supplier_name": "芜湖市丰宜科技有限公司常州分公司",
            "fee_type_name": "服务费",
            "amount": 168.66,
        },
        {
            "source_bill_no": "F-807",
            "source_row_no": "1",
            "source_group_code": "6020105017",
            "supplier_name": "芜湖市丰宜科技有限公司常州分公司",
            "fee_type_name": "服务费",
            "amount": 8.07,
        },
    ]

    result = revenue._reconcile_month_close_detail_rows(nc_details, fuji_details)

    assert result["auto_matched_count"] == 2
    assert result["auto_matched_amount"] == 176.73
    assert result["nc_details"] == []
    assert result["fuji_details"] == []


def test_month_close_supplier_alias_does_not_drop_non_branch_suffixes():
    assert revenue._month_close_supplier_tokens(
        "芜湖市丰宜科技有限公司常州经销部"
    ) == {"芜湖市丰宜科技有限公司常州经销部"}


def test_month_close_supplier_match_tokens_tolerate_safe_nc_name_truncation():
    tokens = revenue._month_close_supplier_match_tokens(
        "菲拉格慕时装贸易(上海)有限公司"
    )

    assert "菲拉格慕时装贸易" in tokens
    assert "菲拉格慕时装贸易上海" in tokens
    assert "菲拉格慕时装贸易上海有限公" in tokens

    shop_tokens = revenue._month_close_supplier_match_tokens(
        "天宁区天宁摹尔家居用品店"
    )
    assert "天宁区天宁摹尔家居用" in shop_tokens


def test_month_close_supplier_match_tokens_strip_individual_business_qualifier():
    tokens = revenue._month_close_supplier_match_tokens(
        "天宁区天宁好特麦饮品店（个体工商户）"
    )

    assert "天宁区天宁好特麦饮品店" in tokens
    assert "天宁区天宁好特麦饮品" in tokens


def test_month_close_reconciliation_matches_long_supplier_brand_core():
    nc_details = [
        {
            "detail_id": "NC-ENERGY",
            "voucher_id": "V-ENERGY",
            "explanation": "20260523-20260622中心八部(特业)常州市新北区财记牛腩能耗服务",
            "amount": 4509.00,
            "is_accrued_tax": False,
        },
        {
            "detail_id": "NC-CARD",
            "voucher_id": "V-CARD",
            "explanation": "20260601-20260630中心八部(特业)常州市新北区财记牛腩储值卡管",
            "amount": 14.62,
            "is_accrued_tax": False,
        },
    ]
    fuji_details = [
        {
            "source_bill_no": "26071560110000000009",
            "source_row_no": "6",
            "source_group_code": "6010112049",
            "supplier_name": "常州市新北区财记牛腩餐饮管理有限公司天宁分公司",
            "fee_type_code": "71",
            "amount": 4509.00,
        },
        {
            "source_bill_no": "26071560110000000009",
            "source_row_no": "3",
            "source_group_code": "6010112049",
            "supplier_name": "常州市新北区财记牛腩餐饮管理有限公司天宁分公司",
            "fee_type_code": "10",
            "amount": 14.62,
        },
    ]

    result = revenue._reconcile_month_close_detail_rows(nc_details, fuji_details)

    assert result["nc_details"] == []
    assert result["fuji_details"] == []
    assert result["auto_matched_count"] == 2
    assert result["auto_matched_amount"] == 4523.62


def test_month_close_supplier_brand_core_does_not_match_shared_location_only():
    assert revenue._month_close_supplier_matches_explanation(
        "常州市新北区乙品牌餐饮管理有限公司",
        "中心八部常州市新北区甲品牌能耗服务",
    ) is False


def test_month_close_reconciliation_aggregates_fuji_rows_after_supplier_normalization():
    nc_details = [
        {
            "detail_id": "1018A9100000000DK286",
            "voucher_id": "1018A9100000000DK283",
            "explanation": "20260801-20261031中心八部(特业)天宁区天宁好特麦饮品租金",
            "amount": 48852.00,
            "is_accrued_tax": False,
        },
        {
            "detail_id": "1018A9100000000DKERU",
            "voucher_id": "1018A9100000000DKERR",
            "explanation": "20260630-20260831中心八部(特业)天宁区天宁豚王餐饮店租金",
            "amount": 26881.80,
            "is_accrued_tax": False,
        },
    ]
    fuji_details = [
        {
            "source_bill_no": "26072260110000000003",
            "source_row_no": str(index),
            "source_group_code": "6010112075",
            "supplier_name": "天宁区天宁好特麦饮品店（个体工商户）",
            "fee_type_code": "01",
            "amount": amount,
        }
        for index, amount in enumerate((16461.00, 15930.00, 16461.00), start=1)
    ] + [
        {
            "source_bill_no": "26072760110000000001",
            "source_row_no": "3",
            "source_group_code": "6010112073",
            "supplier_name": "天宁区天宁豚王餐饮店（个体工商户）",
            "fee_type_code": "01",
            "amount": 20615.00,
        },
        {
            "source_bill_no": "26072760110000000001",
            "source_row_no": "8",
            "source_group_code": "6010112073",
            "supplier_name": "天宁区天宁豚王餐饮店（个体工商户）",
            "fee_type_code": "60",
            "amount": 6266.80,
        },
    ]

    result = revenue._reconcile_month_close_detail_rows(nc_details, fuji_details)

    assert result["nc_details"] == []
    assert result["fuji_details"] == []
    assert result["auto_matched_count"] == 2
    assert result["auto_matched_amount"] == 75733.80


def test_month_close_mapped_fee_rows_replace_legacy_unmapped_adjustments():
    rows = [
        {
            "id": 1,
            "month_close_id": 14,
            "source_department_code": "2121",
            "source_subject_code": "未映射",
            "fee_type_code": "26",
        },
        {
            "id": 2,
            "month_close_id": 14,
            "source_department_code": "2121",
            "source_subject_code": "60515009",
            "fee_type_code": None,
        },
        {
            "id": 3,
            "month_close_id": 14,
            "source_department_code": "2121",
            "source_subject_code": "未映射",
            "fee_type_code": "44",
        },
        {
            "id": 4,
            "month_close_id": 14,
            "source_department_code": "2122",
            "source_subject_code": "未映射",
            "fee_type_code": "26",
        },
    ]

    filtered = revenue._collapse_legacy_mapped_fuji_rows(rows)

    assert [row["id"] for row in filtered] == [2, 3, 4]


def test_month_close_reconciliation_matches_truncated_names_and_supplier_totals():
    nc_details = [
        {
            "detail_id": "NC-SUZHOU",
            "voucher_id": "V-1",
            "explanation": "20260601-20260630营运一部苏州宅慧影贸易有限公信用卡手续费",
            "amount": 312.63,
            "is_accrued_tax": False,
        },
        {
            "detail_id": "NC-HASSEN",
            "voucher_id": "V-2",
            "explanation": "20260717营运一部哈森商贸(中国)股份有付款信用卡手续费",
            "amount": 190.06,
            "is_accrued_tax": False,
        },
        {
            "detail_id": "NC-BELLE",
            "voucher_id": "V-3",
            "explanation": "20260717营运一部百丽鞋业(上海)有限公付款信用卡手续费",
            "amount": 1292.94,
            "is_accrued_tax": False,
        },
        {
            "detail_id": "NC-LINGOU",
            "voucher_id": "V-4",
            "explanation": "20260717营运一部常州市灵欧商贸有限公付款信用卡手续费",
            "amount": 6033.39,
            "is_accrued_tax": False,
        },
    ]
    fuji_details = [
        {"supplier_name": "苏州宅慧影贸易有限公司", "amount": 312.63, "source_bill_no": "F-1"},
        {"supplier_name": "哈森商贸(中国)股份有限公司", "amount": 57.89, "source_bill_no": "F-2"},
        {"supplier_name": "哈森商贸(中国)股份有限公司", "amount": 132.17, "source_bill_no": "F-3"},
        {"supplier_name": "百丽鞋业(上海)有限公司", "amount": 343.49, "source_bill_no": "F-4"},
        {"supplier_name": "百丽鞋业(上海)有限公司", "amount": 383.09, "source_bill_no": "F-5"},
        {"supplier_name": "百丽鞋业(上海)有限公司", "amount": 566.36, "source_bill_no": "F-6"},
        {"supplier_name": "常州市灵欧商贸有限公司", "amount": 2360.84, "source_bill_no": "F-7"},
        {"supplier_name": "常州市灵欧商贸有限公司", "amount": 853.19, "source_bill_no": "F-8"},
        {"supplier_name": "常州市灵欧商贸有限公司", "amount": 1843.97, "source_bill_no": "F-9"},
        {"supplier_name": "常州市灵欧商贸有限公司", "amount": 975.39, "source_bill_no": "F-10"},
    ]

    result = revenue._reconcile_month_close_detail_rows(nc_details, fuji_details)

    assert result["auto_matched_count"] == 4
    assert result["auto_matched_amount"] == 7829.02
    assert result["nc_details"] == []
    assert result["fuji_details"] == []


def test_month_close_reconciliation_matches_multiple_rows_on_both_supplier_sides():
    nc_details = [
        {
            "detail_id": "NC-1",
            "voucher_id": "V-1",
            "explanation": "购物中心一部上海示例服饰有限公司办公费用上半月",
            "amount": 100.00,
            "is_accrued_tax": False,
        },
        {
            "detail_id": "NC-2",
            "voucher_id": "V-2",
            "explanation": "购物中心一部上海示例服饰有限公司办公费用下半月",
            "amount": 200.00,
            "is_accrued_tax": False,
        },
    ]
    fuji_details = [
        {
            "supplier_name": "上海示例服饰有限公司",
            "amount": 150.00,
            "source_bill_no": "F-1",
            "source_row_no": "1",
            "source_group_code": "6010101001",
        },
        {
            "supplier_name": "上海示例服饰有限公司",
            "amount": 150.00,
            "source_bill_no": "F-2",
            "source_row_no": "2",
            "source_group_code": "6010101001",
        },
    ]

    result = revenue._reconcile_month_close_detail_rows(nc_details, fuji_details)

    assert result["auto_matched_count"] == 1
    assert result["auto_matched_amount"] == 300.00
    assert result["nc_details"] == []
    assert result["fuji_details"] == []
    assert result["auto_matches"][0]["nc_detail_id"] == "NC-1,NC-2"
    assert result["auto_matches"][0]["fuji_source_bill_no"] == "F-1,F-2"


def test_month_close_display_never_shows_tax_and_hides_tax_only_rows():
    rows = [
        {"id": 1, "accrued_tax_amount": -905.66},
        {"id": 2, "accrued_tax_amount": -360.05},
        {"id": 3, "accrued_tax_amount": -20.00},
    ]
    reconciled = {
        1: {
            "nc_details": [],
            "fuji_details": [],
            "tax_details": [{"detail_id": "T-1", "amount": -905.66}],
            "tax_detail_count": 1,
            "tax_detail_amount": -905.66,
            "auto_matched_count": 2,
        },
        2: {
            "nc_details": [{"detail_id": "NC-1", "amount": 41.00}],
            "fuji_details": [{"source_bill_no": "F-1", "amount": 41.00}],
            "tax_details": [{"detail_id": "T-2", "amount": -360.05}],
            "tax_detail_count": 1,
            "tax_detail_amount": -360.05,
            "auto_matched_count": 0,
        },
        3: {
            "nc_details": [],
            "fuji_details": [],
            "tax_details": [{"detail_id": "T-3", "amount": -19.25}],
            "tax_detail_count": 1,
            "tax_detail_amount": -19.25,
            "auto_matched_count": 1,
        },
    }

    visible_rows = revenue._filter_month_close_display_rows(rows, reconciled)

    assert [row["id"] for row in visible_rows] == [2]
    assert reconciled[1]["reconciled_tax_amount"] == -905.66
    assert reconciled[1]["tax_details"] == []
    assert reconciled[2]["reconciled_tax_amount"] == -360.05
    assert reconciled[2]["tax_details"] == []
    assert reconciled[3]["tax_details"] == []
    assert reconciled[3]["tax_detail_count"] == 0
    assert reconciled[3]["tax_detail_amount"] == 0.0


def test_fuji_non_matchable_fee_rows_are_excluded_from_month_close_matching():
    list_source = inspect.getsource(revenue.revenue_month_close_pending_bindings)
    side_detail_source = inspect.getsource(revenue._load_month_close_side_details)
    page_source = (
        Path(__file__).resolve().parents[1]
        / "client"
        / "src"
        / "pages"
        / "revenue-dashboard.tsx"
    ).read_text(encoding="utf-8")

    assert revenue._is_fuji_sales_fee_codes("00-0301,00-0303,00-9999") is True
    assert revenue._is_fuji_sales_fee_codes("00-0303,20") is False
    assert revenue._is_fuji_sales_fee_codes("") is False
    assert revenue._is_fuji_non_matchable_fee_row("18", "质保金") is True
    assert revenue._is_fuji_non_matchable_fee_row("37", "代付费用") is True
    assert revenue._is_fuji_non_matchable_fee_row("38", "代扣代缴保险费") is True
    assert revenue._is_fuji_non_matchable_fee_row("61,69", "保证金") is True
    assert revenue._is_fuji_non_matchable_fee_row("00-0303,38", "代扣代缴保险费") is True
    assert revenue._is_fuji_non_matchable_fee_row("38,20", "代扣代缴保险费、信用卡费") is False
    assert revenue._is_fuji_non_matchable_fee_row("", "履约保证金") is True
    assert "_is_fuji_non_matchable_fee_row" in list_source
    assert "NOT LIKE '00%'" in side_detail_source
    assert "NOT IN ('18', '37', '38', '61', '69', '94', '95')" in side_detail_source
    assert "37代付费用、保证金、质保金、38代扣代缴保险费不参与核对" in page_source


def test_non_fuji_property_and_market_departments_are_hidden_from_month_close_differences():
    list_source = inspect.getsource(revenue.revenue_month_close_pending_bindings)
    overlay_source = inspect.getsource(revenue._revenue_month_close_overlay_ctes)

    assert revenue._is_non_fuji_month_close_department(
        {"store_code": "601", "source_department_code": "210303"}
    ) is True
    assert revenue._is_non_fuji_month_close_department(
        {"store_code": "601", "source_department_code": "2112"}
    ) is True
    assert revenue._is_non_fuji_month_close_department(
        {"store_code": "601", "source_department_code": "2113"}
    ) is True
    assert revenue._is_non_fuji_month_close_department(
        {"store_code": "601", "source_department_code": "2125"}
    ) is True
    assert revenue._is_non_fuji_month_close_department(
        {"store_code": "601", "source_department_code": "2120"}
    ) is False
    assert revenue._is_non_fuji_month_close_department(
        {"store_code": "602", "source_department_code": "220303"}
    ) is True
    assert revenue._is_non_fuji_month_close_department(
        {"store_code": "602", "source_department_code": "2212"}
    ) is True
    assert revenue._is_non_fuji_month_close_department(
        {"store_code": "602", "source_department_code": "2225"}
    ) is True
    assert revenue._is_non_fuji_month_close_department(
        {"store_code": "603", "source_department_code": "310303"}
    ) is True
    assert revenue._is_non_fuji_month_close_department(
        {"store_code": "603", "source_department_code": "3112"}
    ) is True
    assert revenue._is_non_fuji_month_close_department(
        {"store_code": "603", "source_department_code": "3125"}
    ) is False
    assert revenue._is_non_fuji_month_close_department(
        {
            "store_code": "603",
            "source_department_code": "3125",
            "source_department_name": "新世纪市场部-运营",
            "period_month": "2025-01",
        }
    ) is True
    assert revenue._is_non_fuji_month_close_department(
        {
            "store_code": "603",
            "source_department_code": "3125",
            "source_department_name": "新世纪市场部-运营",
            "period_month": "2025-12",
        }
    ) is True
    assert revenue._is_non_fuji_month_close_department(
        {
            "store_code": "603",
            "source_department_code": "3125",
            "source_department_name": "新世纪市场部-运营",
            "period_month": "2024-12",
        }
    ) is False
    assert revenue._is_non_fuji_month_close_department(
        {
            "store_code": "603",
            "source_department_code": "3125",
            "source_department_name": "新世纪市场部-运营",
            "period_month": "2026-01",
        }
    ) is True
    assert revenue._is_non_fuji_month_close_department(
        {
            "store_code": "603",
            "source_department_code": "3125",
            "source_department_name": "新世纪市场部-运营",
            "period_month": "2026-06",
        }
    ) is True
    assert revenue._is_non_fuji_month_close_department(
        {
            "store_code": "603",
            "source_department_code": "3125",
            "source_department_name": "新世纪市场部-运营",
            "period_month": "2026-07",
        }
    ) is False
    assert revenue._is_non_fuji_month_close_department(
        {"store_code": "603", "source_department_code": "3128"}
    ) is True
    assert revenue._is_non_fuji_month_close_department(
        {"store_code": "603", "source_department_code": "3130"}
    ) is False
    assert "_is_non_fuji_month_close_department" in list_source
    assert "adjustment.fee_type_code" in overlay_source
    assert "'37'" in overlay_source
    page_source = (
        Path(__file__).resolve().parents[1]
        / "client"
        / "src"
        / "pages"
        / "revenue-dashboard.tsx"
    ).read_text(encoding="utf-8")
    assert "2025年1月至2026年6月各门店物业部和营运部的NC费用按非富基收费处理，不参与匹配" in page_source
    year_end_migration_source = (
        Path(__file__).resolve().parents[1]
        / "python_app"
        / "alembic"
        / "versions"
        / "f9b0c1d2e3f4_exclude_year_end_carry_forward_from_nc_extra.py"
    ).read_text(encoding="utf-8")
    assert "account_period::INTEGER = 12" in year_end_migration_source
    assert "BTRIM(explanation) = ''期间结转''" in year_end_migration_source


def test_new_century_ninth_department_groups_override_to_tenth_department():
    side_detail_source = inspect.getsource(revenue._load_month_close_side_details)

    for group_code in (
        "6030104082",
        "6030104101",
        "6030104096",
        "6030104095",
    ):
        assert revenue._month_close_fuji_department(
            "603",
            group_code,
            "6030104",
            "新世纪九部(超市)",
        ) == ("6030116", "新世纪十部(特业)")

    assert revenue._month_close_fuji_department(
        "603",
        "6030104001",
        "6030104",
        "新世纪九部(超市)",
    ) == ("6030104", "新世纪九部(超市)")
    assert "_month_close_fuji_department" in side_detail_source
    assert '"fuji_department_code": source_department_code' in side_detail_source


def test_shopping_center_goodyear_group_links_property_rent_to_nc_department():
    side_detail_source = inspect.getsource(revenue._load_month_close_side_details)

    assert revenue._month_close_fuji_department(
        "601",
        "6012050002",
        "6010205",
        "中心物业部",
    ) == ("6010115", "中心物业服务部")
    assert revenue._month_close_adjustment_fuji_department(
        {
            "store_code": "601",
            "source_group_code": "6012050002",
            "department_code": None,
        }
    ) == "6010115"
    nc_department_sql = " ".join(
        revenue._month_close_nc_department_sql().split()
    )
    assert "TRIM(store.store_code) = '601'" in nc_department_sql
    assert "TRIM(adjustment.source_group_code) = '6012050002'" in nc_department_sql
    assert "THEN '210303'" in nc_department_sql
    assert "_month_close_adjustment_fuji_department" in side_detail_source
    assert "nc_department_sql" in side_detail_source

    reconciliation_source = (
        Path(__file__).resolve().parents[1]
        / "work"
        / "reconcile-new-century-july-2026"
        / "build_july_department_fee_reconciliation.mjs"
    ).read_text(encoding="utf-8")
    month_close_source = (
        Path(__file__).resolve().parents[1]
        / "work"
        / "month-close-new-century-july-2026"
        / "build_month_close_trial.mjs"
    ).read_text(encoding="utf-8")
    assert '["6012050002", "210303"]' in reconciliation_source
    assert "coveredExtraRows" in month_close_source
    assert "同NC部门、同6051科目、同供应商且金额一致" in month_close_source
    assert 'worksheets.add("NC补收覆盖审计")' in month_close_source


def test_revenue_dashboard_unifies_nc_departments_to_fuji_department_codes():
    alias_sql = " ".join(revenue._revenue_department_aliases_cte().split())
    dashboard_source = inspect.getsource(revenue.revenue_dashboard)
    list_source = inspect.getsource(revenue.revenue_month_close_pending_bindings)
    bind_source = inspect.getsource(revenue.bind_revenue_month_close_difference)
    page_source = (
        Path(__file__).resolve().parents[1]
        / "client"
        / "src"
        / "pages"
        / "revenue-dashboard.tsx"
    ).read_text(encoding="utf-8")

    expected_aliases = {
        ("601", "210303"): ("6010115", "中心物业服务部"),
        ("601", "2112"): ("6010108", "中心企划执行部"),
        ("601", "2125"): ("6010110", "中心营运部"),
        ("601", "2106"): ("6010117", "中心三部(女装)"),
        ("601", "2107"): ("6010118", "中心五部(运休)"),
        ("601", "2113"): ("6010109", "中心企划客服部"),
        ("601", "2116"): ("6010101", "中心一部(名品)"),
        ("601", "2117"): ("6010102", "中心四部(男装)"),
        ("601", "2118"): ("6010103", "中心六部(儿童)"),
        ("601", "2119"): ("6010104", "中心BF部(超市)"),
        ("601", "2120"): ("6010112", "中心八部(特业)"),
        ("601", "2121"): ("6010113", "中心二部(女装)"),
        ("601", "2122"): ("6010114", "中心一部(化妆)"),
        ("601", "2124"): ("6010116", "中心七部(家居)"),
        ("602", "2212"): ("6020105", "大楼市场部"),
        ("602", "2217"): ("6020101", "营运一部"),
        ("602", "2220"): ("6020110", "营运二部"),
        ("603", "310303"): ("6030205", "新世纪物业服务部"),
        ("603", "3117"): ("6030104", "新世纪九部(超市)"),
        ("603", "3125"): ("6030109", "新世纪营运部"),
        ("603", "3130"): ("6030112", "新世纪三部"),
        ("603", "3131"): ("6030117", "新世纪一部(名品)"),
        ("603", "3132"): ("6030102", "新世纪二部"),
        ("603", "3133"): ("6030103", "新世纪六部(男装)"),
        ("603", "3135"): ("6030106", "新世纪八部(儿童)"),
        ("603", "3137"): ("6030116", "新世纪十部(特业)"),
        ("603", "3150"): ("6030113", "新世纪四部"),
        ("603", "3151"): ("6030114", "新世纪五部(运休)"),
        ("603", "3152"): ("6030115", "新世纪七部(家居)"),
        ("603", "3153"): ("6030101", "新世纪一部(化妆)"),
    }
    actual_aliases = {
        (store_code, source_code): (canonical_code, canonical_name)
        for store_code, source_code, canonical_code, canonical_name
        in revenue.REVENUE_DEPARTMENT_ALIASES
    }

    assert actual_aliases == expected_aliases
    assert "revenue_department_aliases" in alias_sql
    assert "department_alias.canonical_department_code" in dashboard_source
    assert "department_alias.canonical_department_name" in dashboard_source
    assert "department_display_sort_key" in dashboard_source
    assert '"department_sort_order"' in dashboard_source
    assert "_revenue_department_aliases_cte()" in list_source
    assert "_revenue_department_aliases_cte()" in bind_source
    assert "adjustment.source_department_code" in list_source
    assert "adjustment.source_department_name" in list_source
    assert "adjustment.source_department_code" in bind_source

    assert 'department_sort_order?: number | null' in page_source
    assert "departmentSortOrder" in page_source
    assert "department_sort_order" in page_source


def test_revenue_dashboard_financial_month_uses_finance_window_and_period_filters():
    period = revenue._dashboard_financial_period(
        start_date=date(2026, 6, 29),
        end_date=date(2026, 7, 28),
        financial_year=2026,
        financial_month=7,
    )

    assert period["period_month_start"] == "2026-07"
    assert period["period_month_end"] == "2026-07"
    assert period["extra_filter"] == "extra.revenue_month BETWEEN :period_month_start AND :period_month_end"
    assert period["date_basis"] == "financial_period"


def test_revenue_dashboard_full_year_covers_twelve_financial_periods():
    period = revenue._dashboard_financial_period(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        financial_year=2026,
        financial_month=None,
    )
    overlay_sql = " ".join(revenue._revenue_month_close_overlay_ctes(period["close_filter"]).split())

    assert period["period_month_start"] == "2026-01"
    assert period["period_month_end"] == "2026-12"
    assert period["period_count"] == 12
    assert "close.period_month BETWEEN :period_month_start AND :period_month_end" in overlay_sql
    assert "close.period_month = src.financial_period_month" in overlay_sql


def test_revenue_dashboard_uses_scoped_timeout_for_full_year_query():
    endpoint_source = inspect.getsource(revenue.revenue_dashboard)

    assert revenue.REVENUE_DASHBOARD_QUERY_TIMEOUT_SECONDS == 90
    assert "SET LOCAL statement_timeout" in endpoint_source
    assert "REVENUE_DASHBOARD_QUERY_TIMEOUT_SECONDS" in endpoint_source
    assert 'if period["period_count"] > 1:' in endpoint_source


def test_revenue_map_uses_scoped_timeout_for_full_year_query():
    endpoint_source = inspect.getsource(revenue.monthly_revenue)

    assert revenue.REVENUE_MONTHLY_QUERY_TIMEOUT_SECONDS == 90
    assert "SET LOCAL statement_timeout" in endpoint_source
    assert "REVENUE_MONTHLY_QUERY_TIMEOUT_SECONDS" in endpoint_source
    assert 'if period["period_count"] > 1:' in endpoint_source


def test_revenue_map_financial_month_reuses_confirmed_month_close_overlay():
    monthly_source = inspect.getsource(revenue.monthly_revenue)
    detail_source = inspect.getsource(revenue.unit_revenue_detail)
    list_source = inspect.getsource(revenue.list_extra_receipts)

    for source in (monthly_source, detail_source, list_source):
        assert "financial_year" in source
        assert "financial_month" in source
        assert "_dashboard_financial_period" in source

    assert 'source_relation = "dashboard_source_rows"' in monthly_source
    assert 'source_relation = "dashboard_source_rows"' in detail_source
    assert "FROM {source_relation} src" in monthly_source
    assert "FROM {source_relation} src" in detail_source
    assert "_revenue_month_close_overlay_ctes" in monthly_source
    assert "_revenue_month_close_overlay_ctes" in detail_source
    assert '"month_close_extra_details"' in detail_source
    assert "adjustment.target_component = 'EXTRA'" in detail_source
    assert "adjustment.binding_status = 'BOUND'" in detail_source


def test_revenue_map_uses_financial_month_picker_and_collapses_daily_detail():
    root = Path(__file__).resolve().parents[1]
    page_source = (root / "client" / "src" / "pages" / "revenue-map.tsx").read_text(
        encoding="utf-8"
    )
    hook_source = (root / "client" / "src" / "hooks" / "useRevenue.ts").read_text(
        encoding="utf-8"
    )

    assert 'from "@/lib/financialMonth"' in page_source
    assert "findFinancialMonthContaining" in page_source
    assert "getFinancialMonthWindow" in page_source
    assert 'aria-label="收益地图财务月"' in page_source
    assert 'data-testid="revenue-map-period-filters"' in page_source
    assert "当前：{appliedPeriod.month" not in page_source
    assert '<h1 className="text-2xl font-bold tracking-tight">收益地图</h1>' not in page_source
    assert "柔和绿色为高收益" not in page_source
    assert "financialYear: appliedPeriod.year" in page_source
    assert "financialMonth: appliedPeriod.month" in page_source
    assert "setDailyCompositionOpen(false)" in page_source
    assert "<Collapsible open={dailyCompositionOpen}" in page_source
    assert "展开查看" in page_source
    assert "收起" in page_source

    assert 'q.set("financial_year", String(params.financialYear))' in hook_source
    assert 'q.set("financial_month", String(params.financialMonth))' in hook_source
