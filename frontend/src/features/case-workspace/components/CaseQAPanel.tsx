import React, { useState, useCallback } from 'react';
import {
  Send,
  Sparkles,
  ShieldCheck,
  AlertTriangle,
  AlertCircle,
  Info,
  ChevronDown,
  ChevronUp,
  Trash2,
  Cpu,
  Clock,
  CheckCircle2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/atoms/Badge';
import { Spinner } from '@/components/atoms/Spinner';
import { CitationChip } from './CitationChip';
import { CitationCard } from './CitationCard';
import { QAEmptyState } from './QAEmptyState';
import type { QAExchange } from '../hooks/useCaseAsk';

interface CaseQAPanelProps {
  caseId: string;
  caseName?: string;
  input: string;
  setInput: (value: string) => void;
  history: QAExchange[];
  submitQuestion: (customQuestion?: string) => Promise<boolean>;
  clearHistory: () => void;
  isSubmitting: boolean;
  cooldownRemaining: number;
}

export function CaseQAPanel({
  caseName,
  input,
  setInput,
  history,
  submitQuestion,
  clearHistory,
  isSubmitting,
  cooldownRemaining,
}: CaseQAPanelProps) {
  const [highlightedCitationId, setHighlightedCitationId] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({});

  const toggleSection = useCallback((id: string) => {
    setExpandedSections((prev) => ({ ...prev, [id]: !prev[id] }));
  }, []);

  const handleChipClick = useCallback((citationId: string) => {
    setHighlightedCitationId(citationId);
    const cardEl = document.getElementById(`citation-card-${citationId}`);
    if (cardEl) {
      cardEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    setTimeout(() => {
      setHighlightedCitationId((curr) => (curr === citationId ? null : curr));
    }, 2500);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isSubmitting || cooldownRemaining > 0) return;
    await submitQuestion();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  // Helper to parse answer text and embed interactive CitationChips
  const renderFormattedAnswer = (answer: string) => {
    const parts = answer.split(/(\[C\d+\])/g);
    return parts.map((part, i) => {
      if (/^\[C\d+\]$/.test(part)) {
        const citationNum = part.replace(/[[\]]/g, '');
        return (
          <CitationChip
            key={i}
            label={part}
            onClick={() => handleChipClick(citationNum)}
          />
        );
      }
      return <span key={i}>{part}</span>;
    });
  };

  return (
    <div className="space-y-6" id="case-qa-panel">
      {/* ── Query Input Box ────────────────────────────────────────── */}
      <div className="p-4 sm:p-5 rounded-2xl border border-slate-800/80 bg-slate-900/60 backdrop-blur-md shadow-xl space-y-3">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-lg bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <Sparkles className="h-4 w-4" />
            </div>
            <h2 className="text-sm font-semibold text-slate-100">
              Inquire into Case Evidence
            </h2>
          </div>

          {history.length > 0 && (
            <button
              type="button"
              id="qa-clear-session-button"
              onClick={clearHistory}
              className="text-xs text-slate-400 hover:text-rose-400 flex items-center gap-1.5 transition-colors cursor-pointer px-2 py-1 rounded hover:bg-slate-800/50"
            >
              <Trash2 className="h-3.5 w-3.5" />
              <span>Clear Session ({history.length})</span>
            </button>
          )}
        </div>

        <form onSubmit={handleSubmit} className="space-y-2.5">
          <div className="relative">
            <textarea
              id="qa-question-input"
              rows={3}
              value={input}
              onChange={(e) => setInput(e.target.value.slice(0, 1000))}
              onKeyDown={handleKeyDown}
              disabled={isSubmitting}
              placeholder="Ask a question about the case evidence… (e.g. regulatory allegations, specific trading dates, or key witness roles)"
              className="w-full px-3.5 py-3 rounded-xl bg-slate-950/70 border border-slate-800 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 resize-none transition-all disabled:opacity-50"
            />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2.5">
            <div className="flex items-center gap-2 text-[11px] text-slate-400">
              <span
                className={cn(
                  'font-mono',
                  input.length > 900 ? 'text-amber-400 font-semibold' : 'text-slate-500'
                )}
              >
                {input.length}/1000
              </span>
              <span className="hidden sm:inline text-slate-600">•</span>
              <span className="hidden sm:inline">Press Enter to submit, Shift+Enter for new line</span>
            </div>

            <button
              type="submit"
              id="qa-submit-button"
              disabled={!input.trim() || isSubmitting || cooldownRemaining > 0}
              className={cn(
                'inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold tracking-wide transition-all shadow-md shrink-0 cursor-pointer disabled:cursor-not-allowed',
                cooldownRemaining > 0
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                  : 'bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-40 disabled:hover:bg-indigo-600'
              )}
            >
              {isSubmitting ? (
                <>
                  <Spinner size="sm" />
                  <span>Analyzing Evidence…</span>
                </>
              ) : cooldownRemaining > 0 ? (
                <>
                  <Clock className="h-3.5 w-3.5" />
                  <span>Rate limited (wait {cooldownRemaining}s)</span>
                </>
              ) : (
                <>
                  <Send className="h-3.5 w-3.5" />
                  <span>Ask Question</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* ── Content Feed: Empty State or Conversation History ───── */}
      {history.length === 0 ? (
        <QAEmptyState caseName={caseName} onSelectQuestion={(q) => submitQuestion(q)} />
      ) : (
        <div className="space-y-5" id="qa-history-feed">
          {history.map((exchange) => {
            const res = exchange.response;
            const isGrounded = res?.status === 'grounded';
            const isInsufficient = res?.status === 'insufficient_evidence';
            const isSuppressed = res?.status === 'suppressed';
            const hasEvidenceItems = Boolean(res?.retrieved_evidence && res.retrieved_evidence.length > 0);
            const isRelatedEvidenceExpanded = Boolean(expandedSections[`evidence-${exchange.id}`]);
            const isDiagnosticsExpanded = Boolean(expandedSections[`diag-${exchange.id}`]);

            return (
              <div
                key={exchange.id}
                className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-5 space-y-4 shadow-sm"
              >
                {/* Exchange Question Header */}
                <div className="flex items-start justify-between gap-3 border-b border-slate-800/60 pb-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
                        Inquiry
                      </span>
                      <span className="text-slate-600">•</span>
                      <span className="text-[11px] text-slate-500">
                        {new Date(exchange.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <p className="text-sm font-semibold text-slate-100 leading-snug">
                      {exchange.question}
                    </p>
                  </div>

                  {/* Outcome Status Badge */}
                  <div>
                    {isGrounded && (
                      <Badge variant="success" dot size="xs">
                        Grounded
                      </Badge>
                    )}
                    {isInsufficient && (
                      <Badge variant="info" size="xs">
                        Insufficient Evidence
                      </Badge>
                    )}
                    {isSuppressed && (
                      <Badge variant="warning" size="xs">
                        Suppressed
                      </Badge>
                    )}
                    {exchange.error && (
                      <Badge variant="danger" size="xs">
                        Query Error
                      </Badge>
                    )}
                  </div>
                </div>

                {/* ── Grounded Outcome ──────────────────────────── */}
                {isGrounded && res?.answer && (
                  <div className="space-y-4" id="qa-grounded-outcome">
                    {/* Provenance Banner */}
                    <div className="flex flex-wrap items-center justify-between gap-2 p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs">
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                        <span className="font-semibold">AI Generated & Grounded</span>
                        <span className="text-emerald-400/60">•</span>
                        <span className="text-[11px] text-emerald-300/80">
                          Verified across Gate A (Citations) & Gate B (Lexical Entailment)
                        </span>
                      </div>
                      <Badge variant="purple" size="xs">
                        Attorney Review Required
                      </Badge>
                    </div>

                    {/* Synthesized Answer with Interactive Citation Chips */}
                    <div className="text-sm text-slate-200 leading-relaxed bg-slate-950/50 p-4 rounded-xl border border-slate-800 font-normal">
                      {renderFormattedAnswer(res.answer)}
                    </div>

                    {/* Verified Citation Cards Section */}
                    {res.citations && res.citations.length > 0 && (
                      <div className="space-y-2 pt-1" id="qa-verified-citations">
                        <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
                          <ShieldCheck className="h-4 w-4 text-indigo-400" />
                          <span>Verified Citations ({res.citations.length})</span>
                        </div>
                        <div className="grid grid-cols-1 gap-2.5">
                          {res.citations.map((c, cIdx) => (
                            <CitationCard
                              key={c.chunk_id || cIdx}
                              item={c}
                              label={`[C${cIdx + 1}]`}
                              highlighted={
                                highlightedCitationId === `C${cIdx + 1}` ||
                                highlightedCitationId === c.chunk_id
                              }
                            />
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Model Version Provenance Footer */}
                    <div className="flex items-center justify-between gap-2 text-[11px] text-slate-500 pt-2 border-t border-slate-800/60 font-mono">
                      <div className="flex items-center gap-1.5">
                        <Cpu className="h-3.5 w-3.5 text-slate-500" />
                        <span>Synthesized via {res.model_version}</span>
                      </div>
                      <span>{res.citations.length} cited document source{res.citations.length > 1 ? 's' : ''}</span>
                    </div>
                  </div>
                )}

                {/* ── Insufficient Evidence Outcome ─────────────── */}
                {isInsufficient && (
                  <div className="space-y-3" id="qa-insufficient-evidence-outcome">
                    <div className="p-4 rounded-xl border border-blue-500/30 bg-blue-500/10 text-blue-300 text-xs flex items-start gap-3">
                      <Info className="h-5 w-5 text-blue-400 shrink-0 mt-0.5" />
                      <div className="space-y-1">
                        <p className="font-semibold text-blue-200 text-sm">
                          Insufficient Case Evidence
                        </p>
                        <p className="text-blue-300/90 leading-relaxed text-xs">
                          The case evidence does not contain sufficient verified information to answer this question reliably. No speculative assertions were generated.
                        </p>
                      </div>
                    </div>

                    {/* Related Candidate Evidence Available for Inspection */}
                    {hasEvidenceItems && (
                      <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3 space-y-2">
                        <button
                          type="button"
                          onClick={() => toggleSection(`evidence-${exchange.id}`)}
                          className="w-full flex items-center justify-between text-xs font-semibold text-slate-300 hover:text-slate-100 transition-colors cursor-pointer"
                        >
                          <span className="flex items-center gap-1.5">
                            <span>Related evidence available but insufficient</span>
                            <Badge variant="outline" size="xs">
                              {res?.retrieved_evidence.length} chunks
                            </Badge>
                          </span>
                          {isRelatedEvidenceExpanded ? (
                            <ChevronUp className="h-4 w-4 text-slate-400" />
                          ) : (
                            <ChevronDown className="h-4 w-4 text-slate-400" />
                          )}
                        </button>

                        {isRelatedEvidenceExpanded && (
                          <div className="space-y-2 pt-2 border-t border-slate-800/60">
                            {res?.retrieved_evidence.map((candidate, cIdx) => (
                              <CitationCard
                                key={candidate.chunk_id || cIdx}
                                item={candidate}
                              />
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* ── Suppressed Outcome ────────────────────────── */}
                {isSuppressed && (
                  <div className="space-y-3" id="qa-suppressed-outcome">
                    <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-300 text-xs flex items-start gap-3">
                      <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
                      <div className="space-y-1">
                        <p className="font-semibold text-amber-200 text-sm">
                          Answer Withheld: Grounding Verification Failed
                        </p>
                        <p className="text-amber-300/90 leading-relaxed text-xs">
                          An answer was drafted but withheld to prevent potentially ungrounded or speculative claims from entering the legal record.
                        </p>
                      </div>
                    </div>

                    {/* Diagnostics Details */}
                    {res?.grounding_diagnostics.failure_reason && (
                      <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3 space-y-2">
                        <button
                          type="button"
                          onClick={() => toggleSection(`diag-${exchange.id}`)}
                          className="w-full flex items-center justify-between text-xs font-semibold text-slate-300 hover:text-slate-100 transition-colors cursor-pointer"
                        >
                          <span>Verification Diagnostics</span>
                          {isDiagnosticsExpanded ? (
                            <ChevronUp className="h-4 w-4 text-slate-400" />
                          ) : (
                            <ChevronDown className="h-4 w-4 text-slate-400" />
                          )}
                        </button>

                        {isDiagnosticsExpanded && (
                          <div className="pt-2 border-t border-slate-800/60 text-xs font-mono text-slate-400 bg-slate-950/80 p-2.5 rounded-lg overflow-x-auto">
                            <p className="text-amber-400 font-semibold mb-1">
                              Reason: {res.grounding_diagnostics.failure_reason}
                            </p>
                            {res.grounding_diagnostics.details && (
                              <pre className="text-[11px] text-slate-500 whitespace-pre-wrap">
                                {JSON.stringify(res.grounding_diagnostics.details, null, 2)}
                              </pre>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* ── Error Outcome ─────────────────────────────── */}
                {exchange.error && (
                  <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-300 text-xs flex items-start gap-3">
                    <AlertCircle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
                    <div className="space-y-1">
                      <p className="font-semibold text-rose-200 text-sm">
                        {exchange.error.status === 429
                          ? 'Rate Limit Active'
                          : exchange.error.status === 503
                          ? 'AI Service Temporarily Unavailable'
                          : exchange.error.status === 403
                          ? 'Access Denied'
                          : 'Inquiry Error'}
                      </p>
                      <p className="text-rose-300/90 leading-relaxed text-xs">
                        {exchange.error.message}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
