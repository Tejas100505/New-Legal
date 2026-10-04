import { useState } from 'react';
import { Badge } from '@/components/atoms/Badge';
import { Brain, FileText, AlertCircle, CheckCircle2, Bookmark, Info } from 'lucide-react';

interface SummaryPanelProps {
  doc?: any;
}

export function SummaryPanel({ doc }: SummaryPanelProps) {
  const [activeType, setActiveType] = useState<'executive' | 'legal' | 'evidence' | 'clause'>('executive');

  const getScoresArray = (val: any): number[] => {
    if (!val) return [];
    if (Array.isArray(val)) return val;
    if (typeof val === 'object') return Object.values(val).map(Number).filter((n) => !isNaN(n));
    return [];
  };

  const summaries: any[] = doc?.doc_metadata?.summaries || [];
  const semanticScores = getScoresArray(doc?.doc_metadata?.semantic_similarity_scores);
  const lexicalScores = getScoresArray(doc?.doc_metadata?.lexical_similarity_scores);

  // If no summaries array in doc_metadata, show honest notice
  if (!summaries || summaries.length === 0) {
    return (
      <div className="flex flex-col gap-3 text-left p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200">
        <div className="flex items-center gap-2">
          <AlertCircle className="h-5 w-5 text-amber-400 shrink-0" />
          <h4 className="text-xs font-bold uppercase tracking-wider text-amber-300">Initial Analysis Version</h4>
        </div>
        <p className="text-xs leading-relaxed text-amber-200/90">
          This document was analyzed prior to multi-type summarization indexing. Structured multi-point summaries, citations, and relevance scores will be generated upon running an updated review.
        </p>
      </div>
    );
  }

  // Find summary matching active type (case-insensitive on both type and summary_type)
  const currentSummary = summaries.find((s: any) =>
    (s.type || s.summary_type || '').toLowerCase() === activeType.toLowerCase()
  ) || summaries[0];

  const summaryText = currentSummary?.content || currentSummary?.text || '';

  const avgSemanticScore = semanticScores.length > 0
    ? (semanticScores.reduce((a, b) => a + b, 0) / semanticScores.length)
    : null;
  const avgLexicalScore = lexicalScores.length > 0
    ? (lexicalScores.reduce((a, b) => a + b, 0) / lexicalScores.length)
    : null;

  const summaryTypes: { id: 'executive' | 'legal' | 'evidence' | 'clause'; label: string; desc: string }[] = [
    { id: 'executive', label: 'Executive', desc: 'Concise overall understanding & context' },
    { id: 'legal', label: 'Legal', desc: 'Regulatory compliance & exposure analysis' },
    { id: 'evidence', label: 'Evidence', desc: 'Factual evidentiary findings & records' },
    { id: 'clause', label: 'Clause', desc: 'Contractual terms, covenants & provisions' },
  ];

  return (
    <div className="flex flex-col gap-4 text-left">
      {/* Similarity & Grounding Header */}
      <div className="grid grid-cols-2 gap-2 bg-slate-950/40 p-3 rounded-lg border border-slate-850">
        <div className="flex flex-col">
          <span className="text-[10px] text-slate-400 flex items-center gap-1">
            <Brain className="h-3 w-3 text-violet-400" /> Conceptual Relevance
          </span>
          <span className="text-xs font-mono font-bold text-violet-400 mt-0.5">
            {avgSemanticScore !== null ? `${(avgSemanticScore * 100).toFixed(1)}%` : '—'}
          </span>
        </div>
        <div className="flex flex-col">
          <span className="text-[10px] text-slate-400 flex items-center gap-1">
            <Bookmark className="h-3 w-3 text-cyan-400" /> Direct Keyword Match
          </span>
          <span className="text-xs font-mono font-bold text-cyan-400 mt-0.5">
            {avgLexicalScore !== null ? `${(avgLexicalScore * 100).toFixed(1)}%` : '—'}
          </span>
        </div>
      </div>

      {/* 4 Summary Type Switcher */}
      <div className="flex bg-slate-900 border border-slate-800 rounded-lg p-1 gap-1">
        {summaryTypes.map((st) => {
          const hasData = summaries.some(
            (s) => (s.type || s.summary_type || '').toLowerCase() === st.id.toLowerCase()
          );
          const active = activeType === st.id;
          return (
            <button
              key={st.id}
              id={`summary-type-${st.id}`}
              onClick={() => setActiveType(st.id)}
              className={`flex-1 py-1.5 px-2 rounded text-[11px] font-semibold transition-all ${
                active
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : hasData
                  ? 'text-slate-300 hover:text-white hover:bg-slate-800'
                  : 'text-slate-600 opacity-60'
              }`}
              title={st.desc}
            >
              {st.label}
            </button>
          );
        })}
      </div>

      {/* Active Summary Content */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
            <FileText className="h-3.5 w-3.5 text-indigo-400" />
            {activeType.charAt(0).toUpperCase() + activeType.slice(1)} Summary
          </h4>
          {currentSummary?.grounding_verified && (
            <Badge variant="success" size="xs" className="flex items-center gap-1">
              <CheckCircle2 className="h-2.5 w-2.5" /> Grounded
            </Badge>
          )}
        </div>

        {summaryText ? (
          <div className="text-xs text-slate-200 leading-relaxed bg-slate-900/60 p-4 rounded-xl border border-slate-800 whitespace-pre-wrap font-sans">
            {summaryText}
          </div>
        ) : currentSummary?.uncertainty ? null : (
          <div className="text-xs text-slate-500 italic p-4 bg-slate-900/30 rounded-xl border border-slate-800">
            No summary content generated for {activeType}.
          </div>
        )}

        {/* Explicit Statement of Uncertainty */}
        {currentSummary?.uncertainty && (
          <div className="flex items-start gap-2.5 p-3 rounded-lg bg-slate-900/80 border border-slate-800 text-slate-400 text-xs">
            <Info className="h-4 w-4 text-cyan-400 shrink-0 mt-0.5" />
            <div className="leading-relaxed">
              <span className="font-semibold text-slate-300 block mb-0.5">Grounding Analysis Note:</span>
              {currentSummary.uncertainty}
            </div>
          </div>
        )}
      </div>

      {/* Grounded Source Citations */}
      <div className="flex flex-col gap-2">
        <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          Source Citations ({currentSummary?.citations?.length || 0})
        </h4>
        {currentSummary?.citations && currentSummary.citations.length > 0 ? (
          <ul className="flex flex-col gap-1.5 text-xs text-slate-300">
            {currentSummary.citations.map((citation: string, idx: number) => (
              <li
                key={idx}
                className="bg-slate-950/70 p-2.5 rounded-lg border border-slate-800/80 font-mono text-[11px] text-indigo-300 flex items-start gap-2"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 shrink-0 mt-1.5" />
                <span className="break-all">{citation}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-slate-500 italic p-3 bg-slate-950/30 rounded-lg border border-slate-850">
            No source citation available.
          </p>
        )}
      </div>
    </div>
  );
}
