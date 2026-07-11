import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useManaframe } from "@/hooks/useManaframe";
import { useToast } from "@/hooks/use-toast";
import { apiGet, apiPut } from "@/lib/api";
import { formatOperationMethod } from "@/lib/operation-method";
import { Building2 } from "lucide-react";

function fmtValue(value?: string | number | null) {
  if (value == null || value === "") return "—";
  return String(value);
}

interface StoreOption {
  storeId?: number;
  store_id?: number;
  storeCode?: string;
  store_code?: string;
  storeName?: string;
  store_name?: string;
}

export default function ManaframePage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [storeId, setStoreId] = useState("ALL");
  const [groupCode, setGroupCode] = useState("");
  const [groupName, setGroupName] = useState("");
  const query = useManaframe({ storeId, groupCode, groupName });
  const storesQuery = useQuery({
    queryKey: ["/api/stores", { is_active: true }],
    queryFn: () => apiGet<StoreOption[]>("/api/stores?is_active=true"),
  });
  const rows = useMemo(() => query.data ?? [], [query.data]);
  const stores = useMemo(() => storesQuery.data ?? [], [storesQuery.data]);
  const keyBrandMutation = useMutation({
    mutationFn: ({ mfcode, isKeyBrand }: { mfcode: string; isKeyBrand: boolean }) =>
      apiPut(`/api/manaframe/${encodeURIComponent(mfcode)}/key-brand`, { is_key_brand: isKeyBrand }),
    onSuccess: async (_data, variables) => {
      await queryClient.invalidateQueries({ queryKey: ["manaframe"] });
      toast({
        title: "重点品牌标记已更新",
        description: `${variables.mfcode} 已标记为${variables.isKeyBrand ? "重点品牌" : "非重点品牌"}`,
      });
    },
    onError: (error) => {
      toast({
        title: "保存失败",
        description: error instanceof Error ? error.message : "更新重点品牌标记时出错",
        variant: "destructive",
      });
    },
  });

  return (
    <div className="mx-auto w-full max-w-7xl p-4 space-y-4 text-sm" data-testid="manaframe-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-normal">柜位定义</h1>
          <p className="mt-1 text-xs text-muted-foreground">基于 `MANAFRAME` 的 ERP 柜组主数据</p>
        </div>
        <div className="inline-flex items-center gap-2 rounded-md border bg-slate-50 px-3 py-1.5 text-xs text-slate-600">
          <Building2 className="h-4 w-4" />
          当前 {rows.length} 条
        </div>
      </div>

      <Card>
        <CardHeader className="px-5 py-4">
          <CardTitle className="text-lg">筛选条件</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 px-5 pb-5 md:grid-cols-3">
          <div className="space-y-1.5">
            <Label className="text-xs">门店</Label>
            <Select value={storeId} onValueChange={setStoreId}>
              <SelectTrigger className="h-9 text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="z-50 bg-white border shadow-xl">
                <SelectItem value="ALL">全部门店</SelectItem>
                {stores.map((store) => {
                  const id = store.storeId ?? store.store_id;
                  const code = store.storeCode ?? store.store_code ?? id;
                  const name = store.storeName ?? store.store_name ?? `门店 ${id}`;
                  if (id == null) return null;
                  const value = code != null ? String(code) : String(id);
                  return (
                    <SelectItem key={id} value={value}>
                      {code ? `${code} · ${name}` : name}
                    </SelectItem>
                  );
                })}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">柜组编码</Label>
            <Input
              className="h-9 text-sm"
              value={groupCode}
              onChange={(e) => setGroupCode(e.target.value)}
              placeholder="输入编码"
            />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">柜组名称</Label>
            <Input
              className="h-9 text-sm"
              value={groupName}
              onChange={(e) => setGroupName(e.target.value)}
              placeholder="输入名称关键字"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="px-5 py-4">
          <CardTitle className="text-lg">柜位定义列表</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto px-5 pb-5">
          <Table className="text-[11px]">
            <TableHeader>
              <TableRow>
                <TableHead className="whitespace-nowrap">柜组编码</TableHead>
                <TableHead className="whitespace-nowrap">重点品牌</TableHead>
                <TableHead className="whitespace-nowrap">柜组名称</TableHead>
                <TableHead className="whitespace-nowrap">经营方式</TableHead>
                <TableHead className="whitespace-nowrap">柜位号</TableHead>
                <TableHead className="whitespace-nowrap">中岛/边厅</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {query.isLoading ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                    加载中...
                  </TableCell>
                </TableRow>
              ) : query.error ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-red-600">
                    {query.error instanceof Error ? query.error.message : "加载失败"}
                  </TableCell>
                </TableRow>
              ) : rows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                    暂无柜位定义数据
                  </TableCell>
                </TableRow>
              ) : (
                rows.map((row) => (
                  <TableRow key={row.mfcode}>
                    <TableCell className="whitespace-nowrap font-medium">{fmtValue(row.mfcode)}</TableCell>
                    <TableCell className="whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <Switch
                          aria-label={`${row.mfcode} 重点品牌标记`}
                          checked={Boolean(row.is_key_brand)}
                          disabled={keyBrandMutation.isPending}
                          onCheckedChange={(checked) => keyBrandMutation.mutate({ mfcode: row.mfcode, isKeyBrand: checked })}
                        />
                        <span className="text-xs text-muted-foreground">{row.is_key_brand ? "是" : "否"}</span>
                      </div>
                    </TableCell>
                    <TableCell className="whitespace-nowrap">{fmtValue(row.mfcname)}</TableCell>
                    <TableCell className="whitespace-nowrap">{formatOperationMethod(row.mfjyfs)}</TableCell>
                    <TableCell className="whitespace-nowrap">{fmtValue(row.mfjywz)}</TableCell>
                    <TableCell className="whitespace-nowrap">{fmtValue(row.mfjyqy)}</TableCell>
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
