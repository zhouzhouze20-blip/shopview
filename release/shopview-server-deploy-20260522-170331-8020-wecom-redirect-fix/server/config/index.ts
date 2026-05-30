/**
 * 配置模块入口
 * 统一导出所有配置相关的功能
 */

export * from './database';
export * from './database-factory';

import appConfig from './database';
import databaseFactory from './database-factory';

// 导出单例实例
export { appConfig, databaseFactory };

// 快捷方法
export async function initializeDatabase() {
  const db = await databaseFactory.createConnection(appConfig.database);
  return db;
}

export function getAppConfig() {
  return appConfig;
}