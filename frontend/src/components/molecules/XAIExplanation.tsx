import { BrainCircuit, Clock, Server, CheckCircle, AlertTriangle, Link2, GitCommit, PlayCircle } from 'lucide-react';
import { Badge } from '@/components/atoms/Badge';

export interface XAIData {
  confidence: number;
  model: string;
  promptVersion: string;
  executionTimeMs: number;
  hallucinationRisk: 'low' | 'medium' | 'high';
  reviewRecommendation: 'auto-accept' | 'manual-review' | 'flagged';
  reasoningTrail: { step: number; title: string; desc: string }[];
  retrievedChunks: { id: string; text: string; relevance: number }[];
  evidenceLinks: string[];
  citations: { text: string; source: string }[];
}

export function XAIExplanation({ data }: { data: XAIData }) {
  return (
    <div className="flex flex-col gap-4">
      {/* Overview Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-800 flex flex-col gap-1">
          <span className="text-[10px] text-slate-500 uppercase font-bold flex items-center gap-1"><BrainCircuit className="h-3 w-3"/> Confidence</span>
          <span className="text-lg font-bold text-slate-200">{(data.confidence * 100).toFixed(1)}%</span>
        </div>
        <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-800 flex flex-col gap-1">
          <span className="text-[10px] text-slate-500 uppercase font-bold flex items-center gap-1"><Server className="h-3 w-3"/> Model Used</span>
          <span className="text-sm font-semibold text-slate-300 mt-1">{data.model}</span>
        </div>
        <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-800 flex flex-col gap-1">
          <span className="text-[10px] text-slate-500 uppercase font-bold flex items-center gap-1"><GitCommit className="h-3 w-3"/> Review Rubric</span>
          <span className="text-sm font-semibold text-slate-300 mt-1">{data.promptVersion}</span>
        </div>
        <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-800 flex flex-col gap-1">
          <span className="text-[10px] text-slate-500 uppercase font-bold flex items-center gap-1"><Clock className="h-3 w-3"/> Exec Time</span>
          <span className="text-sm font-semibold text-slate-300 mt-1">{data.executionTimeMs}ms</span>
        </div>
      </div>

      {/* Verification & Recommendations */}
      <div className="flex items-center gap-3">
        {data.hallucinationRisk === 'low' ? (
          <Badge variant="success" className="flex items-center gap-1"><CheckCircle className="h-3 w-3"/> Hallucination Checked</Badge>
        ) : (
          <Badge variant="warning" className="flex items-center gap-1"><AlertTriangle className="h-3 w-3"/> Risk: {data.hallucinationRisk}</Badge>
        )}
        <Badge variant={data.reviewRecommendation === 'auto-accept' ? 'success' : 'info'} className="flex items-center gap-1">
          <PlayCircle className="h-3 w-3"/> {data.reviewRecommendation === 'auto-accept' ? 'Routine (No Action Needed)' : 'Attorney Review Recommended'}
        </Badge>
      </div>

      {/* Reasoning Trail */}
      <div className="bg-slate-900/50 rounded-xl border border-slate-800 p-4">
        <h4 className="text-xs font-bold text-indigo-400 mb-3 uppercase tracking-wider">Reasoning Trail</h4>
        <div className="space-y-3 relative before:absolute before:inset-0 before:ml-2.5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-700 before:to-transparent">
          {data.reasoningTrail.map((step, idx) => (
            <div key={idx} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
              <div className="flex items-center justify-center w-5 h-5 rounded-full border border-indigo-500 bg-indigo-500/20 text-[10px] font-bold text-indigo-300 shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 shadow">
                {step.step}
              </div>
              <div className="w-[calc(100%-2.5rem)] md:w-[calc(50%-2.5rem)] p-3 rounded-lg border border-slate-800 bg-slate-950/50">
                <h5 className="font-semibold text-slate-300 text-xs">{step.title}</h5>
                <p className="text-[11px] text-slate-500 mt-1">{step.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Retrieved Chunks & Citations */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-slate-900/50 rounded-xl border border-slate-800 p-4">
          <h4 className="text-xs font-bold text-slate-400 mb-3 uppercase tracking-wider">Retrieved Chunks</h4>
          <div className="space-y-2">
            {data.retrievedChunks.map(chunk => (
              <div key={chunk.id} className="p-2 bg-slate-950 rounded border border-slate-800/80">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-[10px] font-mono text-indigo-400">{chunk.id}</span>
                  <span className="text-[10px] text-emerald-400">{Math.round(chunk.relevance * 100)}% Match</span>
                </div>
                <p className="text-[11px] text-slate-400 line-clamp-2">"{chunk.text}"</p>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-slate-900/50 rounded-xl border border-slate-800 p-4">
          <h4 className="text-xs font-bold text-slate-400 mb-3 uppercase tracking-wider flex items-center gap-2">
            Evidence & Citations
          </h4>
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2">
              {data.evidenceLinks.map((link, idx) => (
                <Badge key={idx} variant="outline" size="xs" className="flex items-center gap-1">
                  <Link2 className="h-3 w-3" /> {link}
                </Badge>
              ))}
            </div>
            <div className="space-y-2 mt-3">
              {data.citations.map((cit, idx) => (
                <div key={idx} className="text-[11px] text-slate-400 p-2 bg-slate-950 rounded border border-slate-800/80">
                  <span className="font-bold text-slate-300">{cit.source}:</span> "{cit.text}"
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
