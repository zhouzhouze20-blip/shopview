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
        <Sidebar data-testid="sidebar" />
        
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

            <div className="flex-1 flex bg-slate-50">
              {/* 左侧详细信息面板 */}
              <div className="w-80 p-4 bg-white border-r border-slate-200">
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-slate-900">图例说明</h3>
                  
                  {/* 图例 */}
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <div className="w-4 h-4 bg-green-200 border border-green-400 rounded"></div>
                      <span className="text-sm text-slate-600">已占用</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="w-4 h-4 bg-red-200 border border-red-400 rounded"></div>
                      <span className="text-sm text-slate-600">空置</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="w-4 h-4 bg-yellow-200 border border-yellow-400 rounded"></div>
                      <span className="text-sm text-slate-600">维护中</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="w-4 h-4 bg-green-100 border-2 border-green-500 rounded"></div>
                      <span className="text-sm text-slate-600">用户标记房间</span>
                    </div>
                  </div>
                  
                  {/* 房间详细信息 */}
                  {selectedRoom ? (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">房间详细信息</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <div>
                          <label className="text-sm font-medium text-slate-600">房间号</label>
                          <p className="text-sm text-slate-900">{selectedRoom.roomNumber}</p>
                        </div>
                        
                        <div>
                          <label className="text-sm font-medium text-slate-600">房间名称</label>
                          <p className="text-sm text-slate-900">{selectedRoom.name}</p>
                        </div>
                        
                        <div>
                          <label className="text-sm font-medium text-slate-600">面积</label>
                          <p className="text-sm text-slate-900">{selectedRoom.area} m²</p>
                        </div>
                        
                        <div>
                          <label className="text-sm font-medium text-slate-600">状态</label>
                          <div className="mt-1">
                            <Badge 
                              variant={selectedRoom.status === 'occupied' ? 'default' : 
                                      selectedRoom.status === 'vacant' ? 'destructive' : 'secondary'}
                            >
                              {selectedRoom.status === 'occupied' ? '已占用' : 
                               selectedRoom.status === 'vacant' ? '空置' : '维护中'}
                            </Badge>
                          </div>
                        </div>
                        
                        {selectedRoom.tenant && (
                          <div>
                            <label className="text-sm font-medium text-slate-600">租户</label>
                            <p className="text-sm text-slate-900">{selectedRoom.tenant}</p>
                          </div>
                        )}
                        
                        <div>
                          <label className="text-sm font-medium text-slate-600">月收入</label>
                          <p className="text-sm text-slate-900">¥{parseFloat(selectedRoom.monthlyRevenue).toLocaleString()}</p>
                        </div>
                        
                        <div>
                          <label className="text-sm font-medium text-slate-600">单价/m²</label>
                          <p className="text-sm text-slate-900">¥{parseFloat(selectedRoom.revenuePerSqm).toLocaleString()}</p>
                        </div>
                        
                        {selectedRoom.leaseExpiry && (
                          <div>
                            <label className="text-sm font-medium text-slate-600">租期到期</label>
                            <p className="text-sm text-slate-900">{new Date(selectedRoom.leaseExpiry).toLocaleDateString('zh-CN')}</p>
                          </div>
                        )}
                        
                        {selectedRoom.contractType && (
                          <div>
                            <label className="text-sm font-medium text-slate-600">合同类型</label>
                            <p className="text-sm text-slate-900">{selectedRoom.contractType}</p>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ) : (
                    <div className="text-center py-8">
                      <p className="text-sm text-slate-500">点击房间查看详细信息</p>
                    </div>
                  )}
                </div>
              </div>
              
              {/* 右侧平面图 */}
              <div className="flex-1 p-6">
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
