import { sql } from "drizzle-orm";
import { pgTable, text, varchar, integer, decimal, timestamp, boolean, date, json } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

// ==================== 模块一：系统管理与权限 ====================
export const users = pgTable("users", {
  userId: integer("user_id").primaryKey().generatedByDefaultAsIdentity(),
  username: varchar("username", { length: 50 }).notNull().unique(),
  passwordHash: varchar("password_hash", { length: 255 }).notNull(),
  fullName: varchar("full_name", { length: 100 }).notNull(),
  email: varchar("email", { length: 100 }).notNull().unique(),
  roleId: integer("role_id").references(() => roles.roleId),
  isActive: boolean("is_active").default(true),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow()
});

export const roles = pgTable("roles", {
  roleId: integer("role_id").primaryKey().generatedByDefaultAsIdentity(),
  roleName: varchar("role_name", { length: 50 }).notNull().unique(),
  description: text("description"),
  createdAt: timestamp("created_at").defaultNow()
});

export const rolePermissions = pgTable("role_permissions", {
  id: integer("id").primaryKey().generatedByDefaultAsIdentity(),
  roleId: integer("role_id").references(() => roles.roleId).notNull(),
  permissionCode: varchar("permission_code", { length: 50 }).notNull()
});

// ==================== 模块二：门店管理 ====================
export const stores = pgTable("stores", {
  storeId: integer("store_id").primaryKey().generatedByDefaultAsIdentity(),
  storeName: varchar("store_name", { length: 100 }).notNull(),
  storeCode: varchar("store_code", { length: 20 }).notNull().unique(),
  address: text("address"),
  managerName: varchar("manager_name", { length: 50 }),
  contactPhone: varchar("contact_phone", { length: 20 }),
  contactEmail: varchar("contact_email", { length: 100 }),
  isActive: boolean("is_active").default(true),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow()
});

// ==================== 模块三：空间资产核心 ====================
export const floors = pgTable("floors", {
  floorId: integer("floor_id").primaryKey().generatedByDefaultAsIdentity(),
  storeId: integer("store_id").references(() => stores.storeId).notNull(),
  floorName: varchar("floor_name", { length: 50 }).notNull(),
  displayOrder: integer("display_order").default(0),
  description: text("description"),
  createdAt: timestamp("created_at").defaultNow()
});

export const layouts = pgTable("layouts", {
  layoutId: integer("layout_id").primaryKey().generatedByDefaultAsIdentity(),
  floorId: integer("floor_id").references(() => floors.floorId).notNull(),
  backgroundImageUrl: varchar("background_image_url", { length: 255 }),
  effectiveStartDate: date("effective_start_date").notNull(),
  effectiveEndDate: date("effective_end_date"),
  isActive: boolean("is_active").default(true),
  createdAt: timestamp("created_at").defaultNow()
});

// 柜位管理 (按用户要求的业务流程)
export const counters = pgTable("counters", {
  counterId: integer("counter_id").primaryKey().generatedByDefaultAsIdentity(),
  storeId: integer("store_id").references(() => stores.storeId).notNull(),
  counterNumber: varchar("counter_number", { length: 50 }).notNull(), // 柜位号
  department: varchar("department", { length: 100 }).notNull(), // 部门
  building: varchar("building", { length: 50 }).notNull(), // 楼栋
  floor: varchar("floor", { length: 20 }).notNull(), // 楼层
  area: decimal("area", { precision: 10, scale: 2 }).notNull(), // 面积
  status: varchar("status", { length: 20 }).notNull().default("vacant"), // 状态: vacant, occupied, maintenance
  monthlyRent: decimal("monthly_rent", { precision: 12, scale: 2 }),
  tenantId: integer("tenant_id").references(() => tenants.tenantId),
  description: text("description"),
  isActive: boolean("is_active").default(true),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow()
});

// 厅房管理 (原rooms表的现代化版本)
export const halls = pgTable("halls", {
  hallId: integer("hall_id").primaryKey().generatedByDefaultAsIdentity(),
  storeId: integer("store_id").references(() => stores.storeId).notNull(),
  hallCode: varchar("hall_code", { length: 50 }).notNull(),
  hallName: varchar("hall_name", { length: 100 }).notNull(),
  floorId: integer("floor_id").references(() => floors.floorId),
  area: decimal("area", { precision: 10, scale: 2 }).notNull(),
  status: varchar("status", { length: 20 }).notNull().default("vacant"), // vacant, occupied, maintenance
  monthlyRent: decimal("monthly_rent", { precision: 12, scale: 2 }),
  isActive: boolean("is_active").default(true),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow()
});

export const spaceAssets = pgTable("space_assets", {
  spaceId: integer("space_id").primaryKey().generatedByDefaultAsIdentity(),
  spaceCode: varchar("space_code", { length: 50 }).notNull().unique(),
  floorId: integer("floor_id").references(() => floors.floorId).notNull(),
  area: decimal("area", { precision: 10, scale: 2 }).notNull(),
  spaceType: varchar("space_type", { length: 20 }).notNull().default("Leasable"), // Leasable, Public
  status: varchar("status", { length: 20 }).notNull().default("Active"), // Active, Archived
  effectiveStartDate: date("effective_start_date").notNull(),
  effectiveEndDate: date("effective_end_date"),
  createdAt: timestamp("created_at").defaultNow()
});

export const spaceLineage = pgTable("space_lineage", {
  lineageId: integer("lineage_id").primaryKey().generatedByDefaultAsIdentity(),
  operationType: varchar("operation_type", { length: 20 }).notNull(), // Merge, Split, Reconfigure
  previousSpaceId: integer("previous_space_id").references(() => spaceAssets.spaceId),
  nextSpaceId: integer("next_space_id").references(() => spaceAssets.spaceId),
  areaContributed: decimal("area_contributed", { precision: 10, scale: 2 }),
  effectiveDate: date("effective_date").notNull(),
  createdAt: timestamp("created_at").defaultNow()
});

export const hotspots = pgTable("hotspots", {
  hotspotId: integer("hotspot_id").primaryKey().generatedByDefaultAsIdentity(),
  layoutId: integer("layout_id").references(() => layouts.layoutId).notNull(),
  spaceId: integer("space_id").references(() => spaceAssets.spaceId).notNull(),
  shapeType: varchar("shape_type", { length: 20 }).notNull().default("rect"), // rect, polygon
  coordinatesData: json("coordinates_data").notNull(), // JSON格式的坐标数据
  createdAt: timestamp("created_at").defaultNow()
});

// ==================== 模块四：商户与品牌 ====================
export const tenants = pgTable("tenants", {
  tenantId: integer("tenant_id").primaryKey().generatedByDefaultAsIdentity(),
  companyName: varchar("company_name", { length: 255 }).notNull(),
  tenantCode: varchar("tenant_code", { length: 50 }).notNull().unique(),
  legalRepresentative: varchar("legal_representative", { length: 100 }),
  businessLicense: varchar("business_license", { length: 100 }),
  contactPerson: varchar("contact_person", { length: 100 }),
  contactPhone: varchar("contact_phone", { length: 20 }),
  contactEmail: varchar("contact_email", { length: 100 }),
  address: text("address"),
  isActive: boolean("is_active").default(true),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow()
});

export const brands = pgTable("brands", {
  brandId: integer("brand_id").primaryKey().generatedByDefaultAsIdentity(),
  brandName: varchar("brand_name", { length: 100 }).notNull(),
  brandNameEn: varchar("brand_name_en", { length: 100 }),
  category: varchar("category", { length: 50 }), // 餐饮、零售、配套等
  logoUrl: varchar("logo_url", { length: 255 }),
  description: text("description"),
  isActive: boolean("is_active").default(true),
  createdAt: timestamp("created_at").defaultNow()
});

// ==================== 模块五：合同与财务 ====================
export const contracts = pgTable("contracts", {
  contractId: integer("contract_id").primaryKey().generatedByDefaultAsIdentity(),
  contractCode: varchar("contract_code", { length: 100 }).notNull().unique(),
  tenantId: integer("tenant_id").references(() => tenants.tenantId).notNull(),
  brandId: integer("brand_id").references(() => brands.brandId),
  startDate: date("start_date").notNull(),
  endDate: date("end_date").notNull(),
  status: varchar("status", { length: 20 }).notNull().default("Draft"), // Draft, Approving, Active, Expired, Terminated
  freeRentDays: integer("free_rent_days").default(0),
  securityDeposit: decimal("security_deposit", { precision: 12, scale: 2 }),
  notes: text("notes"),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow()
});

export const contractSpaces = pgTable("contract_spaces", {
  id: integer("id").primaryKey().generatedByDefaultAsIdentity(),
  contractId: integer("contract_id").references(() => contracts.contractId).notNull(),
  spaceId: integer("space_id").references(() => spaceAssets.spaceId).notNull(),
  createdAt: timestamp("created_at").defaultNow()
});

export const rentTerms = pgTable("rent_terms", {
  termId: integer("term_id").primaryKey().generatedByDefaultAsIdentity(),
  contractId: integer("contract_id").references(() => contracts.contractId).notNull(),
  termStartDate: date("term_start_date").notNull(),
  termEndDate: date("term_end_date").notNull(),
  rentType: varchar("rent_type", { length: 20 }).notNull(), // Fixed, Percentage, Hybrid
  fixedAmount: decimal("fixed_amount", { precision: 12, scale: 2 }),
  percentageRate: decimal("percentage_rate", { precision: 5, scale: 2 }),
  createdAt: timestamp("created_at").defaultNow()
});

export const bills = pgTable("bills", {
  billId: integer("bill_id").primaryKey().generatedByDefaultAsIdentity(),
  contractId: integer("contract_id").references(() => contracts.contractId).notNull(),
  billPeriodStart: date("bill_period_start").notNull(),
  billPeriodEnd: date("bill_period_end").notNull(),
  totalAmount: decimal("total_amount", { precision: 12, scale: 2 }).notNull(),
  status: varchar("status", { length: 20 }).notNull().default("Unpaid"), // Unpaid, Paid, Overdue
  dueDate: date("due_date"),
  paidDate: date("paid_date"),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow()
});

// ==================== 模块六：兼容性保持（原有表结构，用于向后兼容） ====================
export const rooms = pgTable("rooms", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  storeId: integer("store_id").references(() => stores.storeId), // 添加门店关联
  roomNumber: text("room_number").notNull(),
  name: text("name").notNull(),
  area: decimal("area", { precision: 10, scale: 2 }).notNull(),
  tenant: text("tenant"),
  status: text("status").notNull().default("vacant"), // occupied, vacant, maintenance
  monthlyRevenue: decimal("monthly_revenue", { precision: 12, scale: 2 }).default("0"),
  revenuePerSqm: decimal("revenue_per_sqm", { precision: 10, scale: 2 }).default("0"),
  leaseExpiry: text("lease_expiry"),
  contractType: text("contract_type"), // fixed, percentage, hybrid
  x: decimal("x", { precision: 8, scale: 4 }).notNull(), // position percentage
  y: decimal("y", { precision: 8, scale: 4 }).notNull(), // position percentage
  width: decimal("width", { precision: 8, scale: 4 }).notNull(), // size percentage
  height: decimal("height", { precision: 8, scale: 4 }).notNull(), // size percentage
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow()
});

export const floorPlans = pgTable("floor_plans", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  storeId: integer("store_id").references(() => stores.storeId), // 添加门店关联
  name: text("name").notNull(),
  planVersion: varchar("plan_version", { length: 50 }).notNull().default("1.0"),
  level: text("level").notNull(),
  floorNumber: integer("floor_number").notNull().default(1),
  imageUrl: text("image_url"),
  description: text("description"),
  isActive: boolean("is_active").default(true),
  effectiveDate: timestamp("effective_date").defaultNow().notNull(),
  expiryDate: timestamp("expiry_date"),
  createdBy: text("created_by"),
  approvedBy: text("approved_by"),
  approvedAt: timestamp("approved_at"),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow()
});

export const activities = pgTable("activities", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  roomId: varchar("room_id").references(() => rooms.id),
  type: text("type").notNull(), // lease_renewal, payment_received, maintenance_request, etc.
  description: text("description").notNull(),
  createdAt: timestamp("created_at").defaultNow()
});

// 用户在楼层平面图上标记的厅房
export const userMarkedRooms = pgTable("user_marked_rooms", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  storeId: integer("store_id").references(() => stores.storeId),
  floorPlanId: varchar("floor_plan_id").references(() => floorPlans.id),
  counterId: integer("counter_id").references(() => counters.counterId), // 关联柜位
  name: text("name").notNull(),
  type: text("type").notNull().default("rectangle"), // rectangle, polygon
  x: decimal("x", { precision: 10, scale: 2 }).notNull(),
  y: decimal("y", { precision: 10, scale: 2 }).notNull(),
  width: decimal("width", { precision: 10, scale: 2 }),
  height: decimal("height", { precision: 10, scale: 2 }),
  polygonPoints: json("polygon_points"), // Array<{x: number, y: number}>
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow()
});

// ==================== TypeScript 类型定义 ====================
export type User = typeof users.$inferSelect;
export type NewUser = typeof users.$inferInsert;
export type Role = typeof roles.$inferSelect;
export type NewRole = typeof roles.$inferInsert;
export type Store = typeof stores.$inferSelect;
export type NewStore = typeof stores.$inferInsert;
export type Floor = typeof floors.$inferSelect;
export type NewFloor = typeof floors.$inferInsert;
export type Layout = typeof layouts.$inferSelect;
export type NewLayout = typeof layouts.$inferInsert;
export type Counter = typeof counters.$inferSelect;
export type NewCounter = typeof counters.$inferInsert;
export type Hall = typeof halls.$inferSelect;
export type NewHall = typeof halls.$inferInsert;
export type SpaceAsset = typeof spaceAssets.$inferSelect;
export type NewSpaceAsset = typeof spaceAssets.$inferInsert;
export type Hotspot = typeof hotspots.$inferSelect;
export type NewHotspot = typeof hotspots.$inferInsert;
export type Tenant = typeof tenants.$inferSelect;
export type NewTenant = typeof tenants.$inferInsert;
export type Brand = typeof brands.$inferSelect;
export type NewBrand = typeof brands.$inferInsert;
export type Contract = typeof contracts.$inferSelect;
export type NewContract = typeof contracts.$inferInsert;
export type RentTerm = typeof rentTerms.$inferSelect;
export type NewRentTerm = typeof rentTerms.$inferInsert;
export type Bill = typeof bills.$inferSelect;
export type NewBill = typeof bills.$inferInsert;

// 向后兼容的类型
export type Room = typeof rooms.$inferSelect;
export type NewRoom = typeof rooms.$inferInsert;
export type FloorPlan = typeof floorPlans.$inferSelect;
export type NewFloorPlan = typeof floorPlans.$inferInsert;
export type Activity = typeof activities.$inferSelect;
export type NewActivity = typeof activities.$inferInsert;
export type UserMarkedRoom = typeof userMarkedRooms.$inferSelect;
export type NewUserMarkedRoom = typeof userMarkedRooms.$inferInsert;

// ==================== Zod 插入模式 ====================
// 系统管理
export const insertUserSchema = createInsertSchema(users).omit({
  userId: true,
  createdAt: true,
  updatedAt: true
});

export const insertRoleSchema = createInsertSchema(roles).omit({
  roleId: true,
  createdAt: true
});

// 门店管理
export const insertStoreSchema = createInsertSchema(stores).omit({
  storeId: true,
  createdAt: true,
  updatedAt: true
});

// 空间资产
export const insertFloorSchema = createInsertSchema(floors).omit({
  floorId: true,
  createdAt: true
});

export const insertLayoutSchema = createInsertSchema(layouts).omit({
  layoutId: true,
  createdAt: true
});

export const insertCounterSchema = createInsertSchema(counters).omit({
  counterId: true,
  createdAt: true,
  updatedAt: true
});

export const insertHallSchema = createInsertSchema(halls).omit({
  hallId: true,
  createdAt: true,
  updatedAt: true
});

export const insertSpaceAssetSchema = createInsertSchema(spaceAssets).omit({
  spaceId: true,
  createdAt: true
});

export const insertHotspotSchema = createInsertSchema(hotspots).omit({
  hotspotId: true,
  createdAt: true
});

// 商户品牌
export const insertTenantSchema = createInsertSchema(tenants).omit({
  tenantId: true,
  createdAt: true,
  updatedAt: true
});

export const insertBrandSchema = createInsertSchema(brands).omit({
  brandId: true,
  createdAt: true
});

// 合同财务
export const insertContractSchema = createInsertSchema(contracts).omit({
  contractId: true,
  createdAt: true,
  updatedAt: true
});

export const insertRentTermSchema = createInsertSchema(rentTerms).omit({
  termId: true,
  createdAt: true
});

export const insertBillSchema = createInsertSchema(bills).omit({
  billId: true,
  createdAt: true,
  updatedAt: true
});

// 向后兼容的插入模式
export const insertRoomSchema = createInsertSchema(rooms).omit({
  id: true,
  createdAt: true,
  updatedAt: true
});

export const insertFloorPlanSchema = createInsertSchema(floorPlans).omit({
  id: true,
  createdAt: true,
  updatedAt: true
});

export const insertActivitySchema = createInsertSchema(activities).omit({
  id: true,
  createdAt: true
});

export const insertUserMarkedRoomSchema = createInsertSchema(userMarkedRooms).omit({
  id: true,
  createdAt: true,
  updatedAt: true
});

// 用于插入操作的类型
export type InsertUser = z.infer<typeof insertUserSchema>;
export type InsertRole = z.infer<typeof insertRoleSchema>;
export type InsertStore = z.infer<typeof insertStoreSchema>;
export type InsertFloor = z.infer<typeof insertFloorSchema>;
export type InsertLayout = z.infer<typeof insertLayoutSchema>;
export type InsertCounter = z.infer<typeof insertCounterSchema>;
export type InsertHall = z.infer<typeof insertHallSchema>;
export type InsertSpaceAsset = z.infer<typeof insertSpaceAssetSchema>;
export type InsertHotspot = z.infer<typeof insertHotspotSchema>;
export type InsertTenant = z.infer<typeof insertTenantSchema>;
export type InsertBrand = z.infer<typeof insertBrandSchema>;
export type InsertContract = z.infer<typeof insertContractSchema>;
export type InsertRentTerm = z.infer<typeof insertRentTermSchema>;
export type InsertBill = z.infer<typeof insertBillSchema>;
export type InsertRoom = z.infer<typeof insertRoomSchema>;
export type InsertFloorPlan = z.infer<typeof insertFloorPlanSchema>;
export type InsertActivity = z.infer<typeof insertActivitySchema>;