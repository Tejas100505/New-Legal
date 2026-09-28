import { useEffect } from 'react';
import { PageShell } from '@/components/templates/PageShell';
import { SettingsSubNav } from '../components/SettingsSubNav';
import { AnalyticsGrid } from '@/features/analytics/components/AnalyticsGrid';
import { useAnalyticsStore } from '@/stores/analyticsStore';
import { Info, Database, ShieldCheck } from 'lucide-react';

export function SettingsAnalyticsPage() {
  const { refreshAnalytics, isLoading } = useAnalyticsStore();

  useEffect(() => {
    refreshAnalytics();
  }, [refreshAnalytics]);

  return (
    <PageShell
      title="System & Corpus Analytics"
      description="Cross-case telemetry, storage consumption, and standardized AI evaluation benchmarks."
    >
      <SettingsSubNav />

      <div className="space-y-6" id="settings-analytics-content">
        {/* Notice Banner: Honest Grounding & Benchmark Scope */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 flex items-start gap-3 text-xs text-slate-300">
          <Info className="h-4 w-4 text-indigo-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-semibold text-slate-200">Evaluation & Measurement Methodology</span>
            <p className="text-slate-400 leading-relaxed">
              Storage consumption, document volumes, and entity counts represent live database state across all active matters. Model quality indicators (OCR Accuracy, Retrieval Quality, Hallucination Rate) reflect calibrated benchmarks evaluated against verified legal datasets. Metrics pending real-time instrumentation display as N/A.
            </p>
          </div>
        </div>

        {/* 11-Metric Analytics Grid */}
        <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-5">
          <AnalyticsGrid isLoading={isLoading} />
        </div>

        {/* Technical Data Sources & Verification Footnote */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl border border-slate-800/60 bg-slate-900/30 space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-200">
              <Database className="h-3.5 w-3.5 text-cyan-400" />
              <span>Corpus Telemetry</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Aggregated directly from PostgreSQL via <code className="text-indigo-300">/api/v1/analytics</code>. Includes exact byte counts for non-terminal document states and extracted entity collections.
            </p>
          </div>

          <div className="p-4 rounded-xl border border-slate-800/60 bg-slate-900/30 space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-200">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
              <span>Model Confidence & Benchmarks</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Maintained in <code className="text-indigo-300">EvaluationRepository</code> using gold-standard legal discovery annotations. Offline benchmarks are strictly isolated from client-specific case telemetry.
            </p>
          </div>
        </div>
      </div>
    </PageShell>
  );
}
