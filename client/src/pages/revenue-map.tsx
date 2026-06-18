import { useEffect, useMemo, useRef, useState, type PointerEvent } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { useBaseMapsList, useFloorDictList } from "@/hooks/useBaseMaps";
import { useBusinessUnits } from "@/hooks/useBusinessUnits";
import { useGeoElements } from "@/hooks/useGeoElements";
import { useAlignTransform, useUnitMapVersions } from "@/hooks/useUnitMapVersions";
import { useStore } from "@/contexts/StoreContext";
import {
  RevenueMonthlyItem,
  useConfirmRevenueExtraReceipt,
  useCreateRevenueExtraReceipt,
  useRecalculateRevenue,
  useRevenueExtraReceipts,
  useRevenueMonthly,
  useRevenueUnitDetail,
  useVoidRevenueExtraReceipt,
} from "@/hooks/useRevenue";
import { resolveApiAssetUrl } from "@/lib/api";
import { deriveSvgViewBox } from "@/lib/svg-metadata";
import { getPathVisualCenter } from "@/lib/svg-path-center";
import { CalendarDays, CheckCircle2, CircleDollarSign, Loader2, Minus, Plus, RefreshCw, RotateCcw, Settings2, Target, XCircle } from "lucide-react";

const money = (value: number) =>
  Number(value || 0).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const todayMonth = () => new Date().toISOString().slice(0, 7);
const todayDate = () => new Date().toISOString().slice(0, 10);
const getFloorStoreRef = (floor: { store_id?: string | null; building_code?: string | null }) =>
  floor.store_id?.trim() || floor.building_code?.trim() || "";
const parseViewBox = (value?: string | null) => {
  if (!value) return null;
  const parts = value.split(/[\s,]+/).map(Number);
  if (parts.length !== 4 || parts.some((item) => !Number.isFinite(item))) return null;
  return { x: parts[0], y: parts[1], w: parts[2], h: parts[3] };
};
function amountClass(value: number) {
  if (value < 0) return "text-red-600";
  if (value > 0) return "text-slate-900";
  return "text-slate-500";
}

type RevenueColorMode = "quantile" | "fixed";
type RevenueCapMode = "none" | "p95";
type RevenueColorConfig = {
  mode: RevenueColorMode;
  capMode: RevenueCapMode;
  ignoreTopCount: number;
  fixedLow: number;
  fixedHigh: number;
};
type RevenueColorScale = {
  low: number;
  high: number;
  cap?: number | null;
  values: number[];
};

const REVENUE_COLOR_CONFIG_STORAGE_KEY = "shopview.revenueMap.colorConfig.v1";
const DEFAULT_REVENUE_COLOR_CONFIG: RevenueColorConfig = {
  mode: "quantile",
  capMode: "p95",
  ignoreTopCount: 1,
  fixedLow: 12000,
  fixedHigh: 32000,
};

function readRevenueColorConfig(): RevenueColorConfig {
  if (typeof window === "undefined") return DEFAULT_REVENUE_COLOR_CONFIG;
  try {
    const raw = window.localStorage.getItem(REVENUE_COLOR_CONFIG_STORAGE_KEY);
    if (!raw) return DEFAULT_REVENUE_COLOR_CONFIG;
    const parsed = JSON.parse(raw) as Partial<RevenueColorConfig>;
    return {
      ...DEFAULT_REVENUE_COLOR_CONFIG,
      ...parsed,
      mode: parsed.mode === "fixed" ? "fixed" : "quantile",
      capMode: parsed.capMode === "none" ? "none" : "p95",
      ignoreTopCount: Number.isFinite(parsed.ignoreTopCount) ? Math.max(0, Math.min(5, Number(parsed.ignoreTopCount))) : DEFAULT_REVENUE_COLOR_CONFIG.ignoreTopCount,
      fixedLow: Number.isFinite(parsed.fixedLow) ? Number(parsed.fixedLow) : DEFAULT_REVENUE_COLOR_CONFIG.fixedLow,
      fixedHigh: Number.isFinite(parsed.fixedHigh) ? Number(parsed.fixedHigh) : DEFAULT_REVENUE_COLOR_CONFIG.fixedHigh,
    };
  } catch {
    return DEFAULT_REVENUE_COLOR_CONFIG;
  }
}

function quantile(sortedValues: number[], q: number) {
  if (!sortedValues.length) return 0;
  if (sortedValues.length === 1) return sortedValues[0];
  const pos = (sortedValues.length - 1) * q;
  const base = Math.floor(pos);
  const rest = pos - base;
  return sortedValues[base] + ((sortedValues[base + 1] ?? sortedValues[base]) - sortedValues[base]) * rest;
}

function buildRevenueColorScale(rows: RevenueMonthlyItem[], config: RevenueColorConfig): RevenueColorScale {
  const positiveValues = rows
    .map((row) => Number(row.metric_amount || 0))
    .filter((value) => Number.isFinite(value) && value > 0)
    .sort((a, b) => a - b);
  if (!positiveValues.length) {
    return { low: 0, high: 0, cap: null, values: [] };
  }
  const cap = config.capMode === "p95" ? quantile(positiveValues, 0.95) : null;
  const cappedValues = cap == null ? positiveValues : positiveValues.map((value) => Math.min(value, cap));
  const trimmedValues = config.ignoreTopCount > 0 && cappedValues.length > config.ignoreTopCount
    ? cappedValues.slice(0, cappedValues.length - config.ignoreTopCount)
    : cappedValues;
  const values = trimmedValues.length ? trimmedValues : cappedValues;
  if (config.mode === "fixed") {
    const low = Math.min(config.fixedLow, config.fixedHigh);
    const high = Math.max(config.fixedLow, config.fixedHigh);
    return { low, high, cap, values };
  }
  return {
    low: quantile(values, 0.25),
    high: quantile(values, 0.75),
    cap,
    values,
  };
}

function revenueFill(value: number | undefined, scale: RevenueColorScale) {
  if (value == null) return { fill: "rgba(226,232,240,0.42)", stroke: "rgba(100,116,139,0.7)" };
  if (value < 0) return { fill: "rgba(244,63,94,0.62)", stroke: "rgba(159,18,57,0.95)" };
  if (value === 0) return { fill: "rgba(251,113,133,0.34)", stroke: "rgba(190,18,60,0.78)" };
  if (scale.high <= scale.low) return { fill: "rgba(20,184,166,0.62)", stroke: "rgba(15,118,110,0.95)" };
  if (value >= scale.high) return { fill: "rgba(16,185,129,0.66)", stroke: "rgba(4,120,87,0.98)" };
  if (value >= scale.low) return { fill: "rgba(250,204,21,0.62)", stroke: "rgba(161,98,7,0.92)" };
  return { fill: "rgba(251,113,133,0.5)", stroke: "rgba(190,18,60,0.88)" };
}

function revenueColorBand(value: number | undefined, scale: RevenueColorScale) {
  if (value == null) return "none";
  if (value <= 0) return "low";
  if (scale.high <= scale.low) return "high";
  if (value >= scale.high) return "high";
  if (value >= scale.low) return "middle";
  return "low";
}

function statusBadge(status: string) {
  if (status === "CONFIRMED") return <Badge className="bg-emerald-600">已确认</Badge>;
  if (status === "VOID") return <Badge variant="secondary">已作废</Badge>;
  return <Badge variant="outline">草稿</Badge>;
}

export default function RevenueMapPage() {
  const [startDate, setStartDate] = useState(todayDate());
  const [endDate, setEndDate] = useState(todayDate());
  const revenueMonth = startDate.slice(0, 7) || todayMonth();
  const [storeFilter, setStoreFilter] = useState("");
  const [floorId, setFloorId] = useState<number | null>(null);
  const [baseMapId, setBaseMapId] = useState<number | null>(null);
  const [versionId, setVersionId] = useState<number | null>(null);
  const [mapZoom, setMapZoom] = useState(1);
  const [mapPan, setMapPan] = useState({ x: 0, y: 0 });
  const [selectedUnit, setSelectedUnit] = useState<RevenueMonthlyItem | null>(null);
  const [extraOpen, setExtraOpen] = useState(false);
  const [colorConfigOpen, setColorConfigOpen] = useState(false);
  const [colorConfig, setColorConfig] = useState<RevenueColorConfig>(() => readRevenueColorConfig());
  const [draftColorConfig, setDraftColorConfig] = useState<RevenueColorConfig>(colorConfig);
  const [form, setForm] = useState({
    unitId: "",
    revenueDate: todayDate(),
    extraType: "临时补收",
    amount: "",
    voucherNo: "",
    supplierName: "",
    remark: "",
  });
  const { toast } = useToast();
  const { selectedStoreId, stores, isLoading: storesLoading } = useStore();
  const dragStateRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    panX: number;
    panY: number;
    moved: boolean;
  } | null>(null);
  const suppressMapClickRef = useRef(false);

  const floorsQuery = useFloorDictList();
  const baseMapsQuery = useBaseMapsList(floorId ?? undefined);
  const unitVersionsQuery = useUnitMapVersions(floorId ?? undefined, baseMapId ?? undefined);
  const geoQuery = useGeoElements(versionId ?? undefined);
  const alignQuery = useAlignTransform(versionId ?? undefined);
  const selectedStoreIdValue = storeFilter && Number.isFinite(Number(storeFilter)) ? Number(storeFilter) : null;
  const monthlyQuery = useRevenueMonthly({ startDate, endDate, storeId: selectedStoreIdValue, floorId });
  const detailQuery = useRevenueUnitDetail({ unitId: selectedUnit?.unit_id, startDate, endDate });
  const extraQuery = useRevenueExtraReceipts({ startDate, endDate, storeId: selectedStoreIdValue, floorId });
  const unitsQuery = useBusinessUnits({ floorId: floorId ?? undefined });
  const createExtra = useCreateRevenueExtraReceipt();
  const confirmExtra = useConfirmRevenueExtraReceipt(revenueMonth);
  const voidExtra = useVoidRevenueExtraReceipt(revenueMonth);
  const recalculate = useRecalculateRevenue();

  const rows = monthlyQuery.data?.items ?? [];
  const extras = extraQuery.data ?? [];
  const units = unitsQuery.data ?? [];
  const floors = floorsQuery.data ?? [];
  const baseMaps = baseMapsQuery.data ?? [];
  const versions = unitVersionsQuery.data ?? [];
  const geoRows = geoQuery.data ?? [];
  const monthlyErrorText = monthlyQuery.error ? String(monthlyQuery.error) : "";

  const storeOptions = useMemo(() => {
    const options = stores.map((store) => ({
      value: String(store.storeId),
      label: store.storeName || store.storeCode || String(store.storeId),
      code: store.storeCode ? String(store.storeCode) : "",
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
  const selectedStoreOption = useMemo(
    () => storeOptions.find((store) => store.value === storeFilter),
    [storeFilter, storeOptions],
  );
  const merchantStoreRef = selectedStoreOption?.code || storeFilter || "";
  const visibleFloorOptions = useMemo(() => {
    if (!storeFilter) return [];
    return floors.filter((floor) => {
      const storeRef = getFloorStoreRef(floor);
      if (!storeRef) return false;
      return storeRef === storeFilter || storeRef === selectedStoreOption?.code;
    });
  }, [floors, selectedStoreOption?.code, storeFilter]);

  useEffect(() => {
    if (storeFilter || !storeOptions.length) return;
    const globalStoreValue = selectedStoreId ? String(selectedStoreId) : "";
    const globalStore = storeOptions.find((store) => store.value === globalStoreValue);
    setStoreFilter(globalStore?.value ?? storeOptions[0].value);
  }, [selectedStoreId, storeFilter, storeOptions]);

  useEffect(() => {
    if (!startDate || !endDate) return;
    monthlyQuery.refetch();
    extraQuery.refetch();
  }, [endDate, floorId, selectedStoreIdValue, startDate]);

  useEffect(() => {
    if (!storeFilter) return;
    const hasCurrentFloor = floorId != null && visibleFloorOptions.some((floor) => floor.id === floorId);
    if (hasCurrentFloor) return;
    const revenueFloorId = rows.find((row) => (
      row.floor_id != null && visibleFloorOptions.some((floor) => floor.id === row.floor_id)
    ))?.floor_id;
    setFloorId(revenueFloorId ?? visibleFloorOptions[0]?.id ?? null);
  }, [floorId, rows, storeFilter, visibleFloorOptions]);

  useEffect(() => {
    if (floorId != null || storeFilter || !floors.length) return;
    const revenueFloorId = rows.find((row) => row.floor_id != null)?.floor_id;
    setFloorId(revenueFloorId ?? floors[0].id);
  }, [floorId, floors, rows, storeFilter]);

  useEffect(() => {
    const active = baseMaps.find((item) => item.is_active) ?? baseMaps[0];
    setBaseMapId(active?.id ?? null);
  }, [baseMaps]);

  useEffect(() => {
    const active = versions.find((item) => item.is_active) ?? versions[0];
    setVersionId(active?.id ?? null);
  }, [versions]);

  const totals = useMemo(() => {
    return rows.reduce(
      (acc, row) => {
        acc.sales += row.sales_gross_profit_amount;
        acc.fee += row.fee_amount;
        acc.extra += row.extra_amount;
        acc.total += row.total_amount;
        return acc;
      },
      { sales: 0, fee: 0, extra: 0, total: 0 },
    );
  }, [rows]);

  const revenueByUnitId = useMemo(() => {
    const map = new Map<number, RevenueMonthlyItem>();
    rows.forEach((row) => map.set(row.unit_id, row));
    return map;
  }, [rows]);
  const revenueMapStats = useMemo(() => {
    const mappedUnitIds = new Set(geoRows.map((geo) => geo.unit_id));
    const mappedRevenueRows = rows.filter((row) => mappedUnitIds.has(row.unit_id));
    return {
      colored: mappedRevenueRows.filter((row) => row.metric_amount !== 0).length,
      matched: mappedRevenueRows.length,
      missingShape: rows.length - mappedRevenueRows.length,
    };
  }, [geoRows, rows]);

  const selectedBaseMap = useMemo(() => baseMaps.find((item) => item.id === baseMapId) ?? null, [baseMaps, baseMapId]);
  const selectedBaseMapUrl = useMemo(() => resolveApiAssetUrl(selectedBaseMap?.file_url), [selectedBaseMap?.file_url]);
  const vb = useMemo(() => {
    const viewBox = deriveSvgViewBox({
      viewBox: selectedBaseMap?.svg_viewbox ?? null,
      width: selectedBaseMap?.svg_width ?? null,
      height: selectedBaseMap?.svg_height ?? null,
    });
    return parseViewBox(viewBox);
  }, [selectedBaseMap?.svg_height, selectedBaseMap?.svg_viewbox, selectedBaseMap?.svg_width]);
  const alignTransformText = useMemo(() => {
    const t = alignQuery.data;
    if (!t) return undefined;
    const rotate = t.rotate ? ` rotate(${t.rotate})` : "";
    return `translate(${t.dx || 0} ${t.dy || 0}) scale(${t.sx || 1} ${t.sy || 1})${rotate}`;
  }, [alignQuery.data]);
  const mapAutoOffset = useMemo(() => {
    if (!vb || !geoRows.length) return { x: 0, y: 0 };
    const t = alignQuery.data;
    const sx = t?.sx || 1;
    const sy = t?.sy || 1;
    const dx = t?.dx || 0;
    const dy = t?.dy || 0;
    const bounds = geoRows.reduce(
      (acc, geo) => {
        const fallback = getPathVisualCenter(geo.path_data);
        const minX = geo.bbox_minx ?? fallback?.x;
        const maxX = geo.bbox_maxx ?? fallback?.x;
        const minY = geo.bbox_miny ?? fallback?.y;
        const maxY = geo.bbox_maxy ?? fallback?.y;
        if (minX == null || maxX == null || minY == null || maxY == null) return acc;
        const left = dx + Math.min(minX * sx, maxX * sx);
        const right = dx + Math.max(minX * sx, maxX * sx);
        const top = dy + Math.min(minY * sy, maxY * sy);
        const bottom = dy + Math.max(minY * sy, maxY * sy);
        return {
          minX: Math.min(acc.minX, left),
          minY: Math.min(acc.minY, top),
          maxX: Math.max(acc.maxX, right),
          maxY: Math.max(acc.maxY, bottom),
        };
      },
      { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity },
    );
    if (![bounds.minX, bounds.minY, bounds.maxX, bounds.maxY].every(Number.isFinite)) {
      return { x: 0, y: 0 };
    }
    return {
      x: vb.x + vb.w / 2 - (bounds.minX + bounds.maxX) / 2,
      y: vb.y + vb.h / 2 - (bounds.minY + bounds.maxY) / 2,
    };
  }, [alignQuery.data, geoRows, vb]);
  const labelPoints = useMemo(
    () =>
      geoRows.map((geo) => ({
        id: geo.id,
        unit_id: geo.unit_id,
        point: getPathVisualCenter(geo.path_data),
      })),
    [geoRows],
  );
  const visibleRevenueRows = useMemo(
    () => rows.filter((row) => (floorId == null ? true : row.floor_id === floorId)),
    [floorId, rows],
  );
  const revenueColorScale = useMemo(
    () => buildRevenueColorScale(visibleRevenueRows, colorConfig),
    [colorConfig, visibleRevenueRows],
  );
  const draftRevenueColorScale = useMemo(
    () => buildRevenueColorScale(visibleRevenueRows, draftColorConfig),
    [draftColorConfig, visibleRevenueRows],
  );
  const revenueColorCounts = useMemo(() => {
    return visibleRevenueRows.reduce(
      (acc, row) => {
        acc[revenueColorBand(row.metric_amount, revenueColorScale)] += 1;
        return acc;
      },
      { high: 0, middle: 0, low: 0, none: Math.max(0, geoRows.length - visibleRevenueRows.length) },
    );
  }, [geoRows.length, revenueColorScale, visibleRevenueRows]);
  const draftRevenueColorCounts = useMemo(() => {
    return visibleRevenueRows.reduce(
      (acc, row) => {
        acc[revenueColorBand(row.metric_amount, draftRevenueColorScale)] += 1;
        return acc;
      },
      { high: 0, middle: 0, low: 0, none: Math.max(0, geoRows.length - visibleRevenueRows.length) },
    );
  }, [draftRevenueColorScale, geoRows.length, visibleRevenueRows]);

  useEffect(() => {
    if (colorConfigOpen) setDraftColorConfig(colorConfig);
  }, [colorConfig, colorConfigOpen]);

  useEffect(() => {
    setMapPan({ x: 0, y: 0 });
  }, [baseMapId, versionId, floorId]);

  const resetMapView = () => {
    setMapZoom(1);
    setMapPan({ x: 0, y: 0 });
  };

  const handleMapPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    suppressMapClickRef.current = false;
    dragStateRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      panX: mapPan.x,
      panY: mapPan.y,
      moved: false,
    };
  };

  const handleMapPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    const drag = dragStateRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    const dx = event.clientX - drag.startX;
    const dy = event.clientY - drag.startY;
    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
      drag.moved = true;
      suppressMapClickRef.current = true;
      setMapPan({ x: drag.panX + dx, y: drag.panY + dy });
    }
  };

  const handleMapPointerUp = (event: PointerEvent<HTMLDivElement>) => {
    const drag = dragStateRef.current;
    if (drag?.pointerId === event.pointerId) {
      dragStateRef.current = null;
      window.setTimeout(() => {
        suppressMapClickRef.current = false;
      }, 0);
    }
  };

  const selectMapUnit = (unitId: number) => {
    const row = revenueByUnitId.get(unitId);
    if (row) {
      setSelectedUnit(row);
      return;
    }
    const unit = units.find((item) => item.id === unitId);
    setSelectedUnit({
      unit_id: unitId,
      unit_code: unit?.unit_code || `unit-${unitId}`,
      floor_id: unit?.floor_id ?? floorId,
      store_id: selectedStoreIdValue ?? undefined,
      unit_status: unit?.status,
      sales_gross_profit_amount: 0,
      fee_amount: 0,
      extra_amount: 0,
      total_amount: 0,
      metric_amount: 0,
      sales_detail_count: 0,
      fee_detail_count: 0,
      extra_detail_count: 0,
    });
  };

  const handleCreateExtra = async () => {
    const unit = units.find((item) => String(item.id) === form.unitId);
    if (!unit) {
      toast({ title: "请选择柜位", variant: "destructive" });
      return;
    }
    const amount = Number(form.amount);
    if (!Number.isFinite(amount) || amount === 0) {
      toast({ title: "请填写非零金额", variant: "destructive" });
      return;
    }
    try {
      await createExtra.mutateAsync({
        unit_id: unit.id,
        unit_code: unit.unit_code,
        store_id: selectedStoreIdValue,
        floor_id: unit.floor_id,
        revenue_date: form.revenueDate,
        extra_type: form.extraType || "其他收益",
        amount,
        receipt_date: form.revenueDate,
        voucher_no: form.voucherNo || undefined,
        supplier_name: form.supplierName || undefined,
        remark: form.remark || undefined,
      });
      setExtraOpen(false);
      setForm({ unitId: "", revenueDate: todayDate(), extraType: "临时补收", amount: "", voucherNo: "", supplierName: "", remark: "" });
      toast({ title: "补收已保存" });
    } catch (error) {
      toast({ title: "补收保存失败", description: String(error), variant: "destructive" });
    }
  };

  const handleRecalculate = async () => {
    try {
      const start = startDate || todayDate();
      const end = endDate || start;
      if (end < start) {
        toast({ title: "结束日期不能早于开始日期", variant: "destructive" });
        return;
      }
      await recalculate.mutateAsync({ start_date: start, end_date: end });
      await Promise.all([
        monthlyQuery.refetch(),
        extraQuery.refetch(),
        selectedUnit ? detailQuery.refetch() : Promise.resolve(),
      ]);
      toast({ title: "收益汇总已重算" });
    } catch (error) {
      toast({ title: "重算失败", description: String(error), variant: "destructive" });
    }
  };

  const saveRevenueColorConfig = () => {
    const nextConfig = {
      ...draftColorConfig,
      fixedLow: Number(draftColorConfig.fixedLow) || 0,
      fixedHigh: Number(draftColorConfig.fixedHigh) || 0,
      ignoreTopCount: Math.max(0, Math.min(5, Number(draftColorConfig.ignoreTopCount) || 0)),
    };
    setColorConfig(nextConfig);
    try {
      window.localStorage.setItem(REVENUE_COLOR_CONFIG_STORAGE_KEY, JSON.stringify(nextConfig));
    } catch {
      // localStorage may be disabled in restricted browser contexts; the in-memory rule still applies.
    }
    setColorConfigOpen(false);
    toast({ title: "收益颜色规则已保存" });
  };

  const resetRevenueColorConfig = () => {
    setDraftColorConfig(DEFAULT_REVENUE_COLOR_CONFIG);
  };

  const openMerchantPlanning = () => {
    if (!selectedUnit) return;
    const params = new URLSearchParams(window.location.search);
    params.set("view", "merchant-planning");
    params.set("merchantTab", "single");
    params.set("merchant_unit_id", String(selectedUnit.unit_id));
    if (selectedUnit.floor_id != null) params.set("merchant_floor_id", String(selectedUnit.floor_id));
    const storeRef = merchantStoreRef || selectedUnit.store_id;
    if (storeRef != null) params.set("merchant_store_id", String(storeRef));
    window.location.href = `${window.location.pathname}?${params.toString()}`;
  };

  const renderRevenueColorConfigSheet = () => (
    <Sheet open={colorConfigOpen} onOpenChange={setColorConfigOpen}>
      <SheetContent className="z-[60] flex w-full flex-col overflow-hidden bg-white p-0 sm:max-w-xl">
        <SheetHeader className="border-b px-5 py-4 pr-12">
          <SheetTitle>收益颜色配置</SheetTitle>
          <SheetDescription>
            只调整地图颜色分档，不改变收益计算结果。推荐使用分位数与极端值封顶，避免单个超高柜位拉偏整张图。
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 space-y-3 overflow-y-auto px-5 py-4">
          <div className="rounded-md border">
            <div className="flex items-center justify-between border-b px-3 py-2">
              <div className="text-sm font-semibold">分档方式</div>
              <div className="text-xs text-muted-foreground">当前楼层数据实时预览</div>
            </div>
            <div className="space-y-3 p-3">
              <div className="grid grid-cols-2 rounded-md bg-muted p-1 text-sm">
                <button
                  type="button"
                  className={`rounded-sm px-3 py-2 font-medium ${draftColorConfig.mode === "quantile" ? "bg-white text-blue-700 shadow-sm" : "text-muted-foreground"}`}
                  onClick={() => setDraftColorConfig((prev) => ({ ...prev, mode: "quantile" }))}
                >
                  分位数
                </button>
                <button
                  type="button"
                  className={`rounded-sm px-3 py-2 font-medium ${draftColorConfig.mode === "fixed" ? "bg-white text-blue-700 shadow-sm" : "text-muted-foreground"}`}
                  onClick={() => setDraftColorConfig((prev) => ({ ...prev, mode: "fixed" }))}
                >
                  固定金额
                </button>
              </div>
              <p className="text-xs text-muted-foreground">
                分位数按当前楼层有收益柜位排序，更适合不同楼层收益规模差异较大的情况。
              </p>
            </div>
          </div>

          <div className="rounded-md border">
            <div className="flex items-center justify-between border-b px-3 py-2">
              <div className="text-sm font-semibold">极端值处理</div>
              <div className="text-xs text-muted-foreground">解决“一个特别高”</div>
            </div>
            <div className="space-y-3 p-3">
              <div className="grid grid-cols-[120px_1fr] items-center gap-3">
                <Label className="text-xs text-muted-foreground">颜色计算上限</Label>
                <div className="grid grid-cols-2 rounded-md bg-muted p-1 text-sm">
                  {[
                    ["p95", "P95 封顶"],
                    ["none", "不封顶"],
                  ].map(([value, label]) => (
                    <button
                      key={value}
                      type="button"
                      className={`rounded-sm px-3 py-2 font-medium ${draftColorConfig.capMode === value ? "bg-white text-blue-700 shadow-sm" : "text-muted-foreground"}`}
                      onClick={() => setDraftColorConfig((prev) => ({ ...prev, capMode: value as RevenueCapMode }))}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-[120px_1fr] items-center gap-3">
                <Label className="text-xs text-muted-foreground">忽略极端高值</Label>
                <div className="grid grid-cols-4 rounded-md bg-muted p-1 text-sm">
                  {[
                    [0, "不忽略"],
                    [1, "前 1 个"],
                    [2, "前 2 个"],
                    [3, "前 3 个"],
                  ].map(([value, label]) => (
                    <button
                      key={value}
                      type="button"
                      className={`rounded-sm px-2 py-2 font-medium ${draftColorConfig.ignoreTopCount === value ? "bg-white text-blue-700 shadow-sm" : "text-muted-foreground"}`}
                      onClick={() => setDraftColorConfig((prev) => ({ ...prev, ignoreTopCount: Number(value) }))}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
              <p className="rounded-md bg-blue-50 px-3 py-2 text-xs text-blue-700">
                极端柜位仍会显示为高收益，只是不再决定其他柜位的颜色边界。
              </p>
            </div>
          </div>

          <div className="rounded-md border">
            <div className="flex items-center justify-between border-b px-3 py-2">
              <div className="text-sm font-semibold">分档阈值</div>
              <div className="text-xs text-muted-foreground">{draftColorConfig.mode === "fixed" ? "手工金额" : "按当前数据估算"}</div>
            </div>
            <div className="space-y-3 p-3">
              {draftColorConfig.mode === "fixed" ? (
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs">低/中分界</Label>
                    <Input
                      className="h-9"
                      inputMode="decimal"
                      value={draftColorConfig.fixedLow}
                      onChange={(event) => setDraftColorConfig((prev) => ({ ...prev, fixedLow: Number(event.target.value) || 0 }))}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">中/高分界</Label>
                    <Input
                      className="h-9"
                      inputMode="decimal"
                      value={draftColorConfig.fixedHigh}
                      onChange={(event) => setDraftColorConfig((prev) => ({ ...prev, fixedHigh: Number(event.target.value) || 0 }))}
                    />
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-md border bg-slate-50 px-3 py-2">
                    <div className="text-xs text-muted-foreground">P25 低/中分界</div>
                    <div className="mt-1 font-semibold">{money(draftRevenueColorScale.low)}</div>
                  </div>
                  <div className="rounded-md border bg-slate-50 px-3 py-2">
                    <div className="text-xs text-muted-foreground">P75 中/高分界</div>
                    <div className="mt-1 font-semibold">{money(draftRevenueColorScale.high)}</div>
                  </div>
                </div>
              )}
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="rounded-md border border-red-100 bg-red-50 px-3 py-2">
                  <div className="font-semibold text-red-700">收益低/负</div>
                  <div className="mt-1 text-muted-foreground">&lt; {money(draftRevenueColorScale.low)}</div>
                </div>
                <div className="rounded-md border border-yellow-100 bg-yellow-50 px-3 py-2">
                  <div className="font-semibold text-yellow-700">中等</div>
                  <div className="mt-1 text-muted-foreground">{money(draftRevenueColorScale.low)} - {money(draftRevenueColorScale.high)}</div>
                </div>
                <div className="rounded-md border border-emerald-100 bg-emerald-50 px-3 py-2">
                  <div className="font-semibold text-emerald-700">收益高</div>
                  <div className="mt-1 text-muted-foreground">≥ {money(draftRevenueColorScale.high)}</div>
                </div>
              </div>
              {draftRevenueColorScale.cap ? (
                <p className="text-xs text-muted-foreground">当前 P95 封顶值：{money(draftRevenueColorScale.cap)}</p>
              ) : null}
            </div>
          </div>

          <div className="rounded-md border">
            <div className="flex items-center justify-between border-b px-3 py-2">
              <div className="text-sm font-semibold">应用后预览</div>
              <div className="text-xs text-muted-foreground">{visibleRevenueRows.length} 个收益柜位</div>
            </div>
            <div className="grid grid-cols-4 gap-2 p-3 text-xs">
              <div className="rounded-md bg-emerald-50 px-3 py-2">
                <div className="font-semibold text-emerald-700">收益高</div>
                <div className="mt-1">{draftRevenueColorCounts.high} 个</div>
              </div>
              <div className="rounded-md bg-yellow-50 px-3 py-2">
                <div className="font-semibold text-yellow-700">中等</div>
                <div className="mt-1">{draftRevenueColorCounts.middle} 个</div>
              </div>
              <div className="rounded-md bg-red-50 px-3 py-2">
                <div className="font-semibold text-red-700">收益低/负</div>
                <div className="mt-1">{draftRevenueColorCounts.low} 个</div>
              </div>
              <div className="rounded-md bg-slate-100 px-3 py-2">
                <div className="font-semibold text-slate-600">无数据</div>
                <div className="mt-1">{draftRevenueColorCounts.none} 个</div>
              </div>
            </div>
          </div>
        </div>

        <SheetFooter className="border-t px-5 py-4">
          <Button type="button" variant="outline" onClick={resetRevenueColorConfig}>恢复推荐</Button>
          <Button type="button" variant="outline" onClick={() => setColorConfigOpen(false)}>取消</Button>
          <Button type="button" onClick={saveRevenueColorConfig}>保存规则</Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );

  const renderRevenueDetailPanel = () => {
    if (!selectedUnit) return null;
    const detailTotals = detailQuery.data?.daily_summary.reduce(
      (acc, row) => {
        acc.sales += row.sales_gross_profit_amount;
        acc.fee += row.fee_amount;
        acc.extra += row.extra_amount;
        acc.total += row.total_amount;
        return acc;
      },
      { sales: 0, fee: 0, extra: 0, total: 0 },
    );
    return (
      <aside className="overflow-hidden rounded-md border bg-white shadow-sm">
        <div className="flex items-start justify-between gap-3 border-b bg-white px-3 py-2.5">
          <div>
            <div className="text-lg font-bold text-slate-900">{selectedUnit.unit_code} 收益明细</div>
            <div className="mt-0.5 text-xs text-muted-foreground">{startDate} 至 {endDate} · 点击左侧其他柜位可切换</div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={openMerchantPlanning}>
              <Target className="mr-1 h-4 w-4" />
              转招商规划
            </Button>
            <Button variant="outline" size="sm" onClick={() => setSelectedUnit(null)}>
              关闭
            </Button>
          </div>
        </div>

        {detailQuery.isLoading ? (
          <div className="py-10 text-center text-muted-foreground">加载中...</div>
        ) : detailQuery.data ? (
          <div className="space-y-3 bg-slate-50 p-3">
            {detailQuery.data.daily_summary.length ? (
              <div className="grid grid-cols-2 gap-2 2xl:grid-cols-4">
                {[
                  ["总收益", detailTotals?.total ?? 0],
                  ["销售毛利", detailTotals?.sales ?? 0],
                  ["收费", detailTotals?.fee ?? 0],
                  ["补收", detailTotals?.extra ?? 0],
                ].map(([label, value]) => (
                  <div key={String(label)} className="rounded-md border bg-white px-3 py-2">
                    <div className="text-xs text-muted-foreground">{label}</div>
                    <div className="mt-1 text-base font-semibold text-slate-900">{money(Number(value))}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-md border bg-white p-4 text-sm text-muted-foreground">当前月份暂无收益数据</div>
            )}

            <div className="rounded-md border bg-white">
              <div className="border-b px-3 py-2 text-sm font-semibold">每日收益组成</div>
              <div className="overflow-x-auto text-xs">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="whitespace-nowrap">日期</TableHead>
                      <TableHead className="whitespace-nowrap text-right">销售毛利</TableHead>
                      <TableHead className="whitespace-nowrap text-right">收费</TableHead>
                      <TableHead className="whitespace-nowrap text-right">补收</TableHead>
                      <TableHead className="whitespace-nowrap text-right">总收益</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {detailQuery.data.daily_summary.map((row) => (
                      <TableRow key={row.revenue_date}>
                        <TableCell className="whitespace-nowrap">{row.revenue_date?.slice(0, 10)}</TableCell>
                        <TableCell className="whitespace-nowrap text-right">{money(row.sales_gross_profit_amount)}</TableCell>
                        <TableCell className="whitespace-nowrap text-right">{money(row.fee_amount)}</TableCell>
                        <TableCell className="whitespace-nowrap text-right">{money(row.extra_amount)}</TableCell>
                        <TableCell className="whitespace-nowrap text-right font-semibold">{money(row.total_amount)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>

            <div className="rounded-md border bg-white">
              <div className="flex items-center justify-between gap-3 border-b px-3 py-2">
                <div className="text-sm font-semibold">销售毛利明细</div>
                <div className="text-xs text-muted-foreground">{detailQuery.data.sales_details.length} 条</div>
              </div>
              <div className="overflow-x-auto text-xs">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="min-w-44">柜组</TableHead>
                      <TableHead className="whitespace-nowrap">经营方式</TableHead>
                      <TableHead className="whitespace-nowrap text-right">不含税销售</TableHead>
                      <TableHead className="whitespace-nowrap text-right">不含税毛利</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {detailQuery.data.sales_details.length ? (
                      detailQuery.data.sales_details.map((row) => (
                        <TableRow key={row.id}>
                          <TableCell>
                            <div className="font-medium">{row.source_group_code || "—"}</div>
                            <div className="text-xs text-muted-foreground">{row.source_group_name || "—"}</div>
                          </TableCell>
                          <TableCell className="whitespace-nowrap">{row.operation_mode || "—"}</TableCell>
                          <TableCell className="whitespace-nowrap text-right">{money(row.tax_excluded_sales_amount)}</TableCell>
                          <TableCell className="whitespace-nowrap text-right font-medium">{money(row.tax_excluded_profit_amount)}</TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={4} className="py-8 text-center text-muted-foreground">暂无销售毛利明细</TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </div>

            <div className="rounded-md border bg-white">
              <div className="flex items-center justify-between gap-3 border-b px-3 py-2">
                <div className="text-sm font-semibold">收费明细</div>
                <div className="text-xs text-muted-foreground">{detailQuery.data.fee_details.length} 条</div>
              </div>
              <div className="overflow-x-auto text-xs">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="min-w-44">柜组</TableHead>
                      <TableHead className="whitespace-nowrap">费用</TableHead>
                      <TableHead className="whitespace-nowrap text-right">含税</TableHead>
                      <TableHead className="whitespace-nowrap text-right">不含税</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {detailQuery.data.fee_details.length ? (
                      detailQuery.data.fee_details.map((row) => (
                        <TableRow key={row.id}>
                          <TableCell>
                            <div className="font-medium">{row.source_group_code || "—"}</div>
                            <div className="text-xs text-muted-foreground">{row.source_group_name || "—"}</div>
                          </TableCell>
                          <TableCell className="whitespace-nowrap">{row.fee_type_name || "—"}</TableCell>
                          <TableCell className="whitespace-nowrap text-right">{money(row.tax_included_amount)}</TableCell>
                          <TableCell className="whitespace-nowrap text-right font-medium">{money(row.tax_excluded_amount)}</TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={4} className="py-8 text-center text-muted-foreground">暂无收费明细</TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </div>

            <div className="rounded-md border bg-white">
              <div className="flex items-center justify-between gap-3 border-b px-3 py-2">
                <div className="text-sm font-semibold">补收明细</div>
                <div className="text-xs text-muted-foreground">{detailQuery.data.extra_receipts.length} 条</div>
              </div>
              <div className="overflow-x-auto text-xs">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="whitespace-nowrap">日期</TableHead>
                      <TableHead>类型</TableHead>
                      <TableHead className="whitespace-nowrap text-right">金额</TableHead>
                      <TableHead className="whitespace-nowrap">状态</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {detailQuery.data.extra_receipts.length ? (
                      detailQuery.data.extra_receipts.map((row) => (
                        <TableRow key={row.id}>
                          <TableCell className="whitespace-nowrap">{row.revenue_date?.slice(0, 10)}</TableCell>
                          <TableCell>
                            <div className="font-medium">{row.extra_type || "—"}</div>
                            <div className="text-xs text-muted-foreground">{row.remark || row.voucher_no || "—"}</div>
                          </TableCell>
                          <TableCell className="whitespace-nowrap text-right font-medium">{money(row.amount)}</TableCell>
                          <TableCell className="whitespace-nowrap">{statusBadge(row.status)}</TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={4} className="py-6 text-center text-muted-foreground">暂无补收明细</TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </div>
          </div>
        ) : (
          <div className="py-10 text-center text-muted-foreground">暂无数据</div>
        )}
      </aside>
    );
  };

  return (
    <div className="container mx-auto space-y-3 p-4" data-testid="revenue-map-page">
      {renderRevenueColorConfigSheet()}

      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-44">
          <h1 className="text-2xl font-bold tracking-tight">收益地图</h1>
          <p className="mt-0.5 text-xs text-muted-foreground">绿色为高收益，黄色为中等，红色为低收益或负收益。</p>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <div className="space-y-1">
            <Label className="text-xs">门店</Label>
            <Select
              value={storeFilter}
              onValueChange={(value) => {
                setStoreFilter(value);
                setFloorId(null);
                setSelectedUnit(null);
              }}
              disabled={storesLoading || !storeOptions.length}
            >
              <SelectTrigger className="h-9 w-44">
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
            <Label className="text-xs">楼层</Label>
            <Select
              value={floorId ? String(floorId) : ""}
              onValueChange={(v) => {
                setFloorId(Number(v));
                setSelectedUnit(null);
              }}
              disabled={floorsQuery.isLoading || !visibleFloorOptions.length}
            >
              <SelectTrigger className="h-9 w-44">
                <SelectValue placeholder={storeFilter ? "选择楼层" : "请先选择门店"} />
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
            <Label className="text-xs">开始日期</Label>
            <Input
              type="date"
              value={startDate}
              onChange={(e) => {
                const next = e.target.value || todayDate();
                setStartDate(next);
                if (endDate < next) setEndDate(next);
              }}
              className="h-9 w-36"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">结束日期</Label>
            <Input
              type="date"
              value={endDate}
              min={startDate}
              onChange={(e) => setEndDate(e.target.value || startDate || todayDate())}
              className="h-9 w-36"
            />
          </div>
          <Button variant="outline" className="h-9" onClick={handleRecalculate} disabled={recalculate.isPending}>
            {recalculate.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            重算
          </Button>
          <Dialog open={extraOpen} onOpenChange={setExtraOpen}>
            <DialogTrigger asChild>
              <Button className="h-9">
                <Plus className="mr-2 h-4 w-4" />
                补收
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-xl">
              <DialogHeader>
                <DialogTitle>新增补收</DialogTitle>
              </DialogHeader>
              <div className="grid gap-4 py-2">
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label>柜位</Label>
                    <Select value={form.unitId} onValueChange={(v) => setForm((prev) => ({ ...prev, unitId: v }))}>
                      <SelectTrigger>
                        <SelectValue placeholder="选择柜位" />
                      </SelectTrigger>
                      <SelectContent>
                        {units.slice(0, 200).map((unit) => (
                          <SelectItem key={unit.id} value={String(unit.id)}>
                            {unit.unit_code}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1">
                    <Label>收益日期</Label>
                    <Input type="date" value={form.revenueDate} onChange={(e) => setForm((prev) => ({ ...prev, revenueDate: e.target.value }))} />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label>类型</Label>
                    <Input value={form.extraType} onChange={(e) => setForm((prev) => ({ ...prev, extraType: e.target.value }))} />
                  </div>
                  <div className="space-y-1">
                    <Label>金额</Label>
                    <Input inputMode="decimal" value={form.amount} onChange={(e) => setForm((prev) => ({ ...prev, amount: e.target.value }))} />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label>凭证号</Label>
                    <Input value={form.voucherNo} onChange={(e) => setForm((prev) => ({ ...prev, voucherNo: e.target.value }))} />
                  </div>
                  <div className="space-y-1">
                    <Label>供应商</Label>
                    <Input value={form.supplierName} onChange={(e) => setForm((prev) => ({ ...prev, supplierName: e.target.value }))} />
                  </div>
                </div>
                <div className="space-y-1">
                  <Label>备注</Label>
                  <Textarea value={form.remark} onChange={(e) => setForm((prev) => ({ ...prev, remark: e.target.value }))} />
                </div>
                <Button onClick={handleCreateExtra} disabled={createExtra.isPending}>
                  {createExtra.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                  保存草稿
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {monthlyQuery.isError ? (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          收益数据加载失败：{monthlyErrorText || "请检查收益汇总接口"}
        </div>
      ) : null}

      <div className="grid gap-2 md:grid-cols-5">
        <Card className="rounded-md">
          <CardContent className="px-4 py-3">
            <div className="text-xs font-medium text-muted-foreground">总收益</div>
            <div className="mt-1 text-xl font-semibold">{money(totals.total)}</div>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="px-4 py-3">
            <div className="text-xs font-medium text-muted-foreground">销售毛利</div>
            <div className="mt-1 text-xl font-semibold">{money(totals.sales)}</div>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="px-4 py-3">
            <div className="text-xs font-medium text-muted-foreground">收费</div>
            <div className="mt-1 text-xl font-semibold">{money(totals.fee)}</div>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="px-4 py-3">
            <div className="text-xs font-medium text-muted-foreground">补收</div>
            <div className="mt-1 text-xl font-semibold">{money(totals.extra)}</div>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="px-4 py-3">
            <div className="text-xs font-medium text-muted-foreground">未匹配</div>
            <div className="mt-1 text-xl font-semibold">{money(monthlyQuery.data?.unmatched.amount ?? 0)}</div>
            <div className="text-xs text-muted-foreground">{monthlyQuery.data?.unmatched.item_count ?? 0} 条待处理</div>
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-md">
        <CardHeader className="px-4 py-3">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <CardTitle className="flex items-center gap-2">
              <CircleDollarSign className="h-5 w-5" />
              图上收益
            </CardTitle>
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1"><span className="h-3 w-5 rounded-sm bg-emerald-400" />收益高</span>
              <span className="inline-flex items-center gap-1"><span className="h-3 w-5 rounded-sm bg-yellow-300" />中等</span>
              <span className="inline-flex items-center gap-1"><span className="h-3 w-5 rounded-sm bg-red-300" />收益低/负</span>
              <span className="inline-flex items-center gap-1"><span className="h-3 w-5 rounded-sm bg-slate-200" />无数据</span>
              <Button type="button" variant="outline" size="sm" className="ml-2 h-8" onClick={() => setColorConfigOpen(true)}>
                <Settings2 className="mr-1 h-4 w-4" />
                颜色规则
              </Button>
              <Button type="button" variant="outline" size="icon" className="ml-2 h-8 w-8" onClick={() => setMapZoom((z) => Math.max(0.6, z - 0.25))}>
                <Minus className="h-4 w-4" />
              </Button>
              <Button type="button" variant="outline" size="icon" className="h-8 w-8" onClick={() => setMapZoom((z) => Math.min(5, z + 0.25))}>
                <Plus className="h-4 w-4" />
              </Button>
              <Button type="button" variant="outline" size="icon" className="h-8 w-8" onClick={resetMapView}>
                <RotateCcw className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="px-4 pb-4 pt-0">
          <div className={selectedUnit ? "grid gap-4 xl:grid-cols-[minmax(0,1fr)_520px]" : "grid gap-4"}>
            {!selectedBaseMapUrl ? (
              <div className="py-12 text-center text-sm text-muted-foreground">当前楼层没有可用底图</div>
            ) : !vb ? (
              <div className="py-12 text-center text-sm text-muted-foreground">当前底图缺少有效 viewBox，无法叠加柜位图</div>
            ) : (
              <div className="overflow-hidden rounded-md border bg-white">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b px-4 py-2 text-xs text-muted-foreground">
                  <span>柜位数量：{geoRows.length}</span>
                  <span>有收益：{revenueMapStats.colored} 个</span>
                  <span>已匹配：{revenueMapStats.matched} 个</span>
                  {revenueMapStats.missingShape > 0 ? <span>未上图：{revenueMapStats.missingShape} 个</span> : null}
                  <span>缩放：{Math.round(mapZoom * 100)}%</span>
                  <span>
                    分档：{colorConfig.mode === "quantile" ? "P25/P75" : `${money(revenueColorScale.low)} / ${money(revenueColorScale.high)}`}
                    {colorConfig.capMode === "p95" ? "，P95封顶" : ""}
                    {colorConfig.ignoreTopCount > 0 ? `，忽略前${colorConfig.ignoreTopCount}个极高值` : ""}
                  </span>
                  <span>高/中/低/无：{revenueColorCounts.high}/{revenueColorCounts.middle}/{revenueColorCounts.low}/{revenueColorCounts.none}</span>
                  <span>{selectedUnit ? "左侧可继续点击其他柜位" : "点击柜位查看收益组成"}</span>
                </div>
                <div
                  className="relative min-h-[clamp(620px,72vh,900px)] cursor-grab overflow-hidden bg-slate-50 active:cursor-grabbing"
                  onPointerDown={handleMapPointerDown}
                  onPointerMove={handleMapPointerMove}
                  onPointerUp={handleMapPointerUp}
                  onPointerCancel={handleMapPointerUp}
                >
                  <svg
                    className="absolute inset-0 h-full w-full select-none"
                    viewBox={`${vb.x} ${vb.y} ${vb.w} ${vb.h}`}
                    preserveAspectRatio="xMidYMid meet"
                    style={{
                      transform: `translate(${mapPan.x}px, ${mapPan.y}px) scale(${mapZoom})`,
                      transformOrigin: "center",
                    }}
                  >
                    <g transform={`translate(${mapAutoOffset.x} ${mapAutoOffset.y})`}>
                      <image href={selectedBaseMapUrl} x={vb.x} y={vb.y} width={vb.w} height={vb.h} />
                      <g transform={alignTransformText}>
                        {geoRows.map((geo) => {
                          const row = revenueByUnitId.get(geo.unit_id);
                          const color = revenueFill(row?.metric_amount, revenueColorScale);
                          const selected = selectedUnit?.unit_id === geo.unit_id;
                          return (
                            <path
                              key={geo.id}
                              d={geo.path_data}
                              fill={selected ? "rgba(59,130,246,0.62)" : color.fill}
                              stroke={selected ? "rgba(37,99,235,1)" : color.stroke}
                              strokeWidth={selected ? 4.5 : row ? 3.25 : 2}
                              vectorEffect="non-scaling-stroke"
                              className="cursor-pointer transition-colors drop-shadow-sm hover:brightness-110"
                              onClick={() => {
                                if (suppressMapClickRef.current) return;
                                selectMapUnit(geo.unit_id);
                              }}
                            />
                          );
                        })}
                        {labelPoints.map(({ id, unit_id, point }) => {
                          if (!point) return null;
                          const row = revenueByUnitId.get(unit_id);
                          const unit = units.find((item) => item.id === unit_id);
                          const hasRevenue = row && row.metric_amount !== 0;
                          return (
                            <g key={`label-${id}`} pointerEvents="none">
                              <text
                                x={point.x}
                                y={hasRevenue ? point.y - 8 : point.y}
                                textAnchor="middle"
                                dominantBaseline="middle"
                                fontSize={24}
                                fontWeight={800}
                                fill="#0f172a"
                                stroke="#ffffff"
                                strokeWidth={6}
                                paintOrder="stroke"
                              >
                                {row?.unit_code || unit?.unit_code || `U${unit_id}`}
                              </text>
                              {hasRevenue ? (
                                <text
                                  x={point.x}
                                  y={point.y + 18}
                                  textAnchor="middle"
                                  dominantBaseline="middle"
                                  fontSize={18}
                                  fontWeight={800}
                                  fill={row.metric_amount < 0 ? "#991b1b" : "#065f46"}
                                  stroke="#ffffff"
                                  strokeWidth={5}
                                  paintOrder="stroke"
                                >
                                  {money(row.metric_amount)}
                                </text>
                              ) : null}
                            </g>
                          );
                        })}
                      </g>
                    </g>
                  </svg>
                </div>
              </div>
            )}
            {renderRevenueDetailPanel()}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CircleDollarSign className="h-5 w-5" />
            柜位收益汇总
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>柜位</TableHead>
                <TableHead>销售毛利</TableHead>
                <TableHead>收费</TableHead>
                <TableHead>补收</TableHead>
                <TableHead>总收益</TableHead>
                <TableHead>明细数</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {monthlyQuery.isLoading ? (
                <TableRow><TableCell colSpan={6} className="py-8 text-center text-muted-foreground">加载中...</TableCell></TableRow>
              ) : rows.length === 0 ? (
                <TableRow><TableCell colSpan={6} className="py-8 text-center text-muted-foreground">暂无数据</TableCell></TableRow>
              ) : (
                rows.map((row) => (
                  <TableRow key={row.unit_id} className="cursor-pointer hover:bg-slate-50" onClick={() => setSelectedUnit(row)}>
                    <TableCell className="font-medium">{row.unit_code}</TableCell>
                    <TableCell>{money(row.sales_gross_profit_amount)}</TableCell>
                    <TableCell>{money(row.fee_amount)}</TableCell>
                    <TableCell>{money(row.extra_amount)}</TableCell>
                    <TableCell className={amountClass(row.total_amount)}>{money(row.total_amount)}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {row.sales_detail_count + row.fee_detail_count + row.extra_detail_count}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CalendarDays className="h-5 w-5" />
            补收记录
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>日期</TableHead>
                <TableHead>柜位</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>金额</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {extras.length === 0 ? (
                <TableRow><TableCell colSpan={6} className="py-8 text-center text-muted-foreground">暂无补收</TableCell></TableRow>
              ) : (
                extras.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell>{row.revenue_date?.slice(0, 10)}</TableCell>
                    <TableCell>{row.unit_code || "—"}</TableCell>
                    <TableCell>{row.extra_type}</TableCell>
                    <TableCell>{money(row.amount)}</TableCell>
                    <TableCell>{statusBadge(row.status)}</TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        {row.status === "DRAFT" ? (
                          <Button size="sm" variant="outline" onClick={() => confirmExtra.mutate(row.id)}>
                            <CheckCircle2 className="mr-1 h-4 w-4" />
                            确认
                          </Button>
                        ) : null}
                        {row.status !== "VOID" ? (
                          <Button size="sm" variant="outline" onClick={() => voidExtra.mutate(row.id)}>
                            <XCircle className="mr-1 h-4 w-4" />
                            作废
                          </Button>
                        ) : null}
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

    </div>
  );
}
