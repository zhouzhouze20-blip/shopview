import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Loader2, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import { apiGet, apiPost } from "@/lib/api";
import { cn } from "@/lib/utils";

type RowData = Record<string, number | string | null>;
type TableColumn = [string, string, ((value: unknown) => string)?, ((row: RowData) => ReactNode)?];

const money = (value: unknown) =>
  new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 0 }).format(Number(value || 0));

const number = (value: unknown) => new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(Number(value || 0));

const fmtDate = (value: unknown) => (typeof value === "string" && value ? value.slice(0, 10) : "—");
const fmtDateTime = (value: unknown) => (typeof value === "string" && value ? value.replace("T", " ").slice(0, 19) : "—");

const toNumber = (value: unknown) => {
  const n = Number(value || 0);
  return Number.isFinite(n) ? n : 0;
};

function localDateString(date = new Date()) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function buildQuery(params: Record<string, string | number | boolean | undefined | null>) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    qs.set(key, String(value));
  });
  const s = qs.toString();
  return s ? `?${s}` : "";
}

const errorText = (error: unknown) => (error instanceof Error ? error.message : "请求失败");

const storeName = (code: unknown) => {
  const value = String(code || "");
  if (value === "601" || value === "101") return "购物中心";
  if (value === "602" || value === "102") return "百货大楼";
  if (value === "603" || value === "105") return "新世纪";
  if (value === "604" || value === "1084") return "半山";
  return value || "—";
};

export default function VoucherMatchPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [startDate, setStartDate] = useState(() => localDateString());
  const [endDate, setEndDate] = useState("");
  const [storeCode, setStoreCode] = useState("all");
  const [manualRow, setManualRow] = useState<RowData | null>(null);
  const [manualKeyword, setManualKeyword] = useState("");
  const [manualTolerance, setManualTolerance] = useState("5000");

  const voucherMatchQuery = useQuery<RowData[]>({
    queryKey: ["/api/activity-analysis/voucher-match-candidates", startDate, endDate, storeCode],
    queryFn: () =>
      apiGet(
        `/api/activity-analysis/voucher-match-candidates${buildQuery({
          scope: "all",
          start_date: startDate,
          end_date: endDate,
          store_code: storeCode === "all" ? "" : storeCode,
          limit: 500,
        })}`,
      ),
  });

  const saveVoucherMatchesMutation = useMutation({
    mutationFn: (body: { confirm_status: "AUTO_CONFIRMED" | "MANUAL_CONFIRMED" | "REJECTED"; rows: RowData[] }) =>
      apiPost<{ saved: number; skipped: number }>("/api/activity-analysis/voucher-matches", {
        confirm_status: body.confirm_status,
        rows: body.rows.map(toVoucherMatchPayload),
      }),
    onSuccess: (result) => {
      toast({ title: "匹配确认已保存", description: `保存 ${result.saved} 行，跳过 ${result.skipped} 行` });
      queryClient.invalidateQueries({ queryKey: ["/api/activity-analysis/voucher-match-candidates"] });
      voucherMatchQuery.refetch();
    },
    onError: (error: Error) => {
      toast({ title: "保存匹配失败", description: error.message, variant: "destructive" });
    },
  });

  const rows = voucherMatchQuery.data || [];
  const summary = useMemo(() => buildSummary(rows), [rows]);
  const storeSummaryRows = useMemo(() => buildStoreSummary(rows), [rows]);
  const manualVoucherQuery = useQuery<RowData[]>({
    queryKey: [
      "/api/activity-analysis/voucher-details",
      manualRow?.business_date,
      manualRow?.market_code,
      manualRow?.coupon_type,
      manualRow?.match_type,
      manualRow?.business_amount,
      manualKeyword,
      manualTolerance,
    ],
    queryFn: () =>
      apiGet(
        `/api/activity-analysis/voucher-details${buildQuery({
          start_date: String(manualRow?.business_date || ""),
          end_date: String(manualRow?.business_date || ""),
          store_code: String(manualRow?.market_code || ""),
          coupon_type: String(manualRow?.coupon_type || ""),
          strict_coupon_type: false,
          match_type: String(manualRow?.match_type || "DEBIT_USE"),
          amount: toNumber(manualRow?.business_amount),
          amount_tolerance: Number(manualTolerance || 0),
          valuename: "企划部",
          keyword: manualKeyword,
          limit: 100,
        })}`,
      ),
    enabled: !!manualRow,
  });

  const confirmStrong = () => {
    const strongRows = rows.filter((row) => row.match_status === "AUTO_STRONG" && row.confirm_status !== "AUTO_CONFIRMED" && row.voucher_detail_id);
    if (strongRows.length === 0) {
      toast({ title: "没有待确认的强匹配" });
      return;
    }
    saveVoucherMatchesMutation.mutate({ confirm_status: "AUTO_CONFIRMED", rows: strongRows });
  };

  return (
    <div className="space-y-5 p-4 sm:p-6">
      <div className="max-w-3xl">
        <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">凭证匹配</h1>
        <p className="mt-1 text-sm text-muted-foreground">按业务卡券门店、凭证摘要门店和财务主体核对卡券使用与财务凭证。</p>
      </div>

      <Card className="rounded-lg">
        <CardContent className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-5 lg:items-end">
          <div className="min-w-0">
            <Label htmlFor="voucher-match-start">开始日期</Label>
            <Input id="voucher-match-start" className="mt-1" type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
          </div>
          <div className="min-w-0">
            <Label htmlFor="voucher-match-end">结束日期</Label>
            <Input id="voucher-match-end" className="mt-1" type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
          </div>
          <div className="min-w-0">
            <Label>门店</Label>
            <Select value={storeCode} onValueChange={setStoreCode}>
              <SelectTrigger className="mt-1 w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部门店</SelectItem>
                <SelectItem value="601">601 购物中心</SelectItem>
                <SelectItem value="602">602 百货大楼</SelectItem>
                <SelectItem value="603">603 新世纪</SelectItem>
                <SelectItem value="604">604 半山</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button variant="outline" onClick={() => voucherMatchQuery.refetch()} disabled={voucherMatchQuery.isFetching}>
            {voucherMatchQuery.isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            刷新
          </Button>
        </CardContent>
      </Card>

      <Card className="rounded-lg">
        <CardContent className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-8 lg:items-end">
          <SummaryBox label="业务汇总行" value={number(summary.total)} />
          <SummaryBox label="强匹配" value={number(summary.strong)} />
          <SummaryBox label="无候选" value={number(summary.missing)} />
          <SummaryBox label="已确认" value={number(summary.confirmed)} />
          <SummaryBox label="业务金额" value={money(summary.businessAmount)} />
          <SummaryBox label="凭证金额" value={money(summary.voucherAmount)} />
          <SummaryBox label="差额" value={money(summary.businessAmount - summary.voucherAmount)} />
          <Button variant="outline" onClick={confirmStrong} disabled={saveVoucherMatchesMutation.isPending || voucherMatchQuery.isFetching}>
            {saveVoucherMatchesMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            一键确认强匹配
          </Button>
        </CardContent>
      </Card>

      <SimpleTable
        rows={storeSummaryRows}
        columns={[
          ["business_store", "卡券业务门店"],
          ["voucher_store", "凭证摘要门店"],
          ["voucher_corp_name", "凭证财务主体"],
          ["row_count", "行数", number],
          ["strong_count", "强匹配", number],
          ["confirmed_count", "已确认", number],
          ["business_amount", "业务金额", money],
          ["voucher_amount", "凭证金额", money],
          ["diff_amount", "差额", money],
        ]}
      />

      <ManualVoucherDialog
        row={manualRow}
        open={!!manualRow}
        keyword={manualKeyword}
        tolerance={manualTolerance}
        vouchers={manualVoucherQuery.data || []}
        loading={manualVoucherQuery.isFetching}
        error={manualVoucherQuery.error}
        saving={saveVoucherMatchesMutation.isPending}
        onKeywordChange={setManualKeyword}
        onToleranceChange={setManualTolerance}
        onSearch={() => manualVoucherQuery.refetch()}
        onOpenChange={(open) => {
          if (!open) {
            setManualRow(null);
            setManualKeyword("");
            setManualTolerance("5000");
          }
        }}
        onSelect={(voucher) => {
          if (!manualRow) return;
          saveVoucherMatchesMutation.mutate({
            confirm_status: "MANUAL_CONFIRMED",
            rows: [mergeManualVoucher(manualRow, voucher)],
          });
          setManualRow(null);
          setManualKeyword("");
          setManualTolerance("5000");
        }}
      />

      {voucherMatchQuery.isError ? (
        <ErrorCard message={errorText(voucherMatchQuery.error)} />
      ) : (
        <SimpleTable
          rows={rows}
          columns={[
            ["match_status", "状态", undefined, (row) => <MatchStatusBadge status={String(row.match_status || "")} />],
            ["confirm_status", "确认", undefined, (row) => <ConfirmStatusBadge status={String(row.confirm_status || "UNCONFIRMED")} />],
            [
              "__actions",
              "操作",
              undefined,
              (row) => (
                <div className="flex gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={!row.voucher_detail_id || saveVoucherMatchesMutation.isPending}
                    onClick={() =>
                      saveVoucherMatchesMutation.mutate({
                        confirm_status: row.match_status === "AUTO_STRONG" ? "AUTO_CONFIRMED" : "MANUAL_CONFIRMED",
                        rows: [row],
                      })
                    }
                  >
                    确认
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={saveVoucherMatchesMutation.isPending}
                    onClick={() => {
                      setManualRow(row);
                      setManualKeyword("");
                      setManualTolerance("5000");
                    }}
                  >
                    手工选择
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={!row.voucher_detail_id || saveVoucherMatchesMutation.isPending}
                    onClick={() => saveVoucherMatchesMutation.mutate({ confirm_status: "REJECTED", rows: [row] })}
                  >
                    排除
                  </Button>
                </div>
              ),
            ],
            ["business_date", "业务日期", fmtDate],
            ["market_code", "卡券门店码"],
            ["market_code", "卡券业务门店", storeName],
            ["business_store_code", "应匹配凭证门店"],
            ["voucher_store_code", "凭证摘要门店"],
            ["voucher_store_code", "凭证摘要门店名", storeName],
            ["voucher_corp_code", "凭证主体编码"],
            ["voucher_corp_name", "凭证财务主体"],
            ["coupon_type", "券字母"],
            ["voucher_coupon_type", "摘要券码"],
            ["coupon_name", "券名称"],
            ["match_type_name", "匹配方向"],
            ["business_amount", "业务金额", money],
            ["voucher_amount", "凭证金额", money],
            ["amount_diff", "差额", money],
            ["match_score", "分数", number],
            ["flow_count", "流水数", number],
            ["member_count", "会员数", number],
            ["voucher_business_date", "凭证日期", fmtDate],
            ["pk_voucher", "凭证主键"],
            ["pk_detail", "源明细键"],
            ["voucher_detail_id", "明细ID"],
            ["confirmed_by_name", "确认人"],
            ["confirmed_at", "确认时间", fmtDateTime],
            ["valuename", "辅助核算"],
            ["explanation", "凭证摘要"],
            ["debit_amount", "借方", money],
            ["credit_amount", "贷方", money],
          ]}
        />
      )}
    </div>
  );
}

function buildSummary(rows: RowData[]) {
  return {
    total: rows.length,
    strong: rows.filter((row) => row.match_status === "AUTO_STRONG").length,
    missing: rows.filter((row) => row.match_status === "NO_CANDIDATE").length,
    confirmed: rows.filter((row) => row.confirm_status === "AUTO_CONFIRMED" || row.confirm_status === "MANUAL_CONFIRMED").length,
    businessAmount: rows.reduce((sum, row) => sum + toNumber(row.business_amount), 0),
    voucherAmount: rows.reduce((sum, row) => sum + toNumber(row.voucher_amount), 0),
  };
}

function buildStoreSummary(rows: RowData[]) {
  const map = new Map<string, RowData>();
  rows.forEach((row) => {
    const businessStore = `${row.market_code || "—"} ${storeName(row.market_code)}`;
    const voucherStore = `${row.voucher_store_code || "—"} ${storeName(row.voucher_store_code)}`;
    const corpName = String(row.voucher_corp_name || "无凭证主体");
    const key = `${businessStore}|${voucherStore}|${corpName}`;
    const current = map.get(key) || {
      business_store: businessStore,
      voucher_store: voucherStore,
      voucher_corp_name: corpName,
      row_count: 0,
      strong_count: 0,
      confirmed_count: 0,
      business_amount: 0,
      voucher_amount: 0,
      diff_amount: 0,
    };
    current.row_count = toNumber(current.row_count) + 1;
    current.strong_count = toNumber(current.strong_count) + (row.match_status === "AUTO_STRONG" ? 1 : 0);
    current.confirmed_count =
      toNumber(current.confirmed_count) + (row.confirm_status === "AUTO_CONFIRMED" || row.confirm_status === "MANUAL_CONFIRMED" ? 1 : 0);
    current.business_amount = toNumber(current.business_amount) + toNumber(row.business_amount);
    current.voucher_amount = toNumber(current.voucher_amount) + toNumber(row.voucher_amount);
    current.diff_amount = toNumber(current.business_amount) - toNumber(current.voucher_amount);
    map.set(key, current);
  });
  return Array.from(map.values()).sort((a, b) => Math.abs(toNumber(b.diff_amount)) - Math.abs(toNumber(a.diff_amount)));
}

function SummaryBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold tabular-nums">{value}</p>
    </div>
  );
}

function ManualVoucherDialog({
  row,
  open,
  keyword,
  tolerance,
  vouchers,
  loading,
  error,
  saving,
  onKeywordChange,
  onToleranceChange,
  onSearch,
  onOpenChange,
  onSelect,
}: {
  row: RowData | null;
  open: boolean;
  keyword: string;
  tolerance: string;
  vouchers: RowData[];
  loading: boolean;
  error: unknown;
  saving: boolean;
  onKeywordChange: (value: string) => void;
  onToleranceChange: (value: string) => void;
  onSearch: () => void;
  onOpenChange: (open: boolean) => void;
  onSelect: (voucher: RowData) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="h-[88vh] max-h-[88vh] w-[94vw] max-w-[94vw] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>手工选择凭证</DialogTitle>
        </DialogHeader>
        {row ? (
          <div className="space-y-4">
            <div className="grid gap-3 rounded-md border p-3 text-sm sm:grid-cols-2 lg:grid-cols-5">
              <SummaryBox label="业务日期" value={fmtDate(row.business_date)} />
              <SummaryBox label="门店" value={`${String(row.market_code || "—")} ${storeName(row.market_code)}`} />
              <SummaryBox label="参考券字母" value={String(row.coupon_type || "—")} />
              <SummaryBox label="匹配方向" value={String(row.match_type_name || "—")} />
              <SummaryBox label="业务金额" value={money(row.business_amount)} />
            </div>
            <Card className="rounded-lg">
              <CardContent className="grid gap-3 p-4 sm:grid-cols-3 lg:grid-cols-5 lg:items-end">
                <div className="min-w-0 sm:col-span-2">
                  <Label htmlFor="manual-voucher-keyword">摘要搜索</Label>
                  <Input
                    id="manual-voucher-keyword"
                    className="mt-1"
                    value={keyword}
                    onChange={(event) => onKeywordChange(event.target.value)}
                    placeholder="摘要、凭证主键、辅助核算"
                  />
                </div>
                <div className="min-w-0">
                  <Label htmlFor="manual-voucher-tolerance">金额范围</Label>
                  <Input
                    id="manual-voucher-tolerance"
                    className="mt-1"
                    type="number"
                    min="0"
                    value={tolerance}
                    onChange={(event) => onToleranceChange(event.target.value)}
                  />
                </div>
                <Button type="button" variant="outline" onClick={onSearch} disabled={loading}>
                  {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
                  查询凭证
                </Button>
              </CardContent>
            </Card>
            {error ? (
              <ErrorCard message={errorText(error)} />
            ) : (
              <SimpleTable
                rows={vouchers}
                columns={[
                  [
                    "__select",
                    "选择",
                    undefined,
                    (voucher) => (
                      <Button type="button" size="sm" variant="outline" disabled={saving} onClick={() => onSelect(voucher)}>
                        选中
                      </Button>
                    ),
                  ],
                  ["voucher_business_date", "凭证日期", fmtDate],
                  ["voucher_store_code", "摘要门店"],
                  ["voucher_corp_name", "凭证主体"],
                  ["voucher_coupon_type", "摘要券码"],
                  ["voucher_amount", "凭证金额", money],
                  ["amount_diff", "与业务差额", money],
                  ["pk_voucher", "凭证主键"],
                  ["pk_detail", "源明细键"],
                  ["voucher_detail_id", "明细ID"],
                  ["valuename", "辅助核算"],
                  ["explanation", "凭证摘要"],
                  ["debit_amount", "借方", money],
                  ["credit_amount", "贷方", money],
                ]}
              />
            )}
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

function ErrorCard({ message }: { message: string }) {
  return (
    <Card className="rounded-lg border-red-200 bg-red-50">
      <CardContent className="flex items-start gap-2 p-4 text-sm text-red-700">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
        <span>{message}</span>
      </CardContent>
    </Card>
  );
}

function MatchStatusBadge({ status }: { status: string }) {
  const meta: Record<string, { label: string; className: string }> = {
    AUTO_STRONG: { label: "强匹配", className: "border-emerald-200 bg-emerald-50 text-emerald-700" },
    AUTO_CANDIDATE: { label: "候选", className: "border-blue-200 bg-blue-50 text-blue-700" },
    REVIEW: { label: "复核", className: "border-amber-200 bg-amber-50 text-amber-700" },
    NO_CANDIDATE: { label: "无候选", className: "border-slate-200 bg-slate-50 text-slate-600" },
  };
  const current = meta[status] || { label: status || "未知", className: "border-slate-200 bg-slate-50 text-slate-600" };
  return (
    <Badge variant="outline" className={cn("whitespace-nowrap", current.className)}>
      {current.label}
    </Badge>
  );
}

function ConfirmStatusBadge({ status }: { status: string }) {
  const meta: Record<string, { label: string; className: string }> = {
    AUTO_CONFIRMED: { label: "自动已确认", className: "border-emerald-200 bg-emerald-50 text-emerald-700" },
    MANUAL_CONFIRMED: { label: "人工已确认", className: "border-blue-200 bg-blue-50 text-blue-700" },
    REJECTED: { label: "已排除", className: "border-red-200 bg-red-50 text-red-700" },
    UNCONFIRMED: { label: "未确认", className: "border-slate-200 bg-slate-50 text-slate-600" },
  };
  const current = meta[status] || { label: status || "未确认", className: "border-slate-200 bg-slate-50 text-slate-600" };
  return (
    <Badge variant="outline" className={cn("whitespace-nowrap", current.className)}>
      {current.label}
    </Badge>
  );
}

function toVoucherMatchPayload(row: RowData) {
  return {
    business_date: String(row.business_date || ""),
    market_code: row.market_code ? String(row.market_code) : null,
    business_store_code: row.business_store_code ? String(row.business_store_code) : null,
    coupon_type: String(row.coupon_type || ""),
    coupon_name: row.coupon_name ? String(row.coupon_name) : null,
    match_type: String(row.match_type || ""),
    match_type_name: row.match_type_name ? String(row.match_type_name) : null,
    business_amount: toNumber(row.business_amount),
    flow_count: Math.trunc(toNumber(row.flow_count)),
    member_count: Math.trunc(toNumber(row.member_count)),
    voucher_detail_id: String(row.voucher_detail_id || ""),
    voucher_amount: toNumber(row.voucher_amount),
    amount_diff: toNumber(row.amount_diff),
    match_score: Math.trunc(toNumber(row.match_score)),
    match_status: String(row.match_status || ""),
  };
}

function mergeManualVoucher(row: RowData, voucher: RowData): RowData {
  const voucherAmount = toNumber(voucher.voucher_amount);
  const businessAmount = toNumber(row.business_amount);
  return {
    ...row,
    voucher_detail_id: String(voucher.voucher_detail_id || ""),
    voucher_amount: voucherAmount,
    amount_diff: voucherAmount - businessAmount,
    match_score: 0,
    match_status: "MANUAL_SELECTED",
  };
}

function SimpleTable({
  rows,
  columns,
}: {
  rows: Array<Record<string, unknown>>;
  columns: TableColumn[];
}) {
  return (
    <Card className="rounded-lg">
      <CardContent className="overflow-hidden p-0">
        <div className="w-full overflow-x-auto">
          <Table className="min-w-max">
            <TableHeader>
              <TableRow>
                {columns.map(([key, label, formatter]) => (
                  <TableHead key={`${key}-${label}`} className={isNumericFormatter(formatter) ? "whitespace-nowrap text-right" : "whitespace-nowrap"}>
                    {label}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={columns.length} className="py-10 text-center text-muted-foreground">
                    暂无数据
                  </TableCell>
                </TableRow>
              ) : (
                rows.map((row, index) => (
                  <TableRow key={index}>
                    {columns.map(([key, label, formatter, render]) => (
                      <TableCell
                        key={`${key}-${label}`}
                        className={cn(
                          "whitespace-nowrap",
                          isNumericFormatter(formatter) || typeof row[key] === "number" ? "text-right tabular-nums" : "",
                        )}
                      >
                        {render ? render(row as RowData) : formatter ? formatter(row[key]) : String(row[key] ?? "—")}
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

function isNumericFormatter(formatter?: (value: unknown) => string) {
  return formatter === money || formatter === number;
}
