# ShopView 文档入口

本文档目录用于给新同事和 Codex 提供统一入口。根目录只保留项目入口文档，专题资料按用途归档到 `docs/` 下。

## 快速入口

| 文档 | 用途 |
| --- | --- |
| [Codex 开发接手指南](./DEVELOPMENT.md) | 新同事使用 Codex 拉代码、理解项目、启动和检查 |
| [Codex 协作规范](./COLLABORATION.md) | 两个人都用 Codex 时的任务边界、分支、PR、验收规则 |
| [Codex 任务拆分和提示词](./TASK_SPLIT.md) | 适合交给 Codex 的任务粒度、提示词模板和验收方式 |
| [系统架构梳理](./architecture/SYSTEM_ARCHITECTURE.md) | 当前业务模块、数据流、核心表和待办 |
| [启动与部署](../STARTUP.md) | 本地启动、服务器 Docker 部署和访问地址 |
| [应用部署说明](./deployment/APP-DEPLOYMENT.md) | Docker 应用部署检查项 |

## 文档分区

| 分区 | 用途 |
| --- | --- |
| [architecture](./architecture/README.md) | 系统架构、权限模型、技术设计 |
| [business](./business/README.md) | 业务流程、业务口径、专题设计 |
| [deployment](./deployment/README.md) | 启动、部署、演示、环境安装 |
| [todos](./todos/README.md) | 模块迁移、待办、后续实施清单 |
| [decoration-process-brief](./decoration-process-brief/README.md) | 装修流程汇报材料 |
| [revenue-attribution](./revenue-attribution/) | 收益归因相关资料 |
| [project_](./project_/) | 项目过程资料 |

## 常用专题

| 文档 | 主题 |
| --- | --- |
| [权限设计](./architecture/AUTH_PERMISSION_DESIGN.md) | 认证、权限和数据范围设计 |
| [系统架构梳理](./architecture/SYSTEM_ARCHITECTURE.md) | 当前业务模块、数据流、核心表和待办 |
| [切换真实 API](./deployment/SWITCH_TO_REAL_API.md) | 前端从 mock 切换到真实接口 |
| [前端演示指南](./business/FRONTEND_DEMO_GUIDE.md) | 前端演示和页面说明 |
| [装修流程开发基线](./business/装修流程开发基线.md) | 装修流程当前开发基线 |
| [装修流程接口设计](./business/装修流程接口设计.md) | 装修流程 API 设计 |
| [销售 AI 分析规则库设计](./business/销售AI分析规则库设计.md) | 销售分析规则设计 |
| [活动分析模块代办](./todos/活动分析模块代办.md) | 活动分析模块待办 |

## 文档维护规则

- 新增通用协作文档放在 `docs/` 根目录。
- 新增专题文档按分区放入 `docs/architecture`、`docs/business`、`docs/deployment` 或 `docs/todos`，并补充对应分区索引。
- 根目录只放 `README.md`、`STARTUP.md` 这类项目入口文档。
- `release/` 是历史部署包归档，不作为当前项目文档入口。
- 文档里不要写真实账号、密码、密钥、企业微信 Secret 或生产数据库公网地址。
- 如果某个说明已经失效，直接修改原文并在提交信息里说明，不要另写一份相似文档。
- 使用 Codex 修改文档时，任务说明里要明确“只改文档，不改业务代码”。
