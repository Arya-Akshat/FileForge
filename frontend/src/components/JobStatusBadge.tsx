import { Badge } from "@/components/ui/badge";
import { Loader2, CheckCircle2, XCircle, Clock } from "lucide-react";

interface JobStatusBadgeProps {
  status: string;
}

export const JobStatusBadge = ({ status }: JobStatusBadgeProps) => {
  const getStatusConfig = () => {
    const normalizedStatus = status.toUpperCase();
    switch (normalizedStatus) {
      case "QUEUED":
        return {
          icon: Clock,
          label: "Queued",
          variant: "outline" as const,
        };
      case "RUNNING":
        return {
          icon: Loader2,
          label: "Running",
          variant: "secondary" as const,
          animate: true,
        };
      case "COMPLETED":
      case "SUCCESS":
        return {
          icon: CheckCircle2,
          label: "Completed",
          variant: "default" as const,
        };
      case "FAILED":
      case "ERROR":
        return {
          icon: XCircle,
          label: "Failed",
          variant: "destructive" as const,
        };
      default:
        return {
          icon: Clock,
          label: status,
          variant: "outline" as const,
        };
    }
  };

  const config = getStatusConfig();
  const Icon = config.icon;

  return (
    <Badge variant={config.variant} className="gap-1.5">
      <Icon className={`w-3.5 h-3.5 ${config.animate ? "animate-spin" : ""}`} />
      {config.label}
    </Badge>
  );
};
