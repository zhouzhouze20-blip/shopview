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
      
      <div className="h-full p-4">
        <FloorPlan 
          onRoomClick={handleRoomClick}
          viewMode={viewMode}
          searchQuery={searchQuery}
          selectedStoreId={selectedStoreId}
          data-testid="floor-plan"
        />
      </div>
    </div>
  );
}
