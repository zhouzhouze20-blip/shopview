import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useLocation } from "wouter";
import { Building2 } from "lucide-react";
import { useStore } from "@/contexts/StoreContext";

interface StoreStats {
  totalRooms: number;
  occupied: number;
  vacant: number;
  avgRevenue: number;
}

export default function StoresPage() {
  const [location, setLocation] = useLocation();
  
  // 使用全局门店状态
  const { stores, isLoading, error, refetch, setSelectedStoreId } = useStore();

  console.log('当前状态:', { isLoading, error, stores: stores?.length });

  // 暂时禁用统计API调用，因为后端没有这个端点
  const statsData: {[key: number]: StoreStats} = {};
  const isLoadingStats = false;

  const handleStoreSelect = (storeId: number) => {
    // 设置全局门店状态
    setSelectedStoreId(storeId);
    // 导航到主页面
    setLocation('/dashboard');
  };

  if (isLoading) {
    return (
      <div className="container mx-auto p-6" data-testid="stores-loading">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-lg">正在加载门店信息...</div>
        </div>
      </div>
    );
  }

  if (error) {
    const isConnectionRefused =
      error?.message?.includes('Failed to fetch') ||
      error?.message?.includes('NetworkError') ||
      error?.message?.includes('ERR_CONNECTION_REFUSED');
    return (
      <div className="container mx-auto p-6" data-testid="stores-error">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center max-w-md">
            <div className="text-lg text-red-600 mb-2">门店列表加载失败</div>
            {isConnectionRefused ? (
              <>
                <p className="text-sm text-gray-600 mb-2">
                  无法连接到后端 API（端口 8000），请先在终端启动本项目的 Python 后端服务。
                </p>
                <p className="text-xs text-gray-500 font-mono bg-slate-100 p-3 rounded mb-4 text-left break-all">
                  cd python_app && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
                </p>
              </>
            ) : (
              <div className="text-sm text-gray-500 mb-4">{String(error)}</div>
            )}
            <Button onClick={() => refetch()} className="mt-2">
              重新加载
            </Button>
          </div>
        </div>
      </div>
    );
  }


  return (
    <div className="container mx-auto p-6 space-y-6" data-testid="stores-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">门店管理</h1>
          <p className="text-muted-foreground mt-2">
            选择门店进入管理系统，查看各门店的运营情况
          </p>
        </div>
        <div className="flex gap-2">
          <Button 
            variant="outline"
            onClick={() => refetch()}
            disabled={isLoading}
          >
            {isLoading ? '加载中...' : '刷新数据'}
          </Button>
        </div>
      </div>


      {/* 门店表格 */}
      <div className="bg-white rounded-lg shadow-sm border border-slate-200">
        {stores && stores.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>门店名称</TableHead>
                <TableHead>门店代码</TableHead>
                <TableHead>总厅房数</TableHead>
                <TableHead>出租率</TableHead>
                <TableHead>平均收益</TableHead>
                <TableHead>状态</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {stores.map((store) => {
                // 使用正确的字段名
                const storeId = store.storeId;
                const storeName = store.storeName;
                const storeCode = store.storeCode;
                const isActive = store.isActive;
                
                const stats = statsData?.[storeId];
                const occupancyRate = stats ? Math.round((stats.occupied / stats.totalRooms) * 100) : 0;
                
                return (
                  <TableRow key={storeId} data-testid={`row-store-${storeId}`}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <Building2 className="h-4 w-4 text-blue-600" />
                        {storeName}
                      </div>
                    </TableCell>
                    <TableCell>{storeCode}</TableCell>
                    <TableCell>
                      {stats && !isLoadingStats ? stats.totalRooms : '-'}
                    </TableCell>
                    <TableCell>
                      {stats && !isLoadingStats ? (
                        <span className="font-medium text-green-600">
                          {occupancyRate}%
                        </span>
                      ) : isLoadingStats ? (
                        <span className="text-gray-500">加载中...</span>
                      ) : '-'}
                    </TableCell>
                    <TableCell>
                      {stats && !isLoadingStats ? (
                        <span className="font-medium">
                          ¥{stats.avgRevenue.toLocaleString()}
                        </span>
                      ) : isLoadingStats ? (
                        <span className="text-gray-500">加载中...</span>
                      ) : '-'}
                    </TableCell>
                    <TableCell>
                      <Badge variant={isActive ? "default" : "secondary"}>
                        {isActive ? "运营中" : "暂停"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex gap-2 justify-end">
                        <Button 
                          size="sm"
                          onClick={() => handleStoreSelect(storeId)}
                          data-testid={`button-enter-store-${storeId}`}
                        >
                          进入管理
                        </Button>
                        <Button 
                          size="sm"
                          variant="outline" 
                          onClick={() => setLocation(`/dashboard?storeId=${storeId}&view=counters`)}
                          data-testid={`button-view-rooms-${storeId}`}
                        >
                          查看柜位
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        ) : (
          <div className="p-8 text-center">
            <div className="text-lg text-slate-500">暂无门店数据</div>
          </div>
        )}
      </div>

      {/* 空状态 */}
      {stores && stores.length === 0 && (
        <div className="text-center py-12" data-testid="stores-empty-state">
          <Building2 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
            暂无门店信息
          </h3>
          <p className="text-gray-500 dark:text-gray-400">
            请联系系统管理员配置门店信息
          </p>
        </div>
      )}
    </div>
  );
}
