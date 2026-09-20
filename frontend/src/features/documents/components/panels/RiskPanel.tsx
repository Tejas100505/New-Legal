import { Badge } from '@/components/atoms/Badge';
import { ShieldAlert, AlertTriangle, ShieldCheck, UserCheck, AlertCircle } from 'lucide-react';
import type { PrivilegeAnalysis, HumanOverrideRecord } from '@/types';

interface RiskPanelProps {
  doc?: any;
}

export function RiskPanel({ doc }: RiskPanelProps) {
  const privilege: PrivilegeAnalysis | null = doc?.doc_metadata?.privilege_analysis || null;
  const humanOverrides: HumanOverrideRecord[] = doc?.doc_metadata?.human_overrides || [];
  const riskLevel = doc?.riskLevel || (privilege?.is_privileged ? 'critical' : 'low');

  // Pending Privilege Analysis Handling
  if (!privilege && !doc?.doc_metadata?.risk_factors && (!doc?.doc_metadata || Object.keys(doc.doc_metadata).length === 0)) {
    return (
      <div className="flex flex-col gap-3 text-left p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200">
        <div className="flex items-center gap-2">
          <AlertCircle className="h-5 w-5 text-amber-400 shrink-0" />
          <h4 className="text-xs font-bold uppercase tracking-wider text-amber-300">Privilege Analysis Pending</h4>
        </div>
        <p className="text-xs leading-relaxed text-amber-200/90">
          Privilege determination and risk factor indexing have not yet run for this document.
        </p>
        <p className="text-[11px] text-amber-300/70">
          Select "Re-run Analysis" to screen for attorney-client privilege, work product doctrine, and legal exposure.
        </p>
      </div>
    );
  }

  const isPrivileged = privilege ? privilege.is_privileged : (doc?.isPrivileged ?? false);
  const confidence = privilege ? privilege.confidence : 0.90;
  const rawMethod = privilege?.detection_method || 'rule_heuristics';
  const detectionMethod = rawMethod === 'rule_heuristics'
    ? 'Automated Privilege Rules'
    : rawMethod === 'llm_reasoning'
    ? 'AI Legal Review'
    : rawMethod.replace(/_/g, ' ');

  return (
    <div className="flex flex-col gap-4 text-left">
      {/* Privilege Status Header */}
      <div className="flex justify-between items-center bg-slate-950/40 p-3 rounded-lg border border-slate-850">
        <span className="text-xs text-slate-400 flex items-center gap-1.5">
          {isPrivileged ? (
            <ShieldAlert className="h-4 w-4 text-rose-400" />
          ) : (
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
          )}
          Privilege Determination
        </span>
        <div className="flex items-center gap-2">
          <Badge
            variant={isPrivileged ? 'danger' : 'success'}
            size="sm"
          >
            {isPrivileged ? 'PRIVILEGED' : 'NON-PRIVILEGED'}
          </Badge>
          <Badge variant="outline" size="xs">
            Risk: {riskLevel.toUpperCase()}
          </Badge>
          <span className="text-xs font-mono font-bold text-slate-300">
            {(confidence * 100).toFixed(0)}% Conf
          </span>
        </div>
      </div>

      {/* Human Review Override Status */}
      {humanOverrides.length > 0 && (
        <div className="flex flex-col gap-2 p-3 rounded-lg bg-indigo-950/30 border border-indigo-500/30">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-indigo-300 flex items-center gap-1">
              <UserCheck className="h-3.5 w-3.5 text-indigo-400" /> Human Override Active
            </span>
            <Badge variant="purple" size="xs">
              {humanOverrides[humanOverrides.length - 1].action.toUpperCase()}
            </Badge>
          </div>
          <div className="text-[11px] text-slate-300">
            <strong>Field:</strong> {humanOverrides[humanOverrides.length - 1].field} | <strong>Value:</strong> {String(humanOverrides[humanOverrides.length - 1].override_value)}
          </div>
          <div className="text-[11px] text-slate-400 italic">
            "{humanOverrides[humanOverrides.length - 1].reason}"
          </div>
          <div className="text-[10px] text-indigo-400">
            Reviewed by: {humanOverrides[humanOverrides.length - 1].reviewer_email || 'Verified Reviewer'}
          </div>
        </div>
      )}

      {/* Privilege Reasoning from LLM */}
      {privilege?.reasoning && (
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Legal Privilege Reasoning</h4>
            <span className="text-[10px] text-slate-500 font-mono">via {detectionMethod}</span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed bg-slate-900/40 p-3 rounded-lg border border-slate-850 whitespace-pre-wrap">
            {privilege.reasoning}
          </p>
        </div>
      )}

      {/* Evidence Spans / Quotes */}
      {privilege?.evidence_spans && privilege.evidence_spans.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
            Flagged Evidence Spans
          </h4>
          <div className="flex flex-col gap-2">
            {privilege.evidence_spans.map((span, idx) => (
              <div key={idx} className="p-2.5 rounded-lg bg-rose-950/20 border border-rose-500/20 text-xs">
                <p className="italic text-slate-300 leading-relaxed font-mono text-[11px]">"{span}"</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Privilege Type if identified */}
      {privilege?.privilege_type && (
        <div className="flex items-center justify-between bg-slate-950/40 p-2.5 rounded-lg border border-slate-850 text-xs">
          <span className="text-slate-400">Identified Category:</span>
          <span className="font-semibold text-indigo-300">{privilege.privilege_type}</span>
        </div>
      )}
    </div>
  );
}
