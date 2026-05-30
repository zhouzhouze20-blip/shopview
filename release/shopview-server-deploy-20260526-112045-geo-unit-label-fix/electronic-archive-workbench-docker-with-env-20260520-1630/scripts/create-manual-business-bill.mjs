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

async function execute(connection, sql, label) {
  await connection.execute(sql)
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
    `create table ETLKP.MANUAL_BUSINESS_BILL (
      id varchar2(64) primary key,
      doc_no varchar2(100) not null,
      doc_source varchar2(50) default '手工补录' not null,
      business_date date not null,
      partner_name varchar2(300) not null,
      store_name varchar2(300),
      department_name varchar2(300),
      business_type varchar2(100),
      amount number(18, 2) not null,
      remark varchar2(1000),
      created_by varchar2(100),
      is_deleted varchar2(1) default '0' not null,
      create_time date default sysdate not null,
      update_time date default sysdate not null
    )`,
    "create ETLKP.MANUAL_BUSINESS_BILL"
  )

  await executeIgnoreExists(
    connection,
    `create unique index ETLKP.UK_MANUAL_BUSINESS_BILL_NO
      on ETLKP.MANUAL_BUSINESS_BILL(doc_no)`,
    "create ETLKP.UK_MANUAL_BUSINESS_BILL_NO"
  )

  await execute(
    connection,
    `comment on table ETLKP.MANUAL_BUSINESS_BILL is '财务手工补录业务单据，用于无 OA/付款单来源的发票关联'`,
    "comment table"
  )
  await execute(
    connection,
    `comment on column ETLKP.MANUAL_BUSINESS_BILL.id is '手工补录单据 ID'`,
    "comment id"
  )
  await execute(
    connection,
    `comment on column ETLKP.MANUAL_BUSINESS_BILL.doc_no is '手工补录单据编号'`,
    "comment doc_no"
  )
  await execute(
    connection,
    `comment on column ETLKP.MANUAL_BUSINESS_BILL.doc_source is '单据来源，默认手工补录'`,
    "comment doc_source"
  )
  await execute(
    connection,
    `comment on column ETLKP.MANUAL_BUSINESS_BILL.business_date is '业务单据日期'`,
    "comment business_date"
  )
  await execute(
    connection,
    `comment on column ETLKP.MANUAL_BUSINESS_BILL.partner_name is '供应商/往来方'`,
    "comment partner_name"
  )
  await execute(
    connection,
    `comment on column ETLKP.MANUAL_BUSINESS_BILL.store_name is '门店/购方'`,
    "comment store_name"
  )
  await execute(
    connection,
    `comment on column ETLKP.MANUAL_BUSINESS_BILL.department_name is '所属部门'`,
    "comment department_name"
  )
  await execute(
    connection,
    `comment on column ETLKP.MANUAL_BUSINESS_BILL.business_type is '业务类型'`,
    "comment business_type"
  )
  await execute(
    connection,
    `comment on column ETLKP.MANUAL_BUSINESS_BILL.amount is '单据金额'`,
    "comment amount"
  )

  const result = await connection.execute(
    `select count(*) as total
     from all_tables
     where owner = 'ETLKP'
       and table_name = 'MANUAL_BUSINESS_BILL'`,
    {},
    { outFormat: oracledb.OUT_FORMAT_OBJECT }
  )
  const total = result.rows?.[0]?.TOTAL ?? 0
  if (Number(total) !== 1) {
    throw new Error("MANUAL_BUSINESS_BILL was not found after creation")
  }

  console.log("[done] MANUAL_BUSINESS_BILL is ready")
} finally {
  await connection.close()
}
