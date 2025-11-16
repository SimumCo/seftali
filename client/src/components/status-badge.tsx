import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  status: string;
  testId?: string;
}

export function StatusBadge({ status, testId }: StatusBadgeProps) {
  const variants: Record<string, { variant: "default" | "secondary" | "destructive", label: string }> = {
    pending: { variant: "secondary", label: "Beklemede" },
    in_progress: { variant: "default", label: "Devam Ediyor" },
    in_transit: { variant: "default", label: "Yolda" },
    completed: { variant: "default", label: "Tamamlandı" },
    delivered: { variant: "default", label: "Teslim Edildi" },
    cancelled: { variant: "destructive", label: "İptal" },
    low: { variant: "secondary", label: "Düşük" },
    medium: { variant: "default", label: "Orta" },
    high: { variant: "default", label: "Yüksek" },
    urgent: { variant: "destructive", label: "Acil" },
  };

  const config = variants[status] || { variant: "secondary" as const, label: status };

  return (
    <Badge 
      variant={config.variant} 
      className={cn(
        status === "completed" && "bg-green-600 hover:bg-green-700 text-white border-green-700",
        status === "delivered" && "bg-green-600 hover:bg-green-700 text-white border-green-700",
        status === "in_progress" && "bg-blue-600 hover:bg-blue-700 text-white border-blue-700",
        status === "in_transit" && "bg-blue-600 hover:bg-blue-700 text-white border-blue-700",
        status === "high" && "bg-amber-600 hover:bg-amber-700 text-white border-amber-700",
        status === "urgent" && "bg-red-600 hover:bg-red-700 text-white border-red-700"
      )}
      data-testid={testId}
    >
      {config.label}
    </Badge>
  );
}
