import fs from "node:fs"
import path from "node:path"
import process from "node:process"
import oracledb from "oracledb"

function loadEnvFile(file) {
  if (!fs.existsSync(file)) return

  const content = fs.readFileSync(file, "utf8")
  for (const line of content.split(/\r?\n/)) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith("#")) continue
    const index = trimmed.indexOf("=")
    if (index <= 0) continue
    const key = trimmed.slice(0, index).trim()
    let value = trimmed.slice(index + 1).trim()
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1)
    }
    process.env[key] ??= value
  }
}

function requireEnv(name) {
  const value = process.env[name]
  if (!value) throw new Error(`Missing Oracle environment variable: ${name}`)
  return value
}

async function executeIgnoreExists(connection, sql, label) {
  try {
    await connection.execute(sql)
    console.log(`[ok] ${label}`)
  } catch (error) {
    if (error?.errorNum === 955) {
      console.log(`[skip] ${label} already exists`)
      return
    }
    throw error
  }
}

async function insertIfMissing(connection, table, keyColumn, keyValue, sql, binds, label) {
  const result = await connection.execute(
    `select count(*) total from ${table} where ${keyColumn} = :keyValue`,
    { keyValue },
    { outFormat: oracledb.OUT_FORMAT_OBJECT }
  )
  const total = Number(result.rows?.[0]?.TOTAL ?? 0)
  if (total > 0) {
    console.log(`[skip] ${label} already exists`)
    return
  }
  await connection.execute(sql, binds)
  console.log(`[ok] ${label}`)
}

const root = process.cwd()
loadEnvFile(path.join(root, ".env.local"))
loadEnvFile(path.join(root, ".env"))

const connection = await oracledb.getConnection({
  user: requireEnv("ORACLE_USER"),
  password: requireEnv("ORACLE_PASSWORD"),
  connectString: requireEnv("ORACLE_CONNECT_STRING"),
})

try {
  await executeIgnoreExists(
    connection,
    `create table ETLKP.EA_USER (
      id varchar2(64) primary key,
      username varchar2(100) not null,
      display_name varchar2(100),
      mobile varchar2(50),
      email varchar2(200),
      wecom_user_id varchar2(100),
      department_name varchar2(200),
      status varchar2(20) default 'enabled',
      last_login_time date,
      is_deleted varchar2(1) default '0',
      create_time date default sysdate,
      update_time date default sysdate
    )`,
    "create ETLKP.EA_USER"
  )
  await executeIgnoreExists(
    connection,
    "create unique index ETLKP.UK_EA_USER_USERNAME on ETLKP.EA_USER(username)",
    "create ETLKP.UK_EA_USER_USERNAME"
  )
  await executeIgnoreExists(
    connection,
    "create index ETLKP.IDX_EA_USER_WECOM on ETLKP.EA_USER(wecom_user_id)",
    "create ETLKP.IDX_EA_USER_WECOM"
  )

  await executeIgnoreExists(
    connection,
    `create table ETLKP.EA_ROLE (
      id varchar2(64) primary key,
      role_code varchar2(100) not null,
      role_name varchar2(100) not null,
      description varchar2(500),
      is_deleted varchar2(1) default '0',
      create_time date default sysdate,
      update_time date default sysdate
    )`,
    "create ETLKP.EA_ROLE"
  )
  await executeIgnoreExists(
    connection,
    "create unique index ETLKP.UK_EA_ROLE_CODE on ETLKP.EA_ROLE(role_code)",
    "create ETLKP.UK_EA_ROLE_CODE"
  )

  await executeIgnoreExists(
    connection,
    `create table ETLKP.EA_PERMISSION (
      id varchar2(64) primary key,
      permission_code varchar2(150) not null,
      permission_name varchar2(150) not null,
      permission_type varchar2(30) default 'menu',
      route_path varchar2(300),
      parent_code varchar2(150),
      sort_no number default 0,
      is_deleted varchar2(1) default '0',
      create_time date default sysdate,
      update_time date default sysdate
    )`,
    "create ETLKP.EA_PERMISSION"
  )
  await executeIgnoreExists(
    connection,
    "create unique index ETLKP.UK_EA_PERMISSION_CODE on ETLKP.EA_PERMISSION(permission_code)",
    "create ETLKP.UK_EA_PERMISSION_CODE"
  )

  await executeIgnoreExists(
    connection,
    `create table ETLKP.EA_USER_ROLE (
      id varchar2(64) primary key,
      user_id varchar2(64) not null,
      role_id varchar2(64) not null,
      is_deleted varchar2(1) default '0',
      create_time date default sysdate,
      update_time date default sysdate
    )`,
    "create ETLKP.EA_USER_ROLE"
  )
  await executeIgnoreExists(
    connection,
    "create index ETLKP.IDX_EA_USER_ROLE_USER on ETLKP.EA_USER_ROLE(user_id)",
    "create ETLKP.IDX_EA_USER_ROLE_USER"
  )
  await executeIgnoreExists(
    connection,
    "create index ETLKP.IDX_EA_USER_ROLE_ROLE on ETLKP.EA_USER_ROLE(role_id)",
    "create ETLKP.IDX_EA_USER_ROLE_ROLE"
  )

  await executeIgnoreExists(
    connection,
    `create table ETLKP.EA_ROLE_PERMISSION (
      id varchar2(64) primary key,
      role_id varchar2(64) not null,
      permission_id varchar2(64) not null,
      is_deleted varchar2(1) default '0',
      create_time date default sysdate,
      update_time date default sysdate
    )`,
    "create ETLKP.EA_ROLE_PERMISSION"
  )
  await executeIgnoreExists(
    connection,
    "create index ETLKP.IDX_EA_ROLE_PERMISSION_ROLE on ETLKP.EA_ROLE_PERMISSION(role_id)",
    "create ETLKP.IDX_EA_ROLE_PERMISSION_ROLE"
  )

  await executeIgnoreExists(
    connection,
    `create table ETLKP.EA_DATA_SCOPE (
      id varchar2(64) primary key,
      scope_code varchar2(100) not null,
      scope_name varchar2(150) not null,
      scope_type varchar2(30) default 'store',
      store_ids varchar2(2000),
      store_names varchar2(4000),
      is_deleted varchar2(1) default '0',
      create_time date default sysdate,
      update_time date default sysdate
    )`,
    "create ETLKP.EA_DATA_SCOPE"
  )
  await executeIgnoreExists(
    connection,
    "create unique index ETLKP.UK_EA_DATA_SCOPE_CODE on ETLKP.EA_DATA_SCOPE(scope_code)",
    "create ETLKP.UK_EA_DATA_SCOPE_CODE"
  )

  await executeIgnoreExists(
    connection,
    `create table ETLKP.EA_USER_DATA_SCOPE (
      id varchar2(64) primary key,
      user_id varchar2(64) not null,
      scope_id varchar2(64) not null,
      is_deleted varchar2(1) default '0',
      create_time date default sysdate,
      update_time date default sysdate
    )`,
    "create ETLKP.EA_USER_DATA_SCOPE"
  )
  await executeIgnoreExists(
    connection,
    "create index ETLKP.IDX_EA_USER_SCOPE_USER on ETLKP.EA_USER_DATA_SCOPE(user_id)",
    "create ETLKP.IDX_EA_USER_SCOPE_USER"
  )

  await executeIgnoreExists(
    connection,
    `create table ETLKP.EA_AUTH_SESSION (
      id varchar2(64) primary key,
      user_id varchar2(64) not null,
      expires_at date not null,
      is_deleted varchar2(1) default '0',
      create_time date default sysdate,
      update_time date default sysdate
    )`,
    "create ETLKP.EA_AUTH_SESSION"
  )
  await executeIgnoreExists(
    connection,
    "create index ETLKP.IDX_EA_SESSION_USER on ETLKP.EA_AUTH_SESSION(user_id)",
    "create ETLKP.IDX_EA_SESSION_USER"
  )
  await executeIgnoreExists(
    connection,
    "create index ETLKP.IDX_EA_SESSION_EXPIRES on ETLKP.EA_AUTH_SESSION(expires_at)",
    "create ETLKP.IDX_EA_SESSION_EXPIRES"
  )

  await executeIgnoreExists(
    connection,
    `create table ETLKP.EA_USER_PASSWORD (
      id varchar2(64) primary key,
      user_id varchar2(64) not null,
      password_hash varchar2(300) not null,
      password_reset_required varchar2(1) default '1',
      is_deleted varchar2(1) default '0',
      create_time date default sysdate,
      update_time date default sysdate
    )`,
    "create ETLKP.EA_USER_PASSWORD"
  )
  await executeIgnoreExists(
    connection,
    "create unique index ETLKP.UK_EA_USER_PASSWORD_USER on ETLKP.EA_USER_PASSWORD(user_id)",
    "create ETLKP.UK_EA_USER_PASSWORD_USER"
  )

  await insertIfMissing(
    connection,
    "ETLKP.EA_ROLE",
    "role_code",
    "admin",
    `insert into ETLKP.EA_ROLE (id, role_code, role_name, description)
     values (rawtohex(sys_guid()), :roleCode, :roleName, :description)`,
    {
      roleCode: "admin",
      roleName: "系统管理员",
      description: "拥有全部管理权限",
    },
    "seed role admin"
  )

  const permissions = [
    ["admin.users", "用户管理", "/admin/users", 900],
    ["admin.permissions", "权限管理", "/admin/permissions", 910],
    ["admin.dataScopes", "数据范围管理", "/admin/data-scopes", 920],
  ]

  for (const [code, name, route, sortNo] of permissions) {
    await insertIfMissing(
      connection,
      "ETLKP.EA_PERMISSION",
      "permission_code",
      code,
      `insert into ETLKP.EA_PERMISSION (
         id, permission_code, permission_name, permission_type, route_path, sort_no
       ) values (
         rawtohex(sys_guid()), :code, :name, 'menu', :route, :sortNo
       )`,
      { code, name, route, sortNo },
      `seed permission ${code}`
    )
  }

  await connection.commit()

  const verify = await connection.execute(
    `select table_name
     from all_tables
     where owner = 'ETLKP'
       and table_name in (
         'EA_USER', 'EA_ROLE', 'EA_PERMISSION', 'EA_USER_ROLE',
         'EA_ROLE_PERMISSION', 'EA_DATA_SCOPE', 'EA_USER_DATA_SCOPE',
         'EA_AUTH_SESSION', 'EA_USER_PASSWORD'
       )
     order by table_name`,
    {},
    { outFormat: oracledb.OUT_FORMAT_OBJECT }
  )
  console.log(`[done] auth schema ready, tables=${verify.rows?.length ?? 0}`)
} finally {
  await connection.close()
}
