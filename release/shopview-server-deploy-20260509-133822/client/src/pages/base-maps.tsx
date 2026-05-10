import { useMemo, useState } from "react";
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
import { apiRequest, resolveApiAssetUrl } from "@/lib/api";
import { deriveSvgViewBox, extractSvgMetadataFromText } from "@/lib/svg-metadata";
import { Pencil, Trash2, Upload } from "lucide-react";
import {
  useActivateBaseMap,
  useBaseMapsList,
  useBaseMapFloorOptions,
  useCreateBaseMap,
  useDeleteBaseMap,
  useUpdateBaseMap,
} from "@/hooks/useBaseMaps";

async function uploadSvg(file: File): Promise<string> {
  const paramsRes = await apiRequest("/api/objects/upload", { method: "POST" });
  const params = (await paramsRes.json()) as { uploadURL: string };

  const formData = new FormData();
  formData.append("file", file);
  const uploadRes = await fetch(params.uploadURL, {
    method: "PUT",
    body: formData,
  });
  if (!uploadRes.ok) {
    const t = await uploadRes.text();
    throw new Error(`上传失败(${uploadRes.status}): ${t || "请重试"}`);
  }
  const result = (await uploadRes.json()) as { fileUrl?: string; error?: string; detail?: string };
  if (!result.fileUrl) {
    throw new Error(result.error || result.detail || "上传成功但未返回 fileUrl");
  }
  return result.fileUrl;
}

async function readSvgMetadata(file: File) {
  const text = await file.text();
  return extractSvgMetadataFromText(text);
}

export default function BaseMapsPage() {
  const { toast } = useToast();
  const { getCurrentFilter, stores } = useStore();
  const floorsQuery = useBaseMapFloorOptions();
  const createBaseMap = useCreateBaseMap();
  const activateBaseMap = useActivateBaseMap();
  const updateBaseMap = useUpdateBaseMap();
  const deleteBaseMap = useDeleteBaseMap();

  const [floorId, setFloorId] = useState<number | undefined>(undefined);
  const [baseMapCode, setBaseMapCode] = useState("");
  const [svgFile, setSvgFile] = useState<File | null>(null);
  const [svgViewbox, setSvgViewbox] = useState("");
  const [svgWidth, setSvgWidth] = useState("");
  const [svgHeight, setSvgHeight] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [editOpen, setEditOpen] = useState(false);
  const [editingMapId, setEditingMapId] = useState<number | null>(null);
  const [editBaseMapCode, setEditBaseMapCode] = useState("");
  const [editSvgViewbox, setEditSvgViewbox] = useState("");
  const [editSvgWidth, setEditSvgWidth] = useState("");
  const [editSvgHeight, setEditSvgHeight] = useState("");
  const [editIsActive, setEditIsActive] = useState(false);

  const baseMapsQuery = useBaseMapsList(floorId);

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
    if (!raw) return "—";
    const matched = stores.find(
      (store) => raw === String(store.storeId) || raw === String(store.storeCode ?? ""),
    );
    return matched ? matched.storeName : raw;
  };

  const visibleFloorOptions = useMemo(
    () => floorOptions.filter((item) => matchStoreRef(item.store_id)),
    [floorOptions, currentFilter.storeId, selectedStore?.storeCode],
  );

  const selectedFloorLabel = useMemo(() => {
    const f = floorOptions.find((x) => x.id === floorId);
    if (!f) return "";
    return `${storeDisplay(f.store_id)} / ${f.building_code}-${f.floor_code} ${f.name}`;
  }, [floorOptions, floorId, stores]);

  const visibleBaseMaps = useMemo(
    () => (baseMapsQuery.data ?? []).filter((item) => matchStoreRef(item.store_id)),
    [baseMapsQuery.data, currentFilter.storeId, selectedStore?.storeCode],
  );

  const openEditDialog = (id: number) => {
    const map = baseMapsQuery.data?.find((item) => item.id === id);
    if (!map) return;
    setEditingMapId(map.id);
    setEditBaseMapCode(map.base_map_code);
    setEditSvgViewbox(map.svg_viewbox ?? "");
    setEditSvgWidth(map.svg_width != null ? String(map.svg_width) : "");
    setEditSvgHeight(map.svg_height != null ? String(map.svg_height) : "");
    setEditIsActive(map.is_active);
    setEditOpen(true);
  };

  const handleEditSubmit = async () => {
    if (!editingMapId) return;
    if (!editBaseMapCode.trim()) {
      toast({ title: "请填写底图编码", variant: "destructive" });
      return;
    }
    try {
      await updateBaseMap.mutateAsync({
        id: editingMapId,
        input: {
          base_map_code: editBaseMapCode.trim(),
          svg_viewbox: editSvgViewbox.trim() || null,
          svg_width: editSvgWidth.trim() ? Number(editSvgWidth) : null,
          svg_height: editSvgHeight.trim() ? Number(editSvgHeight) : null,
          is_active: editIsActive,
        },
      });
      toast({ title: "底图更新成功" });
      setEditOpen(false);
    } catch (e) {
      toast({
        title: "底图更新失败",
        description: e instanceof Error ? e.message : String(e),
        variant: "destructive",
      });
    }
  };

  const handleSubmit = async () => {
    if (!floorId) {
      toast({ title: "请先选择楼层", variant: "destructive" });
      return;
    }
    const floorExists = floorOptions.some((f) => f.id === floorId);
    if (!floorExists) {
      toast({
        title: "楼层不存在或未同步",
        description: `floor_id=${floorId} 不在当前楼层列表，请先创建楼层或刷新后重试`,
        variant: "destructive",
      });
      return;
    }
    if (!baseMapCode.trim()) {
      toast({ title: "请填写底图编码", description: "例如 BASE_1F_2026_V1", variant: "destructive" });
      return;
    }
    if (!svgFile) {
      toast({ title: "请选择 SVG 文件", variant: "destructive" });
      return;
    }
    if (svgFile.type && svgFile.type !== "image/svg+xml") {
      // 某些环境可能为空，这里仅做提示
      toast({ title: "文件类型提示", description: `当前类型: ${svgFile.type || "unknown"}` });
    }

    try {
      const fileUrl = await uploadSvg(svgFile);
      const created = await createBaseMap.mutateAsync({
        floor_id: floorId,
        base_map_code: baseMapCode.trim(),
        file_url: fileUrl,
        svg_viewbox: svgViewbox.trim() || undefined,
        svg_width: svgWidth ? Number(svgWidth) : undefined,
        svg_height: svgHeight ? Number(svgHeight) : undefined,
        is_active: isActive,
      });

      toast({
        title: "底图创建成功",
        description: created.file_url,
      });
      setSvgFile(null);
      // 保留 floorId，方便继续上传下一版
    } catch (e) {
      toast({
        title: "上传/创建失败",
        description: e instanceof Error ? e.message : String(e),
        variant: "destructive",
      });
    }
  };

  const handleSvgFileChange = async (file: File | null) => {
    setSvgFile(file);
    if (!file) return;

    try {
      const metadata = await readSvgMetadata(file);
      const derivedViewBox = deriveSvgViewBox(metadata);
      if (!svgViewbox.trim() && derivedViewBox) {
        setSvgViewbox(derivedViewBox);
      }
      if (!svgWidth.trim() && metadata.width != null) {
        setSvgWidth(String(metadata.width));
      }
      if (!svgHeight.trim() && metadata.height != null) {
        setSvgHeight(String(metadata.height));
      }
    } catch {
      // Ignore parsing failures and allow manual input.
    }
  };

  const floorOptionLabel = (floor: (typeof floorOptions)[number]) =>
    `${storeDisplay(floor.store_id)} / ${floor.building_code}-${floor.floor_code} ${floor.name}`;

  return (
    <div className="container mx-auto p-6 space-y-6" data-testid="base-maps-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">静态底图（SVG）</h1>
          <p className="text-sm text-muted-foreground mt-1">上传楼层底图并登记到 `base_maps`</p>
        </div>
      </div>

      <GlobalStoreSelector compact className="mb-2" />

      <Card>
        <CardHeader>
          <CardTitle>上传新底图</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>楼层</Label>
              <Select
                value={floorId ? String(floorId) : ""}
                onValueChange={(v) => setFloorId(Number(v))}
                disabled={floorsQuery.isLoading || !!floorsQuery.error}
              >
                <SelectTrigger>
                  <SelectValue placeholder={floorsQuery.isLoading ? "加载中..." : "选择楼层"} />
                </SelectTrigger>
                <SelectContent className="z-50 bg-white/95 backdrop-blur border shadow-xl">
                  {visibleFloorOptions.length ? (
                    visibleFloorOptions.map((f) => (
                      <SelectItem key={f.id} value={String(f.id)}>
                        {floorOptionLabel(f)}
                      </SelectItem>
                    ))
                  ) : (
                    <div className="px-3 py-2 text-sm text-muted-foreground">
                      {floorsQuery.isLoading
                        ? "加载中..."
                        : floorsQuery.error
                          ? "楼层加载失败（请确认后端 8000 已启动）"
                          : currentFilter.storeId
                            ? "当前门店下暂无楼层数据"
                            : "暂无楼层数据（请先在「系统管理-楼层定义」创建楼层）"}
                    </div>
                  )}
                </SelectContent>
              </Select>
              <div className="text-xs text-muted-foreground flex items-center gap-2">
                <span>已加载楼层：{visibleFloorOptions.length}</span>
                {floorsQuery.error && (
                  <Button
                    type="button"
                    variant="link"
                    className="h-auto p-0 text-xs"
                    onClick={() => floorsQuery.refetch()}
                  >
                    重试
                  </Button>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="baseMapCode">底图编码</Label>
              <Input
                id="baseMapCode"
                value={baseMapCode}
                onChange={(e) => setBaseMapCode(e.target.value)}
                placeholder="BASE_1F_2026_V1"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="svgViewbox">viewBox（可选）</Label>
              <Input
                id="svgViewbox"
                value={svgViewbox}
                onChange={(e) => setSvgViewbox(e.target.value)}
                placeholder='0 0 5000 3000'
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="svgWidth">宽度（可选）</Label>
              <Input
                id="svgWidth"
                value={svgWidth}
                onChange={(e) => setSvgWidth(e.target.value)}
                placeholder="5000"
                inputMode="decimal"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="svgHeight">高度（可选）</Label>
              <Input
                id="svgHeight"
                value={svgHeight}
                onChange={(e) => setSvgHeight(e.target.value)}
                placeholder="3000"
                inputMode="decimal"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="svgFile">SVG 文件</Label>
            <Input
              id="svgFile"
              type="file"
              accept=".svg,image/svg+xml"
              onChange={(e) => {
                void handleSvgFileChange(e.target.files?.[0] ?? null);
              }}
            />
            {svgFile && (
              <div className="text-xs text-muted-foreground">
                已选择：{svgFile.name}（{Math.round(svgFile.size / 1024)} KB）
              </div>
            )}
          </div>

          <div className="rounded-lg border bg-slate-50 px-4 py-3 flex items-center justify-between">
            <div className="space-y-1">
              <div className="text-sm font-medium text-slate-900">设为该楼层当前底图</div>
              <div className="text-xs text-muted-foreground">同楼层仅一个 active</div>
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
              onClick={handleSubmit}
              disabled={createBaseMap.isPending}
              className="w-full h-11 text-base"
            >
              {createBaseMap.isPending ? (
                "上传中..."
              ) : (
                <>
                  <Upload className="w-4 h-4 mr-2" />
                  上传并创建记录
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>已上传底图</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {baseMapsQuery.isLoading ? (
            <div className="text-sm text-muted-foreground">加载中...</div>
          ) : visibleBaseMaps.length ? (
            <div className="space-y-2">
              {visibleBaseMaps.map((m) => (
                <div key={m.id} className="flex items-center justify-between rounded border p-3">
                  <div className="min-w-0">
                    <div className="font-medium truncate">
                      {m.base_map_code} {m.is_active ? "(active)" : ""}
                    </div>
                    <div className="text-xs text-muted-foreground truncate">
                      门店：{storeDisplay(m.store_id)} · 楼层：{m.building_code || "-"}-{m.floor_code || "-"} {m.floor_name || ""}
                    </div>
                    <div className="text-xs text-muted-foreground truncate">{m.file_url}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      onClick={() => window.open(resolveApiAssetUrl(m.file_url), "_blank", "noopener,noreferrer")}
                    >
                      预览
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => openEditDialog(m.id)}
                    >
                      <Pencil className="w-4 h-4 mr-2" />
                      编辑
                    </Button>
                    <Button
                      variant="outline"
                      className="text-red-600 hover:text-red-700"
                      disabled={deleteBaseMap.isPending}
                      onClick={async () => {
                        if (!window.confirm(`确定删除底图 ${m.base_map_code} 吗？`)) return;
                        try {
                          await deleteBaseMap.mutateAsync(m.id);
                          toast({ title: "底图已删除" });
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
                    {!m.is_active && (
                      <Button
                        onClick={async () => {
                          try {
                            await activateBaseMap.mutateAsync(m.id);
                            toast({ title: "已设为 active" });
                            baseMapsQuery.refetch();
                          } catch (e) {
                            toast({
                              title: "设置失败",
                              description: e instanceof Error ? e.message : String(e),
                              variant: "destructive",
                            });
                          }
                        }}
                        disabled={activateBaseMap.isPending}
                      >
                        设为 active
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-sm text-muted-foreground">暂无数据</div>
          )}
        </CardContent>
      </Card>

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>编辑底图</DialogTitle>
          </DialogHeader>
          <div className="space-y-5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="editBaseMapCode">底图编码</Label>
                <Input
                  id="editBaseMapCode"
                  value={editBaseMapCode}
                  onChange={(e) => setEditBaseMapCode(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="editSvgViewbox">viewBox（可选）</Label>
                <Input
                  id="editSvgViewbox"
                  value={editSvgViewbox}
                  onChange={(e) => setEditSvgViewbox(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="editSvgWidth">宽度（可选）</Label>
                <Input
                  id="editSvgWidth"
                  value={editSvgWidth}
                  onChange={(e) => setEditSvgWidth(e.target.value)}
                  inputMode="decimal"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="editSvgHeight">高度（可选）</Label>
                <Input
                  id="editSvgHeight"
                  value={editSvgHeight}
                  onChange={(e) => setEditSvgHeight(e.target.value)}
                  inputMode="decimal"
                />
              </div>
            </div>

            <div className="rounded-lg border bg-slate-50 px-4 py-3 flex items-center justify-between">
              <div className="space-y-1">
                <div className="text-sm font-medium text-slate-900">设为该楼层当前底图</div>
                <div className="text-xs text-muted-foreground">同楼层仅一个 active</div>
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
              <Button onClick={handleEditSubmit} disabled={updateBaseMap.isPending}>
                {updateBaseMap.isPending ? "保存中..." : "保存"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
