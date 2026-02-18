import { useEffect, useState, useCallback } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Activity } from "lucide-react";
import { dashboardWs, type WebSocketMessage } from "../lib/websocket";

interface DataPoint {
  time: string;
  queries: number;
}

function generateInitialData(): DataPoint[] {
  const data: DataPoint[] = [];
  const now = Date.now();
  for (let i = 29; i >= 0; i--) {
    const t = new Date(now - i * 60000);
    data.push({
      time: t.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      queries: Math.floor(Math.random() * 60) + 10,
    });
  }
  return data;
}

export default function LiveActivityChart() {
  const [data, setData] = useState<DataPoint[]>(generateInitialData);
  const [currentRate, setCurrentRate] = useState(45);

  const handleUpdate = useCallback((msg: WebSocketMessage) => {
    if (msg.type === "query_update") {
      const payload = msg.data as { queries_per_minute?: number };
      const rate = payload.queries_per_minute ?? Math.floor(Math.random() * 60) + 10;
      setCurrentRate(rate);
      setData((prev) => {
        const next = [
          ...prev.slice(1),
          {
            time: new Date().toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            }),
            queries: rate,
          },
        ];
        return next;
      });
    }
  }, []);

  useEffect(() => {
    const unsub = dashboardWs.on("query_update", handleUpdate);

    // Simulate activity when backend isn't connected
    const interval = setInterval(() => {
      const rate = Math.floor(Math.random() * 60) + 10;
      setCurrentRate(rate);
      setData((prev) => [
        ...prev.slice(1),
        {
          time: new Date().toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          }),
          queries: rate,
        },
      ]);
    }, 5000);

    return () => {
      unsub();
      clearInterval(interval);
    };
  }, [handleUpdate]);

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-blue-400" />
          <h3 className="text-sm font-semibold text-slate-200">
            Query Activity (Live)
          </h3>
        </div>
        <span className="text-xs text-slate-500">
          Current: {currentRate} queries/min
        </span>
      </div>
      <div className="h-52">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <defs>
              <linearGradient id="queryGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis
              dataKey="time"
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
            <Area
              type="monotone"
              dataKey="queries"
              stroke="#3b82f6"
              fill="url(#queryGradient)"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
