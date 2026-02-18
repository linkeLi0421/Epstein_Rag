import { useEffect, useState } from "react";
import { Search, Filter, Download, CheckCircle2, Clock, Cpu } from "lucide-react";
import { fetchRecentQueries, type QueryLog } from "../lib/api";
import { cn, formatRelativeTime, formatDuration, truncate } from "../lib/utils";
import QueryDetailModal from "../components/QueryDetailModal";

const FALLBACK_QUERIES: QueryLog[] = [
  {
    id: "q1",
    query_text: "flight logs",
    response_text:
      'The flight logs document extensive travel on Epstein\'s private aircraft, including trips to various destinations. The logs, commonly known as the "Lolita Express" records, detail passenger manifests and flight routes.',
    sources: [
      { source: "flight_manifest.pdf", page: 12, similarity: 0.92 },
      { source: "travel_records.pdf", page: 45, similarity: 0.87 },
    ],
    response_time_ms: 1100,
    timestamp: new Date(Date.now() - 2000).toISOString(),
    client_type: "claude",
    session_id: "s1",
  },
  {
    id: "q2",
    query_text: "palm beach mansion",
    response_text:
      "The Palm Beach property was one of Epstein's primary residences where numerous alleged incidents occurred according to court documents.",
    sources: [
      { source: "property_records.pdf", page: 3, similarity: 0.89 },
      { source: "police_report.pdf", page: 8, similarity: 0.84 },
    ],
    response_time_ms: 900,
    timestamp: new Date(Date.now() - 5000).toISOString(),
    client_type: "dashboard",
    session_id: "s2",
  },
  {
    id: "q3",
    query_text: "witness testimony about island visits",
    response_text:
      "Multiple witnesses provided testimony regarding visits to Little St. James island, detailing events and individuals present during various time periods.",
    sources: [
      { source: "witness_jane_doe.pdf", page: 1, similarity: 0.91 },
      { source: "court_transcript.pdf", page: 23, similarity: 0.85 },
    ],
    response_time_ms: 2300,
    timestamp: new Date(Date.now() - 60000).toISOString(),
    client_type: "cursor",
    session_id: "s3",
  },
  {
    id: "q4",
    query_text: "financial records and wire transfers",
    response_text:
      "Financial records indicate a complex web of wire transfers between multiple accounts across several jurisdictions.",
    sources: [
      { source: "bank_statements.pdf", page: 8, similarity: 0.88 },
    ],
    response_time_ms: 1800,
    timestamp: new Date(Date.now() - 300000).toISOString(),
    client_type: "claude",
    session_id: "s4",
  },
  {
    id: "q5",
    query_text: "black book contacts",
    response_text:
      "The address book, commonly referred to as the 'black book', contained entries for numerous high-profile individuals.",
    sources: [
      { source: "address_book.pdf", page: 1, similarity: 0.93 },
    ],
    response_time_ms: 750,
    timestamp: new Date(Date.now() - 600000).toISOString(),
    client_type: "api",
    session_id: "s5",
  },
];

const CLIENT_OPTIONS = ["All", "claude", "cursor", "dashboard", "api"];

export default function Queries() {
  const [queries, setQueries] = useState<QueryLog[]>(FALLBACK_QUERIES);
  const [searchTerm, setSearchTerm] = useState("");
  const [clientFilter, setClientFilter] = useState("All");
  const [selectedQuery, setSelectedQuery] = useState<QueryLog | null>(null);

  useEffect(() => {
    fetchRecentQueries(100)
      .then(setQueries)
      .catch(() => {});
  }, []);

  const filtered = queries.filter((q) => {
    if (searchTerm && !q.query_text.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false;
    }
    if (clientFilter !== "All" && q.client_type !== clientFilter) {
      return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-slate-100">Queries</h2>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search queries..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-900 py-2.5 pl-10 pr-4 text-sm text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-500" />
          <select
            value={clientFilter}
            onChange={(e) => setClientFilter(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-slate-300 focus:border-blue-500 focus:outline-none"
          >
            {CLIENT_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt === "All" ? "All Clients" : opt}
              </option>
            ))}
          </select>
        </div>
        <button className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-slate-400 hover:bg-slate-800 hover:text-slate-200">
          <Download className="h-4 w-4" />
          Export CSV
        </button>
      </div>

      {/* Query History */}
      <div className="rounded-xl border border-slate-800 bg-slate-900">
        <div className="border-b border-slate-800 px-6 py-4">
          <h3 className="text-sm font-medium text-slate-400">
            Query History ({filtered.length} total)
          </h3>
        </div>
        <div className="divide-y divide-slate-800/50">
          {filtered.map((q) => (
            <div
              key={q.id}
              onClick={() => setSelectedQuery(q)}
              className="cursor-pointer px-6 py-4 transition-colors hover:bg-slate-800/30"
            >
              <div className="mb-2 flex items-start justify-between gap-4">
                <div className="flex items-center gap-2">
                  <Search className="h-4 w-4 shrink-0 text-blue-400" />
                  <h4 className="text-sm font-medium text-slate-200">
                    {q.query_text}
                  </h4>
                </div>
                <span className="flex shrink-0 items-center gap-1 text-xs text-emerald-400">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Success
                </span>
              </div>
              <p className="mb-2 pl-6 text-xs text-slate-500">
                {truncate(q.response_text, 150)}
              </p>
              <div className="flex flex-wrap items-center gap-3 pl-6 text-xs text-slate-600">
                {q.sources.length > 0 && (
                  <span>
                    Sources: {q.sources.map((s) => `${s.source} (p.${s.page})`).join(", ")}
                  </span>
                )}
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-3 pl-6 text-xs text-slate-500">
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {formatDuration(q.response_time_ms)}
                </span>
                <span className="text-slate-700">|</span>
                <span className="flex items-center gap-1">
                  <Cpu className="h-3 w-3" />
                  <span className="capitalize">{q.client_type}</span>
                </span>
                <span className="text-slate-700">|</span>
                <span>{formatRelativeTime(q.timestamp)}</span>
              </div>
              <div className="mt-2 flex gap-2 pl-6">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedQuery(q);
                  }}
                  className="text-xs text-blue-400 hover:text-blue-300"
                >
                  View Full Response
                </button>
              </div>
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="px-6 py-12 text-center text-sm text-slate-500">
              No queries found matching your search.
            </div>
          )}
        </div>
      </div>

      {/* Detail modal */}
      {selectedQuery && (
        <QueryDetailModal
          query={selectedQuery}
          onClose={() => setSelectedQuery(null)}
        />
      )}
    </div>
  );
}
