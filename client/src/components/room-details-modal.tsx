import { X } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Room } from "@shared/schema";

interface RoomDetailsModalProps {
  room: Room;
  onClose: () => void;
}

export default function RoomDetailsModal({ room, onClose }: RoomDetailsModalProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'occupied':
        return 'bg-success text-white';
      case 'vacant':
        return 'bg-slate-300 text-slate-700';
      case 'maintenance':
        return 'bg-warning text-white';
      default:
        return 'bg-slate-300 text-slate-700';
    }
  };

  const formatCurrency = (value: string | null) => {
    if (!value || value === '0.00') return '¥0';
    return `¥${parseFloat(value).toLocaleString()}`;
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  const capitalizeFirst = (str: string | null) => {
    if (!str) return 'N/A';
    return str.charAt(0).toUpperCase() + str.slice(1);
  };

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="room-details-modal">
        <DialogHeader>
          <DialogTitle className="text-xl font-semibold text-slate-900" data-testid="text-room-title">
            {room.name} - {room.roomNumber}
          </DialogTitle>
        </DialogHeader>
        
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-slate-600">房间编号</label>
                <div className="text-lg font-semibold text-slate-900" data-testid="text-room-id">
                  {room.roomNumber}
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-600">面积</label>
                <div className="text-lg font-semibold text-slate-900" data-testid="text-room-area">
                  {parseFloat(room.area).toFixed(0)} m²
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-600">租户</label>
                <div className="text-lg font-semibold text-slate-900" data-testid="text-room-tenant">
                  {room.tenant || '暂无'}
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-600">状态</label>
                <div className="mt-1">
                  <Badge className={getStatusColor(room.status)} data-testid="badge-room-status">
                    {capitalizeFirst(room.status)}
                  </Badge>
                </div>
              </div>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-slate-600">月收入</label>
                <div className="text-lg font-semibold text-slate-900" data-testid="text-monthly-revenue">
                  {formatCurrency(room.monthlyRevenue)}
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-600">每平方米收费</label>
                <div className="text-lg font-semibold text-slate-900" data-testid="text-revenue-per-sqm">
                  {formatCurrency(room.revenuePerSqm)}
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-600">租期到期</label>
                <div className="text-lg font-semibold text-slate-900" data-testid="text-lease-expiry">
                  {formatDate(room.leaseExpiry)}
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-600">合同类型</label>
                <div className="text-lg font-semibold text-slate-900" data-testid="text-contract-type">
                  {capitalizeFirst(room.contractType)}
                </div>
              </div>
            </div>
          </div>
          
          <div className="mt-6">
            <label className="text-sm font-medium text-slate-600 mb-3 block">收入趋势（最近6个月）</label>
            <div className="bg-slate-50 rounded-lg p-4" data-testid="revenue-trend-chart">
              <div className="flex items-end justify-between h-24 space-x-2">
                <div className="bg-primary w-8 h-16 rounded-t"></div>
                <div className="bg-primary w-8 h-20 rounded-t"></div>
                <div className="bg-primary w-8 h-18 rounded-t"></div>
                <div className="bg-primary w-8 h-22 rounded-t"></div>
                <div className="bg-primary w-8 h-24 rounded-t"></div>
                <div className="bg-primary w-8 h-20 rounded-t"></div>
              </div>
              <div className="flex justify-between text-xs text-slate-500 mt-2">
                <span>Aug</span>
                <span>Sep</span>
                <span>Oct</span>
                <span>Nov</span>
                <span>Dec</span>
                <span>Jan</span>
              </div>
            </div>
          </div>
        </div>
        
        <div className="p-6 border-t border-slate-200 flex justify-end space-x-3">
          <Button variant="ghost" className="text-slate-600 hover:text-slate-800" data-testid="button-view-report">
            查看完整报告
          </Button>
          <Button className="bg-primary text-white hover:bg-blue-700" data-testid="button-edit-details">
            编辑详情
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
