import { useState, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ShieldAlert, ArrowUpRight,
  CheckCircle2, ChevronRight
} from 'lucide-react';
import { Badge } from '@/components/atoms/Badge';

export interface AttentionItem {
  id: string;
  filename: string;
  category: 'flagged' | 'privilege' | 'risk' | 'escalated';
  title: string;
  badgeLabel: string;
  badgeVariant: 'danger' | 'warning' | 'purple' | 'info';
  reason?: string;
  actionRoute: string;
  actionLabel: string;
}

interface NeedsAttentionPanelProps {
  caseId: string;
  documents: any[];
  isLoading?: boolean;
}

export function NeedsAttentionPanel({ caseId, documents, isLoading }: NeedsAttentionPanelProps) {
  const navigate = useNavigate();
  const [activeFilter, setActiveFilter] = useState<'all' | 'flagged' | 'privilege' | 'risk' | 'escalated'>('all');

  // Derive genuine attention items from real document metadata
  const attentionItems = useMemo<AttentionItem[]>(() => {
    if (!documents || !Array.isArray(documents)) return [];

    const items: AttentionItem[] = [];

    for (const doc of documents) {
      const meta = doc.doc_metadata || {};
      const pa = meta.privilege_analysis || {};
      const ra = meta.risk_analysis || meta.risk || {};
      const triage = meta.triage || {};
      const filename = doc.original_filename || doc.filename || `Document ${doc.id.slice(0, 8)}`;

      // 1. Flagged documents
      if (doc.status === 'flagged') {
        items.push({
          id: `flagged-${doc.id}`,
          filename,
          category: 'flagged',
          title: `Flagged for Human Determination`,
          badgeLabel: 'Flagged',
          badgeVariant: 'danger',
          reason: pa.reasoning || triage.escalation_reason || 'Marked as flagged for attorney review and determination.',
          actionRoute: `/documents/${doc.id}`,
          actionLabel: 'Review Document',
        });
      }

      // 2. High / Critical Risk
      const overallRisk = (ra.overall_risk || ra.risk_level || '').toLowerCase();
      if (overallRisk === 'high' || overallRisk === 'critical') {
        const topReason = ra.summary || (Array.isArray(ra.assessments) && ra.assessments[0]?.reason) || 'High compliance or exposure risk detected';
        items.push({
          id: `risk-${doc.id}`,
          filename,
          category: 'risk',
          title: `High Risk Exposure Pattern`,
          badgeLabel: overallRisk.toUpperCase(),
          badgeVariant: 'warning',
          reason: topReason,
          actionRoute: `/documents/${doc.id}`,
          actionLabel: 'Inspect Risk',
        });
      }

      // 3. Substantive Privilege Determinations
      if (pa.is_privileged === true) {
        items.push({
          id: `priv-${doc.id}`,
          filename,
          category: 'privilege',
          title: `Privileged Communication Detected`,
          badgeLabel: 'Privilege Protection',
          badgeVariant: 'purple',
          reason: pa.reasoning || 'Contains attorney-client communication or legal counsel work product.',
          actionRoute: `/documents/${doc.id}`,
          actionLabel: 'Review Privilege',
        });
      }

      // 4. Escalations from Triage Orchestrator
      if (triage.is_escalated === true || (triage.priority_score && triage.priority_score >= 85)) {
        items.push({
          id: `esc-${doc.id}`,
          filename,
          category: 'escalated',
          title: `Priority Triage Escalation`,
          badgeLabel: `Priority ${Math.round(triage.priority_score || 90)}`,
          badgeVariant: 'danger',
          reason: triage.escalation_reason || 'Escalated by Triage Orchestrator for urgent attorney review.',
          actionRoute: `/documents/${doc.id}`,
          actionLabel: 'Examine Item',
        });
      }
    }

    return items;
  }, [documents]);

  const filteredItems = useMemo(() => {
    if (activeFilter === 'all') return attentionItems;
    return attentionItems.filter((item) => item.category === activeFilter);
  }, [attentionItems, activeFilter]);

  const counts = useMemo(() => {
    return {
      all: attentionItems.length,
      flagged: attentionItems.filter((i) => i.category === 'flagged').length,
      privilege: attentionItems.filter((i) => i.category === 'privilege').length,
      risk: attentionItems.filter((i) => i.category === 'risk').length,
      escalated: attentionItems.filter((i) => i.category === 'escalated').length,
    };
  }, [attentionItems]);

  const displayedItems = filteredItems.slice(0, 6);

  return (
    <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-5 backdrop-blur-sm space-y-4 shadow-sm" id="needs-attention-section">
      {/* ── Section Header ────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/60 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
            <ShieldAlert className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-slate-100">Needs Attorney Attention</h3>
              <Badge variant={counts.all > 0 ? 'warning' : 'outline'} size="xs">
                {counts.all} actionable items
              </Badge>
            </div>
            <p className="text-[11px] text-slate-400">Flagged evidence, privileged documents, and compliance risk triggers</p>
          </div>
        </div>

        <Link
          to={`/cases/${caseId}/findings`}
          className="text-xs text-indigo-400 hover:text-indigo-300 font-medium inline-flex items-center gap-1 transition-colors self-start sm:self-auto"
          id="needs-attention-view-all"
        >
          <span>Open Full Findings Register</span>
          <ArrowUpRight className="h-3 w-3" />
        </Link>
      </div>

      {/* ── Filter Pills ──────────────────────────────────────────── */}
      {counts.all > 0 && (
        <div className="flex items-center gap-1.5 flex-wrap">
          <button
            type="button"
            onClick={() => setActiveFilter('all')}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
              activeFilter === 'all'
                ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                : 'bg-slate-950/40 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            All ({counts.all})
          </button>
          {counts.flagged > 0 && (
            <button
              type="button"
              onClick={() => setActiveFilter('flagged')}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
                activeFilter === 'flagged'
                  ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                  : 'bg-slate-950/40 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              Flagged ({counts.flagged})
            </button>
          )}
          {counts.privilege > 0 && (
            <button
              type="button"
              onClick={() => setActiveFilter('privilege')}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
                activeFilter === 'privilege'
                  ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                  : 'bg-slate-950/40 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              Privilege ({counts.privilege})
            </button>
          )}
          {counts.risk > 0 && (
            <button
              type="button"
              onClick={() => setActiveFilter('risk')}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
                activeFilter === 'risk'
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                  : 'bg-slate-950/40 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              High Risk ({counts.risk})
            </button>
          )}
          {counts.escalated > 0 && (
            <button
              type="button"
              onClick={() => setActiveFilter('escalated')}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
                activeFilter === 'escalated'
                  ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                  : 'bg-slate-950/40 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              Escalated ({counts.escalated})
            </button>
          )}
        </div>
      )}

      {/* ── Items Grid or Empty State ─────────────────────────────── */}
      {isLoading ? (
        <div className="p-6 text-center text-xs text-slate-400 font-medium">
          Loading attention items...
        </div>
      ) : counts.all === 0 ? (
        <div className="p-6 rounded-xl bg-slate-950/40 border border-slate-800 text-center space-y-2" id="needs-attention-empty">
          <CheckCircle2 className="h-6 w-6 text-emerald-400 mx-auto" />
          <p className="text-xs font-semibold text-slate-200">No immediate attention items</p>
          <p className="text-[11px] text-slate-400">All documents currently reviewed without active privilege flags or escalated risk patterns.</p>
        </div>
      ) : (
        <div className="space-y-2">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5">
            {displayedItems.map((item) => (
              <div
                key={item.id}
                className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700/90 transition-all flex flex-col justify-between gap-2.5 group shadow-sm"
              >
                <div className="space-y-1.5">
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-xs font-medium text-slate-200 truncate flex-1" title={item.filename}>
                      {item.filename}
                    </span>
                    <Badge variant={item.badgeVariant} size="xs" className="shrink-0">
                      {item.badgeLabel}
                    </Badge>
                  </div>
                  <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                    {item.reason}
                  </p>
                </div>

                <div className="pt-2 border-t border-slate-800/50 flex items-center justify-between">
                  <button
                    type="button"
                    onClick={() => {
                      navigate(item.actionRoute, {
                        state: { caseId, returnTab: 'overview' },
                      });
                    }}
                    className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold inline-flex items-center gap-1 transition-colors cursor-pointer"
                  >
                    <span>{item.actionLabel}</span>
                    <ChevronRight className="h-3 w-3 group-hover:translate-x-0.5 transition-transform" />
                  </button>
                  <span className="text-[10px] text-slate-500 font-mono">
                    {item.category.toUpperCase()}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {filteredItems.length > 6 && (
            <div className="pt-2 text-center">
              <Link
                to={`/cases/${caseId}/findings`}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors border border-slate-700/60"
              >
                <span>View all {filteredItems.length} {activeFilter === 'all' ? 'attention' : activeFilter} items in Findings</span>
                <ChevronRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
