/**
 * 数据库配置管理
 * 支持多种数据库类型和环境配置
 */

export type DatabaseType = 'postgresql' | 'mysql' | 'sqlite' | 'neon';

export interface DatabaseConfig {
  type: DatabaseType;
  host?: string;
  port?: number;
  database?: string;
  username?: string;
  password?: string;
  url?: string;
  ssl?: boolean;
  poolSize?: number;
  connectionTimeout?: number;
  schema?: string;
}

export interface AppConfig {
  environment: 'development' | 'production' | 'test';
  database: DatabaseConfig;
  server: {
    port: number;
    host: string;
  };
}

/**
 * 默认数据库配置
 */
const defaultConfigs: Record<string, Partial<DatabaseConfig>> = {
  postgresql: {
    type: 'postgresql',
    host: 'localhost',
    port: 5432,
    ssl: false,
    poolSize: 10,
    connectionTimeout: 30000,
  },
  neon: {
    type: 'neon',
    ssl: true,
    poolSize: 5,
    connectionTimeout: 30000,
  },
  mysql: {
    type: 'mysql',
    host: 'localhost',
    port: 3306,
    ssl: false,
    poolSize: 10,
    connectionTimeout: 30000,
  },
  sqlite: {
    type: 'sqlite',
    database: './data/app.db',
  }
};

/**
 * 环境变量到配置的映射
 */
function loadDatabaseConfigFromEnv(): DatabaseConfig {
  // 优先使用 DATABASE_URL（现有方式兼容）
  if (process.env.DATABASE_URL) {
    return {
      type: 'neon',
      url: process.env.DATABASE_URL,
      ssl: true,
    };
  }

  // 使用分离的环境变量配置
  const dbType = (process.env.DB_TYPE || 'postgresql') as DatabaseType;
  const baseConfig = defaultConfigs[dbType] || defaultConfigs.postgresql;

  return {
    ...baseConfig,
    type: dbType,
    host: process.env.DB_HOST,
    port: process.env.DB_PORT ? parseInt(process.env.DB_PORT) : baseConfig.port,
    database: process.env.DB_NAME || process.env.PGDATABASE,
    username: process.env.DB_USER || process.env.PGUSER,
    password: process.env.DB_PASSWORD || process.env.PGPASSWORD,
    url: process.env.DATABASE_URL,
    ssl: process.env.DB_SSL === 'true',
    poolSize: process.env.DB_POOL_SIZE ? parseInt(process.env.DB_POOL_SIZE) : baseConfig.poolSize,
    connectionTimeout: process.env.DB_TIMEOUT ? parseInt(process.env.DB_TIMEOUT) : baseConfig.connectionTimeout,
    schema: process.env.DB_SCHEMA,
  } as DatabaseConfig;
}

/**
 * 加载应用完整配置
 */
export function loadAppConfig(): AppConfig {
  return {
    environment: (process.env.NODE_ENV || 'development') as 'development' | 'production' | 'test',
    database: loadDatabaseConfigFromEnv(),
    server: {
      port: parseInt(process.env.PORT || '5000'),
      host: process.env.HOST || '0.0.0.0',
    },
  };
}

/**
 * 验证数据库配置
 */
export function validateDatabaseConfig(config: DatabaseConfig): void {
  if (!config.type) {
    throw new Error('数据库类型未配置');
  }

  if (config.type !== 'sqlite' && !config.url && (!config.host || !config.database)) {
    throw new Error('数据库连接信息不完整');
  }

  if (config.type === 'sqlite' && !config.database) {
    throw new Error('SQLite 数据库文件路径未配置');
  }
}

/**
 * 生成数据库连接字符串
 */
export function generateConnectionString(config: DatabaseConfig): string {
  if (config.url) {
    return config.url;
  }

  switch (config.type) {
    case 'postgresql':
      return `postgresql://${config.username}:${config.password}@${config.host}:${config.port}/${config.database}${config.ssl ? '?sslmode=require' : ''}`;
    
    case 'mysql':
      return `mysql://${config.username}:${config.password}@${config.host}:${config.port}/${config.database}${config.ssl ? '?ssl=true' : ''}`;
    
    case 'sqlite':
      return `sqlite:${config.database}`;
    
    case 'neon':
      if (!config.url) {
        throw new Error('Neon 数据库需要提供 URL');
      }
      return config.url;
    
    default:
      throw new Error(`不支持的数据库类型: ${config.type}`);
  }
}

/**
 * 预定义的配置模板
 */
export const configTemplates = {
  // 本地开发环境
  development: {
    environment: 'development',
    database: {
      type: 'postgresql' as DatabaseType,
      host: 'localhost',
      port: 5432,
      database: 'store_management_dev',
      username: 'postgres',
      password: 'password',
      ssl: false,
    },
    server: {
      port: 5000,
      host: '0.0.0.0',
    },
  },

  // 生产环境（Neon）
  production: {
    environment: 'production',
    database: {
      type: 'neon' as DatabaseType,
      url: process.env.DATABASE_URL,
      ssl: true,
      poolSize: 20,
    },
    server: {
      port: parseInt(process.env.PORT || '5000'),
      host: '0.0.0.0',
    },
  },

  // 测试环境
  test: {
    environment: 'test',
    database: {
      type: 'sqlite' as DatabaseType,
      database: ':memory:',
    },
    server: {
      port: 5001,
      host: 'localhost',
    },
  },
} as const;

export default loadAppConfig();