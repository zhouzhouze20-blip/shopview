export type SystemConfigTab =
  | "users"
  | "roles"
  | "departments"
  | "contract-permissions"
  | "wecom-rules"
  | "policies"
  | "audit-logs";

export function getSystemConfigQueryScope(tab: SystemConfigTab) {
  return {
    stores: tab === "users" || tab === "departments",
    permissions: tab === "roles",
    posts: tab === "users",
    roles: tab === "users" || tab === "roles" || tab === "wecom-rules",
    departments: tab === "users" || tab === "departments",
    users: tab === "users" || tab === "departments",
    policies: tab === "policies",
    wecomRules: tab === "wecom-rules",
    meta: tab === "policies",
    contractPermissionOptions: tab === "contract-permissions",
    contractPermissions: tab === "contract-permissions",
  };
}
