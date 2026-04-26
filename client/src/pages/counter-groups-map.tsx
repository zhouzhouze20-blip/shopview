import { useState, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { formatOperationMethod } from "@/lib/operation-method";
import { Building2, Search, Filter, MapPin, Users, Eye, EyeOff, ZoomIn, ZoomOut, RotateCcw } from "lucide-react";
import { useStore } from "@/contexts/StoreContext";

interface CounterGroup {
  group_id: number;
  group_code: string;
  group_name: string;
  department_code?: string;
  department_name?: string;
  operation_method?: string;
  brand_name?: string;
  monthly_revenue?: number;
  is_active: boolean;
  erp_sync_time?: string;
  created_at: string;
  updated_at?: string;
}

interface Hall {
  hall_id: number;
  hall_code: string;
  hall_name?: string;
  counter_number: string;
  area?: number;
  shape_type: string;
  position_data?: {
    x: number;
    y: number;
    width: number;
    height: number;
    points?: Array<{x: number, y: number}>;
  };
  store_id: number;
  floor_id: number;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

interface HallGroupBinding {
  binding_id: number;
  hall_id: number;
  group_code: string;
  is_active: boolean;
  bound_at: string;
  bound_by?: string;
}

interface GroupWithHall extends CounterGroup {
  hall?: Hall;
  binding?: HallGroupBinding;
}

export default function CounterGroupsMapPage() {
  const [groups, setGroups] = useState<GroupWithHall[]>([]);
  const [filteredGroups, setFilteredGroups] = useState<GroupWithHall[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [storeFilter, setStoreFilter] = useState<string>("all");
  const [selectedGroup, setSelectedGroup] = useState<GroupWithHall | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [showInactive, setShowInactive] = useState(false);
  const { stores } = useStore();

  // 获取柜组数据
  useEffect(() => {
    const fetchGroups = async () => {
      try {
        setIsLoading(true);
        const [groupsResponse, hallsResponse, bindingsResponse] = await Promise.all([
          fetch('/api/halls/counter-groups/'),
          fetch('/api/halls/'),
          fetch('/api/halls/bindings/')
        ]);

        if (groupsResponse.ok && hallsResponse.ok && bindingsResponse.ok) {
          const groupsData = await groupsResponse.json();
          const hallsData = await hallsResponse.json();
          const bindingsData = await bindingsResponse.json();

          // 合并数据
          const groupsWithHalls: GroupWithHall[] = groupsData.map((group: CounterGroup) => {
            const binding = bindingsData.find((b: HallGroupBinding) => 
              b.group_code === group.group_code && b.is_active
            );
            const hall = binding ? hallsData.find((h: Hall) => h.hall_id === binding.hall_id) : null;
            
            return {
              ...group,
              hall,
              binding
            };
          });

          setGroups(groupsWithHalls);
          setFilteredGroups(groupsWithHalls);
        } else {
          console.error('获取柜组数据失败');
        }
      } catch (error) {
        console.error('获取柜组数据出错:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchGroups();
  }, []);

  // 筛选柜组数据
  useEffect(() => {
    let filtered = groups;

    // 按搜索关键词筛选
    if (searchQuery) {
      filtered = filtered.filter(group =>
        group.group_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        group.group_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (group.brand_name && group.brand_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (group.department_name && group.department_name.toLowerCase().includes(searchQuery.toLowerCase()))
      );
    }

    // 按状态筛选
    if (statusFilter !== "all") {
      if (statusFilter === "occupied") {
        filtered = filtered.filter(group => group.hall && group.binding?.is_active);
      } else if (statusFilter === "vacant") {
        filtered = filtered.filter(group => !group.hall || !group.binding?.is_active);
      }
    }

    // 按门店筛选
    if (storeFilter !== "all") {
      filtered = filtered.filter(group => 
        group.hall && group.hall.store_id === parseInt(storeFilter)
      );
    }

    // 按活跃状态筛选
    if (!showInactive) {
      filtered = filtered.filter(group => group.is_active);
    }

    setFilteredGroups(filtered);
  }, [groups, searchQuery, statusFilter, storeFilter, showInactive]);

  // 获取状态显示信息
  const getStatusInfo = (group: GroupWithHall) => {
    if (group.hall && group.binding?.is_active) {
      return { label: '已分配', variant: 'default', className: 'bg-green-100 text-green-800' };
    } else {
      return { label: '未分配', variant: 'secondary', className: 'bg-yellow-100 text-yellow-800' };
    }
  };

  // 获取门店名称
  const getStoreName = (storeId: number) => {
    const store = stores.find(s => s.storeId === storeId);
    return store ? store.storeName : `门店${storeId}`;
  };

  // 处理柜组点击
  const handleGroupClick = (group: GroupWithHall) => {
    setSelectedGroup(group);
    setIsDetailModalOpen(true);
  };

  // 缩放控制
  const handleZoomIn = () => {
    setZoom(prev => Math.min(prev + 0.25, 3));
  };

  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev - 0.25, 0.5));
  };

  const handleResetZoom = () => {
    setZoom(1);
  };

  // 计算统计信息
  const stats = {
    total: groups.length,
    occupied: groups.filter(g => g.hall && g.binding?.is_active).length,
    vacant: groups.filter(g => !g.hall || !g.binding?.is_active).length,
    totalRevenue: groups.reduce((sum, g) => sum + (g.monthly_revenue || 0), 0)
  };

  return (
    <div className="w-full p-4 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">柜组地图</h1>
          <p className="text-muted-foreground mt-2">
            在地图上查看柜组分布和详细信息
          </p>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-base font-medium">总柜组数</CardTitle>
            <Building2 className="h-5 w-5 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{stats.total}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-base font-medium">已分配</CardTitle>
            <Users className="h-5 w-5 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600">{stats.occupied}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-base font-medium">未分配</CardTitle>
            <MapPin className="h-5 w-5 text-yellow-600" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-yellow-600">{stats.vacant}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-base font-medium">总收益</CardTitle>
            <Building2 className="h-5 w-5 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-blue-600">¥{stats.totalRevenue.toLocaleString()}</div>
          </CardContent>
        </Card>
      </div>

      {/* 筛选和搜索 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Filter className="h-5 w-5" />
            筛选和搜索
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                <Input
                  placeholder="搜索柜组名称、编码或品牌..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 text-base"
                />
              </div>
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full sm:w-48 text-base">
                <SelectValue placeholder="选择状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部状态</SelectItem>
                <SelectItem value="occupied">已分配</SelectItem>
                <SelectItem value="vacant">未分配</SelectItem>
              </SelectContent>
            </Select>
            <Select value={storeFilter} onValueChange={setStoreFilter}>
              <SelectTrigger className="w-full sm:w-48 text-base">
                <SelectValue placeholder="选择门店" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部门店</SelectItem>
                {stores.map(store => (
                  <SelectItem key={store.storeId} value={store.storeId.toString()}>
                    {store.storeName}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              variant={showInactive ? "default" : "outline"}
              onClick={() => setShowInactive(!showInactive)}
              className="w-full sm:w-auto"
            >
              {showInactive ? <EyeOff className="h-4 w-4 mr-2" /> : <Eye className="h-4 w-4 mr-2" />}
              {showInactive ? "隐藏非活跃" : "显示非活跃"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 地图区域 */}
      <Card className="h-[600px]">
        <CardHeader>
          <CardTitle className="text-lg">柜组分布图 ({filteredGroups.length} 个)</CardTitle>
        </CardHeader>
        <CardContent className="h-full p-0">
          {isLoading ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                <p className="text-gray-500 mt-2">加载中...</p>
              </div>
            </div>
          ) : (
            <div className="relative h-full bg-gray-100 rounded-lg overflow-hidden">
              {/* 缩放控制 */}
              <div className="absolute top-4 right-4 z-10">
                <div className="bg-white rounded-lg shadow-lg border border-slate-200 p-2 space-y-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={handleZoomIn}
                    className="w-8 h-8 p-0"
                  >
                    <ZoomIn className="h-4 w-4" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={handleZoomOut}
                    className="w-8 h-8 p-0"
                  >
                    <ZoomOut className="h-4 w-4" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={handleResetZoom}
                    className="w-8 h-8 p-0"
                  >
                    <RotateCcw className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {/* 地图内容 */}
              <div 
                className="w-full h-full transition-transform duration-200"
                style={{ transform: `scale(${zoom})` }}
              >
                {/* 背景网格 */}
                <div className="absolute inset-0 opacity-20">
                  <svg className="w-full h-full">
                    <defs>
                      <pattern id="grid" width="50" height="50" patternUnits="userSpaceOnUse">
                        <path d="M 50 0 L 0 0 0 50" fill="none" stroke="#ccc" strokeWidth="1"/>
                      </pattern>
                    </defs>
                    <rect width="100%" height="100%" fill="url(#grid)" />
                  </svg>
                </div>

                {/* 柜组标记 */}
                {filteredGroups.map((group) => {
                  const statusInfo = getStatusInfo(group);
                  const hall = group.hall;
                  const hasPosition = hall?.position_data;
                  
                  if (!hasPosition) return null;

                  const { x, y, width, height } = hasPosition;
                  
                  return (
                    <div
                      key={group.group_id}
                      className={`absolute border-2 rounded cursor-pointer transition-all duration-200 hover:scale-105 hover:brightness-110 ${
                        statusInfo.className
                      } ${
                        group.hall && group.binding?.is_active 
                          ? 'bg-green-100 border-green-500' 
                          : 'bg-yellow-100 border-yellow-500'
                      }`}
                      style={{
                        top: `${y}%`,
                        left: `${x}%`,
                        width: `${width}%`,
                        height: `${height}%`,
                        zIndex: 10
                      }}
                      onClick={() => handleGroupClick(group)}
                    >
                      <div className="absolute inset-0 flex items-center justify-center">
                        <div className="text-center">
                          <div className="text-xs font-semibold bg-white px-2 py-1 rounded shadow">
                            {group.group_code}
                          </div>
                          <div className="text-xs text-gray-600 mt-1">
                            {group.group_name}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}

                {/* 无位置数据的柜组列表 */}
                <div className="absolute bottom-4 left-4 max-w-xs">
                  <div className="bg-white rounded-lg shadow-lg border border-slate-200 p-4">
                    <h3 className="text-sm font-semibold text-slate-900 mb-2">无位置信息</h3>
                    <div className="space-y-1 max-h-40 overflow-y-auto">
                      {filteredGroups
                        .filter(group => !group.hall?.position_data)
                        .map(group => {
                          const statusInfo = getStatusInfo(group);
                          return (
                            <div
                              key={group.group_id}
                              className="p-2 rounded cursor-pointer transition-all duration-200 border bg-slate-50 border-slate-200 hover:bg-slate-100"
                              onClick={() => handleGroupClick(group)}
                            >
                              <div className="flex items-center justify-between">
                                <div>
                                  <div className="text-sm font-semibold text-slate-900">
                                    {group.group_code}
                                  </div>
                                  <div className="text-xs text-slate-600">
                                    {group.group_name}
                                  </div>
                                </div>
                                <Badge className={statusInfo.className}>
                                  {statusInfo.label}
                                </Badge>
                              </div>
                            </div>
                          );
                        })}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 柜组详情模态框 */}
      <Dialog open={isDetailModalOpen} onOpenChange={setIsDetailModalOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>柜组详细信息</DialogTitle>
          </DialogHeader>
          {selectedGroup && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-gray-500">柜组编码</label>
                  <p className="text-lg font-semibold">{selectedGroup.group_code}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">柜组名称</label>
                  <p className="text-lg font-semibold">{selectedGroup.group_name}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">部门编码</label>
                  <p className="text-base">{selectedGroup.department_code || '-'}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">部门名称</label>
                  <p className="text-base">{selectedGroup.department_name || '-'}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">经营方式</label>
                  <p className="text-base">{formatOperationMethod(selectedGroup.operation_method)}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">品牌名称</label>
                  <p className="text-base">{selectedGroup.brand_name || '-'}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">月收益</label>
                  <p className="text-base font-semibold text-green-600">
                    ¥{selectedGroup.monthly_revenue?.toLocaleString() || '0'}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">状态</label>
                  <Badge className={getStatusInfo(selectedGroup).className}>
                    {getStatusInfo(selectedGroup).label}
                  </Badge>
                </div>
              </div>

              {selectedGroup.hall && (
                <div className="border-t pt-4">
                  <h3 className="text-lg font-semibold mb-2">关联厅房信息</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm font-medium text-gray-500">厅房编码</label>
                      <p className="text-base">{selectedGroup.hall.hall_code}</p>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-500">厅房名称</label>
                      <p className="text-base">{selectedGroup.hall.hall_name || '-'}</p>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-500">柜位编号</label>
                      <p className="text-base">{selectedGroup.hall.counter_number}</p>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-500">面积</label>
                      <p className="text-base">{selectedGroup.hall.area ? `${selectedGroup.hall.area}㎡` : '-'}</p>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-500">门店</label>
                      <p className="text-base">{getStoreName(selectedGroup.hall.store_id)}</p>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-500">绑定时间</label>
                      <p className="text-base">
                        {selectedGroup.binding?.bound_at ? 
                          new Date(selectedGroup.binding.bound_at).toLocaleDateString() : 
                          '-'
                        }
                      </p>
                    </div>
                  </div>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button variant="outline" onClick={() => setIsDetailModalOpen(false)}>
                  关闭
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
