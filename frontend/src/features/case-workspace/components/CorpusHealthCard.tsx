import { Link } from 'react-router-dom';
import {
  Files, CheckSquare,
  AlertCircle, ArrowUpRight, CheckCircle2, AlertTriangle
} from 'lucide-react';

interface CorpusHealthCardProps {
  caseId: string;
  totalDocs: number;
  reviewedCount: number;
  flaggedCount: number;
  processingCount: number;
  errorCount: number;
  quotaPausedCount: number;
  isLoading?: boolean;
}

export function CorpusHealthCard({
  caseId,
  totalDocs,
  reviewedCount,
  flaggedCount,
  processingCount,
  errorCount,
  quotaPausedCount,
  isLoading,
}: CorpusHealthCardProps) {
  const assessedCount = reviewedCount + flaggedCount;
  const coveragePercent = totalDocs > 0 ? Math.min(100, Math.round((assessedCount / totalDocs) * 100)) : 0;
  const reviewedPercent = totalDocs > 0 ? ((reviewedCount / totalDocs) * 100).toFixed(1) : '0';
  const flaggedPercent = totalDocs > 0 ? ((flaggedCount / totalDocs) * 100).toFixed(1) : '0';

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" id="corpus-health-section">
      {/* ── 1. Corpus Evidence Health ─────────────────────────────── */}
      <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-5 backdrop-blur-sm space-y-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <Files className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-100">Corpus Evidence Health</h3>
              <p className="text-[11px] text-slate-400">Total uploaded and ingested document files</p>
            </div>
          </div>
          <Link
            to={`/cases/${caseId}/evidence`}
            className="text-xs text-indigo-400 hover:text-indigo-300 font-medium inline-flex items-center gap-1 transition-colors"
            id="corpus-health-browse-evidence"
          >
            <span>Browse Evidence</span>
            <ArrowUpRight className="h-3 w-3" />
          </Link>
        </div>

        {/* 4 Health Metrics Columns */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-1">
          <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-0.5">
            <span className="text-[10px] uppercase font-bold text-slate-500">Total Corpus</span>
            <p className="text-lg font-bold text-slate-100 font-mono" id="corpus-total-docs">
              {isLoading ? '...' : totalDocs}
            </p>
            <span className="text-[10px] text-slate-400">Documents</span>
          </div>

          <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-0.5">
            <span className="text-[10px] uppercase font-bold text-emerald-400/90">Reviewed</span>
            <p className="text-lg font-bold text-emerald-300 font-mono" id="corpus-reviewed-docs">
              {isLoading ? '...' : reviewedCount}
            </p>
            <span className="text-[10px] text-emerald-400/80">{reviewedPercent}% of corpus</span>
          </div>

          <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-0.5">
            <span className="text-[10px] uppercase font-bold text-amber-400/90">Flagged</span>
            <p className="text-lg font-bold text-amber-300 font-mono" id="corpus-flagged-docs">
              {isLoading ? '...' : flaggedCount}
            </p>
            <span className="text-[10px] text-amber-400/80">{flaggedPercent}% needs action</span>
          </div>

          <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-0.5">
            <span className="text-[10px] uppercase font-bold text-slate-500">In-Pipeline</span>
            <p className="text-lg font-bold text-slate-300 font-mono" id="corpus-pipeline-docs">
              {isLoading ? '...' : processingCount}
            </p>
            <span className="text-[10px] text-slate-400">
              {errorCount > 0 ? `${errorCount} errors` : quotaPausedCount > 0 ? 'Quota paused' : 'Active stages'}
            </span>
          </div>
        </div>

        {/* Warning pill if any quota paused or error */}
        {quotaPausedCount > 0 && (
          <div className="p-2.5 rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-300 text-xs flex items-center gap-2">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-400 shrink-0" />
            <span>{quotaPausedCount} document(s) temporarily paused due to API quota limits.</span>
          </div>
        )}
        {errorCount > 0 && (
          <div className="p-2.5 rounded-lg border border-rose-500/30 bg-rose-500/10 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="h-3.5 w-3.5 text-rose-400 shrink-0" />
            <span>{errorCount} document(s) failed ingestion pipeline. Retry available in Evidence.</span>
          </div>
        )}
      </div>

      {/* ── 2. Review Workflow Progress ───────────────────────────── */}
      <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-5 backdrop-blur-sm space-y-4 shadow-sm flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="h-8 w-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                <CheckSquare className="h-4 w-4" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-100">Review Workflow Progress</h3>
                <p className="text-[11px] text-slate-400">Attorney assessment and decision status</p>
              </div>
            </div>
            <Link
              to={`/cases/${caseId}/review`}
              className="text-xs text-indigo-400 hover:text-indigo-300 font-medium inline-flex items-center gap-1 transition-colors"
              id="corpus-health-open-review"
            >
              <span>Open Review Queue</span>
              <ArrowUpRight className="h-3 w-3" />
            </Link>
          </div>

          {/* Progress Breakdown Header */}
          <div className="flex items-baseline justify-between pt-3 pb-1">
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold font-mono text-slate-100" id="review-coverage-pct">
                {isLoading ? '...' : `${coveragePercent}%`}
              </span>
              <span className="text-xs text-slate-400">Review Coverage</span>
            </div>
            <span className="text-xs text-slate-400 font-mono">
              {assessedCount} / {totalDocs} documents assessed
            </span>
          </div>

          {/* Dual Segment Progress Bar */}
          <div className="w-full h-2 rounded-full bg-slate-800/80 overflow-hidden flex" title={`${reviewedCount} reviewed, ${flaggedCount} flagged of ${totalDocs} total`}>
            {totalDocs > 0 && (
              <>
                <div
                  className="bg-emerald-500 transition-all duration-500"
                  style={{ width: `${(reviewedCount / totalDocs) * 100}%` }}
                />
                <div
                  className="bg-amber-400 transition-all duration-500"
                  style={{ width: `${(flaggedCount / totalDocs) * 100}%` }}
                />
              </>
            )}
          </div>
        </div>

        {/* Legend / Status Badges */}
        <div className="flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-slate-800/50">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              <span>Reviewed: <strong className="text-slate-200">{reviewedCount}</strong></span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-amber-400" />
              <span>Flagged: <strong className="text-slate-200">{flaggedCount}</strong></span>
            </span>
          </div>

          {coveragePercent === 100 ? (
            <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400 font-medium">
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>Full Coverage</span>
            </span>
          ) : (
            <span className="text-[11px] text-slate-400">
              {totalDocs - assessedCount} remaining in queue
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
