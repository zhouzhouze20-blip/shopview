import { useEffect, useMemo, useState } from "react";
import { BarChart3, Building2, ClipboardList, Loader2, Plus, Save, Target } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { useBaseMapsList, useFloorDictList } from "@/hooks/useBaseMaps";
import { useGeoElements } from "@/hooks/useGeoElements";
import { useUnitMapVersions, useAlignTransform } from "@/hooks/useUnitMapVersions";
import { useStore } from "@/contexts/StoreContext";
import { resolveApiAssetUrl } from "@/lib/api";
import { deriveSvgViewBox } from "@/lib/svg-metadata";
import { getPathVisualCenter } from "@/lib/svg-path-center";
import { candidateMapStyle, candidateTypeText } from "@/lib/merchant-planning-map";
import {
  MerchantCandidate,
  MerchantCalculationInput,
  MerchantOpportunity,
  MerchantOpportunityStatus,
  useCreateMerchantFollowUp,
  useCreateMerchantOpportunity,
  useCreateMerchantPlanningProject,
  useMerchantCandidates,
  useMerchantOpportunities,
  useMerchantOverview,
  usePreviewMerchantCalculation,
  useUpdateMerchantOpportunity,
} from "@/hooks/useMerchantPlanning";

const money = (value?: number | string | null) =>
  new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 0 }).format(Number(value ?? 0));

const statusText: Record<MerchantOpportunityStatus, string> = {
  TODO: "待招商",
  NEGOTIATING: "洽谈中",
  SIGNED: "已签约",
  ABANDONED: "放弃",
};

const priorityText = {
  P0: "立即跟进",
  P1: "优先跟进",
  P2: "常规跟进",
};

const getFloorStoreRef = (floor: { store_id?: string | null; building_code?: string | null }) =>
  floor.store_id?.trim() || floor.building_code?.trim() || "";

const parseViewBox = (value?: string | null) => {
  if (!value) return null;
  const parts = value.split(/[\s,]+/).map(Number);
  if (parts.length !== 4 || parts.some((item) => !Number.isFinite(item))) return null;
  return { x: parts[0], y: parts[1], w: parts[2], h: parts[3] };
};

export default function MerchantPlanningPage() {
  const [tab, setTab] = useState("overview");
  const overview = useMerchantOverview();
  const opportunities = useMerchantOpportunities();

  useEffect(() => {
    const searchParams = new URLSearchParams(window.location.search);
    if (searchParams.get("merchantTab") === "single" || searchParams.get("merchant_unit_id")) {
      setTab("single");
    }
  }, []);

  return (
    <div className="container mx-auto space-y-4 p-4" data-testid="merchant-planning-page">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">招商规划</h1>
          <p className="text-xs text-muted-foreground">基于收益地图识别机会，按合同条件测算招商收益。</p>
        </div>
      </div>

      <Tabs value={tab} onValueChange={setTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">规划总览</TabsTrigger>
          <TabsTrigger value="single">铺位补位</TabsTrigger>
          <TabsTrigger value="floor">整层/片区规划</TabsTrigger>
          <TabsTrigger value="pool">招商机会池</TabsTrigger>
        </TabsList>
        <TabsContent value="overview">
          <OverviewSection loading={overview.isLoading} data={overview.data} opportunities={opportunities.data ?? []} />
        </TabsContent>
        <TabsContent value="single">
          <SingleUnitSection />
        </TabsContent>
        <TabsContent value="floor">
          <FloorPlanningSection opportunities={opportunities.data ?? []} />
        </TabsContent>
        <TabsContent value="pool">
          <OpportunityPool opportunities={opportunities.data ?? []} loading={opportunities.isLoading} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function OverviewSection({
  loading,
  data,
  opportunities,
}: {
  loading: boolean;
  data?: { by_status: Record<string, number>; estimated_lift_amount: number; opportunity_count: number };
  opportunities: MerchantOpportunity[];
}) {
  const counts = data?.by_status ?? {};
  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-5">
        <MetricCard title="机会总数" value={loading ? "加载中" : String(data?.opportunity_count ?? 0)} icon={<ClipboardList className="h-4 w-4" />} />
        <MetricCard title="待招商" value={String(counts.TODO ?? 0)} icon={<Target className="h-4 w-4" />} />
        <MetricCard title="洽谈中" value={String(counts.NEGOTIATING ?? 0)} icon={<BarChart3 className="h-4 w-4" />} />
        <MetricCard title="已签约" value={String(counts.SIGNED ?? 0)} icon={<Save className="h-4 w-4" />} />
        <MetricCard title="预计提升" value={money(data?.estimated_lift_amount)} icon={<Plus className="h-4 w-4" />} />
      </div>
      <OpportunityPool opportunities={opportunities.slice(0, 8)} loading={loading} compact />
    </div>
  );
}

function MetricCard({ title, value, icon }: { title: string; value: string; icon: React.ReactNode }) {
  return (
    <Card className="rounded-md">
      <CardContent className="flex items-center justify-between px-4 py-3">
        <div>
          <div className="text-xs text-muted-foreground">{title}</div>
          <div className="mt-1 text-xl font-semibold">{value}</div>
        </div>
        <div className="text-muted-foreground">{icon}</div>
      </CardContent>
    </Card>
  );
}

function SingleUnitSection() {
  const searchParams = useMemo(() => new URLSearchParams(window.location.search), []);
  const { stores, selectedStoreId } = useStore();
  const [candidateType, setCandidateType] = useState("ALL");
  const [selected, setSelected] = useState<MerchantCandidate | null>(null);
  const floorsQuery = useFloorDictList();
  const floors = floorsQuery.data ?? [];
  const storeOptions = useMemo(() => {
    const options = stores.map((store) => ({
      value: String(store.storeCode || store.storeId),
      label: store.storeName || store.storeCode || String(store.storeId),
      code: store.storeCode ? String(store.storeCode) : String(store.storeId),
    }));
    const knownRefs = new Set(options.flatMap((store) => [store.value, store.code]).filter(Boolean));
    floors.forEach((floor) => {
      const storeRef = getFloorStoreRef(floor);
      if (!storeRef || knownRefs.has(storeRef)) return;
      knownRefs.add(storeRef);
      options.push({ value: storeRef, label: `门店 ${storeRef}`, code: storeRef });
    });
    return options;
  }, [floors, stores]);
  const initialStoreId = searchParams.get("merchant_store_id") || (selectedStoreId ? String(selectedStoreId) : "");
  const [storeId, setStoreId] = useState(initialStoreId);
  const floorIdValue = searchParams.get("merchant_floor_id");
  const [floorId, setFloorId] = useState<number | null>(floorIdValue ? Number(floorIdValue) : null);
  const targetUnitId = searchParams.get("merchant_unit_id");
  const candidates = useMerchantCandidates({ storeId, floorId, candidateType });
  const selectedStoreOption = useMemo(
    () => storeOptions.find((store) => store.value === storeId || store.code === storeId),
    [storeId, storeOptions],
  );
  const visibleFloorOptions = useMemo(() => {
    if (!storeId) return [];
    return floors.filter((floor) => {
      const storeRef = getFloorStoreRef(floor);
      return storeRef === storeId || storeRef === selectedStoreOption?.code;
    });
  }, [floors, selectedStoreOption?.code, storeId]);

  useEffect(() => {
    if (storeId || !storeOptions.length) return;
    setStoreId(storeOptions[0].value);
  }, [storeId, storeOptions]);

  useEffect(() => {
    if (!storeId || !storeOptions.length) return;
    const exists = storeOptions.some((store) => store.value === storeId || store.code === storeId);
    if (!exists) setStoreId(storeOptions[0].value);
  }, [storeId, storeOptions]);

  useEffect(() => {
    if (!storeId) return;
    if (floorId != null && visibleFloorOptions.some((floor) => floor.id === floorId)) return;
    setFloorId(visibleFloorOptions[0]?.id ?? null);
  }, [floorId, storeId, visibleFloorOptions]);

  useEffect(() => {
    if (!targetUnitId || selected || !candidates.data?.items?.length) return;
    const matched = candidates.data.items.find((item) => String(item.unit_id) === targetUnitId);
    if (matched) setSelected(matched);
  }, [candidates.data?.items, selected, targetUnitId]);

  return (
    <div className="space-y-4">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
        <Card className="rounded-md">
          <CardHeader>
            <div className="grid gap-3 lg:grid-cols-[1fr_1fr_160px]">
              <div className="space-y-1">
                <Label>门店</Label>
                <Select value={storeId} onValueChange={(value) => {
                  setStoreId(value);
                  setSelected(null);
                  setFloorId(null);
                }}>
                  <SelectTrigger>
                    <SelectValue placeholder="选择门店" />
                  </SelectTrigger>
                  <SelectContent>
                    {storeOptions.map((store) => (
                      <SelectItem key={store.value} value={store.value}>
                        {store.code ? `${store.code} ${store.label}` : store.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label>楼层</Label>
                <Select value={floorId ? String(floorId) : ""} onValueChange={(value) => {
                  setFloorId(Number(value));
                  setSelected(null);
                }}>
                  <SelectTrigger>
                    <SelectValue placeholder="选择楼层" />
                  </SelectTrigger>
                  <SelectContent>
                    {visibleFloorOptions.map((floor) => (
                      <SelectItem key={floor.id} value={String(floor.id)}>
                        {floor.building_code}-{floor.floor_code} {floor.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label>候选类型</Label>
                <Select value={candidateType} onValueChange={(value) => {
                  setCandidateType(value);
                  setSelected(null);
                }}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">全部</SelectItem>
                    <SelectItem value="VACANT">空置</SelectItem>
                    <SelectItem value="LOW_EFFICIENCY">低效</SelectItem>
                    <SelectItem value="EXPIRING">到期</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <MerchantPlanningMap
              floorId={floorId}
              candidates={candidates.data?.items ?? []}
              loading={candidates.isLoading}
              selectedId={selected?.unit_id}
              onSelect={setSelected}
            />
          </CardContent>
        </Card>
        <OpportunityForm candidate={selected} />
      </div>
      <Card className="rounded-md">
        <CardHeader><CardTitle>候选铺位明细</CardTitle></CardHeader>
        <CardContent>
          <CandidateTable items={candidates.data?.items ?? []} loading={candidates.isLoading} onSelect={setSelected} selectedId={selected?.unit_id} />
        </CardContent>
      </Card>
    </div>
  );
}

function MerchantPlanningMap({
  floorId,
  candidates,
  loading,
  selectedId,
  onSelect,
}: {
  floorId: number | null;
  candidates: MerchantCandidate[];
  loading: boolean;
  selectedId?: number;
  onSelect: (row: MerchantCandidate) => void;
}) {
  const baseMapsQuery = useBaseMapsList(floorId ?? undefined);
  const baseMaps = baseMapsQuery.data ?? [];
  const activeBaseMap = baseMaps.find((item) => item.is_active) ?? baseMaps[0];
  const unitVersionsQuery = useUnitMapVersions(floorId ?? undefined, activeBaseMap?.id);
  const versions = unitVersionsQuery.data ?? [];
  const activeVersion = versions.find((item) => item.is_active) ?? versions[0];
  const geoQuery = useGeoElements(activeVersion?.id);
  const alignQuery = useAlignTransform(activeVersion?.id);
  const geoRows = geoQuery.data ?? [];
  const candidateByUnitId = useMemo(
    () => new Map(candidates.map((candidate) => [candidate.unit_id, candidate])),
    [candidates],
  );
  const svgViewBox = deriveSvgViewBox({
    viewBox: activeBaseMap?.svg_viewbox ?? null,
    width: activeBaseMap?.svg_width ?? null,
    height: activeBaseMap?.svg_height ?? null,
  });
  const vb = parseViewBox(svgViewBox);
  const selectedCandidate = selectedId != null ? candidateByUnitId.get(selectedId) : null;
  const counts = useMemo(() => {
    const next = { VACANT: 0, LOW_EFFICIENCY: 0, EXPIRING: 0, NORMAL: 0 };
    candidates.forEach((candidate) => {
      const key = (candidate.candidate_type || "NORMAL") as keyof typeof next;
      next[key] = (next[key] ?? 0) + 1;
    });
    return next;
  }, [candidates]);
  const align = alignQuery.data;
  const alignTransform = align
    ? `translate(${align.dx} ${align.dy}) rotate(${align.rotate}) scale(${align.sx} ${align.sy})`
    : undefined;
  const baseMapUrl = resolveApiAssetUrl(activeBaseMap?.file_url);

  if (!floorId) {
    return <div className="py-16 text-center text-sm text-muted-foreground">请选择门店和楼层</div>;
  }

  if (loading || baseMapsQuery.isLoading || unitVersionsQuery.isLoading || geoQuery.isLoading) {
    return <div className="py-16 text-center text-sm text-muted-foreground">加载中</div>;
  }

  if (!activeBaseMap || !activeVersion || !vb) {
    return <div className="py-16 text-center text-sm text-muted-foreground">当前楼层没有可用招商地图</div>;
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
        <div className="flex flex-wrap gap-2">
          <Badge variant="secondary">空置 {counts.VACANT}</Badge>
          <Badge variant="secondary">低效 {counts.LOW_EFFICIENCY}</Badge>
          <Badge variant="secondary">到期 {counts.EXPIRING}</Badge>
          <Badge variant="outline">普通 {counts.NORMAL}</Badge>
        </div>
        {selectedCandidate ? (
          <div className="font-medium text-slate-700">
            已选 {selectedCandidate.unit_code || selectedCandidate.unit_id} · {candidateTypeText(selectedCandidate.candidate_type)}
          </div>
        ) : null}
      </div>
      <div className="relative h-[560px] overflow-hidden rounded-md border bg-slate-50">
        <svg viewBox={svgViewBox ?? undefined} className="h-full w-full">
          {baseMapUrl ? <image href={baseMapUrl} x={vb.x} y={vb.y} width={vb.w} height={vb.h} /> : null}
          <g transform={alignTransform}>
            {geoRows.map((geo) => {
              const candidate = candidateByUnitId.get(geo.unit_id);
              const selected = selectedId === geo.unit_id;
              const style = candidateMapStyle(candidate?.candidate_type, selected);
              return (
                <path
                  key={geo.id}
                  d={geo.path_data}
                  fill={style.fill}
                  stroke={style.stroke}
                  strokeWidth={selected ? 4 : candidate ? 2.75 : 1.6}
                  vectorEffect="non-scaling-stroke"
                  className={candidate ? "cursor-pointer transition-colors hover:brightness-110" : "opacity-45"}
                  onClick={() => {
                    if (candidate) onSelect(candidate);
                  }}
                />
              );
            })}
            {geoRows.map((geo) => {
              const candidate = candidateByUnitId.get(geo.unit_id);
              if (!candidate) return null;
              const point = getPathVisualCenter(geo.path_data);
              if (!point) return null;
              const style = candidateMapStyle(candidate.candidate_type, selectedId === geo.unit_id);
              return (
                <text
                  key={`label-${geo.id}`}
                  x={point.x}
                  y={point.y}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  className="pointer-events-none select-none"
                  fill={style.text}
                  fontSize={12}
                  fontWeight={700}
                  paintOrder="stroke"
                  stroke="rgba(255,255,255,0.78)"
                  strokeWidth={2.5}
                >
                  {candidate.unit_code || candidate.unit_id}
                </text>
              );
            })}
          </g>
        </svg>
      </div>
    </div>
  );
}

function CandidateTable({
  items,
  loading,
  selectedId,
  onSelect,
}: {
  items: MerchantCandidate[];
  loading: boolean;
  selectedId?: number;
  onSelect: (row: MerchantCandidate) => void;
}) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>铺位</TableHead>
          <TableHead>楼层</TableHead>
          <TableHead>面积</TableHead>
          <TableHead>当前合同</TableHead>
          <TableHead className="text-right">周期收益</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {loading ? (
          <TableRow>
            <TableCell colSpan={5} className="py-8 text-center text-muted-foreground">加载中</TableCell>
          </TableRow>
        ) : items.length ? (
          items.map((row) => (
            <TableRow
              key={row.unit_id}
              className={selectedId === row.unit_id ? "bg-cyan-50" : "cursor-pointer"}
              onClick={() => onSelect(row)}
            >
              <TableCell className="font-medium">{row.unit_code || row.unit_id}</TableCell>
              <TableCell>{row.floor_id ?? "-"}</TableCell>
              <TableCell>{row.unit_area ?? "-"}</TableCell>
              <TableCell>{row.current_contract_id || <Badge variant="secondary">空置</Badge>}</TableCell>
              <TableCell className="text-right">{money(row.period_revenue)}</TableCell>
            </TableRow>
          ))
        ) : (
          <TableRow>
            <TableCell colSpan={5} className="py-8 text-center text-muted-foreground">暂无候选铺位</TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
  );
}

function OpportunityForm({ candidate }: { candidate: MerchantCandidate | null }) {
  const { toast } = useToast();
  const preview = usePreviewMerchantCalculation();
  const createOpportunity = useCreateMerchantOpportunity();
  const [form, setForm] = useState({
    target_category: "",
    target_brand: "",
    cooperation_mode: "LEASE",
    monthly_rent: "",
    rent_unit_price: "",
    commission_rate: "",
    guaranteed_amount: "",
    expected_monthly_sales: "",
    manual_monthly_revenue: "",
    decoration_days: "0",
    vacancy_days: "0",
    expected_sign_date: "",
    priority: "P2",
    remark: "",
  });

  const calculationInput = useMemo<MerchantCalculationInput>(() => ({
    cooperation_mode: form.cooperation_mode as MerchantCalculationInput["cooperation_mode"],
    unit_area: Number(candidate?.unit_area ?? 0),
    current_annual_revenue: Number(candidate?.period_revenue ?? 0),
    monthly_rent: form.monthly_rent ? Number(form.monthly_rent) : null,
    rent_unit_price: form.rent_unit_price ? Number(form.rent_unit_price) : null,
    commission_rate: form.commission_rate ? Number(form.commission_rate) : null,
    guaranteed_amount: form.guaranteed_amount ? Number(form.guaranteed_amount) : null,
    expected_monthly_sales: form.expected_monthly_sales ? Number(form.expected_monthly_sales) : null,
    manual_monthly_revenue: form.manual_monthly_revenue ? Number(form.manual_monthly_revenue) : null,
    decoration_days: Number(form.decoration_days || 0),
    vacancy_days: Number(form.vacancy_days || 0),
  }), [candidate, form]);

  const submit = async () => {
    if (!candidate) return;
    await createOpportunity.mutateAsync({
      source_type: "MANUAL",
      store_id: candidate.store_id ?? null,
      floor_id: candidate.floor_id ?? null,
      unit_id: candidate.unit_id,
      unit_code: candidate.unit_code ?? null,
      unit_area: candidate.unit_area ?? null,
      current_brand: candidate.current_brand ?? null,
      current_contract_id: candidate.current_contract_id ?? null,
      current_annual_revenue: Number(candidate.period_revenue ?? 0),
      target_category: form.target_category || null,
      target_brand: form.target_brand || null,
      expected_sign_date: form.expected_sign_date || null,
      priority: form.priority as "P0" | "P1" | "P2",
      remark: form.remark || null,
      calculation: calculationInput,
    });
    toast({ title: "招商机会已创建" });
  };

  return (
    <Card className="rounded-md">
      <CardHeader><CardTitle>合同测算</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        {!candidate ? <div className="py-8 text-center text-sm text-muted-foreground">先选择一个候选铺位</div> : null}
        {candidate ? (
          <div className="rounded-md border bg-slate-50 p-3 text-xs text-slate-600">
            {candidate.unit_code || candidate.unit_id} / 当前周期收益 {money(candidate.period_revenue)}
          </div>
        ) : null}
        <div className="grid grid-cols-2 gap-3">
          <Field label="目标业态" value={form.target_category} onChange={(value) => setForm({ ...form, target_category: value })} />
          <Field label="目标品牌" value={form.target_brand} onChange={(value) => setForm({ ...form, target_brand: value })} />
        </div>
        <div className="space-y-1">
          <Label>合作模式</Label>
          <Select value={form.cooperation_mode} onValueChange={(value) => setForm({ ...form, cooperation_mode: value })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="LEASE">租赁</SelectItem>
              <SelectItem value="JOINT_OPERATION">联营</SelectItem>
              <SelectItem value="OTHER">其他</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="月租金" value={form.monthly_rent} onChange={(value) => setForm({ ...form, monthly_rent: value })} />
          <Field label="租金单价" value={form.rent_unit_price} onChange={(value) => setForm({ ...form, rent_unit_price: value })} />
          <Field label="扣点" value={form.commission_rate} onChange={(value) => setForm({ ...form, commission_rate: value })} />
          <Field label="保底金额" value={form.guaranteed_amount} onChange={(value) => setForm({ ...form, guaranteed_amount: value })} />
          <Field label="预计月销售额" value={form.expected_monthly_sales} onChange={(value) => setForm({ ...form, expected_monthly_sales: value })} />
          <Field label="手填月收益" value={form.manual_monthly_revenue} onChange={(value) => setForm({ ...form, manual_monthly_revenue: value })} />
          <Field label="装修期天数" value={form.decoration_days} onChange={(value) => setForm({ ...form, decoration_days: value })} />
          <Field label="空置期天数" value={form.vacancy_days} onChange={(value) => setForm({ ...form, vacancy_days: value })} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="预计签约日期" type="date" value={form.expected_sign_date} onChange={(value) => setForm({ ...form, expected_sign_date: value })} />
          <div className="space-y-1">
            <Label>优先级</Label>
            <Select value={form.priority} onValueChange={(value) => setForm({ ...form, priority: value })}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="P0">P0 立即</SelectItem>
                <SelectItem value="P1">P1 优先</SelectItem>
                <SelectItem value="P2">P2 常规</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <Textarea placeholder="备注" value={form.remark} onChange={(event) => setForm({ ...form, remark: event.target.value })} />
        <div className="flex gap-2">
          <Button variant="outline" disabled={!candidate || preview.isPending} onClick={() => preview.mutate(calculationInput)}>
            {preview.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            预览测算
          </Button>
          <Button disabled={!candidate || createOpportunity.isPending} onClick={submit}>创建机会</Button>
        </div>
        {preview.data ? (
          <div className="rounded-md border bg-slate-50 p-3 text-sm">
            年收益 {money(preview.data.estimated_annual_revenue)}，提升 {money(preview.data.estimated_lift_amount)}，有效月数 {preview.data.effective_months}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function Field({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (value: string) => void; type?: string }) {
  return (
    <div className="space-y-1">
      <Label>{label}</Label>
      <Input type={type} value={value} onChange={(event) => onChange(event.target.value)} />
    </div>
  );
}

function FloorPlanningSection({ opportunities }: { opportunities: MerchantOpportunity[] }) {
  const { toast } = useToast();
  const createProject = useCreateMerchantPlanningProject();
  const [form, setForm] = useState({
    name: "",
    store_id: "",
    floor_ids: "",
    scope_type: "FLOOR",
    target_description: "",
  });
  const draftOpportunityIds = opportunities.filter((item) => item.status !== "ABANDONED").map((item) => item.id);
  const totalCurrent = opportunities.reduce((sum, item) => sum + Number(item.current_annual_revenue || 0), 0);
  const totalEstimated = opportunities.reduce((sum, item) => sum + Number(item.estimated_annual_revenue || 0), 0);

  const submit = async () => {
    const floorIds = form.floor_ids
      .split(",")
      .map((item) => Number(item.trim()))
      .filter((item) => Number.isFinite(item));
    await createProject.mutateAsync({
      name: form.name || "招商规划项目",
      store_id: form.store_id || null,
      floor_ids: floorIds,
      scope_type: form.scope_type as "FLOOR" | "MULTI_FLOOR" | "AREA",
      target_description: form.target_description || null,
      opportunity_ids: draftOpportunityIds,
    });
    toast({ title: "招商规划项目已创建" });
  };

  return (
    <div className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
      <Card className="rounded-md">
        <CardHeader><CardTitle>规划范围</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <Field label="规划名称" value={form.name} onChange={(value) => setForm({ ...form, name: value })} />
          <Field label="门店编码" value={form.store_id} onChange={(value) => setForm({ ...form, store_id: value })} />
          <Field label="楼层ID，多个用逗号分隔" value={form.floor_ids} onChange={(value) => setForm({ ...form, floor_ids: value })} />
          <div className="space-y-1">
            <Label>规划类型</Label>
            <Select value={form.scope_type} onValueChange={(value) => setForm({ ...form, scope_type: value })}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="FLOOR">单楼层</SelectItem>
                <SelectItem value="MULTI_FLOOR">多楼层</SelectItem>
                <SelectItem value="AREA">片区</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Textarea
            placeholder="规划目标，例如降低空置、引入运动潮流业态"
            value={form.target_description}
            onChange={(event) => setForm({ ...form, target_description: event.target.value })}
          />
          <Button className="w-full" disabled={createProject.isPending} onClick={submit}>创建整层规划</Button>
        </CardContent>
      </Card>
      <Card className="rounded-md">
        <CardHeader><CardTitle>整层测算汇总</CardTitle></CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3">
          <MetricCard title="纳入机会" value={String(draftOpportunityIds.length)} icon={<Building2 className="h-4 w-4" />} />
          <MetricCard title="当前年收益" value={money(totalCurrent)} icon={<BarChart3 className="h-4 w-4" />} />
          <MetricCard title="预计年收益" value={money(totalEstimated)} icon={<Target className="h-4 w-4" />} />
        </CardContent>
      </Card>
    </div>
  );
}

function OpportunityPool({ opportunities, loading, compact = false }: { opportunities: MerchantOpportunity[]; loading: boolean; compact?: boolean }) {
  const updateOpportunity = useUpdateMerchantOpportunity();
  const createFollowUp = useCreateMerchantFollowUp();
  const { toast } = useToast();
  const [followText, setFollowText] = useState("");

  const updateStatus = async (item: MerchantOpportunity, status: MerchantOpportunityStatus) => {
    await updateOpportunity.mutateAsync({ id: item.id, input: { status } });
    toast({ title: "机会状态已更新" });
  };

  const addFollowUp = async (item: MerchantOpportunity) => {
    if (!followText.trim()) return;
    await createFollowUp.mutateAsync({ id: item.id, input: { content: followText.trim(), follow_up_type: "NOTE" } });
    setFollowText("");
    toast({ title: "跟进记录已添加" });
  };

  return (
    <Card className="rounded-md">
      <CardHeader><CardTitle>{compact ? "最近机会" : "招商机会池"}</CardTitle></CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>铺位</TableHead>
              <TableHead>目标</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>优先级</TableHead>
              <TableHead className="text-right">预计提升</TableHead>
              {!compact ? <TableHead>跟进</TableHead> : null}
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={compact ? 5 : 6} className="py-8 text-center text-muted-foreground">加载中</TableCell>
              </TableRow>
            ) : opportunities.length ? (
              opportunities.map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="font-medium">{item.unit_code || item.unit_id || "-"}</TableCell>
                  <TableCell>{item.target_brand || item.target_category || "-"}</TableCell>
                  <TableCell>
                    {compact ? (
                      <Badge variant="outline">{statusText[item.status] ?? item.status}</Badge>
                    ) : (
                      <Select value={item.status} onValueChange={(value) => updateStatus(item, value as MerchantOpportunityStatus)}>
                        <SelectTrigger className="h-8 w-28"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="TODO">待招商</SelectItem>
                          <SelectItem value="NEGOTIATING">洽谈中</SelectItem>
                          <SelectItem value="SIGNED">已签约</SelectItem>
                          <SelectItem value="ABANDONED">放弃</SelectItem>
                        </SelectContent>
                      </Select>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant={item.priority === "P0" ? "destructive" : "secondary"}>{priorityText[item.priority] ?? item.priority}</Badge>
                  </TableCell>
                  <TableCell className="text-right">{money(item.estimated_lift_amount)}</TableCell>
                  {!compact ? (
                    <TableCell>
                      <div className="flex max-w-md gap-2">
                        <Input value={followText} onChange={(event) => setFollowText(event.target.value)} placeholder="记录本次跟进" />
                        <Button variant="outline" size="sm" onClick={() => addFollowUp(item)}>保存</Button>
                      </div>
                    </TableCell>
                  ) : null}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={compact ? 5 : 6} className="py-8 text-center text-muted-foreground">暂无招商机会</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
