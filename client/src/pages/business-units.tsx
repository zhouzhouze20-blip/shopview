import { Fragment, useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import GlobalStoreSelector from "@/components/global-store-selector";
import { useStore } from "@/contexts/StoreContext";
import { useToast } from "@/hooks/use-toast";
import { useBaseMapsList, useFloorDictList } from "@/hooks/useBaseMaps";
import { resolveApiAssetUrl } from "@/lib/api";
import { getPathVisualCenter } from "@/lib/svg-path-center";
import {
  BusinessUnitContractMode,
  BusinessUnitStatus,
  useBusinessUnits,
  useCreateBusinessUnit,
  useDeleteBusinessUnit,
  useUpdateBusinessUnit,
} from "@/hooks/useBusinessUnits";
import { useUnitMapVersions, useAlignTransform } from "@/hooks/useUnitMapVersions";
import { useGeoElements } from "@/hooks/useGeoElements";
import { Plus, Pencil, Trash2 } from "lucide-react";

const STATUS_OPTIONS: { value: BusinessUnitStatus; label: string }[] = [
  { value: "ACTIVE", label: "经营中" },
  { value: "VACANT", label: "空置" },
  { value: "FITOUT", label: "装修中" },
  { value: "INACTIVE", label: "失效" },
];

const statusLabel = (value: BusinessUnitStatus | string) =>
  STATUS_OPTIONS.find((option) => option.value === value)?.label ?? value;

const CONTRACT_MODE_OPTIONS: {
  value: BusinessUnitContractMode;
  label: string;
  description: string;
}[] = [
  {
    value: "EXCLUSIVE",
    label: "独占经营",
    description: "同一期间只允许一份正在生效合同",
  },
  {
    value: "SHARED",
    label: "共享经营",
    description: "同一期间允许多个合同同时经营",
  },
];

const contractModeLabel = (value?: BusinessUnitContractMode | string | null) =>
  CONTRACT_MODE_OPTIONS.find((option) => option.value === value)?.label ?? value ?? "独占经营";

const contractModeDescription = (value?: BusinessUnitContractMode | string | null) =>
  CONTRACT_MODE_OPTIONS.find((option) => option.value === value)?.description ?? "同一期间只允许一份正在生效合同";

type BusinessUnitsPageProps = {
  mode?: "business-units" | "counters";
};

export default function BusinessUnitsPage({ mode = "business-units" }: BusinessUnitsPageProps) {
  const { toast } = useToast();
  const { getCurrentFilter, stores } = useStore();
  const floorsQuery = useFloorDictList();
  const floorOptions = useMemo(() => floorsQuery.data ?? [], [floorsQuery.data]);
  const currentFilter = getCurrentFilter();
  const selectedStore = stores.find((store) => store.storeId === currentFilter.storeId) ?? null;
  const matchStoreRef = (storeRef?: string | null) => {
    const raw = storeRef?.trim();
    if (!currentFilter.storeId) return true;
    if (!raw) return false;
    return raw === String(currentFilter.storeId) || raw === String(selectedStore?.storeCode ?? "");
  };
  const storeDisplay = (storeRef?: string | null) => {
    const raw = storeRef?.trim();
    if (!raw) return "-";
    const matched = stores.find(
      (store) => raw === String(store.storeId) || raw === String(store.storeCode ?? ""),
    );
    return matched ? matched.storeName : raw;
  };
  const visibleFloorOptions = useMemo(
    () => floorOptions.filter((item) => matchStoreRef(item.store_id)),
    [floorOptions, currentFilter.storeId, selectedStore?.storeCode],
  );

  const [floorId, setFloorId] = useState<number | undefined>(undefined);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [keyword, setKeyword] = useState("");

  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [unitCode, setUnitCode] = useState("");
  const [statusValue, setStatusValue] = useState<BusinessUnitStatus>("ACTIVE");
  const [contractMode, setContractMode] = useState<BusinessUnitContractMode>("EXCLUSIVE");
  const [manualArea, setManualArea] = useState("");
  const [parentUnitId, setParentUnitId] = useState("");
  const [selectedBaseMapId, setSelectedBaseMapId] = useState<number | undefined>(undefined);
  const [selectedVersionId, setSelectedVersionId] = useState<number | undefined>(undefined);
  const [selectedGeoId, setSelectedGeoId] = useState<number | undefined>(undefined);
  const [mapEditOpen, setMapEditOpen] = useState(false);
  const [labelMode, setLabelMode] = useState<"NONE" | "PATH" | "UNIT">("UNIT");

  const listQuery = useBusinessUnits({
    storeId: currentFilter.storeId,
    floorId,
    status: statusFilter === "ALL" ? undefined : statusFilter,
    keyword: keyword.trim() || undefined,
  });
  const createMutation = useCreateBusinessUnit();
  const updateMutation = useUpdateBusinessUnit();
  const deleteMutation = useDeleteBusinessUnit();
  const baseMapsQuery = useBaseMapsList(floorId);
  const unitVersionsQuery = useUnitMapVersions(floorId, selectedBaseMapId, currentFilter.storeId);
  const geoQuery = useGeoElements(selectedVersionId);
  const alignQuery = useAlignTransform(selectedVersionId);

  const rows = useMemo(() => listQuery.data ?? [], [listQuery.data]);
  const baseMapOptions = useMemo(
    () => (baseMapsQuery.data ?? []).filter((item) => matchStoreRef(item.store_id)),
    [baseMapsQuery.data, currentFilter.storeId, selectedStore?.storeCode],
  );
  const versionOptions = useMemo(() => unitVersionsQuery.data ?? [], [unitVersionsQuery.data]);
  const geoRows = useMemo(() => geoQuery.data ?? [], [geoQuery.data]);
  const selectedBaseMap = useMemo(
    () => baseMapOptions.find((b) => b.id === selectedBaseMapId),
    [baseMapOptions, selectedBaseMapId],
  );
  const selectedBaseMapUrl = useMemo(
    () => resolveApiAssetUrl(selectedBaseMap?.file_url),
    [selectedBaseMap?.file_url],
  );
  const selectedGeoIndex = useMemo(
    () => geoRows.findIndex((g) => g.id === selectedGeoId),
    [geoRows, selectedGeoId],
  );
  const selectedGeo = useMemo(
    () => geoRows.find((g) => g.id === selectedGeoId),
    [geoRows, selectedGeoId],
  );
  const unitCodeMap = useMemo(() => {
    const m = new Map<number, string>();
    geoRows.forEach((g) => {
      if (g.unit_code) m.set(g.unit_id, g.unit_code);
    });
    rows.forEach((r) => m.set(r.id, r.unit_code));
    return m;
  }, [geoRows, rows]);
  const selectedUnitCode = useMemo(() => {
    if (!selectedGeo) return "";
    return unitCodeMap.get(selectedGeo.unit_id) || `unit-${selectedGeo.unit_id}`;
  }, [selectedGeo, unitCodeMap]);
  const vb = useMemo(() => {
    const raw = (selectedBaseMap?.svg_viewbox || "").trim();
    if (!raw) return null;
    const parts = raw.split(/\s+/).map((x) => Number(x));
    if (parts.length !== 4 || parts.some((n) => !Number.isFinite(n))) return null;
    return { x: parts[0], y: parts[1], w: parts[2], h: parts[3] };
  }, [selectedBaseMap?.svg_viewbox]);
  const align = useMemo(() => {
    const a = alignQuery.data;
    return {
      dx: a?.dx ?? 0,
      dy: a?.dy ?? 0,
      sx: a?.sx ?? 1,
      sy: a?.sy ?? 1,
      rotate: a?.rotate ?? 0,
    };
  }, [alignQuery.data]);
  const alignTransformText = useMemo(() => {
    if (!vb) return "";
    const cx = vb.x + vb.w / 2;
    const cy = vb.y + vb.h / 2;
    return `translate(${align.dx} ${align.dy}) rotate(${align.rotate} ${cx} ${cy}) scale(${align.sx} ${align.sy})`;
  }, [align, vb]);
  const geoLabelPoints = useMemo(() => {
    return geoRows.map((g) => {
      const cx =
        g.centroid_x ??
        (g.bbox_minx != null && g.bbox_maxx != null ? (g.bbox_minx + g.bbox_maxx) / 2 : null);
      const cy =
        g.centroid_y ??
        (g.bbox_miny != null && g.bbox_maxy != null ? (g.bbox_miny + g.bbox_maxy) / 2 : null);
      if (cx == null || cy == null) {
        const fallback = getPathVisualCenter(g.path_data);
        if (!fallback) return { id: g.id, x: null as number | null, y: null as number | null };
        return { id: g.id, x: fallback.x, y: fallback.y };
      }
      return { id: g.id, x: cx, y: cy };
    });
  }, [geoRows]);

  const isCountersMode = mode === "counters";
  const pageTitle = isCountersMode ? "柜位管理" : "经营单元设置";
  const pageDescription = isCountersMode ? "维护柜位主数据，并与图纸经营单元一一对应" : "维护 business_units 经营单元主数据";
  const createLabel = isCountersMode ? "新增柜位" : "新增经营单元";
  const editTitle = isCountersMode ? "编辑柜位" : "编辑经营单元";
  const createTitle = isCountersMode ? "新增柜位" : "新增经营单元";
  const codeLabel = isCountersMode ? "柜位编码" : "经营单元编码";
  const codePlaceholder = isCountersMode ? "如 B6-4A / A118 / B101" : "如 A118 / B101";
  const parentLabel = isCountersMode ? "父柜位ID（可选）" : "父经营单元ID（可选）";
  const listTitle = isCountersMode ? "柜位列表" : "经营单元列表";
  const emptyText = isCountersMode ? "暂无柜位数据" : "暂无经营单元数据";
  const deleteConfirmPrefix = isCountersMode ? "柜位" : "经营单元";
  const updateSuccessText = isCountersMode ? "柜位更新成功" : "经营单元更新成功";
  const createSuccessText = isCountersMode ? "柜位创建成功" : "经营单元创建成功";
  const mapEditTitle = isCountersMode ? "编辑柜位（图上选中）" : "编辑经营单元（图上选中）";

  const resetForm = () => {
    setEditingId(null);
    setUnitCode("");
    setStatusValue("ACTIVE");
    setContractMode("EXCLUSIVE");
    setManualArea("");
    setParentUnitId("");
  };

  useEffect(() => {
    if (floorId && floorOptions.length && !visibleFloorOptions.some((f) => f.id === floorId)) {
      setFloorId(undefined);
      setSelectedBaseMapId(undefined);
      setSelectedVersionId(undefined);
      setSelectedGeoId(undefined);
    }
  }, [floorId, floorOptions.length, visibleFloorOptions]);

  useEffect(() => {
    if (!baseMapOptions.length) {
      setSelectedBaseMapId(undefined);
      return;
    }
    if (selectedBaseMapId && baseMapOptions.some((b) => b.id === selectedBaseMapId)) return;
    const active = baseMapOptions.find((b) => b.is_active);
    setSelectedBaseMapId(active?.id ?? baseMapOptions[0].id);
  }, [baseMapOptions, selectedBaseMapId]);

  useEffect(() => {
    if (!versionOptions.length) {
      setSelectedVersionId(undefined);
      return;
    }
    if (selectedVersionId && versionOptions.some((v) => v.id === selectedVersionId)) return;
    const active = versionOptions.find((v) => v.is_active);
    setSelectedVersionId(active?.id ?? versionOptions[0].id);
  }, [versionOptions, selectedVersionId]);

  const pickGeoForEdit = (geoId: number) => {
    setSelectedGeoId(geoId);
    const geo = geoRows.find((g) => g.id === geoId);
    if (!geo) return;
    const unit = rows.find((r) => r.id === geo.unit_id);
    if (!unit) {
      if (geo.unit_code) {
        if (!floorId && geo.floor_id) setFloorId(geo.floor_id);
        setEditingId(geo.unit_id);
        setUnitCode(geo.unit_code);
        setStatusValue(geo.unit_status ?? "ACTIVE");
        setContractMode("EXCLUSIVE");
        setManualArea(geo.unit_manual_area != null ? String(geo.unit_manual_area) : "");
        setParentUnitId(geo.unit_parent_unit_id != null ? String(geo.unit_parent_unit_id) : "");
        setMapEditOpen(true);
        return;
      }
      toast({
        title: "未找到对应经营单元",
        description: `unit_id=${geo.unit_id}，请确认楼层筛选是否正确`,
        variant: "destructive",
      });
      return;
    }
    if (!floorId) setFloorId(unit.floor_id);
    setEditingId(unit.id);
    setUnitCode(unit.unit_code);
    setStatusValue(unit.status);
    setContractMode(unit.contract_mode ?? "EXCLUSIVE");
    setManualArea(unit.manual_area != null ? String(unit.manual_area) : "");
    setParentUnitId(unit.parent_unit_id != null ? String(unit.parent_unit_id) : "");
    setMapEditOpen(true);
  };

  const handleSubmit = async () => {
    if (!floorId) {
      toast({ title: "请先选择楼层", variant: "destructive" });
      return false;
    }
    if (!unitCode.trim()) {
      toast({ title: "请填写经营单元编码", variant: "destructive" });
      return false;
    }
    try {
      const payload = {
        floor_id: floorId,
        unit_code: unitCode.trim(),
        status: statusValue,
        contract_mode: contractMode,
        manual_area: manualArea.trim() ? Number(manualArea) : null,
        parent_unit_id: parentUnitId.trim() ? Number(parentUnitId) : null,
      };
      if (editingId) {
        await updateMutation.mutateAsync({
          id: editingId,
          input: {
            unit_code: payload.unit_code,
            status: payload.status,
            contract_mode: payload.contract_mode,
            manual_area: payload.manual_area,
            parent_unit_id: payload.parent_unit_id,
          },
        });
        toast({ title: updateSuccessText });
      } else {
        await createMutation.mutateAsync(payload);
        toast({ title: createSuccessText });
      }
      resetForm();
      setShowForm(false);
      return true;
    } catch (e) {
      toast({
        title: editingId ? "更新失败" : "创建失败",
        description: e instanceof Error ? e.message : String(e),
        variant: "destructive",
      });
      return false;
    }
  };

  const floorOptionLabel = (floor: (typeof floorOptions)[number]) =>
    `${storeDisplay(floor.store_id)} / ${floor.building_code}-${floor.floor_code} ${floor.name}`;

  const renderUnitForm = ({
    submitLabel,
    onCancel,
  }: {
    submitLabel: string;
    onCancel: () => void;
  }) => (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>{codeLabel}</Label>
          <Input value={unitCode} onChange={(e) => setUnitCode(e.target.value)} placeholder={codePlaceholder} />
        </div>
        <div className="space-y-2">
          <Label>状态</Label>
          <Select value={statusValue} onValueChange={(v) => setStatusValue(v as BusinessUnitStatus)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="z-50 bg-white border shadow-xl">
              {STATUS_OPTIONS.map((s) => (
                <SelectItem key={s.value} value={s.value}>
                  {s.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2 md:col-span-2">
          <Label>合同经营限制</Label>
          <Select value={contractMode} onValueChange={(v) => setContractMode(v as BusinessUnitContractMode)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="z-50 bg-white border shadow-xl">
              {CONTRACT_MODE_OPTIONS.map((mode) => (
                <SelectItem key={mode.value} value={mode.value}>
                  {mode.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">{contractModeDescription(contractMode)}</p>
        </div>
        <div className="space-y-2">
          <Label>人工面积（可选）</Label>
          <Input value={manualArea} onChange={(e) => setManualArea(e.target.value)} inputMode="decimal" placeholder="例如 98.5" />
        </div>
        <div className="space-y-2">
          <Label>{parentLabel}</Label>
          <Input value={parentUnitId} onChange={(e) => setParentUnitId(e.target.value)} inputMode="numeric" placeholder="例如 1001" />
        </div>
      </div>
      <div className="flex items-center justify-end gap-2">
        <Button variant="outline" onClick={onCancel}>
          取消
        </Button>
        <Button onClick={handleSubmit} disabled={createMutation.isPending || updateMutation.isPending}>
          {submitLabel}
        </Button>
      </div>
    </div>
  );

  return (
    <div className="container mx-auto p-6 space-y-6" data-testid="business-units-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{pageTitle}</h1>
          <p className="text-sm text-muted-foreground mt-1">{pageDescription}</p>
        </div>
        <Button
          onClick={() => {
            if (showForm) {
              resetForm();
              setShowForm(false);
              return;
            }
            resetForm();
            setShowForm(true);
          }}
        >
          <Plus className="w-4 h-4 mr-2" />
          {createLabel}
        </Button>
      </div>

      <GlobalStoreSelector compact className="mb-2" />

      <Card>
        <CardHeader>
          <CardTitle>筛选条件</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="space-y-2">
            <Label>楼层</Label>
            <Select value={floorId ? String(floorId) : "ALL"} onValueChange={(v) => setFloorId(v === "ALL" ? undefined : Number(v))}>
              <SelectTrigger>
                <SelectValue placeholder="全部楼层" />
              </SelectTrigger>
              <SelectContent className="z-50 bg-white border shadow-xl">
                <SelectItem value="ALL">全部楼层</SelectItem>
                {visibleFloorOptions.map((f) => (
                  <SelectItem key={f.id} value={String(f.id)}>
                    {floorOptionLabel(f)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>状态</Label>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="z-50 bg-white border shadow-xl">
                <SelectItem value="ALL">全部状态</SelectItem>
                {STATUS_OPTIONS.map((s) => (
                  <SelectItem key={s.value} value={s.value}>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2 md:col-span-2">
            <Label>编码搜索</Label>
            <Input
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              placeholder="输入 unit_code 关键字"
            />
          </div>
        </CardContent>
      </Card>

      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle>{createTitle}</CardTitle>
          </CardHeader>
          <CardContent>
            {renderUnitForm({
              submitLabel: createLabel,
              onCancel: () => {
                resetForm();
                setShowForm(false);
              },
            })}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>{listTitle}</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>楼层ID</TableHead>
                <TableHead>{codeLabel}</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>合同经营限制</TableHead>
                <TableHead>人工面积</TableHead>
                <TableHead>{parentLabel.replace("（可选）", "")}</TableHead>
                <TableHead>更新时间</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {listQuery.isLoading ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                    加载中...
                  </TableCell>
                </TableRow>
              ) : rows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                    {emptyText}
                  </TableCell>
                </TableRow>
              ) : (
                rows.map((r) => (
                  <Fragment key={r.id}>
                    <TableRow data-state={editingId === r.id ? "selected" : undefined}>
                      <TableCell>{r.id}</TableCell>
                      <TableCell>{r.floor_id}</TableCell>
                      <TableCell>{r.unit_code}</TableCell>
                      <TableCell>{statusLabel(r.status)}</TableCell>
                      <TableCell>
                        <div className="space-y-1">
                          <div>{contractModeLabel(r.contract_mode)}</div>
                          <div className="text-xs text-muted-foreground">{contractModeDescription(r.contract_mode)}</div>
                        </div>
                      </TableCell>
                      <TableCell>{r.manual_area ?? "—"}</TableCell>
                      <TableCell>{r.parent_unit_id ?? "—"}</TableCell>
                      <TableCell>{r.updated_at ?? "—"}</TableCell>
                      <TableCell className="text-right space-x-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setEditingId(r.id);
                            setUnitCode(r.unit_code);
                            setStatusValue(r.status);
                            setContractMode(r.contract_mode ?? "EXCLUSIVE");
                            setManualArea(r.manual_area != null ? String(r.manual_area) : "");
                            setParentUnitId(r.parent_unit_id != null ? String(r.parent_unit_id) : "");
                            setShowForm(false);
                            if (!floorId) setFloorId(r.floor_id);
                          }}
                        >
                          <Pencil className="w-4 h-4 mr-1" />
                          编辑
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-red-600 hover:text-red-700"
                          onClick={async () => {
                            if (!window.confirm(`确定删除${deleteConfirmPrefix} ${r.unit_code} 吗？`)) return;
                            try {
                              const result = await deleteMutation.mutateAsync(r.id);
                              toast({
                                title: "删除成功",
                                description: result.detached_bindings
                                  ? `已暂时解除 ${result.detached_bindings} 条柜组/合同绑定，后续可重新设置关联。`
                                  : undefined,
                              });
                            } catch (e) {
                              toast({
                                title: "删除失败",
                                description: e instanceof Error ? e.message : String(e),
                                variant: "destructive",
                              });
                            }
                          }}
                        >
                          <Trash2 className="w-4 h-4 mr-1" />
                          删除
                        </Button>
                      </TableCell>
                    </TableRow>
                    {editingId === r.id && (
                      <TableRow>
                        <TableCell colSpan={9} className="bg-slate-50 p-4">
                          <div className="rounded-md border bg-white p-4">
                            <div className="mb-4 text-base font-semibold">{editTitle}</div>
                            {renderUnitForm({
                              submitLabel: "保存修改",
                              onCancel: resetForm,
                            })}
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </Fragment>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>图上逐个编辑</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>底图</Label>
              <Select
                value={selectedBaseMapId ? String(selectedBaseMapId) : ""}
                onValueChange={(v) => setSelectedBaseMapId(Number(v))}
                disabled={!floorId || baseMapsQuery.isLoading}
              >
                <SelectTrigger>
                  <SelectValue placeholder={!floorId ? "先选择楼层" : "选择底图"} />
                </SelectTrigger>
                <SelectContent className="z-50 bg-white border shadow-xl">
                  {baseMapOptions.map((b) => (
                    <SelectItem key={b.id} value={String(b.id)}>
                      {b.base_map_code} {b.is_active ? "(active)" : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>柜位图版本</Label>
              <Select
                value={selectedVersionId ? String(selectedVersionId) : ""}
                onValueChange={(v) => setSelectedVersionId(Number(v))}
                disabled={!selectedBaseMapId || unitVersionsQuery.isLoading}
              >
                <SelectTrigger>
                  <SelectValue placeholder={!selectedBaseMapId ? "先选择底图" : "选择版本"} />
                </SelectTrigger>
                <SelectContent className="z-50 bg-white border shadow-xl">
                  {versionOptions.map((v) => (
                    <SelectItem key={v.id} value={String(v.id)}>
                      {v.version_code} {v.is_active ? "(active)" : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              disabled={selectedGeoIndex <= 0}
              onClick={() => {
                const prev = geoRows[selectedGeoIndex - 1];
                if (prev) pickGeoForEdit(prev.id);
              }}
            >
              上一个
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={selectedGeoIndex < 0 || selectedGeoIndex >= geoRows.length - 1}
              onClick={() => {
                const next = geoRows[selectedGeoIndex + 1];
                if (next) pickGeoForEdit(next.id);
              }}
            >
              下一个
            </Button>
            <div className="text-xs text-muted-foreground">
              {selectedGeo
                ? `当前 path: ${selectedGeo.svg_element_id || selectedGeo.id}（unit_id=${selectedGeo.unit_id}，编码=${selectedUnitCode}）`
                : "点击图中蓝色区域开始编辑"}
            </div>
            <div className="ml-auto w-[220px]">
              <Select value={labelMode} onValueChange={(v) => setLabelMode(v as "NONE" | "PATH" | "UNIT")}>
                <SelectTrigger className="h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="z-50 bg-white border shadow-xl">
                  <SelectItem value="NONE">不显示标签</SelectItem>
                  <SelectItem value="PATH">显示 Path ID</SelectItem>
                  <SelectItem value="UNIT">显示经营单元编码</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {!selectedBaseMapUrl ? (
            <div className="text-sm text-muted-foreground">请先选择楼层与底图</div>
          ) : !vb ? (
            <div className="text-sm text-muted-foreground">当前底图缺少有效 viewBox，无法在图上叠加编辑</div>
          ) : (
            <div className="rounded-lg border bg-white overflow-hidden">
              <div className="px-4 py-2 border-b text-xs text-muted-foreground">
                版本几何数量：{geoRows.length}（点击蓝色区域进入编辑）
              </div>
              <div className="relative w-full aspect-[16/10] bg-slate-50">
                <svg className="absolute inset-0 w-full h-full" viewBox={`${vb.x} ${vb.y} ${vb.w} ${vb.h}`} preserveAspectRatio="xMidYMid meet">
                  <image href={selectedBaseMapUrl} x={vb.x} y={vb.y} width={vb.w} height={vb.h} />
                  <g transform={alignTransformText}>
                    {geoRows.map((g) => {
                      const isSelected = g.id === selectedGeoId;
                      return (
                        <path
                          key={g.id}
                          d={g.path_data}
                          fill={isSelected ? "rgba(239,68,68,0.25)" : "rgba(59,130,246,0.18)"}
                          stroke={isSelected ? "rgba(220,38,38,0.95)" : "rgba(37,99,235,0.9)"}
                          strokeWidth={isSelected ? 3 : 2}
                          vectorEffect="non-scaling-stroke"
                          className="cursor-pointer"
                          onClick={() => pickGeoForEdit(g.id)}
                        />
                      );
                    })}
                    {labelMode !== "NONE" &&
                      geoLabelPoints.map((p) => {
                        if (p.x == null || p.y == null) return null;
                        const geo = geoRows.find((g) => g.id === p.id);
                        if (!geo) return null;
                        const isSelected = geo.id === selectedGeoId;
                        const textValue =
                          labelMode === "PATH"
                            ? geo.svg_element_id || `path-${geo.id}`
                            : unitCodeMap.get(geo.unit_id) || `unit-${geo.unit_id}`;
                        const fontSize = labelMode === "UNIT" ? (isSelected ? 32 : 28) : 10;
                        const strokeWidth = labelMode === "UNIT" ? 6 : 2;
                        return (
                          <text
                            key={`label-${geo.id}`}
                            x={p.x}
                            y={p.y}
                            textAnchor="middle"
                            dominantBaseline="middle"
                            fontSize={fontSize}
                            fontWeight={labelMode === "UNIT" ? 700 : 500}
                            fill="#1e293b"
                            stroke="#ffffff"
                            strokeWidth={strokeWidth}
                            paintOrder="stroke"
                            pointerEvents="none"
                          >
                            {textValue}
                          </text>
                        );
                      })}

                    {/* 始终在“当前选中区域”中心显示经营单元编码，便于逐个校对 */}
                    {selectedGeo &&
                      (() => {
                        const pt = geoLabelPoints.find((x) => x.id === selectedGeo.id);
                        if (!pt || pt.x == null || pt.y == null) return null;
                        return (
                          <text
                            x={pt.x}
                            y={pt.y}
                            textAnchor="middle"
                            dominantBaseline="middle"
                            fontSize={40}
                            fontWeight={800}
                            fill="#dc2626"
                            stroke="#ffffff"
                            strokeWidth={8}
                            paintOrder="stroke"
                            pointerEvents="none"
                          >
                            {selectedUnitCode}
                          </text>
                        );
                      })()}
                  </g>
                </svg>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={mapEditOpen} onOpenChange={setMapEditOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>{mapEditTitle}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="text-xs text-muted-foreground">
              {selectedGeo
                ? `path: ${selectedGeo.svg_element_id || selectedGeo.id}，unit_id=${selectedGeo.unit_id}`
                : "未选中图元"}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>{codeLabel}</Label>
                <Input value={unitCode} onChange={(e) => setUnitCode(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>状态</Label>
                <Select value={statusValue} onValueChange={(v) => setStatusValue(v as BusinessUnitStatus)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="z-50 bg-white border shadow-xl">
                    {STATUS_OPTIONS.map((s) => (
                      <SelectItem key={s.value} value={s.value}>
                        {s.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2 md:col-span-2">
                <Label>合同经营限制</Label>
                <Select value={contractMode} onValueChange={(v) => setContractMode(v as BusinessUnitContractMode)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="z-50 bg-white border shadow-xl">
                    {CONTRACT_MODE_OPTIONS.map((mode) => (
                      <SelectItem key={mode.value} value={mode.value}>
                        {mode.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">{contractModeDescription(contractMode)}</p>
              </div>
              <div className="space-y-2">
                <Label>人工面积（可选）</Label>
                <Input value={manualArea} onChange={(e) => setManualArea(e.target.value)} inputMode="decimal" />
              </div>
              <div className="space-y-2">
                <Label>{parentLabel}</Label>
                <Input value={parentUnitId} onChange={(e) => setParentUnitId(e.target.value)} inputMode="numeric" />
              </div>
            </div>
            <div className="flex items-center justify-start gap-2 border-t pt-4">
              <Button
                onClick={async () => {
                  const ok = await handleSubmit();
                  if (ok) setMapEditOpen(false);
                }}
                disabled={createMutation.isPending || updateMutation.isPending}
              >
                保存
              </Button>
              <Button variant="outline" onClick={() => setMapEditOpen(false)}>
                取消
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
