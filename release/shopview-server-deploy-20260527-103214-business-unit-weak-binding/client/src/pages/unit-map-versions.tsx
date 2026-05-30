import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import GlobalStoreSelector from "@/components/global-store-selector";
import { useStore } from "@/contexts/StoreContext";
import { useToast } from "@/hooks/use-toast";
import { useFloorDictList, useBaseMapsList } from "@/hooks/useBaseMaps";
import { getApiUrl, resolveApiAssetUrl } from "@/lib/api";
import { useGeoElements } from "@/hooks/useGeoElements";
import {
  useActivateUnitMapVersion,
  useAlignTransform,
  useCreateUnitMapVersion,
  useDeleteUnitMapVersion,
  useSaveAlignTransform,
  useUnitMapVersions,
  useUpdateUnitMapVersion,
} from "@/hooks/useUnitMapVersions";
import { Pencil, Trash2 } from "lucide-react";

export default function UnitMapVersionsPage() {
  const { toast } = useToast();
  const { getCurrentFilter, stores } = useStore();
  const floorsQuery = useFloorDictList();

  const [floorId, setFloorId] = useState<number | undefined>(undefined);
  const baseMapsQuery = useBaseMapsList(floorId);
  const [baseMapId, setBaseMapId] = useState<number | undefined>(undefined);
  const [importingId, setImportingId] = useState<number | null>(null);

  const [versionCode, setVersionCode] = useState("");
  const [changeNote, setChangeNote] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [previewVersionId, setPreviewVersionId] = useState<number | undefined>(undefined);

  const currentFilter = getCurrentFilter();
  const selectedStore = stores.find((store) => store.storeId === currentFilter.storeId) ?? null;
  const versionsQuery = useUnitMapVersions(floorId, baseMapId, currentFilter.storeId);
  const createVersion = useCreateUnitMapVersion();
  const activateVersion = useActivateUnitMapVersion();
  const updateVersion = useUpdateUnitMapVersion();
  const deleteVersion = useDeleteUnitMapVersion();
  const geoQuery = useGeoElements(previewVersionId);
  const alignQuery = useAlignTransform(previewVersionId);
  const saveAlign = useSaveAlignTransform();
  const [align, setAlign] = useState({ dx: 0, dy: 0, sx: 1, sy: 1, rotate: 0 });
  const [editOpen, setEditOpen] = useState(false);
  const [editingVersionId, setEditingVersionId] = useState<number | null>(null);
  const [editVersionCode, setEditVersionCode] = useState("");
  const [editChangeNote, setEditChangeNote] = useState("");
  const [editIsActive, setEditIsActive] = useState(false);

  const floorOptions = useMemo(() => floorsQuery.data ?? [], [floorsQuery.data]);
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
  const baseMapOptions = useMemo(
    () => (baseMapsQuery.data ?? []).filter((item) => matchStoreRef(item.store_id)),
    [baseMapsQuery.data, currentFilter.storeId, selectedStore?.storeCode],
  );
  const selectedBaseMap = useMemo(
    () => baseMapOptions.find((m) => m.id === baseMapId),
    [baseMapOptions, baseMapId],
  );
  const previewVersion = useMemo(
    () => versionsQuery.data?.find((v) => v.id === previewVersionId),
    [versionsQuery.data, previewVersionId],
  );
  const previewBaseMap = useMemo(
    () => baseMapOptions.find((m) => m.id === (previewVersion?.base_map_id ?? baseMapId)),
    [baseMapOptions, previewVersion?.base_map_id, baseMapId],
  );
  const viewBox = previewBaseMap?.svg_viewbox || selectedBaseMap?.svg_viewbox || undefined;
  const previewBaseMapUrl = resolveApiAssetUrl(previewBaseMap?.file_url ?? selectedBaseMap?.file_url);
  const vb = useMemo(() => {
    const v = viewBox?.trim();
    if (!v) return null;
    const parts = v.split(/\s+/).map((x) => Number(x));
    if (parts.length !== 4 || parts.some((n) => !Number.isFinite(n))) return null;
    return { x: parts[0], y: parts[1], w: parts[2], h: parts[3] };
  }, [viewBox]);
  const alignTransformText = useMemo(() => {
    if (!vb) return "";
    const cx = vb.x + vb.w / 2;
    const cy = vb.y + vb.h / 2;
    // 右到左应用：先 scale，再 rotate(中心点)，最后 translate
    return `translate(${align.dx} ${align.dy}) rotate(${align.rotate} ${cx} ${cy}) scale(${align.sx} ${align.sy})`;
  }, [align, vb]);

  useEffect(() => {
    if (floorId && floorOptions.length && !visibleFloorOptions.some((f) => f.id === floorId)) {
      setFloorId(undefined);
      setBaseMapId(undefined);
      setPreviewVersionId(undefined);
    }
  }, [floorId, floorOptions.length, visibleFloorOptions]);

  useEffect(() => {
    if (baseMapId && !baseMapOptions.some((m) => m.id === baseMapId)) {
      setBaseMapId(undefined);
      setPreviewVersionId(undefined);
    }
  }, [baseMapId, baseMapOptions]);

  useEffect(() => {
    if (!alignQuery.data) {
      setAlign({ dx: 0, dy: 0, sx: 1, sy: 1, rotate: 0 });
      return;
    }
    setAlign({
      dx: alignQuery.data.dx,
      dy: alignQuery.data.dy,
      sx: alignQuery.data.sx,
      sy: alignQuery.data.sy,
      rotate: alignQuery.data.rotate,
    });
  }, [alignQuery.data]);

  const openEditDialog = (versionId: number) => {
    const target = versionsQuery.data?.find((item) => item.id === versionId);
    if (!target) return;
    setEditingVersionId(target.id);
    setEditVersionCode(target.version_code);
    setEditChangeNote(target.change_note ?? "");
    setEditIsActive(target.is_active);
    setEditOpen(true);
  };

  const handleEditSubmit = async () => {
    if (!editingVersionId) return;
    if (!editVersionCode.trim()) {
      toast({ title: "请填写版本编码", variant: "destructive" });
      return;
    }
    try {
      const updated = await updateVersion.mutateAsync({
        id: editingVersionId,
        input: {
          version_code: editVersionCode.trim(),
          change_note: editChangeNote.trim() || null,
          is_active: editIsActive,
        },
      });
      toast({ title: "版本更新成功" });
      if (previewVersionId === editingVersionId) {
        setPreviewVersionId(updated.id);
      }
      setEditOpen(false);
    } catch (e) {
      toast({
        title: "版本更新失败",
        description: e instanceof Error ? e.message : String(e),
        variant: "destructive",
      });
    }
  };

  const importSvg = async (versionId: number, file: File) => {
    setImportingId(versionId);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${getApiUrl()}/api/unit-map-versions/${versionId}/import-svg`, {
        method: "PUT",
        body: formData,
      });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(t || `HTTP ${res.status}`);
      }
      const data = await res.json();
      toast({ title: "导入成功", description: `unit_code=${data.unit_code}` });
      setPreviewVersionId(versionId);
    } catch (e) {
      toast({
        title: "导入失败",
        description: e instanceof Error ? e.message : String(e),
        variant: "destructive",
      });
    } finally {
      setImportingId(null);
    }
  };

  const handleCreate = async () => {
    if (!floorId) {
      toast({ title: "请先选择楼层", variant: "destructive" });
      return;
    }
    if (!baseMapId) {
      toast({ title: "请先选择底图", variant: "destructive" });
      return;
    }
    let finalCode = versionCode.trim();
    if (!finalCode) {
      const floor = floorOptions.find((f) => f.id === floorId);
      const floorCode = floor?.floor_code || "F";
      const now = new Date();
      const pad = (n: number) => n.toString().padStart(2, "0");
      const ts = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}${pad(
        now.getHours(),
      )}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
      finalCode = `UNIT_${floorCode}_${ts}`;
      setVersionCode(finalCode);
    }
    try {
      const created = await createVersion.mutateAsync({
        floor_id: floorId,
        base_map_id: baseMapId,
        version_code: finalCode,
        change_note: changeNote.trim() || undefined,
        is_active: isActive,
      });
      toast({
        title: "版本创建成功",
        description: created.version_code,
      });
    } catch (e) {
      toast({
        title: "创建失败",
        description: e instanceof Error ? e.message : String(e),
        variant: "destructive",
      });
    }
  };

  const floorOptionLabel = (floor: (typeof floorOptions)[number]) =>
    `${storeDisplay(floor.store_id)} / ${floor.building_code}-${floor.floor_code} ${floor.name}`;

  return (
    <div className="container mx-auto p-6 space-y-6" data-testid="unit-map-versions-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">柜位图版本管理</h1>
          <p className="text-sm text-muted-foreground mt-1">
            针对每个楼层/底图维护柜位图版本，并设定当前生效版本
          </p>
        </div>
      </div>

      <GlobalStoreSelector compact className="mb-2" />

      <Card>
        <CardHeader>
          <CardTitle>创建新版本</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>楼层</Label>
              <Select
                value={floorId ? String(floorId) : ""}
                onValueChange={(v) => {
                  const id = Number(v);
                  setFloorId(id);
                  setBaseMapId(undefined);
                }}
                disabled={floorsQuery.isLoading || !!floorsQuery.error}
              >
                <SelectTrigger>
                  <SelectValue placeholder={floorsQuery.isLoading ? "加载中..." : "选择楼层"} />
                </SelectTrigger>
                <SelectContent className="z-50 bg-white/95 backdrop-blur border shadow-xl max-h-72">
                  {visibleFloorOptions.length ? (
                    visibleFloorOptions.map((f) => (
                      <SelectItem key={f.id} value={String(f.id)}>
                        {floorOptionLabel(f)}
                      </SelectItem>
                    ))
                  ) : (
                    <div className="px-3 py-2 text-sm text-muted-foreground">
                      {floorsQuery.error
                        ? "楼层加载失败，请确认后端已启动"
                        : currentFilter.storeId
                          ? "当前门店下暂无楼层数据"
                          : "暂无楼层数据，请先在楼层定义页面创建"}
                    </div>
                  )}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>底图</Label>
              <Select
                value={baseMapId ? String(baseMapId) : ""}
                onValueChange={(v) => setBaseMapId(Number(v))}
                disabled={!floorId || baseMapsQuery.isLoading || !!baseMapsQuery.error}
              >
                <SelectTrigger>
                  <SelectValue placeholder={!floorId ? "先选择楼层" : "选择底图"} />
                </SelectTrigger>
                <SelectContent className="z-50 bg-white/95 backdrop-blur border shadow-xl max-h-72">
                  {baseMapOptions.length ? (
                    baseMapOptions.map((m) => (
                      <SelectItem key={m.id} value={String(m.id)}>
                        {m.base_map_code} {m.is_active ? "(active)" : ""}
                      </SelectItem>
                    ))
                  ) : (
                    <div className="px-3 py-2 text-sm text-muted-foreground">
                      {baseMapsQuery.isLoading
                        ? "加载中..."
                        : baseMapsQuery.error
                          ? "底图加载失败，请确认后端已启动"
                          : "该楼层暂无底图，请先在底图管理中上传"}
                    </div>
                  )}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="versionCode">版本编码</Label>
              <Input
                id="versionCode"
                value={versionCode}
                onChange={(e) => setVersionCode(e.target.value)}
                placeholder="UNIT_1F_20260125"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="changeNote">版本说明（可选）</Label>
              <Input
                id="changeNote"
                value={changeNote}
                onChange={(e) => setChangeNote(e.target.value)}
                placeholder="例如：A01 拆分为 A01-1 / A01-2"
              />
            </div>
          </div>

          <div className="rounded-lg border bg-slate-50 px-4 py-3 flex items-center justify-between">
            <div className="space-y-1">
              <div className="text-sm font-medium text-slate-900">设为当前柜位图版本</div>
              <div className="text-xs text-muted-foreground">同一楼层仅一个 active</div>
            </div>
            <div className="flex items-center gap-3">
              <div className={`text-xs font-medium ${isActive ? "text-emerald-700" : "text-slate-500"}`}>
                {isActive ? "是" : "否"}
              </div>
              <Switch checked={isActive} onCheckedChange={setIsActive} />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button
              onClick={handleCreate}
              disabled={createVersion.isPending}
              className="w-full h-11 text-base"
            >
              {createVersion.isPending ? "创建中..." : "创建版本"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>版本列表</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {versionsQuery.isLoading ? (
            <div className="text-sm text-muted-foreground">加载中...</div>
          ) : versionsQuery.error ? (
            <div className="text-sm text-red-600">
              版本列表加载失败：{versionsQuery.error instanceof Error ? versionsQuery.error.message : String(versionsQuery.error)}
            </div>
          ) : versionsQuery.data?.length ? (
            <div className="space-y-2">
              {versionsQuery.data.map((v) => (
                <div key={v.id} className="flex items-center justify-between rounded border p-3">
                  <div className="min-w-0">
                    <div className="font-medium truncate">
                      {v.version_code} {v.is_active ? "(active)" : ""}
                    </div>
                    {v.change_note && (
                      <div className="text-xs text-muted-foreground truncate">{v.change_note}</div>
                    )}
                    {v.created_at && (
                      <div className="text-xs text-muted-foreground">创建时间：{v.created_at}</div>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <label className="inline-flex items-center">
                      <input
                        type="file"
                        accept=".svg,image/svg+xml"
                        className="hidden"
                        onChange={(e) => {
                          const f = e.target.files?.[0];
                          if (f) importSvg(v.id, f);
                          e.currentTarget.value = "";
                        }}
                      />
                      <Button
                        type="button"
                        size="sm"
                        variant="secondary"
                        disabled={importingId === v.id}
                        onClick={(e) => {
                          const input = (e.currentTarget.parentElement?.querySelector("input[type=file]") as HTMLInputElement | null);
                          input?.click();
                        }}
                      >
                        {importingId === v.id ? "导入中..." : "导入SVG"}
                      </Button>
                    </label>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setPreviewVersionId(v.id)}
                    >
                      预览
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => openEditDialog(v.id)}
                    >
                      <Pencil className="w-4 h-4 mr-2" />
                      编辑
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="text-red-600 hover:text-red-700"
                      disabled={deleteVersion.isPending}
                      onClick={async () => {
                        if (!window.confirm(`确定删除版本 ${v.version_code} 吗？`)) return;
                        try {
                          await deleteVersion.mutateAsync(v.id);
                          if (previewVersionId === v.id) {
                            setPreviewVersionId(undefined);
                          }
                          toast({ title: "版本已删除" });
                        } catch (e) {
                          toast({
                            title: "删除失败",
                            description: e instanceof Error ? e.message : String(e),
                            variant: "destructive",
                          });
                        }
                      }}
                    >
                      <Trash2 className="w-4 h-4 mr-2" />
                      删除
                    </Button>
                    {!v.is_active && (
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={activateVersion.isPending}
                        onClick={async () => {
                          try {
                            await activateVersion.mutateAsync(v.id);
                            toast({ title: "已设为当前版本" });
                            versionsQuery.refetch();
                          } catch (e) {
                            toast({
                              title: "设置失败",
                              description: e instanceof Error ? e.message : String(e),
                              variant: "destructive",
                            });
                          }
                        }}
                      >
                        设为 active
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-sm text-muted-foreground">
              暂无版本，请先选择楼层和底图并创建新版本
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>柜位图预览</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {!previewBaseMapUrl ? (
            <div className="text-sm text-muted-foreground">请先选择楼层与底图</div>
          ) : !vb ? (
            <div className="text-sm text-muted-foreground">
              当前底图缺少可用的 viewBox（请在底图管理里填写 svg_viewbox，例如：0 0 3508 2480）
            </div>
          ) : !previewVersionId ? (
            <div className="text-sm text-muted-foreground">在版本列表点“预览”，即可显示导入的柜位路径</div>
          ) : (
            <div className="space-y-3">
              <div className="rounded-lg border bg-slate-50 p-3">
                <div className="text-sm font-medium mb-2">对齐微调（当前版本）</div>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                  <Input
                    value={String(align.dx)}
                    onChange={(e) => setAlign((s) => ({ ...s, dx: Number(e.target.value) || 0 }))}
                    placeholder="dx"
                    inputMode="decimal"
                  />
                  <Input
                    value={String(align.dy)}
                    onChange={(e) => setAlign((s) => ({ ...s, dy: Number(e.target.value) || 0 }))}
                    placeholder="dy"
                    inputMode="decimal"
                  />
                  <Input
                    value={String(align.sx)}
                    onChange={(e) => setAlign((s) => ({ ...s, sx: Number(e.target.value) || 1 }))}
                    placeholder="sx"
                    inputMode="decimal"
                  />
                  <Input
                    value={String(align.sy)}
                    onChange={(e) => setAlign((s) => ({ ...s, sy: Number(e.target.value) || 1 }))}
                    placeholder="sy"
                    inputMode="decimal"
                  />
                  <Input
                    value={String(align.rotate)}
                    onChange={(e) => setAlign((s) => ({ ...s, rotate: Number(e.target.value) || 0 }))}
                    placeholder="rotate"
                    inputMode="decimal"
                  />
                </div>
                <div className="mt-2 flex items-center gap-2 flex-wrap">
                  <Button size="sm" variant="outline" onClick={() => setAlign((s) => ({ ...s, dx: s.dx - 5 }))}>左5</Button>
                  <Button size="sm" variant="outline" onClick={() => setAlign((s) => ({ ...s, dx: s.dx + 5 }))}>右5</Button>
                  <Button size="sm" variant="outline" onClick={() => setAlign((s) => ({ ...s, dy: s.dy - 5 }))}>上5</Button>
                  <Button size="sm" variant="outline" onClick={() => setAlign((s) => ({ ...s, dy: s.dy + 5 }))}>下5</Button>
                  <Button size="sm" variant="outline" onClick={() => setAlign((s) => ({ ...s, sx: Number((s.sx * 1.002).toFixed(6)), sy: Number((s.sy * 1.002).toFixed(6)) }))}>放大</Button>
                  <Button size="sm" variant="outline" onClick={() => setAlign((s) => ({ ...s, sx: Number((s.sx / 1.002).toFixed(6)), sy: Number((s.sy / 1.002).toFixed(6)) }))}>缩小</Button>
                  <Button size="sm" variant="outline" onClick={() => setAlign((s) => ({ ...s, rotate: Number((s.rotate - 0.1).toFixed(3)) }))}>左转0.1°</Button>
                  <Button size="sm" variant="outline" onClick={() => setAlign((s) => ({ ...s, rotate: Number((s.rotate + 0.1).toFixed(3)) }))}>右转0.1°</Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setAlign({ dx: 0, dy: 0, sx: 1, sy: 1, rotate: 0 })}
                  >
                    重置
                  </Button>
                  <Button
                    size="sm"
                    onClick={async () => {
                      if (!previewVersionId) return;
                      try {
                        await saveAlign.mutateAsync({
                          version_id: previewVersionId,
                          dx: align.dx,
                          dy: align.dy,
                          sx: align.sx,
                          sy: align.sy,
                          rotate: align.rotate,
                        });
                        toast({ title: "微调参数已保存" });
                      } catch (e) {
                        toast({
                          title: "保存微调失败",
                          description: e instanceof Error ? e.message : String(e),
                          variant: "destructive",
                        });
                      }
                    }}
                    disabled={saveAlign.isPending || align.sx <= 0 || align.sy <= 0}
                  >
                    {saveAlign.isPending ? "保存中..." : "保存参数"}
                  </Button>
                </div>
              </div>
              <div className="rounded-lg border bg-white overflow-hidden">
              <div className="px-4 py-2 border-b text-xs text-muted-foreground flex items-center justify-between">
                <div>
                  版本ID：{previewVersionId} ｜ 几何数量：{geoQuery.data?.length ?? 0}
                </div>
                <Button size="sm" variant="outline" onClick={() => geoQuery.refetch()} disabled={geoQuery.isLoading}>
                  刷新
                </Button>
              </div>
              <div className="relative w-full aspect-[16/10] bg-slate-50">
                <svg
                  className="absolute inset-0 w-full h-full"
                  viewBox={`${vb.x} ${vb.y} ${vb.w} ${vb.h}`}
                  preserveAspectRatio="xMidYMid meet"
                >
                  {/* 底图 */}
                  <image href={previewBaseMapUrl} x={vb.x} y={vb.y} width={vb.w} height={vb.h} />
                  {/* 柜位路径 */}
                  <g transform={alignTransformText}>
                    {(geoQuery.data ?? []).map((g) => (
                      <path
                        key={g.id}
                        d={g.path_data}
                        fill="rgba(59, 130, 246, 0.18)"
                        stroke="rgba(37, 99, 235, 0.9)"
                        strokeWidth={2}
                        vectorEffect="non-scaling-stroke"
                      />
                    ))}
                  </g>
                </svg>
              </div>
            </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>编辑柜位图版本</DialogTitle>
          </DialogHeader>
          <div className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="editVersionCode">版本编码</Label>
              <Input
                id="editVersionCode"
                value={editVersionCode}
                onChange={(e) => setEditVersionCode(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="editChangeNote">版本说明（可选）</Label>
              <Input
                id="editChangeNote"
                value={editChangeNote}
                onChange={(e) => setEditChangeNote(e.target.value)}
              />
            </div>
            <div className="rounded-lg border bg-slate-50 px-4 py-3 flex items-center justify-between">
              <div className="space-y-1">
                <div className="text-sm font-medium text-slate-900">设为当前柜位图版本</div>
                <div className="text-xs text-muted-foreground">同一楼层仅一个 active</div>
              </div>
              <div className="flex items-center gap-3">
                <div className={`text-xs font-medium ${editIsActive ? "text-emerald-700" : "text-slate-500"}`}>
                  {editIsActive ? "是" : "否"}
                </div>
                <Switch checked={editIsActive} onCheckedChange={setEditIsActive} />
              </div>
            </div>
            <div className="flex items-center justify-end gap-2 border-t pt-4">
              <Button variant="outline" onClick={() => setEditOpen(false)}>
                取消
              </Button>
              <Button onClick={handleEditSubmit} disabled={updateVersion.isPending}>
                {updateVersion.isPending ? "保存中..." : "保存"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
