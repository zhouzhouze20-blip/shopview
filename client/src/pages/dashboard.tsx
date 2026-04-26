import { useState, useEffect, useRef } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Building2, MapPin, Users, ZoomIn, ZoomOut, RotateCcw, Maximize, Minimize, BarChart3, Calendar, TrendingUp, DollarSign } from "lucide-react";
import { useStore } from "@/contexts/StoreContext";
import { getApiUrl } from "@/lib/api";

interface StoreUnit {
  id: string;
  code: string;
  name: string;
  area: number;
  x: number;
  y: number;
  width: number;
  height: number;
  shape: 'rectangle' | 'polygon';
  points?: Array<{x: number, y: number}>;
  status: 'occupied' | 'vacant' | 'renovation';
  brand?: string;
  category?: string;
  floor_id?: number;
  geometry_id?: number;
  geometry_type?: string;
  coordinates?: any;
  counter_type?: string;
  group_code?: string;
  deposit?: number;
  monthly_revenue?: number;
  daily_revenue?: number;
  facade_image_url?: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
  floor_name?: string;
  floor_description?: string;
  store_name?: string;
  store_id?: number;
}

interface RevenueDashboardSummary {
  total_daily_revenue: number;
  total_monthly_revenue: number;
  total_yearly_revenue: number;
  average_daily_revenue: number;
  revenue_growth_rate?: number;
  year_over_year_growth?: number;
  top_performing_counters: Array<{
    counter_id: number;
    counter_code: string;
    counter_name: string;
    daily_revenue: number;
    monthly_revenue: number;
    floor_name: string;
  }>;
  revenue_by_floor: Array<{
    floor_id: number;
    floor_name: string;
    daily_revenue: number;
    monthly_revenue: number;
  }>;
  revenue_trend: string;
}

interface CounterRevenueDetail {
  counter_id: number;
  counter_code: string;
  counter_name: string;
  floor_name: string;
  store_name: string;
  area: number;
  daily_revenue: number;
  monthly_revenue: number;
  yearly_revenue: number;
  revenue_per_sqm: number;
  same_period_daily_revenue?: number;
  same_period_monthly_revenue?: number;
  year_over_year_daily?: number;
  year_over_year_monthly?: number;
  total_sales_profit: number;
  total_fees: number;
  profit_breakdown: any;
}

interface RevenueBreakdown {
  total_revenue: number;
  sales_profit: number;
  fees: number;
  sales_profit_percentage: number;
  fees_percentage: number;
  profit_margin: number;
  fee_breakdown: Array<{fee_type: string; amount: number}>;
  sales_breakdown: Array<{category: string; profit: number}>;
}

interface DashboardProps {
  selectedStoreId?: number;
}

export default function Dashboard({ selectedStoreId: initialStoreId }: DashboardProps) {
  const [units, setUnits] = useState<StoreUnit[]>([]);
  const [filteredUnits, setFilteredUnits] = useState<StoreUnit[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedUnit, setSelectedUnit] = useState<StoreUnit | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [zoom, setZoom] = useState(1.5);
  const [floorFilter, setFloorFilter] = useState<string>("all");
  const [floors, setFloors] = useState<any[]>([]);
  const [showBackground, setShowBackground] = useState(true);
  const [backgroundImages, setBackgroundImages] = useState<{[floorId: string]: string}>({});
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showStatsCards, setShowStatsCards] = useState(true);
  const [showImageModal, setShowImageModal] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState<{x: number, y: number} | null>(null);
  const [mapOffset, setMapOffset] = useState({x: 0, y: 0});
  
  // 新增：日期筛选相关状态
  const [dateFilter, setDateFilter] = useState<string>("month");
  const [customStartDate, setCustomStartDate] = useState<string>("");
  const [customEndDate, setCustomEndDate] = useState<string>("");
  
  // 新增：收益类型筛选状态
  const [revenueTypeFilter, setRevenueTypeFilter] = useState<string>("monthly_revenue");
  const [revenueSummary, setRevenueSummary] = useState<RevenueDashboardSummary | null>(null);
  const [counterRevenueDetail, setCounterRevenueDetail] = useState<CounterRevenueDetail | null>(null);
  const [revenueBreakdown, setRevenueBreakdown] = useState<RevenueBreakdown | null>(null);
  const [showRevenueBreakdown, setShowRevenueBreakdown] = useState(false);
  const [showOrders, setShowOrders] = useState(false);
  const [showFees, setShowFees] = useState(false);
  const [orders, setOrders] = useState<any[]>([]);
  const [fees, setFees] = useState<any[]>([]);
  const [orderItems, setOrderItems] = useState<any[]>([]);
  const [selectedOrder, setSelectedOrder] = useState<any>(null);
  const [showOrderItems, setShowOrderItems] = useState(false);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [detailCache, setDetailCache] = useState<{[key: string]: CounterRevenueDetail}>({});
  const [lastClickTime, setLastClickTime] = useState(0);
  
  const { getCurrentFilter } = useStore();

  // 获取收益仪表盘汇总数据
  const fetchRevenueSummary = async () => {
    try {
      const currentFilter = getCurrentFilter();
      let apiUrl = `${getApiUrl()}/api/revenue-dashboard/summary?date_filter=${dateFilter}`;
      
      if (currentFilter.storeId) {
        apiUrl += `&store_id=${currentFilter.storeId}`;
      }
      if (floorFilter !== "all") {
        apiUrl += `&floor_id=${floorFilter}`;
      }
      if (dateFilter === "custom" && customStartDate && customEndDate) {
        apiUrl += `&start_date=${customStartDate}&end_date=${customEndDate}`;
      }
      
      console.log('获取收益汇总数据:', apiUrl);
      const response = await fetch(apiUrl);
      if (response.ok) {
        const data = await response.json();
        setRevenueSummary(data);
      } else {
        console.error('获取收益汇总数据失败:', response.status);
      }
    } catch (error) {
      console.error('获取收益汇总数据出错:', error);
    }
  };

  // 获取柜位收益详情
  const fetchCounterRevenueDetail = async (counterId: number) => {
    try {
      // 检查缓存
      const cacheKey = `${counterId}_${dateFilter}_${customStartDate}_${customEndDate}`;
      if (detailCache[cacheKey]) {
        console.log('使用缓存的柜位收益详情数据');
        setCounterRevenueDetail(detailCache[cacheKey]);
        return;
      }

      setIsLoadingDetail(true);
      let apiUrl = `${getApiUrl()}/api/revenue-dashboard/counter/${counterId}?date_filter=${dateFilter}`;
      
      if (dateFilter === "custom" && customStartDate && customEndDate) {
        apiUrl += `&start_date=${customStartDate}&end_date=${customEndDate}`;
      }
      
      console.log('获取柜位收益详情:', apiUrl);
      const response = await fetch(apiUrl);
      if (response.ok) {
        const data = await response.json();
        console.log('柜位收益详情数据:', data);
        setCounterRevenueDetail(data);
        // 缓存数据
        setDetailCache(prev => ({
          ...prev,
          [cacheKey]: data
        }));
      } else {
        console.error('获取柜位收益详情失败:', response.status);
      }
    } catch (error) {
      console.error('获取柜位收益详情出错:', error);
    } finally {
      setIsLoadingDetail(false);
    }
  };

  // 获取收益分解数据
  const fetchRevenueBreakdown = async (counterId: number) => {
    try {
      let apiUrl = `${getApiUrl()}/api/revenue-dashboard/counter/${counterId}/breakdown?date_filter=${dateFilter}`;
      
      if (dateFilter === "custom" && customStartDate && customEndDate) {
        apiUrl += `&start_date=${customStartDate}&end_date=${customEndDate}`;
      }
      
      console.log('获取收益分解数据:', apiUrl);
      const response = await fetch(apiUrl);
      if (response.ok) {
        const data = await response.json();
        setRevenueBreakdown(data);
      } else {
        console.error('获取收益分解数据失败:', response.status);
      }
    } catch (error) {
      console.error('获取收益分解数据出错:', error);
    }
  };

  // 获取订单列表
  const fetchOrders = async (counterId: number) => {
    try {
      let apiUrl = `${getApiUrl()}/api/revenue-dashboard/counter/${counterId}/orders?date_filter=${dateFilter}`;
      
      if (dateFilter === "custom" && customStartDate && customEndDate) {
        apiUrl += `&start_date=${customStartDate}&end_date=${customEndDate}`;
      }
      
      console.log('获取订单列表:', apiUrl);
      const response = await fetch(apiUrl);
      if (response.ok) {
        const data = await response.json();
        console.log('订单列表数据:', data);
        setOrders(data);
      } else {
        console.error('获取订单列表失败:', response.status);
      }
    } catch (error) {
      console.error('获取订单列表出错:', error);
    }
  };

  // 获取费用列表
  const fetchFees = async (counterId: number) => {
    try {
      let apiUrl = `${getApiUrl()}/api/revenue-dashboard/counter/${counterId}/fees?date_filter=${dateFilter}`;
      
      if (dateFilter === "custom" && customStartDate && customEndDate) {
        apiUrl += `&start_date=${customStartDate}&end_date=${customEndDate}`;
      }
      
      console.log('获取费用列表:', apiUrl);
      const response = await fetch(apiUrl);
      if (response.ok) {
        const data = await response.json();
        console.log('费用列表数据:', data);
        setFees(data);
      } else {
        console.error('获取费用列表失败:', response.status);
      }
    } catch (error) {
      console.error('获取费用列表出错:', error);
    }
  };

  // 获取订单明细
  const fetchOrderItems = async (orderId: string) => {
    try {
      const apiUrl = `${getApiUrl()}/api/revenue-dashboard/order/${orderId}/items`;
      
      console.log('获取订单明细:', apiUrl);
      const response = await fetch(apiUrl);
      if (response.ok) {
        const data = await response.json();
        setOrderItems(data);
      } else {
        console.error('获取订单明细失败:', response.status);
      }
    } catch (error) {
      console.error('获取订单明细出错:', error);
    }
  };

  // 计算收益段分界点
  const calculateRevenueSegments = (units: StoreUnit[], revenueType: string = 'monthly_revenue') => {
    const revenues = units
      .map(u => {
        if (revenueType === 'daily_revenue') {
          return u.daily_revenue || 0;
        }
        return u.monthly_revenue || 0;
      })
      .filter(revenue => revenue > 0)
      .sort((a, b) => a - b);
    
    if (revenues.length === 0) {
      return { segments: [0, 0, 0, 0], labels: ['无数据', '无数据', '无数据', '无数据'] };
    }
    
    // 计算四分位数
    const q1 = revenues[Math.floor(revenues.length * 0.25)];
    const q2 = revenues[Math.floor(revenues.length * 0.5)];
    const q3 = revenues[Math.floor(revenues.length * 0.75)];
    const max = revenues[revenues.length - 1];
    
    return {
      segments: [q1, q2, q3, max],
      labels: [
        `≤${q1.toLocaleString()}`,
        `${q1.toLocaleString()}-${q2.toLocaleString()}`,
        `${q2.toLocaleString()}-${q3.toLocaleString()}`,
        `≥${q3.toLocaleString()}`
      ]
    };
  };

  // 根据收益获取背景颜色
  const getRevenueBackgroundColor = (revenue: number, segments: number[]) => {
    if (!revenue || revenue <= 0) return '#f3f4f6'; // 浅灰色 - 无收益
    
    if (revenue <= segments[0]) return '#fef2f2'; // 浅红色 - 最低段
    if (revenue <= segments[1]) return '#fff7ed'; // 浅橙色 - 第二段
    if (revenue <= segments[2]) return '#fefce8'; // 浅黄色 - 第三段
    return '#f0fdf4'; // 浅绿色 - 最高段
  };

  // 根据收益获取边框颜色
  const getRevenueBorderColor = (revenue: number, segments: number[]) => {
    if (!revenue || revenue <= 0) return '#d1d5db'; // 灰色 - 无收益
    
    if (revenue <= segments[0]) return '#fca5a5'; // 红色 - 最低段
    if (revenue <= segments[1]) return '#fdba74'; // 橙色 - 第二段
    if (revenue <= segments[2]) return '#fde047'; // 黄色 - 第三段
    return '#86efac'; // 绿色 - 最高段
  };

  // 获取当前显示的收益值
  const getCurrentRevenueValue = (unit: StoreUnit) => {
    if (revenueTypeFilter === 'daily_revenue') {
      return unit.daily_revenue || 0;
    }
    return unit.monthly_revenue || 0;
  };

  // 获取收益汇总数据
  useEffect(() => {
    fetchRevenueSummary();
  }, [dateFilter, floorFilter, customStartDate, customEndDate, getCurrentFilter]);

  // 获取柜位数据
  useEffect(() => {
    const fetchCounters = async () => {
      try {
        setIsLoading(true);
        console.log('开始获取柜位数据...');
        
        const currentFilter = getCurrentFilter();
        let apiUrl = `${getApiUrl()}/api/revenue-dashboard/counters?limit=1000`;
        
        if (currentFilter.storeId) {
          apiUrl += `&store_id=${currentFilter.storeId}`;
        }
        
        // 添加楼层筛选
        if (floorFilter !== "all") {
          apiUrl += `&floor_id=${floorFilter}`;
        }
        
        console.log('API URL:', apiUrl);
        const response = await fetch(apiUrl);
        console.log('API响应状态:', response.status);
        
        if (response.ok) {
          const data = await response.json();
          console.log('API返回柜位数量:', data.length);
          
          // 调试：检查原始API数据中的daily_revenue字段
          const hasDailyRevenue = data.some((counter: any) => counter.daily_revenue !== null && counter.daily_revenue !== undefined);
          console.log('API数据中是否有daily_revenue字段:', hasDailyRevenue);
          
          if (hasDailyRevenue) {
            const dailyRevenueCount = data.filter((counter: any) => counter.daily_revenue > 0).length;
            console.log('有daily_revenue数据的柜位数量:', dailyRevenueCount);
            console.log('前3个有daily_revenue的柜位:', data.filter((c: any) => c.daily_revenue > 0).slice(0, 3).map((c: any) => ({ 
              counter_id: c.counter_id, 
              counter_code: c.counter_code, 
              monthly_revenue: c.monthly_revenue,
              daily_revenue: c.daily_revenue 
            })));
          }
          
          // 调试：检查原始API数据中是否有counter_id=2199的数据
          const rawDebugCounter = data.find((counter: any) => counter.counter_id === 2199);
          if (rawDebugCounter) {
            console.log('原始API数据中找到柜位2199:', rawDebugCounter);
          } else {
            console.log('原始API数据中未找到柜位2199');
            console.log('前5个原始柜位数据:', data.slice(0, 5).map((c: any) => ({ counter_id: c.counter_id, counter_code: c.counter_code, monthly_revenue: c.monthly_revenue, daily_revenue: c.daily_revenue })));
          }
          
          const convertedUnits: StoreUnit[] = data.map((counter: any) => ({
            id: counter.counter_id?.toString() || counter.id?.toString() || '',
            code: counter.counter_code || counter.counter_number || '',
            name: counter.counter_name || counter.group_name || '',
            area: parseFloat(counter.area) || 0,
            x: counter.position_x !== null && counter.position_x !== undefined && parseFloat(counter.position_x) !== 0 ? parseFloat(counter.position_x) : 42,
            y: counter.position_y !== null && counter.position_y !== undefined && parseFloat(counter.position_y) !== 0 ? parseFloat(counter.position_y) : 1,
            width: counter.width !== null && counter.width !== undefined ? parseFloat(counter.width) : (8 + Math.random() * 4),
            height: counter.height !== null && counter.height !== undefined ? parseFloat(counter.height) : (6 + Math.random() * 3),
            shape: 'rectangle' as const,
            status: counter.status === 'occupied' ? 'occupied' : 
                   counter.status === 'maintenance' ? 'renovation' : 'vacant',
            brand: counter.group_name || counter.tenant_name || counter.counter_name || '未分配',
            category: counter.counter_type || counter.department || '待定',
            floor_id: counter.floor_id,
            geometry_id: counter.geometry_id,
            geometry_type: counter.geometry_type,
            coordinates: counter.coordinates,
            counter_type: counter.counter_type,
            group_code: counter.group_code,
            deposit: counter.deposit,
            monthly_revenue: counter.monthly_revenue,
            daily_revenue: counter.daily_revenue,
            facade_image_url: counter.facade_image_url,
            is_active: counter.is_active,
            created_at: counter.created_at,
            updated_at: counter.updated_at,
            floor_name: counter.floor_name,
            floor_description: counter.floor_description,
            store_name: counter.store_name,
            store_id: counter.store_id
          }));

          // 去重：按ID去重，保留第一个
          const uniqueUnits = convertedUnits.filter((unit, index, self) => 
            index === self.findIndex(u => u.id === unit.id)
          );
          
          // 调试：检查特定柜位的数据
          const debugCounter = convertedUnits.find(unit => unit.id === '2199');
          if (debugCounter) {
            console.log('找到柜位2199:', debugCounter);
            console.log('monthly_revenue:', debugCounter.monthly_revenue);
            console.log('daily_revenue:', debugCounter.daily_revenue);
          } else {
            console.log('未找到柜位2199，总柜位数:', convertedUnits.length);
            console.log('前5个柜位ID:', convertedUnits.slice(0, 5).map(u => ({ id: u.id, code: u.code, monthly_revenue: u.monthly_revenue })));
          }
          
          setUnits(uniqueUnits);
          setFilteredUnits(uniqueUnits);
        } else {
          console.error('获取柜位数据失败:', response.status);
        }
      } catch (error) {
        console.error('获取柜位数据出错:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchCounters();
  }, [getCurrentFilter, floorFilter]);

  // 加载背景图片
  useEffect(() => {
    const currentFilter = getCurrentFilter();
    const storeId = currentFilter.storeId || 'default';
    const storageKey = `background_images_${storeId}`;
    const savedImages = JSON.parse(localStorage.getItem(storageKey) || '{}');
    setBackgroundImages(savedImages);
  }, [getCurrentFilter]);

  // 筛选数据 - 现在API已经处理了楼层筛选，这里只需要设置过滤后的数据
  useEffect(() => {
    setFilteredUnits(units);
  }, [units]);

  // 获取状态显示信息
  const getStatusInfo = (status: string) => {
    switch (status) {
      case 'occupied':
        return { label: '已租用', className: 'bg-green-100 text-green-800 border-green-500' };
      case 'vacant':
        return { label: '空置', className: 'bg-yellow-100 text-yellow-800 border-yellow-500' };
      case 'renovation':
        return { label: '装修中', className: 'bg-orange-100 text-orange-800 border-orange-500' };
      default:
        return { label: '未知', className: 'bg-gray-100 text-gray-800 border-gray-500' };
    }
  };

  // 处理单元点击
  const handleUnitClick = async (unit: StoreUnit) => {
    const now = Date.now();
    
    // 防抖：如果距离上次点击不到500ms，则忽略
    if (now - lastClickTime < 500) {
      console.log('点击过于频繁，忽略此次点击');
      return;
    }
    
    setLastClickTime(now);
    setSelectedUnit(unit);
    setIsDetailModalOpen(true);
    
    // 获取柜位收益详情 - 添加加载状态
    if (unit.id) {
      try {
        await fetchCounterRevenueDetail(parseInt(unit.id));
      } catch (error) {
        console.error('获取柜位收益详情失败:', error);
      }
    }
  };

  // 缩放控制
  const handleZoomIn = () => {
    setZoom(prev => Math.min(prev + 0.2, 5));
  };

  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev - 0.2, 0.25));
  };

  // 平滑缩放函数
  const smoothZoom = (targetZoom: number) => {
    const currentZoom = zoom;
    const steps = 10;
    const stepSize = (targetZoom - currentZoom) / steps;
    let step = 0;
    
    const animate = () => {
      if (step < steps) {
        setZoom(prev => prev + stepSize);
        step++;
        requestAnimationFrame(animate);
      }
    };
    
    requestAnimationFrame(animate);
  };

  // 重置地图位置和缩放
  const resetMapView = () => {
    setMapOffset({x: 0, y: 0});
    setZoom(1.5);
  };

  // 全屏切换
  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      const mapContainer = document.getElementById('map-container');
      if (mapContainer) {
        mapContainer.requestFullscreen().then(() => {
          setIsFullscreen(true);
        }).catch((err) => {
          console.error('无法进入全屏模式:', err);
        });
      }
    } else {
      document.exitFullscreen().then(() => {
        setIsFullscreen(false);
      }).catch((err) => {
        console.error('无法退出全屏模式:', err);
      });
    }
  };

  // 监听全屏状态变化；组件卸载时先退出全屏，避免 React 对已移入 fullscreen 的 DOM 做 removeChild 报错
  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    const handleFullscreenChange = () => {
      if (mountedRef.current) setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      mountedRef.current = false;
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      if (document.fullscreenElement) {
        document.exitFullscreen().catch(() => {});
      }
    };
  }, []);

  // 鼠标滚轮缩放支持
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setZoom(prev => Math.max(0.25, Math.min(5, prev + delta)));
  };

  // 地图拖拽处理
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX, y: e.clientY });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging && dragStart) {
      const deltaX = e.clientX - dragStart.x;
      const deltaY = e.clientY - dragStart.y;
      
      setMapOffset(prev => ({
        x: prev.x + deltaX,
        y: prev.y + deltaY
      }));
      
      setDragStart({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    setDragStart(null);
  };

  // 获取当前楼层的背景图
  const getCurrentBackgroundImage = () => {
    return floorFilter !== "all" ? backgroundImages[floorFilter] : null;
  };

  // 计算统计信息
  const stats = {
    total: filteredUnits.length,
    occupied: filteredUnits.filter(u => u.status === 'occupied').length,
    vacant: filteredUnits.filter(u => u.status === 'vacant').length,
    renovation: filteredUnits.filter(u => u.status === 'renovation').length,
    totalArea: filteredUnits.reduce((sum, u) => sum + u.area, 0)
  };

  // 切换统计卡片显示
  const toggleStatsCards = () => {
    setShowStatsCards(!showStatsCards);
  };

  if (isLoading) {
    return (
      <div className="w-full p-4 space-y-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="text-lg mb-2">正在加载收益数据...</div>
            <div className="text-sm text-gray-500">请稍候</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full p-4 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">收益仪表盘</h1>
          <p className="text-muted-foreground mt-2">
            收益数据可视化展示 - 查看各楼层收益情况
          </p>
        </div>
      </div>

      {/* 统计卡片 */}
      {showStatsCards && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-base font-medium">
                {floorFilter !== "all" ? "当前楼层柜位数" : "总柜位数"}
              </CardTitle>
              <Building2 className="h-5 w-5 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{stats.total}</div>
              {floorFilter !== "all" && (
                <p className="text-xs text-muted-foreground mt-1">
                  {floors.find(f => f.floor_id.toString() === floorFilter)?.description || `楼层${floorFilter}`}
                </p>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-base font-medium">
                {floorFilter !== "all" ? "当前楼层已租用" : "已租用"}
              </CardTitle>
              <Users className="h-5 w-5 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-green-600">{stats.occupied}</div>
              {floorFilter !== "all" && stats.total > 0 && (
                <p className="text-xs text-muted-foreground mt-1">
                  出租率 {Math.round((stats.occupied / stats.total) * 100)}%
                </p>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-base font-medium">
                {floorFilter !== "all" ? "当前楼层空置" : "空置"}
              </CardTitle>
              <MapPin className="h-5 w-5 text-yellow-600" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-yellow-600">{stats.vacant}</div>
              {floorFilter !== "all" && stats.total > 0 && (
                <p className="text-xs text-muted-foreground mt-1">
                  空置率 {Math.round((stats.vacant / stats.total) * 100)}%
                </p>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-base font-medium">
                {floorFilter !== "all" ? "当前楼层装修中" : "装修中"}
              </CardTitle>
              <Building2 className="h-5 w-5 text-orange-600" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-orange-600">{stats.renovation}</div>
              {floorFilter !== "all" && stats.total > 0 && (
                <p className="text-xs text-muted-foreground mt-1">
                  装修率 {Math.round((stats.renovation / stats.total) * 100)}%
                </p>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-base font-medium">
                {floorFilter !== "all" ? "当前楼层总面积" : "总面积"}
              </CardTitle>
              <Building2 className="h-5 w-5 text-blue-600" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-blue-600">{stats.totalArea.toLocaleString()}㎡</div>
              {floorFilter !== "all" && stats.total > 0 && (
                <p className="text-xs text-muted-foreground mt-1">
                  平均 {Math.round(stats.totalArea / stats.total)}㎡/柜位
                </p>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-base font-medium">
                {dateFilter === "today" ? "日收益" : "月收益"}
              </CardTitle>
              <BarChart3 className="h-5 w-5 text-purple-600" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-purple-600">
                ¥{revenueSummary ? 
                  (dateFilter === "today" ? 
                    revenueSummary.total_daily_revenue.toLocaleString() : 
                    revenueSummary.total_monthly_revenue.toLocaleString()
                  ) : 
                  filteredUnits
                    .filter(u => u.monthly_revenue && u.monthly_revenue > 0)
                    .reduce((sum, u) => sum + (u.monthly_revenue ?? 0), 0)
                    .toLocaleString()
                }
              </div>
              {revenueSummary && (
                <p className="text-xs text-muted-foreground mt-1">
                  {dateFilter === "today" ? "今日" : "当月"}收益
                  {revenueSummary.year_over_year_growth && (
                    <span className={`ml-2 ${revenueSummary.year_over_year_growth > 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {revenueSummary.year_over_year_growth > 0 ? '+' : ''}{Number(revenueSummary.year_over_year_growth || 0).toFixed(1)}%
                    </span>
                  )}
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* 日期筛选 */}
      <div className="flex items-center gap-4 mb-4">
        <div className="flex items-center gap-2">
          <Calendar className="h-5 w-5 text-gray-600" />
          <span className="text-lg font-medium text-gray-700">日期筛选：</span>
        </div>
        <Select value={dateFilter} onValueChange={setDateFilter}>
          <SelectTrigger className="w-48 text-base bg-white border-gray-300 hover:border-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-200">
            <SelectValue placeholder="选择日期范围" />
          </SelectTrigger>
          <SelectContent className="bg-white border border-gray-200 shadow-lg">
            <SelectItem value="today" className="hover:bg-gray-100">今日</SelectItem>
            <SelectItem value="month" className="hover:bg-gray-100">当月</SelectItem>
            <SelectItem value="custom" className="hover:bg-gray-100">自定义</SelectItem>
          </SelectContent>
        </Select>
        
        {dateFilter === "custom" && (
          <div className="flex items-center gap-2">
            <Label htmlFor="start-date" className="text-sm font-medium">开始日期：</Label>
            <Input
              id="start-date"
              type="date"
              value={customStartDate}
              onChange={(e) => setCustomStartDate(e.target.value)}
              className="w-40"
            />
            <Label htmlFor="end-date" className="text-sm font-medium">结束日期：</Label>
            <Input
              id="end-date"
              type="date"
              value={customEndDate}
              onChange={(e) => setCustomEndDate(e.target.value)}
              className="w-40"
            />
          </div>
        )}
      </div>

      {/* 筛选控件 */}
      <div className="flex items-center gap-6">
        {/* 楼层筛选 */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Building2 className="h-5 w-5 text-gray-600" />
            <span className="text-lg font-medium text-gray-700">楼层筛选：</span>
          </div>
          <Select value={floorFilter} onValueChange={setFloorFilter}>
            <SelectTrigger className="w-64 text-base bg-white border-gray-300 hover:border-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-200">
              <SelectValue placeholder="选择楼层" />
            </SelectTrigger>
            <SelectContent className="bg-white border border-gray-200 shadow-lg">
              <SelectItem value="all" className="hover:bg-gray-100">全部楼层</SelectItem>
              {floors.map(floor => (
                <SelectItem key={floor.floor_id} value={floor.floor_id.toString()} className="hover:bg-gray-100">
                  {floor.description || floor.floor_display_name || floor.floor_name || `楼层${floor.floor_id}`}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* 收益类型筛选 */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <DollarSign className="h-5 w-5 text-gray-600" />
            <span className="text-lg font-medium text-gray-700">收益类型：</span>
          </div>
          <Select value={revenueTypeFilter} onValueChange={setRevenueTypeFilter}>
            <SelectTrigger className="w-48 text-base bg-white border-gray-300 hover:border-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-200">
              <SelectValue placeholder="选择收益类型" />
            </SelectTrigger>
            <SelectContent className="bg-white border border-gray-200 shadow-lg">
              <SelectItem value="monthly_revenue" className="hover:bg-gray-100">月销售</SelectItem>
              <SelectItem value="daily_revenue" className="hover:bg-gray-100">日收益</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* 地图区域 */}
      <Card className={`${isFullscreen ? 'fixed inset-0 z-50 h-screen' : showStatsCards ? 'h-[700px]' : 'h-[900px]'}`}>
        {!isFullscreen && (
          <CardHeader>
            <CardTitle className="text-lg">柜位收益分布图 ({filteredUnits.length} 个柜位)</CardTitle>
          </CardHeader>
        )}
        <CardContent className="h-full p-0">
          <div id="map-container" className={`relative h-full bg-gray-50 ${isFullscreen ? 'rounded-none' : 'rounded-lg'} overflow-hidden`}>
            {/* 控制面板 */}
            <div className="absolute top-4 right-4 z-10 space-y-2">
              {/* 缩放控制 */}
              <div className="bg-white rounded-lg shadow-lg border border-slate-200 p-2 space-y-2">
                <div className="text-center">
                  <div className="text-xs font-semibold text-gray-600">缩放</div>
                  <div className="text-xs text-gray-500">{Math.round(zoom * 100)}%</div>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={handleZoomIn}
                  className="w-8 h-8 p-0"
                  title="放大"
                >
                  <ZoomIn className="h-4 w-4" />
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={handleZoomOut}
                  className="w-8 h-8 p-0"
                  title="缩小"
                >
                  <ZoomOut className="h-4 w-4" />
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={resetMapView}
                  className="w-8 h-8 p-0"
                  title="重置地图位置和缩放"
                >
                  <RotateCcw className="h-4 w-4" />
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={toggleFullscreen}
                  className="w-8 h-8 p-0"
                  title={isFullscreen ? "退出全屏" : "全屏显示"}
                >
                  {isFullscreen ? <Minimize className="h-4 w-4" /> : <Maximize className="h-4 w-4" />}
                </Button>
              </div>
              
              {/* 显示控制 */}
              <div className="bg-white rounded-lg shadow-lg border border-slate-200 p-2 space-y-2">
                <Button
                  size="sm"
                  variant={showStatsCards ? "default" : "ghost"}
                  onClick={toggleStatsCards}
                  className="w-8 h-8 p-0"
                  title={showStatsCards ? "隐藏统计卡片" : "显示统计卡片"}
                >
                  <BarChart3 className="h-4 w-4" />
                </Button>
                <Button
                  size="sm"
                  variant={showBackground ? "default" : "ghost"}
                  onClick={() => setShowBackground(!showBackground)}
                  className="w-8 h-8 p-0"
                  title="切换背景显示"
                >
                  <Building2 className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* 地图内容 */}
            <div 
              className={`w-full h-full transition-transform duration-200 relative ${
                isDragging ? 'cursor-grabbing' : 'cursor-grab'
              }`}
              style={{ 
                transform: `scale(${zoom}) translate(${mapOffset.x}px, ${mapOffset.y}px)`,
                transformOrigin: 'center center'
              }}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onWheel={handleWheel}
            >
              {/* 背景地图 */}
              {showBackground ? (
                getCurrentBackgroundImage() ? (
                  <div className="absolute inset-0">
                    <img 
                      src={getCurrentBackgroundImage() || ''} 
                      alt="楼层平面图" 
                      className="w-full h-full object-contain select-none"
                      style={{ 
                        background: '#f8fafc',
                        filter: 'brightness(0.95) contrast(1.05)',
                        imageRendering: 'auto'
                      }}
                      draggable={false}
                    />
                    <div className="absolute top-4 right-4 bg-white/90 backdrop-blur-sm px-3 py-1 rounded-full shadow-lg text-sm font-semibold text-gray-600 border border-white/20">
                      {floorFilter !== "all" ? floors.find(f => f.floor_id.toString() === floorFilter)?.description || `楼层${floorFilter}` : "全部楼层"}
                    </div>
                  </div>
                ) : (
                  <div className="absolute inset-0 bg-gradient-to-br from-blue-50 to-gray-100">
                    <div className="absolute inset-0">
                      <div className="absolute top-0 left-0 w-full h-2 bg-gray-300 opacity-30"></div>
                      <div className="absolute top-1/3 left-0 w-full h-1 bg-gray-300 opacity-30"></div>
                      <div className="absolute top-2/3 left-0 w-full h-1 bg-gray-300 opacity-30"></div>
                      <div className="absolute top-0 left-1/3 w-1 h-full bg-gray-300 opacity-30"></div>
                      <div className="absolute top-0 left-2/3 w-1 h-full bg-gray-300 opacity-30"></div>
                      
                      <div className="absolute top-1/4 left-1/4 w-2 h-2 bg-gray-400 rounded-full opacity-50"></div>
                      <div className="absolute top-1/4 right-1/4 w-2 h-2 bg-gray-400 rounded-full opacity-50"></div>
                      <div className="absolute bottom-1/4 left-1/4 w-2 h-2 bg-gray-400 rounded-full opacity-50"></div>
                      <div className="absolute bottom-1/4 right-1/4 w-2 h-2 bg-gray-400 rounded-full opacity-50"></div>
                      
                      <div className="absolute top-4 right-4 bg-white px-3 py-1 rounded-full shadow-lg text-sm font-semibold text-gray-600">
                        {floorFilter !== "all" ? floors.find(f => f.floor_id.toString() === floorFilter)?.description || `楼层${floorFilter}` : "全部楼层"}
                      </div>
                    </div>
                  </div>
                )
              ) : (
                <div className="absolute inset-0 bg-gray-100">
                  <div className="absolute inset-0 flex items-center justify-center text-gray-400">
                    <div className="text-center">
                      <Building2 className="h-12 w-12 mx-auto mb-2" />
                      <p>背景已隐藏</p>
                    </div>
                  </div>
                </div>
              )}

              {/* 店铺标记 */}
              {filteredUnits.map((unit) => {
                const statusInfo = getStatusInfo(unit.status);
                
                return (
                  <div
                    key={unit.id}
                    data-unit-id={unit.id}
                    className="absolute border-2 rounded cursor-pointer hover:scale-105 hover:brightness-110 transition-all duration-200"
                    style={{
                      top: `${unit.y}%`,
                      left: `${unit.x}%`,
                      width: `${unit.width}%`,
                      height: `${unit.height}%`,
                      zIndex: 10,
                      backgroundColor: getRevenueBackgroundColor(getCurrentRevenueValue(unit), calculateRevenueSegments(filteredUnits, revenueTypeFilter).segments),
                      borderColor: getRevenueBorderColor(getCurrentRevenueValue(unit), calculateRevenueSegments(filteredUnits, revenueTypeFilter).segments),
                      backdropFilter: 'blur(0.5px)',
                      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.2)',
                      borderImage: 'linear-gradient(45deg, rgba(255,255,255,0.3), rgba(0,0,0,0.1)) 1'
                    }}
                    onClick={() => handleUnitClick(unit)}
                  >
                    <div className="absolute inset-0 flex items-center justify-center p-1">
                      <div className="text-center w-full h-full flex flex-col justify-center">
                        <div 
                          className="font-bold text-black leading-tight break-words overflow-hidden"
                          style={{ 
                            textShadow: '2px 2px 4px white, -2px -2px 4px white, 2px -2px 4px white, -2px 2px 4px white',
                            fontSize: `${Math.max(10, Math.min(16, unit.width * 1.2))}px`,
                            lineHeight: '1.0'
                          }}
                        >
                          {unit.brand || unit.name}
                        </div>
                        {getCurrentRevenueValue(unit) > 0 && (
                          <div 
                            className="font-bold leading-tight mt-1"
                            style={{ 
                              textShadow: '2px 2px 4px white, -2px -2px 4px white, 2px -2px 4px white, -2px 2px 4px white',
                              fontSize: `${Math.max(8, Math.min(12, unit.width * 0.8))}px`,
                              lineHeight: '1.0',
                              color: '#1f2937' // 深灰色文字，在浅色背景上更清晰
                            }}
                          >
                            ¥{getCurrentRevenueValue(unit).toLocaleString()}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}

              {/* 图例 */}
              <div className="absolute bottom-4 left-4 bg-white rounded-lg shadow-lg border border-slate-200 p-4">
                <h3 className="text-sm font-semibold text-slate-900 mb-2">图例</h3>
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 bg-green-100 border-2 border-green-500 rounded"></div>
                    <span className="text-xs">已租用</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 bg-yellow-100 border-2 border-yellow-500 rounded"></div>
                    <span className="text-xs">空置</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 bg-orange-100 border-2 border-orange-500 rounded"></div>
                    <span className="text-xs">装修中</span>
                  </div>
                  <div className="border-t pt-2 mt-2">
                    <div className="text-xs font-medium text-gray-700 mb-1">
                      {revenueTypeFilter === 'daily_revenue' ? '日收益区间（背景色）' : '月销售区间（背景色）'}
                    </div>
                    {(() => {
                      const { segments, labels } = calculateRevenueSegments(filteredUnits, revenueTypeFilter);
                      const bgColors = ['#fef2f2', '#fff7ed', '#fefce8', '#f0fdf4'];
                      const borderColors = ['#fca5a5', '#fdba74', '#fde047', '#86efac'];
                      return (
                        <>
                          {bgColors.map((bgColor, index) => (
                            <div key={index} className="flex items-center gap-2 mb-1">
                              <div 
                                className="w-3 h-3 rounded border" 
                                style={{ 
                                  backgroundColor: bgColor,
                                  borderColor: borderColors[index]
                                }}
                              ></div>
                              <span className="text-xs">{labels[index]}</span>
                            </div>
                          ))}
                          <div className="flex items-center gap-2">
                            <div 
                              className="w-3 h-3 rounded border" 
                              style={{ 
                                backgroundColor: '#f3f4f6',
                                borderColor: '#d1d5db'
                              }}
                            ></div>
                            <span className="text-xs">无收益</span>
                          </div>
                        </>
                      );
                    })()}
                  </div>
                </div>
              </div>

              {/* 操作提示 */}
              <div className="absolute bottom-4 right-4 bg-white rounded-lg shadow-lg border border-slate-200 p-3">
                <div className="text-xs text-gray-600 space-y-1">
                  <div>• 按住鼠标拖拽移动地图</div>
                  <div>• 滚轮缩放地图（平滑缩放）</div>
                  <div>• 点击柜位查看收益详情</div>
                  <div>• 使用楼层筛选查看特定楼层</div>
                  <div>• 背景色区分不同收益区间</div>
                  <div>• 背景地图与柜位框同步缩放</div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 店铺详情模态框 */}
      <Dialog open={isDetailModalOpen} onOpenChange={setIsDetailModalOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>柜位收益详细信息 - {selectedUnit?.code}</DialogTitle>
          </DialogHeader>
          {selectedUnit && (
            <div className="space-y-6">
              {/* 门头图片 */}
              {selectedUnit.facade_image_url && (
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-gray-900 border-b pb-2">门头图片</h3>
                  <div className="flex justify-center">
                    <div className="relative max-w-md w-full">
                      <img
                        src={selectedUnit.facade_image_url}
                        alt={`${selectedUnit.name} 门头图片`}
                        className="w-full h-48 object-cover rounded-lg shadow-lg border border-gray-200 cursor-pointer hover:opacity-90 transition-opacity"
                        onClick={() => setShowImageModal(true)}
                        onError={(e) => {
                          console.error('门头图片加载失败:', selectedUnit.facade_image_url);
                          e.currentTarget.style.display = 'none';
                        }}
                      />
                      <div className="absolute top-2 right-2 bg-black bg-opacity-50 text-white text-xs px-2 py-1 rounded">
                        {selectedUnit.code}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* 收益信息 - 重点显示 */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-900 border-b pb-2">
                  收益信息
                  {isLoadingDetail && (
                    <span className="ml-2 text-sm text-blue-600">正在加载...</span>
                  )}
                </h3>
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-green-50 p-4 rounded-lg">
                    <label className="text-base font-semibold text-green-700">
                      {dateFilter === "today" ? "日收益" : "月收益"}
                    </label>
                    <p className="text-3xl font-bold text-green-600 mt-2">
                      ¥{counterRevenueDetail ? 
                        (dateFilter === "today" ? 
                          counterRevenueDetail.daily_revenue.toLocaleString() : 
                          counterRevenueDetail.monthly_revenue.toLocaleString()
                        ) : 
                        (selectedUnit.monthly_revenue?.toLocaleString() || 0)
                      }
                    </p>
                    <p className="text-sm text-green-600 mt-2">
                      {counterRevenueDetail && counterRevenueDetail.area > 0 ? 
                        `每平米: ¥${Number(counterRevenueDetail.revenue_per_sqm || 0).toFixed(2)}` :
                        selectedUnit.area > 0 && selectedUnit.monthly_revenue ? 
                          `每平米: ¥${(selectedUnit.monthly_revenue / selectedUnit.area).toFixed(2)}` :
                          '未设置租金'
                      }
                    </p>
                  </div>
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <label className="text-base font-semibold text-blue-700">同比数据</label>
                    <p className="text-3xl font-bold text-blue-600 mt-2">
                      {counterRevenueDetail?.year_over_year_daily ? 
                        `${counterRevenueDetail.year_over_year_daily > 0 ? '+' : ''}${Number(counterRevenueDetail.year_over_year_daily || 0).toFixed(1)}%` :
                        '暂无数据'
                      }
                    </p>
                    <p className="text-sm text-blue-600 mt-2">
                      {dateFilter === "today" ? "较去年同期" : "较去年同期"}
                    </p>
                  </div>
                  <div className="bg-purple-50 p-4 rounded-lg">
                    <label className="text-base font-semibold text-purple-700">年度收益</label>
                    <p className="text-3xl font-bold text-purple-600 mt-2">
                      ¥{counterRevenueDetail?.yearly_revenue ? 
                        counterRevenueDetail.yearly_revenue.toLocaleString() :
                        selectedUnit.monthly_revenue ? (selectedUnit.monthly_revenue * 12).toLocaleString() : 0
                      }
                    </p>
                    <p className="text-sm text-purple-600 mt-2">
                      年度总收益
                    </p>
                  </div>
                </div>
                
                {/* 收益分解 */}
                <div className="grid grid-cols-2 gap-4 mt-4">
                  <div className="bg-orange-50 p-4 rounded-lg">
                    <label className="text-base font-semibold text-orange-700">销售毛利</label>
                    <p className="text-3xl font-bold text-orange-600 mt-2">
                      ¥{counterRevenueDetail?.total_sales_profit?.toLocaleString() || '0'}
                    </p>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="mt-2"
                      onClick={async () => {
                        setShowOrders(true);
                        if (selectedUnit?.id) {
                          await fetchOrders(parseInt(selectedUnit.id));
                        }
                      }}
                    >
                      查看订单
                    </Button>
                  </div>
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <label className="text-base font-semibold text-gray-700">收费</label>
                    <p className="text-3xl font-bold text-gray-600 mt-2">
                      ¥{counterRevenueDetail?.total_fees?.toLocaleString() || '0'}
                    </p>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="mt-2"
                      onClick={async () => {
                        setShowFees(true);
                        if (selectedUnit?.id) {
                          await fetchFees(parseInt(selectedUnit.id));
                        }
                      }}
                    >
                      查看费用
                    </Button>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-4 mt-4">
                  <div className="bg-orange-50 p-4 rounded-lg">
                    <label className="text-base font-semibold text-orange-700">装修保证金</label>
                    <p className="text-3xl font-bold text-orange-600 mt-2">
                      ¥{selectedUnit.deposit?.toLocaleString() || 0}
                    </p>
                    <p className="text-sm text-orange-600 mt-2">
                      {selectedUnit.is_active ? '已激活' : '未激活'}
                    </p>
                  </div>
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <label className="text-base font-semibold text-gray-700">年度预期收益</label>
                    <p className="text-3xl font-bold text-gray-600 mt-2">
                      ¥{selectedUnit.monthly_revenue ? (selectedUnit.monthly_revenue * 12).toLocaleString() : 0}
                    </p>
                    <p className="text-sm text-gray-600 mt-2">
                      月收益 × 12个月
                    </p>
                  </div>
                </div>
              </div>

              {/* 基本信息 */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-900 border-b pb-2">柜位基本信息</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-500">柜位编号</label>
                    <p className="text-lg font-semibold">{selectedUnit.code}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">柜位名称</label>
                    <p className="text-lg font-semibold">{selectedUnit.name}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">柜位类型</label>
                    <p className="text-base">{selectedUnit.counter_type || '未设置'}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">柜组编码</label>
                    <p className="text-base">{selectedUnit.group_code || '未设置'}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">面积</label>
                    <p className="text-base">{selectedUnit.area}㎡</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">状态</label>
                    <Badge className={getStatusInfo(selectedUnit.status).className}>
                      {getStatusInfo(selectedUnit.status).label}
                    </Badge>
                  </div>
                </div>
              </div>

              {/* 位置信息 */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-900 border-b pb-2">位置信息</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-500">楼层</label>
                    <p className="text-base">{selectedUnit.floor_name || selectedUnit.floor_description || `楼层${selectedUnit.floor_id}`}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">门店</label>
                    <p className="text-base">{selectedUnit.store_name || `门店${selectedUnit.store_id}`}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">位置坐标</label>
                    <p className="text-base">X: {selectedUnit.x}%, Y: {selectedUnit.y}%</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">尺寸</label>
                    <p className="text-base">{selectedUnit.width} × {selectedUnit.height}</p>
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button variant="outline" onClick={() => setIsDetailModalOpen(false)}>
                  关闭
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* 门头图片放大模态框 */}
      <Dialog open={showImageModal} onOpenChange={setShowImageModal}>
        <DialogContent className="max-w-4xl max-h-[90vh] p-0">
          <DialogHeader className="p-6 pb-0">
            <DialogTitle>门头图片 - {selectedUnit?.name}</DialogTitle>
          </DialogHeader>
          {selectedUnit?.facade_image_url && (
            <div className="p-6 pt-0">
              <div className="flex justify-center">
                <img
                  src={selectedUnit.facade_image_url}
                  alt={`${selectedUnit.name} 门头图片`}
                  className="max-w-full max-h-[70vh] object-contain rounded-lg shadow-lg"
                  onError={(e) => {
                    console.error('门头图片加载失败:', selectedUnit.facade_image_url);
                    e.currentTarget.style.display = 'none';
                  }}
                />
              </div>
              <div className="mt-4 text-center text-sm text-gray-500">
                <p>柜位编号: {selectedUnit.code}</p>
                <p>点击外部区域关闭</p>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* 订单查看模态框 */}
      <Dialog open={showOrders} onOpenChange={setShowOrders}>
        <DialogContent className="max-w-6xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>订单列表 - {selectedUnit?.name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              显示 {dateFilter === "today" ? "今日" : dateFilter === "month" ? "当月" : "自定义时间段"} 的订单数据
            </p>
            
            {orders.length > 0 ? (
              <div className="space-y-4">
                {orders.map((order) => (
                  <Card key={order.order_id} className="p-4">
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <h3 className="text-lg font-semibold">订单 {order.order_id}</h3>
                        <p className="text-sm text-gray-600">
                          {new Date(order.order_date).toLocaleDateString()} | 
                          客户: {order.customer_name} | 
                          电话: {order.customer_phone}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-bold text-green-600">
                          ¥{order.final_amount.toLocaleString()}
                        </p>
                        <Badge className={
                          order.order_status === 'completed' ? 'bg-green-100 text-green-800' :
                          order.order_status === 'cancelled' ? 'bg-red-100 text-red-800' :
                          'bg-yellow-100 text-yellow-800'
                        }>
                          {order.order_status === 'completed' ? '已完成' :
                           order.order_status === 'cancelled' ? '已取消' : '待处理'}
                        </Badge>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-600">订单类型:</span> {order.order_type}
                      </div>
                      <div>
                        <span className="text-gray-600">支付方式:</span> {order.payment_method}
                      </div>
                      <div>
                        <span className="text-gray-600">销售人员:</span> {order.sales_person}
                      </div>
                      <div>
                        <span className="text-gray-600">总金额:</span> ¥{order.total_amount.toLocaleString()}
                      </div>
                      {order.discount_amount > 0 && (
                        <div>
                          <span className="text-gray-600">折扣:</span> -¥{order.discount_amount.toLocaleString()}
                        </div>
                      )}
                    </div>
                    
                    {order.order_items && order.order_items.length > 0 && (
                      <div className="mt-4">
                        <h4 className="text-sm font-semibold text-gray-700 mb-2">商品明细:</h4>
                        <div className="space-y-2">
                          {order.order_items.map((item: any, index: number) => (
                            <div key={index} className="flex justify-between items-center bg-gray-50 p-2 rounded">
                              <div>
                                <span className="font-medium">{item.product_name}</span>
                                <span className="text-sm text-gray-600 ml-2">
                                  {item.brand_name} | {item.product_category}
                                </span>
                              </div>
                              <div className="text-right text-sm">
                                <div>数量: {item.quantity}</div>
                                <div>单价: ¥{item.unit_price.toLocaleString()}</div>
                                <div className="font-semibold">总价: ¥{item.total_price.toLocaleString()}</div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    <div className="mt-4 flex justify-end">
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={async () => {
                          setSelectedOrder(order);
                          setShowOrderItems(true);
                          await fetchOrderItems(order.order_id);
                        }}
                      >
                        查看详细明细
                      </Button>
                    </div>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <DollarSign className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <p>暂无订单数据</p>
                <p className="text-sm">该时间段内没有找到订单记录</p>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* 费用查看模态框 */}
      <Dialog open={showFees} onOpenChange={setShowFees}>
        <DialogContent className="max-w-6xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>费用明细 - {selectedUnit?.name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              显示 {dateFilter === "today" ? "今日" : dateFilter === "month" ? "当月" : "自定义时间段"} 的费用数据
            </p>
            
            {fees.length > 0 ? (
              <div className="space-y-4">
                {fees.map((fee) => (
                  <Card key={fee.fee_id} className="p-4">
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <h3 className="text-lg font-semibold">{fee.fee_type}</h3>
                        <p className="text-sm text-gray-600">
                          {new Date(fee.fee_date).toLocaleDateString()} | 
                          计费周期: {fee.billing_period} | 
                          说明: {fee.fee_description}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-bold text-blue-600">
                          ¥{fee.fee_amount.toLocaleString()}
                        </p>
                        <Badge className={
                          fee.payment_status === 'paid' ? 'bg-green-100 text-green-800' :
                          fee.payment_status === 'overdue' ? 'bg-red-100 text-red-800' :
                          'bg-yellow-100 text-yellow-800'
                        }>
                          {fee.payment_status === 'paid' ? '已付' :
                           fee.payment_status === 'overdue' ? '逾期' : '未付'}
                        </Badge>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-600">付款方式:</span> {fee.payment_method || '未设置'}
                      </div>
                      <div>
                        <span className="text-gray-600">付款日期:</span> {fee.payment_date ? new Date(fee.payment_date).toLocaleDateString() : '未付款'}
                      </div>
                      {fee.notes && (
                        <div className="col-span-2">
                          <span className="text-gray-600">备注:</span> {fee.notes}
                        </div>
                      )}
                    </div>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <TrendingUp className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <p>暂无费用数据</p>
                <p className="text-sm">该时间段内没有找到费用记录</p>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* 订单明细查看模态框 */}
      <Dialog open={showOrderItems} onOpenChange={setShowOrderItems}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>订单明细 - {selectedOrder?.order_id}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {selectedOrder && (
              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="text-lg font-semibold mb-2">订单信息</h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div><span className="text-gray-600">订单ID:</span> {selectedOrder.order_id}</div>
                  <div><span className="text-gray-600">订单日期:</span> {new Date(selectedOrder.order_date).toLocaleDateString()}</div>
                  <div><span className="text-gray-600">客户:</span> {selectedOrder.customer_name}</div>
                  <div><span className="text-gray-600">电话:</span> {selectedOrder.customer_phone}</div>
                  <div><span className="text-gray-600">总金额:</span> ¥{selectedOrder.total_amount.toLocaleString()}</div>
                  <div><span className="text-gray-600">最终金额:</span> ¥{selectedOrder.final_amount.toLocaleString()}</div>
                </div>
              </div>
            )}
            
            {orderItems.length > 0 ? (
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">商品明细</h3>
                {orderItems.map((item, index) => (
                  <Card key={index} className="p-4">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <h4 className="font-semibold text-lg">{item.product_name}</h4>
                        <p className="text-sm text-gray-600">
                          商品编码: {item.product_code} | 
                          品牌: {item.brand_name} | 
                          类别: {item.product_category}
                        </p>
                        {item.notes && (
                          <p className="text-sm text-gray-500 mt-1">备注: {item.notes}</p>
                        )}
                      </div>
                      <div className="text-right ml-4">
                        <div className="text-sm text-gray-600">
                          <div>数量: {item.quantity}</div>
                          <div>单价: ¥{item.unit_price.toLocaleString()}</div>
                          <div>总价: ¥{item.total_price.toLocaleString()}</div>
                        </div>
                        {item.unit_cost && (
                          <div className="text-sm text-gray-600 mt-2 pt-2 border-t">
                            <div>单位成本: ¥{item.unit_cost.toLocaleString()}</div>
                            <div>总成本: ¥{item.total_cost.toLocaleString()}</div>
                            <div className="font-semibold text-green-600">
                              利润: ¥{item.profit.toLocaleString()}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <p>暂无商品明细</p>
                <p className="text-sm">该订单没有商品明细记录</p>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
