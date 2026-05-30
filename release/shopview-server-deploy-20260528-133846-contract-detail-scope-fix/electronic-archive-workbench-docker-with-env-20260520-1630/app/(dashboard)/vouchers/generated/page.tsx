"use client"

import { useState } from "react"
import { ArrowLeft, Search, Send, Eye, CheckCircle2 } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import Link from "next/link"

const generatedVouchers = [
  {
    id: "1",
    voucherNo: "PZ-2024-11-0001",
    businessDate: "2024-11-15",
    summary: "支付货款-深圳市科技有限公司",
    debitAccount: "应付账款",
    creditAccount: "银行存款",
    amount: 96050.0,
    ncVoucherNo: "NC-2024-0892",
    pushStatus: "success",
  },
  {
    id: "2",
    voucherNo: "PZ-2024-11-0002",
    businessDate: "2024-11-14",
    summary: "采购预付款-上海贸易集团",
    debitAccount: "预付账款",
    creditAccount: "银行存款",
    amount: 135600.0,
    ncVoucherNo: "",
    pushStatus: "pending",
  },
  {
    id: "3",
    voucherNo: "PZ-2024-11-0003",
    businessDate: "2024-11-13",
    summary: "销售收款-广州客户有限公司",
    debitAccount: "银行存款",
    creditAccount: "应收账款",
    amount: 258000.0,
    ncVoucherNo: "NC-2024-0891",
    pushStatus: "success",
  },
  {
    id: "4",
    voucherNo: "PZ-2024-11-0004",
    businessDate: "2024-11-12",
    summary: "支付运费-杭州物流有限公司",
    debitAccount: "销售费用",
    creditAccount: "银行存款",
    amount: 36160.0,
    ncVoucherNo: "",
    pushStatus: "pending",
  },
]

const pushStatusMap: Record<
  string,
  { label: string; variant: "default" | "secondary" | "destructive" | "outline" }
> = {
  success: { label: "已推送", variant: "default" as const },
  pending: { label: "待推送", variant: "secondary" as const },
}

export default function GeneratedVouchersPage() {
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [searchTerm, setSearchTerm] = useState("")

  const pendingVouchers = generatedVouchers.filter(
    (v) => v.pushStatus === "pending"
  )

  const toggleAll = () => {
    if (selectedIds.length === pendingVouchers.length) {
      setSelectedIds([])
    } else {
      setSelectedIds(pendingVouchers.map((v) => v.id))
    }
  }

  const toggleOne = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/vouchers">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div>
          <h2 className="text-2xl font-semibold text-foreground">已生成凭证</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            查看已生成的记账凭证，推送至NC系统
          </p>
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-4">
          <div className="flex items-center gap-4">
            <CardTitle className="text-base font-medium">凭证列表</CardTitle>
            <Badge variant="secondary">
              {generatedVouchers.length} 份凭证
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="搜索凭证号"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-48 pl-9"
              />
            </div>
            <Button disabled={selectedIds.length === 0}>
              <Send className="mr-2 h-4 w-4" />
              批量推送NC ({selectedIds.length})
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">
                    <Checkbox
                      checked={
                        selectedIds.length === pendingVouchers.length &&
                        pendingVouchers.length > 0
                      }
                      onCheckedChange={toggleAll}
                    />
                  </TableHead>
                  <TableHead>凭证号</TableHead>
                  <TableHead>凭证日期</TableHead>
                  <TableHead>摘要</TableHead>
                  <TableHead>借方科目</TableHead>
                  <TableHead>贷方科目</TableHead>
                  <TableHead className="text-right">金额</TableHead>
                  <TableHead>NC凭证号</TableHead>
                  <TableHead>推送状态</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {generatedVouchers.map((voucher) => (
                  <TableRow key={voucher.id}>
                    <TableCell>
                      <Checkbox
                        checked={selectedIds.includes(voucher.id)}
                        onCheckedChange={() => toggleOne(voucher.id)}
                        disabled={voucher.pushStatus === "success"}
                      />
                    </TableCell>
                    <TableCell className="font-medium">
                      {voucher.voucherNo}
                    </TableCell>
                    <TableCell>{voucher.businessDate}</TableCell>
                    <TableCell className="max-w-48 truncate">
                      {voucher.summary}
                    </TableCell>
                    <TableCell>{voucher.debitAccount}</TableCell>
                    <TableCell>{voucher.creditAccount}</TableCell>
                    <TableCell className="text-right font-medium">
                      ¥{voucher.amount.toLocaleString()}
                    </TableCell>
                    <TableCell>
                      {voucher.ncVoucherNo ? (
                        <span className="text-primary">{voucher.ncVoucherNo}</span>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={pushStatusMap[voucher.pushStatus].variant}
                        className="gap-1"
                      >
                        {voucher.pushStatus === "success" && (
                          <CheckCircle2 className="h-3 w-3" />
                        )}
                        {pushStatusMap[voucher.pushStatus].label}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button size="sm" variant="outline">
                          <Eye className="mr-1 h-3 w-3" />
                          预览
                        </Button>
                        {voucher.pushStatus === "pending" && (
                          <Button size="sm">
                            <Send className="mr-1 h-3 w-3" />
                            推送
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
