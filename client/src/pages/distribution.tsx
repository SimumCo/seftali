import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Plus, Search, MapPin } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { StatusBadge } from "@/components/status-badge";
import { useToast } from "@/hooks/use-toast";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { insertShipmentSchema, type Product, type Warehouse } from "@shared/schema";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { Skeleton } from "@/components/ui/skeleton";

interface Shipment {
  id: number;
  shipmentNumber: string;
  product: { name: string };
  fromWarehouse: { name: string; location: string };
  toLocation: string;
  quantity: number;
  status: string;
  driverName: string | null;
  vehicleNumber: string | null;
  estimatedDelivery: string | null;
  createdAt: string;
}

export default function Distribution() {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const { toast } = useToast();

  const { data: shipments, isLoading } = useQuery<Shipment[]>({
    queryKey: ["/api/shipments"],
  });

  const { data: products } = useQuery<Product[]>({
    queryKey: ["/api/products"],
  });

  const { data: warehouses } = useQuery<Warehouse[]>({
    queryKey: ["/api/warehouses"],
  });

  const form = useForm({
    resolver: zodResolver(insertShipmentSchema.extend({
      productId: insertShipmentSchema.shape.productId.transform(Number),
      fromWarehouseId: insertShipmentSchema.shape.fromWarehouseId.transform(Number),
      quantity: insertShipmentSchema.shape.quantity.transform(Number),
      createdBy: insertShipmentSchema.shape.createdBy.transform(Number),
    })),
    defaultValues: {
      shipmentNumber: "",
      productId: 0,
      fromWarehouseId: 0,
      toLocation: "",
      quantity: 0,
      status: "pending" as const,
      driverName: "",
      vehicleNumber: "",
      estimatedDelivery: null,
      notes: "",
      createdBy: 1,
    },
  });

  const createShipmentMutation = useMutation({
    mutationFn: async (data: any) => {
      return await apiRequest("POST", "/api/shipments", data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/shipments"] });
      toast({
        title: "Başarılı",
        description: "Sevkiyat oluşturuldu",
      });
      setIsOpen(false);
      form.reset();
    },
    onError: (error: any) => {
      toast({
        title: "Hata",
        description: error.message || "Sevkiyat oluşturulamadı",
        variant: "destructive",
      });
    },
  });

  const filteredShipments = shipments?.filter((shipment) =>
    shipment.shipmentNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
    shipment.toLocation.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Dağıtım Takibi</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Sevkiyatları yönetin ve takip edin
          </p>
        </div>
        <Dialog open={isOpen} onOpenChange={setIsOpen}>
          <DialogTrigger asChild>
            <Button data-testid="button-new-shipment">
              <Plus className="w-4 h-4 mr-2" />
              Yeni Sevkiyat
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Yeni Sevkiyat</DialogTitle>
              <DialogDescription>
                Yeni bir sevkiyat oluşturun
              </DialogDescription>
            </DialogHeader>
            <Form {...form}>
              <form onSubmit={form.handleSubmit((data) => createShipmentMutation.mutate(data))} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <FormField
                    control={form.control}
                    name="shipmentNumber"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Sevkiyat Numarası</FormLabel>
                        <FormControl>
                          <Input placeholder="SHP-001" {...field} data-testid="input-shipment-number" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="productId"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Ürün</FormLabel>
                        <Select onValueChange={(value) => field.onChange(Number(value))} value={field.value?.toString()}>
                          <FormControl>
                            <SelectTrigger data-testid="select-product">
                              <SelectValue placeholder="Ürün seçin" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {products?.map((product) => (
                              <SelectItem key={product.id} value={product.id.toString()}>
                                {product.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <FormField
                    control={form.control}
                    name="fromWarehouseId"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Çıkış Deposu</FormLabel>
                        <Select onValueChange={(value) => field.onChange(Number(value))} value={field.value?.toString()}>
                          <FormControl>
                            <SelectTrigger data-testid="select-warehouse">
                              <SelectValue placeholder="Depo seçin" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {warehouses?.map((warehouse) => (
                              <SelectItem key={warehouse.id} value={warehouse.id.toString()}>
                                {warehouse.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="toLocation"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Varış Noktası</FormLabel>
                        <FormControl>
                          <Input placeholder="İstanbul, Türkiye" {...field} data-testid="input-destination" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <FormField
                    control={form.control}
                    name="quantity"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Miktar</FormLabel>
                        <FormControl>
                          <Input type="number" placeholder="50" {...field} onChange={(e) => field.onChange(Number(e.target.value))} data-testid="input-quantity" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="estimatedDelivery"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Tahmini Teslimat</FormLabel>
                        <FormControl>
                          <Input 
                            type="datetime-local" 
                            {...field} 
                            value={field.value ? new Date(field.value).toISOString().slice(0, 16) : ''}
                            onChange={(e) => field.onChange(e.target.value ? new Date(e.target.value).toISOString() : null)}
                            data-testid="input-estimated-delivery" 
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <FormField
                    control={form.control}
                    name="driverName"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Sürücü</FormLabel>
                        <FormControl>
                          <Input placeholder="Ahmet Yılmaz" {...field} value={field.value || ""} data-testid="input-driver" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="vehicleNumber"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Araç Plakası</FormLabel>
                        <FormControl>
                          <Input placeholder="34 ABC 123" {...field} value={field.value || ""} data-testid="input-vehicle" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
                <FormField
                  control={form.control}
                  name="notes"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Notlar</FormLabel>
                      <FormControl>
                        <Textarea placeholder="Sevkiyat notları..." {...field} value={field.value || ""} data-testid="input-notes" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <div className="flex justify-end gap-2">
                  <Button type="button" variant="outline" onClick={() => setIsOpen(false)}>
                    İptal
                  </Button>
                  <Button type="submit" disabled={createShipmentMutation.isPending} data-testid="button-submit-shipment">
                    {createShipmentMutation.isPending ? "Oluşturuluyor..." : "Oluştur"}
                  </Button>
                </div>
              </form>
            </Form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Aktif Sevkiyatlar</CardTitle>
                <CardDescription>Tüm sevkiyatların listesi</CardDescription>
              </div>
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
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-24" />
                ))}
              </div>
            ) : !filteredShipments || filteredShipments.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                Henüz sevkiyat bulunmuyor
              </p>
            ) : (
              <div className="space-y-4">
                {filteredShipments.map((shipment) => (
                  <Card key={shipment.id} className="hover-elevate" data-testid={`shipment-${shipment.id}`}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <p className="font-medium font-mono">{shipment.shipmentNumber}</p>
                          <p className="text-sm text-muted-foreground">{shipment.product.name}</p>
                        </div>
                        <StatusBadge status={shipment.status} />
                      </div>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <p className="text-muted-foreground">Çıkış</p>
                          <p className="font-medium">{shipment.fromWarehouse.name}</p>
                          <p className="text-xs text-muted-foreground">{shipment.fromWarehouse.location}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Varış</p>
                          <p className="font-medium flex items-center gap-1">
                            <MapPin className="w-3 h-3" />
                            {shipment.toLocation}
                          </p>
                        </div>
                      </div>
                      {shipment.driverName && (
                        <div className="mt-3 pt-3 border-t text-sm">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Sürücü:</span>
                            <span className="font-medium">{shipment.driverName}</span>
                          </div>
                          {shipment.vehicleNumber && (
                            <div className="flex justify-between mt-1">
                              <span className="text-muted-foreground">Plaka:</span>
                              <span className="font-mono">{shipment.vehicleNumber}</span>
                            </div>
                          )}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Dağıtım Haritası</CardTitle>
            <CardDescription>Sevkiyat rotaları</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="bg-muted rounded-md p-8 text-center h-96 flex items-center justify-center">
              <div className="text-muted-foreground">
                <MapPin className="w-12 h-12 mx-auto mb-2" />
                <p className="text-sm">Harita görünümü</p>
                <p className="text-xs mt-1">Yakında eklenecek</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
