import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  BarChart3,
  Check,
  ChevronDown,
  Download,
  Presentation,
  RefreshCw,
  Search,
  ShoppingBasket,
  Sparkles,
  Store,
  Users,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useStore } from "@/contexts/StoreContext";
import { apiGet, apiPost } from "@/lib/api";
import {
  BrandMemberFilters,
  BrandMemberGroupOption,
  BrandMemberReport,
  brandMemberAiFallbackMessage,
  brandMemberRequest,
  buildAiSnapshot,
  defaultBrandMemberDates,
  filterBrandMemberGroups,
  formatBrandMoney,
  formatBrandNumber,
  formatBrandPercent,
  formatBrandShare,
  previousPeriod,
  priorYearPeriod,
} from "@/lib/brand-member-analysis";
import { cn } from "@/lib/utils";


interface AiConclusion {
  status: string;
  provider?: string;
  model?: string;
  conclusion: string;
  fallback_used: boolean;
  error?: string;
}

const SEGMENT_COLORS: Record<string, string> = {
  brand_returning: "#0f766e",
  same_department_inflow: "#2563eb",
  cross_department_inflow: "#7c3aed",
  external_new: "#ea580c",
};

function MetricCard({
  label,
  value,
  prior,
  changeRate,
  hint,
}: {
  label: string;
  value: string;
  prior: string;
  changeRate: number | null;
  hint?: string;
}) {
  return (
    <Card className="border-slate-200 shadow-sm">
      <CardContent className="p-5">
        <div className="text-sm text-slate-500">{label}</div>
        <div className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">{value}</div>
        <div className="mt-2 flex items-center justify-between gap-3 text-xs">
          <span className="text-slate-500">同期 {prior}</span>
          <span
            className={cn(
              "font-medium",
              changeRate == null && "text-slate-400",
              changeRate != null && changeRate > 0 && "text-rose-600",
              changeRate != null && changeRate < 0 && "text-emerald-600",
              changeRate === 0 && "text-slate-500",
            )}
          >
            {formatBrandPercent(changeRate)}
          </span>
        </div>
        {hint ? <div className="mt-2 text-xs text-slate-400">{hint}</div> : null}
      </CardContent>
    </Card>
  );
}

function FunnelStep({ label, value, base, accent }: { label: string; value: number; base: number; accent: string }) {
  const rate = base > 0 ? value / base : 0;
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm text-slate-600">{label}</span>
        <span className="text-xs font-medium text-slate-400">{formatBrandPercent(rate)}</span>
      </div>
      <div className="mt-2 text-2xl font-semibold text-slate-950">{formatBrandNumber(value)}</div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full" style={{ width: `${Math.min(rate * 100, 100)}%`, background: accent }} />
      </div>
    </div>
  );
}

export default function BrandMemberAnalysisPage() {
  const dateDefaults = useMemo(() => defaultBrandMemberDates(), []);
  const { stores, selectedStore } = useStore();
  const [draft, setDraft] = useState<BrandMemberFilters>({
    storeCode: selectedStore?.storeCode || "",
    targetGroupCode: "",
    competitorGroupCodes: [],
    ...dateDefaults,
  });
  const [submitted, setSubmitted] = useState<BrandMemberFilters | null>(null);
  const [queryVersion, setQueryVersion] = useState(0);
  const [targetPickerOpen, setTargetPickerOpen] = useState(false);
  const [targetSearch, setTargetSearch] = useState("");
  const [competitorPickerOpen, setCompetitorPickerOpen] = useState(false);
  const [competitorSearch, setCompetitorSearch] = useState("");
  const [isExporting, setIsExporting] = useState(false);
  const [isExportingPpt, setIsExportingPpt] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  useEffect(() => {
    if (!draft.storeCode && selectedStore?.storeCode) {
      setDraft((current) => ({ ...current, storeCode: selectedStore.storeCode }));
    }
  }, [draft.storeCode, selectedStore?.storeCode]);

  const groupsQuery = useQuery<BrandMemberGroupOption[]>({
    queryKey: ["brand-member-groups", draft.storeCode],
    queryFn: () => apiGet(`/api/sales/brand-member-analysis/groups?store_code=${encodeURIComponent(draft.storeCode)}`),
    enabled: Boolean(draft.storeCode),
    staleTime: 5 * 60 * 1000,
  });

  const reportQuery = useQuery<BrandMemberReport>({
    queryKey: ["brand-member-report", submitted, queryVersion],
    queryFn: () => apiPost("/api/sales/brand-member-analysis/report", brandMemberRequest(submitted!)),
    enabled: Boolean(submitted),
    staleTime: 0,
    retry: false,
  });

  const aiQuery = useQuery<AiConclusion>({
    queryKey: ["brand-member-ai-conclusion", reportQuery.dataUpdatedAt],
    queryFn: () => apiPost("/api/sales/brand-member-analysis/conclusion", { snapshot: buildAiSnapshot(reportQuery.data!) }),
    enabled: Boolean(reportQuery.data),
    staleTime: Infinity,
    retry: false,
  });

  const groupOptions = groupsQuery.data || [];
  const selectedTarget = groupOptions.find((group) => group.group_code === draft.targetGroupCode);
  const targetGroupOptions = useMemo(
    () => groupOptions.filter((group) => group.target_selectable),
    [groupOptions],
  );
  const filteredTargetOptions = useMemo(
    () => filterBrandMemberGroups(targetGroupOptions, targetSearch),
    [targetGroupOptions, targetSearch],
  );
  const filteredCompetitorOptions = useMemo(
    () => filterBrandMemberGroups(groupOptions, competitorSearch)
      .filter((group) => group.group_code !== draft.targetGroupCode),
    [competitorSearch, draft.targetGroupCode, groupOptions],
  );
  const competitors = draft.competitorGroupCodes
    .map((code) => groupOptions.find((group) => group.group_code === code))
    .filter(Boolean) as BrandMemberGroupOption[];

  const handleStoreChange = (storeCode: string) => {
    setDraft((current) => ({
      ...current,
      storeCode,
      targetGroupCode: "",
      competitorGroupCodes: [],
    }));
  };

  const toggleCompetitor = (code: string) => {
    setDraft((current) => {
      const selected = current.competitorGroupCodes.includes(code);
      if (selected) {
        return { ...current, competitorGroupCodes: current.competitorGroupCodes.filter((item) => item !== code) };
      }
      if (current.competitorGroupCodes.length >= 5) return current;
      return { ...current, competitorGroupCodes: [...current.competitorGroupCodes, code] };
    });
  };

  const canQuery = Boolean(
    draft.storeCode
      && draft.targetGroupCode
      && draft.currentStart
      && draft.currentEnd
      && draft.priorStart
      && draft.priorEnd
      && draft.currentStart <= draft.currentEnd
      && draft.priorStart <= draft.priorEnd,
  );

  const submitQuery = () => {
    setExportError(null);
    setSubmitted({ ...draft });
    setQueryVersion((version) => version + 1);
  };

  const report = reportQuery.data;
  const current = report?.target.current;
  const prior = report?.target.prior;
  const selectedStoreName = stores.find((store) => store.storeCode === report?.scope.store_code)?.storeName
    || report?.scope.store_code
    || "所选门店";

  const handleSupplierExport = async () => {
    if (!report || isExporting) return;
    setExportError(null);
    setIsExporting(true);
    try {
      const { exportSupplierWorkbook } = await import("@/lib/export-brand-member-supplier");
      exportSupplierWorkbook(report, selectedStoreName, aiQuery.data?.conclusion);
    } catch (error) {
      setExportError(error instanceof Error ? error.message : "供应商沟通版生成失败，请稍后重试。");
    } finally {
      setIsExporting(false);
    }
  };

  const handlePptExport = async () => {
    if (!report || isExportingPpt) return;
    setExportError(null);
    setIsExportingPpt(true);
    try {
      const { exportSupplierPresentation } = await import("@/lib/export-brand-member-ppt");
      await exportSupplierPresentation(report, selectedStoreName, aiQuery.data?.conclusion);
    } catch (error) {
      setExportError(error instanceof Error ? error.message : "PPT生成失败，请稍后重试。");
    } finally {
      setIsExportingPpt(false);
    }
  };

  const segmentChartData = report
    ? report.target.current.segments.map((row) => ({
        name: row.label,
        本期: row.buyer_count,
        同期: report.target.prior.segments.find((item) => item.code === row.code)?.buyer_count || 0,
        color: SEGMENT_COLORS[row.code],
      }))
    : [];

  return (
    <div className="min-h-full bg-slate-50/70 p-4 md:p-6">
      <div className="mx-auto max-w-[1600px] space-y-5">
        <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-end">
          <div>
            <div className="flex items-center gap-2 text-sm font-medium text-teal-700">
              <Sparkles className="h-4 w-4" />
              面向品牌供应商的经营沟通视图
            </div>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950 md:text-3xl">品牌会员经营分析</h1>
            <p className="mt-2 text-sm text-slate-500">从经营结果、会员流入、老客回购和竞品表现四个方向讲清品牌故事。</p>
          </div>
          {report ? (
            <div className="flex flex-col items-stretch gap-2 sm:items-end">
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" disabled={isExporting || isExportingPpt} onClick={() => void handleSupplierExport()}>
                  {isExporting ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
                  {isExporting ? "正在生成 Excel" : "导出 Excel 沟通版"}
                </Button>
                <Button className="bg-slate-950 text-white hover:bg-slate-800" disabled={isExporting || isExportingPpt} onClick={() => void handlePptExport()}>
                  {isExportingPpt ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <Presentation className="mr-2 h-4 w-4" />}
                  {isExportingPpt ? "正在生成 PPT" : "导出 PPT 沟通版"}
                </Button>
              </div>
              {exportError ? <div className="max-w-xl text-right text-xs text-rose-600">{exportError}</div> : null}
            </div>
          ) : null}
        </div>

        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-4 md:p-5">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <div className="space-y-2">
                <Label>门店</Label>
                <Select value={draft.storeCode} onValueChange={handleStoreChange}>
                  <SelectTrigger><SelectValue placeholder="选择门店" /></SelectTrigger>
                  <SelectContent>
                    {stores.map((store) => (
                      <SelectItem key={store.storeCode} value={store.storeCode}>{store.storeName}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>目标柜组</Label>
                <Popover
                  open={targetPickerOpen}
                  onOpenChange={(open) => {
                    setTargetPickerOpen(open);
                    if (!open) setTargetSearch("");
                  }}
                >
                  <PopoverTrigger asChild>
                    <Button
                      type="button"
                      variant="outline"
                      role="combobox"
                      aria-expanded={targetPickerOpen}
                      disabled={!draft.storeCode || groupsQuery.isLoading}
                      className="w-full justify-between px-3 font-normal"
                    >
                      <span className="truncate">
                        {selectedTarget
                          ? `${selectedTarget.group_name} · ${selectedTarget.group_code}`
                          : groupsQuery.isLoading ? "正在加载柜组" : "选择目标柜组"}
                      </span>
                      <ChevronDown className="ml-2 h-4 w-4 shrink-0 text-slate-400" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-[420px] border-slate-200 bg-white p-0 text-slate-950 shadow-xl" align="start">
                    <div className="border-b p-3">
                      <Input
                        value={targetSearch}
                        onChange={(event) => setTargetSearch(event.target.value)}
                        placeholder="输入品牌名称、柜组编码或部门"
                        aria-label="搜索目标品牌"
                      />
                    </div>
                    <ScrollArea className="h-72 p-2">
                      {filteredTargetOptions.length ? (
                        <div className="space-y-1">
                          {filteredTargetOptions.map((group) => (
                            <button
                              key={group.group_code}
                              type="button"
                              className="flex w-full items-start gap-3 rounded-md px-2 py-2 text-left hover:bg-slate-50"
                              onClick={() => {
                                setDraft((currentFilters) => ({
                                  ...currentFilters,
                                  targetGroupCode: group.group_code,
                                  competitorGroupCodes: currentFilters.competitorGroupCodes.filter((code) => code !== group.group_code),
                                }));
                                setTargetPickerOpen(false);
                                setTargetSearch("");
                              }}
                            >
                              <Check className={cn("mt-0.5 h-4 w-4 shrink-0", draft.targetGroupCode === group.group_code ? "opacity-100" : "opacity-0")} />
                              <span className="min-w-0">
                                <span className="block truncate text-sm font-medium text-slate-800">{group.group_name}</span>
                                <span className="block truncate text-xs text-slate-400">{group.department_name || "未归属部门"} · {group.group_code}</span>
                              </span>
                            </button>
                          ))}
                        </div>
                      ) : (
                        <div className="px-3 py-10 text-center text-sm text-slate-500">没有匹配的品牌柜组</div>
                      )}
                    </ScrollArea>
                  </PopoverContent>
                </Popover>
              </div>

              <div className="space-y-2">
                <Label>竞品柜组（可不选，最多5个）</Label>
                <Popover
                  open={competitorPickerOpen}
                  onOpenChange={(open) => {
                    setCompetitorPickerOpen(open);
                    if (!open) setCompetitorSearch("");
                  }}
                >
                  <PopoverTrigger asChild>
                    <Button variant="outline" className="w-full justify-between px-3 font-normal">
                      <span className="truncate">
                        {competitors.length ? competitors.map((item) => item.group_name).join("、") : "不选择竞品"}
                      </span>
                      <ChevronDown className="ml-2 h-4 w-4 shrink-0 text-slate-400" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-[360px] border-slate-200 bg-white p-0 text-slate-950 shadow-xl" align="start">
                    <div className="border-b p-3">
                      <Input
                        value={competitorSearch}
                        onChange={(event) => setCompetitorSearch(event.target.value)}
                        placeholder="搜索全门店品牌、柜组编码或部门"
                        aria-label="搜索竞品柜组"
                      />
                    </div>
                    <ScrollArea className="h-72 p-3">
                      <div className="space-y-1">
                        {filteredCompetitorOptions.length ? (
                          filteredCompetitorOptions.map((group) => {
                            const checked = draft.competitorGroupCodes.includes(group.group_code);
                            const disabled = !checked && draft.competitorGroupCodes.length >= 5;
                            return (
                              <button
                                key={group.group_code}
                                type="button"
                                className="flex w-full items-start gap-3 rounded-md px-2 py-2 text-left hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                                disabled={disabled}
                                onClick={() => toggleCompetitor(group.group_code)}
                              >
                                <Checkbox checked={checked} className="mt-0.5" />
                                <span className="min-w-0">
                                  <span className="block truncate text-sm font-medium text-slate-800">{group.group_name}</span>
                                  <span className="block truncate text-xs text-slate-400">{group.department_name || "未归属部门"} · {group.group_code}</span>
                                </span>
                              </button>
                            );
                          })
                        ) : (
                          <div className="px-3 py-10 text-center text-sm text-slate-500">没有匹配的竞品柜组</div>
                        )}
                      </div>
                    </ScrollArea>
                  </PopoverContent>
                </Popover>
              </div>

              <div className="flex items-end">
                <Button className="w-full bg-slate-950 text-white hover:bg-slate-800 hover:text-white disabled:bg-slate-500 disabled:text-white" disabled={!canQuery || reportQuery.isFetching} onClick={submitQuery}>
                  {reportQuery.isFetching ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
                  查询分析
                </Button>
              </div>
            </div>

            <div className="mt-4 grid gap-4 border-t border-slate-100 pt-4 md:grid-cols-2 xl:grid-cols-4">
              <div className="space-y-2">
                <Label>本期开始</Label>
                <Input type="date" value={draft.currentStart} onChange={(event) => setDraft((currentFilters) => ({ ...currentFilters, currentStart: event.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label>本期结束</Label>
                <Input type="date" value={draft.currentEnd} onChange={(event) => setDraft((currentFilters) => ({ ...currentFilters, currentEnd: event.target.value }))} />
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <Label>同期开始</Label>
                  <Button type="button" variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={() => setDraft((currentFilters) => ({ ...currentFilters, ...priorYearPeriod(currentFilters.currentStart, currentFilters.currentEnd) }))}>
                    去年同期
                  </Button>
                </div>
                <Input type="date" value={draft.priorStart} onChange={(event) => setDraft((currentFilters) => ({ ...currentFilters, priorStart: event.target.value }))} />
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <Label>同期结束</Label>
                  <Button type="button" variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={() => setDraft((currentFilters) => ({ ...currentFilters, ...previousPeriod(currentFilters.currentStart, currentFilters.currentEnd) }))}>
                    上一周期
                  </Button>
                </div>
                <Input type="date" value={draft.priorEnd} onChange={(event) => setDraft((currentFilters) => ({ ...currentFilters, priorEnd: event.target.value }))} />
              </div>
            </div>
          </CardContent>
        </Card>

        {reportQuery.error ? (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>查询失败</AlertTitle>
            <AlertDescription>{reportQuery.error instanceof Error ? reportQuery.error.message : "请检查查询条件后重试。"}</AlertDescription>
          </Alert>
        ) : null}

        {reportQuery.isFetching && !report ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {Array.from({ length: 8 }).map((_, index) => <Skeleton key={index} className="h-36 rounded-xl" />)}
          </div>
        ) : null}

        {!submitted && !report ? (
          <Card className="border-dashed border-slate-300 bg-white/60">
            <CardContent className="flex min-h-64 flex-col items-center justify-center p-8 text-center">
              <div className="rounded-full bg-teal-50 p-4 text-teal-700"><BarChart3 className="h-8 w-8" /></div>
              <div className="mt-4 text-lg font-semibold text-slate-900">选择目标柜组后开始品牌分析</div>
              <div className="mt-2 max-w-xl text-sm leading-6 text-slate-500">竞品柜组可以留空。本期与同期可分别选择，会员身份分别追溯到各自分析期开始之前的全部历史。</div>
            </CardContent>
          </Card>
        ) : null}

        {report && current && prior ? (
          <>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <MetricCard
                label="销售收入"
                value={formatBrandMoney(current.summary.sales_revenue)}
                prior={formatBrandMoney(prior.summary.sales_revenue)}
                changeRate={report.comparison.sales_revenue?.change_rate ?? null}
                hint="sglxssr 正负数净额"
              />
              <MetricCard
                label="购买会员数"
                value={`${formatBrandNumber(current.summary.member_buyer_count)} 人`}
                prior={`${formatBrandNumber(prior.summary.member_buyer_count)} 人`}
                changeRate={report.comparison.member_buyer_count?.change_rate ?? null}
                hint="至少一笔正向销售"
              />
              <MetricCard
                label="会员人均消费"
                value={formatBrandMoney(current.summary.spend_per_buyer)}
                prior={formatBrandMoney(prior.summary.spend_per_buyer)}
                changeRate={report.comparison.spend_per_buyer?.change_rate ?? null}
              />
              <MetricCard
                label="品牌老客回购率"
                value={formatBrandPercent(current.summary.old_customer_repurchase_rate)}
                prior={formatBrandPercent(prior.summary.old_customer_repurchase_rate)}
                changeRate={report.comparison.old_customer_repurchase_rate?.change ?? null}
                hint={current.summary.department_rank ? `部门销售排名 ${current.summary.department_rank}/${current.summary.department_group_count}` : "暂无部门排名"}
              />
            </div>

            <Card className="overflow-hidden border-slate-200 shadow-sm">
              <CardHeader className="border-b border-slate-100 bg-gradient-to-r from-slate-950 to-slate-800 text-white">
                <div className="flex items-center justify-between gap-3">
                  <CardTitle className="flex items-center gap-2 text-base"><Sparkles className="h-4 w-4 text-amber-300" />AI经营结论</CardTitle>
                  {aiQuery.data ? (
                    <Badge variant="secondary" className="bg-white/10 text-white hover:bg-white/10">
                      {aiQuery.data.fallback_used ? "规则结论" : "AI已生成"}
                    </Badge>
                  ) : null}
                </div>
              </CardHeader>
              <CardContent className="p-5 md:p-6">
                {aiQuery.isFetching ? (
                  <div className="space-y-3"><Skeleton className="h-4 w-full" /><Skeleton className="h-4 w-11/12" /><Skeleton className="h-4 w-4/5" /></div>
                ) : aiQuery.data ? (
                  <div className="whitespace-pre-line text-sm leading-7 text-slate-700">{aiQuery.data.conclusion}</div>
                ) : (
                  <div className="text-sm text-slate-500">经营数据已经完成，AI结论暂未生成。</div>
                )}
                {aiQuery.data?.fallback_used && aiQuery.data.error ? (
                  <div className="mt-3 text-xs text-amber-700">{brandMemberAiFallbackMessage(aiQuery.data.status)}</div>
                ) : null}
              </CardContent>
            </Card>

            <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
              <Card className="border-slate-200 shadow-sm">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base"><Users className="h-4 w-4 text-teal-700" />会员构成变化</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={segmentChartData} margin={{ top: 12, right: 12, left: 0, bottom: 8 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                        <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                        <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                        <Tooltip />
                        <Legend />
                        <Bar dataKey="本期" fill="#0f766e" radius={[4, 4, 0, 0]} />
                        <Bar dataKey="同期" fill="#cbd5e1" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    {current.segments.map((row) => (
                      <div key={row.code} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm">
                        <span className="flex items-center gap-2 text-slate-600"><span className="h-2.5 w-2.5 rounded-full" style={{ background: SEGMENT_COLORS[row.code] }} />{row.label}</span>
                        <span className="font-medium text-slate-900">{formatBrandNumber(row.buyer_count)}人 · {formatBrandPercent(row.buyer_share)}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card className="border-slate-200 shadow-sm">
                <CardHeader>
                  <CardTitle className="text-base">品牌老客回购漏斗</CardTitle>
                </CardHeader>
                <CardContent className="grid gap-3 sm:grid-cols-2">
                  <FunnelStep label="历史品牌会员" value={current.old_customer_funnel.historical_target_member_count} base={current.old_customer_funnel.historical_target_member_count} accent="#0f172a" />
                  <FunnelStep label="本期到店" value={current.old_customer_funnel.store_visit_count} base={current.old_customer_funnel.historical_target_member_count} accent="#2563eb" />
                  <FunnelStep label="到目标部门" value={current.old_customer_funnel.department_visit_count} base={current.old_customer_funnel.historical_target_member_count} accent="#7c3aed" />
                  <FunnelStep label="回购目标柜组" value={current.old_customer_funnel.target_repurchase_count} base={current.old_customer_funnel.historical_target_member_count} accent="#0f766e" />
                </CardContent>
              </Card>
            </div>

            <Card className="border-slate-200 shadow-sm">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <ShoppingBasket className="h-4 w-4 text-amber-700" />购买频次与客件分析
                </CardTitle>
                <div className="text-xs leading-5 text-slate-500">
                  一次客＝期间内1张会员交易小票，多次客＝期间内2张及以上；客件数＝会员净销售件数÷会员交易小票数，退货数量按负数冲减。
                </div>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <Table className="min-w-[1280px]">
                    <TableHeader>
                      <TableRow>
                        <TableHead>客群</TableHead>
                        <TableHead className="text-right">本期会员数</TableHead>
                        <TableHead className="text-right">同期会员数</TableHead>
                        <TableHead className="text-right">本期人数占比</TableHead>
                        <TableHead className="text-right">本期销售收入</TableHead>
                        <TableHead className="text-right">同期销售收入</TableHead>
                        <TableHead className="text-right">消费频次</TableHead>
                        <TableHead className="text-right">客单</TableHead>
                        <TableHead className="text-right">净销售件数</TableHead>
                        <TableHead className="text-right">本期客件数</TableHead>
                        <TableHead className="text-right">同期客件数</TableHead>
                        <TableHead className="text-right">件单价</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {current.purchase_frequency_analysis.map((row) => {
                        const priorRow = prior.purchase_frequency_analysis.find((item) => item.code === row.code);
                        return (
                          <TableRow key={row.code}>
                            <TableCell>
                              <Badge variant="outline" className={cn(
                                "font-medium",
                                row.code === "repeat_purchase" ? "border-teal-200 bg-teal-50 text-teal-800" : "text-slate-700",
                              )}>
                                {row.label}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right font-semibold">{formatBrandNumber(row.buyer_count)}</TableCell>
                            <TableCell className="text-right text-slate-500">{formatBrandNumber(priorRow?.buyer_count ?? 0)}</TableCell>
                            <TableCell className="text-right">{formatBrandShare(row.buyer_share)}</TableCell>
                            <TableCell className="text-right font-medium">{formatBrandMoney(row.sales_revenue)}</TableCell>
                            <TableCell className="text-right text-slate-500">{formatBrandMoney(priorRow?.sales_revenue ?? 0)}</TableCell>
                            <TableCell className="text-right">{formatBrandNumber(row.purchase_frequency, 2)}</TableCell>
                            <TableCell className="text-right">{formatBrandMoney(row.average_ticket_value)}</TableCell>
                            <TableCell className="text-right">{formatBrandNumber(row.sales_quantity, 2)}</TableCell>
                            <TableCell className="text-right font-semibold text-amber-800">{formatBrandNumber(row.items_per_ticket, 2)}</TableCell>
                            <TableCell className="text-right text-slate-500">{formatBrandNumber(priorRow?.items_per_ticket ?? 0, 2)}</TableCell>
                            <TableCell className="text-right">{formatBrandMoney(row.average_item_price)}</TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>

            <Card className="border-slate-200 shadow-sm">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Users className="h-4 w-4 text-violet-700" />会员等级消费分析
                </CardTitle>
                <div className="text-xs text-slate-500">按交易小票记录的会员等级汇总，仅统计期间内至少有一笔正向购买的会员；按等级内去重。客单＝销售收入净额÷会员交易小票数。</div>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                <Table className="min-w-[1680px]">
                  <TableHeader>
                    <TableRow>
                      <TableHead rowSpan={2} className="whitespace-nowrap align-middle">会员等级</TableHead>
                      <TableHead colSpan={7} className="border-l text-center">本期</TableHead>
                      <TableHead colSpan={7} className="border-l text-center">同期</TableHead>
                    </TableRow>
                    <TableRow>
                      <TableHead className="whitespace-nowrap border-l text-right">购买会员</TableHead>
                      <TableHead className="whitespace-nowrap text-right">人数占比</TableHead>
                      <TableHead className="whitespace-nowrap text-right">销售收入</TableHead>
                      <TableHead className="whitespace-nowrap text-right">销售占比</TableHead>
                      <TableHead className="whitespace-nowrap text-right">会员人均消费</TableHead>
                      <TableHead className="whitespace-nowrap text-right">消费频次</TableHead>
                      <TableHead className="whitespace-nowrap text-right">客单</TableHead>
                      <TableHead className="whitespace-nowrap border-l text-right">购买会员</TableHead>
                      <TableHead className="whitespace-nowrap text-right">人数占比</TableHead>
                      <TableHead className="whitespace-nowrap text-right">销售收入</TableHead>
                      <TableHead className="whitespace-nowrap text-right">销售占比</TableHead>
                      <TableHead className="whitespace-nowrap text-right">会员人均消费</TableHead>
                      <TableHead className="whitespace-nowrap text-right">消费频次</TableHead>
                      <TableHead className="whitespace-nowrap text-right">客单</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {current.member_level_consumption.map((row) => {
                      const priorRow = prior.member_level_consumption.find((item) => item.level_code === row.level_code);
                      return (
                        <TableRow key={row.level_code}>
                          <TableCell>
                            <Badge variant="outline" className="font-medium text-slate-700">{row.level_label}</Badge>
                          </TableCell>
                          <TableCell className="text-right font-medium">{formatBrandNumber(row.buyer_count)}</TableCell>
                          <TableCell className="text-right">{formatBrandShare(row.buyer_share)}</TableCell>
                          <TableCell className="text-right font-medium">{formatBrandMoney(row.sales_revenue)}</TableCell>
                          <TableCell className="text-right">{formatBrandShare(row.sales_share)}</TableCell>
                          <TableCell className="text-right">{formatBrandMoney(row.spend_per_buyer)}</TableCell>
                          <TableCell className="text-right">{formatBrandNumber(row.purchase_frequency, 2)}</TableCell>
                          <TableCell className="text-right">{formatBrandMoney(row.average_ticket_value)}</TableCell>
                          <TableCell className="border-l text-right text-slate-500">{formatBrandNumber(priorRow?.buyer_count ?? 0)}</TableCell>
                          <TableCell className="text-right text-slate-500">{formatBrandShare(priorRow?.buyer_share ?? null)}</TableCell>
                          <TableCell className="text-right text-slate-500">{formatBrandMoney(priorRow?.sales_revenue ?? 0)}</TableCell>
                          <TableCell className="text-right text-slate-500">{formatBrandShare(priorRow?.sales_share ?? null)}</TableCell>
                          <TableCell className="text-right text-slate-500">{formatBrandMoney(priorRow?.spend_per_buyer ?? 0)}</TableCell>
                          <TableCell className="text-right text-slate-500">{formatBrandNumber(priorRow?.purchase_frequency ?? 0, 2)}</TableCell>
                          <TableCell className="text-right text-slate-500">{formatBrandMoney(priorRow?.average_ticket_value ?? 0)}</TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
                </div>
              </CardContent>
            </Card>

            <div className="grid gap-5 xl:grid-cols-2">
              <Card className="border-slate-200 shadow-sm">
                <CardHeader><CardTitle className="text-base">内部流入来源</CardTitle></CardHeader>
                <CardContent>
                  {current.inflow_sources.length ? (
                    <Table>
                      <TableHeader><TableRow><TableHead>类型</TableHead><TableHead>来源柜组</TableHead><TableHead>部门</TableHead><TableHead className="text-right">会员数</TableHead></TableRow></TableHeader>
                      <TableBody>
                        {current.inflow_sources.map((row) => (
                          <TableRow key={`${row.segment_code}-${row.group_code}`}>
                            <TableCell><Badge variant="outline">{row.segment_code === "same_department_inflow" ? "同部门" : "跨部门"}</Badge></TableCell>
                            <TableCell><div className="font-medium text-slate-800">{row.group_name}</div><div className="text-xs text-slate-400">{row.group_code}</div></TableCell>
                            <TableCell>{row.department_name || "—"}</TableCell>
                            <TableCell className="text-right font-medium">{formatBrandNumber(row.buyer_count)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  ) : <div className="py-12 text-center text-sm text-slate-500">本期没有可归属的内部流入来源。</div>}
                </CardContent>
              </Card>

              <Card className="border-slate-200 shadow-sm">
                <CardHeader><CardTitle className="text-base">竞品柜组对比</CardTitle></CardHeader>
                <CardContent>
                  {report.competitors.length ? (
                    <Table>
                      <TableHeader><TableRow><TableHead>柜组</TableHead><TableHead className="text-right">销售收入</TableHead><TableHead className="text-right">购买会员</TableHead><TableHead className="text-right">人均消费</TableHead></TableRow></TableHeader>
                      <TableBody>
                        <TableRow className="bg-teal-50/60">
                          <TableCell><div className="font-semibold text-teal-900">{report.target.group_name}</div><div className="text-xs text-teal-700">目标柜组</div></TableCell>
                          <TableCell className="text-right font-medium">{formatBrandMoney(current.summary.sales_revenue)}</TableCell>
                          <TableCell className="text-right">{formatBrandNumber(current.summary.member_buyer_count)}</TableCell>
                          <TableCell className="text-right">{formatBrandMoney(current.summary.spend_per_buyer)}</TableCell>
                        </TableRow>
                        {report.competitors.map((row) => (
                          <TableRow key={row.group_code}>
                            <TableCell><div className="font-medium text-slate-800">{row.group_name}</div><div className="text-xs text-slate-400">{row.department_name || "—"}</div></TableCell>
                            <TableCell className="text-right font-medium">{formatBrandMoney(row.current.sales_revenue)}</TableCell>
                            <TableCell className="text-right">{formatBrandNumber(row.current.member_buyer_count)}</TableCell>
                            <TableCell className="text-right">{formatBrandMoney(row.current.spend_per_buyer)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  ) : (
                    <div className="flex min-h-48 flex-col items-center justify-center text-center">
                      <Store className="h-8 w-8 text-slate-300" />
                      <div className="mt-3 text-sm font-medium text-slate-700">本次未选择竞品柜组</div>
                      <div className="mt-1 text-xs text-slate-400">经营结论只围绕目标柜组展开。</div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

            <Card className="border-slate-200 bg-slate-950 text-slate-100 shadow-sm">
              <CardContent className="grid gap-4 p-5 md:grid-cols-4">
                <div><div className="text-xs text-slate-400">正向销售额</div><div className="mt-1 font-semibold">{formatBrandMoney(current.summary.positive_revenue)}</div></div>
                <div><div className="text-xs text-slate-400">负向销售额</div><div className="mt-1 font-semibold">{formatBrandMoney(current.summary.refund_revenue)}</div></div>
                <div><div className="text-xs text-slate-400">非会员销售额</div><div className="mt-1 font-semibold">{formatBrandMoney(current.summary.nonmember_sales_revenue)}</div></div>
                <div><div className="text-xs text-slate-400">仅退货会员销售额</div><div className="mt-1 font-semibold">{formatBrandMoney(current.summary.refund_only_member_sales_revenue)}</div></div>
              </CardContent>
            </Card>
          </>
        ) : null}
      </div>
    </div>
  );
}
