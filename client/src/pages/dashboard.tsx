import { useState } from "react";
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

  const handleRoomClick = (room: Room) => {
    setSelectedRoom(room);
  };

  const handleCloseModal = () => {
    setSelectedRoom(null);
  };

  return (
    <div className="min-h-screen bg-slate-50" data-testid="dashboard">
      <Header 
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        selectedStoreId={selectedStoreId}
        data-testid="header"
      />
      
      <div className="flex h-screen overflow-hidden">
        <Sidebar selectedRoom={null} data-testid="sidebar" />
        
        <main className="flex-1 overflow-hidden" data-testid="main-content">
          <div className="h-full flex flex-col">
            <div className="p-6 border-b border-slate-200 bg-white">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-slate-900" data-testid="text-floor-plan-title">
                  厅房平面图可视化
                </h2>
                <div className="flex items-center space-x-4">
                  <select 
                    className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    value={viewMode}
                    onChange={(e) => setViewMode(e.target.value as "revenue" | "occupancy" | "lease")}
                    data-testid="select-view-mode"
                  >
                    <option value="revenue">收费视图</option>
                    <option value="occupancy">占用视图</option>
                    <option value="lease">租期视图</option>
                  </select>
                  <button className="text-slate-600 hover:text-slate-900 p-2" data-testid="button-fullscreen">
                    <i className="fas fa-expand"></i>
                  </button>
                </div>
              </div>
            </div>

            <div className="flex-1 bg-slate-50">
              {/* 平面图上方信息区域 */}
              <div className="p-6 bg-white border-b border-slate-200">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* 当前楼层平面图信息 */}
                  <div className="bg-slate-50 rounded-lg p-4">
                    <h3 className="font-semibold text-slate-900 mb-2">当前楼层平面图</h3>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-slate-600">商场 1层</span>
                      <Badge className="bg-success text-white">激活</Badge>
                    </div>
                    <div className="text-xs text-slate-500">最后更新: 2024-01-15</div>
                  </div>

                  {/* 快速统计 */}
                  <div className="bg-slate-50 rounded-lg p-4">
                    <h3 className="font-semibold text-slate-900 mb-2">快速统计</h3>
                    {statsQuery.data ? (
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-600">总房间数</span>
                          <span className="font-semibold">{statsQuery.data.totalRooms}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-600">已出租</span>
                          <span className="font-semibold text-green-600">{statsQuery.data.occupied}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-600">空置</span>
                          <span className="font-semibold text-orange-600">{statsQuery.data.vacant}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-600">平均收费</span>
                          <span className="font-semibold text-blue-600">¥{Math.round(statsQuery.data.avgRevenue)}/m²</span>
                        </div>
                      </div>
                    ) : (
                      <div className="text-sm text-slate-500">加载中...</div>
                    )}
                  </div>

                  {/* 房间详细信息 */}
                  {selectedRoom ? (
                    <div className="bg-slate-50 rounded-lg p-4">
                      <h3 className="font-semibold text-slate-900 mb-2">房间详细信息</h3>
                      <div className="space-y-2">
                        <div>
                          <span className="text-xs text-slate-600">房间号: </span>
                          <span className="text-sm font-medium text-slate-900">{selectedRoom.roomNumber}</span>
                        </div>
                        <div>
                          <span className="text-xs text-slate-600">名称: </span>
                          <span className="text-sm text-slate-900">{selectedRoom.name}</span>
                        </div>
                        <div>
                          <span className="text-xs text-slate-600">面积: </span>
                          <span className="text-sm text-slate-900">{selectedRoom.area} m²</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-slate-600">状态: </span>
                          <Badge 
                            variant={selectedRoom.status === 'occupied' ? 'default' : 
                                    selectedRoom.status === 'vacant' ? 'destructive' : 'secondary'}
                            className="text-xs"
                          >
                            {selectedRoom.status === 'occupied' ? '已占用' : 
                             selectedRoom.status === 'vacant' ? '空置' : '维护中'}
                          </Badge>
                        </div>
                        <div>
                          <span className="text-xs text-slate-600">月收入: </span>
                          <span className="text-sm font-semibold text-green-600">¥{parseFloat(selectedRoom.monthlyRevenue || '0').toLocaleString()}</span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="bg-slate-50 rounded-lg p-4 flex items-center justify-center">
                      <p className="text-sm text-slate-500">点击房间查看详细信息</p>
                    </div>
                  )}
                </div>
              </div>

              {/* 平面图区域 */}
              <div className="p-6">
                <FloorPlan 
                  onRoomClick={handleRoomClick}
                  viewMode={viewMode}
                  searchQuery={searchQuery}
                  selectedStoreId={selectedStoreId}
                  data-testid="floor-plan"
                />
              </div>
            </div>
          </div>
        </main>
      </div>
      
    </div>
  );
}
