"use client"

import { useState } from "react"
import {
  ArrowLeft,
  Search,
  Check,
  Eye,
  FileText,
  CheckCircle2,
  AlertCircle,
} from "lucide-react"
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

const pendingVouchers = [
  {
    id: "1",
    archiveNo: "AR-2024-0010",
    businessDate: "2024-11-15",
    invoiceMatched: true,
    transactionMatched: true,
    documentMatched: true,
    amount: 86500.0,
    readyToGenerate: true,
  },
  {
    id: "2",
    archiveNo: "AR-2024-0011",
    businessDate: "2024-11-14",
    invoiceMatched: true,
    transactionMatched: true,
    documentMatched: false,
    amount: 45200.0,
    readyToGenerate: false,
  },
  {
    id: "3",
    archiveNo: "AR-2024-0012",
    businessDate: "2024-11-14",
    invoiceMatched: true,
    transactionMatched: false,
    documentMatched: true,
    amount: 128000.0,
    readyToGenerate: false,
  },
  {
    id: "4",
    archiveNo: "AR-2024-0013",
    businessDate: "2024-11-13",
    invoiceMatched: true,
    transactionMatched: true,
    documentMatched: true,
    amount: 67800.0,
    readyToGenerate: true,
  },
  {
    id: "5",
    archiveNo: "AR-2024-0014",
    businessDate: "2024-11-13",
    invoiceMatched: true,
    transactionMatched: true,
    documentMatched: true,
    amount: 92300.0,
    readyToGenerate: true,
  },
]

export default function PendingVouchersPage() {
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [searchTerm, setSearchTerm] = useState("")

  const readyVouchers = pendingVouchers.filter((v) => v.readyToGenerate)

  const toggleAll = () => {
    if (selectedIds.length === readyVouchers.length) {
      setSelectedIds([])
    } else {
      setSelectedIds(readyVouchers.map((v) => v.id))
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
          <h2 className="text-2xl font-semibold text-foreground">待生成凭证</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            确认档案包完整后生成记账凭证
          </p>
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-4">
          <div className="flex items-center gap-4">
            <CardTitle className="text-base font-medium">待生成列表</CardTitle>
            <Badge variant="secondary">
              {pendingVouchers.length} 份待处理
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="搜索档案号"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-48 pl-9"
              />
            </div>
            <Button
              disabled={selectedIds.length === 0}
              onClick={() => alert(`生成 ${selectedIds.length} 份凭证`)}
            >
              <FileText className="mr-2 h-4 w-4" />
              批量生成 ({selectedIds.length})
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
                        selectedIds.length === readyVouchers.length &&
                        readyVouchers.length > 0
                      }
                      onCheckedChange={toggleAll}
                    />
                  </TableHead>
                  <TableHead>档案编号</TableHead>
                  <TableHead>业务日期</TableHead>
                  <TableHead className="text-center">发票</TableHead>
                  <TableHead className="text-center">流水</TableHead>
                  <TableHead className="text-center">单据</TableHead>
                  <TableHead className="text-right">金额</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pendingVouchers.map((voucher) => (
                  <TableRow
                    key={voucher.id}
                    className={!voucher.readyToGenerate ? "opacity-60" : ""}
                  >
                    <TableCell>
                      <Checkbox
                        checked={selectedIds.includes(voucher.id)}
                        onCheckedChange={() => toggleOne(voucher.id)}
                        disabled={!voucher.readyToGenerate}
                      />
                    </TableCell>
                    <TableCell className="font-medium">
                      {voucher.archiveNo}
                    </TableCell>
                    <TableCell>{voucher.businessDate}</TableCell>
                    <TableCell className="text-center">
                      {voucher.invoiceMatched ? (
                        <CheckCircle2 className="mx-auto h-4 w-4 text-emerald-500" />
                      ) : (
                        <AlertCircle className="mx-auto h-4 w-4 text-amber-500" />
                      )}
                    </TableCell>
                    <TableCell className="text-center">
                      {voucher.transactionMatched ? (
                        <CheckCircle2 className="mx-auto h-4 w-4 text-emerald-500" />
                      ) : (
                        <AlertCircle className="mx-auto h-4 w-4 text-amber-500" />
                      )}
                    </TableCell>
                    <TableCell className="text-center">
                      {voucher.documentMatched ? (
                        <CheckCircle2 className="mx-auto h-4 w-4 text-emerald-500" />
                      ) : (
                        <AlertCircle className="mx-auto h-4 w-4 text-amber-500" />
                      )}
                    </TableCell>
                    <TableCell className="text-right font-medium">
                      ¥{voucher.amount.toLocaleString()}
                    </TableCell>
                    <TableCell>
                      {voucher.readyToGenerate ? (
                        <Badge variant="default">可生成</Badge>
                      ) : (
                        <Badge variant="secondary">待完善</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button size="sm" variant="outline">
                          <Eye className="mr-1 h-3 w-3" />
                          预览
                        </Button>
                        <Button size="sm" disabled={!voucher.readyToGenerate}>
                          <Check className="mr-1 h-3 w-3" />
                          生成
                        </Button>
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
