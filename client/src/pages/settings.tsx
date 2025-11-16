import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Settings as SettingsIcon, Building2, Package2, Warehouse } from "lucide-react";

export default function Settings() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Ayarlar</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Sistem ayarlarını yönetin
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Building2 className="w-5 h-5 text-muted-foreground" />
              <CardTitle>Tesisler</CardTitle>
            </div>
            <CardDescription>
              Üretim tesislerini yönetin
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Yakında eklenecek
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Package2 className="w-5 h-5 text-muted-foreground" />
              <CardTitle>Ürünler</CardTitle>
            </div>
            <CardDescription>
              Ürün kataloğunu yönetin
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Yakında eklenecek
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Warehouse className="w-5 h-5 text-muted-foreground" />
              <CardTitle>Depolar</CardTitle>
            </div>
            <CardDescription>
              Depo bilgilerini yönetin
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Yakında eklenecek
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <SettingsIcon className="w-5 h-5 text-muted-foreground" />
              <CardTitle>Genel Ayarlar</CardTitle>
            </div>
            <CardDescription>
              Sistem ayarlarını yapılandırın
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Yakında eklenecek
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
