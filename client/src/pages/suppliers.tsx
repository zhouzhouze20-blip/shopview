import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import {
  SupplierDetail,
  SupplierMutationInput,
  SupplierUpdateInput,
  useCreateSupplier,
  useDeleteSupplier,
  useSupplierDetail,
  useSuppliers,
  useUpdateSupplier,
} from "@/hooks/useSuppliers";
import { apiGet } from "@/lib/api";
import { Pencil, Plus, Trash2, Truck } from "lucide-react";

type SupplierFormState = {
  sbid: string;
  sbcname: string;
  sbsname: string;
  sbstatus: string;
  sbflag: string;
  sbregcode: string;
  sbcatcode: string;
  sbtaxpayer: string;
  sblxr: string;
  sblxfs: string;
  sbtel: string;
  sbemail: string;
  sbtaxno: string;
  sbbank: string;
  sbaccntno: string;
  sbaddr: string;
  sbfrdb: string;
  sbyjcgy: string;
  grade: string;
  sbnbtype: string;
  sbiftt: string;
  sbyt: string;
  sbxfdx: string;
  sbyxmf: string;
  sbyxrent: string;
  sbyxmon: string;
  sbyxmj: string;
  sbopendesc: string;
  sbppdesc: string;
  sbjfyq: string;
  sbmemo: string;
};

const defaultForm: SupplierFormState = {
  sbid: "",
  sbcname: "",
  sbsname: "",
  sbstatus: "Y",
  sbflag: "Y",
  sbregcode: "DEFAULT",
  sbcatcode: "DEFAULT",
  sbtaxpayer: "N",
  sblxr: "",
  sblxfs: "",
  sbtel: "",
  sbemail: "",
  sbtaxno: "",
  sbbank: "",
  sbaccntno: "",
  sbaddr: "",
  sbfrdb: "",
  sbyjcgy: "",
  grade: "",
  sbnbtype: "",
  sbiftt: "",
  sbyt: "",
  sbxfdx: "",
  sbyxmf: "",
  sbyxrent: "",
  sbyxmon: "",
  sbyxmj: "",
  sbopendesc: "",
  sbppdesc: "",
  sbjfyq: "",
  sbmemo: "",
};

function toForm(detail: SupplierDetail): SupplierFormState {
  return {
    sbid: detail.sbid ?? "",
    sbcname: detail.sbcname ?? "",
    sbsname: detail.sbsname ?? "",
    sbstatus: detail.sbstatus ?? "Y",
    sbflag: detail.sbflag ?? "Y",
    sbregcode: detail.sbregcode ?? "DEFAULT",
    sbcatcode: detail.sbcatcode ?? "DEFAULT",
    sbtaxpayer: detail.sbtaxpayer ?? "N",
    sblxr: detail.sblxr ?? "",
    sblxfs: detail.sblxfs ?? "",
    sbtel: detail.sbtel ?? "",
    sbemail: detail.sbemail ?? "",
    sbtaxno: detail.sbtaxno ?? "",
    sbbank: detail.sbbank ?? "",
    sbaccntno: detail.sbaccntno ?? "",
    sbaddr: detail.sbaddr ?? "",
    sbfrdb: detail.sbfrdb ?? "",
    sbyjcgy: detail.sbyjcgy ?? "",
    grade: detail.grade ?? "",
    sbnbtype: detail.sbnbtype ?? "",
    sbiftt: detail.sbiftt ?? "",
    sbyt: detail.sbyt ?? "",
    sbxfdx: detail.sbxfdx ?? "",
    sbyxmf: detail.sbyxmf ?? "",
    sbyxrent: detail.sbyxrent != null ? String(detail.sbyxrent) : "",
    sbyxmon: detail.sbyxmon != null ? String(detail.sbyxmon) : "",
    sbyxmj: detail.sbyxmj != null ? String(detail.sbyxmj) : "",
    sbopendesc: detail.sbopendesc ?? "",
    sbppdesc: detail.sbppdesc ?? "",
    sbjfyq: detail.sbjfyq ?? "",
    sbmemo: detail.sbmemo ?? "",
  };
}

function emptyToNull(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function numberOrNull(value: string) {
  const trimmed = value.trim();
  return trimmed ? Number(trimmed) : null;
}

function buildPayload(form: SupplierFormState): SupplierMutationInput {
  return {
    sbid: form.sbid.trim(),
    sbcname: form.sbcname.trim(),
    sbsname: emptyToNull(form.sbsname),
    sbstatus: form.sbstatus,
    sbflag: form.sbflag,
    sbregcode: form.sbregcode.trim() || "DEFAULT",
    sbcatcode: form.sbcatcode.trim() || "DEFAULT",
    sbtaxpayer: form.sbtaxpayer,
    sblxr: emptyToNull(form.sblxr),
    sblxfs: emptyToNull(form.sblxfs),
    sbtel: emptyToNull(form.sbtel),
    sbemail: emptyToNull(form.sbemail),
    sbtaxno: emptyToNull(form.sbtaxno),
    sbbank: emptyToNull(form.sbbank),
    sbaccntno: emptyToNull(form.sbaccntno),
    sbaddr: emptyToNull(form.sbaddr),
    sbfrdb: emptyToNull(form.sbfrdb),
    sbyjcgy: emptyToNull(form.sbyjcgy),
    grade: emptyToNull(form.grade),
    sbnbtype: emptyToNull(form.sbnbtype),
    sbiftt: emptyToNull(form.sbiftt),
    sbyt: emptyToNull(form.sbyt),
    sbxfdx: emptyToNull(form.sbxfdx),
    sbyxmf: emptyToNull(form.sbyxmf),
    sbyxrent: numberOrNull(form.sbyxrent),
    sbyxmon: numberOrNull(form.sbyxmon),
    sbyxmj: numberOrNull(form.sbyxmj),
    sbopendesc: emptyToNull(form.sbopendesc),
    sbppdesc: emptyToNull(form.sbppdesc),
    sbjfyq: emptyToNull(form.sbjfyq),
    sbmemo: emptyToNull(form.sbmemo),
    sbwmid1: "N",
    sbwmid2: "N",
    sbwmid3: "N",
    sbwmid4: "N",
    sbwmid5: "N",
    sbjszq: 0,
    sbdhzq: 0,
    sbdbsend: "N",
    sblry: "system",
  };
}

function statusBadge(status?: string | null) {
  if (status === "Y") {
    return <Badge className="bg-blue-100 text-blue-700 border-blue-200">正常</Badge>;
  }
  if (status === "N") {
    return <Badge className="bg-slate-100 text-slate-700 border-slate-200">停用</Badge>;
  }
  return <Badge variant="outline">{status || "未设置"}</Badge>;
}

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

function DetailItem({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div className="space-y-1 rounded-md border bg-slate-50 px-3 py-2">
      <div className="text-[11px] text-slate-500">{label}</div>
      <div className="break-words text-xs font-medium text-slate-900">{fmtValue(value)}</div>
    </div>
  );
}

export default function SuppliersPage() {
  const { toast } = useToast();
  const [storeId, setStoreId] = useState("ALL");
  const [supplierCode, setSupplierCode] = useState("");
  const [supplierName, setSupplierName] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [viewingId, setViewingId] = useState<string | null>(null);
  const [form, setForm] = useState<SupplierFormState>(defaultForm);

  const suppliersQuery = useSuppliers({ storeId, supplierCode, supplierName });
  const detailQuery = useSupplierDetail(editingId ?? viewingId ?? undefined);
  const storesQuery = useQuery({
    queryKey: ["/api/stores", { is_active: true }],
    queryFn: () => apiGet<StoreOption[]>("/api/stores?is_active=true"),
  });
  const createSupplier = useCreateSupplier();
  const updateSupplier = useUpdateSupplier();
  const deleteSupplier = useDeleteSupplier();

  useEffect(() => {
    if (editingId && detailQuery.data) {
      setForm(toForm(detailQuery.data));
    }
  }, [editingId, detailQuery.data]);

  const suppliers = useMemo(() => suppliersQuery.data ?? [], [suppliersQuery.data]);
  const stores = useMemo(() => storesQuery.data ?? [], [storesQuery.data]);

  const openCreate = () => {
    setEditingId(null);
    setForm(defaultForm);
    setDialogOpen(true);
  };

  const openEdit = (supplierId: string) => {
    setEditingId(supplierId);
    setDialogOpen(true);
  };

  const openDetail = (supplierId: string) => {
    setViewingId(supplierId);
  };

  const closeDetail = () => {
    setViewingId(null);
  };

  const closeDialog = () => {
    setDialogOpen(false);
    setEditingId(null);
    setForm(defaultForm);
  };

  const handleSubmit = async () => {
    if (!form.sbid.trim() && !editingId) {
      toast({ title: "请填写供应商编码", variant: "destructive" });
      return;
    }
    if (!form.sbcname.trim()) {
      toast({ title: "请填写供应商名称", variant: "destructive" });
      return;
    }

    try {
      if (editingId) {
        const payload: SupplierUpdateInput = { ...buildPayload(form), sbxgr: "system" };
        delete payload.sbid;
        await updateSupplier.mutateAsync({ supplierId: editingId, input: payload });
        toast({ title: "供应商更新成功" });
      } else {
        await createSupplier.mutateAsync(buildPayload(form));
        toast({ title: "供应商创建成功" });
      }
      closeDialog();
    } catch (error) {
      toast({
        title: editingId ? "供应商更新失败" : "供应商创建失败",
        description: error instanceof Error ? error.message : String(error),
        variant: "destructive",
      });
    }
  };

  const handleDelete = async (supplierId: string) => {
    if (!window.confirm(`确认删除供应商 ${supplierId} 吗？`)) return;
    try {
      await deleteSupplier.mutateAsync(supplierId);
      toast({ title: "供应商删除成功" });
    } catch (error) {
      toast({
        title: "供应商删除失败",
        description: error instanceof Error ? error.message : String(error),
        variant: "destructive",
      });
    }
  };

  return (
    <div className="p-4 space-y-4 text-sm" data-testid="suppliers-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">供应商管理</h1>
          <p className="mt-1 text-xs text-slate-500">基于 `supplierbase` 的供应商基础资料维护</p>
        </div>
        <Button onClick={openCreate} className="h-9 bg-blue-600 text-sm hover:bg-blue-700">
          <Plus className="w-4 h-4 mr-2" />
          新增供应商
        </Button>
      </div>

      <Card>
        <CardHeader className="px-5 py-4">
          <CardTitle className="text-lg">筛选条件</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 px-5 pb-5 md:grid-cols-4">
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
            <Label className="text-xs">供应商编码</Label>
            <Input
              className="h-9 text-sm"
              value={supplierCode}
              onChange={(event) => setSupplierCode(event.target.value)}
              placeholder="请输入供应商编码"
            />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">供应商名称</Label>
            <Input
              className="h-9 text-sm"
              value={supplierName}
              onChange={(event) => setSupplierName(event.target.value)}
              placeholder="请输入供应商名称"
            />
          </div>
          <div className="flex items-end">
            <div className="inline-flex h-9 items-center text-xs text-slate-500">当前共 {suppliers.length} 条记录</div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="px-5 py-4">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Truck className="w-4 h-4 text-blue-600" />
            供应商列表
          </CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto px-5 pb-5">
          <Table className="text-xs">
            <TableHeader>
              <TableRow>
                <TableHead className="whitespace-nowrap">供应商编码</TableHead>
                <TableHead className="whitespace-nowrap">供应商名称</TableHead>
                <TableHead className="whitespace-nowrap">地址</TableHead>
                <TableHead className="whitespace-nowrap">状态</TableHead>
                <TableHead className="whitespace-nowrap text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {suppliersQuery.isLoading ? (
                <TableRow>
                  <TableCell colSpan={5} className="py-8 text-center text-slate-500">
                    正在加载供应商数据...
                  </TableCell>
                </TableRow>
              ) : suppliersQuery.error ? (
                <TableRow>
                  <TableCell colSpan={5} className="py-8 text-center text-red-600">
                    {suppliersQuery.error instanceof Error ? suppliersQuery.error.message : "供应商加载失败"}
                  </TableCell>
                </TableRow>
              ) : suppliers.length ? (
                suppliers.map((supplier) => (
                  <TableRow key={supplier.sbid}>
                    <TableCell className="whitespace-nowrap font-medium">
                      <button className="text-blue-700 hover:underline" onClick={() => openDetail(supplier.sbid)}>
                        {supplier.sbid}
                      </button>
                    </TableCell>
                    <TableCell className="whitespace-nowrap">
                      <button className="text-blue-700 hover:underline" onClick={() => openDetail(supplier.sbid)}>
                        {supplier.sbcname}
                      </button>
                    </TableCell>
                    <TableCell className="max-w-[420px] truncate whitespace-nowrap" title={supplier.sbaddr ?? ""}>
                      {supplier.sbaddr || "—"}
                    </TableCell>
                    <TableCell className="whitespace-nowrap">{statusBadge(supplier.sbstatus)}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button variant="outline" size="sm" onClick={() => openEdit(supplier.sbid)}>
                          <Pencil className="w-4 h-4" />
                        </Button>
                        <Button variant="outline" size="sm" onClick={() => handleDelete(supplier.sbid)}>
                          <Trash2 className="w-4 h-4 text-red-600" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={5} className="py-8 text-center text-slate-500">
                    暂无供应商数据
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={Boolean(viewingId)} onOpenChange={(open) => (!open ? closeDetail() : undefined)}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle className="text-lg">供应商详情</DialogTitle>
          </DialogHeader>
          {detailQuery.isLoading ? (
            <div className="py-10 text-center text-sm text-slate-500">正在加载供应商详情...</div>
          ) : detailQuery.error ? (
            <div className="py-10 text-center text-sm text-red-600">
              {detailQuery.error instanceof Error ? detailQuery.error.message : "供应商详情加载失败"}
            </div>
          ) : detailQuery.data ? (
            <div className="space-y-4 text-sm">
              <div>
                <div className="text-base font-semibold text-slate-900">
                  {fmtValue(detailQuery.data.sbid)} · {fmtValue(detailQuery.data.sbcname)}
                </div>
                <div className="mt-1 text-xs text-slate-500">{fmtValue(detailQuery.data.sbaddr)}</div>
              </div>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                <DetailItem
                  label="状态"
                  value={
                    detailQuery.data.sbstatus === "Y"
                      ? "正常"
                      : detailQuery.data.sbstatus === "N"
                        ? "停用"
                        : detailQuery.data.sbstatus
                  }
                />
                <DetailItem label="分类" value={detailQuery.data.sbcatcode} />
                <DetailItem label="法定代表人" value={detailQuery.data.sbfrdb} />
                <DetailItem label="开户行" value={detailQuery.data.sbbank} />
                <DetailItem label="账号" value={detailQuery.data.sbaccntno} />
                <DetailItem label="税号" value={detailQuery.data.sbtaxno} />
                <DetailItem label="联系人" value={detailQuery.data.sblxr} />
                <DetailItem label="联系方式" value={detailQuery.data.sblxfs || detailQuery.data.sbtel} />
                <DetailItem label="邮箱" value={detailQuery.data.sbemail} />
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>

      <Dialog open={dialogOpen} onOpenChange={(open) => (!open ? closeDialog() : setDialogOpen(true))}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingId ? `编辑供应商 ${editingId}` : "新增供应商"}</DialogTitle>
          </DialogHeader>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>供应商编码</Label>
              <Input
                value={form.sbid}
                onChange={(event) => setForm((prev) => ({ ...prev, sbid: event.target.value }))}
                disabled={Boolean(editingId)}
                placeholder="SUP0001"
              />
            </div>
            <div className="space-y-2">
              <Label>供应商名称</Label>
              <Input
                value={form.sbcname}
                onChange={(event) => setForm((prev) => ({ ...prev, sbcname: event.target.value }))}
                placeholder="请输入供应商名称"
              />
            </div>
            <div className="space-y-2">
              <Label>简称</Label>
              <Input
                value={form.sbsname}
                onChange={(event) => setForm((prev) => ({ ...prev, sbsname: event.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label>供应商分类</Label>
              <Input
                value={form.sbcatcode}
                onChange={(event) => setForm((prev) => ({ ...prev, sbcatcode: event.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label>状态</Label>
              <Select value={form.sbstatus} onValueChange={(value) => setForm((prev) => ({ ...prev, sbstatus: value }))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Y">正常</SelectItem>
                  <SelectItem value="N">停用</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>可用标志</Label>
              <Select value={form.sbflag} onValueChange={(value) => setForm((prev) => ({ ...prev, sbflag: value }))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Y">可用</SelectItem>
                  <SelectItem value="N">不可用</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>地区编码</Label>
              <Input
                value={form.sbregcode}
                onChange={(event) => setForm((prev) => ({ ...prev, sbregcode: event.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label>纳税人类型</Label>
              <Select value={form.sbtaxpayer} onValueChange={(value) => setForm((prev) => ({ ...prev, sbtaxpayer: value }))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="N">普通</SelectItem>
                  <SelectItem value="Y">一般纳税人</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>联系人</Label>
              <Input
                value={form.sblxr}
                onChange={(event) => setForm((prev) => ({ ...prev, sblxr: event.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label>联系方式</Label>
              <Input
                value={form.sblxfs}
                onChange={(event) => setForm((prev) => ({ ...prev, sblxfs: event.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label>公司电话</Label>
              <Input
                value={form.sbtel}
                onChange={(event) => setForm((prev) => ({ ...prev, sbtel: event.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label>邮箱</Label>
              <Input
                value={form.sbemail}
                onChange={(event) => setForm((prev) => ({ ...prev, sbemail: event.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label>税号</Label>
              <Input
                value={form.sbtaxno}
                onChange={(event) => setForm((prev) => ({ ...prev, sbtaxno: event.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label>银行</Label>
              <Input
                value={form.sbbank}
                onChange={(event) => setForm((prev) => ({ ...prev, sbbank: event.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label>账号</Label>
              <Input
                value={form.sbaccntno}
                onChange={(event) => setForm((prev) => ({ ...prev, sbaccntno: event.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label>评级</Label>
              <Input
                value={form.grade}
                onChange={(event) => setForm((prev) => ({ ...prev, grade: event.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label>法定代表人</Label>
              <Input
                value={form.sbfrdb}
                onChange={(event) => setForm((prev) => ({ ...prev, sbfrdb: event.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label>引进柜员</Label>
              <Input
                value={form.sbyjcgy}
                onChange={(event) => setForm((prev) => ({ ...prev, sbyjcgy: event.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label>业态</Label>
              <Input
                value={form.sbyt}
                onChange={(event) => setForm((prev) => ({ ...prev, sbyt: event.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label>消费对象</Label>
              <Input
                value={form.sbxfdx}
                onChange={(event) => setForm((prev) => ({ ...prev, sbxfdx: event.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label>意向门房</Label>
              <Input
                value={form.sbyxmf}
                onChange={(event) => setForm((prev) => ({ ...prev, sbyxmf: event.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label>意向租金</Label>
              <Input
                value={form.sbyxrent}
                onChange={(event) => setForm((prev) => ({ ...prev, sbyxrent: event.target.value }))}
                inputMode="decimal"
              />
            </div>
            <div className="space-y-2">
              <Label>意向月保底</Label>
              <Input
                value={form.sbyxmon}
                onChange={(event) => setForm((prev) => ({ ...prev, sbyxmon: event.target.value }))}
                inputMode="decimal"
              />
            </div>
            <div className="space-y-2">
              <Label>意向面积</Label>
              <Input
                value={form.sbyxmj}
                onChange={(event) => setForm((prev) => ({ ...prev, sbyxmj: event.target.value }))}
                inputMode="decimal"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label>地址</Label>
            <Input
              value={form.sbaddr}
              onChange={(event) => setForm((prev) => ({ ...prev, sbaddr: event.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label>开店说明</Label>
            <Textarea
              value={form.sbopendesc}
              onChange={(event) => setForm((prev) => ({ ...prev, sbopendesc: event.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label>品牌说明</Label>
            <Textarea
              value={form.sbppdesc}
              onChange={(event) => setForm((prev) => ({ ...prev, sbppdesc: event.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label>经费要求</Label>
            <Textarea
              value={form.sbjfyq}
              onChange={(event) => setForm((prev) => ({ ...prev, sbjfyq: event.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label>备注</Label>
            <Textarea
              value={form.sbmemo}
              onChange={(event) => setForm((prev) => ({ ...prev, sbmemo: event.target.value }))}
            />
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={closeDialog}>
              取消
            </Button>
            <Button onClick={handleSubmit} disabled={createSupplier.isPending || updateSupplier.isPending || detailQuery.isLoading}>
              {editingId ? "保存修改" : "创建供应商"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
