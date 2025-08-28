/**
 * 数据库连接工厂
 * 根据配置创建不同类型的数据库连接
 */

import { drizzle as drizzleNeon } from "drizzle-orm/neon-http";
// import { drizzle as drizzlePostgres } from "drizzle-orm/postgres-js";
// import { drizzle as drizzleMysql } from "drizzle-orm/mysql2";
// import { drizzle as drizzleSqlite } from "drizzle-orm/better-sqlite3";

import { neon } from "@neondatabase/serverless";
// import postgres from "postgres";
// import mysql from "mysql2/promise";
// import Database from "better-sqlite3";

import type { DatabaseConfig } from "./database";
import { generateConnectionString, validateDatabaseConfig } from "./database";

export type DrizzleDatabase = ReturnType<typeof drizzleNeon>;

/**
 * 数据库连接工厂类
 */
export class DatabaseFactory {
  private static instance: DatabaseFactory;
  private connections: Map<string, DrizzleDatabase> = new Map();

  private constructor() {}

  static getInstance(): DatabaseFactory {
    if (!DatabaseFactory.instance) {
      DatabaseFactory.instance = new DatabaseFactory();
    }
    return DatabaseFactory.instance;
  }

  /**
   * 创建数据库连接
   */
  async createConnection(config: DatabaseConfig, connectionId: string = 'default'): Promise<DrizzleDatabase> {
    // 验证配置
    validateDatabaseConfig(config);

    // 检查是否已存在连接
    if (this.connections.has(connectionId)) {
      return this.connections.get(connectionId)!;
    }

    let db: DrizzleDatabase;

    try {
      switch (config.type) {
        case 'neon':
        case 'postgresql':
          db = await this.createNeonConnection(config);
          break;
        
        default:
          throw new Error(`暂不支持的数据库类型: ${config.type}，当前仅支持 neon 和 postgresql`);
      }

      this.connections.set(connectionId, db);
      console.log(`✅ 数据库连接已建立: ${config.type} (${connectionId})`);
      return db;

    } catch (error) {
      console.error(`❌ 数据库连接失败: ${config.type}`, error);
      throw new Error(`数据库连接失败: ${error instanceof Error ? error.message : '未知错误'}`);
    }
  }

  /**
   * 创建 Neon 连接
   */
  private async createNeonConnection(config: DatabaseConfig): Promise<ReturnType<typeof drizzleNeon>> {
    if (!config.url) {
      throw new Error('Neon 数据库需要提供 URL');
    }

    const connection = neon(config.url);
    return drizzleNeon(connection);
  }


  /**
   * 获取连接
   */
  getConnection(connectionId: string = 'default'): DrizzleDatabase | undefined {
    return this.connections.get(connectionId);
  }

  /**
   * 关闭连接
   */
  async closeConnection(connectionId: string = 'default'): Promise<void> {
    const connection = this.connections.get(connectionId);
    if (connection) {
      // 这里可以根据不同数据库类型实现特定的关闭逻辑
      this.connections.delete(connectionId);
      console.log(`🔌 数据库连接已关闭: ${connectionId}`);
    }
  }

  /**
   * 关闭所有连接
   */
  async closeAllConnections(): Promise<void> {
    for (const connectionId of this.connections.keys()) {
      await this.closeConnection(connectionId);
    }
  }

  /**
   * 测试数据库连接
   */
  async testConnection(config: DatabaseConfig): Promise<boolean> {
    try {
      const testConnectionId = `test_${Date.now()}`;
      const db = await this.createConnection(config, testConnectionId);
      
      // 执行简单查询测试连接
      await db.execute("SELECT 1" as any);
      
      await this.closeConnection(testConnectionId);
      return true;
    } catch (error) {
      console.error('数据库连接测试失败:', error);
      return false;
    }
  }
}

export default DatabaseFactory.getInstance();