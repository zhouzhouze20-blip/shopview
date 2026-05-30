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
  "sales-dashboard": ["sales.view"],
  "activity-analysis": ["activity_analysis.view"],
  "voucher-match": ["activity_analysis.view"],
  "star-diamond-analysis": ["activity_analysis.star_diamond.view"],
  "commodity-sales-detail": ["sales.view"],
  "joint-settlement": ["settlement.view"],
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
};

export function isAdminUser(user?: AuthModuleUser | null): boolean {
  return Boolean(user?.role_codes?.some((roleCode) => ADMIN_ROLE_CODES.has(roleCode)));
}

export function canAccessModule(user: AuthModuleUser | null | undefined, moduleId: string): boolean {
  if (!user) return false;
  if (isAdminUser(user)) return true;
  const requiredPermissions = MODULE_PERMISSION_REQUIREMENTS[moduleId];
  if (!requiredPermissions?.length) return false;
  const permissionSet = new Set(user.permission_codes ?? []);
  return requiredPermissions.some((permissionCode) => permissionSet.has(permissionCode));
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
