export interface RolePermissionItem {
  id: number;
  permission_code: string;
  permission_name: string;
  module_code: string;
  action_code: string;
}

export interface RolePermissionTreeNode {
  id: string;
  name: string;
  permissions?: RolePermissionItem[];
  children?: RolePermissionTreeNode[];
}

interface RolePermissionTreeConfig {
  id: string;
  name: string;
  moduleCodes?: string[];
  permissionCodes?: string[];
  permissionPrefixes?: string[];
  children?: RolePermissionTreeConfig[];
}

const rolePermissionTreeConfig: RolePermissionTreeConfig[] = [
  {
    id: "dashboard",
    name: "经营概览",
    moduleCodes: ["dashboard"],
  },
  {
    id: "decoration-management",
    name: "装修管理",
    children: [
      { id: "decorations", name: "装修项目", moduleCodes: ["decoration"], permissionPrefixes: ["decoration."] },
      { id: "decorations-todos", name: "装修待办", permissionPrefixes: ["decoration.todo."] },
    ],
  },
  {
    id: "tenant-management",
    name: "品牌/商户管理",
    children: [
      { id: "manaframe", name: "柜位定义", moduleCodes: ["counter", "counter_group"] },
      { id: "suppliers", name: "供应商管理", moduleCodes: ["supplier"] },
      { id: "tenants", name: "商户管理", moduleCodes: ["tenant"] },
    ],
  },
  {
    id: "contract-management",
    name: "合同管理",
    children: [
      { id: "contracts", name: "合同台账", moduleCodes: ["contract"] },
      { id: "contract-unit-bindings", name: "合同柜位绑定", permissionCodes: ["contract.view", "contract.edit"] },
    ],
  },
  {
    id: "sales-management",
    name: "销售管理",
    children: [
      { id: "sales-dashboard", name: "销售看板", moduleCodes: ["sales"] },
      {
        id: "activity-analysis-group",
        name: "活动分析",
        children: [
          { id: "activity-analysis", name: "通用活动分析", permissionCodes: ["activity_analysis.view"] },
          { id: "points-activity-analysis", name: "积分活动核对", permissionPrefixes: ["activity_analysis.points."] },
          { id: "star-diamond-analysis", name: "中心星钻会员", permissionPrefixes: ["activity_analysis.star_diamond."] },
        ],
      },
      { id: "sales-reports", name: "报表", children: [{ id: "commodity-sales-detail", name: "商品销售明细", moduleCodes: ["sales"] }] },
    ],
  },
  {
    id: "financial-management",
    name: "财务管理",
    children: [
      { id: "merchant-planning", name: "招商规划", moduleCodes: ["merchant_planning"] },
      { id: "revenue-map", name: "收益地图", moduleCodes: ["revenue"] },
      { id: "joint-settlement", name: "联营结算单管理", moduleCodes: ["settlement"] },
      {
        id: "activity-settlement",
        name: "活动结算",
        children: [
          {
            id: "voucher-match",
            name: "凭证匹配",
            permissionCodes: [
              "activity_settlement.voucher_match.view",
              "activity_settlement.voucher_match.confirm",
              "activity_settlement.voucher_match.reject",
            ],
          },
          {
            id: "confirmed-revenue-daily",
            name: "确认收入占比",
            permissionCodes: ["activity_settlement.confirmed_revenue.view"],
          },
          {
            id: "coupon-monthly-balance",
            name: "卡券月结",
            permissionCodes: [
              "activity_settlement.coupon_monthly.view",
              "activity_settlement.coupon_monthly.rebuild",
              "activity_settlement.coupon_monthly.confirm",
              "activity_settlement.coupon_monthly.carryover_create",
            ],
          },
        ],
      },
    ],
  },
  {
    id: "system-management",
    name: "系统管理",
    children: [
      {
        id: "floor-base-definitions",
        name: "楼层基础定义",
        children: [
          { id: "floors", name: "楼层定义", moduleCodes: ["floor"] },
          { id: "base-maps", name: "底图管理", moduleCodes: ["base_map"] },
          { id: "unit-map-versions", name: "柜位图版本", moduleCodes: ["unit_map_version"] },
          { id: "business-units", name: "经营单元设置", moduleCodes: ["business_unit"] },
        ],
      },
      {
        id: "user-role-scope",
        name: "用户角色及范围定义",
        permissionCodes: ["system.user.manage", "system.role.manage", "system.permission.manage", "system.data_policy.manage"],
      },
      { id: "wecom-rules", name: "企微授权规则", permissionCodes: ["system.data_policy.manage"] },
      { id: "audit-logs", name: "日志查询", permissionCodes: ["system.audit_log.view"] },
    ],
  },
];

function permissionsForConfig(
  config: RolePermissionTreeConfig,
  permissions: RolePermissionItem[],
  assignedPermissionIds: Set<number>,
): RolePermissionItem[] {
  const permissionCodes = new Set(config.permissionCodes ?? []);
  const moduleCodes = new Set(config.moduleCodes ?? []);
  const prefixes = config.permissionPrefixes ?? [];
  const matched = permissions.filter((permission) => {
    if (assignedPermissionIds.has(permission.id)) return false;
    return (
      permissionCodes.has(permission.permission_code) ||
      moduleCodes.has(permission.module_code) ||
      prefixes.some((prefix) => permission.permission_code.startsWith(prefix))
    );
  });
  matched.forEach((permission) => assignedPermissionIds.add(permission.id));
  return matched;
}

function buildNode(
  config: RolePermissionTreeConfig,
  permissions: RolePermissionItem[],
  assignedPermissionIds: Set<number>,
): RolePermissionTreeNode | null {
  const children = (config.children ?? [])
    .map((child) => buildNode(child, permissions, assignedPermissionIds))
    .filter((child): child is RolePermissionTreeNode => Boolean(child));
  const nodePermissions = permissionsForConfig(config, permissions, assignedPermissionIds);

  if (!children.length && !nodePermissions.length) return null;
  return {
    id: config.id,
    name: config.name,
    permissions: nodePermissions,
    children,
  };
}

export function buildRolePermissionTree(permissions: RolePermissionItem[]): RolePermissionTreeNode[] {
  const assignedPermissionIds = new Set<number>();
  const nodes = rolePermissionTreeConfig
    .map((config) => buildNode(config, permissions, assignedPermissionIds))
    .filter((node): node is RolePermissionTreeNode => Boolean(node));

  const unassignedPermissions = permissions.filter((permission) => !assignedPermissionIds.has(permission.id));
  if (unassignedPermissions.length) {
    nodes.push({
      id: "other-permissions",
      name: "其他权限",
      permissions: unassignedPermissions,
      children: [],
    });
  }

  return nodes;
}

export function collectPermissionTreeIds(node: RolePermissionTreeNode): number[] {
  const ownIds = (node.permissions ?? []).map((permission) => permission.id);
  const childIds = (node.children ?? []).flatMap((child) => collectPermissionTreeIds(child));
  return [...ownIds, ...childIds];
}

export function getPermissionTreeNodeState(
  node: RolePermissionTreeNode,
  selectedPermissionIds: Set<number>,
): boolean | "indeterminate" {
  const permissionIds = collectPermissionTreeIds(node);
  if (!permissionIds.length) return false;
  const selectedCount = permissionIds.filter((permissionId) => selectedPermissionIds.has(permissionId)).length;
  if (selectedCount === 0) return false;
  if (selectedCount === permissionIds.length) return true;
  return "indeterminate";
}
