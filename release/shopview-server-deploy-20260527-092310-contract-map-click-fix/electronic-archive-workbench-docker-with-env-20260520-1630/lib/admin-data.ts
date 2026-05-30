import { unstable_noStore as noStore } from "next/cache"
import { executeOracle } from "@/lib/oracle"

export type AdminUser = {
  id: string
  username: string
  displayName: string
  mobile: string
  email: string
  wecomUserId: string
  departmentName: string
  status: "enabled" | "disabled"
  roleNames: string
  roleIds: string[]
  dataScopeNames: string
  dataScopeStoreIds: string[]
  lastLoginTime: string
}

export type AdminRole = {
  id: string
  roleCode: string
  roleName: string
  description: string
  userCount: number
  permissionNames: string
  permissionIds: string[]
}

export type AdminPermission = {
  id: string
  permissionCode: string
  permissionName: string
  permissionType: string
  routePath: string
  parentCode: string
}

export type AdminDataScope = {
  id: string
  scopeCode: string
  scopeName: string
  scopeType: string
  storeIds: string
  storeNames: string
  userCount: number
  userIds: string[]
}

function formatDate(value: Date | string | null | undefined) {
  if (!value) return "-"
  const date = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  const hour = String(date.getHours()).padStart(2, "0")
  const minute = String(date.getMinutes()).padStart(2, "0")
  return `${year}-${month}-${day} ${hour}:${minute}`
}

async function safeQuery<T extends Record<string, unknown>>(
  sql: string,
  binds: Record<string, unknown> = {}
) {
  try {
    return await executeOracle<T>(sql, binds)
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    if (message.includes("ORA-00942")) return []
    throw error
  }
}

export async function getAdminUsers(): Promise<AdminUser[]> {
  noStore()
  type Row = {
    ID: string
    USERNAME: string | null
    DISPLAY_NAME: string | null
    MOBILE: string | null
    EMAIL: string | null
    WECOM_USER_ID: string | null
    DEPARTMENT_NAME: string | null
    STATUS: string | null
    ROLE_NAMES: string | null
    ROLE_IDS: string | null
    DATA_SCOPE_NAMES: string | null
    DATA_SCOPE_STORE_IDS: string | null
    LAST_LOGIN_TIME: Date | string | null
  }
  const rows = await safeQuery<Row>(
    `select u.id,
            u.username,
            u.display_name,
            u.mobile,
            u.email,
            u.wecom_user_id,
            u.department_name,
            u.status,
            roles.role_names,
            roles.role_ids,
            scopes.data_scope_names,
            scopes.data_scope_store_ids,
            u.last_login_time
     from ETLKP.EA_USER u
     left join (
       select user_id,
              listagg(role_name, ', ') within group (order by role_name) role_names,
              listagg(role_id, ',') within group (order by role_name) role_ids
       from (
         select distinct ur.user_id, r.id role_id, r.role_name
         from ETLKP.EA_USER_ROLE ur
         join ETLKP.EA_ROLE r on r.id = ur.role_id and nvl(r.is_deleted, '0') <> '1'
         where nvl(ur.is_deleted, '0') <> '1'
       )
       group by user_id
     ) roles on roles.user_id = u.id
     left join (
       select user_id,
              listagg(scope_name, ', ') within group (order by scope_name) data_scope_names,
              listagg(store_ids, ',') within group (order by scope_name) data_scope_store_ids
       from (
         select distinct uds.user_id, ds.scope_name, ds.store_ids
         from ETLKP.EA_USER_DATA_SCOPE uds
         join ETLKP.EA_DATA_SCOPE ds on ds.id = uds.scope_id and nvl(ds.is_deleted, '0') <> '1'
         where nvl(uds.is_deleted, '0') <> '1'
       )
       group by user_id
     ) scopes on scopes.user_id = u.id
     where nvl(u.is_deleted, '0') <> '1'
     order by u.create_time desc nulls last, u.username`
  )

  return rows.map((row) => ({
    id: row.ID,
    username: row.USERNAME || "-",
    displayName: row.DISPLAY_NAME || "-",
    mobile: row.MOBILE || "-",
    email: row.EMAIL || "-",
    wecomUserId: row.WECOM_USER_ID || "-",
    departmentName: row.DEPARTMENT_NAME || "-",
    status: row.STATUS === "disabled" ? "disabled" : "enabled",
    roleNames: row.ROLE_NAMES || "-",
    roleIds: (row.ROLE_IDS || "").split(",").filter(Boolean),
    dataScopeNames: row.DATA_SCOPE_NAMES || "-",
    dataScopeStoreIds: (row.DATA_SCOPE_STORE_IDS || "")
      .split(",")
      .map((id) => id.trim())
      .filter(Boolean),
    lastLoginTime: formatDate(row.LAST_LOGIN_TIME),
  }))
}

export async function getAdminRoles(): Promise<AdminRole[]> {
  noStore()
  type Row = {
    ID: string
    ROLE_CODE: string | null
    ROLE_NAME: string | null
    DESCRIPTION: string | null
    USER_COUNT: number | null
    PERMISSION_NAMES: string | null
    PERMISSION_IDS: string | null
  }
  const rows = await safeQuery<Row>(
    `select r.id,
            r.role_code,
            r.role_name,
            r.description,
            nvl(users.user_count, 0) user_count,
            permissions.permission_names,
            permissions.permission_ids
     from ETLKP.EA_ROLE r
     left join (
       select role_id, count(distinct user_id) user_count
       from ETLKP.EA_USER_ROLE
       where nvl(is_deleted, '0') <> '1'
       group by role_id
     ) users on users.role_id = r.id
     left join (
       select role_id,
              listagg(permission_name, ', ') within group (order by permission_name) permission_names,
              listagg(permission_id, ',') within group (order by permission_name) permission_ids
       from (
         select distinct rp.role_id, p.id permission_id, p.permission_name
         from ETLKP.EA_ROLE_PERMISSION rp
         join ETLKP.EA_PERMISSION p on p.id = rp.permission_id and nvl(p.is_deleted, '0') <> '1'
         where nvl(rp.is_deleted, '0') <> '1'
       )
       group by role_id
     ) permissions on permissions.role_id = r.id
     where nvl(r.is_deleted, '0') <> '1'
     order by r.role_code`
  )

  return rows.map((row) => ({
    id: row.ID,
    roleCode: row.ROLE_CODE || "-",
    roleName: row.ROLE_NAME || "-",
    description: row.DESCRIPTION || "-",
    userCount: Number(row.USER_COUNT || 0),
    permissionNames: row.PERMISSION_NAMES || "-",
    permissionIds: (row.PERMISSION_IDS || "").split(",").filter(Boolean),
  }))
}

export async function getAdminPermissions(): Promise<AdminPermission[]> {
  noStore()
  type Row = {
    ID: string
    PERMISSION_CODE: string | null
    PERMISSION_NAME: string | null
    PERMISSION_TYPE: string | null
    ROUTE_PATH: string | null
    PARENT_CODE: string | null
  }
  const rows = await safeQuery<Row>(
    `select id, permission_code, permission_name, permission_type, route_path, parent_code
     from ETLKP.EA_PERMISSION
     where nvl(is_deleted, '0') <> '1'
     order by parent_code nulls first, sort_no, permission_code`
  )

  return rows.map((row) => ({
    id: row.ID,
    permissionCode: row.PERMISSION_CODE || "-",
    permissionName: row.PERMISSION_NAME || "-",
    permissionType: row.PERMISSION_TYPE || "-",
    routePath: row.ROUTE_PATH || "-",
    parentCode: row.PARENT_CODE || "-",
  }))
}

export async function getAdminDataScopes(): Promise<AdminDataScope[]> {
  noStore()
  type Row = {
    ID: string
    SCOPE_CODE: string | null
    SCOPE_NAME: string | null
    SCOPE_TYPE: string | null
    STORE_IDS: string | null
    STORE_NAMES: string | null
    USER_COUNT: number | null
    USER_IDS: string | null
  }
  const rows = await safeQuery<Row>(
    `select ds.id,
            ds.scope_code,
            ds.scope_name,
            ds.scope_type,
            ds.store_ids,
            ds.store_names,
            nvl(users.user_count, 0) user_count,
            users.user_ids
     from ETLKP.EA_DATA_SCOPE ds
     left join (
       select scope_id,
              count(*) user_count,
              listagg(user_id, ',') within group (order by username) user_ids
       from (
         select distinct uds.scope_id, u.id user_id, u.username
         from ETLKP.EA_USER_DATA_SCOPE uds
         join ETLKP.EA_USER u on u.id = uds.user_id and nvl(u.is_deleted, '0') <> '1'
         where nvl(uds.is_deleted, '0') <> '1'
       )
       group by scope_id
     ) users on users.scope_id = ds.id
     where nvl(ds.is_deleted, '0') <> '1'
     order by ds.scope_code`
  )

  return rows.map((row) => ({
    id: row.ID,
    scopeCode: row.SCOPE_CODE || "-",
    scopeName: row.SCOPE_NAME || "-",
    scopeType: row.SCOPE_TYPE || "-",
    storeIds: row.STORE_IDS || "-",
    storeNames: row.STORE_NAMES || "-",
    userCount: Number(row.USER_COUNT || 0),
    userIds: (row.USER_IDS || "").split(",").filter(Boolean),
  }))
}
