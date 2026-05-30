import { useEffect, useMemo, useState } from "react";
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

export default function SuppliersPage() {
  const { toast } = useToast();
  const [supplierCode, setSupplierCode] = useState("");
  const [supplierName, setSupplierName] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<SupplierFormState>(defaultForm);

  const suppliersQuery = useSuppliers(supplierCode, supplierName, statusFilter === "ALL" ? "" : statusFilter);
  const detailQuery = useSupplierDetail(editingId ?? undefined);
  const createSupplier = useCreateSupplier();
  const updateSupplier = useUpdateSupplier();
  const deleteSupplier = useDeleteSupplier();

  useEffect(() => {
    if (editingId && detailQuery.data) {
      setForm(toForm(detailQuery.data));
    }
  }, [editingId, detailQuery.data]);

  const suppliers = useMemo(() => suppliersQuery.data ?? [], [suppliersQuery.data]);

  const openCreate = () => {
    setEditingId(null);
    setForm(defaultForm);
    setDialogOpen(true);
  };

  const openEdit = (supplierId: string) => {
    setEditingId(supplierId);
    setDialogOpen(true);
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
    <div className="p-6 space-y-6" data-testid="suppliers-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">供应商管理</h1>
          <p className="text-sm text-slate-500 mt-1">基于 `supplierbase` 的供应商基础资料维护</p>
        </div>
        <Button onClick={openCreate} className="bg-blue-600 hover:bg-blue-700">
          <Plus className="w-4 h-4 mr-2" />
          新增供应商
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>筛选条件</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="space-y-2">
            <Label>供应商编码</Label>
            <Input
              value={supplierCode}
              onChange={(event) => setSupplierCode(event.target.value)}
              placeholder="请输入供应商编码"
            />
          </div>
          <div className="space-y-2">
            <Label>供应商名称</Label>
            <Input
              value={supplierName}
              onChange={(event) => setSupplierName(event.target.value)}
              placeholder="请输入供应商名称"
            />
          </div>
          <div className="space-y-2">
            <Label>状态</Label>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger>
                <SelectValue placeholder="全部状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">全部</SelectItem>
                <SelectItem value="Y">正常</SelectItem>
                <SelectItem value="N">停用</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-end">
            <div className="text-sm text-slate-500">当前共 {suppliers.length} 条记录</div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Truck className="w-5 h-5 text-blue-600" />
            供应商列表
          </CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>编码</TableHead>
                <TableHead>名称</TableHead>
                <TableHead>地址</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>分类</TableHead>
                <TableHead>法定代表人</TableHead>
                <TableHead>开户行</TableHead>
                <TableHead>账号</TableHead>
                <TableHead>税号</TableHead>
                <TableHead>更新时间</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {suppliersQuery.isLoading ? (
                <TableRow>
                  <TableCell colSpan={11} className="py-8 text-center text-slate-500">
                    正在加载供应商数据...
                  </TableCell>
                </TableRow>
              ) : suppliersQuery.error ? (
                <TableRow>
                  <TableCell colSpan={11} className="py-8 text-center text-red-600">
                    {suppliersQuery.error instanceof Error ? suppliersQuery.error.message : "供应商加载失败"}
                  </TableCell>
                </TableRow>
              ) : suppliers.length ? (
                suppliers.map((supplier) => (
                  <TableRow key={supplier.sbid}>
                    <TableCell className="font-medium">{supplier.sbid}</TableCell>
                    <TableCell>{supplier.sbcname}</TableCell>
                    <TableCell className="max-w-[260px] truncate" title={supplier.sbaddr ?? ""}>
                      {supplier.sbaddr || "—"}
                    </TableCell>
                    <TableCell>{statusBadge(supplier.sbstatus)}</TableCell>
                    <TableCell>{supplier.sbcatcode || "—"}</TableCell>
                    <TableCell>{supplier.sbfrdb || "—"}</TableCell>
                    <TableCell>{supplier.sbbank || "—"}</TableCell>
                    <TableCell>{supplier.sbaccntno || "—"}</TableCell>
                    <TableCell>{supplier.sbtaxno || "—"}</TableCell>
                    <TableCell>{supplier.sbxgrq ? new Date(supplier.sbxgrq).toLocaleString("zh-CN") : "—"}</TableCell>
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
                  <TableCell colSpan={11} className="py-8 text-center text-slate-500">
                    暂无供应商数据
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

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
