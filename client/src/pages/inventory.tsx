import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, AlertTriangle, Package } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

interface InventoryItem {
  id: number;
  product: { name: string; sku: string; unit: string };
  warehouse: { name: string; location: string };
  quantity: number;
  minStock: number;
  maxStock: number;
  lastUpdated: string;
}

export default function Inventory() {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedWarehouse, setSelectedWarehouse] = useState<string>("all");

  const { data: inventory, isLoading } = useQuery<InventoryItem[]>({
    queryKey: ["/api/inventory"],
  });

  const warehouses = Array.from(
    new Set(inventory?.map((item) => item.warehouse.name) || [])
  );

  const filteredInventory = inventory?.filter((item) => {
    const matchesSearch =
      item.product.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.product.sku.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesWarehouse =
      selectedWarehouse === "all" || item.warehouse.name === selectedWarehouse;
    return matchesSearch && matchesWarehouse;
  });

  const lowStockItems = inventory?.filter((item) => item.quantity < item.minStock).length || 0;
  const totalItems = inventory?.length || 0;

  const getStockStatus = (item: InventoryItem) => {
    const percentage = (item.quantity / item.maxStock) * 100;
    if (item.quantity < item.minStock) return { status: "low", label: "Düşük Stok", color: "text-red-600" };
    if (percentage < 30) return { status: "warning", label: "Uyarı", color: "text-amber-600" };
    return { status: "good", label: "Yeterli", color: "text-green-600" };
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Envanter Yönetimi</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Stok seviyelerini yönetin ve takip edin
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Toplam Ürün
            </CardTitle>
            <Package className="w-4 h-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold" data-testid="stat-total-items">
              {totalItems}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Farklı ürün türü
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Düşük Stok Uyarısı
            </CardTitle>
            <AlertTriangle className="w-4 h-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold text-red-600" data-testid="stat-low-stock">
              {lowStockItems}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Minimum seviyenin altında
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Depo Sayısı
            </CardTitle>
            <Package className="w-4 h-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold" data-testid="stat-warehouses">
              {warehouses.length}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Aktif depo
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-4">
            <div>
              <CardTitle>Stok Seviyeleri</CardTitle>
              <CardDescription>Tüm ürünlerin envanter durumu</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Select value={selectedWarehouse} onValueChange={setSelectedWarehouse}>
                <SelectTrigger className="w-48" data-testid="select-warehouse">
                  <SelectValue placeholder="Depo seçin" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tüm Depolar</SelectItem>
                  {warehouses.map((warehouse) => (
                    <SelectItem key={warehouse} value={warehouse}>
                      {warehouse}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Ara..."
                  className="pl-8 w-48"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  data-testid="input-search"
                />
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <Skeleton key={i} className="h-16" />
              ))}
            </div>
          ) : !filteredInventory || filteredInventory.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              Envanter kaydı bulunamadı
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Ürün</TableHead>
                  <TableHead>Depo</TableHead>
                  <TableHead>Mevcut Stok</TableHead>
                  <TableHead>Min/Max</TableHead>
                  <TableHead>Doluluk</TableHead>
                  <TableHead>Durum</TableHead>
                  <TableHead>Son Güncelleme</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredInventory.map((item) => {
                  const stockStatus = getStockStatus(item);
                  const fillPercentage = (item.quantity / item.maxStock) * 100;

                  return (
                    <TableRow key={item.id} className="hover-elevate" data-testid={`inventory-${item.id}`}>
                      <TableCell>
                        <div>
                          <p className="font-medium">{item.product.name}</p>
                          <p className="text-xs text-muted-foreground">{item.product.sku}</p>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div>
                          <p className="font-medium">{item.warehouse.name}</p>
                          <p className="text-xs text-muted-foreground">{item.warehouse.location}</p>
                        </div>
                      </TableCell>
                      <TableCell className="font-mono font-semibold">
                        {item.quantity} {item.product.unit}
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {item.minStock} / {item.maxStock}
                      </TableCell>
                      <TableCell>
                        <div className="w-24">
                          <Progress value={fillPercentage} className="h-2" />
                          <p className="text-xs text-muted-foreground mt-1">
                            {fillPercentage.toFixed(0)}%
                          </p>
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className={`text-sm font-medium ${stockStatus.color}`}>
                          {stockStatus.label}
                        </span>
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {new Date(item.lastUpdated).toLocaleDateString('tr-TR', {
                          day: '2-digit',
                          month: 'short',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
