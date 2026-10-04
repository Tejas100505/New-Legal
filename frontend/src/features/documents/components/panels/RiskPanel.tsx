import { useState } from 'react';
import { Badge } from '@/components/atoms/Badge';
import {
  ShieldAlert, ShieldCheck, UserCheck, AlertTriangle,
  CheckCircle2, Scale, Check, X, Loader2
} from 'lucide-react';
import api from '@/lib/api';

interface RiskPanelProps {
  doc?: any;
  onDocUpdate?: (updatedDoc: any) => void;
}

export function RiskPanel({ doc, onDocUpdate }: RiskPanelProps) {
  const [activeReviewAction, setActiveReviewAction] = useState<string | null>(null);
  const [overrideReason, setOverrideReason] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const privilege = doc?.doc_metadata?.privilege_analysis || null;
  const riskAnalysis = doc?.doc_metadata?.risk_analysis || null;
  const triage = doc?.doc_metadata?.triage || null;
  const humanOverrides: any[] = doc?.doc_metadata?.human_overrides || [];

  const isPrivileged = privilege ? Boolean(privilege.is_privileged) : (doc?.isPrivileged ?? false);
  const confidenceScore = privilege?.confidence_score ?? privilege?.confidence ?? null;
  const privilegeType = privilege?.privilege_type || (isPrivileged ? 'Attorney-Client Privilege' : null);

  // Real risk metrics
  const riskLevel = riskAnalysis?.risk_level || doc?.riskLevel || (isPrivileged ? 'critical' : 'low');
  const riskScore = riskAnalysis?.risk_score != null ? (Number(riskAnalysis.risk_score) * 100).toFixed(0) : null;
  const assessments: any[] = riskAnalysis?.assessments || [];

  const handleReviewDecision = async (
    field: 'privilege' | 'relevance',
    action: 'confirm' | 'override',
    overrideValue: any,
    defaultReason: string,
    newStatus: string = 'reviewed'
  ) => {
    if (!doc?.id) return;
    const finalReason = overrideReason.trim() || defaultReason;
    if (!finalReason) {
      setActionError('A brief justification reason is required for legal audit compliance.');
      return;
    }

    try {
      setIsSubmitting(true);
      setActionError(null);

      const payload = {
        field,
        action,
        override_value: overrideValue,
        original_ai_value: field === 'privilege' ? isPrivileged : null,
        ai_confidence: confidenceScore != null ? Number(confidenceScore) : null,
        reason: finalReason,
        new_status: newStatus,
      };

      const res = await api.post(`/documents/${doc.id}/override`, payload);
      if (res.data && onDocUpdate) {
        onDocUpdate(res.data);
      }
      setActiveReviewAction(null);
      setOverrideReason('');
    } catch (err: any) {
      console.error('Failed to submit human review decision:', err);
      setActionError(err?.response?.data?.detail || 'Failed to record review decision.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col gap-5 text-left font-sans">
      {/* ── Section 1: Human Review Decision Controls ───────────────────────── */}
      <div className="rounded-xl border border-indigo-500/30 bg-slate-900/60 p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <UserCheck className="h-4 w-4 text-indigo-400" />
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Attorney Human Review
            </h4>
          </div>
          {doc?.doc_metadata?.review_status === 'reviewed_by_human' ? (
            <Badge variant="success" size="xs" className="flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3" /> Human Verified
            </Badge>
          ) : (
            <Badge variant="outline" size="xs" className="text-amber-400 border-amber-500/30">
              Pending Human Sign-off
            </Badge>
          )}
        </div>

        {/* Quick Decision Actions */}
        <div className="space-y-2 pt-1">
          <div className="text-[11px] text-slate-400 font-medium">Record Review Decision:</div>
          <div className="grid grid-cols-2 gap-2">
            {isPrivileged ? (
              <>
                <button
                  type="button"
                  onClick={() => setActiveReviewAction('confirm_privileged')}
                  className="px-2.5 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/30 text-xs font-semibold flex items-center justify-center gap-1 transition-colors cursor-pointer"
                >
                  <ShieldAlert className="h-3.5 w-3.5 text-rose-400" />
                  Confirm Privileged
                </button>
                <button
                  type="button"
                  onClick={() => setActiveReviewAction('override_non_privileged')}
                  className="px-2.5 py-1.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/30 text-xs font-semibold flex items-center justify-center gap-1 transition-colors cursor-pointer"
                >
                  <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                  Override: Not Privileged
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => setActiveReviewAction('confirm_non_privileged')}
                  className="px-2.5 py-1.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/30 text-xs font-semibold flex items-center justify-center gap-1 transition-colors cursor-pointer"
                >
                  <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                  Confirm Non-Privileged
                </button>
                <button
                  type="button"
                  onClick={() => setActiveReviewAction('override_privileged')}
                  className="px-2.5 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/30 text-xs font-semibold flex items-center justify-center gap-1 transition-colors cursor-pointer"
                >
                  <ShieldAlert className="h-3.5 w-3.5 text-rose-400" />
                  Override: Privileged
                </button>
              </>
            )}
          </div>
        </div>

        {/* Interactive Reason Input Form when an action is selected */}
        {activeReviewAction && (
          <div className="p-3 bg-slate-950 rounded-lg border border-indigo-500/40 space-y-2 mt-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-indigo-300">
                {activeReviewAction === 'confirm_privileged' && 'Confirming Attorney-Client Privilege'}
                {activeReviewAction === 'override_non_privileged' && 'Overriding AI Privilege (Marking Non-Privileged)'}
                {activeReviewAction === 'confirm_non_privileged' && 'Confirming Non-Privileged Business Record'}
                {activeReviewAction === 'override_privileged' && 'Overriding to Privileged (Withholding from Production)'}
              </span>
              <button
                type="button"
                onClick={() => { setActiveReviewAction(null); setActionError(null); }}
                className="text-slate-500 hover:text-slate-300"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
            <textarea
              rows={2}
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.target.value)}
              placeholder="Enter auditable legal rationale for this determination..."
              className="w-full bg-slate-900 border border-slate-800 rounded p-2 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
            {actionError && (
              <p className="text-[11px] text-rose-400">{actionError}</p>
            )}
            <div className="flex justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={() => setActiveReviewAction(null)}
                className="px-2.5 py-1 rounded text-xs text-slate-400 hover:text-slate-200"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isSubmitting}
                onClick={() => {
                  if (activeReviewAction === 'confirm_privileged') {
                    handleReviewDecision('privilege', 'confirm', true, 'Confirmed privileged attorney-client communication', 'flagged');
                  } else if (activeReviewAction === 'override_non_privileged') {
                    handleReviewDecision('privilege', 'override', false, 'Overridden: ordinary business record, no legal advice', 'reviewed');
                  } else if (activeReviewAction === 'confirm_non_privileged') {
                    handleReviewDecision('privilege', 'confirm', false, 'Confirmed non-privileged business record', 'reviewed');
                  } else if (activeReviewAction === 'override_privileged') {
                    handleReviewDecision('privilege', 'override', true, 'Overridden: sensitive legal advice detected, withheld', 'flagged');
                  }
                }}
                className="px-3 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1 cursor-pointer disabled:opacity-50"
              >
                {isSubmitting ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
                Submit Decision
              </button>
            </div>
          </div>
        )}

        {/* Existing Human Overrides Trail */}
        {humanOverrides.length > 0 && (
          <div className="pt-2 border-t border-slate-800/80 space-y-2">
            <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider block">
              Recorded Review Decisions ({humanOverrides.length})
            </span>
            {humanOverrides.map((ovr: any, idx: number) => (
              <div key={ovr.id || idx} className="p-2.5 rounded bg-slate-950/60 border border-slate-800 text-[11px] space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-200 capitalize">
                    {ovr.field}: {String(ovr.override_value)}
                  </span>
                  <Badge variant={ovr.action === 'override' ? 'warning' : 'purple'} size="xs">
                    {ovr.action?.toUpperCase()}
                  </Badge>
                </div>
                {ovr.reason && (
                  <p className="text-slate-400 italic">"{ovr.reason}"</p>
                )}
                <div className="text-[10px] text-slate-500 flex justify-between pt-0.5">
                  <span>By: {ovr.reviewed_by || 'Attorney Reviewer'}</span>
                  <span>{ovr.reviewed_at ? new Date(ovr.reviewed_at).toLocaleDateString() : ''}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Section 2: AI Privilege Determination ────────────────────────────── */}
      <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-4 space-y-3">
        <div className="flex justify-between items-center pb-2 border-b border-slate-800/60">
          <span className="text-xs text-slate-300 font-semibold flex items-center gap-1.5">
            {isPrivileged ? (
              <ShieldAlert className="h-4 w-4 text-rose-400" />
            ) : (
              <ShieldCheck className="h-4 w-4 text-emerald-400" />
            )}
            AI Privilege Determination
          </span>
          <div className="flex items-center gap-2">
            <Badge variant={isPrivileged ? 'danger' : 'success'} size="xs">
              {isPrivileged ? 'PRIVILEGED' : 'NON-PRIVILEGED'}
            </Badge>
            <span className="text-xs font-mono text-slate-400">
              {confidenceScore != null ? `${(Number(confidenceScore) * 100).toFixed(0)}% Conf` : '—'}
            </span>
          </div>
        </div>

        {privilegeType && (
          <div className="text-xs text-slate-300">
            <span className="text-slate-500">Privilege Category:</span>{' '}
            <span className="font-medium text-slate-200">{privilegeType}</span>
          </div>
        )}

        {privilege?.reasoning ? (
          <div className="space-y-1">
            <div className="text-[10px] text-slate-400 uppercase font-semibold">AI Legal Reasoning:</div>
            <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-3 rounded-lg border border-slate-850 whitespace-pre-wrap">
              {privilege.reasoning}
            </p>
          </div>
        ) : (
          <p className="text-xs text-slate-500 italic">No privilege indicators detected.</p>
        )}

        {/* Evidence Spans */}
        {privilege?.evidence_spans && privilege.evidence_spans.length > 0 && (
          <div className="space-y-1.5">
            <div className="text-[10px] text-slate-400 uppercase font-semibold">
              Evidence Markers ({privilege.evidence_spans.length})
            </div>
            <div className="space-y-1">
              {privilege.evidence_spans.slice(0, 3).map((span: string, idx: number) => (
                <div
                  key={idx}
                  className="p-2 rounded bg-rose-950/20 border-l-2 border-rose-500 text-slate-300 font-mono text-[11px] break-words"
                >
                  "{span}"
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── Section 3: Risk Assessment & Breakdown ────────────────────────────── */}
      <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-4 space-y-3">
        <div className="flex justify-between items-center pb-2 border-b border-slate-800/60">
          <span className="text-xs text-slate-300 font-semibold flex items-center gap-1.5">
            <AlertTriangle className="h-4 w-4 text-amber-400" />
            Legal & Regulatory Risk
          </span>
          <div className="flex items-center gap-2">
            <Badge
              variant={
                riskLevel.toLowerCase() === 'critical'
                  ? 'danger'
                  : riskLevel.toLowerCase() === 'high'
                  ? 'warning'
                  : 'default'
              }
              size="xs"
            >
              Risk: {riskLevel.toUpperCase()}
            </Badge>
            {riskScore && (
              <span className="text-xs font-mono text-slate-400">{riskScore}% Score</span>
            )}
          </div>
        </div>

        {/* Risk Category Breakdown */}
        {assessments.length > 0 ? (
          <div className="space-y-2">
            <div className="text-[10px] text-slate-400 uppercase font-semibold">
              Risk Factor Breakdown:
            </div>
            {assessments.map((item: any, idx: number) => (
              <div key={idx} className="p-2.5 rounded bg-slate-950/60 border border-slate-850 space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-200">{item.category || 'Risk Factor'}</span>
                  <Badge
                    variant={
                      item.risk_level?.toLowerCase() === 'high' || item.risk_level?.toLowerCase() === 'critical'
                        ? 'danger'
                        : 'default'
                    }
                    size="xs"
                  >
                    {item.risk_level || 'LOW'}
                  </Badge>
                </div>
                {item.reason && (
                  <p className="text-[11px] text-slate-400 leading-relaxed">{item.reason}</p>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-400">
            Standard baseline risk profile. No active regulatory or dispute flags identified.
          </p>
        )}
      </div>

      {/* ── Section 4: AI Triage Prioritization ──────────────────────────────── */}
      {triage && (
        <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-4 space-y-2.5">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800/60">
            <span className="text-xs text-slate-300 font-semibold flex items-center gap-1.5">
              <Scale className="h-4 w-4 text-violet-400" />
              AI Triage Prioritization
            </span>
            <Badge variant="purple" size="xs">
              {triage.priority_tier || 'STANDARD'}
            </Badge>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="p-2 rounded bg-slate-950/40 border border-slate-850">
              <span className="text-[10px] text-slate-500 block">Triage Path</span>
              <span className="font-medium text-slate-200">{triage.triage_path || 'Standard'}</span>
            </div>
            <div className="p-2 rounded bg-slate-950/40 border border-slate-850">
              <span className="text-[10px] text-slate-500 block">Recommended Action</span>
              <span className="font-medium text-slate-200">{triage.recommended_action || 'Routine Queue'}</span>
            </div>
          </div>

          {triage.reasoning && (
            <p className="text-xs text-slate-400 leading-relaxed bg-slate-950/60 p-2.5 rounded border border-slate-850">
              {triage.reasoning}
            </p>
          )}

          <div className="pt-1">
            <p className="text-[10px] text-slate-500 italic">
              AI Advisory Recommendation — Final determination and production approval remain the sole responsibility of reviewing legal counsel.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
