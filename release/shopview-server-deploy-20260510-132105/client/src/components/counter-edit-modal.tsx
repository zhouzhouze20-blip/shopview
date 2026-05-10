import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";
import { useStore } from "@/contexts/StoreContext";
import { ImageUploader } from "@/components/ImageUploader";
import { apiRequest } from "@/lib/api";
import { formatOperationMethod } from "@/lib/operation-method";

interface Counter {
  counter_id: number;
  store_id: number;
  floor_id: number;
  counter_code: string;
  counter_name: string;
  area: number;
  counter_type: string;
  status: 'vacant' | 'occupied' | 'maintenance';
  deposit: number;
  group_code?: string;
  facade_image_url?: string;
  monthly_revenue?: number;
  is_active: boolean;
  created_at: string;
  // 楼层信息
  floor_name?: string;
  floor_number?: number;
}

interface Floor {
  floor_id: number;
  floor_name: string;
  floor_number: number;
  floor_display_name?: string;
  building_code?: string;
  building_name?: string;
  store_id: number;
}

interface CounterGroup {
  group_id: number;
  group_code: string;
  group_name: string;
  brand_name?: string;
  operation_method?: string;
  is_active: boolean;
}

interface CounterEditModalProps {
  counter: Counter | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (updatedCounter: Counter) => void;
}

export default function CounterEditModal({ counter, isOpen, onClose, onSave }: CounterEditModalProps) {
  const [formData, setFormData] = useState<Partial<Counter>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [floors, setFloors] = useState<Floor[]>([]);
  const [isLoadingFloors, setIsLoadingFloors] = useState(false);
  const [counterGroups, setCounterGroups] = useState<CounterGroup[]>([]);
  const [isLoadingGroups, setIsLoadingGroups] = useState(false);
  const [groupSearchQuery, setGroupSearchQuery] = useState('');
  const [showGroupDropdown, setShowGroupDropdown] = useState(false);
  const { toast } = useToast();
  const { stores } = useStore();

  // 获取柜组数据
  const fetchCounterGroups = async (searchQuery: string) => {
    if (!searchQuery.trim() || !counter?.store_id) {
      setCounterGroups([]);
      return;
    }

    setIsLoadingGroups(true);
    try {
      // 根据门店ID筛选柜组
      const response = await apiRequest(`/api/counter-groups/?search=${encodeURIComponent(searchQuery)}&store_id=${counter.store_id}&limit=20`, {
        method: 'GET',
      });
      
      if (response.ok) {
        const groupsData = await response.json();
        setCounterGroups(groupsData);
      } else {
        console.error('获取柜组数据失败');
        setCounterGroups([]);
      }
    } catch (error) {
      console.error('获取柜组数据出错:', error);
      setCounterGroups([]);
    } finally {
      setIsLoadingGroups(false);
    }
  };

  // 防抖搜索柜组
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (groupSearchQuery) {
        fetchCounterGroups(groupSearchQuery);
      } else {
        setCounterGroups([]);
      }
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [groupSearchQuery]);

  // 当模态框打开时，初始化表单数据
  useEffect(() => {
    if (counter && isOpen) {
      setFormData({
        counter_code: counter.counter_code,
        counter_name: counter.counter_name,
        floor_id: counter.floor_id,
        area: counter.area,
        counter_type: counter.counter_type,
        status: counter.status,
        deposit: counter.deposit,
        group_code: counter.group_code || '',
        facade_image_url: counter.facade_image_url || '',
        monthly_revenue: counter.monthly_revenue || 0,
        is_active: counter.is_active
      });
      setGroupSearchQuery(counter.group_code || '');
    }
  }, [counter, isOpen]);

  const handleInputChange = (field: keyof Counter, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // 处理柜组选择
  const handleGroupSelect = (group: CounterGroup) => {
    setFormData(prev => ({
      ...prev,
      group_code: group.group_code,
      counter_name: group.group_name // 自动填入柜位名称
    }));
    setGroupSearchQuery(group.group_code);
    setShowGroupDropdown(false);
  };

  // 处理柜组搜索输入
  const handleGroupSearchChange = (value: string) => {
    setGroupSearchQuery(value);
    setFormData(prev => ({
      ...prev,
      group_code: value
    }));
    setShowGroupDropdown(value.length > 0);
  };

  // 点击外部关闭下拉框
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Element;
      if (!target.closest('.group-search-container')) {
        setShowGroupDropdown(false);
      }
    };

    if (showGroupDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [showGroupDropdown]);

  const handleSave = async () => {
    if (!counter) return;

    setIsLoading(true);
    try {
      const response = await apiRequest(`/api/counters/${counter.counter_id}`, {
        method: 'PUT',
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        const updatedCounter = await response.json();
        onSave(updatedCounter);
        toast({
          title: "保存成功",
          description: "柜位信息已更新",
        });
        onClose();
      } else {
        const errorData = await response.json();
        toast({
          title: "保存失败",
          description: errorData.detail || "更新柜位信息时出错",
          variant: "destructive",
        });
      }
    } catch (error) {
      toast({
        title: "保存失败",
        description: "网络错误，请稍后重试",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const getStoreName = (storeId: number) => {
    const store = stores.find(s => s.storeId === storeId);
    return store ? store.storeName : `门店${storeId}`;
  };

  // 图片上传处理函数
  const handleGetUploadParameters = async () => {
    try {
      const response = await apiRequest('/api/objects/upload', {
        method: 'POST',
      });
      
      const data = await response.json();
      return {
        method: 'PUT' as const,
        url: data.uploadURL,
      };
    } catch (error) {
      console.error('Error getting upload URL:', error);
      throw new Error('获取上传URL失败，请检查网络连接');
    }
  };

  const handleImageUploadComplete = (imageUrl: string) => {
    setFormData(prev => ({
      ...prev,
      facade_image_url: imageUrl
    }));
    toast({
      title: "上传成功",
      description: "门头图片已上传",
    });
  };

  const handleImageUploadError = (error: string) => {
    toast({
      title: "上传失败",
      description: error,
      variant: "destructive",
    });
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-xl">编辑柜位信息</DialogTitle>
        </DialogHeader>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 py-4">
          {/* 基本信息 */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium">基本信息</h3>
            
            <div>
              <Label htmlFor="counter_code">柜位编号</Label>
              <Input
                id="counter_code"
                value={formData.counter_code || ''}
                onChange={(e) => handleInputChange('counter_code', e.target.value)}
                placeholder="请输入柜位编号"
              />
            </div>

            <div className="relative group-search-container">
              <Label htmlFor="group_code">柜组编码</Label>
              <Input
                id="group_code"
                value={groupSearchQuery}
                onChange={(e) => handleGroupSearchChange(e.target.value)}
                onFocus={() => setShowGroupDropdown(true)}
                placeholder="搜索柜组编码或名称"
              />
              
              {/* 柜组搜索结果下拉框 */}
              {showGroupDropdown && (
                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-md shadow-lg max-h-60 overflow-y-auto">
                  {isLoadingGroups ? (
                    <div className="p-3 text-center text-gray-500">搜索中...</div>
                  ) : counterGroups.length > 0 ? (
                    counterGroups.map((group) => (
                      <div
                        key={group.group_id}
                        className="p-3 hover:bg-gray-50 cursor-pointer border-b border-gray-100 last:border-b-0"
                        onClick={() => handleGroupSelect(group)}
                      >
                        <div className="flex justify-between items-start">
                          <div>
                            <div className="font-medium text-sm">{group.group_code}</div>
                            <div className="text-sm text-gray-600">{group.group_name}</div>
                            {group.brand_name && (
                              <div className="text-xs text-gray-500">品牌: {group.brand_name}</div>
                            )}
                          </div>
                          {group.operation_method && (
                            <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                              {formatOperationMethod(group.operation_method)}
                            </span>
                          )}
                        </div>
                      </div>
                    ))
                  ) : groupSearchQuery ? (
                    <div className="p-3 text-center text-gray-500">未找到匹配的柜组</div>
                  ) : null}
                </div>
              )}
            </div>

            <div>
              <Label htmlFor="counter_name">柜位名称</Label>
              <Input
                id="counter_name"
                value={formData.counter_name || ''}
                onChange={(e) => handleInputChange('counter_name', e.target.value)}
                placeholder="请输入柜位名称"
              />
            </div>

            <div>
              <Label htmlFor="store_id">所属门店</Label>
              <div className="text-sm text-gray-600 p-2 bg-gray-50 rounded">
                {counter ? getStoreName(counter.store_id) : ''}
              </div>
            </div>

            <div>
              <Label htmlFor="floor_id">所属楼层</Label>
              <Select 
                value={formData.floor_id?.toString() || ''} 
                onValueChange={(value) => handleInputChange('floor_id', parseInt(value))}
                disabled={isLoadingFloors}
              >
                <SelectTrigger className="bg-white border-gray-300">
                  <SelectValue placeholder={isLoadingFloors ? "加载中..." : "选择楼层"} />
                </SelectTrigger>
                <SelectContent className="bg-white border border-gray-200 shadow-lg">
                  {floors.map(floor => (
                    <SelectItem key={floor.floor_id} value={floor.floor_id.toString()} className="hover:bg-gray-100">
                      <div className="flex flex-col">
                        <span className="font-medium">
                          {floor.building_name && `${floor.building_name} `}
                          {floor.floor_display_name || floor.floor_name}
                        </span>
                        {floor.building_code && (
                          <span className="text-xs text-gray-500">
                            {floor.building_code}栋 第{floor.floor_number}层
                          </span>
                        )}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="counter_type">柜位类型</Label>
              <Input
                id="counter_type"
                value={formData.counter_type || ''}
                onChange={(e) => handleInputChange('counter_type', e.target.value)}
                placeholder="请输入柜位类型"
              />
            </div>

            <div>
              <Label htmlFor="status">状态</Label>
              <Select value={formData.status || 'vacant'} onValueChange={(value) => handleInputChange('status', value)}>
                <SelectTrigger>
                  <SelectValue placeholder="选择状态" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="vacant">空置</SelectItem>
                  <SelectItem value="occupied">已租用</SelectItem>
                  <SelectItem value="maintenance">维护中</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* 面积信息 */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium">面积信息</h3>
            
            <div>
              <Label htmlFor="area">面积 (㎡)</Label>
              <Input
                id="area"
                type="number"
                step="0.01"
                value={formData.area || ''}
                onChange={(e) => handleInputChange('area', parseFloat(e.target.value) || 0)}
                placeholder="请输入面积"
              />
            </div>
          </div>

          {/* 财务信息 */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium">财务信息</h3>
            
            <div>
              <Label htmlFor="deposit">装修保证金 (¥)</Label>
              <Input
                id="deposit"
                type="number"
                step="0.01"
                value={formData.deposit || ''}
                onChange={(e) => handleInputChange('deposit', parseFloat(e.target.value) || 0)}
                placeholder="请输入装修保证金"
              />
            </div>

            <div>
              <Label htmlFor="monthly_revenue">POS机押金 (¥)</Label>
              <Input
                id="monthly_revenue"
                type="number"
                step="0.01"
                value={formData.monthly_revenue || ''}
                onChange={(e) => handleInputChange('monthly_revenue', parseFloat(e.target.value) || 0)}
                placeholder="请输入POS机押金"
              />
            </div>
          </div>

          {/* 扩展信息 */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium">扩展信息</h3>

            <div>
              <Label>门头图片</Label>
              <ImageUploader
                onGetUploadParameters={handleGetUploadParameters}
                onComplete={handleImageUploadComplete}
                onError={handleImageUploadError}
                currentImageUrl={formData.facade_image_url}
                maxFileSize={5242880} // 5MB
              />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isLoading}>
            取消
          </Button>
          <Button onClick={handleSave} disabled={isLoading}>
            {isLoading ? "保存中..." : "保存"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
