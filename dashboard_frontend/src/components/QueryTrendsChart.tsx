import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { TrendingUp } from "lucide-react";

interface QueryTrendsChartProps {
  data: { timestamp: string; count: number }[];
  summary?: {
    total_queries: number;
    peak_queries: number;
    peak_time: string;
    avg_per_hour: number;
  };
}

export default function QueryTrendsChart({
  data,
  summary,
}: QueryTrendsChartProps) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
      <div className="mb-4 flex items-center gap-2">
        <TrendingUp className="h-5 w-5 text-blue-400" />
        <h3 className="text-sm font-semibold text-slate-200">
          Query Volume Over Time
        </h3>
      </div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis
              dataKey="timestamp"
              stroke="#475569"
              fontSize={11}
              tickLine={false}
            />
            <YAxis
              stroke="#475569"
              fontSize={11}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#1e293b",
                border: "1px solid #334155",
                borderRadius: "8px",
                color: "#e2e8f0",
                fontSize: "12px",
              }}
            />
            <Line
              type="monotone"
              dataKey="count"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: "#3b82f6" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      {summary && (
        <div className="mt-4 flex flex-wrap gap-6 text-xs text-slate-500">
          <span>Total: {summary.total_queries.toLocaleString()} queries</span>
          <span>
            Peak: {summary.peak_queries} queries at {summary.peak_time}
          </span>
          <span>Avg: {summary.avg_per_hour} queries/hour</span>
        </div>
      )}
    </div>
  );
}
