import assert from "node:assert/strict";
import test from "node:test";
import {
  buildRolePermissionTree,
  collectPermissionTreeIds,
  getPermissionTreeNodeState,
} from "./role-permission-tree.ts";

const permissions = [
  { id: 1, permission_code: "merchant_planning.view", permission_name: "查看招商规划", module_code: "merchant_planning", action_code: "view" },
  { id: 2, permission_code: "merchant_planning.manage", permission_name: "管理招商规划", module_code: "merchant_planning", action_code: "manage" },
  { id: 3, permission_code: "revenue.view", permission_name: "查看收益", module_code: "revenue", action_code: "view" },
  { id: 4, permission_code: "settlement.view", permission_name: "查看结算单", module_code: "settlement", action_code: "view" },
  { id: 5, permission_code: "activity_settlement.voucher_match.view", permission_name: "查看凭证匹配", module_code: "activity_settlement", action_code: "voucher_match_view" },
  { id: 6, permission_code: "activity_settlement.voucher_match.confirm", permission_name: "确认凭证匹配", module_code: "activity_settlement", action_code: "voucher_match_confirm" },
  { id: 7, permission_code: "activity_settlement.voucher_match.reject", permission_name: "驳回凭证匹配", module_code: "activity_settlement", action_code: "voucher_match_reject" },
  { id: 8, permission_code: "activity_settlement.coupon_monthly.view", permission_name: "查看卡券月结", module_code: "activity_settlement", action_code: "coupon_monthly_view" },
  { id: 9, permission_code: "activity_settlement.coupon_monthly.rebuild", permission_name: "重建卡券月结", module_code: "activity_settlement", action_code: "coupon_monthly_rebuild" },
  { id: 10, permission_code: "activity_settlement.coupon_monthly.confirm", permission_name: "确认卡券月结", module_code: "activity_settlement", action_code: "coupon_monthly_confirm" },
  { id: 11, permission_code: "activity_settlement.coupon_monthly.carryover_create", permission_name: "新增NC结转", module_code: "activity_settlement", action_code: "coupon_monthly_carryover_create" },
  { id: 12, permission_code: "activity_settlement.confirmed_revenue.view", permission_name: "查看确认收入占比", module_code: "activity_settlement", action_code: "confirmed_revenue_view" },
  { id: 13, permission_code: "activity_analysis.view", permission_name: "查看活动分析", module_code: "activity_analysis", action_code: "view" },
  { id: 14, permission_code: "activity_analysis.points.view", permission_name: "查看积分活动核对", module_code: "activity_analysis", action_code: "points_view" },
  { id: 15, permission_code: "sales.view", permission_name: "查看销售", module_code: "sales", action_code: "view" },
  { id: 16, permission_code: "sales.od0002.view", permission_name: "查看OD0002门店销售毛利汇总表", module_code: "sales", action_code: "od0002_view" },
  { id: 17, permission_code: "sales.hdyy01.view", permission_name: "查看HDYY01柜组经营分析表", module_code: "sales", action_code: "hdyy01_view" },
  { id: 18, permission_code: "sales.brand_member_analysis.view", permission_name: "查看品牌会员分析", module_code: "sales", action_code: "brand_member_analysis_view" },
  { id: 19, permission_code: "sales.category_performance.view", permission_name: "查看品类主管绩效", module_code: "sales", action_code: "category_performance_view" },
  { id: 20, permission_code: "sales.category_performance.manage", permission_name: "维护品类主管绩效", module_code: "sales", action_code: "category_performance_manage" },
  { id: 21, permission_code: "revenue.dashboard.view", permission_name: "查看收益看板", module_code: "revenue", action_code: "dashboard_view" },
  { id: 22, permission_code: "sales.commodity_detail.view", permission_name: "查看商品销售明细", module_code: "sales", action_code: "commodity_detail_view" },
  { id: 23, permission_code: "sales.settled_gross_profit.view", permission_name: "查看结算后销售毛利排行表", module_code: "sales", action_code: "settled_gross_profit_view" },
  { id: 24, permission_code: "sales.od0001.view", permission_name: "查看OD0001销售逐日跟进表", module_code: "sales", action_code: "od0001_view" },
  { id: 25, permission_code: "sales.od0003.view", permission_name: "查看OD0003中心销售跟进表", module_code: "sales", action_code: "od0003_view" },
  { id: 26, permission_code: "mobile.sales.view", permission_name: "查看手机端销售看板", module_code: "mobile", action_code: "sales_view" },
  { id: 27, permission_code: "mobile.contracts.view", permission_name: "查看手机端合同台账", module_code: "mobile", action_code: "contracts_view" },
  { id: 28, permission_code: "mobile.inventory.view", permission_name: "查看手机端实时库存查询", module_code: "mobile", action_code: "inventory_view" },
  { id: 29, permission_code: "mobile.revenue_dashboard.view", permission_name: "查看手机端收益看板", module_code: "mobile", action_code: "revenue_dashboard_view" },
  { id: 30, permission_code: "sales.od0004.view", permission_name: "查看OD0004销售逐月跟进表", module_code: "sales", action_code: "od0004_view" },
  { id: 31, permission_code: "sales.non_rental_monthly_revenue.view", permission_name: "查看非租赁品牌月度收益表", module_code: "sales", action_code: "non_rental_monthly_revenue_view" },
  { id: 32, permission_code: "sales.hy0001.view", permission_name: "查看HY0001重点品牌会员消费情况", module_code: "sales", action_code: "hy0001_view" },
  { id: 33, permission_code: "sales.od0005.view", permission_name: "查看OD0005微商城品牌销售统计", module_code: "sales", action_code: "od0005_view" },
  { id: 34, permission_code: "activity_analysis.birthday_coupon.view", permission_name: "查看中心L/C券分析", module_code: "activity_analysis", action_code: "birthday_coupon_view" },
  { id: 35, permission_code: "activity_analysis.star_diamond.view", permission_name: "查看中心星钻会员", module_code: "activity_analysis", action_code: "star_diamond_view" },
  { id: 36, permission_code: "settlement.joint_payment_confirmation.view", permission_name: "查看联营付款单确认", module_code: "settlement", action_code: "joint_payment_confirmation_view" },
  { id: 37, permission_code: "mobile.rental_receivables.view", permission_name: "查看手机端租赁应收未收", module_code: "mobile", action_code: "rental_receivables_view" },
  { id: 38, permission_code: "mobile.coupon_followup.view", permission_name: "查看手机端C券会员跟进", module_code: "mobile", action_code: "coupon_followup_view" },
  { id: 39, permission_code: "mobile.supplier_payments.view", permission_name: "查看手机端供应商付款单", module_code: "mobile", action_code: "supplier_payments_view" },
];

function findNode(nodes, id) {
  for (const node of nodes) {
    if (node.id === id) return node;
    const child = findNode(node.children ?? [], id);
    if (child) return child;
  }
  return null;
}

test("builds financial management as folder, submodule, action permission hierarchy", () => {
  const tree = buildRolePermissionTree(permissions);
  const financialManagement = findNode(tree, "financial-management");
  const revenueManagement = findNode(tree, "revenue-management");
  const activitySettlement = findNode(tree, "activity-settlement");
  const couponMonthly = findNode(tree, "coupon-monthly-balance");

  assert.ok(financialManagement);
  assert.equal(financialManagement.name, "财务管理");
  assert.deepEqual((financialManagement.children ?? []).map((node) => node.id), [
    "merchant-planning",
    "revenue-management",
    "joint-settlement",
    "joint-payment-confirmation",
    "activity-settlement",
  ]);
  assert.ok(revenueManagement);
  assert.deepEqual((revenueManagement.children ?? []).map((node) => node.id), [
    "revenue-map",
    "revenue-dashboard",
  ]);

  assert.ok(activitySettlement);
  assert.deepEqual((activitySettlement.children ?? []).map((node) => node.id), [
    "voucher-match",
    "confirmed-revenue-daily",
    "coupon-monthly-balance",
  ]);

  assert.ok(couponMonthly);
  assert.deepEqual(
    (couponMonthly.permissions ?? []).map((permission) => permission.permission_code),
    [
      "activity_settlement.coupon_monthly.view",
      "activity_settlement.coupon_monthly.rebuild",
      "activity_settlement.coupon_monthly.confirm",
      "activity_settlement.coupon_monthly.carryover_create",
    ],
  );
});

test("groups mobile modules as independent role permissions", () => {
  const tree = buildRolePermissionTree(permissions);
  const mobileWorkbench = findNode(tree, "mobile-workbench");
  const mobileSales = findNode(tree, "mobile-sales-dashboard");
  const mobileContracts = findNode(tree, "mobile-contracts");
  const mobileInventory = findNode(tree, "mobile-inventory");
  const mobileRevenue = findNode(tree, "mobile-revenue-dashboard");
  const mobileSupplierPayments = findNode(tree, "mobile-supplier-payments");

  assert.ok(mobileWorkbench);
  assert.equal(mobileWorkbench.name, "手机端");
  assert.deepEqual((mobileWorkbench.children ?? []).map((node) => node.id), [
    "mobile-sales-dashboard",
    "mobile-contracts",
    "mobile-inventory",
    "mobile-revenue-dashboard",
    "mobile-rental-receivables",
    "mobile-coupon-followups",
    "mobile-supplier-payments",
  ]);
  assert.deepEqual(collectPermissionTreeIds(mobileWorkbench), [26, 27, 28, 29, 37, 38, 39]);
  assert.deepEqual((mobileSales.permissions ?? []).map((permission) => permission.permission_code), ["mobile.sales.view"]);
  assert.deepEqual((mobileContracts.permissions ?? []).map((permission) => permission.permission_code), ["mobile.contracts.view"]);
  assert.deepEqual((mobileInventory.permissions ?? []).map((permission) => permission.permission_code), ["mobile.inventory.view"]);
  assert.deepEqual((mobileRevenue.permissions ?? []).map((permission) => permission.permission_code), ["mobile.revenue_dashboard.view"]);
  assert.deepEqual((mobileSupplierPayments.permissions ?? []).map((permission) => permission.permission_code), ["mobile.supplier_payments.view"]);
});

test("collects descendant permission ids and reports indeterminate folder state", () => {
  const tree = buildRolePermissionTree(permissions);
  const financialManagement = findNode(tree, "financial-management");
  assert.ok(financialManagement);

  assert.deepEqual(collectPermissionTreeIds(financialManagement), [1, 2, 3, 21, 4, 36, 5, 6, 7, 12, 8, 9, 10, 11]);
  assert.equal(getPermissionTreeNodeState(financialManagement, new Set([1, 2, 3])), "indeterminate");
  assert.equal(getPermissionTreeNodeState(financialManagement, new Set([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 21, 36])), true);
  assert.equal(getPermissionTreeNodeState(financialManagement, new Set()), false);
});

test("groups activity analysis permissions by page", () => {
  const tree = buildRolePermissionTree(permissions);
  const activityAnalysisGroup = findNode(tree, "activity-analysis-group");
  const birthdayCoupon = findNode(tree, "birthday-coupon-analysis");
  const pointsAnalysis = findNode(tree, "points-activity-analysis");

  assert.ok(activityAnalysisGroup);
  assert.deepEqual((activityAnalysisGroup.children ?? []).map((node) => node.id), [
    "activity-analysis",
    "birthday-coupon-analysis",
    "points-activity-analysis",
    "star-diamond-analysis",
  ]);

  assert.ok(birthdayCoupon);
  assert.deepEqual(
    (birthdayCoupon.permissions ?? []).map((permission) => permission.permission_code),
    ["activity_analysis.birthday_coupon.view"],
  );

  assert.ok(pointsAnalysis);
  assert.deepEqual(
    (pointsAnalysis.permissions ?? []).map((permission) => permission.permission_code),
    ["activity_analysis.points.view"],
  );
});

test("shows every sales report as an independent permission", () => {
  const tree = buildRolePermissionTree(permissions);
  const salesReports = findNode(tree, "sales-reports");
  const commodityDetail = findNode(tree, "commodity-sales-detail");
  const settledGrossProfit = findNode(tree, "settled-gross-profit-ranking");
  const od0002 = findNode(tree, "od0002-sales-gross-profit");
  const dailyFollowup = findNode(tree, "daily-sales-followup");
  const od0003 = findNode(tree, "od0003-center-sales-followup");
  const od0004 = findNode(tree, "od0004-monthly-followup");
  const od0005 = findNode(tree, "od0005-micro-mall-brand-sales");
  const hy0001 = findNode(tree, "hy0001-key-brand-member");
  const nonRentalMonthlyRevenue = findNode(tree, "non-rental-monthly-revenue");
  const hdyy01 = findNode(tree, "hdyy01-group-operation-analysis");

  assert.ok(salesReports);
  assert.deepEqual((salesReports.children ?? []).map((node) => node.id), [
    "commodity-sales-detail",
    "settled-gross-profit-ranking",
    "daily-sales-followup",
    "od0002-sales-gross-profit",
    "od0003-center-sales-followup",
    "od0004-monthly-followup",
    "od0005-micro-mall-brand-sales",
    "hy0001-key-brand-member",
    "non-rental-monthly-revenue",
    "hdyy01-group-operation-analysis",
  ]);
  assert.deepEqual(
    (commodityDetail.permissions ?? []).map((permission) => permission.permission_code),
    ["sales.commodity_detail.view"],
  );
  assert.deepEqual(
    (settledGrossProfit.permissions ?? []).map((permission) => permission.permission_code),
    ["sales.settled_gross_profit.view"],
  );
  assert.ok(od0002);
  assert.deepEqual(
    (od0002.permissions ?? []).map((permission) => permission.permission_code),
    ["sales.od0002.view"],
  );
  assert.deepEqual(
    (dailyFollowup.permissions ?? []).map((permission) => permission.permission_code),
    ["sales.od0001.view"],
  );
  assert.deepEqual(
    (od0003.permissions ?? []).map((permission) => permission.permission_code),
    ["sales.od0003.view"],
  );
  assert.deepEqual(
    (od0004.permissions ?? []).map((permission) => permission.permission_code),
    ["sales.od0004.view"],
  );
  assert.deepEqual(
    (od0005.permissions ?? []).map((permission) => permission.permission_code),
    ["sales.od0005.view"],
  );
  assert.deepEqual(
    (hy0001.permissions ?? []).map((permission) => permission.permission_code),
    ["sales.hy0001.view"],
  );
  assert.deepEqual(
    (nonRentalMonthlyRevenue.permissions ?? []).map((permission) => permission.permission_code),
    ["sales.non_rental_monthly_revenue.view"],
  );
  assert.equal(nonRentalMonthlyRevenue.name, "非租赁品牌月度收益表");
  assert.ok(hdyy01);
  assert.equal(hdyy01.name, "HDYY01柜组经营分析表");
  assert.deepEqual(
    (hdyy01.permissions ?? []).map((permission) => permission.permission_code),
    ["sales.hdyy01.view"],
  );

  assert.deepEqual(collectPermissionTreeIds(od0002), [16]);
  assert.deepEqual(collectPermissionTreeIds(hdyy01), [17]);
  assert.deepEqual(collectPermissionTreeIds(commodityDetail), [22]);
  assert.deepEqual(collectPermissionTreeIds(settledGrossProfit), [23]);
  assert.deepEqual(collectPermissionTreeIds(dailyFollowup), [24]);
  assert.deepEqual(collectPermissionTreeIds(od0003), [25]);
  assert.deepEqual(collectPermissionTreeIds(od0004), [30]);
  assert.deepEqual(collectPermissionTreeIds(od0005), [33]);
  assert.deepEqual(collectPermissionTreeIds(hy0001), [32]);
  assert.deepEqual(collectPermissionTreeIds(nonRentalMonthlyRevenue), [31]);
  assert.equal(getPermissionTreeNodeState(od0002, new Set([16])), true);
  assert.equal(getPermissionTreeNodeState(hdyy01, new Set([16])), false);
  assert.equal(getPermissionTreeNodeState(od0002, new Set([17])), false);
  assert.equal(getPermissionTreeNodeState(hdyy01, new Set([17])), true);
  assert.equal(getPermissionTreeNodeState(salesReports, new Set([16])), "indeterminate");
  assert.equal(getPermissionTreeNodeState(salesReports, new Set([17])), "indeterminate");
});

test("shows brand member analysis as an independent member analysis permission", () => {
  const tree = buildRolePermissionTree(permissions);
  const memberAnalysis = findNode(tree, "member-analysis-group");
  const brandMemberAnalysis = findNode(tree, "brand-member-analysis");

  assert.ok(memberAnalysis);
  assert.equal(memberAnalysis.name, "会员经营分析");
  assert.deepEqual((memberAnalysis.children ?? []).map((node) => node.id), ["brand-member-analysis"]);
  assert.ok(brandMemberAnalysis);
  assert.deepEqual(
    (brandMemberAnalysis.permissions ?? []).map((permission) => permission.permission_code),
    ["sales.brand_member_analysis.view"],
  );
  assert.deepEqual(collectPermissionTreeIds(brandMemberAnalysis), [18]);
});

test("separates category performance view and maintenance permissions", () => {
  const tree = buildRolePermissionTree(permissions);
  const categoryPerformance = findNode(tree, "category-performance");

  assert.ok(categoryPerformance);
  assert.deepEqual(
    (categoryPerformance.permissions ?? []).map((permission) => permission.permission_code),
    ["sales.category_performance.view", "sales.category_performance.manage"],
  );
  assert.deepEqual(collectPermissionTreeIds(categoryPerformance), [19, 20]);
  assert.equal(getPermissionTreeNodeState(categoryPerformance, new Set([19])), "indeterminate");
});
