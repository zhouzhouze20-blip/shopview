"use client"

import { useState } from "react"
import {
  Search,
  Filter,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Store,
  ArrowRight,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { StatCard } from "@/components/stat-card"

const reconciliations = [
  {
    id: "RC20240115001",
    storeName: "城西旗舰店",
    storeId: "ST001",
    date: "2024-01-15",
    posAmount: 125600,
    bankAmount: 125600,
    difference: 0,
    status: "已对平",
    items: { matched: 38, unmatched: 0 },
  },
  {
    id: "RC20240115002",
    storeName: "滨江购物中心店",
    storeId: "ST002",
    date: "2024-01-15",
    posAmount: 89200,
    bankAmount: 89000,
    difference: 200,
    status: "有差异",
    items: { matched: 26, unmatched: 2 },
  },
  {
    id: "RC20240115003",
    storeName: "南京新街口店",
    storeId: "ST003",
    date: "2024-01-15",
    posAmount: 198500,
    bankAmount: 198500,
    difference: 0,
    status: "已对平",
    items: { matched: 55, unmatched: 0 },
  },
  {
    id: "RC20240114001",
    storeName: "城西旗舰店",
    storeId: "ST001",
    date: "2024-01-14",
    posAmount: 156800,
    bankAmount: 156800,
    difference: 0,
    status: "已对平",
    items: { matched: 45, unmatched: 0 },
  },
  {
    id: "RC20240115004",
    storeName: "苏州观前店",
    storeId: "ST005",
    date: "2024-01-15",
    posAmount: 75600,
    bankAmount: 0,
    difference: 75600,
    status: "待对账",
    items: { matched: 0, unmatched: 22 },
  },
]

export default function StoresReconciliationPage() {
  const [searchTerm, setSearchTerm] = useState("")
  const [statusFilter, setStatusFilter] = useState("all")

  const filteredReconciliations = reconciliations.filter((rec) => {
    const matchesSearch =
      rec.id.includes(searchTerm) || rec.storeName.includes(searchTerm)
    const matchesStatus = statusFilter === "all" || rec.status === statusFilter
    return matchesSearch && matchesStatus
  })

  const matchedCount = reconciliations.filter((r) => r.status === "已对平").length
  const differenceCount = reconciliations.filter((r) => r.status === "有差异").length
  const pendingCount = reconciliations.filter((r) => r.status === "待对账").length

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">门店对账</h1>
          <p className="text-sm text-muted-foreground">POS 收款与银行到账的对账核实</p>
        </div>
        <Button>
          <RefreshCw className="mr-2 h-4 w-4" />
          刷新对账数据
        </Button>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <StatCard
          title="今日对账单"
          value={reconciliations.length}
          suffix="笔"
          icon={<Store className="h-4 w-4" />}
        />
        <StatCard
          title="已对平"
          value={matchedCount}
          suffix="笔"
          icon={<CheckCircle2 className="h-4 w-4" />}
        />
        <StatCard
          title="有差异"
          value={differenceCount}
          suffix="笔"
          icon={<AlertTriangle className="h-4 w-4" />}
        />
        <StatCard
          title="待对账"
          value={pendingCount}
          suffix="笔"
          icon={<XCircle className="h-4 w-4" />}
        />
      </div>

      {/* 筛选区 */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-medium">筛选条件</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="搜索对账单号、门店名称..."
                className="pl-9"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="对账状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部状态</SelectItem>
                <SelectItem value="已对平">已对平</SelectItem>
                <SelectItem value="有差异">有差异</SelectItem>
                <SelectItem value="待对账">待对账</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline">
              <Filter className="mr-2 h-4 w-4" />
              更多筛选
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 对账表格 */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>对账单号</TableHead>
                <TableHead>门店</TableHead>
                <TableHead>对账日期</TableHead>
                <TableHead className="text-right">POS 收款</TableHead>
                <TableHead className="text-center"></TableHead>
                <TableHead className="text-right">银行到账</TableHead>
                <TableHead className="text-right">差异金额</TableHead>
                <TableHead className="text-center">匹配情况</TableHead>
                <TableHead>状态</TableHead>
                <TableHead className="w-[100px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredReconciliations.map((rec) => (
                <TableRow key={rec.id}>
                  <TableCell className="font-mono text-sm">{rec.id}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1.5">
                      <Store className="h-3.5 w-3.5 text-muted-foreground" />
                      {rec.storeName}
                    </div>
                  </TableCell>
                  <TableCell>{rec.date}</TableCell>
                  <TableCell className="text-right font-medium">
                    ¥{rec.posAmount.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-center">
                    <ArrowRight className="h-4 w-4 text-muted-foreground mx-auto" />
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    ¥{rec.bankAmount.toLocaleString()}
                  </TableCell>
                  <TableCell
                    className={`text-right font-medium ${
                      rec.difference !== 0 ? "text-destructive" : "text-muted-foreground"
                    }`}
                  >
                    {rec.difference !== 0 ? `¥${rec.difference.toLocaleString()}` : "-"}
                  </TableCell>
                  <TableCell className="text-center">
                    <span className="text-sm">
                      <span className="text-green-600">{rec.items.matched}</span>
                      {rec.items.unmatched > 0 && (
                        <>
                          {" / "}
                          <span className="text-destructive">{rec.items.unmatched}</span>
                        </>
                      )}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        rec.status === "已对平"
                          ? "default"
                          : rec.status === "有差异"
                          ? "destructive"
                          : "secondary"
                      }
                    >
                      {rec.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="sm">
                      查看详情
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
