import { useQuery } from "@tanstack/react-query";
import { StatCard } from "@/components/stat-card";
import { Package, Truck, AlertTriangle, CheckCircle } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { StatusBadge } from "@/components/status-badge";
import { Skeleton } from "@/components/ui/skeleton";

interface DashboardStats {
  totalProduction: number;
  activeShipments: number;
  pendingOrders: number;
  inventoryAlerts: number;
  recentActivity: Array<{
    id: number;
    type: string;
    description: string;
    status: string;
    timestamp: string;
  }>;
}

export default function Dashboard() {
  const { data: stats, isLoading } = useQuery<DashboardStats>({
    queryKey: ["/api/dashboard/stats"],
  });

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Genel bakış ve önemli metrikler
          </p>
        </div>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Genel bakış ve önemli metrikler
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Bugünkü Üretim"
          value={stats?.totalProduction || 0}
          icon={Package}
          trend={{ value: 12, isPositive: true }}
          testId="stat-production"
        />
        <StatCard
          title="Aktif Sevkiyatlar"
          value={stats?.activeShipments || 0}
          icon={Truck}
          trend={{ value: 8, isPositive: true }}
          testId="stat-shipments"
        />
        <StatCard
          title="Bekleyen Siparişler"
          value={stats?.pendingOrders || 0}
          icon={CheckCircle}
          trend={{ value: 3, isPositive: false }}
          testId="stat-orders"
        />
        <StatCard
          title="Envanter Uyarıları"
          value={stats?.inventoryAlerts || 0}
          icon={AlertTriangle}
          testId="stat-alerts"
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Son Aktiviteler</CardTitle>
          <CardDescription>
            Sistemdeki son güncellemeler ve işlemler
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!stats?.recentActivity || stats.recentActivity.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              Henüz aktivite bulunmuyor
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tip</TableHead>
                  <TableHead>Açıklama</TableHead>
                  <TableHead>Durum</TableHead>
                  <TableHead>Zaman</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {stats.recentActivity.map((activity) => (
                  <TableRow key={activity.id} data-testid={`activity-${activity.id}`}>
                    <TableCell className="font-medium">{activity.type}</TableCell>
                    <TableCell>{activity.description}</TableCell>
                    <TableCell>
                      <StatusBadge status={activity.status} />
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {new Date(activity.timestamp).toLocaleDateString('tr-TR', {
                        day: '2-digit',
                        month: 'short',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
