import { useEffect, useState } from "react";
import { Clock, Search } from "lucide-react";
import { Link } from "react-router-dom";
import { fetchRecentQueries, type QueryLog } from "../lib/api";
import { formatRelativeTime } from "../lib/utils";

const FALLBACK_QUERIES: QueryLog[] = [
  {
    id: "1",
    query_text: "flight logs",
    response_text: "The flight logs document extensive travel...",
    sources: [{ source: "flight_manifest.pdf", page: 12, similarity: 0.92 }],
    response_time_ms: 1100,
    timestamp: new Date(Date.now() - 2000).toISOString(),
    client_type: "claude",
    session_id: "s1",
  },
  {
    id: "2",
    query_text: "palm beach mansion",
    response_text: "The Palm Beach property was one of...",
    sources: [{ source: "property_records.pdf", page: 3, similarity: 0.89 }],
    response_time_ms: 900,
    timestamp: new Date(Date.now() - 5000).toISOString(),
    client_type: "dashboard",
    session_id: "s2",
  },
  {
    id: "3",
    query_text: "witness testimony",
    response_text: "Multiple witnesses provided testimony...",
    sources: [{ source: "witness_jane_doe.pdf", page: 1, similarity: 0.87 }],
    response_time_ms: 1300,
    timestamp: new Date(Date.now() - 60000).toISOString(),
    client_type: "cursor",
    session_id: "s3",
  },
  {
    id: "4",
    query_text: "financial records",
    response_text: "Financial records show extensive...",
    sources: [{ source: "bank_statements.pdf", page: 8, similarity: 0.85 }],
    response_time_ms: 2100,
    timestamp: new Date(Date.now() - 180000).toISOString(),
    client_type: "claude",
    session_id: "s4",
  },
];

export default function RecentQueriesList() {
  const [queries, setQueries] = useState<QueryLog[]>(FALLBACK_QUERIES);

  useEffect(() => {
    fetchRecentQueries(5)
      .then(setQueries)
      .catch(() => {});
  }, []);

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock className="h-5 w-5 text-blue-400" />
          <h3 className="text-sm font-semibold text-slate-200">
            Recent Queries
          </h3>
        </div>
        <Link
          to="/queries"
          className="text-xs text-blue-400 hover:text-blue-300"
        >
          View All
        </Link>
      </div>
      <div className="space-y-3">
        {queries.map((q) => (
          <div
            key={q.id}
            className="flex items-start gap-3 rounded-lg border border-slate-800 bg-slate-950/50 p-3"
          >
            <Search className="mt-0.5 h-4 w-4 shrink-0 text-slate-500" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-slate-200">
                {q.query_text}
              </p>
              <div className="mt-1 flex items-center gap-2 text-xs text-slate-500">
                <span>{formatRelativeTime(q.timestamp)}</span>
                <span className="text-slate-700">|</span>
                <span>{(q.response_time_ms / 1000).toFixed(1)}s</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
