import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect, useRef } from "react";
import { ZoomIn, ZoomOut, RotateCcw, Eye, EyeOff, Plus, Edit, Save, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Room } from "@shared/schema";
import { apiRequest } from "@/lib/queryClient";
import { toast } from "@/hooks/use-toast";

interface FloorPlanProps {
  onRoomClick: (room: Room) => void;
  viewMode: "revenue" | "occupancy" | "lease";
  searchQuery: string;
  selectedStoreId?: number;
}

interface RoomSelection {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  name?: string;
  points?: Array<{x: number, y: number}>; // 多边形顶点
  type: 'rectangle' | 'polygon';
}

export default function FloorPlan({ onRoomClick, viewMode, searchQuery, selectedStoreId }: FloorPlanProps) {
  const [zoom, setZoom] = useState(1);
  const [filteredRooms, setFilteredRooms] = useState<Room[]>([]);
  const [showRoomOverlays, setShowRoomOverlays] = useState(false); // 默认隐藏虚拟房间
  const [selectedRoomId, setSelectedRoomId] = useState<string | null>(null);
  const [drawingType, setDrawingType] = useState<'none' | 'rectangle' | 'polygon'>('none');
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawingStart, setDrawingStart] = useState<{x: number, y: number} | null>(null);
  const [polygonPoints, setPolygonPoints] = useState<Array<{x: number, y: number}>>([]);
  const [userRooms, setUserRooms] = useState<RoomSelection[]>([]);
  const [currentSelection, setCurrentSelection] = useState<RoomSelection | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  const { data: rooms, isLoading } = useQuery<Room[]>({
    queryKey: selectedStoreId ? ["/api/rooms", selectedStoreId] : ["/api/rooms"],
    queryFn: async () => {
      const url = selectedStoreId ? `/api/rooms?storeId=${selectedStoreId}` : '/api/rooms';
      const response = await fetch(url);
      if (!response.ok) throw new Error('Failed to fetch rooms');
      return response.json();
    }
  });

  const { data: floorPlan } = useQuery({
    queryKey: ["/api/floor-plans/active"]
  });

  // 获取用户标记的厅房
  const { data: markedRooms } = useQuery({
    queryKey: ["/api/marked-rooms", selectedStoreId, floorPlan?.id],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (selectedStoreId) params.set('storeId', selectedStoreId.toString());
      if (floorPlan?.id) params.set('floorPlanId', floorPlan.id);
      
      const response = await fetch(`/api/marked-rooms?${params}`);
      if (!response.ok) throw new Error('Failed to fetch marked rooms');
      return response.json();
    },
    enabled: !!floorPlan?.id
  });

  // 保存标记厅房的mutation
  const saveMarkedRoom = useMutation({
    mutationFn: async (roomData: any) => {
      return apiRequest('POST', '/api/marked-rooms', roomData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/marked-rooms"] });
      toast({ title: "成功", description: "厅房标记已保存" });
    },
    onError: () => {
      toast({ title: "错误", description: "保存厅房标记失败", variant: "destructive" });
    }
  });

  // 删除标记厅房的mutation
  const deleteMarkedRoom = useMutation({
    mutationFn: async (roomId: string) => {
      return apiRequest('DELETE', `/api/marked-rooms/${roomId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/marked-rooms"] });
      toast({ title: "成功", description: "厅房标记已删除" });
    },
    onError: () => {
      toast({ title: "错误", description: "删除厅房标记失败", variant: "destructive" });
    }
  });

  useEffect(() => {
    if (!rooms) return;
    
    if (!searchQuery) {
      setFilteredRooms(rooms);
    } else {
      const filtered = rooms.filter(room => 
        room.roomNumber.toLowerCase().includes(searchQuery.toLowerCase()) ||
        room.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (room.tenant && room.tenant.toLowerCase().includes(searchQuery.toLowerCase()))
      );
      setFilteredRooms(filtered);
    }
  }, [rooms, searchQuery]);

  // 加载保存的标记厅房
  useEffect(() => {
    if (markedRooms && Array.isArray(markedRooms)) {
      const convertedRooms: RoomSelection[] = markedRooms.map((room: any) => ({
        id: room.id,
        x: parseFloat(room.x),
        y: parseFloat(room.y), 
        width: parseFloat(room.width),
        height: parseFloat(room.height),
        name: room.name,
        type: room.type,
        points: room.polygonPoints || undefined
      }));
      setUserRooms(convertedRooms);
    }
  }, [markedRooms]);

  const handleZoomIn = () => {
    setZoom(prev => Math.min(prev + 0.25, 3));
  };

  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev - 0.25, 0.5));
  };

  const handleResetZoom = () => {
    setZoom(1);
  };

  const getRoomColor = (room: Room) => {
    if (room.status === 'vacant') {
      return {
        bg: 'bg-slate-300 bg-opacity-20',
        border: 'border-slate-300',
        text: 'text-slate-600'
      };
    }

    if (viewMode === 'revenue') {
      const revenuePerSqm = parseFloat(room.revenuePerSqm || '0');
      if (revenuePerSqm > 200) {
        return {
          bg: 'bg-success bg-opacity-20',
          border: 'border-success',
          text: 'text-success'
        };
      } else if (revenuePerSqm >= 100) {
        return {
          bg: 'bg-primary bg-opacity-20',
          border: 'border-primary',
          text: 'text-primary'
        };
      } else {
        return {
          bg: 'bg-warning bg-opacity-20',
          border: 'border-warning',
          text: 'text-warning'
        };
      }
    }

    // Default for other view modes
    return {
      bg: 'bg-primary bg-opacity-20',
      border: 'border-primary',
      text: 'text-primary'
    };
  };

  const isRoomHighlighted = (room: Room) => {
    if (!searchQuery) return false;
    return room.roomNumber.toLowerCase().includes(searchQuery.toLowerCase()) ||
           room.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
           (room.tenant && room.tenant.toLowerCase().includes(searchQuery.toLowerCase()));
  };

  const handleRoomClick = (room: Room) => {
    setSelectedRoomId(room.id);
    onRoomClick(room);
  };

  // 处理鼠标绘制房间的功能
  const handleMouseDown = (e: React.MouseEvent) => {
    if (drawingType === 'none' || !containerRef.current) return;
    
    const rect = containerRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    
    if (drawingType === 'rectangle') {
      setDrawingStart({ x, y });
      setIsDrawing(true);
    } else if (drawingType === 'polygon') {
      // 多边形绘制：每次点击添加一个顶点
      setPolygonPoints(prev => [...prev, { x, y }]);
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (drawingType !== 'rectangle' || !isDrawing || !drawingStart || !containerRef.current) return;
    
    const rect = containerRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    
    const width = Math.abs(x - drawingStart.x);
    const height = Math.abs(y - drawingStart.y);
    const left = Math.min(x, drawingStart.x);
    const top = Math.min(y, drawingStart.y);
    
    setCurrentSelection({
      id: `temp-${Date.now()}`,
      x: left,
      y: top,
      width,
      height,
      type: 'rectangle'
    });
  };

  const handleMouseUp = () => {
    if (drawingType !== 'rectangle' || !isDrawing || !currentSelection) return;
    
    // 只有当选择区域足够大时才添加
    if (currentSelection.width > 2 && currentSelection.height > 2) {
      const roomName = prompt('请输入厅房名称:') || `厅房 ${userRooms.length + 1}`;
      const newRoom: RoomSelection = {
        ...currentSelection,
        id: `user-room-${Date.now()}`,
        name: roomName,
        type: 'rectangle'
      };
      setUserRooms(prev => [...prev, newRoom]);

      // 保存到服务器
      if (selectedStoreId && floorPlan?.id) {
        saveMarkedRoom.mutate({
          storeId: selectedStoreId,
          floorPlanId: floorPlan.id,
          name: roomName,
          type: 'rectangle',
          x: currentSelection.x,
          y: currentSelection.y,
          width: currentSelection.width,
          height: currentSelection.height
        });
      }
    }
    
    setIsDrawing(false);
    setDrawingStart(null);
    setCurrentSelection(null);
  };

  // 完成多边形绘制
  const finishPolygon = async () => {
    if (polygonPoints.length < 3) {
      alert('多边形至少需要3个顶点');
      return;
    }
    
    const roomName = prompt('请输入厅房名称:') || `厅房 ${userRooms.length + 1}`;
    
    // 计算边界框
    const minX = Math.min(...polygonPoints.map(p => p.x));
    const maxX = Math.max(...polygonPoints.map(p => p.x));
    const minY = Math.min(...polygonPoints.map(p => p.y));
    const maxY = Math.max(...polygonPoints.map(p => p.y));
    
    const newRoom: RoomSelection = {
      id: `user-room-${Date.now()}`,
      x: minX,
      y: minY,
      width: maxX - minX,
      height: maxY - minY,
      name: roomName,
      type: 'polygon',
      points: [...polygonPoints]
    };
    
    setUserRooms(prev => [...prev, newRoom]);

    // 保存到服务器
    if (selectedStoreId && floorPlan?.id) {
      try {
        await saveMarkedRoom.mutateAsync({
          storeId: selectedStoreId,
          floorPlanId: floorPlan.id,
          name: roomName,
          type: 'polygon',
          x: minX,
          y: minY,
          width: maxX - minX,
          height: maxY - minY,
          polygonPoints: polygonPoints
        });
      } catch (error) {
        console.error('Failed to save marked room:', error);
      }
    }
    
    setPolygonPoints([]);
    setDrawingType('none');
  };

  // 取消多边形绘制
  const cancelPolygon = () => {
    setPolygonPoints([]);
    setDrawingType('none');
  };

  const handleUserRoomClick = (room: RoomSelection) => {
    // 创建一个临时的Room对象来适配现有的弹窗
    const tempRoom: Room = {
      id: room.id,
      storeId: selectedStoreId || null,
      roomNumber: room.name || room.id,
      name: room.name || '用户标记房间',
      area: '0',
      tenant: null,
      status: 'vacant',
      monthlyRevenue: '0',
      revenuePerSqm: '0',
      leaseExpiry: null,
      contractType: null,
      x: room.x.toString(),
      y: room.y.toString(),
      width: room.width.toString(),
      height: room.height.toString(),
      createdAt: new Date(),
      updatedAt: new Date()
    };
    onRoomClick(tempRoom);
  };

  if (isLoading) {
    return (
      <div className="floor-plan-container bg-white rounded-xl shadow-sm border border-slate-200 h-full relative">
        <Skeleton className="w-full h-full" />
      </div>
    );
  }

  return (
    <div className="floor-plan-container bg-white rounded-xl shadow-sm border border-slate-200 h-full relative overflow-hidden" data-testid="floor-plan-container">
      <div className="absolute top-4 right-4 z-10">
        <div className="bg-white rounded-lg shadow-lg border border-slate-200 p-2 space-y-2" data-testid="zoom-controls">
          <Button
            size="sm"
            variant="ghost"
            onClick={handleZoomIn}
            className="w-8 h-8 p-0"
            data-testid="button-zoom-in"
          >
            <ZoomIn className="h-4 w-4" />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={handleZoomOut}
            className="w-8 h-8 p-0"
            data-testid="button-zoom-out"
          >
            <ZoomOut className="h-4 w-4" />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={handleResetZoom}
            className="w-8 h-8 p-0"
            data-testid="button-reset-zoom"
          >
            <RotateCcw className="h-4 w-4" />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setShowRoomOverlays(!showRoomOverlays)}
            className="w-8 h-8 p-0"
            data-testid="button-toggle-overlays"
            title={showRoomOverlays ? "隐藏虚拟房间" : "显示虚拟房间"}
          >
            {showRoomOverlays ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </Button>
          <Button
            size="sm"
            variant={drawingType === 'rectangle' ? "default" : "ghost"}
            onClick={() => setDrawingType(drawingType === 'rectangle' ? 'none' : 'rectangle')}
            className="w-8 h-8 p-0"
            data-testid="button-draw-rectangle"
            title={drawingType === 'rectangle' ? "退出矩形绘制" : "绘制矩形房间"}
          >
            <Plus className="h-4 w-4" />
          </Button>
          <Button
            size="sm"
            variant={drawingType === 'polygon' ? "default" : "ghost"}
            onClick={() => setDrawingType(drawingType === 'polygon' ? 'none' : 'polygon')}
            className="w-8 h-8 p-0"
            data-testid="button-draw-polygon"
            title={drawingType === 'polygon' ? "退出多边形绘制" : "绘制多边形房间"}
          >
            <Edit className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* 房间列表面板 */}
      <div className="absolute top-4 left-4 z-10 max-w-xs">
        <div className="bg-white rounded-lg shadow-lg border border-slate-200 p-4" data-testid="room-list-panel">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-slate-900">房间管理</h3>
            {drawingType !== 'none' && (
              <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                {drawingType === 'rectangle' ? '矩形模式' : '多边形模式'}
              </span>
            )}
          </div>
          
          {drawingType === 'rectangle' && (
            <div className="mb-3 p-2 bg-blue-50 rounded text-xs text-blue-700">
              在图纸上拖拽鼠标绘制矩形房间
            </div>
          )}
          
          {drawingType === 'polygon' && (
            <div className="mb-3 p-2 bg-orange-50 rounded text-xs text-orange-700">
              <div>点击图纸上的点绘制多边形房间</div>
              {polygonPoints.length > 0 && (
                <div className="mt-2 flex gap-2">
                  <button 
                    onClick={finishPolygon}
                    className="px-2 py-1 bg-green-500 text-white rounded text-xs"
                  >
                    完成 ({polygonPoints.length}个点)
                  </button>
                  <button 
                    onClick={cancelPolygon}
                    className="px-2 py-1 bg-red-500 text-white rounded text-xs"
                  >
                    取消
                  </button>
                </div>
              )}
            </div>
          )}

          <div className="space-y-2 max-h-60 overflow-y-auto">
            {/* 用户标记的房间 */}
            {userRooms.length > 0 && (
              <>
                <div className="text-xs font-medium text-green-700 mb-1">您标记的房间</div>
                {userRooms.map((room) => (
                  <div
                    key={room.id}
                    className="p-2 rounded cursor-pointer transition-all duration-200 border bg-green-50 border-green-200 hover:bg-green-100"
                    onClick={() => handleUserRoomClick(room)}
                    data-testid={`user-room-list-item-${room.id}`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm font-semibold text-green-900">
                          {room.name}
                        </div>
                        <div className="text-xs text-green-600">
                          {room.type === 'polygon' ? '多边形' : '矩形'} ({room.type === 'polygon' && room.points ? room.points.length : '4'}个点)
                        </div>
                      </div>
                      <div className="w-3 h-3 rounded-full bg-green-500"></div>
                    </div>
                  </div>
                ))}
                <div className="border-t border-slate-200 my-2"></div>
              </>
            )}

            {/* 虚拟房间（仅在显示覆盖层时显示） */}
            {showRoomOverlays && (
              <>
                <div className="text-xs font-medium text-slate-600 mb-1">虚拟房间</div>
                {filteredRooms.map((room) => {
                  const colors = getRoomColor(room);
                  const isSelected = selectedRoomId === room.id;
                  const isHighlighted = isRoomHighlighted(room);
                  
                  return (
                    <div
                      key={room.id}
                      className={`p-2 rounded cursor-pointer transition-all duration-200 border ${
                        isSelected 
                          ? 'bg-blue-50 border-blue-300 shadow-sm' 
                          : 'bg-slate-50 border-slate-200 hover:bg-slate-100'
                      } ${
                        isHighlighted ? 'ring-2 ring-yellow-400 ring-opacity-50' : ''
                      }`}
                      onClick={() => handleRoomClick(room)}
                      data-testid={`room-list-item-${room.roomNumber}`}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="text-sm font-semibold text-slate-900">
                            {room.roomNumber}
                          </div>
                          <div className="text-xs text-slate-600">
                            {room.name}
                          </div>
                        </div>
                        <div className={`w-3 h-3 rounded-full ${colors.bg.replace('bg-opacity-20', '')}`}></div>
                      </div>
                    </div>
                  );
                })}
              </>
            )}
          </div>
        </div>
      </div>

      <div 
        ref={containerRef}
        className={`absolute inset-0 bg-gray-100 rounded-xl transition-transform duration-200 ${
          drawingType !== 'none' ? 'cursor-crosshair' : 'cursor-default'
        }`}
        style={{
          backgroundImage: (floorPlan as any)?.imageUrl ? `url(${window.location.origin}${(floorPlan as any).imageUrl})` : "url('https://images.unsplash.com/photo-1600585154526-990dced4db0d?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=1920&h=1080')",
          backgroundSize: 'contain',
          backgroundRepeat: 'no-repeat',
          backgroundPosition: 'center',
          transform: `scale(${zoom})`
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        data-testid="floor-plan-background"
      >
        {/* 虚拟房间覆盖层 */}
        {showRoomOverlays && filteredRooms.map((room) => {
          const colors = getRoomColor(room);
          const isHighlighted = isRoomHighlighted(room);
          const isSelected = selectedRoomId === room.id;
          
          return (
            <div
              key={room.id}
              className={`room-overlay absolute border-2 rounded cursor-pointer transition-all duration-200 hover:scale-105 hover:brightness-110 ${colors.bg} ${colors.border} ${
                isHighlighted ? 'ring-4 ring-yellow-400 ring-opacity-50' : ''
              } ${
                isSelected ? 'ring-4 ring-blue-500 ring-opacity-70 shadow-lg' : ''
              }`}
              style={{
                top: `${parseFloat(room.y)}%`,
                left: `${parseFloat(room.x)}%`,
                width: `${parseFloat(room.width)}%`,
                height: `${parseFloat(room.height)}%`
              }}
              onClick={() => handleRoomClick(room)}
              data-testid={`room-overlay-${room.roomNumber}`}
            >
              <div className="absolute inset-0 flex items-center justify-center">
                <span className={`text-xs font-semibold bg-white px-2 py-1 rounded shadow ${colors.text} ${
                  isSelected ? 'bg-blue-100 border border-blue-300' : ''
                }`}>
                  {room.roomNumber}
                </span>
              </div>
            </div>
          );
        })}

        {/* 用户标记的房间 */}
        {userRooms.map((room) => {
          if (room.type === 'polygon' && room.points) {
            // 多边形房间 - 使用百分比坐标系统
            return (
              <svg
                key={room.id}
                className="absolute inset-0 w-full h-full pointer-events-none"
                style={{ zIndex: 10 }}
                viewBox="0 0 100 100"
                preserveAspectRatio="none"
              >
                <polygon
                  points={room.points.map(p => `${p.x},${p.y}`).join(' ')}
                  fill="rgba(34, 197, 94, 0.2)"
                  stroke="#22c55e"
                  strokeWidth="0.3"
                  className="cursor-pointer pointer-events-auto"
                  onClick={() => handleUserRoomClick(room)}
                />
                <text
                  x={room.x + room.width / 2}
                  y={room.y + room.height / 2}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  className="text-xs font-semibold fill-green-800 pointer-events-auto cursor-pointer"
                  style={{ fontSize: '2px' }}
                  onClick={() => handleUserRoomClick(room)}
                >
                  {room.name}
                </text>
              </svg>
            );
          } else {
            // 矩形房间
            return (
              <div
                key={room.id}
                className="absolute border-2 border-green-500 bg-green-100 bg-opacity-40 rounded cursor-pointer transition-all duration-200 hover:bg-opacity-60"
                style={{
                  top: `${room.y}%`,
                  left: `${room.x}%`,
                  width: `${room.width}%`,
                  height: `${room.height}%`
                }}
                onClick={() => handleUserRoomClick(room)}
                data-testid={`user-room-${room.id}`}
              >
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-xs font-semibold bg-green-200 text-green-800 px-2 py-1 rounded shadow">
                    {room.name}
                  </span>
                </div>
              </div>
            );
          }
        })}

        {/* 当前绘制的选择 */}
        {currentSelection && (
          <div
            className="absolute border-2 border-blue-500 bg-blue-100 bg-opacity-30 rounded pointer-events-none"
            style={{
              top: `${currentSelection.y}%`,
              left: `${currentSelection.x}%`,
              width: `${currentSelection.width}%`,
              height: `${currentSelection.height}%`
            }}
          />
        )}

        {/* 多边形绘制过程中的顶点显示 */}
        {drawingType === 'polygon' && polygonPoints.length > 0 && (
          <svg 
            className="absolute inset-0 w-full h-full pointer-events-none" 
            style={{ zIndex: 15 }}
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
          >
            {/* 绘制已连接的线条 */}
            {polygonPoints.length > 1 && (
              <polyline
                points={polygonPoints.map(p => `${p.x},${p.y}`).join(' ')}
                fill="none"
                stroke="#3b82f6"
                strokeWidth="0.3"
                strokeDasharray="1,1"
              />
            )}
            
            {/* 绘制顶点 */}
            {polygonPoints.map((point, index) => (
              <circle
                key={index}
                cx={point.x}
                cy={point.y}
                r="0.8"
                fill="#3b82f6"
                stroke="white"
                strokeWidth="0.2"
              />
            ))}
            
            {/* 如果有足够的点，显示预览的闭合线 */}
            {polygonPoints.length >= 3 && (
              <line
                x1={polygonPoints[polygonPoints.length - 1].x}
                y1={polygonPoints[polygonPoints.length - 1].y}
                x2={polygonPoints[0].x}
                y2={polygonPoints[0].y}
                stroke="#3b82f6"
                strokeWidth="0.2"
                strokeDasharray="0.5,0.5"
                opacity="0.6"
              />
            )}
          </svg>
        )}
      </div>
    </div>
  );
}
