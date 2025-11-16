import {
  users, facilities, products, productionOrders, warehouses, inventory, shipments,
  type User, type InsertUser,
  type Facility, type InsertFacility,
  type Product, type InsertProduct,
  type ProductionOrder, type InsertProductionOrder,
  type Warehouse, type InsertWarehouse,
  type Inventory, type InsertInventory,
  type Shipment, type InsertShipment,
} from "@shared/schema";
import { db } from "./db";
import { eq, desc, and, lt } from "drizzle-orm";

export interface IStorage {
  // Users
  getUser(id: number): Promise<User | undefined>;
  getUserByUsername(username: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;

  // Facilities
  getFacilities(): Promise<Facility[]>;
  createFacility(facility: InsertFacility): Promise<Facility>;

  // Products
  getProducts(): Promise<Product[]>;
  createProduct(product: InsertProduct): Promise<Product>;

  // Production Orders
  getProductionOrders(): Promise<any[]>;
  getProductionOrderById(id: number): Promise<any | undefined>;
  createProductionOrder(order: InsertProductionOrder): Promise<ProductionOrder>;
  updateProductionOrder(id: number, order: Partial<InsertProductionOrder>): Promise<ProductionOrder>;

  // Warehouses
  getWarehouses(): Promise<Warehouse[]>;
  createWarehouse(warehouse: InsertWarehouse): Promise<Warehouse>;

  // Inventory
  getInventory(): Promise<any[]>;
  updateInventory(id: number, inventory: Partial<InsertInventory>): Promise<Inventory>;

  // Shipments
  getShipments(): Promise<any[]>;
  getShipmentById(id: number): Promise<any | undefined>;
  createShipment(shipment: InsertShipment): Promise<Shipment>;
  updateShipment(id: number, shipment: Partial<InsertShipment>): Promise<Shipment>;

  // Dashboard
  getDashboardStats(): Promise<any>;
}

export class DatabaseStorage implements IStorage {
  // Users
  async getUser(id: number): Promise<User | undefined> {
    const [user] = await db.select().from(users).where(eq(users.id, id));
    return user || undefined;
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    const [user] = await db.select().from(users).where(eq(users.username, username));
    return user || undefined;
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const [user] = await db.insert(users).values(insertUser).returning();
    return user;
  }

  // Facilities
  async getFacilities(): Promise<Facility[]> {
    return await db.select().from(facilities).orderBy(desc(facilities.createdAt));
  }

  async createFacility(facility: InsertFacility): Promise<Facility> {
    const [newFacility] = await db.insert(facilities).values(facility).returning();
    return newFacility;
  }

  // Products
  async getProducts(): Promise<Product[]> {
    return await db.select().from(products).orderBy(desc(products.createdAt));
  }

  async createProduct(product: InsertProduct): Promise<Product> {
    const [newProduct] = await db.insert(products).values(product).returning();
    return newProduct;
  }

  // Production Orders
  async getProductionOrders(): Promise<any[]> {
    const ordersRaw = await db
      .select()
      .from(productionOrders)
      .orderBy(desc(productionOrders.createdAt));

    const result = [];
    for (const order of ordersRaw) {
      const [product] = await db.select().from(products).where(eq(products.id, order.productId));
      const [facility] = await db.select().from(facilities).where(eq(facilities.id, order.facilityId));
      
      result.push({
        ...order,
        product: product ? { id: product.id, name: product.name, sku: product.sku } : null,
        facility: facility ? { id: facility.id, name: facility.name, location: facility.location } : null,
      });
    }

    return result;
  }

  async getProductionOrderById(id: number): Promise<any | undefined> {
    const [order] = await db
      .select()
      .from(productionOrders)
      .where(eq(productionOrders.id, id));
    return order || undefined;
  }

  async createProductionOrder(order: InsertProductionOrder): Promise<ProductionOrder> {
    const [newOrder] = await db.insert(productionOrders).values(order).returning();
    return newOrder;
  }

  async updateProductionOrder(id: number, order: Partial<InsertProductionOrder>): Promise<ProductionOrder> {
    const [updated] = await db
      .update(productionOrders)
      .set({ ...order, updatedAt: new Date() })
      .where(eq(productionOrders.id, id))
      .returning();
    return updated;
  }

  // Warehouses
  async getWarehouses(): Promise<Warehouse[]> {
    return await db.select().from(warehouses).orderBy(desc(warehouses.createdAt));
  }

  async createWarehouse(warehouse: InsertWarehouse): Promise<Warehouse> {
    const [newWarehouse] = await db.insert(warehouses).values(warehouse).returning();
    return newWarehouse;
  }

  // Inventory
  async getInventory(): Promise<any[]> {
    const inventoryRaw = await db.select().from(inventory).orderBy(desc(inventory.lastUpdated));

    const result = [];
    for (const item of inventoryRaw) {
      const [product] = await db.select().from(products).where(eq(products.id, item.productId));
      const [warehouse] = await db.select().from(warehouses).where(eq(warehouses.id, item.warehouseId));
      
      result.push({
        ...item,
        product: product ? { id: product.id, name: product.name, sku: product.sku, unit: product.unit } : null,
        warehouse: warehouse ? { id: warehouse.id, name: warehouse.name, location: warehouse.location } : null,
      });
    }

    return result;
  }

  async updateInventory(id: number, inventoryUpdate: Partial<InsertInventory>): Promise<Inventory> {
    const [updated] = await db
      .update(inventory)
      .set({ ...inventoryUpdate, lastUpdated: new Date() })
      .where(eq(inventory.id, id))
      .returning();
    return updated;
  }

  // Shipments
  async getShipments(): Promise<any[]> {
    const shipmentsRaw = await db.select().from(shipments).orderBy(desc(shipments.createdAt));

    const result = [];
    for (const shipment of shipmentsRaw) {
      const [product] = await db.select().from(products).where(eq(products.id, shipment.productId));
      const [warehouse] = await db.select().from(warehouses).where(eq(warehouses.id, shipment.fromWarehouseId));
      
      result.push({
        ...shipment,
        product: product ? { id: product.id, name: product.name, sku: product.sku } : null,
        fromWarehouse: warehouse ? { id: warehouse.id, name: warehouse.name, location: warehouse.location } : null,
      });
    }

    return result;
  }

  async getShipmentById(id: number): Promise<any | undefined> {
    const [shipment] = await db
      .select()
      .from(shipments)
      .where(eq(shipments.id, id));
    return shipment || undefined;
  }

  async createShipment(shipment: InsertShipment): Promise<Shipment> {
    const [newShipment] = await db.insert(shipments).values(shipment).returning();
    return newShipment;
  }

  async updateShipment(id: number, shipmentUpdate: Partial<InsertShipment>): Promise<Shipment> {
    const [updated] = await db
      .update(shipments)
      .set({ ...shipmentUpdate, updatedAt: new Date() })
      .where(eq(shipments.id, id))
      .returning();
    return updated;
  }

  // Dashboard
  async getDashboardStats(): Promise<any> {
    const allOrders = await db.select().from(productionOrders);
    const allShipments = await db.select().from(shipments);
    const allInventory = await db.select().from(inventory);

    const totalProduction = allOrders.filter(o => o.status === 'completed').length;
    const activeShipments = allShipments.filter(s => s.status === 'in_transit').length;
    const pendingOrders = allOrders.filter(o => o.status === 'pending').length;
    const inventoryAlerts = allInventory.filter(inv => inv.quantity < inv.minStock).length;

    // Recent activity
    const recentOrders = allOrders.slice(0, 5).map(order => ({
      id: order.id,
      type: 'Üretim',
      description: `Sipariş ${order.orderNumber}`,
      status: order.status,
      timestamp: order.createdAt,
    }));

    const recentShipments = allShipments.slice(0, 5).map(shipment => ({
      id: shipment.id + 1000,
      type: 'Sevkiyat',
      description: `Sevkiyat ${shipment.shipmentNumber}`,
      status: shipment.status,
      timestamp: shipment.createdAt,
    }));

    const recentActivity = [...recentOrders, ...recentShipments]
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, 10);

    return {
      totalProduction,
      activeShipments,
      pendingOrders,
      inventoryAlerts,
      recentActivity,
    };
  }
}

export const storage = new DatabaseStorage();
