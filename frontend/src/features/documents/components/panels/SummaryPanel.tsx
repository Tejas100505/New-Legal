import { useState } from 'react';
import { Badge } from '@/components/atoms/Badge';
import { Brain, FileText, AlertCircle, CheckCircle2, Bookmark } from 'lucide-react';

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
  const entities = doc?.extractedEntities || doc?.doc_metadata?.entities || [];

  // Stale Document Handling: Document processed prior to current multi-type summarization model
  if (!summaries || summaries.length === 0) {
    return (
      <div className="flex flex-col gap-3 text-left p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200">
        <div className="flex items-center gap-2">
          <AlertCircle className="h-5 w-5 text-amber-400 shrink-0" />
          <h4 className="text-xs font-bold uppercase tracking-wider text-amber-300">Initial Analysis Version</h4>
        </div>
        <p className="text-xs leading-relaxed text-amber-200/90">
          This document was analyzed with an earlier analysis model. Structured multi-point summaries, citations, and relevance scores will be generated upon running an updated review.
        </p>
        <p className="text-[11px] text-amber-300/70">
          Select "Re-run Analysis" to generate executive, legal, evidence, and clause summaries.
        </p>
      </div>
    );
  }

  const currentSummary = summaries.find((s: any) =>
    (s.summary_type || s.type || '').toLowerCase() === activeType.toLowerCase()
  ) || summaries[0];
  const summaryText = currentSummary?.text || currentSummary?.content || 'No summary generated for this type.';

  const avgSemanticScore = semanticScores.length > 0
    ? (semanticScores.reduce((a, b) => a + b, 0) / semanticScores.length)
    : null;
  const avgLexicalScore = lexicalScores.length > 0
    ? (lexicalScores.reduce((a, b) => a + b, 0) / lexicalScores.length)
    : null;

  return (
    <div className="flex flex-col gap-4 text-left">
      {/* Similarity & Grounding Header */}
      <div className="grid grid-cols-2 gap-2 bg-slate-950/40 p-3 rounded-lg border border-slate-850">
        <div className="flex flex-col">
          <span className="text-[10px] text-slate-400 flex items-center gap-1">
            <Brain className="h-3 w-3 text-violet-400" /> Conceptual Relevance
          </span>
          <span className="text-xs font-mono font-bold text-violet-400 mt-0.5">
            {avgSemanticScore !== null ? `${(avgSemanticScore * 100).toFixed(1)}%` : 'N/A'}
          </span>
        </div>
        <div className="flex flex-col">
          <span className="text-[10px] text-slate-400 flex items-center gap-1">
            <Bookmark className="h-3 w-3 text-cyan-400" /> Direct Keyword Match
          </span>
          <span className="text-xs font-mono font-bold text-cyan-400 mt-0.5">
            {avgLexicalScore !== null ? `${(avgLexicalScore * 100).toFixed(1)}%` : 'N/A'}
          </span>
        </div>
      </div>

      {/* 4 Summary Type Switcher */}
      <div className="flex bg-slate-900 border border-slate-800 rounded-lg p-1 gap-1">
        {(['executive', 'legal', 'evidence', 'clause'] as const).map((type) => {
          const hasData = summaries.some((s) => s.summary_type === type);
          const active = activeType === type;
          return (
            <button
              key={type}
              onClick={() => setActiveType(type)}
              className={`flex-1 py-1 px-1.5 rounded text-[10px] font-semibold uppercase tracking-wider transition-all ${
                active
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : hasData
                  ? 'text-slate-400 hover:text-slate-200'
                  : 'text-slate-600 cursor-not-allowed opacity-50'
              }`}
            >
              {type}
            </button>
          );
        })}
      </div>

      {/* Active Summary Content */}
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
            <FileText className="h-3.5 w-3.5 text-indigo-400" />
            {activeType} Summary
          </h4>
          {currentSummary?.grounding_verified && (
            <Badge variant="success" size="xs" className="flex items-center gap-1">
              <CheckCircle2 className="h-2.5 w-2.5" /> Grounded
            </Badge>
          )}
        </div>
        <div className="text-xs text-slate-300 leading-relaxed bg-slate-900/40 p-3 rounded-lg border border-slate-850 whitespace-pre-wrap">
          {summaryText}
        </div>
      </div>

      {/* Grounded Citations */}
      {currentSummary?.citations && currentSummary.citations.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Source Citations ({currentSummary.citations.length})
          </h4>
          <ul className="flex flex-col gap-1 text-xs text-slate-300">
            {currentSummary.citations.map((citation: string, idx: number) => (
              <li
                key={idx}
                className="bg-slate-950/60 p-2 rounded border border-slate-800/80 font-mono text-[11px] text-indigo-300 flex items-start gap-2"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 shrink-0 mt-1.5" />
                <span className="break-all">{citation}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Extracted Entities if present */}
      {entities.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Extracted Entities</h4>
          <div className="grid grid-cols-2 gap-2">
            {entities.slice(0, 8).map((entity: any, idx: number) => (
              <div key={idx} className="p-2 rounded bg-slate-950/40 border border-slate-850 flex justify-between items-center text-xs">
                <span className="text-slate-300 truncate max-w-[100px]" title={entity.name || entity.text}>
                  {entity.name || entity.text}
                </span>
                <Badge variant="outline" size="xs">{entity.type}</Badge>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
