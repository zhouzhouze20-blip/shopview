import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Header from "@/components/header";
import Sidebar from "@/components/sidebar";
import SimpleFloorPlan from "@/components/simple-floor-plan";
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
      <SimpleFloorPlan />
    </div>
  );
}
