declare module "oracledb" {
  type OracleConnection = {
    execute: <T>(
      sql: string,
      binds: Record<string, unknown>,
      options?: Record<string, unknown>
    ) => Promise<{ rows?: T[]; rowsAffected?: number }>
    commit: () => Promise<void>
    rollback: () => Promise<void>
    close: () => Promise<void>
  }

  const oracledb: {
    OUT_FORMAT_OBJECT: number
    outFormat: number
    getConnection: (config: {
      user: string
      password: string
      connectString: string
    }) => Promise<OracleConnection>
    createPool: (config: {
      user: string
      password: string
      connectString: string
      poolMin?: number
      poolMax?: number
      poolIncrement?: number
      poolTimeout?: number
      queueTimeout?: number
    }) => Promise<{
      getConnection: () => Promise<OracleConnection>
    }>
  }

  export default oracledb
}
