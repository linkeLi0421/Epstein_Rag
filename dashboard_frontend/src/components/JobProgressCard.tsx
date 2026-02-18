import {
  Loader2,
  CheckCircle2,
  XCircle,
  Pause,
  Clock,
  ExternalLink,
  FileText,
} from "lucide-react";
import { type IndexingJob, cancelJob } from "../lib/api";
import { cn, formatRelativeTime } from "../lib/utils";

interface JobProgressCardProps {
  job: IndexingJob;
  onRefresh?: () => void;
  expanded?: boolean;
}

const statusConfig = {
  pending: {
    icon: Pause,
    color: "text-slate-400",
    bg: "bg-slate-400/10",
    bar: "bg-slate-500",
    label: "Pending",
  },
  processing: {
    icon: Loader2,
    color: "text-blue-400",
    bg: "bg-blue-400/10",
    bar: "bg-blue-500",
    label: "Processing",
  },
  completed: {
    icon: CheckCircle2,
    color: "text-emerald-400",
    bg: "bg-emerald-400/10",
    bar: "bg-emerald-500",
    label: "Completed",
  },
  failed: {
    icon: XCircle,
    color: "text-red-400",
    bg: "bg-red-400/10",
    bar: "bg-red-500",
    label: "Failed",
  },
  cancelled: {
    icon: XCircle,
    color: "text-amber-400",
    bg: "bg-amber-400/10",
    bar: "bg-amber-500",
    label: "Cancelled",
  },
};

export default function JobProgressCard({
  job,
  onRefresh,
  expanded = false,
}: JobProgressCardProps) {
  const status = statusConfig[job.status];
  const StatusIcon = status.icon;

  async function handleCancel() {
    try {
      await cancelJob(job.id);
      onRefresh?.();
    } catch {
      // ignore
    }
  }

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <div className="mb-3 flex items-start justify-between">
        <div className="min-w-0 flex-1">
          <h4 className="truncate text-sm font-semibold text-slate-200">
            {(job.metadata?.name as string) || job.source_url}
          </h4>
          {job.source_url && (
            <p className="mt-0.5 flex items-center gap-1 truncate text-xs text-slate-500">
              <ExternalLink className="h-3 w-3" />
              {job.source_url}
            </p>
          )}
        </div>
        <span
          className={cn(
            "ml-3 inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
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
      <div className="mb-3 h-2.5 overflow-hidden rounded-full bg-slate-800">
        <div
          className={cn("h-full rounded-full transition-all duration-500", status.bar)}
          style={{ width: `${job.progress_percent}%` }}
        />
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
        <span className="flex items-center gap-1">
          <FileText className="h-3 w-3" />
          {job.processed_files} / {job.total_files} files
        </span>
        {job.failed_files > 0 && (
          <span className="text-red-400">{job.failed_files} failed</span>
        )}
        <span>{job.progress_percent}%</span>
        {job.started_at && (
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            Started {formatRelativeTime(job.started_at)}
          </span>
        )}
      </div>

      {job.current_file && job.status === "processing" && (
        <p className="mt-2 truncate text-xs text-slate-600">
          Processing: {job.current_file}
        </p>
      )}

      {job.error_message && (
        <p className="mt-2 rounded bg-red-950/30 px-3 py-2 text-xs text-red-400">
          {job.error_message}
        </p>
      )}

      {expanded && (
        <div className="mt-4 flex gap-2">
          {job.status === "processing" && (
            <button
              onClick={handleCancel}
              className="rounded-lg border border-red-800 bg-red-950/30 px-3 py-1.5 text-xs font-medium text-red-400 hover:bg-red-950/50"
            >
              Cancel
            </button>
          )}
          {job.status === "failed" && (
            <button
              onClick={onRefresh}
              className="rounded-lg border border-blue-800 bg-blue-950/30 px-3 py-1.5 text-xs font-medium text-blue-400 hover:bg-blue-950/50"
            >
              Retry
            </button>
          )}
        </div>
      )}
    </div>
  );
}
