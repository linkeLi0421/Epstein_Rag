import { X, Clock, Cpu, FileText, Copy, CheckCircle2 } from "lucide-react";
import { useState } from "react";
import { type QueryLog } from "../lib/api";
import { formatDateTime, formatDuration } from "../lib/utils";

interface QueryDetailModalProps {
  query: QueryLog;
  onClose: () => void;
}

export default function QueryDetailModal({
  query,
  onClose,
}: QueryDetailModalProps) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(query.query_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl">
        {/* Header */}
        <div className="sticky top-0 flex items-center justify-between border-b border-slate-800 bg-slate-900 px-6 py-4">
          <h2 className="text-lg font-semibold text-slate-100">
            Query Details
          </h2>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-6 p-6">
          {/* Query text */}
          <div>
            <div className="mb-2 flex items-center justify-between">
              <label className="text-xs font-medium uppercase text-slate-500">
                Query
              </label>
              <button
                onClick={handleCopy}
                className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300"
              >
                {copied ? (
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                ) : (
                  <Copy className="h-3.5 w-3.5" />
                )}
                {copied ? "Copied" : "Copy"}
              </button>
            </div>
            <p className="rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm text-slate-200">
              {query.query_text}
            </p>
          </div>

          {/* Metadata */}
          <div className="grid grid-cols-3 gap-4">
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
              <div className="mb-1 flex items-center gap-1.5 text-xs text-slate-500">
                <Clock className="h-3.5 w-3.5" />
                Response Time
              </div>
              <p className="text-sm font-semibold text-slate-200">
                {formatDuration(query.response_time_ms)}
              </p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
              <div className="mb-1 flex items-center gap-1.5 text-xs text-slate-500">
                <Cpu className="h-3.5 w-3.5" />
                Client
              </div>
              <p className="text-sm font-semibold capitalize text-slate-200">
                {query.client_type}
              </p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
              <div className="mb-1 flex items-center gap-1.5 text-xs text-slate-500">
                <Clock className="h-3.5 w-3.5" />
                Timestamp
              </div>
              <p className="text-sm font-semibold text-slate-200">
                {formatDateTime(query.timestamp)}
              </p>
            </div>
          </div>

          {/* Response */}
          <div>
            <label className="mb-2 block text-xs font-medium uppercase text-slate-500">
              Response
            </label>
            <div className="max-h-48 overflow-y-auto rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm leading-relaxed text-slate-300">
              {query.response_text || "No response available"}
            </div>
          </div>

          {/* Sources */}
          {query.sources && query.sources.length > 0 && (
            <div>
              <label className="mb-2 block text-xs font-medium uppercase text-slate-500">
                Sources
              </label>
              <div className="space-y-2">
                {query.sources.map((source, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950 p-3"
                  >
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-slate-500" />
                      <span className="text-sm text-slate-300">
                        {source.source}
                      </span>
                      {source.page && (
                        <span className="text-xs text-slate-600">
                          p.{source.page}
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-slate-500">
                      {(source.similarity * 100).toFixed(0)}% match
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
