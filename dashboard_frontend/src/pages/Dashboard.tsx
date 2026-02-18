import { useEffect, useState } from "react";
import { Search, Timer, FileText } from "lucide-react";
import StatCard from "../components/StatCard";
import LiveActivityChart from "../components/LiveActivityChart";
import RecentQueriesList from "../components/RecentQueriesList";
import ActiveJobsList from "../components/ActiveJobsList";
import SystemHealth from "../components/SystemHealth";
import { fetchQueryStats, type QueryStats } from "../lib/api";

const FALLBACK_STATS: QueryStats = {
  total_queries: 12456,
  avg_response_time: 1.2,
  top_queries: [
    { query: "flight logs", count: 234 },
    { query: "palm beach", count: 189 },
    { query: "witness names", count: 156 },
    { query: "financial records", count: 134 },
    { query: "little st james", count: 112 },
  ],
  query_trend: [],
  total_documents: 1234,
  queries_change_percent: 23,
  response_time_change: -0.3,
  documents_added_today: 56,
};

export default function Dashboard() {
  const [stats, setStats] = useState<QueryStats>(FALLBACK_STATS);

  useEffect(() => {
    fetchQueryStats("24h")
      .then(setStats)
      .catch(() => {});
  }, []);

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-slate-100">Dashboard</h2>

      {/* Stat cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          title="Total Queries"
          value={stats.total_queries}
          change={`${stats.queries_change_percent >= 0 ? "+" : ""}${stats.queries_change_percent}% from last week`}
          changeType={
            stats.queries_change_percent >= 0 ? "positive" : "negative"
          }
          icon={Search}
          iconColor="text-blue-400"
        />
        <StatCard
          title="Avg Response Time"
          value={`${stats.avg_response_time}s`}
          change={`${stats.response_time_change >= 0 ? "+" : ""}${stats.response_time_change}s vs last week`}
          changeType={
            stats.response_time_change <= 0 ? "positive" : "negative"
          }
          icon={Timer}
          iconColor="text-emerald-400"
        />
        <StatCard
          title="Indexed Documents"
          value={stats.total_documents}
          change={`+${stats.documents_added_today} added today`}
          changeType="positive"
          icon={FileText}
          iconColor="text-violet-400"
        />
      </div>

      {/* Charts row */}
      <div className="grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <LiveActivityChart />
        </div>
        <div className="lg:col-span-2">
          <RecentQueriesList />
        </div>
      </div>

      {/* Active jobs */}
      <ActiveJobsList />

      {/* Bottom row */}
      <div className="grid gap-6 lg:grid-cols-2">
        <SystemHealth />

        {/* Top queries */}
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h3 className="mb-4 text-sm font-semibold text-slate-200">
            Top Queries (Last 24h)
          </h3>
          <div className="space-y-3">
            {stats.top_queries.map((q, i) => (
              <div
                key={q.query}
                className="flex items-center justify-between text-sm"
              >
                <div className="flex items-center gap-3">
                  <span className="w-5 text-right text-xs text-slate-600">
                    {i + 1}.
                  </span>
                  <span className="text-slate-300">{q.query}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-1.5 w-24 overflow-hidden rounded-full bg-slate-800">
                    <div
                      className="h-full rounded-full bg-blue-500"
                      style={{
                        width: `${(q.count / (stats.top_queries[0]?.count || 1)) * 100}%`,
                      }}
                    />
                  </div>
                  <span className="w-8 text-right text-xs text-slate-500">
                    {q.count}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
