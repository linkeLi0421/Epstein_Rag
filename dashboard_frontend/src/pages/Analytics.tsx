import { useEffect, useState } from "react";
import { cn } from "../lib/utils";
import { fetchAnalytics, type AnalyticsData } from "../lib/api";
import QueryTrendsChart from "../components/QueryTrendsChart";
import PopularQueries from "../components/PopularQueries";
import ResponseTimeChart from "../components/ResponseTimeChart";
import { FileText } from "lucide-react";

const TIME_RANGES = [
  { label: "Last 24 hours", value: "24h" },
  { label: "Last 7 days", value: "7d" },
  { label: "Last 30 days", value: "30d" },
];

const FALLBACK_DATA: AnalyticsData = {
  query_trend: Array.from({ length: 24 }, (_, i) => ({
    timestamp: `${String(i).padStart(2, "0")}:00`,
    count: Math.floor(Math.random() * 80) + 10,
  })),
  popular_queries: [
    { query: "flight logs", count: 234 },
    { query: "palm beach", count: 189 },
    { query: "witness testimony", count: 156 },
    { query: "financial records", count: 134 },
    { query: "little st james", count: 112 },
    { query: "black book", count: 98 },
    { query: "court documents", count: 87 },
    { query: "plea deal", count: 76 },
    { query: "surveillance footage", count: 65 },
    { query: "travel records", count: 54 },
  ],
  response_time_distribution: [
    { range: "<0.5s", count: 560, percent: 45 },
    { range: "0.5-1s", count: 398, percent: 32 },
    { range: "1-2s", count: 186, percent: 15 },
    { range: "2-5s", count: 75, percent: 6 },
    { range: ">5s", count: 25, percent: 2 },
  ],
  document_types: [
    { type: "PDF", count: 802, percent: 65 },
    { type: "TXT", count: 284, percent: 23 },
    { type: "MD", count: 99, percent: 8 },
    { type: "DOCX", count: 49, percent: 4 },
  ],
  summary: {
    total_queries: 1234,
    peak_queries: 89,
    peak_time: "14:32",
    avg_per_hour: 51,
    avg_response: 1.2,
    median_response: 0.9,
    p95_response: 3.4,
  },
};

export default function Analytics() {
  const [timeRange, setTimeRange] = useState("24h");
  const [data, setData] = useState<AnalyticsData>(FALLBACK_DATA);

  useEffect(() => {
    fetchAnalytics(timeRange)
      .then(setData)
      .catch(() => {});
  }, [timeRange]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-xl font-bold text-slate-100">Analytics</h2>
        <div className="flex gap-2">
          {TIME_RANGES.map((range) => (
            <button
              key={range.value}
              onClick={() => setTimeRange(range.value)}
              className={cn(
                "rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
                timeRange === range.value
                  ? "bg-blue-600 text-white"
                  : "border border-slate-700 text-slate-400 hover:bg-slate-800 hover:text-slate-200",
              )}
            >
              {range.label}
            </button>
          ))}
        </div>
      </div>

      {/* Query Trends */}
      <QueryTrendsChart data={data.query_trend} summary={data.summary} />

      {/* Popular queries + response time */}
      <div className="grid gap-6 lg:grid-cols-2">
        <PopularQueries data={data.popular_queries} />
        <ResponseTimeChart
          data={data.response_time_distribution}
          summary={data.summary}
        />
      </div>

      {/* Document types */}
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <div className="mb-4 flex items-center gap-2">
            <FileText className="h-5 w-5 text-violet-400" />
            <h3 className="text-sm font-semibold text-slate-200">
              Documents by Type
            </h3>
          </div>
          <div className="space-y-4">
            {data.document_types.map((dt) => (
              <div key={dt.type}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span className="text-slate-300">{dt.type}</span>
                  <span className="text-xs text-slate-500">
                    {dt.count} ({dt.percent}%)
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-slate-800">
                  <div
                    className="h-full rounded-full bg-violet-500"
                    style={{ width: `${dt.percent}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
          <p className="mt-4 text-xs text-slate-500">
            Total: {data.document_types.reduce((a, b) => a + b.count, 0).toLocaleString()} documents
          </p>
        </div>

        {/* Summary stats */}
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h3 className="mb-4 text-sm font-semibold text-slate-200">
            Summary Statistics
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-lg bg-slate-950 p-4">
              <p className="text-xs text-slate-500">Total Queries</p>
              <p className="mt-1 text-2xl font-bold text-slate-100">
                {data.summary.total_queries.toLocaleString()}
              </p>
            </div>
            <div className="rounded-lg bg-slate-950 p-4">
              <p className="text-xs text-slate-500">Peak Queries</p>
              <p className="mt-1 text-2xl font-bold text-slate-100">
                {data.summary.peak_queries}
              </p>
              <p className="text-xs text-slate-600">
                at {data.summary.peak_time}
              </p>
            </div>
            <div className="rounded-lg bg-slate-950 p-4">
              <p className="text-xs text-slate-500">Avg Response</p>
              <p className="mt-1 text-2xl font-bold text-slate-100">
                {data.summary.avg_response}s
              </p>
            </div>
            <div className="rounded-lg bg-slate-950 p-4">
              <p className="text-xs text-slate-500">P95 Response</p>
              <p className="mt-1 text-2xl font-bold text-slate-100">
                {data.summary.p95_response}s
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
