import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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

      {/* 门店网格 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-6">
        {stores?.map((store) => {
          const stats = statsData?.[store.storeId];
          const occupancyRate = stats ? Math.round((stats.occupied / stats.totalRooms) * 100) : 0;
          
          return (
            <Card 
              key={store.storeId} 
              className="hover:shadow-lg transition-shadow cursor-pointer border-l-4 border-l-blue-500"
              onClick={() => handleStoreSelect(store.storeId)}
              data-testid={`store-card-${store.storeId}`}
            >
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-xl flex items-center gap-2">
                    <Building2 className="h-5 w-5 text-blue-600" />
                    {store.storeName}
                  </CardTitle>
                  <Badge variant={store.isActive ? "default" : "secondary"}>
                    {store.isActive ? "运营中" : "暂停"}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground">
                  门店代码: {store.storeCode}
                </p>
              </CardHeader>

              <CardContent className="space-y-4">
                {/* 门店地址 */}
                {store.address && (
                  <div className="flex items-center gap-2 text-sm">
                    <MapPin className="h-4 w-4 text-gray-500" />
                    <span>{store.address}</span>
                  </div>
                )}

                {/* 联系信息 */}
                <div className="space-y-2">
                  {store.managerName && (
                    <div className="flex items-center gap-2 text-sm">
                      <User className="h-4 w-4 text-gray-500" />
                      <span>负责人: {store.managerName}</span>
                    </div>
                  )}
                  {store.contactPhone && (
                    <div className="flex items-center gap-2 text-sm">
                      <Phone className="h-4 w-4 text-gray-500" />
                      <span>{store.contactPhone}</span>
                    </div>
                  )}
                  {store.contactEmail && (
                    <div className="flex items-center gap-2 text-sm">
                      <Mail className="h-4 w-4 text-gray-500" />
                      <span className="text-blue-600">{store.contactEmail}</span>
                    </div>
                  )}
                </div>

                {/* 运营统计 */}
                {stats && !isLoadingStats ? (
                  <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 space-y-2">
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-gray-600">总厅房数</span>
                      <span className="font-medium">{stats.totalRooms}</span>
                    </div>
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-gray-600">出租率</span>
                      <span className="font-medium text-green-600">
                        {occupancyRate}%
                      </span>
                    </div>
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-gray-600">已租/空置</span>
                      <span className="font-medium">
                        {stats.occupied} / {stats.vacant}
                      </span>
                    </div>
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-gray-600">平均收益</span>
                      <span className="font-medium">¥{stats.avgRevenue.toLocaleString()}</span>
                    </div>
                  </div>
                ) : isLoadingStats ? (
                  <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 text-center text-sm text-gray-500">
                    加载统计数据中...
                  </div>
                ) : null}

                {/* 操作按钮 */}
                <div className="flex gap-2 pt-2">
                  <Button 
                    onClick={(e) => {
                      e.stopPropagation();
                      handleStoreSelect(store.storeId);
                    }}
                    className="flex-1"
                    data-testid={`button-enter-store-${store.storeId}`}
                  >
                    进入管理
                  </Button>
                  <Button 
                    variant="outline" 
                    onClick={(e) => {
                      e.stopPropagation();
                      setLocation(`/dashboard?storeId=${store.storeId}&view=rooms`);
                    }}
                    data-testid={`button-view-rooms-${store.storeId}`}
                  >
                    查看厅房
                  </Button>
                </div>
              </CardContent>
            </Card>
          );
        })}
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