import { useState, useEffect } from "react";
import { useLocation } from "wouter";
import NavigationSidebar from "@/components/navigation-sidebar";
import Dashboard from "./dashboard";
import TenantsPage from "./tenants";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StoreSelector } from "@/components/store-selector";
import { Building2, Users, FileText, CreditCard, BarChart3, TrendingUp, ArrowLeft } from "lucide-react";

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