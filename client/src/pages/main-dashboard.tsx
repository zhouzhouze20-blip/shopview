import { useState, useEffect } from "react";
import { useLocation } from "wouter";
import { useQuery } from "@tanstack/react-query";
import NavigationSidebar from "@/components/navigation-sidebar";
import Dashboard from "./dashboard";
import TenantsPage from "./tenants";
import CountersPage from "./counters";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { StoreSelector } from "@/components/store-selector";
import { Building2, Users, FileText, CreditCard, BarChart3, TrendingUp, ArrowLeft, Calendar, CheckCircle, Clock, Plus, Edit, Trash2 } from "lucide-react";

// 品牌管理页面组件
function BrandsPage() {
  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold text-slate-900 mb-6">品牌档案</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>TechWorld</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-slate-600">专业电子产品零售</p>
            <div className="mt-2 text-sm text-slate-500">分类: 电子产品</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>时尚佳人</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-slate-600">时尚女装品牌</p>
            <div className="mt-2 text-sm text-slate-500">分类: 服装</div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// 合同管理页面组件
function ContractsPage() {
  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold text-slate-900 mb-6">合同台账</h1>
      <div className="grid grid-cols-1 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <FileText className="w-5 h-5 mr-2" />
              合同概览
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">12</div>
                <div className="text-sm text-slate-600">活跃合同</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">8</div>
                <div className="text-sm text-slate-600">续约合同</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-600">3</div>
                <div className="text-sm text-slate-600">即将到期</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">1</div>
                <div className="text-sm text-slate-600">过期合同</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// 财务管理页面组件
function FinancialPage() {
  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold text-slate-900 mb-6">财务管理</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">本月收入</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">¥2,458,000</div>
            <p className="text-xs text-muted-foreground">比上月增长 +12.5%</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">待收款</CardTitle>
            <CreditCard className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">¥186,400</div>
            <p className="text-xs text-muted-foreground">5个账单逾期</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">年收入目标</CardTitle>
            <BarChart3 className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">78%</div>
            <p className="text-xs text-muted-foreground">已完成年度目标</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// 系统总览页面组件
function SystemOverview() {
  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold text-slate-900 mb-6">可视化驾驶舱</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总商户数</CardTitle>
            <Users className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">24</div>
            <p className="text-xs text-muted-foreground">本月新增 3 家</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总铺位数</CardTitle>
            <Building2 className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">48</div>
            <p className="text-xs text-muted-foreground">出租率 85%</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">活跃合同</CardTitle>
            <FileText className="h-4 w-4 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">41</div>
            <p className="text-xs text-muted-foreground">3份即将到期</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">月收入</CardTitle>
            <CreditCard className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">¥2.4M</div>
            <p className="text-xs text-muted-foreground">环比增长 +12%</p>
          </CardContent>
        </Card>
      </div>
      
      <Card>
        <CardHeader>
          <CardTitle>系统功能模块</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="p-4 border rounded-lg hover:bg-slate-50 cursor-pointer">
              <Building2 className="w-8 h-8 text-blue-600 mb-2" />
              <h3 className="font-semibold">铺位资源管理</h3>
              <p className="text-sm text-slate-600">楼层平面图、厅房管理、空间资产</p>
            </div>
            <div className="p-4 border rounded-lg hover:bg-slate-50 cursor-pointer">
              <Users className="w-8 h-8 text-green-600 mb-2" />
              <h3 className="font-semibold">品牌商户管理</h3>
              <p className="text-sm text-slate-600">商户档案、品牌管理</p>
            </div>
            <div className="p-4 border rounded-lg hover:bg-slate-50 cursor-pointer">
              <FileText className="w-8 h-8 text-purple-600 mb-2" />
              <h3 className="font-semibold">合同管理</h3>
              <p className="text-sm text-slate-600">合同台账、租金条款</p>
            </div>
            <div className="p-4 border rounded-lg hover:bg-slate-50 cursor-pointer">
              <CreditCard className="w-8 h-8 text-orange-600 mb-2" />
              <h3 className="font-semibold">财务管理</h3>
              <p className="text-sm text-slate-600">账单管理、财务报表</p>
            </div>
            <div className="p-4 border rounded-lg hover:bg-slate-50 cursor-pointer">
              <BarChart3 className="w-8 h-8 text-blue-600 mb-2" />
              <h3 className="font-semibold">数据分析</h3>
              <p className="text-sm text-slate-600">收益分析、运营报表</p>
            </div>
            <div className="p-4 border rounded-lg hover:bg-slate-50 cursor-pointer">
              <Building2 className="w-8 h-8 text-slate-600 mb-2" />
              <h3 className="font-semibold">系统管理</h3>
              <p className="text-sm text-slate-600">用户管理、权限配置</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// 厅房管理页面组件
function HallsPage({ selectedStoreId }: { selectedStoreId?: number }) {
  const { toast } = useToast();
  
  const { data: halls, isLoading: isLoadingHalls } = useQuery({
    queryKey: ["/api/halls", selectedStoreId],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (selectedStoreId) params.set('storeId', selectedStoreId.toString());
      const response = await fetch(`/api/halls?${params}`);
      if (!response.ok) throw new Error('Failed to fetch halls');
      return response.json();
    },
    enabled: !!selectedStoreId
  });

  const { data: markedRooms, isLoading: isLoadingMarkedRooms } = useQuery({
    queryKey: ["/api/marked-rooms", selectedStoreId],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (selectedStoreId) params.set('storeId', selectedStoreId.toString());
      const response = await fetch(`/api/marked-rooms?${params}`);
      if (!response.ok) throw new Error('Failed to fetch marked rooms');
      return response.json();
    },
    enabled: !!selectedStoreId
  });

  const isLoading = isLoadingHalls || isLoadingMarkedRooms;

  if (!selectedStoreId) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-lg text-slate-500">请先选择一个门店</div>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-lg">正在加载厅房信息...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold text-slate-900 mb-6">厅房管理</h1>
      
      {/* 用户标记的厅房 */}
      <div className="mb-8">
        <div className="bg-white rounded-lg shadow-sm border border-slate-200">
          <div className="p-4 border-b border-slate-200">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold flex items-center gap-2">
                  <Building2 className="h-5 w-5 text-blue-600" />
                  用户标记的厅房
                </h2>
                <p className="text-sm text-slate-600 mt-1">在楼层平面图中绘制的厅房</p>
              </div>
              <Button 
                onClick={async () => {
                  try {
                    const response = await fetch("/api/marked-rooms/auto-link", {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ storeId: selectedStoreId }),
                    });
                    const result = await response.json();
                    if (response.ok) {
                      toast({
                        title: "关联成功",
                        description: `成功关联 ${result.linked} 个厅房`,
                      });
                      // 刷新数据
                      window.location.reload();
                    } else {
                      throw new Error(result.error);
                    }
                  } catch (error) {
                    toast({
                      title: "关联失败",
                      description: "自动关联过程中发生错误",
                      variant: "destructive",
                    });
                  }
                }}
                size="sm"
                data-testid="button-auto-link"
              >
                <Building2 className="w-4 h-4 mr-2" />
                自动关联柜位
              </Button>
            </div>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>厅房名称</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>位置</TableHead>
                <TableHead>尺寸</TableHead>
                <TableHead>关联柜位</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>创建时间</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {markedRooms && markedRooms.length > 0 ? (
                markedRooms.map((room: any) => (
                  <TableRow key={room.id}>
                    <TableCell className="font-medium text-blue-600">{room.name}</TableCell>
                    <TableCell>{room.type === 'rectangle' ? '矩形' : '多边形'}</TableCell>
                    <TableCell>
                      ({parseFloat(room.x).toFixed(1)}%, {parseFloat(room.y).toFixed(1)}%)
                    </TableCell>
                    <TableCell>
                      {room.width && room.height 
                        ? `${parseFloat(room.width).toFixed(1)}% × ${parseFloat(room.height).toFixed(1)}%`
                        : '-'
                      }
                    </TableCell>
                    <TableCell>
                      {room.counterId ? (
                        <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                          ✓ 已关联
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="bg-gray-50 text-gray-700 border-gray-200">
                          未关联
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                        用户绘制
                      </Badge>
                    </TableCell>
                    <TableCell>{new Date(room.createdAt).toLocaleDateString()}</TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-slate-500">
                    <Building2 className="h-12 w-12 mx-auto mb-3 text-slate-300" />
                    <p>暂无用户标记的厅房</p>
                    <p className="text-sm mt-1">在楼层平面图中绘制厅房后会在这里显示</p>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* 系统厅房 */}
      <div className="bg-white rounded-lg shadow-sm border border-slate-200">
        <div className="p-4 border-b border-slate-200">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Building2 className="h-5 w-5 text-green-600" />
            系统厅房
          </h2>
          <p className="text-sm text-slate-600 mt-1">系统预定义的厅房</p>
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>厅房名称</TableHead>
              <TableHead>编号</TableHead>
              <TableHead>面积</TableHead>
              <TableHead>月租金</TableHead>
              <TableHead>状态</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {halls && halls.length > 0 ? (
              halls.map((hall: any) => (
                <TableRow key={hall.hallId}>
                  <TableCell className="font-medium text-green-600">{hall.hallName}</TableCell>
                  <TableCell>{hall.hallCode}</TableCell>
                  <TableCell>{parseFloat(hall.area).toFixed(0)} m²</TableCell>
                  <TableCell>
                    ¥{hall.monthlyRent ? parseFloat(hall.monthlyRent).toLocaleString() : '未设定'}
                  </TableCell>
                  <TableCell>
                    <Badge 
                      variant={hall.status === 'occupied' ? 'default' : hall.status === 'vacant' ? 'secondary' : 'outline'}
                      className={
                        hall.status === 'occupied' ? 'bg-green-100 text-green-800 border-green-200' :
                        hall.status === 'vacant' ? 'bg-gray-100 text-gray-800 border-gray-200' :
                        'bg-yellow-100 text-yellow-800 border-yellow-200'
                      }
                    >
                      {hall.status === 'occupied' ? '已占用' : hall.status === 'vacant' ? '空闲' : '维护中'}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={5} className="text-center py-8 text-slate-500">
                  <Building2 className="h-12 w-12 mx-auto mb-3 text-slate-300" />
                  <p>暂无系统厅房数据</p>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

// 楼层管理页面组件
function FloorsPage({ selectedStoreId }: { selectedStoreId?: number }) {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newFloorPlan, setNewFloorPlan] = useState({
    name: "",
    planVersion: "1.0",
    level: "",
    floorNumber: 1,
    description: "",
    effectiveDate: new Date().toISOString().split('T')[0],
    expiryDate: ""
  });
  const { toast } = useToast();

  const { data: floorPlans, isLoading, refetch } = useQuery({
    queryKey: ["/api/floor-plans", selectedStoreId],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (selectedStoreId) params.set('storeId', selectedStoreId.toString());
      const response = await fetch(`/api/floor-plans?${params}`);
      if (!response.ok) throw new Error('Failed to fetch floor plans');
      return response.json();
    },
    enabled: !!selectedStoreId
  });

  const handleCreateFloorPlan = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      const floorPlanData = {
        ...newFloorPlan,
        storeId: selectedStoreId,
        floorNumber: parseInt(newFloorPlan.floorNumber.toString()),
        effectiveDate: new Date(newFloorPlan.effectiveDate).toISOString(),
        expiryDate: newFloorPlan.expiryDate ? new Date(newFloorPlan.expiryDate).toISOString() : null,
        createdBy: "current-user"
      };

      const response = await fetch("/api/floor-plans", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(floorPlanData)
      });

      if (!response.ok) throw new Error("Failed to create floor plan");
      
      toast({ title: "成功", description: "楼层平面图创建成功" });
      setIsCreateModalOpen(false);
      setNewFloorPlan({
        name: "",
        planVersion: "1.0", 
        level: "",
        floorNumber: 1,
        description: "",
        effectiveDate: new Date().toISOString().split('T')[0],
        expiryDate: ""
      });
      refetch();
    } catch (error) {
      toast({ title: "错误", description: "创建楼层平面图失败", variant: "destructive" });
    }
  };

  const handleActivateFloorPlan = async (id: string) => {
    try {
      const response = await fetch(`/api/floor-plans/${id}/activate`, {
        method: "POST"
      });

      if (!response.ok) throw new Error("Failed to activate floor plan");
      
      toast({ title: "成功", description: "楼层平面图已激活" });
      refetch();
    } catch (error) {
      toast({ title: "错误", description: "激活楼层平面图失败", variant: "destructive" });
    }
  };

  const handleDeactivateFloorPlan = async (id: string) => {
    try {
      const response = await fetch(`/api/floor-plans/${id}/deactivate`, {
        method: "POST"
      });

      if (!response.ok) throw new Error("Failed to deactivate floor plan");
      
      toast({ title: "成功", description: "楼层平面图已停用" });
      refetch();
    } catch (error) {
      toast({ title: "错误", description: "停用楼层平面图失败", variant: "destructive" });
    }
  };

  if (!selectedStoreId) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-lg text-slate-500">请先选择一个门店</div>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-lg">正在加载楼层信息...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-slate-900">楼层管理</h1>
        
        <Dialog open={isCreateModalOpen} onOpenChange={setIsCreateModalOpen}>
          <DialogTrigger asChild>
            <Button className="flex items-center gap-2">
              <Plus className="h-4 w-4" />
              创建新平面图
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>创建楼层平面图</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreateFloorPlan} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="name">平面图名称</Label>
                  <Input
                    id="name"
                    value={newFloorPlan.name}
                    onChange={(e) => setNewFloorPlan({ ...newFloorPlan, name: e.target.value })}
                    placeholder="例: L1主营业区"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="version">版本号</Label>
                  <Input
                    id="version"
                    value={newFloorPlan.planVersion}
                    onChange={(e) => setNewFloorPlan({ ...newFloorPlan, planVersion: e.target.value })}
                    placeholder="例: 1.0"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="level">楼层</Label>
                  <Input
                    id="level"
                    value={newFloorPlan.level}
                    onChange={(e) => setNewFloorPlan({ ...newFloorPlan, level: e.target.value })}
                    placeholder="例: L1, F1, B1"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="floorNumber">楼层编号</Label>
                  <Input
                    id="floorNumber"
                    type="number"
                    value={newFloorPlan.floorNumber}
                    onChange={(e) => setNewFloorPlan({ ...newFloorPlan, floorNumber: parseInt(e.target.value) })}
                    placeholder="1"
                    required
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="description">描述</Label>
                <Textarea
                  id="description"
                  value={newFloorPlan.description}
                  onChange={(e) => setNewFloorPlan({ ...newFloorPlan, description: e.target.value })}
                  placeholder="楼层平面图描述信息"
                  rows={2}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="effectiveDate">生效日期</Label>
                  <Input
                    id="effectiveDate"
                    type="date"
                    value={newFloorPlan.effectiveDate}
                    onChange={(e) => setNewFloorPlan({ ...newFloorPlan, effectiveDate: e.target.value })}
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="expiryDate">失效日期 (可选)</Label>
                  <Input
                    id="expiryDate"
                    type="date"
                    value={newFloorPlan.expiryDate}
                    onChange={(e) => setNewFloorPlan({ ...newFloorPlan, expiryDate: e.target.value })}
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-4">
                <Button type="button" variant="outline" onClick={() => setIsCreateModalOpen(false)}>
                  取消
                </Button>
                <Button type="submit">创建</Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-slate-200">
        <div className="p-4 border-b border-slate-200">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Building2 className="h-5 w-5 text-blue-600" />
            楼层平面图管理
          </h2>
          <p className="text-sm text-slate-600 mt-1">管理楼层平面图版本、生效时间和状态</p>
        </div>
        
        <div className="divide-y divide-slate-200">
          {floorPlans && floorPlans.length > 0 ? (
            floorPlans.map((plan: any) => (
              <div key={plan.id} className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="font-semibold text-lg">{plan.name}</h3>
                      <Badge 
                        variant={plan.isActive ? "default" : "secondary"}
                        className={plan.isActive ? "bg-green-100 text-green-800 border-green-200" : ""}
                      >
                        {plan.isActive ? "当前激活" : "未激活"}
                      </Badge>
                      <Badge variant="outline">v{plan.planVersion}</Badge>
                    </div>
                    
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-slate-600">
                      <div className="flex items-center gap-1">
                        <Building2 className="h-4 w-4" />
                        <span>{plan.level} ({plan.floorNumber}楼)</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Calendar className="h-4 w-4" />
                        <span>生效: {new Date(plan.effectiveDate).toLocaleDateString()}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Clock className="h-4 w-4" />
                        <span>失效: {plan.expiryDate ? new Date(plan.expiryDate).toLocaleDateString() : "无限期"}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Users className="h-4 w-4" />
                        <span>创建者: {plan.createdBy || "系统"}</span>
                      </div>
                    </div>
                    
                    {plan.description && (
                      <p className="text-sm text-slate-500 mt-2">{plan.description}</p>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-2 ml-4">
                    {!plan.isActive && (
                      <Button 
                        size="sm" 
                        onClick={() => handleActivateFloorPlan(plan.id)}
                        className="flex items-center gap-1"
                      >
                        <CheckCircle className="h-4 w-4" />
                        激活
                      </Button>
                    )}
                    {plan.isActive && (
                      <Button 
                        size="sm" 
                        variant="outline"
                        onClick={() => handleDeactivateFloorPlan(plan.id)}
                        className="flex items-center gap-1"
                      >
                        <Clock className="h-4 w-4" />
                        停用
                      </Button>
                    )}
                    <Button size="sm" variant="outline" className="flex items-center gap-1">
                      <Edit className="h-4 w-4" />
                      编辑
                    </Button>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="p-8 text-center text-slate-500">
              <Building2 className="h-12 w-12 mx-auto mb-3 text-slate-300" />
              <p>暂无楼层平面图</p>
              <p className="text-sm mt-1">点击"创建新平面图"开始配置楼层</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function MainDashboard() {
  const [activeModule, setActiveModule] = useState("dashboard");
  const [selectedStoreId, setSelectedStoreId] = useState<number | undefined>(undefined);
  const [location, setLocation] = useLocation();

  // 从URL参数获取门店ID和视图
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const storeIdParam = params.get('storeId');
    const viewParam = params.get('view');
    
    if (storeIdParam) {
      setSelectedStoreId(parseInt(storeIdParam));
    }
    
    if (viewParam) {
      if (viewParam === 'rooms') {
        setActiveModule('floor-plan');
      } else {
        setActiveModule(viewParam);
      }
    }
  }, [location]);

  const renderContent = () => {
    switch (activeModule) {
      case "dashboard":
        return <SystemOverview />;
      case "floor-plan":
        return <Dashboard selectedStoreId={selectedStoreId} />;
      case "floors":
        return <FloorsPage selectedStoreId={selectedStoreId} />;
      case "counters":
        return <CountersPage selectedStoreId={selectedStoreId} />;
      case "halls":
        return <HallsPage selectedStoreId={selectedStoreId} />;
      case "tenants":
        return <TenantsPage selectedStoreId={selectedStoreId} />;
      case "brands":
        return <BrandsPage />;
      case "contracts":
        return <ContractsPage />;
      case "bills":
        return <FinancialPage />;
      default:
        return <SystemOverview />;
    }
  };

  const handleBackToStores = () => {
    setLocation('/stores');
  };

  const handleStoreChange = (storeId: number | undefined) => {
    setSelectedStoreId(storeId);
    // 更新URL参数
    const params = new URLSearchParams();
    if (storeId) {
      params.set('storeId', storeId.toString());
    }
    const newUrl = `/dashboard${params.toString() ? '?' + params.toString() : ''}`;
    setLocation(newUrl);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex" data-testid="main-dashboard">
      <NavigationSidebar 
        activeModule={activeModule} 
        onModuleChange={setActiveModule}
      />
      <main className="flex-1 overflow-auto" data-testid="main-content">
        {/* 顶部工具栏 */}
        <div className="bg-white border-b px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleBackToStores}
              className="flex items-center gap-2"
              data-testid="button-back-to-stores"
            >
              <ArrowLeft className="h-4 w-4" />
              返回门店选择
            </Button>
            
            <div className="h-4 w-px bg-gray-300" />
            
            <StoreSelector
              selectedStoreId={selectedStoreId}
              onStoreChange={handleStoreChange}
              placeholder="选择门店"
            />
          </div>
          
          <div className="text-sm text-muted-foreground">
            百货柜位管理系统
          </div>
        </div>
        
        {renderContent()}
      </main>
    </div>
  );
}