import { ShieldAlert, Lock, AlertTriangle, Hash, ShieldCheck } from 'lucide-react';
import { Badge } from '@/components/atoms/Badge';
import { EvidenceLink } from './EvidenceLink';

export type FindingCategory = 'privilege' | 'risk' | 'escalation';

export interface FindingItem {
  id: string;
  filename: string;
  category: FindingCategory;
  title: string;
  badgeLabel: string;
  badgeVariant: 'warning' | 'purple' | 'danger' | 'info';
  details: {
    privilegeType?: string | null;
    privilegeReasoning?: string | null;
    confidence?: number | null;
    riskLevel?: string | null;
    riskScore?: number | null;
    riskReasons?: string[] | null;
    escalationReason?: string | null;
    priorityTier?: string | null;
    priorityScore?: number | null;
    recommendedAction?: string | null;
    evidenceSpans?: string[] | null;
    documentType?: string | null;
  };
}

interface FindingCardProps {
  finding: FindingItem;
}

export function FindingCard({ finding }: FindingCardProps) {
  const { category, details, id, filename, badgeLabel, badgeVariant } = finding;

  return (
    <div
      id={`finding-card-${id}`}
      className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/50 hover:bg-slate-900/80 hover:border-slate-700/80 transition-all duration-200 flex flex-col justify-between space-y-3 group shadow-sm"
    >
      {/* Top Header: Filename EvidenceLink and Category Badges */}
      <div className="space-y-2">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className="p-1.5 rounded-lg bg-slate-800/70 border border-slate-700/50 text-slate-300 shrink-0">
              {category === 'privilege' && <Lock className="h-4 w-4 text-violet-400" />}
              {category === 'risk' && <ShieldAlert className="h-4 w-4 text-rose-400" />}
              {category === 'escalation' && <AlertTriangle className="h-4 w-4 text-amber-400" />}
            </div>
            <div className="min-w-0">
              <EvidenceLink
                documentId={id}
                filename={filename}
                className="text-sm font-semibold max-w-[280px] sm:max-w-[340px]"
              />
              <div className="flex items-center gap-2 text-[10px] text-slate-500 font-mono mt-0.5">
                <span className="flex items-center gap-0.5">
                  <Hash className="h-2.5 w-2.5 text-slate-600" />
                  {id.slice(0, 8)}
                </span>
                {details.documentType && (
                  <>
                    <span>•</span>
                    <span className="uppercase text-slate-400">{details.documentType}</span>
                  </>
                )}
                {details.confidence !== undefined && details.confidence !== null && (
                  <>
                    <span>•</span>
                    <span className="text-slate-400 font-sans">
                      {Math.round(details.confidence * 100)}% AI confidence
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            <Badge variant={badgeVariant} size="xs" dot>
              {badgeLabel}
            </Badge>
            {details.priorityTier && (
              <Badge variant="outline" size="xs" className="font-mono">
                {details.priorityTier}
              </Badge>
            )}
          </div>
        </div>

        {/* ── Privilege Specific Details ──────────────────────────── */}
        {category === 'privilege' && (
          <div className="space-y-2 pt-1 text-xs">
            {details.privilegeType && (
              <div className="text-[11px] font-medium text-violet-300 flex items-center gap-1.5">
                <ShieldCheck className="h-3.5 w-3.5 text-violet-400 shrink-0" />
                <span>Protection: {details.privilegeType}</span>
              </div>
            )}
            {details.privilegeReasoning ? (
              <p className="text-slate-300 leading-relaxed font-serif italic text-xs bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/60">
                "{details.privilegeReasoning}"
              </p>
            ) : (
              <p className="text-slate-500 italic text-[11px]">
                No detailed privilege rationale available.
              </p>
            )}
          </div>
        )}

        {/* ── Risk Specific Details ───────────────────────────────── */}
        {category === 'risk' && (
          <div className="space-y-2 pt-1 text-xs">
            {details.riskReasons && details.riskReasons.length > 0 ? (
              <div className="space-y-1 bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/60">
                {details.riskReasons.map((reason, idx) => (
                  <p key={idx} className="text-slate-300 leading-snug text-xs flex items-start gap-1.5">
                    <span className="text-rose-400 mt-0.5">•</span>
                    <span>{reason}</span>
                  </p>
                ))}
              </div>
            ) : (
              <p className="text-slate-500 italic text-[11px]">
                High risk flags identified during automated compliance review.
              </p>
            )}
          </div>
        )}

        {/* ── Escalation / Triage Specific Details ────────────────── */}
        {category === 'escalation' && (
          <div className="space-y-2 pt-1 text-xs">
            {details.escalationReason ? (
              <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs space-y-1">
                <p className="font-semibold text-amber-200">
                  Triage Escalation Reason
                </p>
                <p className="leading-relaxed text-amber-300/90 text-xs">
                  {details.escalationReason}
                </p>
                {details.recommendedAction && (
                  <div className="text-[10px] font-mono uppercase tracking-wider text-amber-400/80 pt-1">
                    Action: {details.recommendedAction.replace(/_/g, ' ')}
                  </div>
                )}
              </div>
            ) : (
              <p className="text-slate-500 italic text-[11px]">
                Flagged for mandatory human review by Triage Orchestrator.
              </p>
            )}
          </div>
        )}

        {/* Evidence Spans / Citations (if present) */}
        {details.evidenceSpans && details.evidenceSpans.length > 0 && (
          <div className="space-y-1 pt-1">
            <span className="text-[10px] uppercase font-mono tracking-wider text-slate-500">
              Matched Evidence Traces:
            </span>
            <div className="flex flex-wrap gap-1">
              {details.evidenceSpans.map((span, sIdx) => (
                <span
                  key={sIdx}
                  className="px-2 py-0.5 rounded text-[10px] bg-slate-800/90 border border-slate-700/60 text-slate-300 font-mono truncate max-w-xs"
                >
                  {span}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Bottom Footer: Traceability Link */}
      <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between text-xs">
        <span className="text-[11px] text-slate-500">Evidence Source</span>
        <EvidenceLink
          documentId={id}
          filename="Review in Document Viewer"
          variant="subtle"
          showIcon={false}
          showExternalIcon={true}
          className="text-xs font-medium text-indigo-400 hover:text-indigo-300"
        />
      </div>
    </div>
  );
}
