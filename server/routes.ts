import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { insertUserSchema, insertProductionOrderSchema, insertShipmentSchema } from "@shared/schema";
import session from "express-session";
import bcrypt from "bcryptjs";

const SESSION_SECRET = process.env.SESSION_SECRET || "your-secret-key-change-in-production";

declare module "express-session" {
  interface SessionData {
    userId: number;
  }
}

export async function registerRoutes(app: Express): Promise<Server> {
  // Session middleware
  app.use(
    session({
      secret: SESSION_SECRET,
      resave: false,
      saveUninitialized: false,
      cookie: {
        secure: process.env.NODE_ENV === "production",
        httpOnly: true,
        maxAge: 1000 * 60 * 60 * 24 * 7, // 1 week
      },
    })
  );

  // Auth middleware
  const requireAuth = (req: any, res: any, next: any) => {
    if (!req.session.userId) {
      return res.status(401).json({ message: "Unauthorized" });
    }
    next();
  };

  // Authentication routes
  app.post("/api/auth/register", async (req, res) => {
    try {
      const { username, password, email, fullName } = insertUserSchema.parse(req.body);
      
      const existing = await storage.getUserByUsername(username);
      if (existing) {
        return res.status(400).json({ message: "Kullanıcı adı zaten kullanımda" });
      }

      const hashedPassword = await bcrypt.hash(password, 10);
      const user = await storage.createUser({
        username,
        password: hashedPassword,
        email,
        fullName,
        role: "operator",
      });

      req.session.userId = user.id;
      res.json({ id: user.id, username: user.username, email: user.email, fullName: user.fullName });
    } catch (error: any) {
      res.status(400).json({ message: error.message || "Kayıt başarısız" });
    }
  });

  app.post("/api/auth/login", async (req, res) => {
    try {
      const { username, password } = req.body;
      
      const user = await storage.getUserByUsername(username);
      if (!user) {
        return res.status(401).json({ message: "Geçersiz kullanıcı adı veya şifre" });
      }

      const valid = await bcrypt.compare(password, user.password);
      if (!valid) {
        return res.status(401).json({ message: "Geçersiz kullanıcı adı veya şifre" });
      }

      req.session.userId = user.id;
      res.json({ id: user.id, username: user.username, email: user.email, fullName: user.fullName });
    } catch (error: any) {
      res.status(400).json({ message: error.message || "Giriş başarısız" });
    }
  });

  app.post("/api/auth/logout", (req, res) => {
    req.session.destroy(() => {
      res.json({ message: "Çıkış başarılı" });
    });
  });

  app.get("/api/auth/me", requireAuth, async (req, res) => {
    try {
      const user = await storage.getUser(req.session.userId!);
      if (!user) {
        return res.status(404).json({ message: "Kullanıcı bulunamadı" });
      }
      res.json({ id: user.id, username: user.username, email: user.email, fullName: user.fullName });
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  // Dashboard routes
  app.get("/api/dashboard/stats", requireAuth, async (req, res) => {
    try {
      const stats = await storage.getDashboardStats();
      res.json(stats);
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  // Facilities routes
  app.get("/api/facilities", requireAuth, async (req, res) => {
    try {
      const facilities = await storage.getFacilities();
      res.json(facilities);
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  // Products routes
  app.get("/api/products", requireAuth, async (req, res) => {
    try {
      const products = await storage.getProducts();
      res.json(products);
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  // Production Orders routes
  app.get("/api/production/orders", requireAuth, async (req, res) => {
    try {
      const orders = await storage.getProductionOrders();
      res.json(orders);
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  app.post("/api/production/orders", requireAuth, async (req, res) => {
    try {
      const orderData = insertProductionOrderSchema.parse({
        ...req.body,
        createdBy: req.session.userId,
      });
      const order = await storage.createProductionOrder(orderData);
      res.status(201).json(order);
    } catch (error: any) {
      res.status(400).json({ message: error.message });
    }
  });

  app.patch("/api/production/orders/:id", requireAuth, async (req, res) => {
    try {
      const id = parseInt(req.params.id);
      const order = await storage.updateProductionOrder(id, req.body);
      res.json(order);
    } catch (error: any) {
      res.status(400).json({ message: error.message });
    }
  });

  // Warehouses routes
  app.get("/api/warehouses", requireAuth, async (req, res) => {
    try {
      const warehouses = await storage.getWarehouses();
      res.json(warehouses);
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  // Inventory routes
  app.get("/api/inventory", requireAuth, async (req, res) => {
    try {
      const inventory = await storage.getInventory();
      res.json(inventory);
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  // Shipments routes
  app.get("/api/shipments", requireAuth, async (req, res) => {
    try {
      const shipments = await storage.getShipments();
      res.json(shipments);
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  app.post("/api/shipments", requireAuth, async (req, res) => {
    try {
      const shipmentData = insertShipmentSchema.parse({
        ...req.body,
        createdBy: req.session.userId,
      });
      const shipment = await storage.createShipment(shipmentData);
      res.status(201).json(shipment);
    } catch (error: any) {
      res.status(400).json({ message: error.message });
    }
  });

  app.patch("/api/shipments/:id", requireAuth, async (req, res) => {
    try {
      const id = parseInt(req.params.id);
      const shipment = await storage.updateShipment(id, req.body);
      res.json(shipment);
    } catch (error: any) {
      res.status(400).json({ message: error.message });
    }
  });

  const httpServer = createServer(app);
  return httpServer;
}
