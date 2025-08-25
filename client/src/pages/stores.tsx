import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Link, useLocation } from "wouter";
import { Store } from "@shared/schema";
import { Building2, Users, MapPin, Phone, Mail, User } from "lucide-react";

interface StoreStats {
  totalRooms: number;
  occupied: number;
  vacant: number;
  avgRevenue: number;
}

export default function StoresPage() {
  const [location, setLocation] = useLocation();

  const { data: stores, isLoading } = useQuery<Store[]>({
    queryKey: ['/api/stores'],
  });

  const { data: statsData, isLoading: isLoadingStats } = useQuery<{[key: number]: StoreStats}>({
    queryKey: ['/api/stores/stats'],
    queryFn: async () => {
      if (!stores) return {};
      
      const stats: {[key: number]: StoreStats} = {};
      
      // 获取每个门店的统计数据
      await Promise.all(
        stores.map(async (store) => {
          try {
            const response = await fetch(`/api/stats?storeId=${store.storeId}`);
            if (response.ok) {
              stats[store.storeId] = await response.json();
            }
          } catch (error) {
            console.error(`Failed to fetch stats for store ${store.storeId}:`, error);
          }
        })
      );
      
      return stats;
    },
    enabled: !!stores,
  });

  const handleStoreSelect = (storeId: number) => {
    // 导航到主页面并传递选中的门店ID
    setLocation(`/dashboard?storeId=${storeId}`);
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

  // 调试信息
  console.log('门店数据:', stores);
  console.log('是否加载中:', isLoading);

  return (
    <div className="container mx-auto p-6 space-y-6" data-testid="stores-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">门店管理</h1>
          <p className="text-muted-foreground mt-2">
            选择门店进入管理系统，查看各门店的运营情况
          </p>
        </div>
      </div>

      {/* 调试信息显示 */}
      <div className="bg-yellow-100 p-4 rounded-lg">
        <h3 className="font-bold">调试信息:</h3>
        <p>门店数量: {stores?.length || 0}</p>
        <p>加载状态: {isLoading ? '加载中' : '已完成'}</p>
        <p>数据: {JSON.stringify(stores)}</p>
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
                const stats = statsData?.[store.storeId];
                const occupancyRate = stats ? Math.round((stats.occupied / stats.totalRooms) * 100) : 0;
                
                return (
                  <TableRow key={store.storeId} data-testid={`row-store-${store.storeId}`}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <Building2 className="h-4 w-4 text-blue-600" />
                        {store.storeName}
                      </div>
                    </TableCell>
                    <TableCell>{store.storeCode}</TableCell>
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
                      <Badge variant={store.isActive ? "default" : "secondary"}>
                        {store.isActive ? "运营中" : "暂停"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex gap-2 justify-end">
                        <Button 
                          size="sm"
                          onClick={() => handleStoreSelect(store.storeId)}
                          data-testid={`button-enter-store-${store.storeId}`}
                        >
                          进入管理
                        </Button>
                        <Button 
                          size="sm"
                          variant="outline" 
                          onClick={() => setLocation(`/dashboard?storeId=${store.storeId}&view=rooms`)}
                          data-testid={`button-view-rooms-${store.storeId}`}
                        >
                          查看厅房
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