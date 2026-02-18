import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { Timer } from "lucide-react";

interface ResponseTimeChartProps {
  data: { range: string; count: number; percent: number }[];
  summary?: {
    avg_response: number;
    median_response: number;
    p95_response: number;
  };
}

const COLORS = ["#10b981", "#22c55e", "#3b82f6", "#f59e0b", "#ef4444"];

export default function ResponseTimeChart({
  data,
  summary,
}: ResponseTimeChartProps) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
      <div className="mb-4 flex items-center gap-2">
        <Timer className="h-5 w-5 text-blue-400" />
        <h3 className="text-sm font-semibold text-slate-200">
          Response Time Distribution
        </h3>
      </div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis
              dataKey="range"
              stroke="#475569"
              fontSize={11}
              tickLine={false}
            />
            <YAxis
              stroke="#475569"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#1e293b",
                border: "1px solid #334155",
                borderRadius: "8px",
                color: "#e2e8f0",
                fontSize: "12px",
              }}
              formatter={(value: number) => [`${value}%`, "Percent"]}
            />
            <Bar dataKey="percent" radius={[4, 4, 0, 0]} barSize={40}>
              {data.map((_, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={COLORS[index % COLORS.length]}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      {summary && (
        <div className="mt-4 flex flex-wrap gap-6 text-xs text-slate-500">
          <span>Avg: {summary.avg_response}s</span>
          <span>Median: {summary.median_response}s</span>
          <span>P95: {summary.p95_response}s</span>
        </div>
      )}
    </div>
  );
}
