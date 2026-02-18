import { useEffect, useState } from "react";
import { Filter, Plus } from "lucide-react";
import { fetchJobs, type IndexingJob } from "../lib/api";
import { cn } from "../lib/utils";
import JobProgressCard from "../components/JobProgressCard";

const STATUS_OPTIONS = ["all", "pending", "processing", "completed", "failed", "cancelled"];

const FALLBACK_JOBS: IndexingJob[] = [
  {
    id: "j1",
    source_type: "github",
    source_url: "https://github.com/yung-megafone/Epstein-Files",
    status: "processing",
    total_files: 1000,
    processed_files: 650,
    failed_files: 45,
    current_file: "flight_logs_volume_2.pdf",
    progress_percent: 65,
    started_at: new Date(Date.now() - 1800000).toISOString(),
    completed_at: null,
    error_message: null,
    metadata: { name: "Epstein-Files Dataset" },
  },
  {
    id: "j2",
    source_type: "upload",
    source_url: "/uploads/batch_2024_01_15",
    status: "completed",
    total_files: 42,
    processed_files: 42,
    failed_files: 0,
    current_file: "",
    progress_percent: 100,
    started_at: new Date(Date.now() - 7200000).toISOString(),
    completed_at: new Date(Date.now() - 3600000).toISOString(),
    error_message: null,
    metadata: { name: "User Uploads (batch_2024_01_15)" },
  },
  {
    id: "j3",
    source_type: "local",
    source_url: "/data/legal_docs",
    status: "failed",
    total_files: 200,
    processed_files: 124,
    failed_files: 76,
    current_file: "",
    progress_percent: 62,
    started_at: new Date(Date.now() - 14400000).toISOString(),
    completed_at: null,
    error_message: "PDF parsing failed for encrypted documents",
    metadata: { name: "Legal Documents Collection" },
  },
];

export default function Jobs() {
  const [jobs, setJobs] = useState<IndexingJob[]>(FALLBACK_JOBS);
  const [statusFilter, setStatusFilter] = useState("all");

  function loadJobs() {
    fetchJobs()
      .then(setJobs)
      .catch(() => {});
  }

  useEffect(() => {
    loadJobs();
    const interval = setInterval(loadJobs, 10000);
    return () => clearInterval(interval);
  }, []);

  const filtered = jobs.filter((j) => {
    if (statusFilter === "all") return true;
    return j.status === statusFilter;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-xl font-bold text-slate-100">Indexing Jobs</h2>
        <button className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          <Plus className="h-4 w-4" />
          New Import
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <Filter className="h-4 w-4 text-slate-500" />
        <div className="flex gap-2">
          {STATUS_OPTIONS.map((opt) => (
            <button
              key={opt}
              onClick={() => setStatusFilter(opt)}
              className={cn(
                "rounded-lg px-3 py-1.5 text-xs font-medium capitalize transition-colors",
                statusFilter === opt
                  ? "bg-blue-600 text-white"
                  : "border border-slate-700 text-slate-400 hover:bg-slate-800 hover:text-slate-200",
              )}
            >
              {opt}
            </button>
          ))}
        </div>
      </div>

      {/* Job list */}
      <div className="space-y-4">
        {filtered.map((job) => (
          <JobProgressCard
            key={job.id}
            job={job}
            onRefresh={loadJobs}
            expanded
          />
        ))}
        {filtered.length === 0 && (
          <div className="rounded-xl border border-slate-800 bg-slate-900 py-16 text-center text-sm text-slate-500">
            No jobs match the current filter.
          </div>
        )}
      </div>
    </div>
  );
}
