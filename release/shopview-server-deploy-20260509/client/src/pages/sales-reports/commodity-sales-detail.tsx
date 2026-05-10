import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

/**
 * 销售管理 - 报表 - 商品销售明细（ERP 633）
 * 数据落库表：rpt_goods_sales_detail（由 Alembic 创建）。此处为列表壳子，后续接同步/查询 API。
 */
export default function CommoditySalesDetailReportPage() {
  const columns = [
    "楼层",
    "库区",
    "柜组",
    "供应商",
    "商品编码",
    "商品条码",
    "商品名称",
    "原扣率",
    "销售扣率",
    "优惠扣率",
    "让扣金额",
    "销售数量",
    "售价金额",
    "销售收入",
    "毛利",
    "毛利率",
    "销售净额",
    "净毛利",
    "净毛利率",
    "销售成本",
    "净销售成本",
    "总折扣",
    "会员折扣",
    "促销折扣",
    "授权折扣",
    "其他折扣",
  ] as const;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">商品销售明细</h1>
        <p className="text-sm text-muted-foreground mt-1">
          对应 ERP「销售管理 · 报表分析 · 633 · 商品销售明细报表」。筛选条件与汇总口径见{" "}
          <code className="text-xs bg-slate-100 px-1 rounded">建表/数据报表/商品销售明细报表条件窗口.txt</code>
        </p>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">筛选</CardTitle>
          <CardDescription>发生日期、记账日期、部门、库区、供应商、商品编码、经营方式等（待对接接口）</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="space-y-2">
            <Label htmlFor="csd-start">发生日期起</Label>
            <Input id="csd-start" type="date" disabled />
          </div>
          <div className="space-y-2">
            <Label htmlFor="csd-end">发生日期止</Label>
            <Input id="csd-end" type="date" disabled />
          </div>
          <div className="space-y-2">
            <Label htmlFor="csd-dept">部门</Label>
            <Input id="csd-dept" placeholder="预留" disabled />
          </div>
          <div className="space-y-2">
            <Label htmlFor="csd-area">库区</Label>
            <Input id="csd-area" placeholder="预留" disabled />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">明细</CardTitle>
          <CardDescription>列与 ERP 报表一致；数据写入表 rpt_goods_sales_detail 后可在此展示</CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                {columns.map((c) => (
                  <TableHead key={c} className="whitespace-nowrap text-xs">
                    {c}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow>
                <TableCell colSpan={columns.length} className="text-center text-muted-foreground py-10">
                  暂无数据（待接入查询）
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
