export interface AuthModuleUser {
  role_codes?: string[];
  permission_codes?: string[];
}

interface ModuleTreeItem {
  id: string;
  subItems?: ModuleTreeItem[];
}

const ADMIN_ROLE_CODES = new Set(["super_admin", "system_admin"]);

export const MODULE_PERMISSION_REQUIREMENTS: Record<string, string[]> = {
  dashboard: ["dashboard.view"],
  stores: ["store.view"],
  counters: ["counter.view"],
  tenants: ["tenant.view"],
  brands: ["tenant.view"],
  manaframe: ["counter.view"],
  suppliers: ["supplier.view"],
  contracts: ["contract.view"],
  "contract-unit-bindings": ["contract.view"],
  "sales-dashboard": ["sales.view"],
  "self-operated-sales-import": ["sales.self_operated.import"],
  "category-performance": ["sales.category_performance.view"],
  "activity-analysis": ["activity_analysis.view"],
  "coupon-campaigns": ["activity_analysis.campaign.view"],
  "coupon-live": ["activity_analysis.campaign.view"],
  "new-century-campaign-analysis": ["activity_analysis.new_century_campaign.view"],
  "birthday-coupon-analysis": ["activity_analysis.birthday_coupon.view"],
  "points-activity-analysis": ["activity_analysis.points.view"],
  "voucher-match": ["activity_settlement.voucher_match.view"],
  "confirmed-revenue-daily": ["activity_settlement.confirmed_revenue.view"],
  "coupon-monthly-balance": ["activity_settlement.coupon_monthly.view"],
  "star-diamond-analysis": ["activity_analysis.star_diamond.view"],
  "brand-member-analysis": ["sales.brand_member_analysis.view"],
  "commodity-sales-detail": ["sales.commodity_detail.view"],
  "settled-gross-profit-ranking": ["sales.settled_gross_profit.view"],
  "od0002-sales-gross-profit": ["sales.od0002.view"],
  "daily-sales-followup": ["sales.od0001.view"],
  "od0003-center-sales-followup": ["sales.od0003.view"],
  "od0004-monthly-followup": ["sales.od0004.view"],
  "od0005-micro-mall-brand-sales": ["sales.od0005.view"],
  "new-century-payment-report": ["sales.new_century_payments.view"],
  "hy0001-key-brand-member": ["sales.hy0001.view"],
  "non-rental-monthly-revenue": ["sales.non_rental_monthly_revenue.view"],
  "store-other-business-income": ["sales.store_other_business_income.view"],
  "hdyy01-group-operation-analysis": ["sales.hdyy01.view"],
  "inventory-detail": ["sales.inventory.view"],
  "inventory-turnover": ["sales.inventory_turnover.view"],
  "historical-inventory-detail": ["sales.inventory_history.view"],
  "inventory-movement-detail": ["sales.inventory_movement.view"],
  "merchant-planning": ["merchant_planning.view"],
  "revenue-map": ["revenue.view"],
  "revenue-dashboard": ["revenue.dashboard.view"],
  "joint-renewal-revenue": ["revenue.view"],
  "joint-settlement": ["settlement.view"],
  "cosmetics-payment-matching": ["settlement.cosmetics_matching.view"],
  "joint-payment-confirmation": ["settlement.joint_payment_confirmation.view"],
  "rental-receivables": ["settlement.view"],
  decorations: ["decoration.view"],
  "decorations-todos": ["decoration.todo.view"],
  floors: ["floor.view"],
  "base-maps": ["base_map.view"],
  "unit-map-versions": ["unit_map_version.view"],
  "business-units": ["business_unit.view"],
  "floor-area-report": ["floor.view"],
  "user-role-scope": ["system.user.manage", "system.role.manage", "system.data_policy.manage"],
  users: ["system.user.manage"],
  roles: ["system.role.manage"],
  departments: ["system.data_policy.manage"],
  "contract-permissions": ["system.data_policy.manage"],
  "wecom-rules": ["system.data_policy.manage"],
  "audit-logs": ["system.audit_log.view"],
  "mobile-sales-dashboard": ["mobile.sales.view"],
  "mobile-contracts": ["mobile.contracts.view"],
  "mobile-inventory": ["mobile.inventory.view"],
  "mobile-revenue-dashboard": ["mobile.revenue_dashboard.view"],
  "mobile-rental-receivables": ["mobile.rental_receivables.view"],
  "mobile-coupon-followups": ["mobile.coupon_followup.view"],
  "mobile-supplier-payments": ["mobile.supplier_payments.view"],
};

// Mobile entry permissions are an additional channel gate. The matching
// business permission remains required because the underlying APIs enforce it.
export const MODULE_PERMISSION_DEPENDENCIES: Record<string, string[]> = {
  "mobile-sales-dashboard": ["sales.view"],
  "mobile-contracts": ["contract.view"],
  "mobile-inventory": ["sales.inventory.view"],
  "mobile-revenue-dashboard": ["revenue.dashboard.view"],
  "mobile-rental-receivables": ["settlement.view"],
};

export const DEFAULT_MOBILE_ROLE_PERMISSION_CODES = [
  "mobile.sales.view",
  "mobile.contracts.view",
  "mobile.inventory.view",
] as const;

export function getDefaultMobileRolePermissionIds(
  permissions: Array<{ id: number; permission_code: string }>,
): number[] {
  const defaultCodes = new Set<string>(DEFAULT_MOBILE_ROLE_PERMISSION_CODES);
  return permissions
    .filter((permission) => defaultCodes.has(permission.permission_code))
    .map((permission) => permission.id)
    .sort((a, b) => a - b);
}

export function isAdminUser(user?: AuthModuleUser | null): boolean {
  return Boolean(user?.role_codes?.some((roleCode) => ADMIN_ROLE_CODES.has(roleCode)));
}

export function canAccessModule(user: AuthModuleUser | null | undefined, moduleId: string): boolean {
  if (!user) return false;
  if (isAdminUser(user)) return true;
  const requiredPermissions = MODULE_PERMISSION_REQUIREMENTS[moduleId];
  if (!requiredPermissions?.length) return false;
  const permissionSet = new Set(user.permission_codes ?? []);
  if (!requiredPermissions.some((permissionCode) => permissionSet.has(permissionCode))) return false;
  const dependencies = MODULE_PERMISSION_DEPENDENCIES[moduleId] ?? [];
  return dependencies.every((permissionCode) => permissionSet.has(permissionCode));
}

export function filterAccessibleModuleTree<T extends ModuleTreeItem>(items: T[], user: AuthModuleUser | null | undefined): T[] {
  const result: T[] = [];
  for (const item of items) {
    const subItems = item.subItems ? filterAccessibleModuleTree(item.subItems, user) : undefined;
    if (subItems?.length) {
      result.push({ ...item, subItems } as T);
      continue;
    }
    if (canAccessModule(user, item.id)) {
      result.push({ ...item, subItems } as T);
    }
  }
  return result;
}

export function findFirstAccessibleModule<T extends ModuleTreeItem>(items: T[], user: AuthModuleUser | null | undefined): string | null {
  for (const item of items) {
    if (item.subItems?.length) {
      const childModuleId = findFirstAccessibleModule(item.subItems, user);
      if (childModuleId) return childModuleId;
    }
    if (canAccessModule(user, item.id)) return item.id;
  }
  return null;
}
