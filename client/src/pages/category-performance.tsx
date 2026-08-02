import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  Award,
  BarChart3,
  CheckCircle2,
  FileSpreadsheet,
  RefreshCw,
  Save,
  Search,
  Target,
  Upload,
  Users,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useStore } from "@/contexts/StoreContext";
import { useToast } from "@/hooks/use-toast";
import { apiGet, apiPut, getApiUrl } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";

type ManagerOption = {
  user_id: number;
  real_name: string;
  username: string;
  employee_no?: string | null;
};

type GroupOption = {
  group_code: string;
  group_name: string;
  department_code?: string | null;
  department_name?: string | null;
  area_name?: string | null;
  is_key_brand: boolean;
};

type PerformanceOptions = {
  store: { store_id: number; store_code: string; store_name: string };
  can_manage: boolean;
  latest_period?: string | null;
  groups: GroupOption[];
  managers: ManagerOption[];
};

type BrandAssignment = {
  id: number;
  group_code: string;
  group_name: string;
  department_name?: string | null;
  manager_user_id: number;
  manager_name: string;
  is_key_brand: boolean;
  is_active: boolean;
  updated_at: string;
};

type KeyBrandTarget = {
  id: number;
  group_code: string;
  group_name: string;
  department_name?: string | null;
  manager_user_id: number;
  manager_name: string;
  sales_target: number;
  is_active: boolean;
  updated_at: string;
};

type ManagerTarget = {
  id: number;
  manager_user_id: number;
  manager_name: string;
  area_revenue_target: number;
  area_weight: number;
  key_brand_weight: number;
  self_weight: number;
  self_score: number | null;
  assessment_content?: string | null;
  updated_at: string;
};

type ScoreItem = {
  manager_user_id: number;
  manager_name: string;
  assessment_content?: string | null;
  area_weight: number;
  key_brand_weight: number;
  self_weight: number;
  key_brand_count: number;
  area_target: number;
  area_actual: number;
  area_rate: number | null;
  area_score: number | null;
  key_target: number;
  key_actual: number;
  key_rate: number | null;
  key_score: number | null;
  self_score: number | null;
  score_complete: boolean;
  total_score: number | null;
  coefficient: number | null;
};

type Scorecard = {
  store: { store_id: number; store_code: string; store_name: string };
  period: string;
  period_start: string;
  period_end: string;
  effective_end_date: string;
  latest_sales_date?: string | null;
  latest_fee_date?: string | null;
  definitions: Record<string, string>;
  items: ScoreItem[];
};

type ImportResult = {
  imported: {
    brand_assignments: number;
    key_brand_targets: number;
    manager_targets: number;
  };
  unmatched_count: number;
  unmatched: Array<{ sheet: string; brand: string; manager: string }>;
};

const currentPeriod = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
};

const number = (value: number | null | undefined, digits = 2) =>
  value == null || !Number.isFinite(Number(value))
    ? "—"
    : new Intl.NumberFormat("zh-CN", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      }).format(Number(value));

const percent = (value: number | null | undefined) =>
  value == null || !Number.isFinite(Number(value)) ? "—" : `${number(Number(value) * 100, 1)}%`;

function MetricCard({
  title,
  value,
  note,
  icon,
}: {
  title: string;
  value: string;
  note: string;
  icon: ReactNode;
}) {
  return (
    <Card className="border-slate-200 shadow-sm">
      <CardContent className="flex items-start justify-between gap-3 p-4">
        <div className="min-w-0">
          <p className="text-sm text-slate-500">{title}</p>
          <p className="mt-1 whitespace-nowrap text-2xl font-semibold tabular-nums text-slate-900">{value}</p>
          <p className="mt-1 text-xs text-slate-500">{note}</p>
        </div>
        <div className="rounded-xl bg-blue-50 p-2.5 text-blue-600">{icon}</div>
      </CardContent>
    </Card>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="flex min-h-40 flex-col items-center justify-center rounded-lg border border-dashed border-slate-200 bg-slate-50/60 p-8 text-center">
      <AlertCircle className="mb-2 h-7 w-7 text-slate-400" />
      <p className="text-sm text-slate-600">{text}</p>
    </div>
  );
}

function CategoryPerformancePage() {
  const { stores, selectedStoreId, setSelectedStoreId } = useStore();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const initializedPeriodStoreRef = useRef<number | null>(null);
  const [period, setPeriod] = useState("");
  const [search, setSearch] = useState("");
  const [brandGroupCode, setBrandGroupCode] = useState("");
  const [brandManagerId, setBrandManagerId] = useState("");
  const [brandIsKey, setBrandIsKey] = useState("false");
  const [keyGroupCode, setKeyGroupCode] = useState("");
  const [keyManagerId, setKeyManagerId] = useState("");
  const [keyTarget, setKeyTarget] = useState("");
  const [targetManagerId, setTargetManagerId] = useState("");
  const [areaTarget, setAreaTarget] = useState("");
  const [areaWeight, setAreaWeight] = useState("40");
  const [keyWeight, setKeyWeight] = useState("40");
  const [selfWeight, setSelfWeight] = useState("20");
  const [selfScore, setSelfScore] = useState("");
  const [assessmentContent, setAssessmentContent] = useState("");
  const [isImporting, setIsImporting] = useState(false);
  const [lastImport, setLastImport] = useState<ImportResult | null>(null);

  useEffect(() => {
    if (!selectedStoreId && stores.length) {
      setSelectedStoreId(stores[0].storeId);
    }
  }, [selectedStoreId, setSelectedStoreId, stores]);

  const baseQuery = selectedStoreId && period
    ? `store_id=${selectedStoreId}&period=${encodeURIComponent(period)}`
    : "";

  const optionsQuery = useQuery<PerformanceOptions>({
    queryKey: ["category-performance-options", selectedStoreId],
    queryFn: () => apiGet(`/api/category-performance/options?store_id=${selectedStoreId}`),
    enabled: Boolean(selectedStoreId),
  });
  useEffect(() => {
    if (!selectedStoreId || !optionsQuery.data) return;
    if (initializedPeriodStoreRef.current === selectedStoreId) return;
    setPeriod(optionsQuery.data.latest_period ?? currentPeriod());
    initializedPeriodStoreRef.current = selectedStoreId;
  }, [optionsQuery.data, selectedStoreId]);

  const assignmentsQuery = useQuery<BrandAssignment[]>({
    queryKey: ["category-performance-assignments", selectedStoreId],
    queryFn: () => apiGet(`/api/category-performance/brand-assignments?store_id=${selectedStoreId}`),
    enabled: Boolean(selectedStoreId),
  });
  const keyTargetsQuery = useQuery<KeyBrandTarget[]>({
    queryKey: ["category-performance-key-targets", selectedStoreId, period],
    queryFn: () => apiGet(`/api/category-performance/key-brand-targets?${baseQuery}`),
    enabled: Boolean(baseQuery),
  });
  const managerTargetsQuery = useQuery<ManagerTarget[]>({
    queryKey: ["category-performance-manager-targets", selectedStoreId, period],
    queryFn: () => apiGet(`/api/category-performance/manager-targets?${baseQuery}`),
    enabled: Boolean(baseQuery),
  });
  const scorecardQuery = useQuery<Scorecard>({
    queryKey: ["category-performance-scorecard", selectedStoreId, period],
    queryFn: () => apiGet(`/api/category-performance/scorecard?${baseQuery}`),
    enabled: Boolean(baseQuery),
    refetchInterval: 5 * 60 * 1000,
  });

  const invalidateAll = async () => {
    await queryClient.invalidateQueries({
      predicate: (query) => String(query.queryKey[0] ?? "").startsWith("category-performance"),
    });
  };

  const brandMutation = useMutation({
    mutationFn: () =>
      apiPut(
        `/api/category-performance/brand-assignments/${encodeURIComponent(brandGroupCode)}?store_id=${selectedStoreId}`,
        {
          manager_user_id: Number(brandManagerId),
          is_active: true,
          is_key_brand: brandIsKey === "true",
        },
      ),
    onSuccess: async () => {
      toast({ title: "品牌主管已保存" });
      await invalidateAll();
    },
    onError: (error: Error) => toast({ title: "保存失败", description: error.message, variant: "destructive" }),
  });

  const keyMutation = useMutation({
    mutationFn: () =>
      apiPut(
        `/api/category-performance/key-brand-targets/${encodeURIComponent(keyGroupCode)}?${baseQuery}`,
        {
          manager_user_id: Number(keyManagerId),
          sales_target: Number(keyTarget),
          is_active: true,
        },
      ),
    onSuccess: async () => {
      toast({ title: "重点品牌目标已保存" });
      await invalidateAll();
    },
    onError: (error: Error) => toast({ title: "保存失败", description: error.message, variant: "destructive" }),
  });

  const managerMutation = useMutation({
    mutationFn: () =>
      apiPut(`/api/category-performance/manager-targets/${targetManagerId}?${baseQuery}`, {
        manager_user_id: Number(targetManagerId),
        area_revenue_target: Number(areaTarget),
        area_weight: Number(areaWeight),
        key_brand_weight: Number(keyWeight),
        self_weight: Number(selfWeight),
        self_score: selfScore === "" ? null : Number(selfScore),
        assessment_content: assessmentContent,
      }),
    onSuccess: async () => {
      toast({ title: "月度绩效参数已保存" });
      await invalidateAll();
    },
    onError: (error: Error) => toast({ title: "保存失败", description: error.message, variant: "destructive" }),
  });

  const options = optionsQuery.data;
  const assignments = assignmentsQuery.data ?? [];
  const keyTargets = keyTargetsQuery.data ?? [];
  const managerTargets = managerTargetsQuery.data ?? [];
  const scorecard = scorecardQuery.data;
  const scoreItems = scorecard?.items ?? [];
  const canManage = Boolean(options?.can_manage);
  const isLoading =
    optionsQuery.isLoading ||
    assignmentsQuery.isLoading ||
    keyTargetsQuery.isLoading ||
    managerTargetsQuery.isLoading ||
    scorecardQuery.isLoading;

  const assignedManagerIds = useMemo(
    () =>
      new Set([
        ...assignments.filter((item) => item.is_active).map((item) => item.manager_user_id),
        ...keyTargets.filter((item) => item.is_active).map((item) => item.manager_user_id),
      ]),
    [assignments, keyTargets],
  );
  const availableTargetManagers = useMemo(
    () => (options?.managers ?? []).filter((manager) => assignedManagerIds.has(manager.user_id)),
    [assignedManagerIds, options?.managers],
  );
  const filteredAssignments = useMemo(() => {
    const needle = search.trim().toLowerCase();
    if (!needle) return assignments;
    return assignments.filter((item) =>
      [
        item.group_code,
        item.group_name,
        item.department_name,
        item.manager_name,
        item.is_key_brand ? "重点品牌" : "普通品牌",
      ]
        .some((value) => String(value ?? "").toLowerCase().includes(needle)),
    );
  }, [assignments, search]);
  const keyBrandAssignmentCount = assignments.filter((item) => item.is_key_brand).length;

  const completeScores = scoreItems.filter((item) => item.score_complete && item.total_score != null);
  const averageScore = completeScores.length
    ? completeScores.reduce((sum, item) => sum + Number(item.total_score), 0) / completeScores.length
    : null;
  const highScoreCount = completeScores.filter((item) => Number(item.total_score) >= 100).length;
  const incompleteCount = scoreItems.length - completeScores.length;
  const chartData = [...completeScores]
    .sort((a, b) => Number(b.total_score) - Number(a.total_score))
    .slice(0, 20)
    .map((item) => ({ name: item.manager_name, score: Number(item.total_score) }));

  const loadManagerTarget = (target: ManagerTarget) => {
    setTargetManagerId(String(target.manager_user_id));
    setAreaTarget(String(target.area_revenue_target));
    setAreaWeight(String(target.area_weight));
    setKeyWeight(String(target.key_brand_weight));
    setSelfWeight(String(target.self_weight));
    setSelfScore(target.self_score == null ? "" : String(target.self_score));
    setAssessmentContent(target.assessment_content ?? "");
  };

  const importWorkbook = async (file: File) => {
    if (!selectedStoreId) return;
    setIsImporting(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(
        `${getApiUrl()}/api/category-performance/import-workbook?store_id=${selectedStoreId}&period=${encodeURIComponent(period)}`,
        { method: "POST", credentials: "include", body: formData },
      );
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const result = (await response.json()) as ImportResult;
      setLastImport(result);
      await invalidateAll();
      toast({
        title: "Excel导入完成",
        description:
          `品牌主管 ${result.imported.brand_assignments} 条，重点品牌 ${result.imported.key_brand_targets} 条，` +
          `月度参数 ${result.imported.manager_targets} 条；待确认 ${result.unmatched_count} 条。`,
      });
    } catch (error) {
      toast({
        title: "Excel导入失败",
        description: error instanceof Error ? error.message : "请检查文件格式",
        variant: "destructive",
      });
    } finally {
      setIsImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  if (!selectedStoreId && !stores.length) {
    return <div className="p-6"><EmptyState text="暂无可用门店，请先维护门店或检查账号数据范围。" /></div>;
  }

  return (
    <div className="space-y-4 p-3 md:p-6">
      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-semibold text-slate-900 md:text-2xl">
            <Target className="h-6 w-6 text-blue-600" />
            品类主管实时绩效
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            维护品牌责任人和重点品牌目标，系统按销售、收益及收费数据自动更新。
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <div className="min-w-44">
            <Label className="mb-1 block text-xs text-slate-500">门店</Label>
            <Select
              value={selectedStoreId ? String(selectedStoreId) : ""}
              onValueChange={(value) => {
                initializedPeriodStoreRef.current = null;
                setPeriod("");
                setSelectedStoreId(Number(value));
              }}
            >
              <SelectTrigger><SelectValue placeholder="选择门店" /></SelectTrigger>
              <SelectContent>
                {stores.map((store) => (
                  <SelectItem key={store.storeId} value={String(store.storeId)}>
                    {store.storeName}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="mb-1 block text-xs text-slate-500">绩效月份</Label>
            <Input type="month" value={period} onChange={(event) => setPeriod(event.target.value)} className="w-40" />
          </div>
          <Button variant="outline" onClick={() => void invalidateAll()} disabled={isLoading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
            刷新
          </Button>
          {canManage && (
            <>
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) void importWorkbook(file);
                }}
              />
              <Button onClick={() => fileInputRef.current?.click()} disabled={isImporting}>
                <Upload className="mr-2 h-4 w-4" />
                {isImporting ? "导入中…" : "导入绩效表"}
              </Button>
            </>
          )}
        </div>
      </div>

      {optionsQuery.error ? (
        <EmptyState text="绩效维护表尚未初始化或当前账号无权查看，请联系系统管理员。" />
      ) : (
        <Tabs defaultValue="scorecard" className="space-y-4">
          <TabsList className="grid h-auto w-full grid-cols-2 gap-1 p-1 lg:w-[720px] lg:grid-cols-4">
            <TabsTrigger value="scorecard">实时绩效</TabsTrigger>
            <TabsTrigger value="brands">品牌主管维护</TabsTrigger>
            <TabsTrigger value="keys">重点品牌维护</TabsTrigger>
            <TabsTrigger value="targets">月度绩效参数</TabsTrigger>
          </TabsList>

          <TabsContent value="scorecard" className="space-y-4">
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <MetricCard title="绩效主管" value={String(scoreItems.length)} note="当前月份已纳入" icon={<Users className="h-5 w-5" />} />
              <MetricCard title="平均得分" value={number(averageScore, 1)} note={`已完整评分 ${completeScores.length} 人`} icon={<BarChart3 className="h-5 w-5" />} />
              <MetricCard title="100分及以上" value={String(highScoreCount)} note="对应系数 1.2" icon={<Award className="h-5 w-5" />} />
              <MetricCard title="待补参数" value={String(incompleteCount)} note="目标或自定得分未齐" icon={<AlertCircle className="h-5 w-5" />} />
            </div>

            <Card>
              <CardHeader className="pb-2">
                <div className="flex flex-col gap-1 md:flex-row md:items-center md:justify-between">
                  <CardTitle className="text-base">主管绩效得分</CardTitle>
                  <div className="text-xs text-slate-500">
                    实际数据截至 {scorecard?.effective_end_date ?? "—"}；
                    销售 {scorecard?.latest_sales_date ?? "—"}，收费 {scorecard?.latest_fee_date ?? "—"}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {chartData.length ? (
                  <div className="h-72 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={chartData} margin={{ top: 10, right: 12, left: 0, bottom: 58 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="name" interval={0} angle={-40} textAnchor="end" height={70} fontSize={11} />
                        <YAxis fontSize={11} />
                        <Tooltip formatter={(value: number) => [`${number(value, 2)} 分`, "总分"]} />
                        <Bar dataKey="score" fill="#2563eb" radius={[5, 5, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <EmptyState text="尚无完整得分。请先维护品牌主管、重点品牌目标和月度绩效参数。" />
                )}
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="sticky left-0 min-w-24 bg-white">主管</TableHead>
                        <TableHead className="text-right">区域目标</TableHead>
                        <TableHead className="text-right">区域实际</TableHead>
                        <TableHead className="text-right">区域达成</TableHead>
                        <TableHead className="text-right">区域得分</TableHead>
                        <TableHead className="text-right">重点品牌</TableHead>
                        <TableHead className="text-right">销售目标</TableHead>
                        <TableHead className="text-right">销售实际</TableHead>
                        <TableHead className="text-right">重点得分</TableHead>
                        <TableHead className="text-right">自定得分</TableHead>
                        <TableHead className="text-right">总分</TableHead>
                        <TableHead className="text-right">系数</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {scoreItems.map((item) => (
                        <TableRow key={item.manager_user_id}>
                          <TableCell className="sticky left-0 bg-white font-medium">{item.manager_name}</TableCell>
                          <TableCell className="text-right tabular-nums">{number(item.area_target)}</TableCell>
                          <TableCell className="text-right tabular-nums">{number(item.area_actual)}</TableCell>
                          <TableCell className="text-right tabular-nums">{percent(item.area_rate)}</TableCell>
                          <TableCell className="text-right tabular-nums">{number(item.area_score)}</TableCell>
                          <TableCell className="text-right">{item.key_brand_count}</TableCell>
                          <TableCell className="text-right tabular-nums">{number(item.key_target)}</TableCell>
                          <TableCell className="text-right tabular-nums">{number(item.key_actual)}</TableCell>
                          <TableCell className="text-right tabular-nums">{number(item.key_score)}</TableCell>
                          <TableCell className="text-right tabular-nums">{number(item.self_score)}</TableCell>
                          <TableCell className="text-right font-semibold tabular-nums">
                            {item.score_complete ? number(item.total_score) : <Badge variant="outline">待补</Badge>}
                          </TableCell>
                          <TableCell className="text-right font-semibold tabular-nums">{number(item.coefficient, 1)}</TableCell>
                        </TableRow>
                      ))}
                      {!scoreItems.length && (
                        <TableRow><TableCell colSpan={12} className="h-28 text-center text-slate-500">暂无绩效记录</TableCell></TableRow>
                      )}
                    </TableBody>
                  </Table>
                </div>
                <div className="border-t bg-slate-50 px-4 py-3 text-xs leading-5 text-slate-500">
                  单位均为万元。区域实际＝分管品牌柜组不含税毛利＋收费＋已确认补录收益；重点品牌实际＝售价金额。
                  得分按达成率×权重计算且不封顶。
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="brands" className="space-y-4">
            {!canManage && <EmptyState text="当前账号只有查看权限；维护需授予“维护品类主管绩效”权限。" />}
            {canManage && (
              <Card>
                <CardHeader><CardTitle className="text-base">设置品牌对应品类主管</CardTitle></CardHeader>
                <CardContent className="grid gap-3 md:grid-cols-[1.3fr_1fr_160px_auto] md:items-end">
                  <div>
                    <Label>品牌柜组</Label>
                    <Select
                      value={brandGroupCode}
                      onValueChange={(value) => {
                        setBrandGroupCode(value);
                        const group = options?.groups.find((item) => item.group_code === value);
                        setBrandIsKey(group?.is_key_brand ? "true" : "false");
                      }}
                    >
                      <SelectTrigger className="mt-1"><SelectValue placeholder="选择品牌柜组" /></SelectTrigger>
                      <SelectContent>
                        {(options?.groups ?? []).map((group) => (
                          <SelectItem key={group.group_code} value={group.group_code}>
                            {group.is_key_brand ? "★ " : ""}{group.group_name}（{group.group_code}）
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>品类主管</Label>
                    <Select value={brandManagerId} onValueChange={setBrandManagerId}>
                      <SelectTrigger className="mt-1"><SelectValue placeholder="选择主管" /></SelectTrigger>
                      <SelectContent>
                        {(options?.managers ?? []).map((manager) => (
                          <SelectItem key={manager.user_id} value={String(manager.user_id)}>
                            {manager.real_name}{manager.employee_no ? `（${manager.employee_no}）` : ""}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>重点属性</Label>
                    <Select value={brandIsKey} onValueChange={setBrandIsKey}>
                      <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="true">重点品牌</SelectItem>
                        <SelectItem value="false">普通品牌</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <Button
                    onClick={() => brandMutation.mutate()}
                    disabled={!brandGroupCode || !brandManagerId || brandMutation.isPending}
                  >
                    <Save className="mr-2 h-4 w-4" />保存
                  </Button>
                </CardContent>
              </Card>
            )}
            <Card>
              <CardHeader className="pb-3">
                <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                  <CardTitle className="text-base">
                    已维护品牌（{assignments.length}，其中重点品牌 {keyBrandAssignmentCount}）
                  </CardTitle>
                  <div className="relative w-full md:w-72">
                    <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                    <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="搜索品牌、部门或主管" className="pl-9" />
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader><TableRow><TableHead>品牌柜组</TableHead><TableHead>部门</TableHead><TableHead>重点属性</TableHead><TableHead>品类主管</TableHead><TableHead>状态</TableHead><TableHead>更新时间</TableHead></TableRow></TableHeader>
                    <TableBody>
                      {filteredAssignments.map((item) => (
                        <TableRow
                          key={item.group_code}
                          className={canManage ? "cursor-pointer" : ""}
                          onClick={() => {
                            if (!canManage) return;
                            setBrandGroupCode(item.group_code);
                            setBrandManagerId(String(item.manager_user_id));
                            setBrandIsKey(item.is_key_brand ? "true" : "false");
                          }}
                        >
                          <TableCell><div className="font-medium">{item.group_name}</div><div className="text-xs text-slate-500">{item.group_code}</div></TableCell>
                          <TableCell>{item.department_name || "—"}</TableCell>
                          <TableCell>
                            {item.is_key_brand
                              ? <Badge className="bg-amber-500 text-white hover:bg-amber-500">重点品牌</Badge>
                              : <span className="text-slate-400">普通品牌</span>}
                          </TableCell>
                          <TableCell>{item.manager_name}</TableCell>
                          <TableCell>{item.is_active ? <Badge className="bg-emerald-600">有效</Badge> : <Badge variant="outline">停用</Badge>}</TableCell>
                          <TableCell className="whitespace-nowrap text-sm text-slate-500">{item.updated_at?.slice(0, 10)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="keys" className="space-y-4">
            {canManage && (
              <Card>
                <CardHeader><CardTitle className="text-base">设置重点品牌主管及月销售目标</CardTitle></CardHeader>
                <CardContent className="grid gap-3 lg:grid-cols-[1.3fr_1fr_180px_auto] lg:items-end">
                  <div>
                    <Label>重点品牌柜组</Label>
                    <Select value={keyGroupCode} onValueChange={setKeyGroupCode}>
                      <SelectTrigger className="mt-1"><SelectValue placeholder="选择品牌柜组" /></SelectTrigger>
                      <SelectContent>
                        {(options?.groups ?? []).map((group) => (
                          <SelectItem key={group.group_code} value={group.group_code}>
                            {group.is_key_brand ? "★ " : ""}{group.group_name}（{group.group_code}）
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>品类主管</Label>
                    <Select value={keyManagerId} onValueChange={setKeyManagerId}>
                      <SelectTrigger className="mt-1"><SelectValue placeholder="选择主管" /></SelectTrigger>
                      <SelectContent>
                        {(options?.managers ?? []).map((manager) => (
                          <SelectItem key={manager.user_id} value={String(manager.user_id)}>{manager.real_name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div><Label>销售目标（万元）</Label><Input className="mt-1" type="number" min="0" step="0.01" value={keyTarget} onChange={(event) => setKeyTarget(event.target.value)} /></div>
                  <Button onClick={() => keyMutation.mutate()} disabled={!keyGroupCode || !keyManagerId || keyTarget === "" || keyMutation.isPending}><Save className="mr-2 h-4 w-4" />保存</Button>
                </CardContent>
              </Card>
            )}
            <Card>
              <CardHeader><CardTitle className="text-base">{period} 重点品牌（{keyTargets.length}）</CardTitle></CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader><TableRow><TableHead>重点品牌</TableHead><TableHead>部门</TableHead><TableHead>品类主管</TableHead><TableHead className="text-right">销售目标（万元）</TableHead><TableHead>更新时间</TableHead></TableRow></TableHeader>
                    <TableBody>
                      {keyTargets.map((item) => (
                        <TableRow key={item.group_code} className={canManage ? "cursor-pointer" : ""} onClick={() => {
                          if (!canManage) return;
                          setKeyGroupCode(item.group_code);
                          setKeyManagerId(String(item.manager_user_id));
                          setKeyTarget(String(item.sales_target));
                        }}>
                          <TableCell><div className="font-medium">{item.group_name}</div><div className="text-xs text-slate-500">{item.group_code}</div></TableCell>
                          <TableCell>{item.department_name || "—"}</TableCell>
                          <TableCell>{item.manager_name}</TableCell>
                          <TableCell className="text-right font-medium tabular-nums">{number(item.sales_target)}</TableCell>
                          <TableCell className="whitespace-nowrap text-sm text-slate-500">{item.updated_at?.slice(0, 10)}</TableCell>
                        </TableRow>
                      ))}
                      {!keyTargets.length && <TableRow><TableCell colSpan={5} className="h-28 text-center text-slate-500">本月尚未维护重点品牌目标</TableCell></TableRow>}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="targets" className="space-y-4">
            {canManage && (
              <Card>
                <CardHeader><CardTitle className="text-base">设置主管月度目标、权重和自定得分</CardTitle></CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-6">
                    <div className="lg:col-span-2">
                      <Label>品类主管</Label>
                      <Select value={targetManagerId} onValueChange={setTargetManagerId}>
                        <SelectTrigger className="mt-1"><SelectValue placeholder="先维护主管负责的品牌" /></SelectTrigger>
                        <SelectContent>
                          {availableTargetManagers.map((manager) => (
                            <SelectItem key={manager.user_id} value={String(manager.user_id)}>{manager.real_name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div><Label>区域收益目标（万元）</Label><Input className="mt-1" type="number" min="0" step="0.01" value={areaTarget} onChange={(event) => setAreaTarget(event.target.value)} /></div>
                    <div><Label>区域权重</Label><Input className="mt-1" type="number" min="0" value={areaWeight} onChange={(event) => setAreaWeight(event.target.value)} /></div>
                    <div><Label>重点品牌权重</Label><Input className="mt-1" type="number" min="0" value={keyWeight} onChange={(event) => setKeyWeight(event.target.value)} /></div>
                    <div><Label>部门自定权重</Label><Input className="mt-1" type="number" min="0" value={selfWeight} onChange={(event) => setSelfWeight(event.target.value)} /></div>
                  </div>
                  <div className="grid gap-3 md:grid-cols-[180px_1fr_auto] md:items-end">
                    <div><Label>部门自定得分</Label><Input className="mt-1" type="number" min="0" value={selfScore} onChange={(event) => setSelfScore(event.target.value)} placeholder="可稍后补录" /></div>
                    <div><Label>考核内容</Label><Textarea className="mt-1 min-h-10" value={assessmentContent} onChange={(event) => setAssessmentContent(event.target.value)} /></div>
                    <Button onClick={() => managerMutation.mutate()} disabled={!targetManagerId || areaTarget === "" || managerMutation.isPending}><Save className="mr-2 h-4 w-4" />保存</Button>
                  </div>
                  <p className="text-xs text-slate-500">三项权重合计必须为100；部门自定得分不能超过部门自定权重。</p>
                </CardContent>
              </Card>
            )}
            <Card>
              <CardHeader><CardTitle className="text-base">{period} 月度绩效参数（{managerTargets.length}）</CardTitle></CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader><TableRow><TableHead>主管</TableHead><TableHead className="text-right">区域目标</TableHead><TableHead className="text-right">权重（区域/重点/自定）</TableHead><TableHead className="text-right">自定得分</TableHead><TableHead>考核内容</TableHead><TableHead>更新时间</TableHead></TableRow></TableHeader>
                    <TableBody>
                      {managerTargets.map((item) => (
                        <TableRow key={item.manager_user_id} className={canManage ? "cursor-pointer" : ""} onClick={() => canManage && loadManagerTarget(item)}>
                          <TableCell className="font-medium">{item.manager_name}</TableCell>
                          <TableCell className="text-right tabular-nums">{number(item.area_revenue_target)}</TableCell>
                          <TableCell className="text-right tabular-nums">{number(item.area_weight, 0)} / {number(item.key_brand_weight, 0)} / {number(item.self_weight, 0)}</TableCell>
                          <TableCell className="text-right tabular-nums">{number(item.self_score)}</TableCell>
                          <TableCell className="max-w-72 truncate" title={item.assessment_content ?? ""}>{item.assessment_content || "—"}</TableCell>
                          <TableCell className="whitespace-nowrap text-sm text-slate-500">{item.updated_at?.slice(0, 10)}</TableCell>
                        </TableRow>
                      ))}
                      {!managerTargets.length && <TableRow><TableCell colSpan={6} className="h-28 text-center text-slate-500">本月尚未维护主管绩效参数</TableCell></TableRow>}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}

      {lastImport && (
        <Card className={lastImport.unmatched_count ? "border-amber-200 bg-amber-50/50" : "border-emerald-200 bg-emerald-50/50"}>
          <CardContent className="p-4">
            <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
              <div>
                <p className="font-medium text-slate-900">
                  最近一次导入：品牌主管 {lastImport.imported.brand_assignments} 条，重点品牌 {lastImport.imported.key_brand_targets} 条，
                  月度参数 {lastImport.imported.manager_targets} 条
                </p>
                <p className="mt-1 text-sm text-slate-600">
                  {lastImport.unmatched_count
                    ? `另有 ${lastImport.unmatched_count} 条因品牌重名或账号未匹配而未自动写入，请按ERP柜组编码人工确认。`
                    : "全部记录已匹配。"}
                </p>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setLastImport(null)}>关闭</Button>
            </div>
            {lastImport.unmatched.length > 0 && (
              <div className="mt-3 max-h-36 overflow-auto rounded-md border border-amber-200 bg-white">
                {lastImport.unmatched.map((item, index) => (
                  <div key={`${item.sheet}-${item.brand}-${index}`} className="grid grid-cols-[1fr_1fr_auto] gap-2 border-b px-3 py-2 text-xs last:border-0">
                    <span className="truncate" title={item.brand}>{item.brand}</span>
                    <span>{item.manager}</span>
                    <span className="text-slate-500">{item.sheet}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {isLoading && (
        <div className="fixed bottom-5 right-5 flex items-center gap-2 rounded-full bg-slate-900 px-4 py-2 text-sm text-white shadow-lg">
          <RefreshCw className="h-4 w-4 animate-spin" />正在更新实时绩效
        </div>
      )}
      {!isLoading && scorecard && (
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          已加载 {scorecard.store.store_name} {scorecard.period} 实时绩效
          <FileSpreadsheet className="ml-2 h-4 w-4" />
          支持导入现有“中心月度绩效-品类”格式
        </div>
      )}
    </div>
  );
}

export default CategoryPerformancePage;
