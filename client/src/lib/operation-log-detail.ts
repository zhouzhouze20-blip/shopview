const conditionLabels: Record<string, string> = {
  start_date: "开始日期",
  end_date: "结束日期",
  prior_start_date: "同期开始",
  prior_end_date: "同期结束",
  query_level: "查询层级",
  query_type: "查询类型",
  detail_type: "明细类型",
  keyword: "关键词",
  store_id: "门店ID",
  store_code: "门店编码",
  store_name: "门店",
  department_code: "部门编码",
  department_name: "部门",
  group_code: "柜组编码",
  group_name: "柜组",
  supplier_code: "供应商编码",
  supplier_name: "供应商",
  goods_code: "商品编码",
  barcode: "商品条码",
  contract_no: "合同号",
  ticket_no: "小票号",
  bill_no: "内部小票号",
  navigation_action: "页面动作",
  from_level: "返回前层级",
  to_level: "返回后层级",
  page: "页码",
  exclude_rental: "排除租赁销售",
  exclude_backoffice_departments: "排除后台部门销售",
  unassigned_department: "未归属部门",
  filter_action: "筛选动作",
  view_mode: "查看期间",
  preset_days: "快捷天数",
  refresh: "刷新查询",
};

const levelLabels: Record<string, string> = {
  stores: "门店汇总",
  departments: "部门汇总",
  groups: "柜组汇总",
  goods: "商品明细",
  suppliers: "供应商汇总",
  tickets: "小票明细",
  detail: "详情",
};

const queryTypeLabels: Record<string, string> = {
  sales: "销售看板",
  product_inventory: "单品库存",
  supplier_inventory: "供应商库存",
  group_inventory: "柜组库存",
  contract: "合同台账",
  revenue: "收益看板",
};

function displayValue(key: string, value: unknown): string {
  if (Array.isArray(value)) return value.map(String).join("、");
  if (typeof value === "boolean") return value ? "是" : "否";
  if (key === "query_level") return levelLabels[String(value)] || String(value);
  if (key === "query_type") return queryTypeLabels[String(value)] || String(value);
  if (key === "navigation_action" && String(value) === "back") return "返回上一级";
  if (key === "view_mode") return String(value) === "prior" ? "上年同期" : "本期";
  if (key === "from_level" || key === "to_level") return levelLabels[String(value)] || String(value);
  return String(value);
}

export function formatOperationQueryConditions(detail?: Record<string, unknown> | null): string {
  const conditions = detail?.query_conditions;
  if (!conditions || typeof conditions !== "object" || Array.isArray(conditions)) return "-";

  const parts = Object.entries(conditions as Record<string, unknown>)
    .filter(([, value]) => value !== null && value !== undefined && String(value).trim() !== "")
    .map(([key, value]) => `${conditionLabels[key] || key}：${displayValue(key, value)}`);
  return parts.length ? parts.join("；") : "-";
}
