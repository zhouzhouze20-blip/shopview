import { useState, useEffect } from "react";
import { useStore } from "@/contexts/StoreContext";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Building2, Filter, X } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

interface GlobalStoreSelectorProps {
  className?: string;
  showFilterToggle?: boolean;
  compact?: boolean;
}

export function GlobalStoreSelector({ 
  className = "", 
  showFilterToggle = true,
  compact = false 
}: GlobalStoreSelectorProps) {
  const { 
    selectedStoreId, 
    setSelectedStoreId, 
    stores, 
    isLoading,
    isGlobalFilterEnabled,
    setGlobalFilterEnabled,
    getCurrentFilter
  } = useStore();

  const currentFilter = getCurrentFilter();

  // 处理门店选择
  const handleStoreChange = (value: string) => {
    if (value === "all") {
      setSelectedStoreId(null);
    } else {
      setSelectedStoreId(parseInt(value));
    }
  };

  // 清除筛选
  const handleClearFilter = () => {
    setSelectedStoreId(null);
    setGlobalFilterEnabled(false);
  };

  if (compact) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <Building2 className="h-4 w-4 text-muted-foreground" />
        <Select
          value={selectedStoreId?.toString() || "all"}
          onValueChange={handleStoreChange}
          disabled={isLoading}
        >
          <SelectTrigger className="w-[200px] bg-white border-gray-300 hover:border-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-200">
            <SelectValue placeholder={isLoading ? "加载中..." : "选择门店"} />
          </SelectTrigger>
          <SelectContent className="bg-white border border-gray-200 shadow-lg">
            <SelectItem value="all" className="hover:bg-gray-100">全部门店</SelectItem>
            {stores.map(store => (
              <SelectItem key={store.storeId} value={store.storeId.toString()} className="hover:bg-gray-100">
                {store.storeName}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {showFilterToggle && (
          <div className="flex items-center gap-2">
            <Switch
              id="global-filter"
              checked={isGlobalFilterEnabled}
              onCheckedChange={setGlobalFilterEnabled}
            />
            <Label htmlFor="global-filter" className="text-sm">
              全局筛选
            </Label>
          </div>
        )}
      </div>
    );
  }

  return (
    <Card className={`${className}`}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Building2 className="h-5 w-5 text-muted-foreground" />
              <span className="font-medium">门店筛选</span>
            </div>
            
            <Select
              value={selectedStoreId?.toString() || "all"}
              onValueChange={handleStoreChange}
              disabled={isLoading}
            >
              <SelectTrigger className="w-[250px] bg-white border-gray-300 hover:border-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-200">
                <SelectValue placeholder={isLoading ? "加载中..." : "选择门店"} />
              </SelectTrigger>
              <SelectContent className="bg-white border border-gray-200 shadow-lg">
                <SelectItem value="all" className="hover:bg-gray-100">全部门店</SelectItem>
                {stores.map(store => (
                  <SelectItem key={store.storeId} value={store.storeId.toString()} className="hover:bg-gray-100">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{store.storeName}</span>
                      <span className="text-xs text-muted-foreground">
                        ({store.storeCode})
                      </span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {showFilterToggle && (
              <div className="flex items-center gap-2">
                <Switch
                  id="global-filter"
                  checked={isGlobalFilterEnabled}
                  onCheckedChange={setGlobalFilterEnabled}
                />
                <Label htmlFor="global-filter" className="text-sm">
                  启用全局筛选
                </Label>
              </div>
            )}
          </div>

          {currentFilter.storeId && (
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-2 px-3 py-1 bg-blue-50 text-blue-700 rounded-md text-sm">
                <Filter className="h-4 w-4" />
                <span>当前筛选: {currentFilter.storeName}</span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleClearFilter}
                className="h-8 w-8 p-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default GlobalStoreSelector;
