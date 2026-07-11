import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Loader2, RefreshCw, Save, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { apiGet, apiPost } from "@/lib/api";
import { cn } from "@/lib/utils";

type BalanceRow = {
  id: number;
  period_month: string;
  market_code: string;
  coupon_type: string;
  coupon_name: string | null;
  opening_balance: number;
  current_month_increase: number;
  current_month_decrease: number;
  nc_carryover_amount: number;
  ending_balance: number;
  missing_rate_count: number;
  movement_count: number;
  status: "DRAFT" | "CONFIRMED";
  confirmed_by_name: string | null;
  confirmed_at: string | null;
};

const money = (value: unknown) =>
  new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 2 }).format(Number(value || 0));

const number = (value: unknown) => new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 0 }).format(Number(value || 0));

const fmtDateTime = (value: unknown) => (typeof value === "string" && value ? value.replace("T", " ").slice(0, 19) : "—");

function currentMonthString(date = new Date()) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
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

const storeName = (code: unknown) => {
  const value = String(code || "");
  if (value === "601") return "购物中心";
  if (value === "602") return "百货大楼";
  if (value === "603") return "新世纪";
  if (value === "604") return "半山";
  return value || "—";
};

const errorText = (error: unknown) => (error instanceof Error ? error.message : "请求失败");

export default function CouponMonthlyBalancePage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [periodMonth, setPeriodMonth] = useState(() => currentMonthString());
  const [storeCode, setStoreCode] = useState("all");
  const [carryoverRow, setCarryoverRow] = useState<BalanceRow | null>(null);
  const [ncVoucherNo, setNcVoucherNo] = useState("");
  const [carryoverAmount, setCarryoverAmount] = useState("");
  const [carryoverDate, setCarryoverDate] = useState("");
  const [remark, setRemark] = useState("");

  const commonBody = {
    period_month: periodMonth,
    market_code: storeCode === "all" ? null : storeCode,
  };

  const balancesQuery = useQuery<BalanceRow[]>({
    queryKey: ["/api/activity-analysis/coupon-monthly-balances", periodMonth, storeCode],
    queryFn: () =>
      apiGet(
        `/api/activity-analysis/coupon-monthly-balances${buildQuery({
          period_month: periodMonth,
          market_code: storeCode === "all" ? "" : storeCode,
        })}`,
      ),
  });

  const invalidateBalances = () => {
    queryClient.invalidateQueries({ queryKey: ["/api/activity-analysis/coupon-monthly-balances"] });
    balancesQuery.refetch();
  };

  const rebuildMovementsMutation = useMutation({
    mutationFn: () => apiPost<{ rebuilt: number }>("/api/activity-analysis/coupon-revenue-movements/rebuild", commonBody),
    onSuccess: (result) => {
      toast({ title: "每日变动已刷新", description: `处理 ${number(result.rebuilt)} 行` });
    },
    onError: (error: Error) => toast({ title: "刷新每日变动失败", description: error.message, variant: "destructive" }),
  });

  const rebuildBalancesMutation = useMutation({
    mutationFn: () => apiPost<{ rebuilt: number }>("/api/activity-analysis/coupon-monthly-balances/rebuild", commonBody),
    onSuccess: (result) => {
      toast({ title: "月结草稿已生成", description: `处理 ${number(result.rebuilt)} 行` });
      invalidateBalances();
    },
    onError: (error: Error) => toast({ title: "生成月结草稿失败", description: error.message, variant: "destructive" }),
  });

  const confirmBalancesMutation = useMutation({
    mutationFn: () => apiPost<{ confirmed: number }>("/api/activity-analysis/coupon-monthly-balances/confirm", commonBody),
    onSuccess: (result) => {
      toast({ title: "月结已确认", description: `确认 ${number(result.confirmed)} 行` });
      invalidateBalances();
    },
    onError: (error: Error) => toast({ title: "确认月结失败", description: error.message, variant: "destructive" }),
  });

  const createCarryoverMutation = useMutation({
    mutationFn: () => {
      if (!carryoverRow) throw new Error("未选择月结行");
      return apiPost<{ saved: number }>("/api/activity-analysis/coupon-nc-carryovers", {
        period_month: periodMonth,
        market_code: carryoverRow.market_code,
        coupon_type: carryoverRow.coupon_type,
        coupon_name: carryoverRow.coupon_name,
        nc_voucher_no: ncVoucherNo,
        carryover_amount: Number(carryoverAmount || 0),
        carryover_date: carryoverDate || null,
        remark: remark || null,
      });
    },
    onSuccess: () => {
      toast({ title: "NC 结转已登记" });
      setCarryoverRow(null);
      setNcVoucherNo("");
      setCarryoverAmount("");
      setCarryoverDate("");
      setRemark("");
      rebuildBalancesMutation.mutate();
    },
    onError: (error: Error) => toast({ title: "登记 NC 结转失败", description: error.message, variant: "destructive" }),
  });

  const rows = balancesQuery.data || [];
  const summary = useMemo(() => buildSummary(rows), [rows]);
  const busy =
    rebuildMovementsMutation.isPending || rebuildBalancesMutation.isPending || confirmBalancesMutation.isPending || createCarryoverMutation.isPending;
  const hasMissingRate = rows.some((row) => Number(row.missing_rate_count || 0) > 0);
  const hasDraftRows = rows.some((row) => row.status === "DRAFT");

  return (
    <div className="space-y-5 p-4 sm:p-6">
      <div className="max-w-3xl">
        <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">卡券月结</h1>
        <p className="mt-1 text-sm text-muted-foreground">按已确认凭证匹配、每日收入占比和 NC 手工结转登记计算门店券种月末余额。</p>
      </div>

      <Card className="rounded-lg">
        <CardContent className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-6 lg:items-end">
          <div className="min-w-0">
            <Label htmlFor="coupon-monthly-period">月份</Label>
            <Input id="coupon-monthly-period" className="mt-1" type="month" value={periodMonth} onChange={(event) => setPeriodMonth(event.target.value)} />
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
          <Button variant="outline" onClick={() => balancesQuery.refetch()} disabled={balancesQuery.isFetching || busy}>
            {balancesQuery.isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            刷新
          </Button>
          <Button variant="outline" onClick={() => rebuildMovementsMutation.mutate()} disabled={busy}>
            {rebuildMovementsMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            刷新每日变动
          </Button>
          <Button variant="outline" onClick={() => rebuildBalancesMutation.mutate()} disabled={busy}>
            {rebuildBalancesMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            生成草稿
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              if (window.confirm(`确认 ${periodMonth} 月结？确认后不能直接刷新覆盖。`)) {
                confirmBalancesMutation.mutate();
              }
            }}
            disabled={busy || !hasDraftRows || hasMissingRate}
          >
            {confirmBalancesMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ShieldCheck className="mr-2 h-4 w-4" />}
            确认月结
          </Button>
        </CardContent>
      </Card>

      <Card className="rounded-lg">
        <CardContent className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-6">
          <SummaryBox label="行数" value={number(summary.count)} />
          <SummaryBox label="本月增加" value={money(summary.increase)} />
          <SummaryBox label="本月减少" value={money(summary.decrease)} />
          <SummaryBox label="NC 结转" value={money(summary.carryover)} />
          <SummaryBox label="期末余额" value={money(summary.ending)} />
          <SummaryBox label="缺占比行" value={number(summary.missingRate)} danger={summary.missingRate > 0} />
        </CardContent>
      </Card>

      {balancesQuery.isError ? <ErrorCard message={errorText(balancesQuery.error)} /> : null}
      {hasMissingRate ? <ErrorCard message="存在缺收入占比的月结行，补齐每日门店券种收入占比后才能确认月结。" /> : null}

      <CarryoverDialog
        row={carryoverRow}
        ncVoucherNo={ncVoucherNo}
        carryoverAmount={carryoverAmount}
        carryoverDate={carryoverDate}
        remark={remark}
        saving={createCarryoverMutation.isPending}
        onOpenChange={(open) => {
          if (!open) setCarryoverRow(null);
        }}
        onNcVoucherNoChange={setNcVoucherNo}
        onCarryoverAmountChange={setCarryoverAmount}
        onCarryoverDateChange={setCarryoverDate}
        onRemarkChange={setRemark}
        onSubmit={() => createCarryoverMutation.mutate()}
      />

      <BalanceTable
        rows={rows}
        onCarryover={(row) => {
          setCarryoverRow(row);
          setNcVoucherNo("");
          setCarryoverAmount("");
          setCarryoverDate("");
          setRemark("");
        }}
      />
    </div>
  );
}

function buildSummary(rows: BalanceRow[]) {
  return rows.reduce(
    (summary, row) => ({
      count: summary.count + 1,
      increase: summary.increase + Number(row.current_month_increase || 0),
      decrease: summary.decrease + Number(row.current_month_decrease || 0),
      carryover: summary.carryover + Number(row.nc_carryover_amount || 0),
      ending: summary.ending + Number(row.ending_balance || 0),
      missingRate: summary.missingRate + Number(row.missing_rate_count || 0),
    }),
    { count: 0, increase: 0, decrease: 0, carryover: 0, ending: 0, missingRate: 0 },
  );
}

function SummaryBox({ label, value, danger = false }: { label: string; value: string; danger?: boolean }) {
  return (
    <div className={cn("rounded-md border p-3", danger ? "border-red-200 bg-red-50" : "")}>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={cn("mt-1 text-lg font-semibold tabular-nums", danger ? "text-red-700" : "")}>{value}</p>
    </div>
  );
}

function BalanceTable({ rows, onCarryover }: { rows: BalanceRow[]; onCarryover: (row: BalanceRow) => void }) {
  return (
    <Card className="rounded-lg">
      <CardContent className="overflow-hidden p-0">
        <div className="w-full overflow-x-auto">
          <Table className="min-w-max">
            <TableHeader>
              <TableRow>
                <TableHead>状态</TableHead>
                <TableHead>门店</TableHead>
                <TableHead>券字母</TableHead>
                <TableHead>券名称</TableHead>
                <TableHead className="text-right">上月余额</TableHead>
                <TableHead className="text-right">本月增加</TableHead>
                <TableHead className="text-right">本月减少</TableHead>
                <TableHead className="text-right">NC 结转</TableHead>
                <TableHead className="text-right">期末余额</TableHead>
                <TableHead className="text-right">缺占比</TableHead>
                <TableHead className="text-right">变动行</TableHead>
                <TableHead>确认人</TableHead>
                <TableHead>确认时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={14} className="py-10 text-center text-muted-foreground">
                    暂无月结数据
                  </TableCell>
                </TableRow>
              ) : (
                rows.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell>
                      <StatusBadge status={row.status} missingRate={Number(row.missing_rate_count || 0)} />
                    </TableCell>
                    <TableCell>{`${row.market_code} ${storeName(row.market_code)}`}</TableCell>
                    <TableCell>{row.coupon_type}</TableCell>
                    <TableCell>{row.coupon_name || "—"}</TableCell>
                    <TableCell className="text-right tabular-nums">{money(row.opening_balance)}</TableCell>
                    <TableCell className="text-right tabular-nums">{money(row.current_month_increase)}</TableCell>
                    <TableCell className="text-right tabular-nums">{money(row.current_month_decrease)}</TableCell>
                    <TableCell className="text-right tabular-nums">{money(row.nc_carryover_amount)}</TableCell>
                    <TableCell className={cn("text-right tabular-nums", Number(row.ending_balance || 0) < 0 ? "text-red-700" : "")}>
                      {money(row.ending_balance)}
                    </TableCell>
                    <TableCell className={cn("text-right tabular-nums", Number(row.missing_rate_count || 0) > 0 ? "text-red-700" : "")}>
                      {number(row.missing_rate_count)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{number(row.movement_count)}</TableCell>
                    <TableCell>{row.confirmed_by_name || "—"}</TableCell>
                    <TableCell>{fmtDateTime(row.confirmed_at)}</TableCell>
                    <TableCell>
                      <Button type="button" size="sm" variant="outline" disabled={row.status === "CONFIRMED"} onClick={() => onCarryover(row)}>
                        登记 NC 结转
                      </Button>
                    </TableCell>
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

function StatusBadge({ status, missingRate }: { status: string; missingRate: number }) {
  if (missingRate > 0) {
    return (
      <Badge variant="outline" className="border-red-200 bg-red-50 text-red-700">
        缺占比
      </Badge>
    );
  }
  if (status === "CONFIRMED") {
    return (
      <Badge variant="outline" className="border-emerald-200 bg-emerald-50 text-emerald-700">
        已确认
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className="border-blue-200 bg-blue-50 text-blue-700">
      草稿
    </Badge>
  );
}

function CarryoverDialog({
  row,
  ncVoucherNo,
  carryoverAmount,
  carryoverDate,
  remark,
  saving,
  onOpenChange,
  onNcVoucherNoChange,
  onCarryoverAmountChange,
  onCarryoverDateChange,
  onRemarkChange,
  onSubmit,
}: {
  row: BalanceRow | null;
  ncVoucherNo: string;
  carryoverAmount: string;
  carryoverDate: string;
  remark: string;
  saving: boolean;
  onOpenChange: (open: boolean) => void;
  onNcVoucherNoChange: (value: string) => void;
  onCarryoverAmountChange: (value: string) => void;
  onCarryoverDateChange: (value: string) => void;
  onRemarkChange: (value: string) => void;
  onSubmit: () => void;
}) {
  return (
    <Dialog open={!!row} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>登记 NC 结转</DialogTitle>
        </DialogHeader>
        {row ? (
          <div className="space-y-4">
            <div className="grid gap-3 rounded-md border p-3 text-sm sm:grid-cols-3">
              <SummaryBox label="门店" value={`${row.market_code} ${storeName(row.market_code)}`} />
              <SummaryBox label="券种" value={`${row.coupon_type} ${row.coupon_name || ""}`.trim()} />
              <SummaryBox label="当前余额" value={money(row.ending_balance)} danger={Number(row.ending_balance || 0) < 0} />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <Label htmlFor="nc-voucher-no">NC 凭证号</Label>
                <Input id="nc-voucher-no" className="mt-1" value={ncVoucherNo} onChange={(event) => onNcVoucherNoChange(event.target.value)} />
              </div>
              <div>
                <Label htmlFor="carryover-amount">结转金额</Label>
                <Input
                  id="carryover-amount"
                  className="mt-1"
                  type="number"
                  min="0"
                  value={carryoverAmount}
                  onChange={(event) => onCarryoverAmountChange(event.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="carryover-date">结转日期</Label>
                <Input
                  id="carryover-date"
                  className="mt-1"
                  type="date"
                  value={carryoverDate}
                  onChange={(event) => onCarryoverDateChange(event.target.value)}
                />
              </div>
              <div className="sm:col-span-2">
                <Label htmlFor="carryover-remark">备注</Label>
                <Textarea id="carryover-remark" className="mt-1" value={remark} onChange={(event) => onRemarkChange(event.target.value)} />
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                取消
              </Button>
              <Button type="button" onClick={onSubmit} disabled={saving || !ncVoucherNo || Number(carryoverAmount || 0) <= 0}>
                {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                保存登记
              </Button>
            </div>
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
