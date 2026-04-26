import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useManaframe } from "@/hooks/useManaframe";
import { formatOperationMethod } from "@/lib/operation-method";
import { Building2 } from "lucide-react";

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

export default function ManaframePage() {
  const [keyword, setKeyword] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const query = useManaframe(keyword, statusFilter);
  const rows = useMemo(() => query.data ?? [], [query.data]);

  return (
    <div className="container mx-auto p-6 space-y-6" data-testid="manaframe-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">柜位定义</h1>
          <p className="text-sm text-muted-foreground mt-1">基于 `MANAFRAME` 的 ERP 柜组主数据</p>
        </div>
        <div className="inline-flex items-center gap-2 rounded-md border bg-slate-50 px-3 py-2 text-sm text-slate-600">
          <Building2 className="h-4 w-4" />
          当前 {rows.length} 条
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>筛选条件</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2 md:col-span-2">
            <Label>关键字</Label>
            <Input
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              placeholder="柜组编码 / 柜组名称"
            />
          </div>
          <div className="space-y-2">
            <Label>状态</Label>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="z-50 bg-white border shadow-xl">
                <SelectItem value="ALL">全部状态</SelectItem>
                <SelectItem value="Y">正常</SelectItem>
                <SelectItem value="N">停用</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>柜位定义列表</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>柜组编码</TableHead>
                <TableHead>柜组名称</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>经营方式</TableHead>
                <TableHead>经营位置</TableHead>
                <TableHead>经营区域</TableHead>
                <TableHead>级次</TableHead>
                <TableHead>上级编码</TableHead>
                <TableHead>末级</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {query.isLoading ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                    加载中...
                  </TableCell>
                </TableRow>
              ) : query.error ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center py-8 text-red-600">
                    {query.error instanceof Error ? query.error.message : "加载失败"}
                  </TableCell>
                </TableRow>
              ) : rows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                    暂无柜位定义数据
                  </TableCell>
                </TableRow>
              ) : (
                rows.map((row) => (
                  <TableRow key={row.mfcode}>
                    <TableCell className="font-medium">{fmtValue(row.mfcode)}</TableCell>
                    <TableCell>{fmtValue(row.mfcname)}</TableCell>
                    <TableCell>{statusBadge(row.mfstatus)}</TableCell>
                    <TableCell>{formatOperationMethod(row.mfjyfs)}</TableCell>
                    <TableCell>{fmtValue(row.mfjywz)}</TableCell>
                    <TableCell>{fmtValue(row.mfjyqy)}</TableCell>
                    <TableCell>{fmtValue(row.mfclass)}</TableCell>
                    <TableCell>{fmtValue(row.mfpcode)}</TableCell>
                    <TableCell>{row.mfflag === "Y" ? "是" : row.mfflag === "N" ? "否" : fmtValue(row.mfflag)}</TableCell>
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
