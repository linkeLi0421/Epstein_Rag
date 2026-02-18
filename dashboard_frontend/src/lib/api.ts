import axios from "axios";

const api = axios.create({
  baseURL: "/api/dashboard",
  headers: {
    "Content-Type": "application/json",
  },
});

// ---- Types ----

export interface QueryLog {
  id: string;
  query_text: string;
  response_text: string;
  sources: { source: string; page: number; similarity: number }[];
  response_time_ms: number;
  timestamp: string;
  client_type: string;
  session_id: string;
}

export interface QueryStats {
  total_queries: number;
  avg_response_time: number;
  top_queries: { query: string; count: number }[];
  query_trend: { timestamp: string; count: number }[];
  total_documents: number;
  queries_change_percent: number;
  response_time_change: number;
  documents_added_today: number;
}

export interface IndexingJob {
  id: string;
  source_type: string;
  source_url: string;
  status: "pending" | "processing" | "completed" | "failed" | "cancelled";
  total_files: number;
  processed_files: number;
  failed_files: number;
  current_file: string;
  progress_percent: number;
  started_at: string;
  completed_at: string | null;
  error_message: string | null;
  metadata: Record<string, unknown>;
}

export interface HealthComponent {
  name: string;
  status: string;
  details: string | null;
}

export interface SystemHealth {
  status: string;
  uptime_seconds?: number;
  components: HealthComponent[];
  metrics?: {
    cpu_usage: number;
    memory_usage: number;
    disk_usage: number;
  };
}

export interface AnalyticsData {
  query_trend: { timestamp: string; count: number }[];
  popular_queries: { query: string; count: number }[];
  response_time_distribution: { range: string; count: number; percent: number }[];
  document_types: { type: string; count: number; percent: number }[];
  summary: {
    total_queries: number;
    peak_queries: number;
    peak_time: string;
    avg_per_hour: number;
    avg_response: number;
    median_response: number;
    p95_response: number;
  };
}

// ---- API calls ----

// Backend returns { queries: [...], total, page, page_size }
export async function fetchRecentQueries(limit = 50): Promise<QueryLog[]> {
  const { data } = await api.get("/queries", { params: { limit } });
  return Array.isArray(data) ? data : data.queries ?? [];
}

// Backend returns { total_queries, avg_response_time_ms, query_trend, popular_queries, ... }
export async function fetchQueryStats(timeRange = "24h"): Promise<QueryStats> {
  const { data } = await api.get("/queries/stats", {
    params: { time_range: timeRange },
  });
  // Normalize backend field names to what the frontend expects
  return {
    total_queries: data.total_queries ?? 0,
    avg_response_time: (data.avg_response_time_ms ?? 0) / 1000,
    top_queries: (data.popular_queries ?? []).map((q: { query_text?: string; query?: string; count: number }) => ({
      query: q.query_text ?? q.query ?? "",
      count: q.count ?? 0,
    })),
    query_trend: data.query_trend ?? [],
    total_documents: data.total_documents ?? 0,
    queries_change_percent: data.queries_change_percent ?? 0,
    response_time_change: data.response_time_change ?? 0,
    documents_added_today: data.documents_added_today ?? 0,
  };
}

export async function fetchQueryById(id: string): Promise<QueryLog> {
  const { data } = await api.get(`/queries/${id}`);
  return data;
}

// Backend returns { jobs: [...], total }
export async function fetchJobs(): Promise<IndexingJob[]> {
  const { data } = await api.get("/jobs");
  return Array.isArray(data) ? data : data.jobs ?? [];
}

export async function fetchJobById(id: string): Promise<IndexingJob> {
  const { data } = await api.get(`/jobs/${id}`);
  return data;
}

export async function fetchJobProgress(
  id: string,
): Promise<IndexingJob> {
  const { data } = await api.get(`/jobs/${id}/progress`);
  return data;
}

export async function cancelJob(id: string): Promise<void> {
  await api.post(`/jobs/${id}/cancel`);
}

export async function fetchHealth(): Promise<SystemHealth> {
  const { data } = await api.get("/health");
  return data;
}

// Backend returns { query_trend, popular_queries, response_time_distribution, ... }
export async function fetchAnalytics(
  timeRange = "24h",
): Promise<AnalyticsData> {
  const { data } = await api.get("/analytics", {
    params: { time_range: timeRange },
  });
  // Normalize to expected shape with safe defaults
  return {
    query_trend: data.query_trend ?? [],
    popular_queries: (data.popular_queries ?? []).map((q: { query_text?: string; query?: string; count: number }) => ({
      query: q.query_text ?? q.query ?? "",
      count: q.count ?? 0,
    })),
    response_time_distribution: (data.response_time_distribution ?? []).map((r: { bucket?: string; range?: string; count: number; percentage?: number; percent?: number }) => ({
      range: r.bucket ?? r.range ?? "",
      count: r.count ?? 0,
      percent: r.percentage ?? r.percent ?? 0,
    })),
    document_types: data.document_types ?? [],
    summary: data.summary ?? {
      total_queries: data.total_queries ?? 0,
      peak_queries: 0,
      peak_time: "",
      avg_per_hour: 0,
      avg_response: 0,
      median_response: 0,
      p95_response: 0,
    },
  };
}

export default api;
