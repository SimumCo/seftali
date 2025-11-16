import { db } from "./db";
import { users, facilities, products, warehouses, inventory, productionOrders, shipments } from "@shared/schema";
import bcrypt from "bcryptjs";

async function seed() {
  console.log("🌱 Seeding database...");

  try {
    // Create admin user
    const hashedPassword = await bcrypt.hash("admin123", 10);
    const [admin] = await db.insert(users).values({
      username: "admin",
      password: hashedPassword,
      email: "admin@system.com",
      fullName: "Sistem Yöneticisi",
      role: "admin",
    }).returning();
    console.log("✅ Admin user created");

    // Create facilities
    const facilityData = [
      { name: "İstanbul Fabrika", location: "İstanbul, Türkiye", type: "factory", capacity: 5000, active: 1 },
      { name: "Ankara Fabrika", location: "Ankara, Türkiye", type: "factory", capacity: 3000, active: 1 },
      { name: "İzmir Üretim", location: "İzmir, Türkiye", type: "factory", capacity: 2500, active: 1 },
    ];
    const createdFacilities = await db.insert(facilities).values(facilityData).returning();
    console.log("✅ Facilities created");

    // Create products
    const productData = [
      { name: "Ürün A", sku: "PRD-A-001", description: "Premium kalite ürün", unit: "adet", unitPrice: "150.00" },
      { name: "Ürün B", sku: "PRD-B-001", description: "Standart ürün", unit: "adet", unitPrice: "85.00" },
      { name: "Ürün C", sku: "PRD-C-001", description: "Ekonomik ürün", unit: "adet", unitPrice: "50.00" },
      { name: "Ürün D", sku: "PRD-D-001", description: "Özel ürün", unit: "kg", unitPrice: "200.00" },
      { name: "Ürün E", sku: "PRD-E-001", description: "Toptan ürün", unit: "paket", unitPrice: "120.00" },
    ];
    const createdProducts = await db.insert(products).values(productData).returning();
    console.log("✅ Products created");

    // Create warehouses
    const warehouseData = [
      { name: "Merkez Depo", location: "İstanbul, Türkiye", capacity: 10000, active: 1 },
      { name: "Bölge Depo 1", location: "Ankara, Türkiye", capacity: 5000, active: 1 },
      { name: "Bölge Depo 2", location: "İzmir, Türkiye", capacity: 5000, active: 1 },
    ];
    const createdWarehouses = await db.insert(warehouses).values(warehouseData).returning();
    console.log("✅ Warehouses created");

    // Create inventory
    const inventoryData = [];
    for (const product of createdProducts) {
      for (const warehouse of createdWarehouses) {
        const quantity = Math.floor(Math.random() * 500) + 50;
        inventoryData.push({
          productId: product.id,
          warehouseId: warehouse.id,
          quantity,
          minStock: 100,
          maxStock: 1000,
        });
      }
    }
    await db.insert(inventory).values(inventoryData);
    console.log("✅ Inventory created");

    // Create production orders
    const orderStatuses = ["pending", "in_progress", "completed"] as const;
    const priorities = ["low", "medium", "high", "urgent"] as const;
    const productionOrderData = [];

    for (let i = 1; i <= 15; i++) {
      const product = createdProducts[Math.floor(Math.random() * createdProducts.length)];
      const facility = createdFacilities[Math.floor(Math.random() * createdFacilities.length)];
      const status = orderStatuses[Math.floor(Math.random() * orderStatuses.length)];
      const priority = priorities[Math.floor(Math.random() * priorities.length)];
      
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - Math.floor(Math.random() * 30));

      productionOrderData.push({
        orderNumber: `ORD-${String(i).padStart(4, '0')}`,
        productId: product.id,
        facilityId: facility.id,
        quantity: Math.floor(Math.random() * 500) + 50,
        status,
        priority,
        startDate,
        endDate: null,
        completedDate: status === 'completed' ? startDate : null,
        notes: `Üretim siparişi ${i}`,
        createdBy: admin.id,
      });
    }
    await db.insert(productionOrders).values(productionOrderData);
    console.log("✅ Production orders created");

    // Create shipments
    const shipmentStatuses = ["pending", "in_transit", "delivered"] as const;
    const shipmentData = [];
    const destinations = [
      "İstanbul, Kadıköy",
      "Ankara, Çankaya",
      "İzmir, Konak",
      "Bursa, Osmangazi",
      "Antalya, Muratpaşa",
      "Gaziantep, Şahinbey",
    ];

    for (let i = 1; i <= 12; i++) {
      const product = createdProducts[Math.floor(Math.random() * createdProducts.length)];
      const warehouse = createdWarehouses[Math.floor(Math.random() * createdWarehouses.length)];
      const status = shipmentStatuses[Math.floor(Math.random() * shipmentStatuses.length)];
      const destination = destinations[Math.floor(Math.random() * destinations.length)];

      const estimatedDelivery = new Date();
      estimatedDelivery.setDate(estimatedDelivery.getDate() + Math.floor(Math.random() * 7) + 1);

      shipmentData.push({
        shipmentNumber: `SHP-${String(i).padStart(4, '0')}`,
        productId: product.id,
        fromWarehouseId: warehouse.id,
        toLocation: destination,
        quantity: Math.floor(Math.random() * 200) + 20,
        status,
        driverName: `Sürücü ${i}`,
        vehicleNumber: `34 ABC ${String(i).padStart(3, '0')}`,
        estimatedDelivery,
        actualDelivery: status === 'delivered' ? estimatedDelivery : null,
        notes: `Sevkiyat ${i}`,
        createdBy: admin.id,
      });
    }
    await db.insert(shipments).values(shipmentData);
    console.log("✅ Shipments created");

    console.log("\n✨ Database seeding completed successfully!");
    console.log("\n📝 Login credentials:");
    console.log("   Username: admin");
    console.log("   Password: admin123");
    
  } catch (error) {
    console.error("❌ Error seeding database:", error);
    throw error;
  }
}

seed()
  .then(() => process.exit(0))
  .catch(() => process.exit(1));
