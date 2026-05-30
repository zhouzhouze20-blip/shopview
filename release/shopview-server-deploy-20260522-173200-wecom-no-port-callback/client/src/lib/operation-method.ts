const OPERATION_METHOD_LABELS: Record<string, string> = {
  "1": "经销",
  "2": "成本代销",
  "3": "扣率代销",
  "4": "联营",
  "5": "租赁",
  经销: "经销",
  成本代销: "成本代销",
  扣率代销: "扣率代销",
  联营: "联营",
  租赁: "租赁",
  自营: "经销",
  非租赁: "联营",
  空厅: "空置",
  空置: "空置",
};

export function formatOperationMethod(value?: string | number | null) {
  if (value == null) return "-";
  const normalized = String(value).trim();
  if (!normalized) return "-";
  return OPERATION_METHOD_LABELS[normalized] ?? normalized;
}
