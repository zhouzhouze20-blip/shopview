import "server-only"

import { pbkdf2Sync, randomBytes, randomUUID, timingSafeEqual } from "crypto"
import { cookies } from "next/headers"
import { executeOracle, executeOracleStatement } from "@/lib/oracle"

export const AUTH_SESSION_COOKIE = "eaSessionId"

export type CurrentUser = {
  id: string
  username: string
  displayName: string
  wecomUserId: string
  mobile: string
  email: string
  departmentName: string
  permissionCodes: string[]
  permissionRoutes: string[]
  dataScopeStoreIds: string[]
  hasAllDataScope: boolean
}

let userPasswordTableReady: Promise<void> | undefined

async function safeStatement(sql: string, binds: Record<string, unknown>) {
  try {
    return await executeOracleStatement(sql, binds)
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    if (message.includes("ORA-00942")) return 0
    throw error
  }
}

export function createPasswordHash(password: string) {
  const salt = randomBytes(16).toString("hex")
  const hash = pbkdf2Sync(password, salt, 120000, 32, "sha256").toString("hex")
  return `pbkdf2_sha256$120000$${salt}$${hash}`
}

function verifyPassword(password: string, storedHash: string) {
  const [algorithm, iterationsText, salt, hash] = storedHash.split("$")
  if (algorithm !== "pbkdf2_sha256" || !iterationsText || !salt || !hash) {
    return false
  }

  const iterations = Number(iterationsText)
  if (!Number.isInteger(iterations) || iterations <= 0) return false

  const inputHash = pbkdf2Sync(password, salt, iterations, 32, "sha256")
  const storedBuffer = Buffer.from(hash, "hex")
  if (inputHash.length !== storedBuffer.length) return false
  return timingSafeEqual(inputHash, storedBuffer)
}

export async function ensureUserPasswordTable() {
  if (!userPasswordTableReady) {
    userPasswordTableReady = (async () => {
      try {
        await executeOracleStatement(
          `create table ETLKP.EA_USER_PASSWORD (
             id varchar2(64) primary key,
             user_id varchar2(64) not null,
             password_hash varchar2(300) not null,
             password_reset_required varchar2(1) default '1',
             is_deleted varchar2(1) default '0',
             create_time date default sysdate,
             update_time date default sysdate
           )`
        )
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error)
        if (!message.includes("ORA-00955")) throw error
      }

      try {
        await executeOracleStatement(
          "create unique index ETLKP.UK_EA_USER_PASSWORD_USER on ETLKP.EA_USER_PASSWORD(user_id)"
        )
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error)
        if (!message.includes("ORA-00955")) throw error
      }
    })()
  }

  return userPasswordTableReady
}

export async function verifyUserPassword(userId: string, password: string) {
  await ensureUserPasswordTable()

  type Row = { PASSWORD_HASH: string | null }
  const rows = await executeOracle<Row>(
    `select password_hash
     from ETLKP.EA_USER_PASSWORD
     where user_id = :userId
       and nvl(is_deleted, '0') <> '1'
     fetch first 1 rows only`,
    { userId }
  )
  const passwordHash = rows[0]?.PASSWORD_HASH
  if (!passwordHash) return false

  return verifyPassword(password, passwordHash)
}

export async function getCurrentUser(): Promise<CurrentUser | undefined> {
  const cookieStore = await cookies()
  const sessionId = cookieStore.get(AUTH_SESSION_COOKIE)?.value
  if (!sessionId) return undefined

  type Row = {
    ID: string
    USERNAME: string | null
    DISPLAY_NAME: string | null
    WECOM_USER_ID: string | null
    MOBILE: string | null
    EMAIL: string | null
    DEPARTMENT_NAME: string | null
  }

  try {
    const rows = await executeOracle<Row>(
      `select u.id,
              u.username,
              u.display_name,
              u.wecom_user_id,
              u.mobile,
              u.email,
              u.department_name
       from ETLKP.EA_AUTH_SESSION s
       join ETLKP.EA_USER u on u.id = s.user_id
       where s.id = :sessionId
         and s.expires_at > sysdate
         and nvl(s.is_deleted, '0') <> '1'
         and nvl(u.is_deleted, '0') <> '1'
         and nvl(u.status, 'enabled') = 'enabled'`,
      { sessionId }
    )
    const user = rows[0]
    if (!user) return undefined

    type PermissionRow = {
      PERMISSION_CODE: string | null
      ROUTE_PATH: string | null
    }
    const permissions = await executeOracle<PermissionRow>(
      `select permission_code, route_path
       from (
         select distinct p.permission_code, p.route_path, p.sort_no
         from ETLKP.EA_USER_ROLE ur
         join ETLKP.EA_ROLE r
           on r.id = ur.role_id
          and nvl(r.is_deleted, '0') <> '1'
         join ETLKP.EA_ROLE_PERMISSION rp
           on rp.role_id = r.id
          and nvl(rp.is_deleted, '0') <> '1'
         join ETLKP.EA_PERMISSION p
           on p.id = rp.permission_id
          and nvl(p.is_deleted, '0') <> '1'
         where ur.user_id = :userId
           and nvl(ur.is_deleted, '0') <> '1'
       )
       order by sort_no, permission_code`,
      { userId: user.ID }
    )

    type DataScopeRow = {
      SCOPE_TYPE: string | null
      STORE_IDS: string | null
    }
    const dataScopes = await executeOracle<DataScopeRow>(
      `select distinct ds.scope_type, ds.store_ids
       from ETLKP.EA_USER_DATA_SCOPE uds
       join ETLKP.EA_DATA_SCOPE ds
         on ds.id = uds.scope_id
        and nvl(ds.is_deleted, '0') <> '1'
       where uds.user_id = :userId
         and nvl(uds.is_deleted, '0') <> '1'`,
      { userId: user.ID }
    )
    const hasAllDataScope =
      user.USERNAME?.toLowerCase() === "admin" ||
      dataScopes.some((scope) => scope.SCOPE_TYPE === "all")
    const dataScopeStoreIds = Array.from(
      new Set(
        dataScopes.flatMap((scope) =>
          (scope.STORE_IDS || "")
            .split(",")
            .map((id) => id.trim())
            .filter(Boolean)
        )
      )
    )

    return {
      id: user.ID,
      username: user.USERNAME || "-",
      displayName: user.DISPLAY_NAME || user.USERNAME || "-",
      wecomUserId: user.WECOM_USER_ID || "-",
      mobile: user.MOBILE || "-",
      email: user.EMAIL || "-",
      departmentName: user.DEPARTMENT_NAME || "-",
      permissionCodes: permissions
        .map((permission) => permission.PERMISSION_CODE)
        .filter((code): code is string => Boolean(code)),
      permissionRoutes: permissions
        .map((permission) => permission.ROUTE_PATH)
        .filter((route): route is string => Boolean(route)),
      dataScopeStoreIds,
      hasAllDataScope,
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    if (message.includes("ORA-00942")) return undefined
    throw error
  }
}

export async function createAuthSession(userId: string) {
  const sessionId = randomUUID().replace(/-/g, "")
  await safeStatement(
    `insert into ETLKP.EA_AUTH_SESSION (
       id, user_id, expires_at, is_deleted, create_time, update_time
     ) values (
       :sessionId, :userId, sysdate + 7, '0', sysdate, sysdate
     )`,
    { sessionId, userId }
  )
  await safeStatement(
    `update ETLKP.EA_USER
        set last_login_time = sysdate,
            update_time = sysdate
      where id = :userId`,
    { userId }
  )

  const cookieStore = await cookies()
  cookieStore.set(AUTH_SESSION_COOKIE, sessionId, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  })
}

export async function logoutCurrentSession() {
  const cookieStore = await cookies()
  const sessionId = cookieStore.get(AUTH_SESSION_COOKIE)?.value

  if (sessionId) {
    await safeStatement(
      `update ETLKP.EA_AUTH_SESSION
          set is_deleted = '1',
              update_time = sysdate
        where id = :sessionId`,
      { sessionId }
    )
  }

  cookieStore.delete(AUTH_SESSION_COOKIE)
}

export async function findUserByWecomUserId(wecomUserId: string) {
  type Row = { ID: string }
  try {
    const rows = await executeOracle<Row>(
      `select id
       from ETLKP.EA_USER
       where wecom_user_id = :wecomUserId
         and nvl(is_deleted, '0') <> '1'
         and nvl(status, 'enabled') = 'enabled'
       fetch first 1 rows only`,
      { wecomUserId }
    )
    return rows[0]?.ID
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    if (message.includes("ORA-00942")) return undefined
    throw error
  }
}

export async function findUserByUsername(username: string) {
  type Row = { ID: string }
  try {
    const rows = await executeOracle<Row>(
      `select id
       from ETLKP.EA_USER
       where lower(username) = lower(:username)
         and nvl(is_deleted, '0') <> '1'
         and nvl(status, 'enabled') = 'enabled'
       fetch first 1 rows only`,
      { username }
    )
    return rows[0]?.ID
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    if (message.includes("ORA-00942")) return undefined
    throw error
  }
}

export async function userCanAccessStore(
  userId: string,
  storeId: string,
  storeName: string
) {
  type Row = { TOTAL: number }
  try {
    const rows = await executeOracle<Row>(
      `select count(*) total
       from ETLKP.EA_USER_DATA_SCOPE uds
       join ETLKP.EA_DATA_SCOPE ds
         on ds.id = uds.scope_id
        and nvl(ds.is_deleted, '0') <> '1'
       where uds.user_id = :userId
         and nvl(uds.is_deleted, '0') <> '1'
         and (
           ds.scope_type = 'all'
           or instr(',' || replace(nvl(ds.store_ids, ''), ' ', '') || ',', ',' || :storeId || ',') > 0
           or instr(',' || nvl(ds.store_names, '') || ',', ',' || :storeName || ',') > 0
         )`,
      { userId, storeId, storeName }
    )
    return Number(rows[0]?.TOTAL ?? 0) > 0
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    if (message.includes("ORA-00942")) return true
    throw error
  }
}

export async function ensureAdminUser() {
  await safeStatement(
    `merge into ETLKP.EA_USER target
     using (
       select 'admin' username,
              '系统管理员' display_name,
              '系统管理' department_name
       from dual
     ) source
     on (lower(target.username) = source.username)
     when matched then update set
       target.display_name = nvl(target.display_name, source.display_name),
       target.department_name = nvl(target.department_name, source.department_name),
       target.status = 'enabled',
       target.is_deleted = '0',
       target.update_time = sysdate
     when not matched then insert (
       id,
       username,
       display_name,
       department_name,
       status,
       is_deleted,
       create_time,
       update_time
     ) values (
       rawtohex(sys_guid()),
       source.username,
       source.display_name,
       source.department_name,
       'enabled',
       '0',
       sysdate,
       sysdate
     )`,
    {}
  )

  await safeStatement(
    `merge into ETLKP.EA_USER_ROLE target
     using (
       select u.id user_id, r.id role_id
       from ETLKP.EA_USER u
       join ETLKP.EA_ROLE r on r.role_code = 'admin' and nvl(r.is_deleted, '0') <> '1'
       where lower(u.username) = 'admin'
         and nvl(u.is_deleted, '0') <> '1'
     ) source
     on (target.user_id = source.user_id and target.role_id = source.role_id)
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
    {}
  )

  return findUserByUsername("admin")
}
