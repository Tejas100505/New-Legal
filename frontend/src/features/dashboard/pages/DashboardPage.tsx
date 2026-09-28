/**
 * DashboardPage — Actionable Case & Review Command Center
 *
 * Focuses on "What needs my attention?":
 * - Urgent review queue (Triage Orchestrator escalations & high/critical risk documents)
 * - Active case matters & review progress
 * - Recent audit activity and reviewer actions
 *
 * Technical pipeline visualizers and system analytics have been relocated
 * to /settings/agents and /settings/analytics per the Batch 4 architecture.
 */

import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  FolderOpen,
  FileText,
  Clock,
  ChevronRight,
  ShieldAlert,
  CheckCircle2,
  ExternalLink,
  Activity,
  UserCheck,
  Hash,
} from 'lucide-react';
import { PageShell } from '@/components/templates/PageShell';
import { Badge } from '@/components/atoms/Badge';
import { Spinner } from '@/components/atoms/Spinner';
import { useAuthStore } from '@/features/auth/store';
import { formatDate } from '@/lib/utils';
import api from '@/lib/api';
import type { LegalCase } from '@/types';

interface ActionableDocument {
  id: string;
  filename: string;
  caseId?: string;
  status: string;
  isEscalated: boolean;
  escalationReason?: string | null;
  priorityTier?: string | null;
  recommendedAction?: string | null;
  hasHighRisk: boolean;
  riskLevel?: string | null;
  riskReasons: string[];
}

interface AuditActivity {
  id: string;
  action: string;
  user_email?: string;
  created_at: string;
  resource_type?: string;
  resource_id?: string;
  details?: Record<string, any>;
}

export function DashboardPage() {
  const { user } = useAuthStore();

  const [cases, setCases] = useState<LegalCase[]>([]);
  const [documents, setDocuments] = useState<any[]>([]);
  const [activities, setActivities] = useState<AuditActivity[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);

    Promise.allSettled([
      api.get('/documents', { params: { page_size: 1000, include_content: false } }),
      api.get('/cases'),
      api.get('/reports/audit-logs'),
    ]).then(([docsRes, casesRes, auditRes]) => {
      if (!isMounted) return;

      if (docsRes.status === 'fulfilled') {
        setDocuments(docsRes.value.data?.documents || []);
      }
      if (casesRes.status === 'fulfilled') {
        setCases(casesRes.value.data?.cases || []);
      }
      if (auditRes.status === 'fulfilled') {
        setActivities(auditRes.value.data?.audit_logs || []);
      }

      setIsLoading(false);
    });

    return () => {
      isMounted = false;
    };
  }, []);

  // Compute Actionable Documents (Escalated & High-Risk) using corrected substantive logic
  const actionableDocs = useMemo<ActionableDocument[]>(() => {
    const items: ActionableDocument[] = [];

    for (const doc of documents) {
      const meta = doc.doc_metadata || {};
      const triage = meta.triage || {};
      const ra = meta.risk_analysis || meta.risk || {};

      // Substantive Triage Escalation check
      const isEscalated =
        doc.status === 'flagged' ||
        triage.escalation_flag === true ||
        meta.is_escalated === true;

      // Substantive High/Critical Risk check
      const assessments = ra.assessments || [];
      const highReasons: string[] = [];
      let maxRiskLevel: string | null = null;

      if (Array.isArray(assessments)) {
        for (const a of assessments) {
          const lvl = (a.risk_level || '').toUpperCase();
          if (lvl === 'HIGH' || lvl === 'CRITICAL') {
            maxRiskLevel = lvl;
            const categoryLabel = a.category || 'Risk Exposure';
            const reason = a.reason || 'High risk pattern identified';
            highReasons.push(`${categoryLabel}: ${reason}`);
          }
        }
      }

      const overallRisk = (ra.risk_level || ra.overall_risk || '').toUpperCase();
      if (!highReasons.length && (overallRisk === 'HIGH' || overallRisk === 'CRITICAL')) {
        maxRiskLevel = overallRisk;
        highReasons.push(ra.summary || 'Significant operational or compliance exposure detected.');
      }

      const hasHighRisk = highReasons.length > 0;

      if (isEscalated || hasHighRisk) {
        items.push({
          id: doc.id,
          filename: doc.original_filename || doc.filename,
          caseId: doc.case_id,
          status: doc.status,
          isEscalated,
          escalationReason: triage.escalation_reason || triage.reasoning || null,
          priorityTier: triage.priority_tier || (isEscalated ? 'CRITICAL' : null),
          recommendedAction: triage.recommended_action || (isEscalated ? 'IMMEDIATE_HUMAN_REVIEW' : null),
          hasHighRisk,
          riskLevel: maxRiskLevel,
          riskReasons: highReasons,
        });
      }
    }

    return items;
  }, [documents]);

  // Derived Counts
  const metrics = useMemo(() => {
    const escalatedCount = actionableDocs.filter((d) => d.isEscalated).length;
    const highRiskCount = actionableDocs.filter((d) => d.hasHighRisk).length;
    const pendingCount = documents.filter((d) =>
      ['uploaded', 'validating', 'ocr_processing', 'chunking', 'embedding', 'analyzing'].includes(d.status)
    ).length;

    return {
      activeCases: cases.length,
      escalatedCount,
      highRiskCount,
      pendingCount,
      totalActionable: actionableDocs.length,
    };
  }, [actionableDocs, cases, documents]);

  const greeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  };

  return (
    <PageShell
      title="Action Center"
      description="Consolidated overview of urgent case escalations, risk exposure, and active matters."
    >
      <div className="space-y-6" id="dashboard-action-center">
        {/* ── 1. Attention Header Banner ────────────────────────────── */}
        <div className="relative rounded-2xl overflow-hidden bg-gradient-to-br from-slate-900/90 via-slate-900/60 to-indigo-950/40 border border-slate-800/80 p-6 md:p-8 shadow-xl">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">
                  {greeting()}, {user?.name?.split(' ')[0] || 'Counselor'}
                </span>
                <span className="text-slate-600">•</span>
                <span className="text-xs text-slate-400">Review & Case Command</span>
              </div>
              <h1 className="text-2xl md:text-3xl font-bold text-slate-100 tracking-tight">
                What Needs Your Attention
              </h1>
              <p className="text-xs md:text-sm text-slate-400 max-w-2xl leading-relaxed">
                {metrics.escalatedCount > 0 ? (
                  <span>
                    You have <strong className="text-amber-300 font-semibold">{metrics.escalatedCount} documents</strong> flagged for immediate human review across active case matters.
                  </span>
                ) : (
                  <span>All case documents are currently cleared without active workflow escalations.</span>
                )}
              </p>
            </div>

            <div className="flex items-center gap-3 shrink-0">
              <Link
                to="/cases"
                id="dashboard-view-cases-btn"
                className="px-4 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-800 border border-slate-700/60 text-slate-200 text-xs font-semibold transition-all flex items-center gap-1.5"
              >
                <FolderOpen className="h-3.5 w-3.5 text-indigo-400" />
                <span>View All Cases</span>
              </Link>
            </div>
          </div>
        </div>

        {/* ── 2. Attention Summary Metrics Row ──────────────────────── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5" id="dashboard-attention-metrics">
          <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/50 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-amber-400 block">
                Urgent Escalations
              </span>
              <span className="text-2xl font-bold font-mono text-slate-100" id="metric-escalations-count">
                {isLoading ? '—' : metrics.escalatedCount}
              </span>
              <span className="text-[11px] text-slate-500 block">Needs counsel sign-off</span>
            </div>
            <div className="h-10 w-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 shrink-0">
              <AlertTriangle className="h-5 w-5" />
            </div>
          </div>

          <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/50 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-rose-400 block">
                High & Critical Risk
              </span>
              <span className="text-2xl font-bold font-mono text-slate-100" id="metric-risk-count">
                {isLoading ? '—' : metrics.highRiskCount}
              </span>
              <span className="text-[11px] text-slate-500 block">Substantial exposure</span>
            </div>
            <div className="h-10 w-10 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 shrink-0">
              <ShieldAlert className="h-5 w-5" />
            </div>
          </div>

          <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/50 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-indigo-400 block">
                Active Matters
              </span>
              <span className="text-2xl font-bold font-mono text-slate-100" id="metric-cases-count">
                {isLoading ? '—' : metrics.activeCases}
              </span>
              <span className="text-[11px] text-slate-500 block">Open workspaces</span>
            </div>
            <div className="h-10 w-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shrink-0">
              <FolderOpen className="h-5 w-5" />
            </div>
          </div>

          <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/50 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-cyan-400 block">
                Pending Processing
              </span>
              <span className="text-2xl font-bold font-mono text-slate-100" id="metric-pending-count">
                {isLoading ? '—' : metrics.pendingCount}
              </span>
              <span className="text-[11px] text-slate-500 block">In OCR / indexing</span>
            </div>
            <div className="h-10 w-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 shrink-0">
              <Clock className="h-5 w-5" />
            </div>
          </div>
        </div>

        {/* ── 3. Main Action Grid: Urgent Queue & Active Matters ──────── */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Urgent Review Queue (7 cols) */}
          <div className="lg:col-span-7 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-400" />
                <h2 className="text-sm font-bold text-slate-100 tracking-tight">
                  Urgent Review Queue ({actionableDocs.length})
                </h2>
              </div>
              <span className="text-[11px] text-slate-500 font-mono">
                Sorted by priority
              </span>
            </div>

            {isLoading ? (
              <div className="p-12 rounded-2xl border border-slate-800/80 bg-slate-900/30 flex justify-center">
                <Spinner size="md" />
              </div>
            ) : actionableDocs.length === 0 ? (
              <div className="p-12 text-center rounded-2xl border border-slate-800/80 bg-slate-900/30 space-y-3">
                <div className="h-10 w-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mx-auto">
                  <CheckCircle2 className="h-5 w-5" />
                </div>
                <h3 className="text-sm font-semibold text-slate-200">
                  Review Queue Cleared
                </h3>
                <p className="text-xs text-slate-400 max-w-sm mx-auto">
                  No documents currently require escalation sign-off or exhibit critical risk factors.
                </p>
              </div>
            ) : (
              <div className="space-y-3" id="dashboard-urgent-queue">
                {actionableDocs.slice(0, 6).map((item) => (
                  <div
                    key={item.id}
                    className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/50 hover:bg-slate-900/80 hover:border-slate-700/80 transition-all flex flex-col justify-between space-y-2.5"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <FileText className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                          <Link
                            to={`/documents/${item.id}`}
                            className="text-xs font-semibold text-slate-200 hover:text-indigo-300 transition-colors truncate max-w-xs sm:max-w-sm block"
                            title={item.filename}
                          >
                            {item.filename}
                          </Link>
                        </div>
                        <div className="flex items-center gap-2 text-[10px] text-slate-500 font-mono">
                          <span className="flex items-center gap-0.5">
                            <Hash className="h-2.5 w-2.5" />
                            {item.id.slice(0, 8)}
                          </span>
                          {item.recommendedAction && (
                            <>
                              <span>•</span>
                              <span className="text-amber-400/90 uppercase font-sans">
                                {item.recommendedAction.replace(/_/g, ' ')}
                              </span>
                            </>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5 shrink-0">
                        {item.isEscalated && (
                          <Badge variant="warning" size="xs" dot>
                            {item.priorityTier || 'ESCALATED'}
                          </Badge>
                        )}
                        {item.hasHighRisk && !item.isEscalated && (
                          <Badge variant="danger" size="xs" dot>
                            {item.riskLevel || 'HIGH RISK'}
                          </Badge>
                        )}
                      </div>
                    </div>

                    {/* Rationale Excerpt */}
                    {item.escalationReason ? (
                      <p className="text-[11px] text-amber-300/90 leading-relaxed bg-amber-500/5 border border-amber-500/20 p-2.5 rounded-lg">
                        {item.escalationReason}
                      </p>
                    ) : item.riskReasons.length > 0 ? (
                      <p className="text-[11px] text-slate-300 leading-relaxed bg-slate-950/40 border border-slate-800/60 p-2.5 rounded-lg">
                        {item.riskReasons[0]}
                      </p>
                    ) : null}

                    {/* Card Footer Link */}
                    <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between text-[11px]">
                      <span className="text-slate-500 font-mono text-[10px]">
                        Status: {item.status.toUpperCase()}
                      </span>
                      <Link
                        to={`/documents/${item.id}`}
                        className="text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium transition-colors"
                      >
                        <span>Review in Viewer</span>
                        <ExternalLink className="h-2.5 w-2.5" />
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Right Column: Active Matters & Recent Activity (5 cols) */}
          <div className="lg:col-span-5 space-y-6">
            {/* Active Case Matters */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FolderOpen className="h-4 w-4 text-indigo-400" />
                  <h2 className="text-sm font-bold text-slate-100 tracking-tight">
                    Active Matters ({cases.length})
                  </h2>
                </div>
                <Link
                  to="/cases"
                  className="text-[11px] text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
                >
                  Manage Cases →
                </Link>
              </div>

              {isLoading ? (
                <div className="p-8 rounded-2xl border border-slate-800/80 bg-slate-900/30 flex justify-center">
                  <Spinner size="md" />
                </div>
              ) : cases.length === 0 ? (
                <div className="p-8 text-center rounded-2xl border border-slate-800/80 bg-slate-900/30 text-xs text-slate-400">
                  No active case matters found.
                </div>
              ) : (
                <div className="space-y-2.5" id="dashboard-cases-list">
                  {cases.slice(0, 4).map((c) => (
                    <Link
                      key={c.id}
                      to={`/cases/${c.id}/overview`}
                      className="p-3.5 rounded-xl border border-slate-800/80 bg-slate-900/40 hover:bg-slate-900/70 hover:border-slate-700/80 transition-all flex items-center justify-between gap-3 group block"
                    >
                      <div className="space-y-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h4 className="text-xs font-bold text-slate-200 group-hover:text-indigo-300 transition-colors truncate">
                            {c.name}
                          </h4>
                        </div>
                        <div className="flex items-center gap-2 text-[10px] text-slate-500 font-mono">
                          <span>{c.caseNumber || 'NO-REF'}</span>
                          <span>•</span>
                          <span className="capitalize">{c.status}</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <Badge variant="outline" size="xs" className="font-mono text-[10px]">
                          {c.priority.toUpperCase()}
                        </Badge>
                        <ChevronRight className="h-3.5 w-3.5 text-slate-500 group-hover:text-slate-300 transition-colors" />
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>

            {/* Recent Review Audit Logs */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-cyan-400" />
                <h2 className="text-sm font-bold text-slate-100 tracking-tight">
                  Recent Audit Trail
                </h2>
              </div>

              {isLoading ? (
                <div className="p-6 rounded-2xl border border-slate-800/80 bg-slate-900/30 flex justify-center">
                  <Spinner size="sm" />
                </div>
              ) : activities.length === 0 ? (
                <div className="p-6 text-center rounded-2xl border border-slate-800/80 bg-slate-900/30 text-xs text-slate-500">
                  No recent audit activity recorded.
                </div>
              ) : (
                <div className="space-y-2" id="dashboard-audit-feed">
                  {activities.slice(0, 4).map((act, idx) => (
                    <div
                      key={act.id || idx}
                      className="p-3 rounded-lg border border-slate-800/60 bg-slate-950/40 text-xs flex items-start gap-2.5"
                    >
                      <UserCheck className="h-3.5 w-3.5 text-indigo-400 shrink-0 mt-0.5" />
                      <div className="space-y-0.5 min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-semibold text-slate-300 truncate text-[11px]">
                            {act.action.replace(/_/g, ' ')}
                          </span>
                          <span className="text-[10px] text-slate-500 shrink-0">
                            {formatDate(act.created_at)}
                          </span>
                        </div>
                        <p className="text-[10px] text-slate-400 truncate">
                          {act.user_email || 'System Operation'}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </PageShell>
  );
}
