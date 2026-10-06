import { useEffect, useState, useCallback } from 'react';
import { Loader2, AlertTriangle, AlertCircle, X } from 'lucide-react';
import api from '@/lib/api';

interface CaseProcessingBannerProps {
  caseId: string;
  onRefreshCase?: () => void;
}

interface IngestionStats {
  total: number;
  completed: number;
  processing: number;
  failed: number;
  quotaPaused: number;
}

const TERMINAL_STATUSES = ['reviewed', 'flagged', 'completed'];
const ACTIVE_PROCESSING_STATUSES = [
  'uploaded',
  'validating',
  'ocr_processing',
  'chunking',
  'embedding',
  'analyzing',
  'processing',
];

export function CaseProcessingBanner({ caseId, onRefreshCase }: CaseProcessingBannerProps) {
  const [stats, setStats] = useState<IngestionStats | null>(null);
  const [isDismissed, setIsDismissed] = useState(false);

  const checkStatus = useCallback(async () => {
    if (!caseId) return;
    try {
      // Fetch documents for the case
      const res = await api.get('/documents', {
        params: { case_id: caseId, page: 1, page_size: 100, include_content: false },
      });
      const docs: any[] = res.data?.documents || [];

      if (docs.length === 0) {
        setStats(null);
        return;
      }

      let completed = 0;
      let processing = 0;
      let failed = 0;
      let quotaPaused = 0;

      docs.forEach((d) => {
        const s = (d.status || '').toLowerCase();
        if (TERMINAL_STATUSES.includes(s)) {
          completed++;
        } else if (s === 'quota_paused') {
          quotaPaused++;
        } else if (s === 'error' || s === 'failed') {
          failed++;
        } else if (ACTIVE_PROCESSING_STATUSES.includes(s)) {
          processing++;
        } else {
          processing++;
        }
      });

      const newStats: IngestionStats = {
        total: docs.length,
        completed,
        processing,
        failed,
        quotaPaused,
      };

      setStats(newStats);

      // If processing just completed, refresh case telemetry in header
      if (processing === 0 && onRefreshCase) {
        onRefreshCase();
      }
    } catch {
      // Silently ignore polling errors
    }
  }, [caseId, onRefreshCase]);

  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  // Reactive polling while processing is active
  const isProcessingActive = !!stats && (stats.processing > 0 || stats.quotaPaused > 0);

  useEffect(() => {
    if (!isProcessingActive) {
      return;
    }

    const interval = setInterval(() => {
      checkStatus();
    }, 4000);

    return () => clearInterval(interval);
  }, [isProcessingActive, checkStatus]);

  if (isDismissed || !stats) return null;

  // Don't show banner if there are no processing or error documents
  if (stats.processing === 0 && stats.failed === 0 && stats.quotaPaused === 0) {
    return null;
  }

  const progressPercent =
    stats.total > 0 ? Math.round(((stats.completed + stats.failed) / stats.total) * 100) : 0;

  return (
    <div className="mb-6 rounded-2xl border overflow-hidden shadow-lg transition-all duration-300">
      {/* Active Processing State */}
      {stats.processing > 0 && (
        <div className="bg-gradient-to-r from-indigo-950/80 via-slate-900 to-indigo-950/80 border-indigo-500/30 p-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 shrink-0">
                <Loader2 className="h-5 w-5 animate-spin" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-semibold text-slate-100 tracking-tight">
                    Processing Case Evidence
                  </h4>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 font-medium">
                    {progressPercent}% processed
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  {stats.completed} of {stats.total} documents analyzed · {stats.processing} active
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="hidden sm:block w-36 bg-slate-800 rounded-full h-2 overflow-hidden border border-slate-700/50">
                <div
                  className="bg-indigo-500 h-full rounded-full transition-all duration-500"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
              <button
                type="button"
                onClick={() => setIsDismissed(true)}
                className="p-1 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition-colors"
                title="Dismiss banner"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Quota Paused State */}
      {stats.processing === 0 && stats.quotaPaused > 0 && (
        <div className="bg-amber-950/50 border-amber-500/30 p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-amber-200">
                Processing paused — AI service limit reached
              </h4>
              <p className="text-xs text-amber-300/80 mt-0.5">
                {stats.quotaPaused} document(s) queued. Your evidence is safe. Processing will resume when the AI service becomes available.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setIsDismissed(true)}
            className="p-1 rounded-lg text-amber-400/60 hover:text-amber-200 hover:bg-amber-900/40 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Completed with Errors State */}
      {stats.processing === 0 && stats.quotaPaused === 0 && stats.failed > 0 && (
        <div className="bg-rose-950/40 border-rose-500/30 p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400">
              <AlertCircle className="h-5 w-5" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-rose-200">
                Evidence processing complete with issues
              </h4>
              <p className="text-xs text-rose-300/80 mt-0.5">
                {stats.completed} document(s) successfully analyzed · {stats.failed} failed to process.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setIsDismissed(true)}
            className="p-1 rounded-lg text-rose-400/60 hover:text-rose-200 hover:bg-rose-900/40 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
}
