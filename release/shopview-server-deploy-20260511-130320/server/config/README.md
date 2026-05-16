# 数据库配置系统使用指南

## 概述

这是一个灵活的数据库配置系统，支持多种数据库类型和环境配置，实现了应用与数据库的完全分离。

## 特性

- ✅ **多数据库支持**: PostgreSQL、MySQL、SQLite、Neon
- ✅ **环境配置**: 开发、测试、生产环境独立配置
- ✅ **配置方式**: 支持 DATABASE_URL 和分离式配置
- ✅ **连接管理**: 自动连接池管理和故障恢复
- ✅ **向下兼容**: 兼容现有的 DATABASE_URL 配置方式

## 配置方式

### 方式一：DATABASE_URL（兼容现有方式）

```bash
DATABASE_URL=postgresql://user:pass@host:port/database
```

### 方式二：分离式配置（推荐）

```bash
DB_TYPE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=store_management
DB_USER=postgres
DB_PASSWORD=your_password
DB_SSL=false
DB_POOL_SIZE=10
```

## 支持的数据库类型

| 数据库类型 | 状态 | 配置示例 |
|-----------|------|----------|
| **Neon** | ✅ 已实现 | `DB_TYPE=neon` + `DATABASE_URL` |
| **PostgreSQL** | ✅ 已实现 | `DB_TYPE=postgresql` + 连接参数 |
| **MySQL** | 🚧 计划中 | `DB_TYPE=mysql` + 连接参数 |
| **SQLite** | 🚧 计划中 | `DB_TYPE=sqlite` + `DB_NAME=./data/app.db` |

## 快速开始

### 1. 环境配置

复制 `.env.example` 为 `.env` 并配置数据库信息：

```bash
cp .env.example .env
```

### 2. 应用代码中使用

```typescript
import { initializeDatabase, getAppConfig } from './config';

// 初始化数据库连接
const db = await initializeDatabase();

// 获取应用配置
const config = getAppConfig();
console.log('当前环境:', config.environment);
console.log('数据库类型:', config.database.type);
```

### 3. 在 Storage 类中使用

```typescript
import { initializeDatabase, type DrizzleDatabase } from "./config";

class MemStorage {
  private db: DrizzleDatabase | null = null;

  constructor() {
    this.initializeDatabase();
  }

  private async initializeDatabase() {
    try {
      this.db = await initializeDatabase();
      console.log('数据库连接成功');
    } catch (error) {
      console.warn('数据库连接失败，使用内存存储');
    }
  }
}
```

## 环境配置示例

### 开发环境

```bash
NODE_ENV=development
DB_TYPE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=store_dev
DB_USER=postgres
DB_PASSWORD=dev_password
```

### 生产环境（Neon）

```bash
NODE_ENV=production
DB_TYPE=neon
DATABASE_URL=postgresql://user:pass@ep-xxx.neon.tech/dbname?sslmode=require
```

### 测试环境

```bash
NODE_ENV=test
DB_TYPE=sqlite
DB_NAME=:memory:
```

## 连接测试

```typescript
import { databaseFactory, getAppConfig } from './config';

// 测试数据库连接
const config = getAppConfig();
const isConnected = await databaseFactory.testConnection(config.database);

if (isConnected) {
  console.log('✅ 数据库连接测试成功');
} else {
  console.log('❌ 数据库连接测试失败');
}
```

## 故障排除

### 常见问题

1. **连接失败**
   - 检查网络连接
   - 验证数据库服务是否运行
   - 确认用户名密码正确

2. **配置错误**
   - 使用 `validateDatabaseConfig()` 验证配置
   - 检查环境变量是否正确设置

3. **兼容性问题**
   - 确保数据库版本兼容
   - 检查SSL配置

### 调试模式

设置环境变量启用详细日志：

```bash
DEBUG=database:*
```

## 扩展数据库支持

要添加新的数据库类型支持：

1. 在 `database.ts` 中添加新的 `DatabaseType`
2. 在 `database-factory.ts` 中实现连接逻辑
3. 添加相应的依赖包
4. 更新配置模板

## 最佳实践

1. **环境分离**: 不同环境使用不同的数据库配置
2. **连接池**: 合理配置连接池大小
3. **SSL**: 生产环境启用SSL连接
4. **备份**: 定期备份数据库配置
5. **监控**: 监控数据库连接状态

## 版本历史

- **v1.0.0**: 初始版本，支持 Neon 和 PostgreSQL
- **v1.1.0**: 计划添加 MySQL 和 SQLite 支持