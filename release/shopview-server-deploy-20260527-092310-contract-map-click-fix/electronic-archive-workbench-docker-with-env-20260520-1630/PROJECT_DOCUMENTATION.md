# 电子档案工作台项目文档

## 1. 项目概述

本项目是一个面向财务档案、发票、业务单据和匹配记录管理的电子档案工作台。系统通过 Oracle 数据库读取 ETL 数据，提供发票池、付款单、OA 单据、门店管理、凭证档案等页面，用于辅助财务人员进行单据查看、发票匹配确认、人工关联和归档处理。

当前项目重点对接了以下数据域：

- 发票数据：发票列表、匹配状态、金额差异、未匹配发票。
- 付款单数据：ERP/付款单列表、付款金额、已关联发票数量。
- OA 单据数据：OA 报销单据、门店、申请人、供应商、关联发票明细。
- 匹配记录：通过匹配表维护发票与业务单据之间的关联关系。
- 门店信息：支持按门店查看业务数据。

## 2. 技术栈

- 框架：Next.js 16 App Router
- 语言：TypeScript
- UI：React 19、Tailwind CSS 4、Radix UI、lucide-react
- 数据库：Oracle
- 数据库驱动：oracledb
- 包管理：pnpm
- 部署方式：Next standalone、Docker、Docker Compose

主要脚本见 `package.json`：

```bash
pnpm dev        # 本地开发
pnpm build      # 构建 standalone 产物
pnpm start      # 启动 standalone 服务
pnpm start:next # 使用 next start 启动
pnpm lint       # ESLint 检查
```

## 3. 目录结构

```text
app/
  (dashboard)/                 # 工作台主应用页面
    page.tsx                   # 首页工作台
    invoices/                  # 发票池
    documents/                 # 业务单据，包括 ERP / OA / 合同
    bank-transactions/         # 银行流水
    vouchers/                  # 凭证档案
    stores/                    # 门店管理
  api/stores/route.ts          # 门店接口
  login/page.tsx               # 登录页
  layout.tsx                   # 根布局

components/
  app-sidebar.tsx              # 左侧菜单和门店选择
  app-header.tsx               # 顶部栏
  invoice-actions.tsx          # 发票操作组件
  manual-invoice-association.tsx
  table-pagination.tsx
  query-select.tsx
  ui/                          # 通用 UI 组件

lib/
  oracle.ts                    # Oracle 连接和执行封装
  etl-data.ts                  # 主要数据查询和映射逻辑
  actions.ts                   # Server Actions 写操作
  stores.ts                    # 门店读取和当前门店 cookie
  utils.ts

scripts/
  rm-next-standalone.mjs       # 构建前清理 standalone
  start-standalone.mjs         # standalone 启动辅助脚本

Dockerfile
docker-compose.yml
DOCKER_DEPLOY.md
```

## 4. 环境变量

项目运行依赖 Oracle 连接配置：

```env
ORACLE_USER=
ORACLE_PASSWORD=
ORACLE_CONNECT_STRING=
```

OA 单据字段可通过环境变量覆盖，默认按当前 `ETLKP.OA_BILL` 表结构读取：

```env
# OA_BILL_DOC_NO_EXPR=ob.sphbillno
# OA_BILL_STORE_EXPR=ob.store_id
# OA_BILL_DOC_TYPE_EXPR=ob.type_01
# OA_BILL_AMOUNT_EXPR=ob.payment_amount
# OA_BILL_BUSINESS_DATE_EXPR=ob.create_time
# OA_BILL_APPLICANT_EXPR=ob.lastname
# OA_BILL_SUPPLIER_EXPR=ob.supplier_name
# OA_BILL_DEPT_EXPR=ob.departmentname
# OA_BILL_TARGET_OBJECT_TYPE=报销
```

## 5. 数据库对接说明

### 5.1 Oracle 执行封装

数据库访问集中在 `lib/oracle.ts`：

- `executeOracle<T>()`：执行查询 SQL。
- `executeOracleStatement()`：执行单条写操作，自动提交。
- `executeOracleTransaction()`：执行事务语句组，失败回滚。

所有 Oracle 连接配置从环境变量读取。

### 5.2 发票相关表

主要表：

- `ETLKP.INVOICE_HEADER`
- `ETLKP.INVOICE_MATCH_RECORD_ZJB`
- `ETLKP.PAYMENT_BILL`

当前发票模块支持：

- 全部发票分页。
- 已匹配待确认。
- 匹配确认报表。
- 金额不一致处理。
- 未匹配发票。
- 人工关联付款单。

匹配状态计算逻辑位于 `lib/etl-data.ts`：

- 无匹配记录：`unmatched`
- 有匹配且差额不为 0：`amount_mismatch`
- 有匹配且人工确认：`archived`
- 其他有匹配：`matched`

### 5.3 付款单相关表

主要表：

- `ETLKP.PAYMENT_BILL`
- `ETLKP.PAYMENT_STORE_NAME`
- `ETLKP.INVOICE_MATCH_RECORD_ZJB`
- `ETLKP.INVOICE_HEADER`

付款单页面会统计：

- 单据金额。
- 已关联发票数量。
- 已匹配金额。
- 剩余金额。
- 状态：已完成、部分关联、待关联。

### 5.4 OA 单据相关表

主要表：

- `ETLKP.OA_BILL`
- `ETLKP.PAYMENT_STORE_NAME`
- `ETLKP.INVOICE_MATCH_RECORD_ZJB`
- `ETLKP.INVOICE_HEADER`

当前 `OA_BILL` 默认字段映射：

| 页面字段 | 数据库字段 |
| --- | --- |
| 单据 ID | `OA_BILL.ID` |
| 单据编号 | `OA_BILL.SPHBILLNO` |
| 门店编码 | `OA_BILL.STORE_ID` |
| 门店名称 | `PAYMENT_STORE_NAME.STORE_NAME` |
| 单据类型 | `OA_BILL.TYPE_01` |
| 申请人 | `OA_BILL.LASTNAME` |
| 供应商/往来方 | `OA_BILL.SUPPLIER_NAME` |
| 部门 | `OA_BILL.DEPARTMENTNAME` |
| 金额 | `OA_BILL.PAYMENT_AMOUNT` |
| 业务日期 | `OA_BILL.CREATE_TIME` |

OA 单据与发票的关联：

```text
OA_BILL.ID
  = INVOICE_MATCH_RECORD_ZJB.TARGET_OBJECT_ID

INVOICE_MATCH_RECORD_ZJB.HEADER_ID
  = INVOICE_HEADER.ID
```

当前默认 `TARGET_OBJECT_TYPE` 为：

```text
报销
```

OA 状态规则：

- 没有关联发票：待关联
- 有关联发票，且 `MANUAL_CONFIRM_FLAG = 'Y'` 或 `MATCH_STATUS = 'OA确认'/'CONFIRMED'`，且非异常：已完成
- 其他有关联情况：部分关联

OA 详情弹窗展示：

- OA 单据基础信息。
- 门店名称和门店编码。
- 供应商/往来方。
- 关联发票明细，点击详情时通过 `/api/oa-bills/[id]/invoices` 按需加载。
- 发票号码、销方、购方、开票日期、价税合计、匹配状态、匹配度、差额。

## 6. 主要页面说明

### 6.1 工作台

路径：`/`

展示：

- 待确认发票。
- 金额不一致。
- 未匹配发票。
- 付款单数量。
- 最近匹配记录。
- 快捷入口。

### 6.2 发票池

路径：

- `/invoices`
- `/invoices/matched`
- `/invoices/confirmed-report`
- `/invoices/amount-mismatch`
- `/invoices/unmatched`

功能：

- 发票分页查询。
- 按供应商/发票号筛选。
- 按年月筛选。
- 批量确认匹配。
- 删除错误匹配。
- 金额不一致人工关联。

### 6.3 业务单据

路径：

- `/documents`
- `/documents/erp`
- `/documents/oa`
- `/documents/contracts`

其中 OA 页面已完成真实数据库对接和详情弹窗。

### 6.4 门店管理

路径：

- `/stores`
- `/stores/list`
- `/stores/archives`
- `/stores/reconciliation`

当前门店通过 cookie 保存：

- `activeStoreId`
- `activeStoreName`

门店列表来自 `ETLKP.PAYMENT_STORE_NAME`。

### 6.5 凭证档案

路径：

- `/vouchers`
- `/vouchers/pending`
- `/vouchers/generated`
- `/vouchers/nc-records`

当前页面以展示为主，部分数据仍为静态或待对接状态。

## 7. 写操作说明

写操作集中在 `lib/actions.ts`：

- `confirmInvoiceMatch()`：确认单张发票匹配。
- `confirmInvoiceMatches()`：批量确认发票匹配。
- `deleteInvoiceMatch()`：删除或标记错误匹配。
- `createManualInvoiceAssociation()`：人工创建发票与付款单关联。

这些操作会写入或更新 `ETLKP.INVOICE_MATCH_RECORD_ZJB`。

## 8. 部署说明

### 8.1 本地开发

```bash
pnpm install
pnpm dev
```

默认访问：

```text
http://localhost:3020
```

### 8.2 生产构建

```bash
pnpm build
pnpm start
```

自定义端口：

```bash
pnpm start -p 3019
```

### 8.3 Docker

```bash
docker build -t electronic-archive-workbench:latest .
docker run -d \
  --name electronic-archive-workbench \
  --restart unless-stopped \
  -p 3020:3000 \
  --env-file .env \
  electronic-archive-workbench:latest
```

或：

```bash
docker compose up -d --build
```

## 9. 当前验证状态

已验证：

- TypeScript 检查通过：

```bash
pnpm exec tsc --noEmit --pretty false
```

- 完整构建在提升权限下通过：

```bash
pnpm build
```

注意：

在 Windows 环境中，普通权限执行 `pnpm build` 可能遇到：

- `.next\standalone` 被占用。
- Next worker `spawn EPERM`。

这通常是旧 Node 服务、文件资源管理器占用目录或当前执行环境权限限制导致。处理方式：

- 停止正在运行的 `pnpm start` 或 Node 服务。
- 关闭打开 `.next\standalone` 的资源管理器窗口。
- 重新执行构建。

## 10. 待办事项

### 10.1 登录认证

当前登录页为前端模拟登录。需要接入正式认证能力：

- 账号密码校验。
- 用户会话。
- 退出登录。
- 角色权限。
- 菜单权限。

### 10.2 权限与门店隔离

当前门店通过 cookie 保存，后端部分查询使用门店过滤。后续需要：

- 将门店权限与真实登录用户绑定。
- 后端强校验用户可访问门店。
- 防止手动修改 cookie 越权访问。

### 10.3 OA 关联功能

OA 页面“关联”按钮当前仍是界面入口，未实现完整操作流程。待实现：

- 打开可关联发票选择器。
- 支持一张 OA 单据关联多张发票。
- 写入 `INVOICE_MATCH_RECORD_ZJB`。
- 支持撤销或调整关联。
- 操作后刷新 OA 列表和详情。

### 10.4 银行流水模块

银行流水页面目前仍偏静态，需要确认并对接：

- 银行流水主表。
- 回单表。
- 异常流水规则。
- 流水与付款单/发票/凭证的关联逻辑。

### 10.5 凭证档案模块

凭证档案仍需进一步真实化：

- 待生成凭证数据源。
- 已生成凭证数据源。
- NC 对接记录。
- 凭证详情。
- 附件预览和下载。

### 10.6 数据层拆分

`lib/etl-data.ts` 当前承担了大量查询职责。建议后续拆分：

- `lib/data/invoices.ts`
- `lib/data/payments.ts`
- `lib/data/oa.ts`
- `lib/data/dashboard.ts`
- `lib/data/stores.ts`

这样可以降低维护成本，避免单文件过大。

### 10.7 测试补充

建议补充：

- 查询参数归一化测试。
- 金额和红字发票计算测试。
- OA 状态推导测试。
- Server Actions 写入测试。
- Oracle 集成验证脚本。

### 10.8 构建和部署稳定性

需要处理 Windows 环境下 `.next\standalone` 文件锁问题：

- 部署前停止旧服务。
- 构建脚本中加入服务停止步骤。
- 避免资源管理器或编辑器占用 `.next\standalone`。

### 10.9 错误处理和空状态

当前部分页面对数据库错误、空数据、字段缺失的用户提示较少。建议：

- 增加数据库连接失败提示。
- 增加页面级错误边界。
- 对关键查询显示明确错误信息。
- 保留空状态和重试入口。

### 10.10 字段配置治理

OA 字段支持环境变量覆盖，但需要进一步规范：

- 将字段映射写入文档。
- 标明每个字段的数据类型和来源。
- 对危险 SQL 表达式覆盖增加校验。

## 11. 交接重点

如果后续开发者接手，建议优先阅读：

1. `lib/oracle.ts`
2. `lib/etl-data.ts`
3. `lib/actions.ts`
4. `components/app-sidebar.tsx`
5. `app/(dashboard)/documents/oa/page.tsx`
6. `app/(dashboard)/invoices/amount-mismatch/page.tsx`
7. `.env.example`

其中 `lib/etl-data.ts` 是当前最核心的数据对接文件，`app/(dashboard)/documents/oa/page.tsx` 是最近重点改造的 OA 页面。
