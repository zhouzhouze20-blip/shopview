import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import { useBusinessUnits } from "@/hooks/useBusinessUnits";
import { useContractsList } from "@/hooks/useContracts";
import { formatOperationMethod } from "@/lib/operation-method";
import {
  ContractUnitBindingItem,
  ContractUnitBindingStatus,
  useContractUnitBindings,
  useCreateContractUnitBinding,
  useDisableContractUnitBinding,
  useUpdateContractUnitBinding,
} from "@/hooks/useContractUnitBindings";
import { Search, Link2, Pencil, Ban, RefreshCw } from "lucide-react";

const STATUS_OPTIONS: { value: ContractUnitBindingStatus; label: string }[] = [
  { value: "ACTIVE", label: "有效" },
  { value: "INACTIVE", label: "停用" },
  { value: "HISTORY", label: "历史" },
];

const statusLabel = (value?: string | null) =>
  STATUS_OPTIONS.find((option) => option.value === value)?.label ?? value ?? "-";

const fmtDate = (value?: string | null) => (value ? value.slice(0, 10) : "-");

function normalizeContractNo(value: string) {
  const trimmed = value.trim();
  if (/^\d{1,7}$/.test(trimmed)) return trimmed.padStart(8, "0");
  return trimmed;
}

export default function ContractUnitBindingsPage() {
  const { toast } = useToast();
  const [keyword, setKeyword] = useState("");
  const [statusFilter, setStatusFilter] = useState("ACTIVE");
  const [unitKeyword, setUnitKeyword] = useState("");
  const [contractKeyword, setContractKeyword] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [shopUnitId, setShopUnitId] = useState("");
  const [contractId, setContractId] = useState("");
  const [unitPickerOpen, setUnitPickerOpen] = useState(false);
  const [contractPickerOpen, setContractPickerOpen] = useState(false);

  const bindingsQuery = useContractUnitBindings({
    keyword: keyword.trim() || undefined,
    status: statusFilter,
    limit: 200,
  });
  const unitQuery = useBusinessUnits({ keyword: unitKeyword.trim() || undefined });
  const contractQuery = useContractsList({ keyword: contractKeyword.trim() || contractId.trim() || undefined, limit: 20 });
  const createMutation = useCreateContractUnitBinding();
  const updateMutation = useUpdateContractUnitBinding();
  const disableMutation = useDisableContractUnitBinding();

  const bindings = useMemo(() => bindingsQuery.data?.items ?? [], [bindingsQuery.data?.items]);
  const unitOptions = useMemo(() => unitQuery.data ?? [], [unitQuery.data]);
  const contractOptions = useMemo(() => contractQuery.data?.items ?? [], [contractQuery.data?.items]);
  const selectedUnit = useMemo(
    () => unitOptions.find((item) => String(item.id) === shopUnitId),
    [shopUnitId, unitOptions],
  );
  const selectedContract = useMemo(
    () => contractOptions.find((item) => item.cmcontno === normalizeContractNo(contractId)),
    [contractId, contractOptions],
  );
  const derivedBinding = useMemo(() => {
    return {
      businessType: formatOperationMethod(selectedContract?.cmwmid) || null,
      startDate: selectedContract?.cmeffdate ? selectedContract.cmeffdate.slice(0, 10) : null,
      endDate: selectedContract?.cmlapdate ? selectedContract.cmlapdate.slice(0, 10) : null,
      remark: selectedContract
        ? `前端手工补维护；合同=${selectedContract.cmcontno}；柜位=${selectedUnit?.unit_code || shopUnitId}`
        : "前端手工补维护",
    };
  }, [selectedContract, selectedUnit?.unit_code, shopUnitId]);

  const resetForm = () => {
    setEditingId(null);
    setShopUnitId("");
    setContractId("");
    setUnitKeyword("");
    setContractKeyword("");
    setUnitPickerOpen(false);
    setContractPickerOpen(false);
  };

  const loadForEdit = (item: ContractUnitBindingItem) => {
    setEditingId(item.id);
    setShopUnitId(item.shop_unit_id ? String(item.shop_unit_id) : "");
    setUnitKeyword(item.unit_code || "");
    setContractId(item.contract_id || "");
    setContractKeyword(item.contract_id || "");
    setUnitPickerOpen(false);
    setContractPickerOpen(false);
  };

  const submit = async () => {
    const normalizedContractId = normalizeContractNo(contractId);
    if (!shopUnitId) {
      toast({ title: "请选择柜位", variant: "destructive" });
      return;
    }
    if (!normalizedContractId) {
      toast({ title: "请输入合同号", variant: "destructive" });
      return;
    }
    const input = {
      shop_unit_id: Number(shopUnitId),
      contract_id: normalizedContractId,
      business_type: derivedBinding.businessType,
      start_date: derivedBinding.startDate,
      end_date: derivedBinding.endDate,
      is_primary: true,
      status: "ACTIVE" as const,
      remark: derivedBinding.remark,
    };
    try {
      if (editingId) {
        await updateMutation.mutateAsync({ id: editingId, input });
        toast({ title: "绑定已更新" });
      } else {
        await createMutation.mutateAsync(input);
        toast({ title: "绑定已创建" });
      }
      resetForm();
    } catch (error) {
      toast({
        title: editingId ? "更新失败" : "创建失败",
        description: error instanceof Error ? error.message : String(error),
        variant: "destructive",
      });
    }
  };

  const disableBinding = async (item: ContractUnitBindingItem) => {
    if (!window.confirm(`确定停用 ${item.unit_code || item.shop_unit_id} 与合同 ${item.contract_id} 的绑定吗？`)) return;
    try {
      await disableMutation.mutateAsync(item.id);
      toast({ title: "绑定已停用" });
      if (editingId === item.id) resetForm();
    } catch (error) {
      toast({
        title: "停用失败",
        description: error instanceof Error ? error.message : String(error),
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">合同柜位绑定</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            当 ERP 合同没有维护柜位/经营单元字段时，在这里补充合同号与 ShopView 柜位号的对应关系。
          </p>
        </div>
        <Button variant="outline" onClick={() => bindingsQuery.refetch()} disabled={bindingsQuery.isFetching}>
          <RefreshCw className="mr-2 h-4 w-4" />
          刷新
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Link2 className="h-5 w-5" />
            {editingId ? "编辑绑定" : "新增绑定"}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="space-y-2">
              <Label>柜位号</Label>
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  className="pl-9"
                  value={unitKeyword}
                  onChange={(e) => {
                    setUnitKeyword(e.target.value);
                    setShopUnitId("");
                    setUnitPickerOpen(true);
                  }}
                  onFocus={() => setUnitPickerOpen(true)}
                  placeholder="输入柜位号，如 B124"
                />
                {unitPickerOpen && unitKeyword.trim() ? (
                  <div className="absolute left-0 right-0 top-[46px] z-50 max-h-64 overflow-auto rounded-md border bg-white shadow-lg">
                    {unitOptions.length ? (
                      unitOptions.map((item) => (
                        <button
                          key={item.id}
                          type="button"
                          className="block w-full border-b px-3 py-2 text-left text-sm hover:bg-slate-50 last:border-b-0"
                          onClick={() => {
                            setShopUnitId(String(item.id));
                            setUnitKeyword(item.unit_code);
                            setUnitPickerOpen(false);
                          }}
                        >
                          <div className="font-medium">{item.unit_code}</div>
                          <div className="text-xs text-muted-foreground">ID {item.id} · {item.status}</div>
                        </button>
                      ))
                    ) : (
                      <div className="px-3 py-6 text-center text-sm text-muted-foreground">暂无柜位结果</div>
                    )}
                  </div>
                ) : null}
              </div>
              {selectedUnit ? (
                <p className="text-xs text-muted-foreground">
                  已选柜位：{selectedUnit.unit_code}，状态 {selectedUnit.status}
                </p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label>合同号</Label>
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  className="pl-9"
                  value={contractKeyword}
                  onChange={(e) => {
                    setContractKeyword(e.target.value);
                    setContractId("");
                    setContractPickerOpen(true);
                  }}
                  onFocus={() => setContractPickerOpen(true)}
                  placeholder="输入合同号/供应商/主题"
                />
                {contractPickerOpen && contractKeyword.trim() ? (
                  <div className="absolute left-0 right-0 top-[46px] z-50 max-h-64 overflow-auto rounded-md border bg-white shadow-lg">
                    {contractOptions.length ? (
                      contractOptions.map((item) => (
                        <button
                          key={item.cmcontno}
                          type="button"
                          className="block w-full border-b px-3 py-2 text-left text-sm hover:bg-slate-50 last:border-b-0"
                          onClick={() => {
                            setContractId(item.cmcontno);
                            setContractKeyword(item.cmcontno);
                            setContractPickerOpen(false);
                          }}
                        >
                          <div className="font-medium">{item.cmcontno}</div>
                          <div className="truncate text-xs text-muted-foreground">
                            {item.cmtitle || item.supplier_name || "-"} · {fmtDate(item.cmeffdate)} 至 {fmtDate(item.cmlapdate)}
                          </div>
                        </button>
                      ))
                    ) : (
                      <div className="px-3 py-6 text-center text-sm text-muted-foreground">暂无合同结果</div>
                    )}
                  </div>
                ) : null}
              </div>
              {selectedContract ? (
                <p className="text-xs text-muted-foreground">
                  {selectedContract.cmtitle || "-"} · {selectedContract.cmsupid || "-"} · {fmtDate(selectedContract.cmeffdate)} 至{" "}
                  {fmtDate(selectedContract.cmlapdate)}
                </p>
              ) : null}
            </div>
          </div>

          {selectedContract ? (
            <div className="grid grid-cols-1 gap-3 rounded-md border bg-slate-50 p-3 text-sm md:grid-cols-4">
              <div>
                <div className="text-xs text-muted-foreground">经营类型</div>
                <div className="font-medium">{derivedBinding.businessType || "-"}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">绑定开始</div>
                <div className="font-medium">{derivedBinding.startDate || "-"}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">绑定结束</div>
                <div className="font-medium">{derivedBinding.endDate || "-"}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">状态/关系</div>
                <div className="font-medium">有效 · 主关系</div>
              </div>
            </div>
          ) : null}

          <div className="flex gap-2">
            <Button onClick={submit} disabled={createMutation.isPending || updateMutation.isPending}>
              <Link2 className="mr-2 h-4 w-4" />
              {editingId ? "保存修改" : "保存绑定"}
            </Button>
            {editingId ? (
              <Button variant="outline" onClick={resetForm}>
                取消编辑
              </Button>
            ) : null}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>绑定列表</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-[1fr_180px]">
            <Input
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              placeholder="搜索合同号、柜位号、供应商、主题"
            />
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="z-50 bg-white">
                <SelectItem value="ALL">全部状态</SelectItem>
                {STATUS_OPTIONS.map((item) => (
                  <SelectItem key={item.value} value={item.value}>
                    {item.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>柜位号</TableHead>
                  <TableHead>合同号</TableHead>
                  <TableHead>合同主题</TableHead>
                  <TableHead>供应商/品牌</TableHead>
                  <TableHead>绑定日期</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>备注</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {bindingsQuery.isLoading ? (
                  <TableRow>
                    <TableCell colSpan={8} className="py-8 text-center text-muted-foreground">
                      加载中...
                    </TableCell>
                  </TableRow>
                ) : bindings.length ? (
                  bindings.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell>
                        <div className="font-medium">{item.unit_code || `ID ${item.shop_unit_id || "-"}`}</div>
                        <div className="text-xs text-muted-foreground">
                          {[item.building_code, item.floor_code].filter(Boolean).join("-") || item.floor_name || "-"}
                        </div>
                      </TableCell>
                      <TableCell className="font-medium">{item.contract_id}</TableCell>
                      <TableCell className="min-w-[180px]">{item.contract_title || "-"}</TableCell>
                      <TableCell>
                        <div>{item.supplier_name || item.supplier_code || "-"}</div>
                        <div className="text-xs text-muted-foreground">{item.brand_name || item.brand_id || "-"}</div>
                      </TableCell>
                      <TableCell>
                        {fmtDate(item.start_date)} 至 {fmtDate(item.end_date)}
                      </TableCell>
                      <TableCell>
                        <Badge variant={item.status === "ACTIVE" ? "default" : "secondary"}>{statusLabel(item.status)}</Badge>
                      </TableCell>
                      <TableCell className="max-w-[220px] truncate">{item.remark || "-"}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button size="sm" variant="outline" onClick={() => loadForEdit(item)}>
                            <Pencil className="mr-1 h-4 w-4" />
                            编辑
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={item.status !== "ACTIVE" || disableMutation.isPending}
                            onClick={() => disableBinding(item)}
                          >
                            <Ban className="mr-1 h-4 w-4" />
                            停用
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={8} className="py-8 text-center text-muted-foreground">
                      暂无绑定数据
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
