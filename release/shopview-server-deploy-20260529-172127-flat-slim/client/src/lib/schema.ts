// 本地schema定义，用于前端组件
export interface Store {
  storeId: number;
  storeName: string;
  storeCode: string;
  address?: string;
  managerName?: string;
  contactPhone?: string;
  contactEmail?: string;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface Counter {
  counterId: number;
  storeId: number;
  counterNumber: string;
  department: string;
  building: string;
  floor: string;
  area: number;
  status: 'vacant' | 'occupied' | 'maintenance';
  monthlyRent?: number;
  tenantId?: number;
  groupCode?: string;
  groupName?: string;
  description?: string;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface Tenant {
  tenantId: number;
  companyName: string;
  tenantCode: string;
  legalRepresentative?: string;
  contactPerson?: string;
  contactPhone?: string;
  contactEmail?: string;
  address?: string;
  businessCategory?: string;
  isActive: boolean;
  createdAt: string;
  updatedAt?: string;
}

export interface Contract {
  contractId: number;
  tenantId: number;
  counterId?: number;
  hallId?: number;
  contractNumber: string;
  startDate: string;
  endDate: string;
  monthlyRent: number;
  deposit: number;
  status: 'active' | 'expired' | 'terminated';
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface Bill {
  billId: number;
  contractId: number;
  billNumber: string;
  billDate: string;
  dueDate: string;
  amount: number;
  status: 'pending' | 'paid' | 'overdue';
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface Room {
  id: string;
  storeId?: number;
  roomNumber: string;
  name: string;
  area: number;
  tenant?: string;
  status: 'occupied' | 'vacant' | 'maintenance';
  monthlyRevenue?: number;
  revenuePerSqm?: number;
  leaseExpiry?: string;
  contractType?: 'fixed' | 'percentage' | 'hybrid';
  x: number;
  y: number;
  width: number;
  height: number;
  counterId?: number;
  createdAt: string;
  updatedAt: string;
}

// 表单相关的类型定义
export interface InsertCounter {
  storeId: number;
  counterNumber: string;
  department: string;
  building: string;
  floor: string;
  area: string | number;
  status: 'vacant' | 'occupied' | 'maintenance';
  monthlyRent?: string | number;
  groupCode?: string;
  groupName?: string;
  description?: string;
}

export interface UpdateCounter extends Partial<InsertCounter> {
  counterId: number;
}

// Zod schema 验证
export const insertCounterSchema = {
  storeId: { type: 'number', required: true },
  counterNumber: { type: 'string', required: true },
  department: { type: 'string', required: true },
  building: { type: 'string', required: true },
  floor: { type: 'string', required: true },
  area: { type: 'string', required: true },
  status: { type: 'string', required: true },
  monthlyRent: { type: 'string', required: false },
  groupCode: { type: 'string', required: false },
  groupName: { type: 'string', required: false },
  description: { type: 'string', required: false }
};
