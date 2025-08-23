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
        <Sidebar selectedRoom={selectedRoom} data-testid="sidebar" />
        
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

            <div className="flex-1 p-6 bg-slate-50">
              <FloorPlan 
                onRoomClick={handleRoomClick}
                viewMode={viewMode}
                searchQuery={searchQuery}
                selectedStoreId={selectedStoreId}
                data-testid="floor-plan"
              />
            </div>
          </div>
        </main>
      </div>
      
    </div>
  );
}
