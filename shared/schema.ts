import { sql } from "drizzle-orm";
import { pgTable, text, varchar, integer, timestamp, decimal, pgEnum } from "drizzle-orm/pg-core";
import { relations } from "drizzle-orm";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

// Enums
export const orderStatusEnum = pgEnum("order_status", ["pending", "in_progress", "completed", "cancelled"]);
export const shipmentStatusEnum = pgEnum("shipment_status", ["pending", "in_transit", "delivered", "cancelled"]);
export const priorityEnum = pgEnum("priority", ["low", "medium", "high", "urgent"]);

// Users table
export const users = pgTable("users", {
  id: integer("id").primaryKey().generatedAlwaysAsIdentity(),
  username: text("username").notNull().unique(),
  password: text("password").notNull(),
  email: text("email").notNull().unique(),
  fullName: text("full_name").notNull(),
  role: text("role").notNull().default("operator"), // operator, manager, admin
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

// Facilities table
export const facilities = pgTable("facilities", {
  id: integer("id").primaryKey().generatedAlwaysAsIdentity(),
  name: text("name").notNull(),
  location: text("location").notNull(),
  type: text("type").notNull(), // factory, warehouse, distribution_center
  capacity: integer("capacity").notNull(),
  active: integer("active").notNull().default(1), // 0 or 1 for boolean
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

// Products table
export const products = pgTable("products", {
  id: integer("id").primaryKey().generatedAlwaysAsIdentity(),
  name: text("name").notNull(),
  sku: text("sku").notNull().unique(),
  description: text("description"),
  unit: text("unit").notNull().default("piece"), // piece, kg, liter, etc
  unitPrice: decimal("unit_price", { precision: 10, scale: 2 }).notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

// Production Orders table
export const productionOrders = pgTable("production_orders", {
  id: integer("id").primaryKey().generatedAlwaysAsIdentity(),
  orderNumber: text("order_number").notNull().unique(),
  productId: integer("product_id").notNull().references(() => products.id),
  facilityId: integer("facility_id").notNull().references(() => facilities.id),
  quantity: integer("quantity").notNull(),
  status: orderStatusEnum("status").notNull().default("pending"),
  priority: priorityEnum("priority").notNull().default("medium"),
  startDate: timestamp("start_date"),
  endDate: timestamp("end_date"),
  completedDate: timestamp("completed_date"),
  notes: text("notes"),
  createdBy: integer("created_by").notNull().references(() => users.id),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// Warehouses table
export const warehouses = pgTable("warehouses", {
  id: integer("id").primaryKey().generatedAlwaysAsIdentity(),
  name: text("name").notNull(),
  location: text("location").notNull(),
  capacity: integer("capacity").notNull(),
  active: integer("active").notNull().default(1),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

// Inventory table
export const inventory = pgTable("inventory", {
  id: integer("id").primaryKey().generatedAlwaysAsIdentity(),
  productId: integer("product_id").notNull().references(() => products.id),
  warehouseId: integer("warehouse_id").notNull().references(() => warehouses.id),
  quantity: integer("quantity").notNull().default(0),
  minStock: integer("min_stock").notNull().default(10),
  maxStock: integer("max_stock").notNull().default(1000),
  lastUpdated: timestamp("last_updated").defaultNow().notNull(),
});

// Shipments table
export const shipments = pgTable("shipments", {
  id: integer("id").primaryKey().generatedAlwaysAsIdentity(),
  shipmentNumber: text("shipment_number").notNull().unique(),
  productId: integer("product_id").notNull().references(() => products.id),
  fromWarehouseId: integer("from_warehouse_id").notNull().references(() => warehouses.id),
  toLocation: text("to_location").notNull(),
  quantity: integer("quantity").notNull(),
  status: shipmentStatusEnum("status").notNull().default("pending"),
  driverName: text("driver_name"),
  vehicleNumber: text("vehicle_number"),
  estimatedDelivery: timestamp("estimated_delivery"),
  actualDelivery: timestamp("actual_delivery"),
  notes: text("notes"),
  createdBy: integer("created_by").notNull().references(() => users.id),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// Relations
export const usersRelations = relations(users, ({ many }) => ({
  productionOrders: many(productionOrders),
  shipments: many(shipments),
}));

export const facilitiesRelations = relations(facilities, ({ many }) => ({
  productionOrders: many(productionOrders),
}));

export const productsRelations = relations(products, ({ many }) => ({
  productionOrders: many(productionOrders),
  inventory: many(inventory),
  shipments: many(shipments),
}));

export const productionOrdersRelations = relations(productionOrders, ({ one }) => ({
  product: one(products, {
    fields: [productionOrders.productId],
    references: [products.id],
  }),
  facility: one(facilities, {
    fields: [productionOrders.facilityId],
    references: [facilities.id],
  }),
  createdByUser: one(users, {
    fields: [productionOrders.createdBy],
    references: [users.id],
  }),
}));

export const warehousesRelations = relations(warehouses, ({ many }) => ({
  inventory: many(inventory),
  shipmentsFrom: many(shipments),
}));

export const inventoryRelations = relations(inventory, ({ one }) => ({
  product: one(products, {
    fields: [inventory.productId],
    references: [products.id],
  }),
  warehouse: one(warehouses, {
    fields: [inventory.warehouseId],
    references: [warehouses.id],
  }),
}));

export const shipmentsRelations = relations(shipments, ({ one }) => ({
  product: one(products, {
    fields: [shipments.productId],
    references: [products.id],
  }),
  fromWarehouse: one(warehouses, {
    fields: [shipments.fromWarehouseId],
    references: [warehouses.id],
  }),
  createdByUser: one(users, {
    fields: [shipments.createdBy],
    references: [users.id],
  }),
}));

// Insert schemas
export const insertUserSchema = createInsertSchema(users).omit({
  id: true,
  createdAt: true,
});

export const insertFacilitySchema = createInsertSchema(facilities).omit({
  id: true,
  createdAt: true,
});

export const insertProductSchema = createInsertSchema(products).omit({
  id: true,
  createdAt: true,
});

export const insertProductionOrderSchema = createInsertSchema(productionOrders).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

export const insertWarehouseSchema = createInsertSchema(warehouses).omit({
  id: true,
  createdAt: true,
});

export const insertInventorySchema = createInsertSchema(inventory).omit({
  id: true,
  lastUpdated: true,
});

export const insertShipmentSchema = createInsertSchema(shipments).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

// Types
export type InsertUser = z.infer<typeof insertUserSchema>;
export type User = typeof users.$inferSelect;

export type InsertFacility = z.infer<typeof insertFacilitySchema>;
export type Facility = typeof facilities.$inferSelect;

export type InsertProduct = z.infer<typeof insertProductSchema>;
export type Product = typeof products.$inferSelect;

export type InsertProductionOrder = z.infer<typeof insertProductionOrderSchema>;
export type ProductionOrder = typeof productionOrders.$inferSelect;

export type InsertWarehouse = z.infer<typeof insertWarehouseSchema>;
export type Warehouse = typeof warehouses.$inferSelect;

export type InsertInventory = z.infer<typeof insertInventorySchema>;
export type Inventory = typeof inventory.$inferSelect;

export type InsertShipment = z.infer<typeof insertShipmentSchema>;
export type Shipment = typeof shipments.$inferSelect;
