"use client"

import { useState } from "react"
import {
  Search,
  Filter,
  RefreshCw,
  Calculator,
  TrendingUp,
  TrendingDown,
  LayoutGrid,
  FileText,
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
import { Progress } from "@/components/ui/progress"

const accountingRecords = [
  {
    id: "ACC20240115001",
    sectionName: "男装板块",
    sectionId: "SEC001",
    period: "2024-01",
    revenue: 3256000,
    cost: 1872000,
    grossProfit: 1384000,
    grossMargin: 42.5,
    operatingExpense: 456000,
    netProfit: 928000,
    status: "已核算",
    completeness: 100,
  },
  {
    id: "ACC20240115002",
    sectionName: "女装板块",
    sectionId: "SEC002",
    period: "2024-01",
    revenue: 4580000,
    cost: 2510000,
    grossProfit: 2070000,
    grossMargin: 45.2,
    operatingExpense: 598000,
    netProfit: 1472000,
    status: "已核算",
    completeness: 100,
  },
  {
    id: "ACC20240115003",
    sectionName: "童装板块",
    sectionId: "SEC003",
    period: "2024-01",
    revenue: 1890000,
    cost: 968000,
    grossProfit: 922000,
    grossMargin: 48.8,
    operatingExpense: 256000,
    netProfit: 666000,
    status: "已核算",
    completeness: 100,
  },
  {
    id: "ACC20240115004",
    sectionName: "运动板块",
    sectionId: "SEC004",
    period: "2024-01",
    revenue: 2680000,
    cost: 1648000,
    grossProfit: 1032000,
    grossMargin: 38.5,
    operatingExpense: 385000,
    netProfit: 647000,
    status: "核算中",
    completeness: 85,
  },
  {
    id: "ACC20240115005",
    sectionName: "鞋类板块",
    sectionId: "SEC005",
    period: "2024-01",
    revenue: 1560000,
    cost: 744000,
    grossProfit: 816000,
    grossMargin: 52.3,
    operatingExpense: 198000,
    netProfit: 618000,
    status: "待核算",
    completeness: 45,
  },
]

export default function SectionsAccountingPage() {
  const [searchTerm, setSearchTerm] = useState("")
  const [statusFilter, setStatusFilter] = useState("all")

  const filteredRecords = accountingRecords.filter((record) => {
    const matchesSearch =
      record.id.includes(searchTerm) ||
      record.sectionName.includes(searchTerm)
    const matchesStatus = statusFilter === "all" || record.status === statusFilter
    return matchesSearch && matchesStatus
  })

  const totalRevenue = accountingRecords.reduce((sum, r) => sum + r.revenue, 0)
  const totalProfit = accountingRecords.reduce((sum, r) => sum + r.netProfit, 0)
  const avgMargin =
    accountingRecords.reduce((sum, r) => sum + r.grossMargin, 0) /
    accountingRecords.length
  const completedCount = accountingRecords.filter(
    (r) => r.status === "已核算"
  ).length

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">板块核算</h1>
          <p className="text-sm text-muted-foreground">各板块的收入、成本、利润核算</p>
        </div>
        <Button>
          <RefreshCw className="mr-2 h-4 w-4" />
          重新核算
        </Button>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <StatCard
          title="总营收"
          value={`${(totalRevenue / 10000).toFixed(0)}万`}
          trend={{ value: 15.2, isPositive: true }}
          icon={<TrendingUp className="h-4 w-4" />}
        />
        <StatCard
          title="总净利润"
          value={`${(totalProfit / 10000).toFixed(0)}万`}
          trend={{ value: 8.6, isPositive: true }}
          icon={<Calculator className="h-4 w-4" />}
        />
        <StatCard
          title="平均毛利率"
          value={`${avgMargin.toFixed(1)}%`}
          icon={<TrendingUp className="h-4 w-4" />}
        />
        <StatCard
          title="已完成核算"
          value={`${completedCount}/${accountingRecords.length}`}
          icon={<FileText className="h-4 w-4" />}
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
                placeholder="搜索核算单号、板块名称..."
                className="pl-9"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="核算状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部状态</SelectItem>
                <SelectItem value="已核算">已核算</SelectItem>
                <SelectItem value="核算中">核算中</SelectItem>
                <SelectItem value="待核算">待核算</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline">
              <Filter className="mr-2 h-4 w-4" />
              更多筛选
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 核算表格 */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>核算单号</TableHead>
                <TableHead>板块</TableHead>
                <TableHead>核算期间</TableHead>
                <TableHead className="text-right">营收</TableHead>
                <TableHead className="text-right">成本</TableHead>
                <TableHead className="text-right">毛利</TableHead>
                <TableHead className="text-right">毛利率</TableHead>
                <TableHead className="text-right">净利润</TableHead>
                <TableHead>进度</TableHead>
                <TableHead>状态</TableHead>
                <TableHead className="w-[100px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredRecords.map((record) => (
                <TableRow key={record.id}>
                  <TableCell className="font-mono text-sm">{record.id}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1.5">
                      <LayoutGrid className="h-3.5 w-3.5 text-muted-foreground" />
                      {record.sectionName}
                    </div>
                  </TableCell>
                  <TableCell>{record.period}</TableCell>
                  <TableCell className="text-right font-medium">
                    ¥{(record.revenue / 10000).toFixed(0)}万
                  </TableCell>
                  <TableCell className="text-right text-muted-foreground">
                    ¥{(record.cost / 10000).toFixed(0)}万
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    ¥{(record.grossProfit / 10000).toFixed(0)}万
                  </TableCell>
                  <TableCell className="text-right">
                    <span
                      className={
                        record.grossMargin >= 45
                          ? "text-green-600"
                          : record.grossMargin >= 40
                          ? "text-foreground"
                          : "text-amber-600"
                      }
                    >
                      {record.grossMargin}%
                    </span>
                  </TableCell>
                  <TableCell className="text-right font-medium text-green-600">
                    ¥{(record.netProfit / 10000).toFixed(0)}万
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Progress value={record.completeness} className="h-2 w-16" />
                      <span className="text-xs text-muted-foreground">
                        {record.completeness}%
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        record.status === "已核算"
                          ? "default"
                          : record.status === "核算中"
                          ? "secondary"
                          : "outline"
                      }
                    >
                      {record.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="sm">
                      查看明细
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
