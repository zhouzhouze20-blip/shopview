import { useState, useEffect, useRef, Component, ReactNode } from "react";
import { useLocation } from "wouter";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import NavigationSidebar from "@/components/navigation-sidebar";
import BaseMapsPage from "@/pages/base-maps";
import UnitMapVersionsPage from "@/pages/unit-map-versions";
import BusinessUnitsPage from "@/pages/business-units";
import FloorAreaReportPage from "@/pages/floor-area-report";
import Dashboard from "./dashboard";
import TenantsPage from "./tenants";
import CountersPage from "./counters";
import FloorsPage from "./floors";
import CounterRevenueMapPage from "./counter-revenue-map";
import ContractsPage from "./contracts";
import ManaframePage from "./manaframe";
import SuppliersPage from "./suppliers";
import SystemConfigPage from "./system-config";
import DecorationsPage from "./decorations";
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
import { useStore } from "@/contexts/StoreContext";
import { useAuth } from "@/contexts/AuthContext";
import { Building2, Users, FileText, CreditCard, BarChart3, TrendingUp, Calendar, CheckCircle, Clock, Plus, Edit, Trash2, Upload, Image } from "lucide-react";

// 内容区错误边界：捕获切换时的 removeChild 等错误，避免整页白屏
class ContentErrorBoundary extends Component<{ children: ReactNode; activeModule: string }> {
  state = { hasError: false };
  static getDerivedStateFromError() {
    return { hasError: true };
  }
  componentDidUpdate(prev: { activeModule: string }) {
    if (prev.activeModule !== this.props.activeModule && this.state.hasError) {
      this.setState({ hasError: false });
    }
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 text-center text-slate-600">
          <p className="mb-2">页面切换时出现异常</p>
          <Button variant="outline" size="sm" onClick={() => this.setState({ hasError: false })}>
            重试
          </Button>
        </div>
      );
    }
    return this.props.children;
  }
}

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
              <p className="text-sm text-slate-600">收益仪表盘、厅房管理、空间资产</p>
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

export default function MainDashboard() {
  const [activeModule, setActiveModule] = useState("dashboard");
  const [location] = useLocation();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const hasSyncedUrlRef = useRef(false);
  const { user, logout } = useAuth();

  // 使用全局门店状态
  const { selectedStoreId } = useStore();

  // 仅首次进入本页时根据 URL 设置模块，之后不再覆盖用户点击的菜单
  useEffect(() => {
    if (hasSyncedUrlRef.current) return;
    hasSyncedUrlRef.current = true;
    const params = new URLSearchParams(window.location.search);
    const viewParam = params.get('view');
    if (viewParam) {
      if (viewParam === 'rooms') {
        setActiveModule('floor-plan');
      } else {
        setActiveModule(viewParam);
      }
    }
  }, []);

  const renderContent = () => {
    switch (activeModule) {
      case "dashboard":
        return <SystemOverview />;
      case "floor-plan":
        return <Dashboard selectedStoreId={selectedStoreId ?? undefined} />;
      case "counter-revenue-map":
        return <CounterRevenueMapPage />;
      case "counters":
        return <CountersPage />;
      case "halls":
        return <HallsPage selectedStoreId={selectedStoreId ?? undefined} />;
      case "tenants":
        return <TenantsPage selectedStoreId={selectedStoreId ?? undefined} />;
      case "floors":
        return <FloorsPage />;
      case "base-maps":
        return <BaseMapsPage />;
      case "unit-map-versions":
        return <UnitMapVersionsPage />;
      case "business-units":
        return <BusinessUnitsPage />;
      case "floor-area-report":
        return <FloorAreaReportPage />;
      case "brands":
        return <BrandsPage />;
      case "suppliers":
        return <SuppliersPage />;
      case "manaframe":
        return <ManaframePage />;
      case "contracts":
        return <ContractsPage />;
      case "decorations":
        return <DecorationsPage initialTab="projects" />;
      case "decorations-todos":
        return <DecorationsPage initialTab="todos" />;
      case "bills":
        return <FinancialPage />;
      case "users":
        return <SystemConfigPage initialTab="users" />;
      case "roles":
        return <SystemConfigPage initialTab="roles" />;
      default:
        return <SystemOverview />;
    }
  };

  const handleToggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  const { toast } = useToast();

  const exitFullscreenSafely = () => {
    if (!document.fullscreenElement) return Promise.resolve(true);

    return new Promise<boolean>((resolve) => {
      let settled = false;
      let timeoutId: number | undefined;

      const finish = (result: boolean) => {
        if (settled) return;
        settled = true;
        if (timeoutId !== undefined) window.clearTimeout(timeoutId);
        document.removeEventListener("fullscreenchange", handleFullscreenChange);
        resolve(result);
      };

      const handleFullscreenChange = () => {
        if (!document.fullscreenElement) finish(true);
      };

      document.addEventListener("fullscreenchange", handleFullscreenChange);
      timeoutId = window.setTimeout(() => {
        finish(!document.fullscreenElement);
      }, 1500);

      try {
        const result = document.exitFullscreen();
        if (result && typeof result.then === "function") {
          result.catch(() => finish(!document.fullscreenElement));
        }
      } catch {
        finish(!document.fullscreenElement);
      }
    });
  };

  // 切换模块：非全屏时直接切换；全屏时先退出全屏再切换
  const handleModuleChange = async (moduleId: string) => {
    if (document.fullscreenElement) {
      const exited = await exitFullscreenSafely();
      if (!exited) {
        toast({
          title: "请先退出全屏",
          description: "当前全屏未能自动退出，请按 Esc 退出全屏后再切换模块。",
          variant: "destructive",
        });
        return;
      }
    }
    setActiveModule(moduleId);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex" data-testid="main-dashboard">
      <NavigationSidebar 
        activeModule={activeModule} 
        onModuleChange={handleModuleChange}
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={handleToggleSidebar}
      />
      <main className="flex-1 overflow-auto" data-testid="main-content">
        {/* 顶部栏：仅显示系统标题 */}
        <div className="bg-white border-b px-6 py-4 flex items-center justify-end">
          <div className="flex items-center gap-4">
            <div className="text-right">
              <div className="text-sm font-medium text-slate-900">{user?.real_name || user?.username}</div>
              <div className="text-xs text-muted-foreground">{user?.role_names?.join(" / ") || "已登录"}</div>
            </div>
            <Button variant="outline" size="sm" onClick={() => logout()}>
              退出登录
            </Button>
          </div>
        </div>

        {/* key 强制按模块完整卸载再挂载；错误边界兜底 removeChild 等异常 */}
        <ContentErrorBoundary activeModule={activeModule}>
          <div key={activeModule} className="min-h-0 flex-1">
            {renderContent()}
          </div>
        </ContentErrorBoundary>
      </main>
    </div>
  );
}
