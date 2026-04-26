import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Store } from '@/lib/schema';
import { getApiUrl } from '../lib/api';

interface StoreContextType {
  selectedStore: Store | null;
  selectedStoreId: number | null;
  setSelectedStore: (store: Store | null) => void;
  setSelectedStoreId: (storeId: number | null) => void;
  stores: Store[];
  isLoading: boolean;
  error: any;
  refetch: () => void;
  // 新增：全局筛选状态
  isGlobalFilterEnabled: boolean;
  setGlobalFilterEnabled: (enabled: boolean) => void;
  // 新增：获取当前筛选条件
  getCurrentFilter: () => { storeId: number | null; storeName: string | null };
}

const StoreContext = createContext<StoreContextType | undefined>(undefined);

interface StoreProviderProps {
  children: ReactNode;
}

export function StoreProvider({ children }: StoreProviderProps) {
  const [selectedStore, setSelectedStore] = useState<Store | null>(null);
  const [selectedStoreId, setSelectedStoreId] = useState<number | null>(null);
  const [isGlobalFilterEnabled, setGlobalFilterEnabled] = useState<boolean>(true);

  // 获取门店列表
  const { data: stores, isLoading, error, refetch } = useQuery<Store[]>({
    queryKey: ['/api/stores'],
    queryFn: async () => {
      console.log('StoreContext: 开始获取门店数据...');
      try {
        const response = await fetch(`${getApiUrl()}/api/stores`);
        console.log('StoreContext: API响应状态:', response.status);
        
        if (!response.ok) {
          const errorText = await response.text();
          console.error('StoreContext: API请求失败:', response.status, errorText);
          throw new Error(`Failed to fetch stores: ${response.status} ${errorText}`);
        }
        
        const result = await response.json();
        console.log('StoreContext: API返回数据:', result);
        
        // 处理不同的响应格式：可能是 { data: [...] } 或直接是 [...]
        const data = Array.isArray(result) ? result : (result.data || []);
        console.log('StoreContext: 提取后的门店数据:', data.length, '条');
        
        // 确保 data 是数组
        if (!Array.isArray(data)) {
          console.error('StoreContext: 数据格式错误，期望数组但得到:', typeof data, data);
          return [];
        }
        
        // 转换snake_case到camelCase
        const transformedData = data.map((store: any) => ({
          storeId: store.store_id,
          storeName: store.store_name,
          storeCode: store.store_code,
          address: store.address,
          managerName: store.manager_name,
          contactPhone: store.contact_phone,
          contactEmail: store.contact_email,
          isActive: store.is_active,
          createdAt: store.created_at,
          updatedAt: store.updated_at,
        }));
        
        console.log('StoreContext: 转换后的门店数据:', transformedData);
        return transformedData;
      } catch (error) {
        console.error('StoreContext: 获取门店数据出错:', error);
        throw error;
      }
    },
    retry: 3,
    refetchOnWindowFocus: false,
    staleTime: 5 * 60 * 1000, // 5分钟缓存
  });

  // 当selectedStoreId变化时，自动设置selectedStore
  useEffect(() => {
    if (selectedStoreId && stores) {
      const store = stores.find(s => s.storeId === selectedStoreId);
      setSelectedStore(store || null);
    } else {
      setSelectedStore(null);
    }
  }, [selectedStoreId, stores]);

  // 从URL参数初始化门店选择
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const storeIdParam = params.get('storeId');
    if (storeIdParam && !selectedStoreId) {
      const storeId = parseInt(storeIdParam);
      if (!isNaN(storeId)) {
        setSelectedStoreId(storeId);
      }
    }
  }, []); // 只在组件挂载时执行一次

  const handleSetSelectedStore = (store: Store | null) => {
    setSelectedStore(store);
    setSelectedStoreId(store?.storeId || null);
    
    // 更新URL参数
    const params = new URLSearchParams(window.location.search);
    if (store) {
      params.set('storeId', store.storeId.toString());
    } else {
      params.delete('storeId');
    }
    
    const newUrl = `${window.location.pathname}${params.toString() ? '?' + params.toString() : ''}`;
    window.history.replaceState({}, '', newUrl);
  };

  const handleSetSelectedStoreId = (storeId: number | null) => {
    setSelectedStoreId(storeId);
    
    // 更新URL参数
    const params = new URLSearchParams(window.location.search);
    if (storeId) {
      params.set('storeId', storeId.toString());
    } else {
      params.delete('storeId');
    }
    
    const newUrl = `${window.location.pathname}${params.toString() ? '?' + params.toString() : ''}`;
    window.history.replaceState({}, '', newUrl);
  };

  // 获取当前筛选条件
  const getCurrentFilter = () => {
    if (isGlobalFilterEnabled && selectedStore) {
      return {
        storeId: selectedStore.storeId,
        storeName: selectedStore.storeName
      };
    }
    return {
      storeId: null,
      storeName: null
    };
  };

  const value: StoreContextType = {
    selectedStore,
    selectedStoreId,
    setSelectedStore: handleSetSelectedStore,
    setSelectedStoreId: handleSetSelectedStoreId,
    stores: stores || [],
    isLoading,
    error,
    refetch,
    isGlobalFilterEnabled,
    setGlobalFilterEnabled,
    getCurrentFilter,
  };

  return (
    <StoreContext.Provider value={value}>
      {children}
    </StoreContext.Provider>
  );
}

export function useStore() {
  const context = useContext(StoreContext);
  if (context === undefined) {
    throw new Error('useStore must be used within a StoreProvider');
  }
  return context;
}

export default StoreContext;
