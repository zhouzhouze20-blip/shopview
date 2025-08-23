import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { 
  insertRoomSchema, insertFloorPlanSchema, insertActivitySchema,
  insertTenantSchema, insertBrandSchema, insertContractSchema,
  insertFloorSchema, insertSpaceAssetSchema, insertStoreSchema,
  insertCounterSchema, insertHallSchema
} from "@shared/schema";
import { z } from "zod";
import { ObjectStorageService } from "./objectStorage";

export async function registerRoutes(app: Express): Promise<Server> {
  // Health check endpoint for Docker
  app.get("/api/health", (req, res) => {
    res.status(200).json({ 
      status: "healthy", 
      timestamp: new Date().toISOString(),
      version: "1.0.0"
    });
  });

  // ==================== 门店管理 API ====================
  app.get("/api/stores", async (req, res) => {
    try {
      const stores = await storage.getAllStores();
      res.json(stores);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch stores" });
    }
  });

  app.get("/api/stores/:id", async (req, res) => {
    try {
      const storeId = parseInt(req.params.id);
      if (isNaN(storeId)) {
        return res.status(400).json({ message: "Invalid store ID" });
      }
      const store = await storage.getStore(storeId);
      if (!store) {
        return res.status(404).json({ message: "Store not found" });
      }
      res.json(store);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch store" });
    }
  });

  app.post("/api/stores", async (req, res) => {
    try {
      const storeData = insertStoreSchema.parse(req.body);
      const store = await storage.createStore(storeData);
      res.status(201).json(store);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid store data", errors: error.errors });
      }
      res.status(500).json({ message: "Failed to create store" });
    }
  });

  app.put("/api/stores/:id", async (req, res) => {
    try {
      const storeId = parseInt(req.params.id);
      if (isNaN(storeId)) {
        return res.status(400).json({ message: "Invalid store ID" });
      }
      const storeData = insertStoreSchema.partial().parse(req.body);
      const store = await storage.updateStore(storeId, storeData);
      res.json(store);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid store data", errors: error.errors });
      }
      res.status(500).json({ message: "Failed to update store" });
    }
  });

  // ==================== 柜位管理 API ====================
  app.get("/api/counters", async (req, res) => {
    try {
      const storeId = req.query.storeId ? parseInt(req.query.storeId as string) : undefined;
      const counters = await storage.getAllCounters(storeId);
      res.json(counters);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch counters" });
    }
  });

  app.get("/api/counters/search", async (req, res) => {
    try {
      const query = req.query.q as string;
      const storeId = req.query.storeId ? parseInt(req.query.storeId as string) : undefined;
      if (!query) {
        return res.status(400).json({ message: "Search query is required" });
      }
      const counters = await storage.searchCounters(query, storeId);
      res.json(counters);
    } catch (error) {
      res.status(500).json({ message: "Failed to search counters" });
    }
  });

  app.get("/api/counters/department/:department", async (req, res) => {
    try {
      const department = req.params.department;
      const storeId = req.query.storeId ? parseInt(req.query.storeId as string) : undefined;
      const counters = await storage.getCountersByDepartment(department, storeId);
      res.json(counters);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch counters by department" });
    }
  });

  app.get("/api/counters/:id", async (req, res) => {
    try {
      const counterId = parseInt(req.params.id);
      if (isNaN(counterId)) {
        return res.status(400).json({ message: "Invalid counter ID" });
      }
      const counter = await storage.getCounter(counterId);
      if (!counter) {
        return res.status(404).json({ message: "Counter not found" });
      }
      res.json(counter);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch counter" });
    }
  });

  app.post("/api/counters", async (req, res) => {
    try {
      const counterData = insertCounterSchema.parse(req.body);
      const counter = await storage.createCounter(counterData);
      res.status(201).json(counter);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid counter data", errors: error.errors });
      }
      res.status(500).json({ message: "Failed to create counter" });
    }
  });

  app.put("/api/counters/:id", async (req, res) => {
    try {
      const counterId = parseInt(req.params.id);
      if (isNaN(counterId)) {
        return res.status(400).json({ message: "Invalid counter ID" });
      }
      const counterData = insertCounterSchema.partial().parse(req.body);
      const counter = await storage.updateCounter(counterId, counterData);
      res.json(counter);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid counter data", errors: error.errors });
      }
      res.status(500).json({ message: "Failed to update counter" });
    }
  });

  app.delete("/api/counters/:id", async (req, res) => {
    try {
      const counterId = parseInt(req.params.id);
      if (isNaN(counterId)) {
        return res.status(400).json({ message: "Invalid counter ID" });
      }
      const success = await storage.deleteCounter(counterId);
      if (!success) {
        return res.status(404).json({ message: "Counter not found" });
      }
      res.json({ message: "Counter deleted successfully" });
    } catch (error) {
      res.status(500).json({ message: "Failed to delete counter" });
    }
  });

  // ==================== 厅房管理 API ====================
  app.get("/api/halls", async (req, res) => {
    try {
      const storeId = req.query.storeId ? parseInt(req.query.storeId as string) : undefined;
      const halls = await storage.getAllHalls(storeId);
      res.json(halls);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch halls" });
    }
  });

  app.get("/api/halls/search", async (req, res) => {
    try {
      const query = req.query.q as string;
      const storeId = req.query.storeId ? parseInt(req.query.storeId as string) : undefined;
      if (!query) {
        return res.status(400).json({ message: "Search query is required" });
      }
      const halls = await storage.searchHalls(query, storeId);
      res.json(halls);
    } catch (error) {
      res.status(500).json({ message: "Failed to search halls" });
    }
  });

  app.get("/api/halls/:id", async (req, res) => {
    try {
      const hallId = parseInt(req.params.id);
      if (isNaN(hallId)) {
        return res.status(400).json({ message: "Invalid hall ID" });
      }
      const hall = await storage.getHall(hallId);
      if (!hall) {
        return res.status(404).json({ message: "Hall not found" });
      }
      res.json(hall);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch hall" });
    }
  });

  app.post("/api/halls", async (req, res) => {
    try {
      const hallData = insertHallSchema.parse(req.body);
      const hall = await storage.createHall(hallData);
      res.status(201).json(hall);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid hall data", errors: error.errors });
      }
      res.status(500).json({ message: "Failed to create hall" });
    }
  });

  app.put("/api/halls/:id", async (req, res) => {
    try {
      const hallId = parseInt(req.params.id);
      if (isNaN(hallId)) {
        return res.status(400).json({ message: "Invalid hall ID" });
      }
      const hallData = insertHallSchema.partial().parse(req.body);
      const hall = await storage.updateHall(hallId, hallData);
      res.json(hall);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid hall data", errors: error.errors });
      }
      res.status(500).json({ message: "Failed to update hall" });
    }
  });

  // Room routes (厅房遗留兼容性)
  app.get("/api/rooms", async (req, res) => {
    try {
      const storeId = req.query.storeId ? parseInt(req.query.storeId as string) : undefined;
      const rooms = await storage.getAllRooms(storeId);
      res.json(rooms);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch rooms" });
    }
  });

  app.get("/api/rooms/search", async (req, res) => {
    try {
      const query = req.query.q as string;
      const storeId = req.query.storeId ? parseInt(req.query.storeId as string) : undefined;
      if (!query) {
        return res.status(400).json({ message: "Search query is required" });
      }
      const rooms = await storage.searchRooms(query, storeId);
      res.json(rooms);
    } catch (error) {
      res.status(500).json({ message: "Failed to search rooms" });
    }
  });

  app.get("/api/rooms/:id", async (req, res) => {
    try {
      const room = await storage.getRoom(req.params.id);
      if (!room) {
        return res.status(404).json({ message: "Room not found" });
      }
      res.json(room);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch room" });
    }
  });

  app.post("/api/rooms", async (req, res) => {
    try {
      const roomData = insertRoomSchema.parse(req.body);
      const room = await storage.createRoom(roomData);
      res.status(201).json(room);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid room data", errors: error.errors });
      }
      res.status(500).json({ message: "Failed to create room" });
    }
  });

  app.put("/api/rooms/:id", async (req, res) => {
    try {
      const roomData = insertRoomSchema.partial().parse(req.body);
      const room = await storage.updateRoom(req.params.id, roomData);
      res.json(room);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid room data", errors: error.errors });
      }
      if (error instanceof Error && error.message.includes("not found")) {
        return res.status(404).json({ message: "Room not found" });
      }
      res.status(500).json({ message: "Failed to update room" });
    }
  });

  app.delete("/api/rooms/:id", async (req, res) => {
    try {
      const deleted = await storage.deleteRoom(req.params.id);
      if (!deleted) {
        return res.status(404).json({ message: "Room not found" });
      }
      res.status(204).send();
    } catch (error) {
      res.status(500).json({ message: "Failed to delete room" });
    }
  });

  // Floor plan routes
  app.get("/api/floor-plans", async (req, res) => {
    try {
      const floorPlans = await storage.getAllFloorPlans();
      res.json(floorPlans);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch floor plans" });
    }
  });

  app.get("/api/floor-plans/active", async (req, res) => {
    try {
      const floorPlan = await storage.getActiveFloorPlan();
      if (!floorPlan) {
        return res.status(404).json({ message: "No active floor plan found" });
      }
      res.json(floorPlan);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch active floor plan" });
    }
  });

  app.post("/api/floor-plans", async (req, res) => {
    try {
      const floorPlanData = insertFloorPlanSchema.parse(req.body);
      const floorPlan = await storage.createFloorPlan(floorPlanData);
      res.status(201).json(floorPlan);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid floor plan data", errors: error.errors });
      }
      res.status(500).json({ message: "Failed to create floor plan" });
    }
  });

  app.put("/api/floor-plans/:id", async (req, res) => {
    try {
      const floorPlanData = insertFloorPlanSchema.partial().parse(req.body);
      const floorPlan = await storage.updateFloorPlan(req.params.id, floorPlanData);
      res.json(floorPlan);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid floor plan data", errors: error.errors });
      }
      if (error instanceof Error && error.message.includes("not found")) {
        return res.status(404).json({ message: "Floor plan not found" });
      }
      res.status(500).json({ message: "Failed to update floor plan" });
    }
  });

  app.put("/api/floor-plans/upload", async (req, res) => {
    try {
      const { imageUrl } = req.body;
      if (!imageUrl) {
        return res.status(400).json({ message: "imageUrl is required" });
      }

      // Get the active floor plan and update its image URL
      const activeFloorPlan = await storage.getActiveFloorPlan();
      if (!activeFloorPlan) {
        return res.status(404).json({ message: "No active floor plan found" });
      }

      const updatedFloorPlan = await storage.updateFloorPlan(activeFloorPlan.id, { imageUrl });
      res.json(updatedFloorPlan);
    } catch (error) {
      res.status(500).json({ message: "Failed to update floor plan image" });
    }
  });

  // Activity routes
  app.get("/api/activities", async (req, res) => {
    try {
      const limit = req.query.limit ? parseInt(req.query.limit as string) : 10;
      const activities = await storage.getRecentActivities(limit);
      res.json(activities);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch activities" });
    }
  });

  app.post("/api/activities", async (req, res) => {
    try {
      const activityData = insertActivitySchema.parse(req.body);
      const activity = await storage.createActivity(activityData);
      res.status(201).json(activity);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid activity data", errors: error.errors });
      }
      res.status(500).json({ message: "Failed to create activity" });
    }
  });

  // Analytics routes (支持门店过滤)
  app.get("/api/stats", async (req, res) => {
    try {
      const storeId = req.query.storeId ? parseInt(req.query.storeId as string) : undefined;
      const stats = await storage.getStats(storeId);
      res.json(stats);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch stats" });
    }
  });

  // 获取所有门店的统计信息
  app.get("/api/stores/stats", async (req, res) => {
    try {
      const stores = await storage.getAllStores();
      const stats: {[key: number]: any} = {};
      
      await Promise.all(
        stores.map(async (store: any) => {
          try {
            stats[store.storeId] = await storage.getStats(store.storeId);
          } catch (error) {
            console.error(`Failed to get stats for store ${store.storeId}:`, error);
            stats[store.storeId] = {
              totalRooms: 0,
              occupied: 0,
              vacant: 0,
              avgRevenue: 0
            };
          }
        })
      );
      
      res.json(stats);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch stores stats" });
    }
  });

  // 用户标记厅房相关路由
  app.get("/api/marked-rooms", async (req, res) => {
    try {
      const storeId = req.query.storeId ? parseInt(req.query.storeId as string) : undefined;
      const floorPlanId = req.query.floorPlanId as string | undefined;
      
      const markedRooms = await storage.getUserMarkedRooms(storeId, floorPlanId);
      res.json(markedRooms);
    } catch (error) {
      console.error("Failed to fetch marked rooms:", error);
      res.status(500).json({ message: "Failed to fetch marked rooms" });
    }
  });

  app.post("/api/marked-rooms", async (req, res) => {
    try {
      const markedRoomData = req.body;
      const savedRoom = await storage.createUserMarkedRoom(markedRoomData);
      res.status(201).json(savedRoom);
    } catch (error) {
      console.error("Failed to create marked room:", error);
      res.status(500).json({ message: "Failed to create marked room" });
    }
  });

  app.delete("/api/marked-rooms/:id", async (req, res) => {
    try {
      const { id } = req.params;
      await storage.deleteUserMarkedRoom(id);
      res.status(204).send();
    } catch (error) {
      console.error("Failed to delete marked room:", error);
      res.status(500).json({ message: "Failed to delete marked room" });
    }
  });

  // 关联柜位和标记房间
  app.post("/api/marked-rooms/:id/link-counter", async (req, res) => {
    try {
      const { id } = req.params;
      const { counterNumber, storeId } = req.body;
      
      const updatedRoom = await storage.linkMarkedRoomToCounter(
        id, 
        counterNumber, 
        storeId ? parseInt(storeId) : undefined
      );
      
      if (!updatedRoom) {
        return res.status(404).json({ error: "房间或柜位未找到" });
      }
      
      res.json(updatedRoom);
    } catch (error) {
      console.error("Error linking counter to marked room:", error);
      res.status(500).json({ error: "关联失败" });
    }
  });

  // 自动关联同名的柜位和标记房间
  app.post("/api/marked-rooms/auto-link", async (req, res) => {
    try {
      const { storeId } = req.body;
      const result = await storage.autoLinkCountersToMarkedRooms(
        storeId ? parseInt(storeId) : undefined
      );
      res.json(result);
    } catch (error) {
      console.error("Error auto-linking counters:", error);
      res.status(500).json({ error: "自动关联失败" });
    }
  });

  // ==================== 楼层平面图管理 API ====================
  app.get("/api/floor-plans", async (req, res) => {
    try {
      const storeId = req.query.storeId ? parseInt(req.query.storeId as string) : undefined;
      const floorPlans = await storage.getAllFloorPlans(storeId);
      res.json(floorPlans);
    } catch (error) {
      console.error("Failed to fetch floor plans:", error);
      res.status(500).json({ message: "Failed to fetch floor plans" });
    }
  });

  app.get("/api/floor-plans/:id", async (req, res) => {
    try {
      const { id } = req.params;
      const floorPlan = await storage.getFloorPlan(id);
      if (!floorPlan) {
        return res.status(404).json({ message: "Floor plan not found" });
      }
      res.json(floorPlan);
    } catch (error) {
      console.error("Failed to fetch floor plan:", error);
      res.status(500).json({ message: "Failed to fetch floor plan" });
    }
  });

  app.post("/api/floor-plans", async (req, res) => {
    try {
      const floorPlanData = req.body;
      const floorPlan = await storage.createFloorPlan(floorPlanData);
      res.status(201).json(floorPlan);
    } catch (error) {
      console.error("Failed to create floor plan:", error);
      res.status(500).json({ message: "Failed to create floor plan" });
    }
  });

  app.put("/api/floor-plans/:id", async (req, res) => {
    try {
      const { id } = req.params;
      const floorPlanData = req.body;
      const floorPlan = await storage.updateFloorPlan(id, floorPlanData);
      res.json(floorPlan);
    } catch (error) {
      console.error("Failed to update floor plan:", error);
      res.status(500).json({ message: "Failed to update floor plan" });
    }
  });

  app.post("/api/floor-plans/:id/activate", async (req, res) => {
    try {
      const { id } = req.params;
      const floorPlan = await storage.activateFloorPlan(id);
      res.json(floorPlan);
    } catch (error) {
      console.error("Failed to activate floor plan:", error);
      res.status(500).json({ message: "Failed to activate floor plan" });
    }
  });

  app.post("/api/floor-plans/:id/deactivate", async (req, res) => {
    try {
      const { id } = req.params;
      const floorPlan = await storage.deactivateFloorPlan(id);
      res.json(floorPlan);
    } catch (error) {
      console.error("Failed to deactivate floor plan:", error);
      res.status(500).json({ message: "Failed to deactivate floor plan" });
    }
  });

  // ==================== 商户管理 API ====================
  app.get("/api/tenants", async (req, res) => {
    try {
      const tenants = await storage.getAllTenants();
      res.json(tenants);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch tenants" });
    }
  });

  app.get("/api/tenants/search", async (req, res) => {
    try {
      const query = req.query.q as string;
      if (!query) {
        return res.status(400).json({ message: "Search query is required" });
      }
      const tenants = await storage.searchTenants(query);
      res.json(tenants);
    } catch (error) {
      res.status(500).json({ message: "Failed to search tenants" });
    }
  });

  app.get("/api/tenants/:id", async (req, res) => {
    try {
      const tenantId = parseInt(req.params.id);
      const tenant = await storage.getTenant(tenantId);
      if (!tenant) {
        return res.status(404).json({ message: "Tenant not found" });
      }
      res.json(tenant);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch tenant" });
    }
  });

  app.post("/api/tenants", async (req, res) => {
    try {
      const tenantData = insertTenantSchema.parse(req.body);
      const tenant = await storage.createTenant(tenantData);
      res.status(201).json(tenant);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid tenant data", errors: error.errors });
      }
      res.status(500).json({ message: "Failed to create tenant" });
    }
  });

  app.put("/api/tenants/:id", async (req, res) => {
    try {
      const tenantId = parseInt(req.params.id);
      const tenantData = insertTenantSchema.partial().parse(req.body);
      const tenant = await storage.updateTenant(tenantId, tenantData);
      res.json(tenant);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid tenant data", errors: error.errors });
      }
      if (error instanceof Error && error.message.includes("not found")) {
        return res.status(404).json({ message: "Tenant not found" });
      }
      res.status(500).json({ message: "Failed to update tenant" });
    }
  });

  // ==================== 品牌管理 API ====================
  app.get("/api/brands", async (req, res) => {
    try {
      const brands = await storage.getAllBrands();
      res.json(brands);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch brands" });
    }
  });

  app.get("/api/brands/:id", async (req, res) => {
    try {
      const brandId = parseInt(req.params.id);
      const brand = await storage.getBrand(brandId);
      if (!brand) {
        return res.status(404).json({ message: "Brand not found" });
      }
      res.json(brand);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch brand" });
    }
  });

  app.post("/api/brands", async (req, res) => {
    try {
      const brandData = insertBrandSchema.parse(req.body);
      const brand = await storage.createBrand(brandData);
      res.status(201).json(brand);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid brand data", errors: error.errors });
      }
      res.status(500).json({ message: "Failed to create brand" });
    }
  });

  app.put("/api/brands/:id", async (req, res) => {
    try {
      const brandId = parseInt(req.params.id);
      const brandData = insertBrandSchema.partial().parse(req.body);
      const brand = await storage.updateBrand(brandId, brandData);
      res.json(brand);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid brand data", errors: error.errors });
      }
      if (error instanceof Error && error.message.includes("not found")) {
        return res.status(404).json({ message: "Brand not found" });
      }
      res.status(500).json({ message: "Failed to update brand" });
    }
  });

  // ==================== 合同管理 API ====================
  app.get("/api/contracts", async (req, res) => {
    try {
      const contracts = await storage.getAllContracts();
      res.json(contracts);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch contracts" });
    }
  });

  app.get("/api/contracts/tenant/:tenantId", async (req, res) => {
    try {
      const tenantId = parseInt(req.params.tenantId);
      const contracts = await storage.getContractsByTenant(tenantId);
      res.json(contracts);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch contracts for tenant" });
    }
  });

  app.get("/api/contracts/:id", async (req, res) => {
    try {
      const contractId = parseInt(req.params.id);
      const contract = await storage.getContract(contractId);
      if (!contract) {
        return res.status(404).json({ message: "Contract not found" });
      }
      res.json(contract);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch contract" });
    }
  });

  app.post("/api/contracts", async (req, res) => {
    try {
      const contractData = insertContractSchema.parse(req.body);
      const contract = await storage.createContract(contractData);
      res.status(201).json(contract);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid contract data", errors: error.errors });
      }
      res.status(500).json({ message: "Failed to create contract" });
    }
  });

  app.put("/api/contracts/:id", async (req, res) => {
    try {
      const contractId = parseInt(req.params.id);
      const contractData = insertContractSchema.partial().parse(req.body);
      const contract = await storage.updateContract(contractId, contractData);
      res.json(contract);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid contract data", errors: error.errors });
      }
      if (error instanceof Error && error.message.includes("not found")) {
        return res.status(404).json({ message: "Contract not found" });
      }
      res.status(500).json({ message: "Failed to update contract" });
    }
  });

  // ==================== 楼层管理 API (新架构) ====================
  app.get("/api/floors", async (req, res) => {
    try {
      const floors = await storage.getAllFloors();
      res.json(floors);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch floors" });
    }
  });

  app.get("/api/floors/:id", async (req, res) => {
    try {
      const floorId = parseInt(req.params.id);
      const floor = await storage.getFloor(floorId);
      if (!floor) {
        return res.status(404).json({ message: "Floor not found" });
      }
      res.json(floor);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch floor" });
    }
  });

  app.post("/api/floors", async (req, res) => {
    try {
      const floorData = insertFloorSchema.parse(req.body);
      const floor = await storage.createFloor(floorData);
      res.status(201).json(floor);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid floor data", errors: error.errors });
      }
      res.status(500).json({ message: "Failed to create floor" });
    }
  });

  // ==================== 空间资产管理 API (新架构) ====================
  app.get("/api/space-assets", async (req, res) => {
    try {
      const spaceAssets = await storage.getAllSpaceAssets();
      res.json(spaceAssets);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch space assets" });
    }
  });

  app.get("/api/space-assets/floor/:floorId", async (req, res) => {
    try {
      const floorId = parseInt(req.params.floorId);
      const spaceAssets = await storage.getSpaceAssetsByFloor(floorId);
      res.json(spaceAssets);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch space assets for floor" });
    }
  });

  app.get("/api/space-assets/:id", async (req, res) => {
    try {
      const spaceId = parseInt(req.params.id);
      const spaceAsset = await storage.getSpaceAsset(spaceId);
      if (!spaceAsset) {
        return res.status(404).json({ message: "Space asset not found" });
      }
      res.json(spaceAsset);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch space asset" });
    }
  });

  app.post("/api/space-assets", async (req, res) => {
    try {
      const spaceAssetData = insertSpaceAssetSchema.parse(req.body);
      const spaceAsset = await storage.createSpaceAsset(spaceAssetData);
      res.status(201).json(spaceAsset);
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: "Invalid space asset data", errors: error.errors });
      }
      res.status(500).json({ message: "Failed to create space asset" });
    }
  });

  // Object storage routes for CAD uploads
  app.post("/api/objects/upload", async (req, res) => {
    try {
      const objectStorageService = new ObjectStorageService();
      const uploadURL = await objectStorageService.getObjectEntityUploadURL();
      res.json({ uploadURL });
    } catch (error) {
      console.error("Error getting upload URL:", error);
      res.status(500).json({ message: "Failed to get upload URL" });
    }
  });

  app.put("/api/floor-plans/active/image", async (req, res) => {
    try {
      if (!req.body.imageURL) {
        return res.status(400).json({ message: "imageURL is required" });
      }

      const objectStorageService = new ObjectStorageService();
      const objectPath = objectStorageService.normalizeObjectEntityPath(
        req.body.imageURL
      );

      // Update floor plan with new image URL
      const floorPlan = await storage.getActiveFloorPlan();
      if (floorPlan) {
        await storage.updateFloorPlan(floorPlan.id, { imageUrl: objectPath });
      }

      res.status(200).json({
        objectPath: objectPath,
      });
    } catch (error) {
      console.error("Error updating floor plan image:", error);
      res.status(500).json({ message: "Failed to update floor plan image" });
    }
  });

  app.get("/objects/:objectPath(*)", async (req, res) => {
    try {
      const objectStorageService = new ObjectStorageService();
      const objectFile = await objectStorageService.getObjectEntityFile(
        req.path
      );
      objectStorageService.downloadObject(objectFile, res);
    } catch (error) {
      console.error("Error serving object:", error);
      res.status(404).json({ message: "Object not found" });
    }
  });

  const httpServer = createServer(app);
  return httpServer;
}
