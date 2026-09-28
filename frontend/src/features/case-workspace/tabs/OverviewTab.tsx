import {
  Brain, Sparkles, RefreshCw, AlertTriangle, AlertCircle,
  Clock, Loader2, Info
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/atoms/Badge';
import { Spinner } from '@/components/atoms/Spinner';
import { useCaseWorkspace } from '../CaseWorkspaceContext';
import { useCaseSummary } from '../hooks/useCaseSummary';
import { CaseSummaryPanel } from '../components/CaseSummaryPanel';

export function OverviewTab() {
  const { caseId, caseData } = useCaseWorkspace();
  const {
    summary,
    isLoading,
    isError,
    error,
    isGenerating,
    isGeneratingMutation,
    isPollingTimedOut,
    cooldownRemaining,
    rateLimitError,
    generateSummary,
    manualRefresh,
  } = useCaseSummary(caseId);

  // Derive state per plan Section 3C
  const hasSummary = Boolean(summary?.summary_json);
  const isComplete = summary?.status === 'complete' && !summary.generating && !summary.stale && !summary.failed_last_generation;
  const isFailed = Boolean(summary?.failed_last_generation || summary?.status === 'failed');
  const isQuotaPaused = summary?.last_generation_status === 'quota_paused' || summary?.status === 'quota_paused';
  const isStale = Boolean(summary?.stale && summary?.status === 'complete');
  const isEmptyState = !isLoading && !summary && !isGenerating;

  return (
    <div className="space-y-6" id="case-overview-tab">
      {/* ── Tab Controls Header ───────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-slate-900/40 border border-slate-800/80 backdrop-blur-sm">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-slate-100 tracking-tight">Case Intelligence Summary</h2>
            {isStale && (
              <Badge variant="warning" size="xs" dot>
                Outdated
              </Badge>
            )}
            {isQuotaPaused && (
              <Badge variant="warning" size="xs" dot>
                Quota Paused
              </Badge>
            )}
            {isFailed && (
              <Badge variant="danger" size="xs" dot>
                Generation Failed
              </Badge>
            )}
            {isComplete && (
              <Badge variant="success" size="xs" dot>
                Synthesized
              </Badge>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            {caseData?.name ? `AI synthesis & holistic overview for ${caseData.name}` : 'Investigation dashboard & summary'}
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {isPollingTimedOut && (
            <button
              type="button"
              onClick={manualRefresh}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors border border-slate-700"
              id="summary-manual-refresh-button"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>Check Status</span>
            </button>
          )}

          <button
            type="button"
            onClick={generateSummary}
            disabled={isGenerating || cooldownRemaining > 0 || isGeneratingMutation}
            id="summary-generate-button"
            className={cn(
              'inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold shadow-md transition-all',
              isGenerating || cooldownRemaining > 0 || isGeneratingMutation
                ? 'bg-slate-800 text-slate-500 border border-slate-700/50 cursor-not-allowed'
                : 'bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-600 hover:to-violet-700 text-white shadow-indigo-500/20 cursor-pointer hover:shadow-indigo-500/30'
            )}
          >
            {isGenerating || isGeneratingMutation ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                <span>Generating...</span>
              </>
            ) : cooldownRemaining > 0 ? (
              <>
                <Clock className="h-3.5 w-3.5" />
                <span>Rate limited (wait {cooldownRemaining}s)</span>
              </>
            ) : hasSummary ? (
              <>
                <RefreshCw className="h-3.5 w-3.5" />
                <span>Regenerate Summary</span>
              </>
            ) : (
              <>
                <Sparkles className="h-3.5 w-3.5" />
                <span>Generate Summary</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* ── Banners & Status Alerts ───────────────────────────────── */}
      {rateLimitError && (
        <div className="p-3.5 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-300 text-xs flex items-center gap-2.5">
          <AlertCircle className="h-4 w-4 shrink-0 text-amber-400" />
          <span>{rateLimitError}</span>
        </div>
      )}

      {/* Polling Timed Out Alert */}
      {isPollingTimedOut && isGenerating && (
        <div className="p-4 rounded-xl border border-amber-500/40 bg-amber-500/10 text-amber-300 text-xs flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <Clock className="h-4 w-4 shrink-0 text-amber-400" />
            <div>
              <p className="font-semibold">Synthesis in Progress</p>
              <p className="text-[11px] text-amber-300/80 mt-0.5">
                Summary generation has taken more than 60 seconds and is still processing in the background. You can check status manually.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={manualRefresh}
            className="px-3 py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 border border-amber-500/30 text-xs font-semibold shrink-0"
          >
            Refresh Status
          </button>
        </div>
      )}

      {/* State 4: Failed Banner */}
      {isFailed && (
        <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-300 text-xs flex items-center justify-between gap-3" id="banner-failed">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
            <div>
              <p className="font-semibold text-rose-200">Last Generation Attempt Failed</p>
              <p className="text-[11px] text-rose-300/80 mt-0.5">
                {hasSummary
                  ? 'An error occurred during the last synthesis attempt. Serving previously completed case summary.'
                  : 'An error occurred during case summary synthesis. Please check API credentials and retry.'}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={generateSummary}
            disabled={cooldownRemaining > 0 || isGenerating}
            className="px-3 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 border border-rose-500/30 text-xs font-semibold shrink-0 cursor-pointer disabled:opacity-50"
          >
            Retry Generation
          </button>
        </div>
      )}

      {/* State 5: Quota Paused Banner */}
      {isQuotaPaused && (
        <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-300 text-xs flex items-center gap-2.5" id="banner-quota-paused">
          <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400" />
          <div>
            <p className="font-semibold text-amber-200">Generation Paused Due to API Quota Limits</p>
            <p className="text-[11px] text-amber-300/80 mt-0.5">
              Case intelligence synthesis has hit Google Gemini API quota limits and is temporarily paused. {hasSummary ? 'Displaying last completed summary.' : 'Will resume automatically when quota refreshes.'}
            </p>
          </div>
        </div>
      )}

      {/* State 6: Stale Banner */}
      {isStale && !isGenerating && (
        <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-300 text-xs flex items-center justify-between gap-3" id="banner-stale">
          <div className="flex items-center gap-2.5">
            <Info className="h-4 w-4 shrink-0 text-amber-400" />
            <div>
              <p className="font-semibold text-amber-200">Summary May Be Outdated</p>
              <p className="text-[11px] text-amber-300/80 mt-0.5">
                New documents or modifications have been detected in this case since the last intelligence synthesis.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={generateSummary}
            disabled={cooldownRemaining > 0 || isGenerating}
            className="px-3 py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 border border-amber-500/30 text-xs font-semibold shrink-0 cursor-pointer disabled:opacity-50"
          >
            Regenerate Now
          </button>
        </div>
      )}

      {/* ── Main Content Area ─────────────────────────────────────── */}
      {isLoading && !summary ? (
        /* Initial Loading */
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/30 p-12 text-center flex flex-col items-center justify-center space-y-3">
          <Spinner size="lg" />
          <p className="text-xs text-slate-400 font-medium">Checking case intelligence summary...</p>
        </div>
      ) : isEmptyState ? (
        /* State 1: No Summary (404) Empty State */
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/30 p-10 text-center space-y-4" id="overview-empty-state">
          <div className="h-12 w-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mx-auto">
            <Brain className="h-6 w-6" />
          </div>
          <div className="max-w-md mx-auto space-y-1.5">
            <h3 className="text-base font-bold text-slate-100">No Summary Generated Yet</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Synthesize a holistic intelligence summary across all uploaded corpus evidence, privilege indicators, regulatory posture, and chronological events for this case.
            </p>
          </div>
          <div className="pt-2">
            <button
              type="button"
              onClick={generateSummary}
              disabled={isGenerating || cooldownRemaining > 0}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-600 hover:to-violet-700 text-white text-xs font-semibold shadow-lg shadow-indigo-500/20 transition-all cursor-pointer disabled:opacity-50"
            >
              <Sparkles className="h-4 w-4" />
              <span>Generate Case Summary</span>
            </button>
          </div>
        </div>
      ) : isGenerating && !hasSummary ? (
        /* State 2a: Generating with No Prior Summary */
        <div className="rounded-2xl border border-indigo-500/30 bg-slate-900/40 p-12 text-center space-y-4" id="overview-generating-state">
          <div className="relative mx-auto w-12 h-12 flex items-center justify-center">
            <Loader2 className="h-10 w-10 text-indigo-500 animate-spin" />
            <Brain className="h-5 w-5 text-indigo-300 absolute" />
          </div>
          <div className="max-w-md mx-auto space-y-1">
            <h3 className="text-base font-bold text-slate-100">Synthesizing Case Intelligence</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Gemini is analyzing corpus documents, extracting notable legal findings, timeline milestones, and entity networks. This typically takes 20–40 seconds.
            </p>
          </div>
          <div className="pt-1">
            <Badge variant="purple" size="xs" className="animate-pulse">
              AI Multi-Stage Synthesis in Progress...
            </Badge>
          </div>
        </div>
      ) : summary ? (
        /* State 2b (Generating with prior summary) / State 3 (Complete) / State 4 (Failed w/ prior) / State 5 (Quota w/ prior) / State 6 (Stale w/ prior) */
        <div className="relative">
          {/* Updating Overlay for State 2b */}
          {isGenerating && hasSummary && (
            <div className="absolute inset-0 z-10 bg-slate-950/60 backdrop-blur-[2px] rounded-2xl flex flex-col items-center justify-center p-6 text-center space-y-3 animate-fade-in" id="overview-updating-overlay">
              <div className="p-3 rounded-xl bg-slate-900/90 border border-indigo-500/40 shadow-2xl flex items-center gap-3">
                <Loader2 className="h-5 w-5 text-indigo-400 animate-spin" />
                <div className="text-left">
                  <p className="text-xs font-semibold text-slate-100">Updating Case Intelligence…</p>
                  <p className="text-[10px] text-slate-400">Re-analyzing case corpus with latest documents</p>
                </div>
              </div>
            </div>
          )}

          {/* Render Full 5 Sections */}
          <div className={cn(isGenerating && hasSummary && 'opacity-60 transition-opacity')}>
            <CaseSummaryPanel summary={summary} caseId={caseId} />
          </div>
        </div>
      ) : isError ? (
        <div className="rounded-2xl border border-rose-500/20 bg-rose-500/10 p-6 text-center space-y-2">
          <AlertCircle className="h-6 w-6 text-rose-400 mx-auto" />
          <h3 className="text-sm font-semibold text-rose-200">Failed to load case summary</h3>
          <p className="text-xs text-rose-400/80">{(error as any)?.message || 'An unexpected error occurred.'}</p>
        </div>
      ) : null}
    </div>
  );
}
