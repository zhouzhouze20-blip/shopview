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
  const activitySettlement = findNode(tree, "activity-settlement");
  const couponMonthly = findNode(tree, "coupon-monthly-balance");

  assert.ok(financialManagement);
  assert.equal(financialManagement.name, "财务管理");
  assert.deepEqual((financialManagement.children ?? []).map((node) => node.id), [
    "merchant-planning",
    "revenue-map",
    "joint-settlement",
    "activity-settlement",
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

test("collects descendant permission ids and reports indeterminate folder state", () => {
  const tree = buildRolePermissionTree(permissions);
  const financialManagement = findNode(tree, "financial-management");
  assert.ok(financialManagement);

  assert.deepEqual(collectPermissionTreeIds(financialManagement), [1, 2, 3, 4, 5, 6, 7, 12, 8, 9, 10, 11]);
  assert.equal(getPermissionTreeNodeState(financialManagement, new Set([1, 2, 3])), "indeterminate");
  assert.equal(getPermissionTreeNodeState(financialManagement, new Set([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])), true);
  assert.equal(getPermissionTreeNodeState(financialManagement, new Set()), false);
});

test("groups activity analysis permissions by page", () => {
  const tree = buildRolePermissionTree(permissions);
  const activityAnalysisGroup = findNode(tree, "activity-analysis-group");
  const pointsAnalysis = findNode(tree, "points-activity-analysis");

  assert.ok(activityAnalysisGroup);
  assert.deepEqual((activityAnalysisGroup.children ?? []).map((node) => node.id), [
    "activity-analysis",
    "points-activity-analysis",
  ]);

  assert.ok(pointsAnalysis);
  assert.deepEqual(
    (pointsAnalysis.permissions ?? []).map((permission) => permission.permission_code),
    ["activity_analysis.points.view"],
  );
});

test("shows OD0002 and HDYY01 as independent sales report permissions", () => {
  const tree = buildRolePermissionTree(permissions);
  const salesReports = findNode(tree, "sales-reports");
  const od0002 = findNode(tree, "od0002-sales-gross-profit");
  const hdyy01 = findNode(tree, "hdyy01-group-operation-analysis");

  assert.ok(salesReports);
  assert.deepEqual((salesReports.children ?? []).map((node) => node.id), [
    "od0002-sales-gross-profit",
    "hdyy01-group-operation-analysis",
  ]);
  assert.ok(od0002);
  assert.deepEqual(
    (od0002.permissions ?? []).map((permission) => permission.permission_code),
    ["sales.od0002.view"],
  );
  assert.ok(hdyy01);
  assert.equal(hdyy01.name, "HDYY01柜组经营分析表");
  assert.deepEqual(
    (hdyy01.permissions ?? []).map((permission) => permission.permission_code),
    ["sales.hdyy01.view"],
  );

  assert.deepEqual(collectPermissionTreeIds(od0002), [16]);
  assert.deepEqual(collectPermissionTreeIds(hdyy01), [17]);
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
