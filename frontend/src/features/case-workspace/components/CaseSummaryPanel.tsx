import { Link } from 'react-router-dom';
import {
  Scale, ShieldAlert, Files, Users,
  Calendar, Shield, AlertTriangle, FileText,
  Brain, ExternalLink
} from 'lucide-react';
import { Badge } from '@/components/atoms/Badge';
import { CaseSummarySection } from './CaseSummarySection';
import type { CaseSummaryResponse } from '../hooks/useCaseSummary';

interface CaseSummaryPanelProps {
  summary: CaseSummaryResponse;
  caseId: string;
}

export function CaseSummaryPanel({ summary, caseId }: CaseSummaryPanelProps) {
  const json = summary.summary_json;
  const metrics = json?.metrics;
  const sections = json?.sections;
  const topEntities = json?.top_entities || [];
  const keyDates = json?.key_dates || [];

  const formatDate = (isoString?: string | null) => {
    if (!isoString) return 'Unknown';
    try {
      return new Date(isoString).toLocaleString('en-US', {
        dateStyle: 'medium',
        timeStyle: 'short',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="space-y-6">
      {/* ── 1. Executive Overview (Hero Section) ────────────────────── */}
      <div className="rounded-2xl border border-indigo-500/30 bg-gradient-to-br from-indigo-950/40 via-slate-900/60 to-slate-950/80 p-6 shadow-xl backdrop-blur-md space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/60 pb-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-600 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
              <Brain className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-lg font-bold text-slate-100 tracking-tight">Executive Intelligence Overview</h2>
                <Badge variant="purple" size="xs" className="font-mono">
                  {summary.model_version || 'gemini-3.5-flash-lite'}
                </Badge>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Synthesized case-level intelligence from {summary.source_doc_count} corpus documents • Generated {formatDate(summary.generated_at)}
              </p>
            </div>
          </div>
        </div>

        {/* Corpus Metrics Grid */}
        {metrics && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
            <div className="p-3 rounded-xl bg-slate-900/70 border border-slate-800/80 space-y-1">
              <div className="flex items-center justify-between text-slate-400 text-xs">
                <span>Analyzed Corpus</span>
                <Files className="h-3.5 w-3.5 text-indigo-400" />
              </div>
              <p className="text-xl font-bold text-slate-100 font-mono">
                {metrics.total_documents ?? summary.source_doc_count}
              </p>
              <p className="text-[10px] text-slate-500">Total documents</p>
            </div>

            <div className="p-3 rounded-xl bg-slate-900/70 border border-slate-800/80 space-y-1">
              <div className="flex items-center justify-between text-slate-400 text-xs">
                <span>Privileged Items</span>
                <Shield className="h-3.5 w-3.5 text-purple-400" />
              </div>
              <p className="text-xl font-bold text-purple-300 font-mono">
                {metrics.privileged_documents_count ?? 0}
              </p>
              <p className="text-[10px] text-purple-400/80">Protected communications</p>
            </div>

            <div className="p-3 rounded-xl bg-slate-900/70 border border-slate-800/80 space-y-1">
              <div className="flex items-center justify-between text-slate-400 text-xs">
                <span>High / Critical Risk</span>
                <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
              </div>
              <p className="text-xl font-bold text-amber-300 font-mono">
                {metrics.high_or_critical_risk_count ?? 0}
              </p>
              <p className="text-[10px] text-amber-400/80">Requiring immediate review</p>
            </div>

            <div className="p-3 rounded-xl bg-slate-900/70 border border-slate-800/80 space-y-1">
              <div className="flex items-center justify-between text-slate-400 text-xs">
                <span>Timeline Events</span>
                <Calendar className="h-3.5 w-3.5 text-emerald-400" />
              </div>
              <p className="text-xl font-bold text-emerald-300 font-mono">
                {metrics.timeline_span?.total_events ?? 0}
              </p>
              <p className="text-[10px] text-slate-500 truncate" title={`${metrics.timeline_span?.core_activity_start || ''} — ${metrics.timeline_span?.core_activity_end || ''}`}>
                {metrics.timeline_span?.core_activity_start ? `${metrics.timeline_span.core_activity_start.slice(0, 4)} – ${metrics.timeline_span.core_activity_end?.slice(0, 4)}` : 'Chronological span'}
              </p>
            </div>
          </div>
        )}

        {/* Executive Text */}
        <div className="prose prose-invert max-w-none text-slate-200 text-sm leading-relaxed space-y-3 pt-1">
          {sections?.executive ? (
            sections.executive.split('\n\n').map((para, i) => (
              <p key={i} className="text-slate-300 leading-relaxed">
                {para}
              </p>
            ))
          ) : (
            <p className="text-slate-500 italic">No executive overview text available.</p>
          )}
        </div>
      </div>

      {/* ── 2. Legal Analysis ───────────────────────────────────────── */}
      <CaseSummarySection
        id="section-legal"
        title="Legal Framing & Posture"
        icon={<Scale className="h-4 w-4" />}
        badge={<Badge variant="outline" size="xs">Regulatory & Compliance</Badge>}
        defaultOpen={true}
      >
        <div className="space-y-3">
          {sections?.legal ? (
            sections.legal.split('\n\n').map((para, i) => (
              <p key={i} className="text-slate-300 leading-relaxed">
                {para}
              </p>
            ))
          ) : (
            <p className="text-slate-500 italic">No legal analysis text available.</p>
          )}
        </div>
      </CaseSummarySection>

      {/* ── 3. Notable Provisions & Findings ───────────────────────── */}
      <CaseSummarySection
        id="section-findings"
        title="Notable Provisions & Key Findings"
        icon={<ShieldAlert className="h-4 w-4 text-amber-400" />}
        badge={
          metrics?.high_or_critical_risk_count ? (
            <Badge variant="warning" size="xs">
              {metrics.high_or_critical_risk_count} Risk Factors
            </Badge>
          ) : undefined
        }
        defaultOpen={true}
      >
        <div className="space-y-3">
          {sections?.notable_provisions_and_findings ? (
            sections.notable_provisions_and_findings.split('\n\n').map((para, i) => (
              <p key={i} className="text-slate-300 leading-relaxed">
                {para}
              </p>
            ))
          ) : (
            <p className="text-slate-500 italic">No provisions text available.</p>
          )}
        </div>
      </CaseSummarySection>

      {/* ── 4. Evidence Assessment ─────────────────────────────────── */}
      <CaseSummarySection
        id="section-evidence"
        title="Evidentiary Landscape & Communications"
        icon={<Files className="h-4 w-4 text-indigo-400" />}
        badge={<Badge variant="outline" size="xs">{summary.source_doc_count} Documents</Badge>}
        defaultOpen={true}
      >
        <div className="space-y-4">
          <div className="space-y-3">
            {sections?.evidence ? (
              sections.evidence.split('\n\n').map((para, i) => (
                <p key={i} className="text-slate-300 leading-relaxed">
                  {para}
                </p>
              ))
            ) : (
              <p className="text-slate-500 italic">No evidence synthesis text available.</p>
            )}
          </div>

          {/* Key Reference Documents / Dates */}
          {keyDates.length > 0 && (
            <div className="mt-4 pt-4 border-t border-slate-800/60 space-y-2.5">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Calendar className="h-3.5 w-3.5 text-indigo-400" />
                Referenced Evidentiary Milestones
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                {keyDates.map((kd, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/60 flex flex-col justify-between gap-1 text-xs"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-indigo-400 font-semibold">{kd.date}</span>
                      {kd.source_document && (
                        <Link
                          to={`/cases/${caseId}/evidence`}
                          className="inline-flex items-center gap-1 text-[11px] text-slate-400 hover:text-indigo-300 truncate max-w-[200px] transition-colors"
                          title={kd.source_document}
                        >
                          <FileText className="h-3 w-3 shrink-0" />
                          <span className="truncate">{kd.source_document}</span>
                          <ExternalLink className="h-2.5 w-2.5 shrink-0" />
                        </Link>
                      )}
                    </div>
                    <p className="text-slate-300 text-[11px] line-clamp-2 leading-snug">
                      {kd.title}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </CaseSummarySection>

      {/* ── 5. Key People & Relationships ──────────────────────────── */}
      <CaseSummarySection
        id="section-relationships"
        title="Key Entities & Communication Graphs"
        icon={<Users className="h-4 w-4 text-violet-400" />}
        badge={<Badge variant="outline" size="xs">{topEntities.length} Primary Actors</Badge>}
        defaultOpen={true}
      >
        <div className="space-y-4">
          <div className="space-y-3">
            {sections?.key_people_and_relationships ? (
              sections.key_people_and_relationships.split('\n\n').map((para, i) => (
                <p key={i} className="text-slate-300 leading-relaxed">
                  {para}
                </p>
              ))
            ) : (
              <p className="text-slate-500 italic">No entity synthesis text available.</p>
            )}
          </div>

          {/* Top Entities Grid */}
          {topEntities.length > 0 && (
            <div className="mt-4 pt-4 border-t border-slate-800/60 space-y-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Users className="h-3.5 w-3.5 text-violet-400" />
                Network Centrality & Key Entities
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {topEntities.map((ent, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800/80 space-y-2 hover:border-slate-700/80 transition-colors"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold text-slate-100 text-xs truncate" title={ent.name}>
                        {ent.name}
                      </span>
                      <Badge
                        variant={ent.type === 'person' ? 'info' : 'purple'}
                        size="xs"
                        className="uppercase text-[10px]"
                      >
                        {ent.type}
                      </Badge>
                    </div>

                    {ent.weighted_degree !== undefined && (
                      <div className="text-[11px] text-slate-400 flex items-center justify-between">
                        <span>Centrality Score</span>
                        <span className="font-mono text-slate-200 font-semibold">{ent.weighted_degree.toFixed(1)}</span>
                      </div>
                    )}

                    {ent.top_edges && ent.top_edges.length > 0 && (
                      <div className="pt-1.5 border-t border-slate-800/50 space-y-1">
                        <span className="text-[10px] text-slate-500 uppercase tracking-wider block">Top Connections:</span>
                        <div className="space-y-0.5">
                          {ent.top_edges.slice(0, 3).map((edge, eIdx) => (
                            <div key={eIdx} className="text-[11px] text-slate-400 flex items-center justify-between">
                              <span className="truncate max-w-[130px]" title={edge.target}>• {edge.target}</span>
                              <span className="font-mono text-slate-500 text-[10px]">{edge.shared_docs} docs</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </CaseSummarySection>
    </div>
  );
}
