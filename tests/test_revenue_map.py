import inspect
import sys
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
    assert "enabled: selectedStoreIdValue != null" in page_source
    assert "row.floor_id === floorId" in page_source
    assert "monthlyQuery.refetch()" not in page_source


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
    assert "6051 电表、物业、营运收费由后台自动同步" in page_source
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
    assert "TRIM(COALESCE(fee.source_doc_no, ''))" in sql
    assert "TRIM(COALESCE(fee.source_row_key, ''))" in sql
    assert f"NOT ({loss_condition}) OR fee.exact_duplicate_rank = 1" in sql
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
    assert "FROM live_sales mapped" in unmatched_sql
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
    assert "SUM(fee.tax_excluded_amount) OVER ()" in endpoint_source

    assert 'openDetail(row, "gross-profit")' in page_source
    assert 'openDetail(row, "fees")' in page_source
    assert "每日毛利明细" in page_source
    assert "收益日期" in page_source
    assert "付款单号" in page_source
    assert "结算单号" in page_source
    assert "费用项目" in page_source
    assert "不含税金额" in page_source
    assert "付款日期" in page_source
    assert "收费按付款日期统计，仅包含已关联付款记录的数据" in page_source


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
    assert "_dashboard_row_allowed(scope, scope_subject)" in endpoint_source
    assert "extra.source_department_code" in live_source_sql
    assert "extra.source_department_name" in live_source_sql
    assert "src.source_department_code" in dashboard_source
    assert "src.source_department_name" in dashboard_source
    assert 'require_permission(db, current_user, "revenue.dashboard.view")' in export_endpoint_source
    assert "_nc_6051_extra_detail_ctes()" in export_endpoint_source
    assert "_dashboard_row_allowed(" in export_endpoint_source
    assert '"source_detail_key"' in export_endpoint_source
    assert 'openDetail(row, "extras")' in page_source
    assert "/api/revenue-map/dashboard/extra-details" in page_source
    assert "其他收益科目及摘要明细" in page_source
    assert "科目明细" in page_source
    assert "摘要明细" in page_source
    assert "NC凭证" in page_source
    assert 'row.group_code || `unit:${row.unit_codes || "未绑定"}:name:${row.group_name}`' in page_source


def test_revenue_dashboard_exports_group_grain_with_untaxed_fee_columns():
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
    assert "去税收费汇总" in export_source
    assert "其他收益" in export_source
    assert "feeColumns.map" in export_source
    assert "收费分类校验差额" in export_source
    assert "其他收益科目汇总" in export_source
    assert "其他收益摘要明细" in export_source
    assert "科目编码" in export_source
    assert "NC凭证" in export_source
    assert "来源明细键" in export_source
    assert "/api/revenue-map/dashboard/extra-export-details" in page_source
    assert "正在整理科目" in page_source
    assert "销售毛利按财务日期；收费按付款日期；其他收益按确认收益日期" in export_source
    assert "未关联结算付款日期或租赁付款日期的收费不进入本次导出" in export_source
