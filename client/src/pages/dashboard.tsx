import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Header from "@/components/header";
import Sidebar from "@/components/sidebar";
import FloorPlan from "@/components/floor-plan";
import { Room } from "@shared/schema";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface DashboardProps {
  selectedStoreId?: number;
}

export default function Dashboard({ selectedStoreId }: DashboardProps) {
  const [selectedRoom, setSelectedRoom] = useState<Room | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [viewMode, setViewMode] = useState<"revenue" | "occupancy" | "lease">("revenue");

  const statsQuery = useQuery({
    queryKey: ['/api/stats'],
    enabled: !!selectedStoreId
  });

  const handleRoomClick = (room: Room) => {
    setSelectedRoom(room);
  };

  const handleCloseModal = () => {
    setSelectedRoom(null);
  };

  return (
    <div className="h-screen bg-slate-50">
      <div className="p-4 bg-white border-b border-slate-200">
        <h1 className="text-xl font-bold text-slate-900">厅房平面图管理</h1>
      </div>
      
      <div className="flex h-full">
        {/* 平面图区域 */}
        <div className="flex-1 p-4">
          <FloorPlan 
            onRoomClick={handleRoomClick}
            viewMode={viewMode}
            searchQuery={searchQuery}
            selectedStoreId={selectedStoreId}
            data-testid="floor-plan"
          />
        </div>
        
        {/* 详细信息面板 */}
        <div className="w-80 bg-white border-l border-slate-200 p-4">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">厅房详细信息</h2>
          
          {selectedRoom ? (
            <div className="space-y-4">
              <div className="bg-slate-50 rounded-lg p-4">
                <div className="space-y-3">
                  <div>
                    <label className="text-xs font-medium text-slate-600">厅房号</label>
                    <p className="text-sm text-slate-900 font-medium">{selectedRoom.roomNumber}</p>
                  </div>
                  
                  <div>
                    <label className="text-xs font-medium text-slate-600">厅房名称</label>
                    <p className="text-sm text-slate-900">{selectedRoom.name}</p>
                  </div>
                  
                  <div>
                    <label className="text-xs font-medium text-slate-600">面积</label>
                    <p className="text-sm text-slate-900">{selectedRoom.area} m²</p>
                  </div>
                  
                  <div>
                    <label className="text-xs font-medium text-slate-600">状态</label>
                    <div className="mt-1">
                      <Badge 
                        variant={selectedRoom.status === 'occupied' ? 'default' : 
                                selectedRoom.status === 'vacant' ? 'destructive' : 'secondary'}
                        className="text-xs"
                      >
                        {selectedRoom.status === 'occupied' ? '已占用' : 
                         selectedRoom.status === 'vacant' ? '空置' : '维护中'}
                      </Badge>
                    </div>
                  </div>

                  {selectedRoom.tenant && (
                    <div>
                      <label className="text-xs font-medium text-slate-600">租户</label>
                      <p className="text-sm text-slate-900">{selectedRoom.tenant}</p>
                    </div>
                  )}

                  <div>
                    <label className="text-xs font-medium text-slate-600">月收入</label>
                    <p className="text-sm text-slate-900 font-semibold text-green-600">
                      ¥{parseFloat(selectedRoom.monthlyRevenue || '0').toLocaleString()}
                    </p>
                  </div>

                  <div>
                    <label className="text-xs font-medium text-slate-600">每平米收费</label>
                    <p className="text-sm text-slate-900">¥{selectedRoom.revenuePerSqm}/m²</p>
                  </div>

                  {selectedRoom.leaseExpiry && (
                    <div>
                      <label className="text-xs font-medium text-slate-600">租约到期</label>
                      <p className="text-sm text-slate-900">{selectedRoom.leaseExpiry}</p>
                    </div>
                  )}

                  {selectedRoom.contractType && (
                    <div>
                      <label className="text-xs font-medium text-slate-600">合同类型</label>
                      <p className="text-sm text-slate-900">{selectedRoom.contractType}</p>
                    </div>
                  )}
                </div>
              </div>
              
              {/* 位置信息 */}
              <div className="bg-blue-50 rounded-lg p-4">
                <h3 className="text-sm font-semibold text-blue-900 mb-2">位置信息</h3>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-blue-600">X坐标:</span>
                    <span className="text-blue-900">{parseFloat(selectedRoom.x).toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-blue-600">Y坐标:</span>
                    <span className="text-blue-900">{parseFloat(selectedRoom.y).toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-blue-600">宽度:</span>
                    <span className="text-blue-900">{parseFloat(selectedRoom.width).toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-blue-600">高度:</span>
                    <span className="text-blue-900">{parseFloat(selectedRoom.height).toFixed(1)}%</span>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-slate-50 rounded-lg p-8 text-center">
              <div className="text-slate-400 mb-2">
                <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
              </div>
              <p className="text-sm text-slate-500">点击平面图上的厅房</p>
              <p className="text-xs text-slate-400 mt-1">查看详细信息</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
