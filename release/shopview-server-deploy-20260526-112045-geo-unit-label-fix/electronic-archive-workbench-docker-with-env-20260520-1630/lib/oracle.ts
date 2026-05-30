import "server-only"

import oracledb from "oracledb"

oracledb.outFormat = oracledb.OUT_FORMAT_OBJECT

function requireEnv(name: string) {
  const value = process.env[name]

  if (!value) {
    throw new Error(`Missing Oracle environment variable: ${name}`)
  }

  return value
}

function getDbConfig() {
  return {
    user: requireEnv("ORACLE_USER"),
    password: requireEnv("ORACLE_PASSWORD"),
    connectString: requireEnv("ORACLE_CONNECT_STRING"),
  }
}

function envNumber(name: string, fallback: number) {
  const raw = process.env[name]
  if (!raw) return fallback
  const value = Number(raw)
  return Number.isFinite(value) && value >= 0 ? value : fallback
}

type OracleConnection = Awaited<ReturnType<typeof oracledb.getConnection>>

let poolPromise:
  | Promise<{
      getConnection: () => Promise<OracleConnection>
    }>
  | undefined

async function getPool() {
  if (!poolPromise) {
    poolPromise = oracledb.createPool({
      ...getDbConfig(),
      poolMin: envNumber("ORACLE_POOL_MIN", 1),
      poolMax: envNumber("ORACLE_POOL_MAX", 10),
      poolIncrement: envNumber("ORACLE_POOL_INCREMENT", 1),
      poolTimeout: envNumber("ORACLE_POOL_TIMEOUT", 60),
      queueTimeout: envNumber("ORACLE_QUEUE_TIMEOUT", 60000),
    })
  }

  return poolPromise
}

async function getConnection() {
  const pool = await getPool()
  return pool.getConnection()
}

export async function executeOracle<T extends Record<string, unknown>>(
  sql: string,
  binds: Record<string, unknown> = {}
): Promise<T[]> {
  let connection: OracleConnection | undefined

  try {
    connection = await getConnection()
    const result = await connection.execute(sql, binds, {
      outFormat: oracledb.OUT_FORMAT_OBJECT,
    })

    return (result.rows ?? []) as T[]
  } finally {
    if (connection) {
      await connection.close()
    }
  }
}

export async function executeOracleStatement(
  sql: string,
  binds: Record<string, unknown> = {}
): Promise<number> {
  let connection: OracleConnection | undefined

  try {
    connection = await getConnection()
    const result = await connection.execute(sql, binds, {
      autoCommit: true,
    })

    return result.rowsAffected ?? 0
  } finally {
    if (connection) {
      await connection.close()
    }
  }
}

export async function executeOracleTransaction(
  statements: { sql: string; binds?: Record<string, unknown> }[]
): Promise<number> {
  let connection: OracleConnection | undefined

  try {
    connection = await getConnection()

    let rows = 0
    for (const statement of statements) {
      const result = await connection.execute(
        statement.sql,
        statement.binds ?? {},
        { autoCommit: false }
      )
      rows += result.rowsAffected ?? 0
    }

    await connection.commit()
    return rows
  } catch (error) {
    if (connection) {
      await connection.rollback()
    }
    throw error
  } finally {
    if (connection) {
      await connection.close()
    }
  }
}
