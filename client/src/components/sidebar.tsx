import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Room } from "@shared/schema";

interface Stats {
  totalRooms: number;
  occupied: number;
  vacant: number;
  avgRevenue: number;
}

interface Activity {
  id: string;
  type: string;
  description: string;
  createdAt: string;
}

interface SidebarProps {
  selectedRoom?: Room | null;
}

function formatTimeAgo(dateString: string) {
  const date = new Date(dateString);
  const now = new Date();
  const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));
  
  if (diffInHours < 1) return "Just now";
  if (diffInHours < 24) return `${diffInHours} hours ago`;
  const diffInDays = Math.floor(diffInHours / 24);
  return `${diffInDays} day${diffInDays > 1 ? 's' : ''} ago`;
}

export default function Sidebar({ selectedRoom }: SidebarProps) {
  const { data: stats, isLoading: statsLoading } = useQuery<Stats>({
    queryKey: ["/api/stats"]
  });

  const { data: activities, isLoading: activitiesLoading } = useQuery<Activity[]>({
    queryKey: ["/api/activities"]
  });

  return (
    <aside className="w-80 bg-white border-r border-slate-200 flex flex-col" data-testid="sidebar">
      <div className="p-6 border-b border-slate-200">
        <h2 className="text-lg font-semibold text-slate-900 mb-4" data-testid="text-current-floor-plan">
          当前楼层平面图
        </h2>
        <div className="bg-slate-50 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-slate-600" data-testid="text-floor-level">
              商场 1层
            </span>
            <Badge className="bg-success text-white" data-testid="badge-status">
              激活
            </Badge>
          </div>
          <div className="text-xs text-slate-500" data-testid="text-last-updated">
            最后更新: 2024-01-15
          </div>
        </div>
      </div>
      
      <div className="p-6 border-b border-slate-200">
        <h3 className="text-md font-semibold text-slate-900 mb-4" data-testid="text-quick-stats">
          快速统计
        </h3>
        <div className="space-y-3">
          {statsLoading ? (
            <>
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-full" />
            </>
          ) : (
            <>
              <div className="flex justify-between items-center">
                <span className="text-sm text-slate-600">总房间数</span>
                <span className="text-sm font-semibold text-slate-900" data-testid="text-total-rooms">
                  {stats?.totalRooms || 0}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-slate-600">已出租</span>
                <span className="text-sm font-semibold text-success" data-testid="text-occupied-rooms">
                  {stats?.occupied || 0}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-slate-600">空置</span>
                <span className="text-sm font-semibold text-warning" data-testid="text-vacant-rooms">
                  {stats?.vacant || 0}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-slate-600">平均收费/m²</span>
                <span className="text-sm font-semibold text-slate-900" data-testid="text-avg-revenue">
                  ¥{stats?.avgRevenue || 0}
                </span>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="p-6 border-b border-slate-200">
        <h3 className="text-md font-semibold text-slate-900 mb-4" data-testid="text-legend">
          图例说明
        </h3>
        <div className="space-y-3">
          <div className="flex items-center space-x-3">
            <div className="w-4 h-4 bg-success rounded"></div>
            <span className="text-sm text-slate-600">高收费 (&gt;¥200/m²)</span>
          </div>
          <div className="flex items-center space-x-3">
            <div className="w-4 h-4 bg-primary rounded"></div>
            <span className="text-sm text-slate-600">中等收费 (¥100-200/m²)</span>
          </div>
          <div className="flex items-center space-x-3">
            <div className="w-4 h-4 bg-warning rounded"></div>
            <span className="text-sm text-slate-600">低收费 (&lt;¥100/m²)</span>
          </div>
          <div className="flex items-center space-x-3">
            <div className="w-4 h-4 bg-slate-300 rounded"></div>
            <span className="text-sm text-slate-600">空置</span>
          </div>
        </div>
      </div>

      {/* 房间详细信息 */}
      {selectedRoom && (
        <div className="p-6 border-b border-slate-200">
          <h3 className="text-md font-semibold text-slate-900 mb-4" data-testid="text-room-details">
            房间详细信息
          </h3>
          <Card>
            <CardContent className="pt-4 space-y-3">
              <div>
                <label className="text-xs font-medium text-slate-600">房间号</label>
                <p className="text-sm text-slate-900 font-medium">{selectedRoom.roomNumber}</p>
              </div>
              
              <div>
                <label className="text-xs font-medium text-slate-600">房间名称</label>
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
                <p className="text-sm text-slate-900 font-semibold text-green-600">¥{parseFloat(selectedRoom.monthlyRevenue).toLocaleString()}</p>
              </div>
              
              <div>
                <label className="text-xs font-medium text-slate-600">单价/m²</label>
                <p className="text-sm text-slate-900">¥{parseFloat(selectedRoom.revenuePerSqm).toLocaleString()}</p>
              </div>
              
              {selectedRoom.leaseExpiry && (
                <div>
                  <label className="text-xs font-medium text-slate-600">租期到期</label>
                  <p className="text-sm text-slate-900">{new Date(selectedRoom.leaseExpiry).toLocaleDateString('zh-CN')}</p>
                </div>
              )}
              
              {selectedRoom.contractType && (
                <div>
                  <label className="text-xs font-medium text-slate-600">合同类型</label>
                  <p className="text-sm text-slate-900">{selectedRoom.contractType}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      <div className="p-6 flex-1">
        <h3 className="text-md font-semibold text-slate-900 mb-4" data-testid="text-recent-activity">
          {selectedRoom ? '最近活动' : '点击房间查看详情'}
        </h3>
        {!selectedRoom ? (
          <div className="text-center py-8">
            <p className="text-sm text-slate-500">在平面图中点击任意房间</p>
            <p className="text-sm text-slate-500">查看详细信息</p>
          </div>
        ) : (
          <div className="space-y-3">
            {activitiesLoading ? (
              <>
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </>
            ) : activities && activities.length > 0 ? (
              activities.map((activity) => (
                <div key={activity.id} className="flex items-start space-x-3" data-testid={`activity-${activity.id}`}>
                  <div className={`w-2 h-2 rounded-full mt-2 ${
                    activity.type === 'lease_renewal' ? 'bg-primary' :
                    activity.type === 'payment_received' ? 'bg-success' :
                    'bg-warning'
                  }`}></div>
                  <div className="flex-1">
                    <div className="text-sm text-slate-900" data-testid={`text-activity-description-${activity.id}`}>
                      {activity.description}
                    </div>
                    <div className="text-xs text-slate-500" data-testid={`text-activity-time-${activity.id}`}>
                      {formatTimeAgo(activity.createdAt)}
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-sm text-slate-500" data-testid="text-no-activities">
                暂无最近活动
              </div>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}
