import { type LucideIcon, TrendingUp, TrendingDown } from "lucide-react";
import { cn, formatNumber } from "../lib/utils";

interface StatCardProps {
  title: string;
  value: number | string;
  change?: string;
  changeType?: "positive" | "negative" | "neutral";
  icon: LucideIcon;
  iconColor?: string;
}

export default function StatCard({
  title,
  value,
  change,
  changeType = "neutral",
  icon: Icon,
  iconColor = "text-blue-400",
}: StatCardProps) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-slate-400">{title}</p>
        <Icon className={cn("h-5 w-5", iconColor)} />
      </div>
      <p className="mt-3 text-3xl font-bold text-slate-100">
        {typeof value === "number" ? formatNumber(value) : value}
      </p>
      {change && (
        <div className="mt-2 flex items-center gap-1">
          {changeType === "positive" && (
            <TrendingUp className="h-3.5 w-3.5 text-emerald-400" />
          )}
          {changeType === "negative" && (
            <TrendingDown className="h-3.5 w-3.5 text-red-400" />
          )}
          <span
            className={cn(
              "text-xs font-medium",
              changeType === "positive" && "text-emerald-400",
              changeType === "negative" && "text-red-400",
              changeType === "neutral" && "text-slate-500",
            )}
          >
            {change}
          </span>
        </div>
      )}
    </div>
  );
}
