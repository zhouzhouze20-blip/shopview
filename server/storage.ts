import { 
  type Room, type InsertRoom, 
  type FloorPlan, type InsertFloorPlan, 
  type Activity, type InsertActivity,
  type User, type InsertUser,
  type Store, type InsertStore,
  type Counter, type InsertCounter,
  type Hall, type InsertHall,
  type Tenant, type InsertTenant,
  type Brand, type InsertBrand,
  type Contract, type InsertContract,
  type Floor, type InsertFloor,
  type SpaceAsset, type InsertSpaceAsset,
  type UserMarkedRoom, type NewUserMarkedRoom,
  userMarkedRooms
} from "@shared/schema";
import { randomUUID } from "crypto";
import { drizzle } from "drizzle-orm/neon-http";
import { neon } from "@neondatabase/serverless";
import { eq } from "drizzle-orm";

export interface IStorage {
  // User methods (keeping for compatibility)
  getUser(userId: number): Promise<User | undefined>;
  getUserByUsername(username: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;
  
  // Store methods
  getAllStores(): Promise<Store[]>;
  getStore(storeId: number): Promise<Store | undefined>;
  createStore(store: InsertStore): Promise<Store>;
  updateStore(storeId: number, store: Partial<InsertStore>): Promise<Store>;
  
  // Counter methods (柜位管理)
  getAllCounters(storeId?: number): Promise<Counter[]>;
  getCounter(counterId: number): Promise<Counter | undefined>;
  createCounter(counter: InsertCounter): Promise<Counter>;
  updateCounter(counterId: number, counter: Partial<InsertCounter>): Promise<Counter>;
  deleteCounter(counterId: number): Promise<boolean>;
  searchCounters(query: string, storeId?: number): Promise<Counter[]>;
  getCountersByDepartment(department: string, storeId?: number): Promise<Counter[]>;
  
  // Hall methods (厅房管理)
  getAllHalls(storeId?: number): Promise<Hall[]>;
  getHall(hallId: number): Promise<Hall | undefined>;
  createHall(hall: InsertHall): Promise<Hall>;
  updateHall(hallId: number, hall: Partial<InsertHall>): Promise<Hall>;
  searchHalls(query: string, storeId?: number): Promise<Hall[]>;
  
  // Tenant methods
  getAllTenants(): Promise<Tenant[]>;
  getTenant(tenantId: number): Promise<Tenant | undefined>;
  createTenant(tenant: InsertTenant): Promise<Tenant>;
  updateTenant(tenantId: number, tenant: Partial<InsertTenant>): Promise<Tenant>;
  searchTenants(query: string): Promise<Tenant[]>;

  // Brand methods
  getAllBrands(): Promise<Brand[]>;
  getBrand(brandId: number): Promise<Brand | undefined>;
  createBrand(brand: InsertBrand): Promise<Brand>;
  updateBrand(brandId: number, brand: Partial<InsertBrand>): Promise<Brand>;

  // Contract methods
  getAllContracts(): Promise<Contract[]>;
  getContract(contractId: number): Promise<Contract | undefined>;
  createContract(contract: InsertContract): Promise<Contract>;
  updateContract(contractId: number, contract: Partial<InsertContract>): Promise<Contract>;
  getContractsByTenant(tenantId: number): Promise<Contract[]>;

  // Floor methods (new architecture)
  getAllFloors(): Promise<Floor[]>;
  getFloor(floorId: number): Promise<Floor | undefined>;
  createFloor(floor: InsertFloor): Promise<Floor>;

  // Space Asset methods (new architecture)
  getAllSpaceAssets(): Promise<SpaceAsset[]>;
  getSpaceAsset(spaceId: number): Promise<SpaceAsset | undefined>;
  createSpaceAsset(spaceAsset: InsertSpaceAsset): Promise<SpaceAsset>;
  getSpaceAssetsByFloor(floorId: number): Promise<SpaceAsset[]>;
  
  // Room methods (legacy compatibility)
  getAllRooms(storeId?: number): Promise<Room[]>;
  getRoom(id: string): Promise<Room | undefined>;
  getRoomByNumber(roomNumber: string, storeId?: number): Promise<Room | undefined>;
  createRoom(room: InsertRoom): Promise<Room>;
  updateRoom(id: string, room: Partial<InsertRoom>): Promise<Room>;
  deleteRoom(id: string): Promise<boolean>;
  searchRooms(query: string, storeId?: number): Promise<Room[]>;
  
  // Floor plan methods (legacy compatibility)
  getAllFloorPlans(storeId?: number): Promise<FloorPlan[]>;
  getFloorPlan(id: string): Promise<FloorPlan | undefined>;
  getActiveFloorPlan(storeId?: number): Promise<FloorPlan | undefined>;
  createFloorPlan(floorPlan: InsertFloorPlan): Promise<FloorPlan>;
  updateFloorPlan(id: string, floorPlan: Partial<InsertFloorPlan>): Promise<FloorPlan>;
  activateFloorPlan(id: string): Promise<FloorPlan>;
  deactivateFloorPlan(id: string): Promise<FloorPlan>;
  
  // Activity methods
  getRecentActivities(limit?: number): Promise<Activity[]>;
  createActivity(activity: InsertActivity): Promise<Activity>;
  
  // Analytics methods
  getStats(storeId?: number): Promise<{
    totalRooms: number;
    occupied: number;
    vacant: number;
    avgRevenue: number;
  }>;

  // User marked rooms methods (用户标记厅房)
  getUserMarkedRooms(storeId?: number, floorPlanId?: string): Promise<UserMarkedRoom[]>;
  createUserMarkedRoom(markedRoom: NewUserMarkedRoom): Promise<UserMarkedRoom>;
  updateUserMarkedRoom(id: string, markedRoom: Partial<NewUserMarkedRoom>): Promise<UserMarkedRoom>;
  deleteUserMarkedRoom(id: string): Promise<void>;
}

export class MemStorage implements IStorage {
  private users: Map<number, User>;
  private stores: Map<number, Store>;
  private counters: Map<number, Counter>;
  private halls: Map<number, Hall>;
  private tenants: Map<number, Tenant>;
  private brands: Map<number, Brand>;
  private contracts: Map<number, Contract>;
  private floors: Map<number, Floor>;
  private spaceAssets: Map<number, SpaceAsset>;
  private rooms: Map<string, Room>;
  private floorPlans: Map<string, FloorPlan>;
  private activities: Map<string, Activity>;
  private userMarkedRooms: Map<string, UserMarkedRoom>;
  private db: any;

  constructor() {
    this.users = new Map();
    this.stores = new Map();
    this.counters = new Map();
    this.halls = new Map();
    this.tenants = new Map();
    this.brands = new Map();
    this.contracts = new Map();
    this.floors = new Map();
    this.spaceAssets = new Map();
    this.rooms = new Map();
    this.floorPlans = new Map();
    this.activities = new Map();
    this.userMarkedRooms = new Map();
    
    // Initialize database connection if DATABASE_URL is available
    if (process.env.DATABASE_URL) {
      const connection = neon(process.env.DATABASE_URL);
      this.db = drizzle(connection);
    }
    
    // Initialize with sample data
    this.initializeData();
  }

  private initializeData() {
    // Initialize sample stores (门店数据)
    const sampleStores: (Omit<Store, 'storeId' | 'createdAt' | 'updatedAt'>)[] = [
      {
        storeName: "常州购物中心",
        storeCode: "CZ001",
        address: "江苏省常州市新北区中央商务区",
        managerName: "张经理",
        contactPhone: "0519-12345678",
        contactEmail: "cz001@counter-mgmt.com",
        isActive: true
      },
      {
        storeName: "常州新世纪",
        storeCode: "CZ002", 
        address: "江苏省常州市天宁区新世纪商业广场",
        managerName: "李经理",
        contactPhone: "0519-87654321",
        contactEmail: "cz002@counter-mgmt.com",
        isActive: true
      },
      {
        storeName: "常州百货大楼",
        storeCode: "CZ003",
        address: "江苏省常州市钟楼区南大街百货大楼",
        managerName: "王经理", 
        contactPhone: "0519-11223344",
        contactEmail: "cz003@counter-mgmt.com",
        isActive: true
      },
      {
        storeName: "常州半山数据",
        storeCode: "CZ004",
        address: "江苏省常州市武进区半山数据中心",
        managerName: "赵经理",
        contactPhone: "0519-55667788", 
        contactEmail: "cz004@counter-mgmt.com",
        isActive: true
      }
    ];

    let storeIdCounter = 1;
    sampleStores.forEach(storeData => {
      const store: Store = {
        ...storeData,
        storeId: storeIdCounter++,
        createdAt: new Date(),
        updatedAt: new Date()
      };
      this.stores.set(store.storeId, store);
    });

    // Initialize sample tenants
    const sampleTenants: (Omit<Tenant, 'tenantId' | 'createdAt' | 'updatedAt'>)[] = [
      {
        companyName: "科技世界有限公司",
        tenantCode: "TW001",
        legalRepresentative: "张三",
        contactPerson: "李四",
        contactPhone: "13800138001",
        contactEmail: "contact@techworld.com",
        businessLicense: "91310000123456789X",
        address: "上海市浦东新区张江路123号",
        isActive: true
      },
      {
        companyName: "时尚佳人服饰",
        tenantCode: "SP001", 
        legalRepresentative: "王五",
        contactPerson: "赵六",
        contactPhone: "13800138002",
        contactEmail: "info@styleplus.com",
        businessLicense: "91310000987654321Y",
        address: "上海市黄浦区南京路456号",
        isActive: true
      }
    ];

    let tenantIdCounter = 1;
    sampleTenants.forEach(tenantData => {
      const tenant: Tenant = {
        ...tenantData,
        tenantId: tenantIdCounter++,
        createdAt: new Date(),
        updatedAt: new Date()
      };
      this.tenants.set(tenant.tenantId, tenant);
    });

    // Initialize sample brands
    const sampleBrands: (Omit<Brand, 'brandId' | 'createdAt'>)[] = [
      {
        brandName: "TechWorld",
        brandNameEn: "TechWorld",
        category: "电子产品",
        description: "专业电子产品零售",
        isActive: true,
        logoUrl: null
      },
      {
        brandName: "时尚佳人",
        brandNameEn: "Style Plus",
        category: "服装",
        description: "时尚女装品牌",
        isActive: true,
        logoUrl: null
      }
    ];

    let brandIdCounter = 1;
    sampleBrands.forEach(brandData => {
      const brand: Brand = {
        ...brandData,
        brandId: brandIdCounter++,
        createdAt: new Date()
      };
      this.brands.set(brand.brandId, brand);
    });

    // Initialize sample floors for each store
    const sampleFloors: (Omit<Floor, 'floorId' | 'createdAt'>)[] = [
      // 常州购物中心 (storeId: 1)
      {
        storeId: 1,
        floorName: "L1",
        displayOrder: 1,
        description: "购物中心一层"
      },
      {
        storeId: 1,
        floorName: "L2", 
        displayOrder: 2,
        description: "购物中心二层"
      },
      // 常州新世纪 (storeId: 2)
      {
        storeId: 2,
        floorName: "1F",
        displayOrder: 1,
        description: "新世纪一楼"
      },
      {
        storeId: 2,
        floorName: "2F", 
        displayOrder: 2,
        description: "新世纪二楼"
      }
    ];

    let floorIdCounter = 1;
    sampleFloors.forEach(floorData => {
      const floor: Floor = {
        ...floorData,
        floorId: floorIdCounter++,
        createdAt: new Date()
      };
      this.floors.set(floor.floorId, floor);
    });

    // Create default floor plan for store 1 (常州购物中心)
    const floorPlan: FloorPlan = {
      id: randomUUID(),
      storeId: 1, // 关联到常州购物中心
      name: "常州购物中心 L1层",
      planVersion: "1.0",
      level: "L1",
      floorNumber: 1,
      imageUrl: "/objects/uploads/1e7d422a-b780-4647-81bc-742863a78bb5",
      description: "商场一楼主要区域平面图",
      isActive: true,
      effectiveDate: new Date(),
      expiryDate: null,
      createdBy: "system",
      approvedBy: null,
      approvedAt: null,
      createdAt: new Date(),
      updatedAt: new Date()
    };
    this.floorPlans.set(floorPlan.id, floorPlan);

    // Create sample rooms (添加storeId关联)
    const sampleRooms: Omit<Room, 'id' | 'createdAt' | 'updatedAt'>[] = [
      {
        storeId: 1, // 常州购物中心
        roomNumber: "A-101",
        name: "Electronics Store",
        area: "120.00",
        tenant: "Tech World",
        status: "occupied",
        monthlyRevenue: "28500.00",
        revenuePerSqm: "237.50",
        leaseExpiry: "2024-12-31",
        contractType: "fixed",
        x: "10.00",
        y: "15.00",
        width: "12.00",
        height: "15.00"
      },
      {
        storeId: 1, // 常州购物中心
        roomNumber: "A-102",
        name: "Fashion Boutique",
        area: "150.00",
        tenant: "Style Plus",
        status: "occupied",
        monthlyRevenue: "22800.00",
        revenuePerSqm: "152.00",
        leaseExpiry: "2025-06-30",
        contractType: "percentage",
        x: "25.00",
        y: "15.00",
        width: "15.00",
        height: "15.00"
      },
      {
        storeId: 1, // 常州购物中心
        roomNumber: "A-103",
        name: "Coffee Shop",
        area: "80.00",
        tenant: "Bean Counter",
        status: "occupied",
        monthlyRevenue: "6400.00",
        revenuePerSqm: "80.00",
        leaseExpiry: "2024-08-15",
        contractType: "fixed",
        x: "43.00",
        y: "15.00",
        width: "10.00",
        height: "15.00"
      },
      {
        storeId: 1, // 常州购物中心
        roomNumber: "A-104",
        name: "Vacant Space",
        area: "200.00",
        tenant: null,
        status: "vacant",
        monthlyRevenue: "0.00",
        revenuePerSqm: "0.00",
        leaseExpiry: null,
        contractType: null,
        x: "56.00",
        y: "15.00",
        width: "18.00",
        height: "15.00"
      },
      {
        storeId: 2, // 常州新世纪
        roomNumber: "B-201",
        name: "Department Store",
        area: "300.00",
        tenant: "MegaMart",
        status: "occupied",
        monthlyRevenue: "75000.00",
        revenuePerSqm: "250.00",
        leaseExpiry: "2025-12-31",
        contractType: "fixed",
        x: "10.00",
        y: "35.00",
        width: "20.00",
        height: "18.00"
      },
      {
        storeId: 2, // 常州新世纪
        roomNumber: "B-202",
        name: "Bookstore",
        area: "90.00",
        tenant: "Page Turner",
        status: "occupied",
        monthlyRevenue: "13500.00",
        revenuePerSqm: "150.00",
        leaseExpiry: "2024-09-30",
        contractType: "fixed",
        x: "33.00",
        y: "35.00",
        width: "16.00",
        height: "18.00"
      },
      {
        storeId: 2, // 常州新世纪
        roomNumber: "B-203",
        name: "Jewelry Store",
        area: "110.00",
        tenant: "Sparkle & Co",
        status: "occupied",
        monthlyRevenue: "33000.00",
        revenuePerSqm: "300.00",
        leaseExpiry: "2025-03-31",
        contractType: "percentage",
        x: "52.00",
        y: "35.00",
        width: "22.00",
        height: "18.00"
      },
      {
        storeId: 3, // 常州百货大楼
        roomNumber: "C-301",
        name: "Phone Repair",
        area: "45.00",
        tenant: "Fix It Fast",
        status: "occupied",
        monthlyRevenue: "4500.00",
        revenuePerSqm: "100.00",
        leaseExpiry: "2024-06-30",
        contractType: "fixed",
        x: "15.00",
        y: "58.00",
        width: "14.00",
        height: "12.00"
      },
      {
        storeId: 3, // 常州百货大楼
        roomNumber: "C-302",
        name: "Gift Shop",
        area: "60.00",
        tenant: "Memories",
        status: "occupied",
        monthlyRevenue: "9000.00",
        revenuePerSqm: "150.00",
        leaseExpiry: "2024-11-30",
        contractType: "fixed",
        x: "32.00",
        y: "58.00",
        width: "12.00",
        height: "12.00"
      },
      {
        storeId: 4, // 常州半山数据
        roomNumber: "C-303",
        name: "Shoe Store",
        area: "85.00",
        tenant: "Step Forward",
        status: "occupied",
        monthlyRevenue: "25500.00",
        revenuePerSqm: "300.00",
        leaseExpiry: "2025-07-31",
        contractType: "percentage",
        x: "47.00",
        y: "58.00",
        width: "16.00",
        height: "12.00"
      },
      {
        storeId: 4, // 常州半山数据
        roomNumber: "C-304",
        name: "Small Space",
        area: "30.00",
        tenant: null,
        status: "vacant",
        monthlyRevenue: "0.00",
        revenuePerSqm: "0.00",
        leaseExpiry: null,
        contractType: null,
        x: "66.00",
        y: "58.00",
        width: "8.00",
        height: "12.00"
      }
    ];

    sampleRooms.forEach(roomData => {
      const room: Room = {
        id: randomUUID(),
        ...roomData,
        createdAt: new Date(),
        updatedAt: new Date()
      };
      this.rooms.set(room.id, room);
    });

    // Initialize sample counters (柜位数据)
    const sampleCounters: (Omit<Counter, 'counterId' | 'createdAt' | 'updatedAt'>)[] = [
      // 常州购物中心 (storeId: 1)
      {
        storeId: 1,
        counterNumber: "A001",
        department: "服装部",
        building: "A栋",
        floor: "1F",
        area: "25.50",
        status: "occupied",
        monthlyRent: "8500.00",
        tenantId: 1, // TechWorld
        description: "主要销售时尚女装",
        isActive: true
      },
      {
        storeId: 1,
        counterNumber: "A002",
        department: "服装部",
        building: "A栋",
        floor: "1F",
        area: "30.00",
        status: "vacant",
        monthlyRent: "9000.00",
        tenantId: null,
        description: "空置柜位，待租",
        isActive: true
      },
      {
        storeId: 1,
        counterNumber: "A003",
        department: "电子产品部",
        building: "A栋",
        floor: "2F",
        area: "20.00",
        status: "occupied",
        monthlyRent: "7500.00",
        tenantId: 1, // TechWorld
        description: "主要销售数码产品",
        isActive: true
      },
      {
        storeId: 1,
        counterNumber: "B001",
        department: "化妆品部",
        building: "B栋",
        floor: "1F",
        area: "15.00",
        status: "maintenance",
        monthlyRent: "6000.00",
        tenantId: null,
        description: "装修中，预计下月完成",
        isActive: true
      },
      // 常州新世纪 (storeId: 2)
      {
        storeId: 2,
        counterNumber: "C101",
        department: "珠宝部",
        building: "C栋",
        floor: "1F",
        area: "12.00",
        status: "occupied",
        monthlyRent: "12000.00",
        tenantId: 2, // 时尚佳人
        description: "高端珠宝专柜",
        isActive: true
      },
      {
        storeId: 2,
        counterNumber: "C102",
        department: "珠宝部",
        building: "C栋",
        floor: "1F",
        area: "10.00",
        status: "vacant",
        monthlyRent: "10000.00",
        tenantId: null,
        description: "小型珠宝展示柜",
        isActive: true
      },
      {
        storeId: 2,
        counterNumber: "D201",
        department: "运动用品部",
        building: "D栋",
        floor: "2F",
        area: "40.00",
        status: "occupied",
        monthlyRent: "15000.00",
        tenantId: null,
        description: "运动服装和器材",
        isActive: true
      }
    ];

    let counterIdCounter = 1;
    sampleCounters.forEach(counterData => {
      const counter: Counter = {
        ...counterData,
        counterId: counterIdCounter++,
        createdAt: new Date(),
        updatedAt: new Date()
      };
      this.counters.set(counter.counterId, counter);
    });

    // Create sample activities
    const sampleActivities: Omit<Activity, 'id' | 'createdAt'>[] = [
      {
        roomId: Array.from(this.rooms.values())[0].id,
        type: "lease_renewal",
        description: "Room A-101 lease renewed"
      },
      {
        roomId: Array.from(this.rooms.values())[1].id,
        type: "payment_received",
        description: "Room B-202 payment received"
      },
      {
        roomId: Array.from(this.rooms.values())[2].id,
        type: "maintenance_request",
        description: "Room C-301 maintenance request"
      }
    ];

    sampleActivities.forEach(activityData => {
      const activity: Activity = {
        id: randomUUID(),
        ...activityData,
        createdAt: new Date()
      };
      this.activities.set(activity.id, activity);
    });
  }

  // User methods
  async getUser(userId: number): Promise<User | undefined> {
    return this.users.get(userId);
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    return Array.from(this.users.values()).find(
      (user) => user.username === username,
    );
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const userId = Math.floor(Math.random() * 1000000); // Simple ID generation for testing
    const user: User = { 
      ...insertUser,
      userId,
      isActive: insertUser.isActive ?? true,
      roleId: insertUser.roleId ?? null,
      createdAt: new Date(),
      updatedAt: new Date()
    };
    this.users.set(userId, user);
    return user;
  }

  // Store methods (门店管理)
  async getAllStores(): Promise<Store[]> {
    return Array.from(this.stores.values());
  }

  async getStore(storeId: number): Promise<Store | undefined> {
    return this.stores.get(storeId);
  }

  async createStore(insertStore: InsertStore): Promise<Store> {
    const storeId = Math.floor(Math.random() * 1000000);
    const store: Store = {
      ...insertStore,
      storeId,
      isActive: insertStore.isActive ?? true,
      managerName: insertStore.managerName ?? null,
      contactPhone: insertStore.contactPhone ?? null,
      contactEmail: insertStore.contactEmail ?? null,
      address: insertStore.address ?? null,
      createdAt: new Date(),
      updatedAt: new Date()
    };
    this.stores.set(storeId, store);
    return store;
  }

  async updateStore(storeId: number, storeUpdate: Partial<InsertStore>): Promise<Store> {
    const existingStore = this.stores.get(storeId);
    if (!existingStore) {
      throw new Error(`Store with id ${storeId} not found`);
    }
    
    const updatedStore: Store = {
      ...existingStore,
      ...storeUpdate,
      updatedAt: new Date()
    };
    this.stores.set(storeId, updatedStore);
    return updatedStore;
  }

  // Counter methods (柜位管理)
  async getAllCounters(storeId?: number): Promise<Counter[]> {
    const counters = Array.from(this.counters.values());
    if (storeId) {
      return counters.filter(counter => counter.storeId === storeId);
    }
    return counters;
  }

  async getCounter(counterId: number): Promise<Counter | undefined> {
    return this.counters.get(counterId);
  }

  async createCounter(insertCounter: InsertCounter): Promise<Counter> {
    const counterId = Math.floor(Math.random() * 1000000);
    const counter: Counter = {
      ...insertCounter,
      counterId,
      status: insertCounter.status ?? "vacant",
      tenantId: insertCounter.tenantId ?? null,
      monthlyRent: insertCounter.monthlyRent ?? null,
      description: insertCounter.description ?? null,
      isActive: insertCounter.isActive ?? true,
      createdAt: new Date(),
      updatedAt: new Date()
    };
    this.counters.set(counterId, counter);
    return counter;
  }

  async updateCounter(counterId: number, counterUpdate: Partial<InsertCounter>): Promise<Counter> {
    const existingCounter = this.counters.get(counterId);
    if (!existingCounter) {
      throw new Error(`Counter with id ${counterId} not found`);
    }
    
    const updatedCounter: Counter = {
      ...existingCounter,
      ...counterUpdate,
      updatedAt: new Date()
    };
    this.counters.set(counterId, updatedCounter);
    return updatedCounter;
  }

  async deleteCounter(counterId: number): Promise<boolean> {
    return this.counters.delete(counterId);
  }

  async searchCounters(query: string, storeId?: number): Promise<Counter[]> {
    const counters = await this.getAllCounters(storeId);
    const lowercaseQuery = query.toLowerCase();
    return counters.filter(counter => 
      counter.counterNumber.toLowerCase().includes(lowercaseQuery) ||
      counter.department.toLowerCase().includes(lowercaseQuery) ||
      counter.building.toLowerCase().includes(lowercaseQuery) ||
      counter.floor.toLowerCase().includes(lowercaseQuery)
    );
  }

  async getCountersByDepartment(department: string, storeId?: number): Promise<Counter[]> {
    const counters = await this.getAllCounters(storeId);
    return counters.filter(counter => counter.department === department);
  }

  // Hall methods (厅房管理)
  async getAllHalls(storeId?: number): Promise<Hall[]> {
    const allHalls = Array.from(this.halls.values());
    return storeId ? allHalls.filter(hall => hall.storeId === storeId) : allHalls;
  }

  async getHall(hallId: number): Promise<Hall | undefined> {
    return this.halls.get(hallId);
  }

  async createHall(insertHall: InsertHall): Promise<Hall> {
    const hallId = Math.floor(Math.random() * 1000000);
    const hall: Hall = {
      ...insertHall,
      hallId,
      status: insertHall.status || 'vacant',
      isActive: insertHall.isActive ?? true,
      floorId: insertHall.floorId ?? null,
      monthlyRent: insertHall.monthlyRent ?? null,
      createdAt: new Date(),
      updatedAt: new Date()
    };
    this.halls.set(hallId, hall);
    return hall;
  }

  async updateHall(hallId: number, hallUpdate: Partial<InsertHall>): Promise<Hall> {
    const existingHall = this.halls.get(hallId);
    if (!existingHall) {
      throw new Error(`Hall with id ${hallId} not found`);
    }
    
    const updatedHall: Hall = {
      ...existingHall,
      ...hallUpdate,
      updatedAt: new Date()
    };
    this.halls.set(hallId, updatedHall);
    return updatedHall;
  }

  async searchHalls(query: string, storeId?: number): Promise<Hall[]> {
    const lowerQuery = query.toLowerCase();
    let halls = Array.from(this.halls.values());
    
    if (storeId) {
      halls = halls.filter(hall => hall.storeId === storeId);
    }
    
    return halls.filter(hall =>
      hall.hallCode.toLowerCase().includes(lowerQuery) ||
      hall.hallName.toLowerCase().includes(lowerQuery)
    );
  }

  // Tenant methods
  async getAllTenants(): Promise<Tenant[]> {
    return Array.from(this.tenants.values());
  }

  async getTenant(tenantId: number): Promise<Tenant | undefined> {
    return this.tenants.get(tenantId);
  }

  async createTenant(insertTenant: InsertTenant): Promise<Tenant> {
    const tenantId = Math.floor(Math.random() * 1000000); // Simple ID generation for testing
    const tenant: Tenant = {
      ...insertTenant,
      tenantId,
      isActive: insertTenant.isActive ?? true,
      legalRepresentative: insertTenant.legalRepresentative ?? null,
      businessLicense: insertTenant.businessLicense ?? null,
      contactPerson: insertTenant.contactPerson ?? null,
      contactPhone: insertTenant.contactPhone ?? null,
      contactEmail: insertTenant.contactEmail ?? null,
      address: insertTenant.address ?? null,
      createdAt: new Date(),
      updatedAt: new Date()
    };
    this.tenants.set(tenantId, tenant);
    return tenant;
  }

  async updateTenant(tenantId: number, tenantUpdate: Partial<InsertTenant>): Promise<Tenant> {
    const existingTenant = this.tenants.get(tenantId);
    if (!existingTenant) {
      throw new Error(`Tenant with id ${tenantId} not found`);
    }
    
    const updatedTenant: Tenant = {
      ...existingTenant,
      ...tenantUpdate,
      updatedAt: new Date()
    };
    this.tenants.set(tenantId, updatedTenant);
    return updatedTenant;
  }

  async searchTenants(query: string): Promise<Tenant[]> {
    const lowerQuery = query.toLowerCase();
    return Array.from(this.tenants.values()).filter(tenant =>
      tenant.companyName.toLowerCase().includes(lowerQuery) ||
      tenant.tenantCode.toLowerCase().includes(lowerQuery) ||
      (tenant.contactPerson && tenant.contactPerson.toLowerCase().includes(lowerQuery))
    );
  }

  // Brand methods
  async getAllBrands(): Promise<Brand[]> {
    return Array.from(this.brands.values());
  }

  async getBrand(brandId: number): Promise<Brand | undefined> {
    return this.brands.get(brandId);
  }

  async createBrand(insertBrand: InsertBrand): Promise<Brand> {
    const brandId = Math.floor(Math.random() * 1000000); // Simple ID generation for testing
    const brand: Brand = {
      ...insertBrand,
      brandId,
      brandNameEn: insertBrand.brandNameEn ?? null,
      category: insertBrand.category ?? null,
      logoUrl: insertBrand.logoUrl ?? null,
      description: insertBrand.description ?? null,
      isActive: insertBrand.isActive ?? true,
      createdAt: new Date()
    };
    this.brands.set(brandId, brand);
    return brand;
  }

  async updateBrand(brandId: number, brandUpdate: Partial<InsertBrand>): Promise<Brand> {
    const existingBrand = this.brands.get(brandId);
    if (!existingBrand) {
      throw new Error(`Brand with id ${brandId} not found`);
    }
    
    const updatedBrand: Brand = {
      ...existingBrand,
      ...brandUpdate
    };
    this.brands.set(brandId, updatedBrand);
    return updatedBrand;
  }

  // Contract methods
  async getAllContracts(): Promise<Contract[]> {
    return Array.from(this.contracts.values());
  }

  async getContract(contractId: number): Promise<Contract | undefined> {
    return this.contracts.get(contractId);
  }

  async createContract(insertContract: InsertContract): Promise<Contract> {
    const contractId = Math.floor(Math.random() * 1000000); // Simple ID generation for testing
    const contract: Contract = {
      ...insertContract,
      contractId,
      status: insertContract.status || "Draft",
      brandId: insertContract.brandId ?? null,
      freeRentDays: insertContract.freeRentDays ?? null,
      securityDeposit: insertContract.securityDeposit ?? null,
      notes: insertContract.notes ?? null,
      createdAt: new Date(),
      updatedAt: new Date()
    };
    this.contracts.set(contractId, contract);
    return contract;
  }

  async updateContract(contractId: number, contractUpdate: Partial<InsertContract>): Promise<Contract> {
    const existingContract = this.contracts.get(contractId);
    if (!existingContract) {
      throw new Error(`Contract with id ${contractId} not found`);
    }
    
    const updatedContract: Contract = {
      ...existingContract,
      ...contractUpdate,
      updatedAt: new Date()
    };
    this.contracts.set(contractId, updatedContract);
    return updatedContract;
  }

  async getContractsByTenant(tenantId: number): Promise<Contract[]> {
    return Array.from(this.contracts.values()).filter(contract =>
      contract.tenantId === tenantId
    );
  }

  // Floor methods (new architecture)
  async getAllFloors(): Promise<Floor[]> {
    return Array.from(this.floors.values());
  }

  async getFloor(floorId: number): Promise<Floor | undefined> {
    return this.floors.get(floorId);
  }

  async createFloor(insertFloor: InsertFloor): Promise<Floor> {
    const floorId = Math.floor(Math.random() * 1000000); // Simple ID generation for testing
    const floor: Floor = {
      ...insertFloor,
      floorId,
      displayOrder: insertFloor.displayOrder ?? null,
      description: insertFloor.description ?? null,
      createdAt: new Date()
    };
    this.floors.set(floorId, floor);
    return floor;
  }

  // Space Asset methods (new architecture)
  async getAllSpaceAssets(): Promise<SpaceAsset[]> {
    return Array.from(this.spaceAssets.values());
  }

  async getSpaceAsset(spaceId: number): Promise<SpaceAsset | undefined> {
    return this.spaceAssets.get(spaceId);
  }

  async createSpaceAsset(insertSpaceAsset: InsertSpaceAsset): Promise<SpaceAsset> {
    const spaceId = Math.floor(Math.random() * 1000000); // Simple ID generation for testing
    const spaceAsset: SpaceAsset = {
      ...insertSpaceAsset,
      spaceId,
      spaceType: insertSpaceAsset.spaceType || "Leasable",
      status: insertSpaceAsset.status || "Active",
      effectiveEndDate: insertSpaceAsset.effectiveEndDate ?? null,
      createdAt: new Date()
    };
    this.spaceAssets.set(spaceId, spaceAsset);
    return spaceAsset;
  }

  async getSpaceAssetsByFloor(floorId: number): Promise<SpaceAsset[]> {
    return Array.from(this.spaceAssets.values()).filter(space =>
      space.floorId === floorId
    );
  }

  // Room methods (legacy compatibility)
  async getAllRooms(storeId?: number): Promise<Room[]> {
    const allRooms = Array.from(this.rooms.values());
    return storeId ? allRooms.filter(room => room.storeId === storeId) : allRooms;
  }

  async getRoom(id: string): Promise<Room | undefined> {
    return this.rooms.get(id);
  }

  async getRoomByNumber(roomNumber: string, storeId?: number): Promise<Room | undefined> {
    let rooms = Array.from(this.rooms.values());
    
    if (storeId) {
      rooms = rooms.filter(room => room.storeId === storeId);
    }
    
    return rooms.find((room) => room.roomNumber === roomNumber);
  }

  async createRoom(room: InsertRoom): Promise<Room> {
    const id = randomUUID();
    const newRoom: Room = {
      ...room,
      id,
      storeId: room.storeId ?? null,
      status: room.status || "vacant",
      tenant: room.tenant ?? null,
      monthlyRevenue: room.monthlyRevenue ?? null,
      revenuePerSqm: room.revenuePerSqm ?? null,
      leaseExpiry: room.leaseExpiry ?? null,
      contractType: room.contractType ?? null,
      createdAt: new Date(),
      updatedAt: new Date()
    };
    this.rooms.set(id, newRoom);
    return newRoom;
  }

  async updateRoom(id: string, roomUpdate: Partial<InsertRoom>): Promise<Room> {
    const existingRoom = this.rooms.get(id);
    if (!existingRoom) {
      throw new Error(`Room with id ${id} not found`);
    }
    
    const updatedRoom: Room = {
      ...existingRoom,
      ...roomUpdate,
      updatedAt: new Date()
    };
    this.rooms.set(id, updatedRoom);
    return updatedRoom;
  }

  async deleteRoom(id: string): Promise<boolean> {
    return this.rooms.delete(id);
  }

  async searchRooms(query: string, storeId?: number): Promise<Room[]> {
    const lowerQuery = query.toLowerCase();
    let rooms = Array.from(this.rooms.values());
    
    if (storeId) {
      rooms = rooms.filter(room => room.storeId === storeId);
    }
    
    return rooms.filter(room =>
      room.roomNumber.toLowerCase().includes(lowerQuery) ||
      room.name.toLowerCase().includes(lowerQuery) ||
      (room.tenant && room.tenant.toLowerCase().includes(lowerQuery))
    );
  }

  // Floor plan methods
  async getAllFloorPlans(storeId?: number): Promise<FloorPlan[]> {
    const allPlans = Array.from(this.floorPlans.values());
    return storeId ? allPlans.filter(plan => plan.storeId === storeId) : allPlans;
  }

  async getActiveFloorPlan(storeId?: number): Promise<FloorPlan | undefined> {
    let plans = Array.from(this.floorPlans.values());
    
    if (storeId) {
      plans = plans.filter(plan => plan.storeId === storeId);
    }
    
    return plans.find(plan => plan.isActive);
  }

  async getFloorPlan(id: string): Promise<FloorPlan | undefined> {
    return this.floorPlans.get(id);
  }

  async createFloorPlan(floorPlan: InsertFloorPlan): Promise<FloorPlan> {
    const id = randomUUID();
    const newFloorPlan: FloorPlan = {
      ...floorPlan,
      id,
      storeId: floorPlan.storeId ?? null,
      planVersion: floorPlan.planVersion ?? "1.0",
      floorNumber: floorPlan.floorNumber ?? 1,
      imageUrl: floorPlan.imageUrl ?? null,
      description: floorPlan.description ?? null,
      isActive: floorPlan.isActive ?? null,
      effectiveDate: floorPlan.effectiveDate ?? new Date(),
      expiryDate: floorPlan.expiryDate ?? null,
      createdBy: floorPlan.createdBy ?? null,
      approvedBy: floorPlan.approvedBy ?? null,
      approvedAt: floorPlan.approvedAt ?? null,
      createdAt: new Date(),
      updatedAt: new Date()
    };
    this.floorPlans.set(id, newFloorPlan);
    return newFloorPlan;
  }

  async updateFloorPlan(id: string, floorPlanUpdate: Partial<InsertFloorPlan>): Promise<FloorPlan> {
    const existingFloorPlan = this.floorPlans.get(id);
    if (!existingFloorPlan) {
      throw new Error(`Floor plan with id ${id} not found`);
    }
    
    const updatedFloorPlan: FloorPlan = {
      ...existingFloorPlan,
      ...floorPlanUpdate,
      imageUrl: floorPlanUpdate.imageUrl ?? existingFloorPlan.imageUrl,
      isActive: floorPlanUpdate.isActive ?? existingFloorPlan.isActive,
      updatedAt: new Date()
    };
    this.floorPlans.set(id, updatedFloorPlan);
    return updatedFloorPlan;
  }

  async activateFloorPlan(id: string): Promise<FloorPlan> {
    const plan = this.floorPlans.get(id);
    if (!plan) {
      throw new Error(`Floor plan with id ${id} not found`);
    }

    // Deactivate other plans for the same store
    if (plan.storeId) {
      Array.from(this.floorPlans.entries()).forEach(([existingId, existingPlan]) => {
        if (existingPlan.storeId === plan.storeId && existingId !== id && existingPlan.isActive) {
          existingPlan.isActive = false;
          existingPlan.updatedAt = new Date();
        }
      });
    }

    plan.isActive = true;
    plan.updatedAt = new Date();
    return plan;
  }

  async deactivateFloorPlan(id: string): Promise<FloorPlan> {
    const plan = this.floorPlans.get(id);
    if (!plan) {
      throw new Error(`Floor plan with id ${id} not found`);
    }

    plan.isActive = false;
    plan.updatedAt = new Date();
    return plan;
  }

  // Activity methods
  async getRecentActivities(limit: number = 10): Promise<Activity[]> {
    return Array.from(this.activities.values())
      .sort((a, b) => (b.createdAt?.getTime() ?? 0) - (a.createdAt?.getTime() ?? 0))
      .slice(0, limit);
  }

  async createActivity(activity: InsertActivity): Promise<Activity> {
    const id = randomUUID();
    const newActivity: Activity = {
      ...activity,
      id,
      roomId: activity.roomId ?? null,
      createdAt: new Date()
    };
    this.activities.set(id, newActivity);
    return newActivity;
  }

  // Analytics methods
  async getStats(storeId?: number): Promise<{
    totalRooms: number;
    occupied: number;
    vacant: number;
    avgRevenue: number;
  }> {
    let rooms = Array.from(this.rooms.values());
    
    if (storeId) {
      rooms = rooms.filter(room => room.storeId === storeId);
    }
    
    const totalRooms = rooms.length;
    const occupied = rooms.filter(room => room.status === 'occupied').length;
    const vacant = rooms.filter(room => room.status === 'vacant').length;
    
    const totalRevenue = rooms.reduce((sum, room) => sum + parseFloat(room.revenuePerSqm || '0'), 0);
    const avgRevenue = totalRooms > 0 ? totalRevenue / totalRooms : 0;

    return {
      totalRooms,
      occupied,
      vacant,
      avgRevenue: Math.round(avgRevenue)
    };
  }

  // User marked rooms methods implementation
  async getUserMarkedRooms(storeId?: number, floorPlanId?: string): Promise<UserMarkedRoom[]> {
    // Load from database if available and memory is empty
    if (this.db && this.userMarkedRooms.size === 0) {
      try {
        const dbRooms = await this.db.select().from(userMarkedRooms);
        dbRooms.forEach(room => {
          this.userMarkedRooms.set(room.id, room);
        });
      } catch (error) {
        console.error('Error loading from database:', error);
      }
    }
    
    let markedRooms = Array.from(this.userMarkedRooms.values());
    
    if (storeId) {
      markedRooms = markedRooms.filter(room => room.storeId === storeId);
    }
    
    if (floorPlanId) {
      markedRooms = markedRooms.filter(room => room.floorPlanId === floorPlanId);
    }
    
    return markedRooms;
  }

  async createUserMarkedRoom(markedRoom: NewUserMarkedRoom): Promise<UserMarkedRoom> {
    const id = randomUUID();
    const newMarkedRoom: UserMarkedRoom = {
      ...markedRoom,
      id,
      type: markedRoom.type || "rectangle",
      storeId: markedRoom.storeId ?? null,
      floorPlanId: markedRoom.floorPlanId ?? null,
      counterId: markedRoom.counterId ?? null,
      width: markedRoom.width ?? null,
      height: markedRoom.height ?? null,
      polygonPoints: markedRoom.polygonPoints ?? null,
      createdAt: new Date(),
      updatedAt: new Date()
    };
    
    // Save to database if available
    if (this.db) {
      try {
        await this.db.insert(userMarkedRooms).values(newMarkedRoom);
      } catch (error) {
        console.error('Error saving to database:', error);
      }
    }
    
    // Save to memory cache
    this.userMarkedRooms.set(id, newMarkedRoom);
    return newMarkedRoom;
  }

  async updateUserMarkedRoom(id: string, markedRoomUpdate: Partial<NewUserMarkedRoom>): Promise<UserMarkedRoom> {
    const existingRoom = this.userMarkedRooms.get(id);
    if (!existingRoom) {
      throw new Error(`Marked room with id ${id} not found`);
    }
    
    const updatedRoom: UserMarkedRoom = {
      ...existingRoom,
      ...markedRoomUpdate,
      updatedAt: new Date()
    };
    this.userMarkedRooms.set(id, updatedRoom);
    return updatedRoom;
  }

  // 根据柜位号关联标记房间
  async linkMarkedRoomToCounter(markedRoomId: string, counterNumber: string, storeId?: number): Promise<UserMarkedRoom | null> {
    const markedRoom = this.userMarkedRooms.get(markedRoomId);
    if (!markedRoom) {
      return null;
    }

    // 查找匹配的柜位
    const counters = Array.from(this.counters.values());
    const matchingCounter = counters.find(counter => 
      counter.counterNumber === counterNumber && 
      (!storeId || counter.storeId === storeId)
    );

    if (!matchingCounter) {
      return null;
    }

    // 更新标记房间，关联柜位
    const updatedRoom: UserMarkedRoom = {
      ...markedRoom,
      counterId: matchingCounter.counterId,
      updatedAt: new Date()
    };
    this.userMarkedRooms.set(markedRoomId, updatedRoom);
    return updatedRoom;
  }

  // 自动关联同名的柜位和标记房间
  async autoLinkCountersToMarkedRooms(storeId?: number): Promise<{ linked: number; total: number }> {
    let linkedCount = 0;
    const markedRooms = Array.from(this.userMarkedRooms.values());
    const counters = Array.from(this.counters.values());

    for (const markedRoom of markedRooms) {
      if (storeId && markedRoom.storeId !== storeId) continue;
      if (markedRoom.counterId) continue; // 已经关联

      const matchingCounter = counters.find(counter => 
        counter.counterNumber === markedRoom.name &&
        (!storeId || counter.storeId === storeId)
      );

      if (matchingCounter) {
        const updatedRoom: UserMarkedRoom = {
          ...markedRoom,
          counterId: matchingCounter.counterId,
          updatedAt: new Date()
        };
        
        // Update database if available
        if (this.db) {
          try {
            await this.db.update(userMarkedRooms)
              .set({ counterId: matchingCounter.counterId, updatedAt: new Date() })
              .where(eq(userMarkedRooms.id, markedRoom.id));
          } catch (error) {
            console.error('Error updating database:', error);
            continue; // Skip this room if database update fails
          }
        }
        
        // Update memory cache
        this.userMarkedRooms.set(markedRoom.id, updatedRoom);
        linkedCount++;
      }
    }

    return { linked: linkedCount, total: markedRooms.length };
  }

  async deleteUserMarkedRoom(id: string): Promise<void> {
    if (!this.userMarkedRooms.has(id)) {
      throw new Error(`Marked room with id ${id} not found`);
    }
    this.userMarkedRooms.delete(id);
  }
}

export const storage = new MemStorage();
