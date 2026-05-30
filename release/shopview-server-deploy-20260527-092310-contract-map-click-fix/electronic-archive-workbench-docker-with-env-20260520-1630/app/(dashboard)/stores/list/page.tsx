"use client"

import { useState } from "react"
import {
  Search,
  Filter,
  Download,
  MapPin,
  Phone,
  User,
  MoreHorizontal,
  Eye,
  Edit,
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { StatCard } from "@/components/stat-card"

const stores = [
  {
    id: "ST001",
    name: "城西旗舰店",
    region: "华东区",
    city: "杭州市",
    address: "西湖区文三路 388 号",
    manager: "张明",
    phone: "0571-88888001",
    status: "正常营业",
    monthlyRevenue: 1256000,
    archiveCount: 342,
    lastSync: "2024-01-15 14:30",
  },
  {
    id: "ST002",
    name: "滨江购物中心店",
    region: "华东区",
    city: "杭州市",
    address: "滨江区江南大道 1288 号",
    manager: "李红",
    phone: "0571-88888002",
    status: "正常营业",
    monthlyRevenue: 892000,
    archiveCount: 256,
    lastSync: "2024-01-15 13:45",
  },
  {
    id: "ST003",
    name: "南京新街口店",
    region: "华东区",
    city: "南京市",
    address: "玄武区新街口大街 168 号",
    manager: "王磊",
    phone: "025-88888003",
    status: "正常营业",
    monthlyRevenue: 1580000,
    archiveCount: 428,
    lastSync: "2024-01-15 12:15",
  },
  {
    id: "ST004",
    name: "上海淮海店",
    region: "华东区",
    city: "上海市",
    address: "黄浦区淮海中路 688 号",
    manager: "赵芳",
    phone: "021-88888004",
    status: "装修中",
    monthlyRevenue: 0,
    archiveCount: 156,
    lastSync: "2024-01-10 09:00",
  },
  {
    id: "ST005",
    name: "苏州观前店",
    region: "华东区",
    city: "苏州市",
    address: "姑苏区观前街 299 号",
    manager: "孙伟",
    phone: "0512-88888005",
    status: "正常营业",
    monthlyRevenue: 756000,
    archiveCount: 198,
    lastSync: "2024-01-15 14:00",
  },
]

const statusColorMap: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  "正常营业": "default",
  "装修中": "secondary",
  "暂停营业": "destructive",
}

export default function StoresListPage() {
  const [searchTerm, setSearchTerm] = useState("")
  const [regionFilter, setRegionFilter] = useState("all")

  const filteredStores = stores.filter((store) => {
    const matchesSearch =
      store.name.includes(searchTerm) ||
      store.id.includes(searchTerm) ||
      store.city.includes(searchTerm)
    const matchesRegion = regionFilter === "all" || store.region === regionFilter
    return matchesSearch && matchesRegion
  })

  const totalRevenue = stores.reduce((sum, s) => sum + s.monthlyRevenue, 0)
  const activeStores = stores.filter((s) => s.status === "正常营业").length
  const totalArchives = stores.reduce((sum, s) => sum + s.archiveCount, 0)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">门店列表</h1>
          <p className="text-sm text-muted-foreground">管理百货事业部所有门店信息</p>
        </div>
        <Button>
          <Download className="mr-2 h-4 w-4" />
          导出门店数据
        </Button>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <StatCard
          title="门店总数"
          value={stores.length}
          suffix="家"
          trend={{ value: 2, isPositive: true }}
          icon={<MapPin className="h-4 w-4" />}
        />
        <StatCard
          title="正常营业"
          value={activeStores}
          suffix="家"
          icon={<MapPin className="h-4 w-4" />}
        />
        <StatCard
          title="本月营收"
          value={`${(totalRevenue / 10000).toFixed(0)}万`}
          trend={{ value: 8.5, isPositive: true }}
          icon={<FileText className="h-4 w-4" />}
        />
        <StatCard
          title="档案总数"
          value={totalArchives}
          suffix="份"
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
                placeholder="搜索门店编号、名称、城市..."
                className="pl-9"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <Select value={regionFilter} onValueChange={setRegionFilter}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="选择区域" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部区域</SelectItem>
                <SelectItem value="华东区">华东区</SelectItem>
                <SelectItem value="华南区">华南区</SelectItem>
                <SelectItem value="华北区">华北区</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline">
              <Filter className="mr-2 h-4 w-4" />
              更多筛选
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 门店表格 */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[100px]">门店编号</TableHead>
                <TableHead>门店名称</TableHead>
                <TableHead>所在城市</TableHead>
                <TableHead>门店地址</TableHead>
                <TableHead>店长</TableHead>
                <TableHead>状态</TableHead>
                <TableHead className="text-right">本月营收</TableHead>
                <TableHead className="text-right">档案数</TableHead>
                <TableHead className="w-[60px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredStores.map((store) => (
                <TableRow key={store.id}>
                  <TableCell className="font-mono text-sm">{store.id}</TableCell>
                  <TableCell className="font-medium">{store.name}</TableCell>
                  <TableCell>{store.city}</TableCell>
                  <TableCell className="max-w-[200px] truncate text-muted-foreground">
                    {store.address}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <User className="h-3 w-3 text-muted-foreground" />
                      {store.manager}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant={statusColorMap[store.status]}>
                      {store.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {store.monthlyRevenue > 0
                      ? `¥${(store.monthlyRevenue / 10000).toFixed(1)}万`
                      : "-"}
                  </TableCell>
                  <TableCell className="text-right">{store.archiveCount}</TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem>
                          <Eye className="mr-2 h-4 w-4" />
                          查看详情
                        </DropdownMenuItem>
                        <DropdownMenuItem>
                          <Edit className="mr-2 h-4 w-4" />
                          编辑门店
                        </DropdownMenuItem>
                        <DropdownMenuItem>
                          <FileText className="mr-2 h-4 w-4" />
                          查看档案
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
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
