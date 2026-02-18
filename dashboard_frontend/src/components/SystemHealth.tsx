import { useEffect, useState } from "react";
import { HeartPulse, CheckCircle2, AlertTriangle, XCircle } from "lucide-react";
import { fetchHealth, type SystemHealth as HealthData, type HealthComponent } from "../lib/api";
import { cn } from "../lib/utils";

const FALLBACK_HEALTH: HealthData = {
  status: "healthy",
  components: [
    { name: "MCP Server", status: "running", details: null },
    { name: "Vector Database", status: "connected", details: null },
    { name: "PostgreSQL", status: "connected", details: null },
    { name: "Indexing Engine", status: "idle", details: null },
  ],
};

function getStatusStyle(status: string) {
  const s = status.toLowerCase();
  if (["running", "connected", "available", "ready", "healthy"].includes(s)) {
    return { icon: CheckCircle2, color: "text-emerald-400" };
  }
  if (["warning", "degraded", "idle"].includes(s)) {
    return { icon: AlertTriangle, color: "text-amber-400" };
  }
  return { icon: XCircle, color: "text-red-400" };
}

export default function SystemHealth() {
  const [health, setHealth] = useState<HealthData>(FALLBACK_HEALTH);

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch(() => {});

    const interval = setInterval(() => {
      fetchHealth()
        .then(setHealth)
        .catch(() => {});
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  // Normalize components to array format
  const components: HealthComponent[] = Array.isArray(health.components)
    ? health.components
    : Object.entries(health.components).map(([name, status]) => ({
        name,
        status: typeof status === "string" ? status : "unknown",
        details: null,
      }));

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
      <div className="mb-4 flex items-center gap-2">
        <HeartPulse className="h-5 w-5 text-blue-400" />
        <h3 className="text-sm font-semibold text-slate-200">System Health</h3>
      </div>
      <div className="space-y-3">
        {components.map((comp) => {
          const style = getStatusStyle(comp.status);
          const StatusIcon = style.icon;
          return (
            <div
              key={comp.name}
              className="flex items-center justify-between text-sm"
            >
              <span className="text-slate-400">{comp.name}</span>
              <span className={cn("flex items-center gap-1.5", style.color)}>
                <StatusIcon className="h-4 w-4" />
                <span className="capitalize">{comp.status}</span>
              </span>
            </div>
          );
        })}
      </div>

      {health.metrics && health.metrics.disk_usage >= 80 && (
        <div className="mt-4 flex items-center gap-2 rounded-lg border border-amber-900/50 bg-amber-950/30 p-3 text-xs text-amber-400">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          Disk usage at {health.metrics.disk_usage}%
        </div>
      )}
    </div>
  );
}
