"use server"

import { randomUUID } from "crypto"
import { revalidatePath } from "next/cache"
import { createPasswordHash, ensureUserPasswordTable } from "@/lib/auth"
import { executeOracleStatement, executeOracleTransaction } from "@/lib/oracle"
import { getWecomUsers } from "@/lib/wecom"

const invoicePaths = [
  "/",
  "/invoices",
  "/invoices/matched",
  "/invoices/confirmed-report",
  "/invoices/amount-mismatch",
  "/invoices/unmatched",
  "/documents",
  "/documents/erp",
]

function asIds(value: FormDataEntryValue | null) {
  return String(value ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
}

function revalidateInvoiceViews() {
  for (const path of invoicePaths) {
    revalidatePath(path)
  }
}

const defaultPermissionDefinitions = [
  ["dashboard", "工作台", "menu", "/", "", 10],
  ["stores", "门店管理", "menu", "/stores", "", 100],
  ["stores.list", "门店列表", "menu", "/stores/list", "stores", 110],
  ["stores.archives", "门店档案", "menu", "/stores/archives", "stores", 120],
  ["stores.reconciliation", "门店对账", "menu", "/stores/reconciliation", "stores", 130],
  ["invoices", "发票池", "menu", "/invoices", "", 200],
  ["invoices.matched", "已匹配单据确认", "menu", "/invoices/matched", "invoices", 210],
  ["invoices.confirmedReport", "匹配确认报表", "menu", "/invoices/confirmed-report", "invoices", 220],
  ["invoices.amountMismatch", "金额不一致处理", "menu", "/invoices/amount-mismatch", "invoices", 230],
  ["invoices.unmatched", "未匹配发票确认", "menu", "/invoices/unmatched", "invoices", 240],
  ["bankTransactions", "银行流水", "menu", "/bank-transactions", "", 300],
  ["bankTransactions.matching", "流水匹配", "menu", "/bank-transactions/matching", "bankTransactions", 310],
  ["bankTransactions.receipts", "回单归档", "menu", "/bank-transactions/receipts", "bankTransactions", 320],
  ["bankTransactions.exceptions", "异常流水", "menu", "/bank-transactions/exceptions", "bankTransactions", 330],
  ["documents", "业务单据", "menu", "/documents", "", 400],
  ["documents.erp", "ERP单据", "menu", "/documents/erp", "documents", 410],
  ["documents.oa", "OA单据", "menu", "/documents/oa", "documents", 420],
  ["documents.contracts", "合同/结算单", "menu", "/documents/contracts", "documents", 430],
  ["vouchers", "凭证档案", "menu", "/vouchers", "", 500],
  ["vouchers.pending", "待生成凭证", "menu", "/vouchers/pending", "vouchers", 510],
  ["vouchers.generated", "已生成凭证", "menu", "/vouchers/generated", "vouchers", 520],
  ["vouchers.ncRecords", "NC对接记录", "menu", "/vouchers/nc-records", "vouchers", 530],
  ["admin", "系统管理", "menu", "/admin", "", 900],
  ["admin.users", "用户管理", "menu", "/admin/users", "admin", 910],
  ["admin.permissions", "权限管理", "menu", "/admin/permissions", "admin", 920],
  ["admin.dataScopes", "数据范围", "menu", "/admin/data-scopes", "admin", 930],
] as const

export async function syncWecomUsers() {
  try {
    const users = await getWecomUsers()
    if (users.length === 0) {
      return { ok: true, message: "企业微信没有返回可同步用户" }
    }

    await ensureUserPasswordTable()
    const defaultPassword = process.env.DEFAULT_USER_PASSWORD || "123456"

    await executeOracleTransaction(
      users.flatMap((user) => [
        {
          sql: `merge into ETLKP.EA_USER target
                using (
                  select :wecomUserId wecom_user_id,
                         :username username,
                         :displayName display_name,
                         :mobile mobile,
                         :email email,
                         :departmentName department_name
                  from dual
                ) source
                on (target.wecom_user_id = source.wecom_user_id)
                when matched then update set
                  target.username = source.username,
                  target.display_name = source.display_name,
                  target.mobile = source.mobile,
                  target.email = source.email,
                  target.department_name = source.department_name,
                  target.status = 'enabled',
                  target.is_deleted = '0',
                  target.update_time = sysdate
                when not matched then insert (
                  id,
                  username,
                  display_name,
                  mobile,
                  email,
                  wecom_user_id,
                  department_name,
                  status,
                  is_deleted,
                  create_time,
                  update_time
                ) values (
                  rawtohex(sys_guid()),
                  source.username,
                  source.display_name,
                  source.mobile,
                  source.email,
                  source.wecom_user_id,
                  source.department_name,
                  'enabled',
                  '0',
                  sysdate,
                  sysdate
                )`,
          binds: {
            wecomUserId: user.userid,
            username: user.userid,
            displayName: user.name,
            mobile: user.mobile ?? null,
            email: user.email ?? null,
            departmentName: user.departmentName ?? null,
          },
        },
        {
          sql: `merge into ETLKP.EA_USER_PASSWORD target
                using (
                  select u.id user_id,
                         :passwordHash password_hash
                  from ETLKP.EA_USER u
                  where u.wecom_user_id = :wecomUserId
                    and nvl(u.is_deleted, '0') <> '1'
                ) source
                on (target.user_id = source.user_id)
                when matched then update set
                  target.is_deleted = '0',
                  target.update_time = sysdate
                when not matched then insert (
                  id,
                  user_id,
                  password_hash,
                  password_reset_required,
                  is_deleted,
                  create_time,
                  update_time
                ) values (
                  rawtohex(sys_guid()),
                  source.user_id,
                  source.password_hash,
                  '1',
                  '0',
                  sysdate,
                  sysdate
                )`,
          binds: {
            wecomUserId: user.userid,
            passwordHash: createPasswordHash(defaultPassword),
          },
        },
      ])
    )

    revalidatePath("/admin/users")
    return {
      ok: true,
      message: `已同步 ${users.length} 个企业微信用户，新用户默认密码为 ${defaultPassword}`,
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    return { ok: false, message }
  }
}

export async function syncDefaultPermissions() {
  try {
    await executeOracleTransaction(
      defaultPermissionDefinitions.map(
        ([code, name, type, routePath, parentCode, sortNo]) => ({
          sql: `merge into ETLKP.EA_PERMISSION target
                using (
                  select :code permission_code,
                         :name permission_name,
                         :type permission_type,
                         :routePath route_path,
                         :parentCode parent_code,
                         :sortNo sort_no
                  from dual
                ) source
                on (target.permission_code = source.permission_code)
                when matched then update set
                  target.permission_name = source.permission_name,
                  target.permission_type = source.permission_type,
                  target.route_path = source.route_path,
                  target.parent_code = nullif(source.parent_code, ''),
                  target.sort_no = source.sort_no,
                  target.is_deleted = '0',
                  target.update_time = sysdate
                when not matched then insert (
                  id,
                  permission_code,
                  permission_name,
                  permission_type,
                  route_path,
                  parent_code,
                  sort_no,
                  is_deleted,
                  create_time,
                  update_time
                ) values (
                  rawtohex(sys_guid()),
                  source.permission_code,
                  source.permission_name,
                  source.permission_type,
                  source.route_path,
                  nullif(source.parent_code, ''),
                  source.sort_no,
                  '0',
                  sysdate,
                  sysdate
                )`,
          binds: { code, name, type, routePath, parentCode, sortNo },
        })
      )
    )

    revalidatePath("/admin/permissions")
    return { ok: true, message: `已同步 ${defaultPermissionDefinitions.length} 个权限点` }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    return { ok: false, message }
  }
}

export async function createRole(formData: FormData) {
  try {
    const roleCode = String(formData.get("roleCode") ?? "").trim()
    const roleName = String(formData.get("roleName") ?? "").trim()
    const description = String(formData.get("description") ?? "").trim()
    const rawPermissionIds = String(formData.get("permissionIds") ?? "[]")

    if (!roleCode || !roleName) {
      return { ok: false, message: "请输入角色编码和角色名称" }
    }

    let permissionIds: string[]
    try {
      const parsed = JSON.parse(rawPermissionIds)
      permissionIds = Array.isArray(parsed)
        ? parsed.map((item) => String(item).trim()).filter(Boolean)
        : []
    } catch {
      permissionIds = asIds(rawPermissionIds)
    }

    const uniquePermissionIds = Array.from(new Set(permissionIds))
    const roleId = randomUUID().replace(/-/g, "")
    await executeOracleTransaction([
      {
        sql: `insert into ETLKP.EA_ROLE (
                id,
                role_code,
                role_name,
                description,
                is_deleted,
                create_time,
                update_time
              ) values (
                :roleId,
                :roleCode,
                :roleName,
                :description,
                '0',
                sysdate,
                sysdate
              )`,
        binds: {
          roleId,
          roleCode,
          roleName,
          description: description || null,
        },
      },
      ...uniquePermissionIds.map((permissionId) => ({
        sql: `insert into ETLKP.EA_ROLE_PERMISSION (
                id,
                role_id,
                permission_id,
                is_deleted,
                create_time,
                update_time
              ) values (
                rawtohex(sys_guid()),
                :roleId,
                :permissionId,
                '0',
                sysdate,
                sysdate
              )`,
        binds: { roleId, permissionId },
      })),
    ])

    revalidatePath("/admin/permissions")
    revalidatePath("/admin/users")
    return { ok: true, message: "角色已创建" }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    if (message.includes("UK_EA_ROLE_CODE") || message.includes("unique")) {
      return { ok: false, message: "角色编码已存在" }
    }
    return { ok: false, message }
  }
}

export async function updateRolePermissions(formData: FormData) {
  try {
    const roleId = String(formData.get("roleId") ?? "").trim()
    const rawPermissionIds = String(formData.get("permissionIds") ?? "[]")

    if (!roleId) {
      return { ok: false, message: "缺少角色 ID" }
    }

    let permissionIds: string[]
    try {
      const parsed = JSON.parse(rawPermissionIds)
      permissionIds = Array.isArray(parsed)
        ? parsed.map((item) => String(item).trim()).filter(Boolean)
        : []
    } catch {
      permissionIds = asIds(rawPermissionIds)
    }

    const uniquePermissionIds = Array.from(new Set(permissionIds))
    await executeOracleTransaction([
      {
        sql: `update ETLKP.EA_ROLE_PERMISSION
              set is_deleted = '1',
                  update_time = sysdate
              where role_id = :roleId
                and nvl(is_deleted, '0') <> '1'`,
        binds: { roleId },
      },
      ...uniquePermissionIds.map((permissionId) => ({
        sql: `merge into ETLKP.EA_ROLE_PERMISSION target
              using (
                select :roleId role_id,
                       :permissionId permission_id
                from dual
              ) source
              on (
                target.role_id = source.role_id
                and target.permission_id = source.permission_id
              )
              when matched then update set
                target.is_deleted = '0',
                target.update_time = sysdate
              when not matched then insert (
                id,
                role_id,
                permission_id,
                is_deleted,
                create_time,
                update_time
              ) values (
                rawtohex(sys_guid()),
                source.role_id,
                source.permission_id,
                '0',
                sysdate,
                sysdate
              )`,
        binds: { roleId, permissionId },
      })),
    ])

    revalidatePath("/admin/permissions")
    return { ok: true, message: "权限设置已保存" }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    return { ok: false, message }
  }
}

export async function updateDataScopeUsers(formData: FormData) {
  try {
    const scopeId = String(formData.get("scopeId") ?? "").trim()
    const rawUserIds = String(formData.get("userIds") ?? "[]")

    if (!scopeId) {
      return { ok: false, message: "缺少数据范围 ID" }
    }

    let userIds: string[]
    try {
      const parsed = JSON.parse(rawUserIds)
      userIds = Array.isArray(parsed)
        ? parsed.map((item) => String(item).trim()).filter(Boolean)
        : []
    } catch {
      userIds = asIds(rawUserIds)
    }

    const uniqueUserIds = Array.from(new Set(userIds))
    await executeOracleTransaction([
      {
        sql: `update ETLKP.EA_USER_DATA_SCOPE
              set is_deleted = '1',
                  update_time = sysdate
              where scope_id = :scopeId
                and nvl(is_deleted, '0') <> '1'`,
        binds: { scopeId },
      },
      ...uniqueUserIds.map((userId) => ({
        sql: `merge into ETLKP.EA_USER_DATA_SCOPE target
              using (
                select :userId user_id,
                       :scopeId scope_id
                from dual
              ) source
              on (
                target.user_id = source.user_id
                and target.scope_id = source.scope_id
              )
              when matched then update set
                target.is_deleted = '0',
                target.update_time = sysdate
              when not matched then insert (
                id,
                user_id,
                scope_id,
                is_deleted,
                create_time,
                update_time
              ) values (
                rawtohex(sys_guid()),
                source.user_id,
                source.scope_id,
                '0',
                sysdate,
                sysdate
              )`,
        binds: { userId, scopeId },
      })),
    ])

    revalidatePath("/admin/data-scopes")
    revalidatePath("/admin/users")
    return { ok: true, message: "数据范围用户已保存" }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    return { ok: false, message }
  }
}

export async function updateUserRoles(formData: FormData) {
  try {
    const userId = String(formData.get("userId") ?? "").trim()
    const rawRoleIds = String(formData.get("roleIds") ?? "[]")

    if (!userId) {
      return { ok: false, message: "缺少用户 ID" }
    }

    let roleIds: string[]
    try {
      const parsed = JSON.parse(rawRoleIds)
      roleIds = Array.isArray(parsed)
        ? parsed.map((item) => String(item).trim()).filter(Boolean)
        : []
    } catch {
      roleIds = asIds(rawRoleIds)
    }

    const uniqueRoleIds = Array.from(new Set(roleIds))
    await executeOracleTransaction([
      {
        sql: `update ETLKP.EA_USER_ROLE
              set is_deleted = '1',
                  update_time = sysdate
              where user_id = :userId
                and nvl(is_deleted, '0') <> '1'`,
        binds: { userId },
      },
      ...uniqueRoleIds.map((roleId) => ({
        sql: `merge into ETLKP.EA_USER_ROLE target
              using (
                select :userId user_id,
                       :roleId role_id
                from dual
              ) source
              on (
                target.user_id = source.user_id
                and target.role_id = source.role_id
              )
              when matched then update set
                target.is_deleted = '0',
                target.update_time = sysdate
              when not matched then insert (
                id,
                user_id,
                role_id,
                is_deleted,
                create_time,
                update_time
              ) values (
                rawtohex(sys_guid()),
                source.user_id,
                source.role_id,
                '0',
                sysdate,
                sysdate
              )`,
        binds: { userId, roleId },
      })),
    ])

    revalidatePath("/admin/users")
    revalidatePath("/admin/permissions")
    return { ok: true, message: "用户角色已保存" }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    return { ok: false, message }
  }
}

export async function updateUserStoreScopes(formData: FormData) {
  try {
    const userId = String(formData.get("userId") ?? "").trim()
    const rawStores = String(formData.get("stores") ?? "[]")

    if (!userId) {
      return { ok: false, message: "缺少用户 ID" }
    }

    let stores: { id: string; name: string; taxNo?: string }[]
    try {
      const parsed = JSON.parse(rawStores)
      stores = Array.isArray(parsed)
        ? parsed
            .map((item) => ({
              id: String(item?.id ?? "").trim(),
              name: String(item?.name ?? "").trim(),
              taxNo: item?.taxNo ? String(item.taxNo).trim() : undefined,
            }))
            .filter((item) => item.id && item.name)
        : []
    } catch {
      stores = []
    }

    const uniqueStores = Array.from(
      new Map(stores.map((store) => [store.id, store])).values()
    )

    await executeOracleTransaction([
      {
        sql: `update ETLKP.EA_USER_DATA_SCOPE
              set is_deleted = '1',
                  update_time = sysdate
              where user_id = :userId
                and nvl(is_deleted, '0') <> '1'`,
        binds: { userId },
      },
      ...uniqueStores.flatMap((store) => {
        const scopeCode = `store:${store.id}`
        return [
          {
            sql: `merge into ETLKP.EA_DATA_SCOPE target
                  using (
                    select :scopeCode scope_code,
                           :scopeName scope_name,
                           :storeId store_ids,
                           :storeName store_names
                    from dual
                  ) source
                  on (target.scope_code = source.scope_code)
                  when matched then update set
                    target.scope_name = source.scope_name,
                    target.scope_type = 'store',
                    target.store_ids = source.store_ids,
                    target.store_names = source.store_names,
                    target.is_deleted = '0',
                    target.update_time = sysdate
                  when not matched then insert (
                    id,
                    scope_code,
                    scope_name,
                    scope_type,
                    store_ids,
                    store_names,
                    is_deleted,
                    create_time,
                    update_time
                  ) values (
                    rawtohex(sys_guid()),
                    source.scope_code,
                    source.scope_name,
                    'store',
                    source.store_ids,
                    source.store_names,
                    '0',
                    sysdate,
                    sysdate
                  )`,
            binds: {
              scopeCode,
              scopeName: store.name,
              storeId: store.id,
              storeName: store.name,
            },
          },
          {
            sql: `merge into ETLKP.EA_USER_DATA_SCOPE target
                  using (
                    select :userId user_id,
                           ds.id scope_id
                    from ETLKP.EA_DATA_SCOPE ds
                    where ds.scope_code = :scopeCode
                      and nvl(ds.is_deleted, '0') <> '1'
                  ) source
                  on (
                    target.user_id = source.user_id
                    and target.scope_id = source.scope_id
                  )
                  when matched then update set
                    target.is_deleted = '0',
                    target.update_time = sysdate
                  when not matched then insert (
                    id,
                    user_id,
                    scope_id,
                    is_deleted,
                    create_time,
                    update_time
                  ) values (
                    rawtohex(sys_guid()),
                    source.user_id,
                    source.scope_id,
                    '0',
                    sysdate,
                    sysdate
                  )`,
            binds: { userId, scopeCode },
          },
        ]
      }),
    ])

    revalidatePath("/admin/users")
    revalidatePath("/admin/data-scopes")
    return { ok: true, message: "用户门店数据范围已保存" }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    return { ok: false, message }
  }
}

type ManualAssociationPair = {
  invoiceId: string
  billId: string
  billNo: string
  amount: number
}

type OracleStatement = {
  sql: string
  binds?: Record<string, unknown>
}

const INVOICE_CHECKED_STATUS = "已勾选"

function uniqueIds(ids: string[]) {
  return Array.from(new Set(ids.map((id) => id.trim()).filter(Boolean)))
}

function markInvoiceCheckedStatements(invoiceIds: string[]): OracleStatement[] {
  return uniqueIds(invoiceIds).map((invoiceId) => ({
    sql: `update ETLKP.INVOICE_HEADER
            set check_status = :checkStatus,
                update_time = sysdate
          where to_char(id) = :invoiceId
            and nvl(is_deleted, '0') <> '1'`,
    binds: {
      invoiceId,
      checkStatus: INVOICE_CHECKED_STATUS,
    },
  }))
}

async function markInvoicesChecked(invoiceIds: string[]) {
  for (const statement of markInvoiceCheckedStatements(invoiceIds)) {
    await executeOracleStatement(statement.sql, statement.binds)
  }
}

function manualAssociationPairs(formData: FormData): ManualAssociationPair[] {
  const rawPairs = String(formData.get("pairs") ?? "")
  if (rawPairs) {
    try {
      const parsed = JSON.parse(rawPairs) as Partial<ManualAssociationPair>[]
      if (Array.isArray(parsed)) {
        return parsed
          .map((pair) => ({
            invoiceId: String(pair.invoiceId ?? "").trim(),
            billId: String(pair.billId ?? "").trim(),
            billNo: String(pair.billNo ?? "").trim(),
            amount: Number(pair.amount ?? 0),
          }))
          .filter((pair) => pair.invoiceId && pair.billId && pair.amount !== 0)
      }
    } catch {
      return []
    }
  }

  const invoiceIds = asIds(formData.get("invoiceIds"))
  const billIds = asIds(formData.get("billIds"))
  const billNos = asIds(formData.get("billNos"))
  const amounts = asIds(formData.get("amounts"))

  return invoiceIds
    .map((invoiceId, index) => ({
      invoiceId,
      billId: billIds[index] ?? "",
      billNo: billNos[index] ?? billIds[index] ?? "",
      amount: Number(amounts[index] ?? 0),
    }))
    .filter((pair) => pair.invoiceId && pair.billId && pair.amount !== 0)
}

export async function confirmInvoiceMatch(formData: FormData) {
  const invoiceId = String(formData.get("invoiceId") ?? "")
  if (!invoiceId) {
    return { ok: false, message: "缺少发票 ID" }
  }

  const rows = await executeOracleStatement(
    `update ETLKP.INVOICE_MATCH_RECORD_ZJB
        set manual_confirm_flag = 'Y',
            match_status = nvl(match_status, 'CONFIRMED'),
            update_time = sysdate
      where header_id = :invoiceId
        and nvl(is_deleted, '0') <> '1'
        and id = (
          select id
          from (
            select id
            from ETLKP.INVOICE_MATCH_RECORD_ZJB
            where header_id = :invoiceId
              and nvl(is_deleted, '0') <> '1'
            order by update_time desc nulls last, create_time desc nulls last
          )
          where rownum = 1
        )`,
    { invoiceId }
  )

  if (rows > 0) {
    await markInvoicesChecked([invoiceId])
  }

  revalidateInvoiceViews()
  return {
    ok: rows > 0,
    message: rows > 0 ? "已确认匹配" : "没有找到可确认的匹配记录",
  }
}

export async function confirmInvoiceMatches(formData: FormData) {
  const invoiceIds = asIds(formData.get("invoiceIds"))
  if (invoiceIds.length === 0) {
    return { ok: false, message: "请先选择发票" }
  }

  let rows = 0
  for (const invoiceId of invoiceIds) {
    rows += await executeOracleStatement(
      `update ETLKP.INVOICE_MATCH_RECORD_ZJB
          set manual_confirm_flag = 'Y',
              match_status = nvl(match_status, 'CONFIRMED'),
              update_time = sysdate
        where header_id = :invoiceId
          and nvl(is_deleted, '0') <> '1'`,
      { invoiceId }
    )
  }

  if (rows > 0) {
    await markInvoicesChecked(invoiceIds)
  }

  revalidateInvoiceViews()
  return {
    ok: rows > 0,
    message: rows > 0 ? `已确认 ${rows} 条匹配记录` : "没有找到可确认的匹配记录",
  }
}

export async function deleteInvoiceMatch(formData: FormData) {
  const invoiceId = String(formData.get("invoiceId") ?? "")
  if (!invoiceId) {
    return { ok: false, message: "缺少发票 ID" }
  }

  const rows = await executeOracleStatement(
    `update ETLKP.INVOICE_MATCH_RECORD_ZJB
        set is_deleted = '1',
            update_time = sysdate
      where header_id = :invoiceId
        and nvl(is_deleted, '0') <> '1'
        and id = (
          select id
          from (
            select id
            from ETLKP.INVOICE_MATCH_RECORD_ZJB
            where header_id = :invoiceId
              and nvl(is_deleted, '0') <> '1'
            order by update_time desc nulls last, create_time desc nulls last
          )
          where rownum = 1
        )`,
    { invoiceId }
  )

  revalidateInvoiceViews()
  return {
    ok: rows > 0,
    message: rows > 0 ? "已删除错误匹配" : "没有找到可删除的匹配记录",
  }
}

export async function createManualInvoiceAssociation(formData: FormData) {
  const pairs = manualAssociationPairs(formData)
  const invoiceIds = Array.from(new Set(pairs.map((pair) => pair.invoiceId)))

  if (invoiceIds.length === 0 || pairs.length === 0) {
    return { ok: false, message: "请选择发票和业务单据" }
  }

  const statements: OracleStatement[] =
    invoiceIds.map((invoiceId) => ({
      sql: `update ETLKP.INVOICE_MATCH_RECORD_ZJB
              set is_deleted = '1',
                  update_time = sysdate
            where header_id = :invoiceId
              and nvl(is_deleted, '0') <> '1'`,
      binds: { invoiceId },
    }))

  for (const pair of pairs) {
    statements.push({
      sql: `insert into ETLKP.INVOICE_MATCH_RECORD_ZJB (
           id,
           header_id,
           target_system,
           target_object_type,
           target_object_id,
           target_no,
           match_scene,
           match_rule_code,
           match_rule_name,
           match_status,
           match_score,
           match_confidence,
           auto_match_flag,
           match_amount,
           diff_amount,
           manual_confirm_flag,
           confirm_user,
           confirm_time,
           remark,
           is_deleted,
           create_time,
           update_time
         ) values (
           rawtohex(sys_guid()),
           :invoiceId,
           'PAYMENT',
           'PAYMENT_BILL',
           :billId,
           :billNo,
           'MANUAL_ASSOCIATION',
           'MANUAL',
           '人工关联',
           'MANUAL',
           100,
           100,
           'N',
           :matchAmount,
           0,
           'Y',
           'system',
           sysdate,
           '金额不一致页面人工关联',
           '0',
           sysdate,
           sysdate
         )`,
      binds: {
        invoiceId: pair.invoiceId,
        billId: pair.billId,
        billNo: pair.billNo || pair.billId,
        matchAmount: pair.amount,
      },
    })
  }

  statements.push(...markInvoiceCheckedStatements(invoiceIds))

  await executeOracleTransaction(statements)
  revalidateInvoiceViews()

  return {
    ok: true,
    message: `已建立 ${pairs.length} 条人工关联`,
  }
}

function requiredText(formData: FormData, key: string) {
  return String(formData.get(key) ?? "").trim()
}

function optionalText(formData: FormData, key: string) {
  const value = requiredText(formData, key)
  return value || null
}

function generatedManualDocNo() {
  const date = new Date().toISOString().slice(0, 10).replace(/-/g, "")
  const suffix = randomUUID().replace(/-/g, "").slice(0, 8).toUpperCase()
  return `MANUAL-${date}-${suffix}`
}

export async function createSupplementalInvoiceAssociation(formData: FormData) {
  const invoiceId = requiredText(formData, "invoiceId")
  const invoiceAmount = Number(formData.get("invoiceAmount") ?? 0)
  const docNo = generatedManualDocNo()
  const businessDate = requiredText(formData, "businessDate")
  const partnerName = requiredText(formData, "partnerName")
  const amount = Number(formData.get("amount") ?? 0)
  const manualBillId = randomUUID().replace(/-/g, "").toUpperCase()
  const diffAmount = Number((invoiceAmount - amount).toFixed(2))

  if (!invoiceId || !businessDate || !partnerName || !Number.isFinite(amount)) {
    return { ok: false, message: "请补全业务日期、往来方和金额" }
  }

  const statements: OracleStatement[] = [
    {
      sql: `update ETLKP.INVOICE_MATCH_RECORD_ZJB
              set is_deleted = '1',
                  update_time = sysdate
            where header_id = :invoiceId
              and nvl(is_deleted, '0') <> '1'`,
      binds: { invoiceId },
    },
    {
      sql: `insert into ETLKP.MANUAL_BUSINESS_BILL (
             id,
             doc_no,
             doc_source,
             business_date,
             partner_name,
             store_name,
             department_name,
             business_type,
             amount,
             remark,
             created_by,
             is_deleted,
             create_time,
             update_time
           ) values (
             :id,
             :docNo,
             '手工补录',
             to_date(:businessDate, 'yyyy-mm-dd'),
             :partnerName,
             :storeName,
             :departmentName,
             :businessType,
             :amount,
             :remark,
             'system',
             '0',
             sysdate,
             sysdate
           )`,
      binds: {
        id: manualBillId,
        docNo,
        businessDate,
        partnerName,
        storeName: optionalText(formData, "storeName"),
        departmentName: optionalText(formData, "departmentName"),
        businessType: optionalText(formData, "businessType"),
        amount,
        remark: optionalText(formData, "remark"),
      },
    },
    {
      sql: `insert into ETLKP.INVOICE_MATCH_RECORD_ZJB (
             id,
             header_id,
             target_system,
             target_object_type,
             target_object_id,
             target_no,
             match_scene,
             match_rule_code,
             match_rule_name,
             match_status,
             match_score,
             match_confidence,
             auto_match_flag,
             match_amount,
             diff_amount,
             manual_confirm_flag,
             confirm_user,
             confirm_time,
             remark,
             is_deleted,
             create_time,
             update_time
           ) values (
             rawtohex(sys_guid()),
             :invoiceId,
             'MANUAL',
             'MANUAL_BUSINESS_BILL',
             :manualBillId,
             :docNo,
             'SUPPLEMENTAL_ASSOCIATION',
             'MANUAL_SUPPLEMENT',
             '财务补录关联',
             'MANUAL',
             100,
             100,
             'N',
             :amount,
             :diffAmount,
             case when abs(:diffAmount) < 0.01 then 'Y' else 'N' end,
             'system',
             case when abs(:diffAmount) < 0.01 then sysdate else null end,
             :remark,
             '0',
             sysdate,
             sysdate
           )`,
      binds: {
        invoiceId,
        manualBillId,
        docNo,
        amount,
        diffAmount,
        remark: optionalText(formData, "remark") || "财务手工补录业务单据并关联发票",
      },
    },
  ]

  if (Math.abs(diffAmount) < 0.01) {
    statements.push(...markInvoiceCheckedStatements([invoiceId]))
  }

  await executeOracleTransaction(statements)
  revalidateInvoiceViews()

  return {
    ok: true,
    message:
      Math.abs(diffAmount) < 0.01
        ? "已补录单据并确认关联"
        : "已补录单据，金额不一致，进入金额异常处理",
  }
}
