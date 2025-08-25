import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Link, useLocation } from "wouter";
import { Store } from "@shared/schema";
import { Building2, Upload, Image } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface StoreStats {
  totalRooms: number;
  occupied: number;
  vacant: number;
  avgRevenue: number;
}

export default function StoresPage() {
  const [location, setLocation] = useLocation();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const { toast } = useToast();
  const queryClient = useQueryClient();

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

  // 上传平面图
  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      // 获取上传URL
      const uploadResponse = await fetch('/api/objects/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      
      if (!uploadResponse.ok) throw new Error('获取上传URL失败');
      
      const { uploadURL } = await uploadResponse.json();
      
      // 上传文件
      const uploadFileResponse = await fetch(uploadURL, {
        method: 'PUT',
        body: file,
        headers: {
          'Content-Type': file.type,
        },
      });
      
      if (!uploadFileResponse.ok) throw new Error('文件上传失败');
      
      return { uploadURL };
    },
    onSuccess: (data) => {
      toast({
        title: "上传成功！",
        description: "平面图已上传，请刷新页面查看效果"
      });
      setSelectedFile(null);
      queryClient.invalidateQueries({ queryKey: ['/api/floor-plans'] });
    },
    onError: (error) => {
      toast({
        title: "上传失败",
        description: error.message,
        variant: "destructive"
      });
    }
  });

  const handleFileUpload = () => {
    if (selectedFile) {
      uploadMutation.mutate(selectedFile);
    }
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

      {/* 平面图上传功能 */}
      <div className="bg-blue-50 border border-blue-200 p-4 rounded-lg">
        <h3 className="font-bold text-blue-800 mb-3 flex items-center gap-2">
          <Image className="h-5 w-5" />
          平面图上传
        </h3>
        <div className="flex items-center gap-4">
          <Input
            type="file"
            accept="image/*"
            onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
            className="flex-1"
          />
          <Button 
            onClick={handleFileUpload}
            disabled={!selectedFile || uploadMutation.isPending}
            className="flex items-center gap-2"
          >
            <Upload className="h-4 w-4" />
            {uploadMutation.isPending ? '上传中...' : '上传平面图'}
          </Button>
        </div>
        <p className="text-sm text-blue-600 mt-2">
          💡 支持 JPG、PNG、SVG 格式，建议尺寸 1920x1080 或更高
        </p>
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