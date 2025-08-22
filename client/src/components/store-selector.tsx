import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Store } from "@shared/schema";
import { Building2 } from "lucide-react";

interface StoreSelectorProps {
  selectedStoreId?: number;
  onStoreChange: (storeId: number | undefined) => void;
  placeholder?: string;
  className?: string;
}

export function StoreSelector({
  selectedStoreId,
  onStoreChange,
  placeholder = "选择门店",
  className = "",
}: StoreSelectorProps) {
  const { data: stores, isLoading } = useQuery<Store[]>({
    queryKey: ['/api/stores'],
  });

  const selectedStore = stores?.find(store => store.storeId === selectedStoreId);

  return (
    <div className={`flex items-center gap-2 ${className}`} data-testid="store-selector">
      <Building2 className="h-4 w-4 text-muted-foreground" />
      <Select
        value={selectedStoreId?.toString() || ""}
        onValueChange={(value) => {
          if (value === "all") {
            onStoreChange(undefined);
          } else {
            onStoreChange(parseInt(value));
          }
        }}
        disabled={isLoading}
      >
        <SelectTrigger className="w-[200px]" data-testid="store-selector-trigger">
          <SelectValue placeholder={isLoading ? "加载中..." : placeholder} />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all" data-testid="store-option-all">
            所有门店
          </SelectItem>
          {stores?.map((store) => (
            <SelectItem 
              key={store.storeId} 
              value={store.storeId.toString()}
              data-testid={`store-option-${store.storeId}`}
            >
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
      
      {selectedStore && (
        <div className="text-sm text-muted-foreground" data-testid="selected-store-info">
          当前: {selectedStore.storeName}
        </div>
      )}
    </div>
  );
}

export default StoreSelector;