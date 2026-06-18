# 销售 AI 分析规则库设计

## 1. 决策范围

第一版只做销售看板的柜组分析。

- 分析对象：柜组汇总数据
- 数据来源：复用现有销售看板柜组汇总接口的数据口径
- 规则存放方式：后端代码配置
- AI 接入方式：规则库先生成结构化结论，再把结构化结论交给 AI 生成经营分析文案
- 前端传参方式：前端只传当前筛选条件，不传整张表格数据

不在第一版处理：

- 小票明细级异常
- 商品级异常
- 会员、支付流水、完整小票等敏感明细
- 后台规则配置页面
- 规则入库管理

## 2. 总体链路

```text
销售看板当前筛选条件
  -> POST /api/sales/analysis
  -> 后端按权限拉取柜组汇总数据
  -> 基础指标规则库计算派生指标
  -> 异常规则库识别异常项
  -> 排名/贡献规则生成重点对象
  -> 组装结构化分析结果
  -> AI 根据结构化结果生成经营分析文案
  -> 前端展示结构化结果 + AI 文案
```

关键原则：

- 权限过滤必须发生在分析前。
- AI 不直接接触未经裁剪的原始业务表。
- AI 失败时，接口仍返回规则分析结果。
- 所有规则都必须可解释，返回命中的规则编号、阈值和计算值。

## 3. 输入参数

建议新增接口：

```http
POST /api/sales/analysis
```

请求体：

```json
{
  "level": "groups",
  "start_date": "2026-05-07",
  "end_date": "2026-05-07",
  "prior_start_date": "2025-05-07",
  "prior_end_date": "2025-05-07",
  "store_id": "optional",
  "department_code": "optional",
  "keyword": "optional",
  "limit": 200,
  "include_ai": true
}
```

字段说明：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `level` | 是 | 第一版固定为 `groups` |
| `start_date` | 是 | 本期开始日期 |
| `end_date` | 是 | 本期结束日期 |
| `prior_start_date` | 是 | 同期开始日期 |
| `prior_end_date` | 是 | 同期结束日期 |
| `store_id` | 否 | 当前钻取门店 |
| `department_code` | 否 | 当前钻取部门 |
| `keyword` | 否 | 柜组搜索关键词 |
| `limit` | 否 | 最大分析柜组数，默认 200 |
| `include_ai` | 否 | 是否生成 AI 文案，默认 true |

## 4. 输入数据字段

后端拉取的柜组汇总数据至少需要以下字段：

| 字段 | 说明 |
| --- | --- |
| `group_code` | 柜组编码 |
| `group_name` | 柜组名称 |
| `department_code` | 部门编码 |
| `department_name` | 部门名称 |
| `effective_sales` | 本期销售收入 |
| `same_period_effective_sales` | 同期销售收入 |
| `net_profit` | 本期净毛利 |
| `same_period_net_profit` | 同期净毛利 |
| `ticket_count` | 本期小票数 |
| `same_period_ticket_count` | 同期小票数 |
| `ticket_margin` | 本期毛利率 |
| `same_period_margin` | 同期毛利率 |
| `quantity` | 本期销售数量 |

## 5. 派生指标

规则库先为每个柜组计算派生指标：

| 指标 | 计算方式 |
| --- | --- |
| `sales_delta` | `effective_sales - same_period_effective_sales` |
| `sales_yoy_rate` | 同期销售大于 0 时，`sales_delta / same_period_effective_sales` |
| `profit_delta` | `net_profit - same_period_net_profit` |
| `margin_delta_pp` | `(ticket_margin - same_period_margin) * 100` |
| `ticket_delta` | `ticket_count - same_period_ticket_count` |
| `ticket_yoy_rate` | 同期小票数大于 0 时，`ticket_delta / same_period_ticket_count` |
| `sales_share` | 柜组本期销售 / 全部柜组本期销售 |
| `decline_impact` | 销售下滑金额，`max(0, same_period_effective_sales - effective_sales)` |
| `growth_contribution` | 销售增长金额，`max(0, effective_sales - same_period_effective_sales)` |

## 6. 默认阈值

第一版使用代码默认配置：

```python
DEFAULT_GROUP_ANALYSIS_CONFIG = {
    "min_sales_for_yoy": 1000,
    "min_prior_sales_for_yoy": 1000,
    "large_decline_rate": -0.30,
    "large_growth_rate": 3.00,
    "low_margin_rate": 0.05,
    "margin_drop_pp": -5.0,
    "ticket_decline_rate": -0.30,
    "high_sales_share": 0.10,
    "high_sales_low_margin_rate": 0.08,
    "top_n": 5,
}
```

阈值解释：

| 阈值 | 默认值 | 说明 |
| --- | --- | --- |
| `min_sales_for_yoy` | 1000 | 本期销售低于 1000 元时，不参与部分同比异常判断 |
| `min_prior_sales_for_yoy` | 1000 | 同期销售低于 1000 元时，不参与常规同比判断 |
| `large_decline_rate` | -30% | 销售同比下降超过 30% 视为明显下滑 |
| `large_growth_rate` | +300% | 销售同比增长超过 300% 视为异常增长 |
| `low_margin_rate` | 5% | 毛利率低于 5% 视为低毛利 |
| `margin_drop_pp` | -5 个百分点 | 毛利率较同期下降超过 5 个百分点 |
| `ticket_decline_rate` | -30% | 小票数同比下降超过 30% |
| `high_sales_share` | 10% | 柜组销售占比超过 10% 视为高贡献柜组 |
| `high_sales_low_margin_rate` | 8% | 高销售柜组毛利率低于 8% 需关注 |
| `top_n` | 5 | 排名类结果默认取前 5 |

## 7. 规则分类

### 7.1 基础指标规则

用于生成汇总卡片和 AI 总览素材：

- 总销售收入
- 总同期销售收入
- 总销售同比
- 总净毛利
- 总同期净毛利
- 综合毛利率
- 同期综合毛利率
- 柜组数
- 本期有销售柜组数
- 同期有销售柜组数

### 7.2 排名规则

用于识别重点柜组：

- 本期销售 TOP
- 销售增长金额 TOP
- 销售下滑金额 TOP
- 毛利 TOP
- 低毛利率 TOP
- 小票数下降 TOP

### 7.3 异常规则

#### R001 销售明显下滑

命中条件：

```text
same_period_effective_sales >= min_prior_sales_for_yoy
AND sales_yoy_rate <= large_decline_rate
```

默认严重级别：`high`

解释模板：

```text
{group_name} 本期销售 {effective_sales} 元，较同期 {same_period_effective_sales} 元下降 {sales_yoy_rate}，减少 {decline_impact} 元。
```

#### R002 销售异常增长

命中条件：

```text
same_period_effective_sales >= min_prior_sales_for_yoy
AND effective_sales >= min_sales_for_yoy
AND sales_yoy_rate >= large_growth_rate
```

默认严重级别：`medium`

用途：

- 识别活动拉动、统计口径变化、同期低基数之外的异常增长。

#### R003 同期有销售，本期无销售

命中条件：

```text
same_period_effective_sales >= min_prior_sales_for_yoy
AND effective_sales <= 0
```

默认严重级别：`critical`

用途：

- 识别停柜、撤场、未同步销售、柜组映射异常。

#### R004 本期有销售，同期无销售

命中条件：

```text
effective_sales >= min_sales_for_yoy
AND same_period_effective_sales <= 0
```

默认严重级别：`info`

用途：

- 识别新柜组、新品牌、去年同期无经营、柜组编码变化。

#### R005 毛利率过低

命中条件：

```text
effective_sales >= min_sales_for_yoy
AND ticket_margin < low_margin_rate
```

默认严重级别：`high`

用途：

- 识别低毛利经营、折扣过大、成本或毛利字段异常。

#### R006 毛利率明显下降

命中条件：

```text
effective_sales >= min_sales_for_yoy
AND same_period_effective_sales >= min_prior_sales_for_yoy
AND margin_delta_pp <= margin_drop_pp
```

默认严重级别：`medium`

用途：

- 识别销售结构变化、折扣加深、成本变化。

#### R007 销售增长但毛利率下降

命中条件：

```text
sales_yoy_rate > 0
AND margin_delta_pp <= margin_drop_pp
AND effective_sales >= min_sales_for_yoy
```

默认严重级别：`medium`

用途：

- 识别销售靠促销拉动但利润质量变差。

#### R008 高销售低毛利

命中条件：

```text
sales_share >= high_sales_share
AND ticket_margin < high_sales_low_margin_rate
```

默认严重级别：`high`

用途：

- 识别对总体销售贡献大但利润质量偏低的柜组。

#### R009 小票数明显下降

命中条件：

```text
same_period_ticket_count > 0
AND ticket_yoy_rate <= ticket_decline_rate
AND same_period_effective_sales >= min_prior_sales_for_yoy
```

默认严重级别：`medium`

用途：

- 识别客流、成交笔数、开单状态变化。

## 8. 严重级别

| 级别 | 含义 | 前端建议 |
| --- | --- | --- |
| `critical` | 需要优先核查，可能是经营中断或数据口径问题 | 红色强调 |
| `high` | 明显经营异常，需要重点关注 | 红色 |
| `medium` | 值得复盘的变化 | 黄色或橙色 |
| `info` | 解释性信息，不一定是坏事 | 蓝色或灰色 |

同一柜组可命中多条规则。前端展示时按严重级别和金额影响排序。

## 9. 返回结构

建议接口返回：

```json
{
  "scope": {
    "level": "groups",
    "start_date": "2026-05-07",
    "end_date": "2026-05-07",
    "prior_start_date": "2025-05-07",
    "prior_end_date": "2025-05-07",
    "store_id": null,
    "department_code": null
  },
  "summary": {
    "group_count": 21,
    "active_group_count": 21,
    "sales": 267778,
    "prior_sales": 0,
    "sales_delta": 267778,
    "sales_yoy_rate": null,
    "net_profit": 29087,
    "prior_net_profit": 0,
    "margin": 0.1086,
    "prior_margin": 0,
    "ticket_count": 50,
    "prior_ticket_count": 0
  },
  "rankings": {
    "top_sales": [],
    "top_growth": [],
    "top_decline": [],
    "low_margin": [],
    "ticket_decline": []
  },
  "anomalies": [
    {
      "rule_id": "R001",
      "severity": "high",
      "group_code": "6010101036",
      "group_name": "Rolex劳力士厅",
      "title": "销售明显下滑",
      "message": "Rolex劳力士厅本期销售 91,200 元，较同期 233,900 元下降 61.01%，减少 142,700 元。",
      "metrics": {
        "effective_sales": 91200,
        "same_period_effective_sales": 233900,
        "sales_yoy_rate": -0.6101,
        "decline_impact": 142700
      },
      "thresholds": {
        "large_decline_rate": -0.3,
        "min_prior_sales_for_yoy": 1000
      }
    }
  ],
  "actions": [
    {
      "priority": "high",
      "title": "优先复盘销售下滑金额最大的柜组",
      "description": "检查活动、客流、库存、柜组映射和同期口径是否变化。",
      "related_rule_ids": ["R001", "R003"]
    }
  ],
  "ai": {
    "enabled": true,
    "status": "success",
    "report": "本期柜组销售主要由若干头部柜组贡献..."
  }
}
```

AI 失败时：

```json
{
  "ai": {
    "enabled": true,
    "status": "failed",
    "error": "AI 服务暂不可用，已返回规则分析结果。",
    "report": null
  }
}
```

## 10. AI 输入约束

传给 AI 的数据只包含：

- 分析范围
- 汇总指标
- TOP 排名
- 异常项
- 建议动作草稿

不传：

- 会员号
- 支付流水
- 完整小票明细
- 商品明细
- 原始 SQL
- 用户权限策略详情

AI 提示词目标：

```text
你是百货商场销售经营分析助手。
请基于结构化规则结果，生成一份面向门店/营运人员的销售分析。
不要编造数据，不要推断未提供的原因。
输出分为：核心结论、重点异常、可能原因线索、建议动作。
```

### 10.1 AI 模型配置

第一版后端 AI 供应商通过环境变量配置，后续如果需要后台页面维护，可把同一组字段迁移到数据库配置表。

通用配置：

| 环境变量 | 说明 |
| --- | --- |
| `SALES_ANALYSIS_AI_PROVIDER` | AI 供应商，支持 `openai`、`minimax`、`openai_compatible` |
| `SALES_ANALYSIS_AI_API_KEY` | 通用 API Key，优先级高于供应商专用 Key |
| `SALES_ANALYSIS_AI_MODEL` | 通用模型名，优先级高于供应商专用模型名 |
| `SALES_ANALYSIS_AI_BASE_URL` | 通用 API Base URL |
| `SALES_ANALYSIS_AI_API_STYLE` | OpenAI 默认 `responses`；兼容接口可用 `chat_completions` |
| `SALES_ANALYSIS_AI_TIMEOUT_SECONDS` | 请求超时时间，默认 30 秒 |
| `SALES_ANALYSIS_AI_MAX_OUTPUT_TOKENS` | 最大输出 token，默认 1200 |

OpenAI 配置示例：

```bash
SALES_ANALYSIS_AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5-mini
```

MiniMax 配置示例：

```bash
SALES_ANALYSIS_AI_PROVIDER=minimax
MINIMAX_API_KEY=...
MINIMAX_MODEL=MiniMax-M2.7
MINIMAX_BASE_URL=https://api.minimax.io/v1
```

OpenAI 兼容接口配置示例：

```bash
SALES_ANALYSIS_AI_PROVIDER=openai_compatible
SALES_ANALYSIS_AI_API_KEY=...
SALES_ANALYSIS_AI_MODEL=your-model
SALES_ANALYSIS_AI_BASE_URL=https://your-provider.example.com/v1
```

降级规则：

- 未配置 API Key：返回 `ai.status = not_configured`
- AI 调用失败：返回 `ai.status = failed`
- 以上两种情况都不影响 `summary`、`rankings`、`anomalies`、`actions` 返回

## 11. 后端模块设计

建议新增：

```text
python_app/services/sales_analysis/
  __init__.py
  config.py
  metrics.py
  rules.py
  engine.py
  ai_report.py
```

职责：

| 文件 | 职责 |
| --- | --- |
| `config.py` | 默认阈值和规则启停配置 |
| `metrics.py` | 派生指标计算 |
| `rules.py` | 规则定义和规则命中逻辑 |
| `engine.py` | 编排指标、规则、排名、行动建议 |
| `ai_report.py` | 调用 AI 生成经营报告 |

`python_app/routers/sales.py` 中新增 `/analysis` 路由，负责：

- 校验权限
- 接收筛选条件
- 拉取柜组汇总数据
- 调用分析引擎
- 返回结果

## 12. 前端展示设计

入口：

- 销售看板顶部增加 `AI 分析` 按钮
- 或在 `柜组销售汇总` 卡片标题右侧增加 `AI 分析`

第一版推荐放在 `柜组销售汇总` 卡片右侧，因为第一版只支持柜组分析。

展示结构：

- 分析范围
- 核心指标摘要
- AI 经营报告
- 异常柜组列表
- 排名列表
- 建议动作

交互：

- 点击异常柜组可定位或筛选对应柜组
- 支持重新生成
- AI 失败时仍展示规则分析

## 13. 实施顺序

1. 新增规则库设计文档。
2. 新增后端规则配置、指标计算和规则引擎。
3. 在后端新增 `/api/sales/analysis`，先返回规则结果。
4. 接入 AI 文案生成，失败时降级为规则结果。
5. 前端增加 `AI 分析` 按钮和结果弹窗。
6. 用当前截图里的柜组数据验证异常命中。
7. 再根据实际经营反馈微调阈值。

## 14. 验收标准

- 只分析当前用户权限范围内的柜组。
- 前端切换日期、同期日期、门店、部门后，分析范围同步变化。
- 销售明显下滑、销售异常增长、低毛利、毛利率下降等规则可命中。
- 每条异常都能解释命中原因和阈值。
- AI 不可用时，规则分析结果仍可正常展示。
- 分析结果中不包含敏感小票、会员、支付明细。
