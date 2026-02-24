import { useState } from "react";
import { Search as SearchIcon, FileText, Clock, Loader2 } from "lucide-react";
import api from "../lib/api";

interface SearchResult {
  id: string;
  text: string;
  source: string;
  chunk_index: number;
  similarity: number;
}

interface SearchResponse {
  query: string;
  results: SearchResult[];
  result_count: number;
  response_time_ms: number;
}

export default function Search() {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get("/search", {
        params: { q: query.trim(), top_k: topK },
      });
      setResponse(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Search failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-100">Search Documents</h2>
        <p className="mt-1 text-sm text-slate-400">
          Query the indexed Epstein documents using semantic search
        </p>
      </div>

      {/* Search form */}
      <form onSubmit={handleSearch} className="flex gap-3">
        <div className="relative flex-1">
          <SearchIcon className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. flight logs, names mentioned, court documents..."
            className="w-full rounded-lg border border-slate-700 bg-slate-900 py-3 pl-10 pr-4 text-sm text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <select
          value={topK}
          onChange={(e) => setTopK(Number(e.target.value))}
          className="rounded-lg border border-slate-700 bg-slate-900 px-3 text-sm text-slate-300 focus:border-blue-500 focus:outline-none"
        >
          {[3, 5, 10, 15, 20].map((n) => (
            <option key={n} value={n}>
              Top {n}
            </option>
          ))}
        </select>
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <SearchIcon className="h-4 w-4" />
          )}
          Search
        </button>
      </form>

      {error && (
        <div className="rounded-lg border border-red-800 bg-red-900/20 p-4 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Results */}
      {response && (
        <div className="space-y-4">
          <div className="flex items-center gap-4 text-sm text-slate-400">
            <span>
              {response.result_count} result{response.result_count !== 1 && "s"} for "{response.query}"
            </span>
            <span className="flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" />
              {response.response_time_ms}ms
            </span>
          </div>

          {response.results.length === 0 && (
            <div className="rounded-lg border border-slate-800 bg-slate-900 p-8 text-center text-sm text-slate-500">
              No matching documents found. Try a different query.
            </div>
          )}

          {response.results.map((result, idx) => (
            <div
              key={result.id}
              className="rounded-lg border border-slate-800 bg-slate-900 p-5"
            >
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-blue-400" />
                  <span className="text-sm font-medium text-slate-200">
                    {result.source}
                  </span>
                  <span className="text-xs text-slate-500">
                    chunk #{result.chunk_index}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500">#{idx + 1}</span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      result.similarity > 0.7
                        ? "bg-emerald-400/10 text-emerald-400"
                        : result.similarity > 0.4
                          ? "bg-amber-400/10 text-amber-400"
                          : "bg-slate-400/10 text-slate-400"
                    }`}
                  >
                    {(result.similarity * 100).toFixed(1)}% match
                  </span>
                </div>
              </div>
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-300">
                {result.text}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
