import { useEffect, useState } from "react";
import { FolderOpen, Loader2, CheckCircle2, XCircle, Pause } from "lucide-react";
import { Link } from "react-router-dom";
import { fetchJobs, type IndexingJob } from "../lib/api";
import { cn } from "../lib/utils";

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
];

const statusConfig = {
  pending: { icon: Pause, color: "text-slate-400", bg: "bg-slate-400/10", label: "Pending" },
  processing: { icon: Loader2, color: "text-blue-400", bg: "bg-blue-400/10", label: "Processing" },
  completed: { icon: CheckCircle2, color: "text-emerald-400", bg: "bg-emerald-400/10", label: "Completed" },
  failed: { icon: XCircle, color: "text-red-400", bg: "bg-red-400/10", label: "Failed" },
  cancelled: { icon: XCircle, color: "text-amber-400", bg: "bg-amber-400/10", label: "Cancelled" },
};

export default function ActiveJobsList() {
  const [jobs, setJobs] = useState<IndexingJob[]>(FALLBACK_JOBS);

  useEffect(() => {
    fetchJobs()
      .then(setJobs)
      .catch(() => {});
  }, []);

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FolderOpen className="h-5 w-5 text-blue-400" />
          <h3 className="text-sm font-semibold text-slate-200">
            Active Indexing Jobs
          </h3>
        </div>
        <Link
          to="/jobs"
          className="text-xs text-blue-400 hover:text-blue-300"
        >
          View All
        </Link>
      </div>
      <div className="space-y-4">
        {jobs.map((job) => {
          const status = statusConfig[job.status];
          const StatusIcon = status.icon;
          return (
            <div
              key={job.id}
              className="rounded-lg border border-slate-800 bg-slate-950/50 p-4"
            >
              <div className="mb-2 flex items-center justify-between">
                <h4 className="text-sm font-medium text-slate-200">
                  {(job.metadata?.name as string) || job.source_url}
                </h4>
                <span
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
                    status.bg,
                    status.color,
                  )}
                >
                  <StatusIcon
                    className={cn(
                      "h-3 w-3",
                      job.status === "processing" && "animate-spin",
                    )}
                  />
                  {status.label}
                </span>
              </div>

              {/* Progress bar */}
              <div className="mb-2 h-2 overflow-hidden rounded-full bg-slate-800">
                <div
                  className={cn(
                    "h-full rounded-full transition-all duration-500",
                    job.status === "completed"
                      ? "bg-emerald-500"
                      : job.status === "failed"
                        ? "bg-red-500"
                        : "bg-blue-500",
                  )}
                  style={{ width: `${job.progress_percent}%` }}
                />
              </div>

              <div className="flex items-center justify-between text-xs text-slate-500">
                <span>
                  {job.processed_files} / {job.total_files} files
                </span>
                {job.current_file && (
                  <span className="truncate max-w-[200px]">
                    Current: {job.current_file}
                  </span>
                )}
              </div>
            </div>
          );
        })}
        {jobs.length === 0 && (
          <p className="py-4 text-center text-sm text-slate-500">
            No active jobs
          </p>
        )}
      </div>
    </div>
  );
}
