import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { getApiUrl } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { useStore } from "@/contexts/StoreContext";
import { Plus, Pencil, Trash2 } from "lucide-react";

/** 楼层字典单条（与 public.floors 表一致） */
export interface FloorDict {
  id: number;
  store_id: string | null;
  building_code: string;
  floor_code: string;
  name: string;
  building_area: number | null;
  sort_no: number;
  created_at: string;
}

interface StoreOption {
  store_id: number;
  store_code?: string | null;
  store_name?: string | null;
}

/** 与列表 storeMap 一致：有名称用名称，否则用门店编码，避免多条「未命名门店」 */
function storeOptionLabel(s: StoreOption): string {
  const name = s.store_name?.trim();
  if (name) return name;
  const code = s.store_code?.trim();
  if (code) return code;
  return String(s.store_id);
}

const defaultForm = {
  store_id: "" as string | null,
  building_code: "DEFAULT",
  floor_code: "",
  name: "",
  building_area: "",
  sort_no: 0,
};

async function fetchJsonWithTimeout<T>(url: string, init?: RequestInit, timeoutMs = 20000): Promise<T> {
  const controller = new AbortController();
  const t = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { ...init, credentials: "include", signal: controller.signal });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `HTTP ${res.status}`);
    }
    return (await res.json()) as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error(`请求超时：${timeoutMs / 1000} 秒内未收到 /api/floors/ 响应，请检查后端服务和数据库连接`);
    }
    throw error;
  } finally {
    window.clearTimeout(t);
  }
}

export default function FloorsPage() {
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<typeof defaultForm>(defaultForm);
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { stores: globalStores } = useStore();
  const baseUrl = getApiUrl();

  const {
    data: floors = [],
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<FloorDict[]>({
    queryKey: ["/api/floors"],
    queryFn: async () => {
      const data = await fetchJsonWithTimeout<unknown>(`${baseUrl}/api/floors/`);
      return Array.isArray(data) ? (data as FloorDict[]) : [];
    },
  });

  const stores: StoreOption[] = globalStores.map((store) => ({
    store_id: store.storeId,
    store_code: store.storeCode ?? null,
    store_name: store.storeName ?? null,
  }));

  const storeMap = new Map(
    stores.map((s) => [String(s.store_code ?? s.store_id), storeOptionLabel(s)]),
  );

  const createMutation = useMutation({
    mutationFn: async (body: typeof defaultForm) => {
      return await fetchJsonWithTimeout(
        `${baseUrl}/api/floors/`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            store_id: body.store_id || null,
            building_code: body.building_code,
            floor_code: body.floor_code,
            name: body.name,
            building_area: body.building_area === "" ? null : Number(body.building_area),
            sort_no: Number(body.sort_no) || 0,
          }),
        },
        8000,
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/floors"] });
      setForm(defaultForm);
      setShowForm(false);
      toast({ title: "新增成功" });
    },
    onError: (e: Error) => {
      toast({ title: "新增失败", description: e.message, variant: "destructive" });
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, body }: { id: number; body: Partial<typeof defaultForm> }) => {
      return await fetchJsonWithTimeout(
        `${baseUrl}/api/floors/${id}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            store_id: body.store_id ?? undefined,
            building_code: body.building_code,
            floor_code: body.floor_code,
            name: body.name,
            building_area:
              body.building_area === undefined
                ? undefined
                : body.building_area === ""
                  ? null
                  : Number(body.building_area),
            sort_no: body.sort_no !== undefined ? Number(body.sort_no) : undefined,
          }),
        },
        8000,
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/floors"] });
      setForm(defaultForm);
      setEditingId(null);
      toast({ title: "更新成功" });
    },
    onError: (e: Error) => {
      toast({ title: "更新失败", description: e.message, variant: "destructive" });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await fetchJsonWithTimeout(
        `${baseUrl}/api/floors/${id}`,
        { method: "DELETE" },
        8000,
      );
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["/api/floors"] });
      await refetch();
      toast({ title: "删除成功" });
    },
    onError: (e: Error) => {
      toast({ title: "删除失败", description: e.message, variant: "destructive" });
    },
  });

  const handleSubmit = () => {
    if (!form.floor_code.trim() || !form.name.trim()) {
      toast({ title: "请填写楼层编码和名称", variant: "destructive" });
      return;
    }
    if (editingId !== null) {
      updateMutation.mutate({ id: editingId, body: form });
    } else {
      createMutation.mutate(form);
    }
  };

  const handleEdit = (row: FloorDict) => {
    setEditingId(row.id);
    setForm({
      store_id: row.store_id ?? "",
      building_code: row.building_code,
      floor_code: row.floor_code,
      name: row.name,
      building_area: row.building_area != null ? String(row.building_area) : "",
      sort_no: row.sort_no,
    });
    setShowForm(true);
  };

  const handleCancel = () => {
    setForm(defaultForm);
    setEditingId(null);
    setShowForm(false);
  };

  const storeDisplay = (storeId: string | null) => {
    const key = storeId?.trim();
    if (!key) return "—";
    return storeMap.get(key) || key;
  };

  const formatDate = (s: string) => {
    try {
      return new Date(s).toLocaleString("zh-CN", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return s;
    }
  };

  return (
    <div className="p-6 max-w-5xl" data-testid="floors-page">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-slate-900">楼层定义</h1>
        <Button
          onClick={() => {
            setEditingId(null);
            setForm(defaultForm);
            setShowForm(!showForm);
          }}
          className="bg-blue-600 hover:bg-blue-700"
        >
          <Plus className="w-4 h-4 mr-2" />
          新增楼层
        </Button>
      </div>

      {/* 新增/编辑表单 */}
      {showForm && (
        <div className="bg-white rounded-lg border border-slate-200 p-6 mb-6 shadow-sm">
          <h2 className="text-base font-semibold text-slate-900 mb-4">
            {editingId !== null ? "编辑楼层" : "新增楼层"}
          </h2>
          <div className="grid grid-cols-1 gap-5">
            <div className="grid grid-cols-[72px_1fr] gap-4 items-center">
              <Label className="text-slate-600">门店名称</Label>
              <Select
                value={form.store_id ?? ""}
                onValueChange={(v) => setForm((f) => ({ ...f, store_id: v || null }))}
              >
                <SelectTrigger className="w-[220px] h-9">
                  <SelectValue placeholder="请选择门店" />
                </SelectTrigger>
                <SelectContent className="z-50 bg-white border shadow-xl">
                  {stores.map((s) => {
                    const value = String(s.store_code ?? s.store_id);
                    return (
                      <SelectItem key={String(s.store_id)} value={value}>
                        {storeOptionLabel(s)}
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-wrap gap-6 items-center">
              <div className="grid grid-cols-[72px_1fr] gap-4 items-center">
                <Label className="text-slate-600">楼栋编码</Label>
                <Input
                  className="w-[220px] h-9"
                  value={form.building_code}
                  onChange={(e) => setForm((f) => ({ ...f, building_code: e.target.value }))}
                  placeholder="DEFAULT"
                />
              </div>
              <div className="grid grid-cols-[72px_1fr] gap-4 items-center">
                <Label className="text-slate-600">楼层编码</Label>
                <Input
                  className="w-[120px] h-9"
                  value={form.floor_code}
                  onChange={(e) => setForm((f) => ({ ...f, floor_code: e.target.value }))}
                  placeholder="B1 / 1F / 2F"
                />
              </div>
            </div>
            <div className="flex flex-wrap gap-6 items-center">
              <div className="grid grid-cols-[72px_1fr] gap-4 items-center">
                <Label className="text-slate-600">名称</Label>
                <Input
                  className="w-[220px] h-9"
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="地下一层"
                />
              </div>
              <div className="grid grid-cols-[72px_1fr] gap-4 items-center">
                <Label className="text-slate-600">排序</Label>
                <Input
                  type="number"
                  className="w-[100px] h-9"
                  value={form.sort_no}
                  onChange={(e) => setForm((f) => ({ ...f, sort_no: Number(e.target.value) || 0 }))}
                  placeholder="0"
                />
              </div>
              <div className="grid grid-cols-[84px_1fr] gap-4 items-center">
                <Label className="text-slate-600">建筑面积</Label>
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  className="w-[140px] h-9"
                  value={form.building_area}
                  onChange={(e) => setForm((f) => ({ ...f, building_area: e.target.value }))}
                  placeholder="㎡"
                />
              </div>
            </div>
          </div>
          <div className="mt-5 pt-5 border-t border-slate-200 flex justify-end gap-2">
            <Button variant="outline" onClick={handleCancel}>
              取消
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={createMutation.isPending || updateMutation.isPending}
              className="bg-blue-600 hover:bg-blue-700"
            >
              保存
            </Button>
          </div>
        </div>
      )}

      {/* 列表表格 */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
        {isError && (
          <div className="px-4 py-3 text-sm border-b bg-red-50 text-red-700 flex items-center justify-between">
            <div className="min-w-0">
              <div className="font-medium">加载失败</div>
              <div className="text-xs break-all">
                API：{baseUrl}/api/floors/ ｜ {error instanceof Error ? error.message : String(error)}
              </div>
            </div>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              重试
            </Button>
          </div>
        )}
        <Table>
          <TableHeader>
            <TableRow className="bg-slate-50">
              <TableHead className="w-[120px]">门店名称</TableHead>
              <TableHead className="w-[100px]">楼栋编码</TableHead>
              <TableHead className="w-[90px]">楼层编码</TableHead>
              <TableHead className="w-[120px]">名称</TableHead>
              <TableHead className="w-[110px]">建筑面积</TableHead>
              <TableHead className="w-[60px]">排序</TableHead>
              <TableHead className="w-[150px]">创建时间</TableHead>
              <TableHead className="w-[120px] text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-slate-500">
                  加载中...
                </TableCell>
              </TableRow>
            ) : floors.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-slate-500">
                  暂无楼层数据，请点击「新增楼层」添加
                </TableCell>
              </TableRow>
            ) : (
              floors.map((row) => (
                <TableRow key={row.id}>
                  <TableCell>{storeDisplay(row.store_id)}</TableCell>
                  <TableCell>{row.building_code}</TableCell>
                  <TableCell>{row.floor_code}</TableCell>
                  <TableCell>{row.name}</TableCell>
                  <TableCell>{row.building_area != null ? `${row.building_area}㎡` : "—"}</TableCell>
                  <TableCell>{row.sort_no}</TableCell>
                  <TableCell className="text-slate-500 text-sm">
                    {formatDate(row.created_at)}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-blue-600 hover:text-blue-700"
                      onClick={() => handleEdit(row)}
                    >
                      <Pencil className="w-4 h-4 mr-1" />
                      编辑
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-red-600 hover:text-red-700"
                      onClick={() => {
                        if (window.confirm("确定删除该楼层？")) deleteMutation.mutate(row.id);
                      }}
                    >
                      <Trash2 className="w-4 h-4 mr-1" />
                      删除
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
