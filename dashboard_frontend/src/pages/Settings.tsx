import { useState, useEffect } from "react";
import {
  Settings as SettingsIcon,
  Monitor,
  Bell,
  Database,
  Key,
  BarChart3,
  Save,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";
import { fetchHealth, type SystemHealth, type HealthComponent } from "../lib/api";

const FALLBACK_HEALTH: SystemHealth = {
  status: "healthy",
  components: [
    { name: "MCP Server", status: "running", details: null },
    { name: "Vector Database", status: "connected", details: null },
    { name: "LLM Service", status: "available", details: null },
  ],
};

export default function Settings() {
  const [health, setHealth] = useState<SystemHealth>(FALLBACK_HEALTH);
  const [theme, setTheme] = useState("dark");
  const [timeFormat, setTimeFormat] = useState("24h");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [notifications, setNotifications] = useState(true);
  const [jobNotifications, setJobNotifications] = useState(true);
  const [errorAlerts, setErrorAlerts] = useState(true);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch(() => {});
  }, []);

  function handleSave() {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  // Normalize components to array format
  const components: HealthComponent[] = Array.isArray(health.components)
    ? health.components
    : Object.entries(health.components).map(([name, status]) => ({
        name,
        status: typeof status === "string" ? status : "unknown",
        details: null,
      }));

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-slate-100">Settings</h2>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* MCP Server Configuration */}
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <div className="mb-4 flex items-center gap-2">
            <SettingsIcon className="h-5 w-5 text-blue-400" />
            <h3 className="text-sm font-semibold text-slate-200">
              MCP Server Configuration
            </h3>
          </div>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-400">LLM Provider</span>
              <span className="text-sm text-slate-200">Ollama</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-400">Model</span>
              <span className="text-sm text-slate-200">llama3.2:8b</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-400">Embedding</span>
              <span className="text-sm text-slate-200">all-MiniLM-L6-v2</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-400">Vector DB</span>
              <span className="text-sm text-slate-200">ChromaDB</span>
            </div>
          </div>
        </div>

        {/* Dashboard Preferences */}
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <div className="mb-4 flex items-center gap-2">
            <Monitor className="h-5 w-5 text-blue-400" />
            <h3 className="text-sm font-semibold text-slate-200">
              Dashboard Preferences
            </h3>
          </div>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <label className="text-sm text-slate-400">Theme</label>
              <select
                value={theme}
                onChange={(e) => setTheme(e.target.value)}
                className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
              >
                <option value="dark">Dark</option>
                <option value="light">Light</option>
              </select>
            </div>
            <div className="flex items-center justify-between">
              <label className="text-sm text-slate-400">Time Format</label>
              <select
                value={timeFormat}
                onChange={(e) => setTimeFormat(e.target.value)}
                className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
              >
                <option value="24h">24-hour</option>
                <option value="12h">12-hour</option>
              </select>
            </div>
            <div className="flex items-center justify-between">
              <label className="text-sm text-slate-400">Auto-refresh</label>
              <button
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`relative h-6 w-11 rounded-full transition-colors ${autoRefresh ? "bg-blue-600" : "bg-slate-700"}`}
              >
                <span
                  className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${autoRefresh ? "left-[22px]" : "left-0.5"}`}
                />
              </button>
            </div>
            <div className="flex items-center justify-between">
              <label className="text-sm text-slate-400">Notifications</label>
              <button
                onClick={() => setNotifications(!notifications)}
                className={`relative h-6 w-11 rounded-full transition-colors ${notifications ? "bg-blue-600" : "bg-slate-700"}`}
              >
                <span
                  className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${notifications ? "left-[22px]" : "left-0.5"}`}
                />
              </button>
            </div>
          </div>
          <button
            onClick={handleSave}
            className="mt-4 flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            {saved ? (
              <>
                <CheckCircle2 className="h-4 w-4" />
                Saved
              </>
            ) : (
              <>
                <Save className="h-4 w-4" />
                Save Preferences
              </>
            )}
          </button>
        </div>

        {/* Data Management */}
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <div className="mb-4 flex items-center gap-2">
            <Database className="h-5 w-5 text-blue-400" />
            <h3 className="text-sm font-semibold text-slate-200">
              Data Management
            </h3>
          </div>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-400">Vector Store Size</span>
              <span className="text-sm text-slate-200">2.3 GB</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-400">Query Log Size</span>
              <span className="text-sm text-slate-200">145 MB</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-400">Indexed Documents</span>
              <span className="text-sm text-slate-200">1,234</span>
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <button className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-400 hover:bg-slate-800 hover:text-slate-200">
              Export Data
            </button>
            <button className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-400 hover:bg-slate-800 hover:text-slate-200">
              Clear Logs
            </button>
            <button className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-400 hover:bg-slate-800 hover:text-slate-200">
              Backup
            </button>
          </div>
          {health.metrics && health.metrics.disk_usage >= 80 && (
            <div className="mt-4 flex items-center gap-2 rounded-lg border border-amber-900/50 bg-amber-950/30 p-3 text-xs text-amber-400">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              Disk usage at {health.metrics.disk_usage}%
            </div>
          )}
        </div>

        {/* Notification Settings */}
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <div className="mb-4 flex items-center gap-2">
            <Bell className="h-5 w-5 text-blue-400" />
            <h3 className="text-sm font-semibold text-slate-200">
              Notification Settings
            </h3>
          </div>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <label className="text-sm text-slate-400">
                Job completion notifications
              </label>
              <button
                onClick={() => setJobNotifications(!jobNotifications)}
                className={`relative h-6 w-11 rounded-full transition-colors ${jobNotifications ? "bg-blue-600" : "bg-slate-700"}`}
              >
                <span
                  className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${jobNotifications ? "left-[22px]" : "left-0.5"}`}
                />
              </button>
            </div>
            <div className="flex items-center justify-between">
              <label className="text-sm text-slate-400">Error alerts</label>
              <button
                onClick={() => setErrorAlerts(!errorAlerts)}
                className={`relative h-6 w-11 rounded-full transition-colors ${errorAlerts ? "bg-blue-600" : "bg-slate-700"}`}
              >
                <span
                  className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${errorAlerts ? "left-[22px]" : "left-0.5"}`}
                />
              </button>
            </div>
          </div>
        </div>

        {/* Service Status */}
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <div className="mb-4 flex items-center gap-2">
            <Key className="h-5 w-5 text-blue-400" />
            <h3 className="text-sm font-semibold text-slate-200">
              Service Status
            </h3>
          </div>
          <div className="space-y-3">
            {components.map((comp) => (
              <div
                key={comp.name}
                className="flex items-center justify-between text-sm"
              >
                <span className="text-slate-400">{comp.name}</span>
                <span className="flex items-center gap-1.5 text-emerald-400">
                  <CheckCircle2 className="h-4 w-4" />
                  <span className="capitalize">{comp.status}</span>
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Usage Statistics */}
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <div className="mb-4 flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-blue-400" />
            <h3 className="text-sm font-semibold text-slate-200">
              Usage Statistics
            </h3>
          </div>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-400">Total Queries</span>
              <span className="text-sm font-semibold text-slate-200">
                12,456
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-400">Total Documents</span>
              <span className="text-sm font-semibold text-slate-200">
                1,234
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-400">Total Jobs</span>
              <span className="text-sm font-semibold text-slate-200">42</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-400">Uptime</span>
              <span className="text-sm font-semibold text-slate-200">
                {health.uptime_seconds
                  ? `${Math.floor(health.uptime_seconds / 3600)}h ${Math.floor((health.uptime_seconds % 3600) / 60)}m`
                  : "N/A"}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
