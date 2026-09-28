import { MessageSquare, Sparkles, ShieldCheck, ArrowRight } from 'lucide-react';

interface QAEmptyStateProps {
  caseName?: string;
  onSelectQuestion: (question: string) => void;
}

const SAMPLE_QUESTIONS = [
  {
    title: 'Clean Air Act Defense',
    question: 'What defense did outside counsel assert regarding the opacity intervals exceeding permit thresholds?',
    category: 'Regulatory Defense',
  },
  {
    title: 'Trading Performance',
    question: 'What financial performance figures did Pam achieve during her prior three-year tenure running the trading book at TXU?',
    category: 'Financial Evidence',
  },
  {
    title: 'Hourly Scheduling',
    question: 'What was the WAPA hourly balanced schedule requirement as of October 28th?',
    category: 'Operational Records',
  },
  {
    title: 'Market Inquiry Overview',
    question: 'What were the core inquiries and regulatory concerns regarding California energy trading practices?',
    category: 'Inquiry Scope',
  },
];

export function QAEmptyState({ caseName, onSelectQuestion }: QAEmptyStateProps) {
  return (
    <div id="qa-empty-state" className="p-8 rounded-2xl border border-slate-800/80 bg-slate-900/40 text-center max-w-3xl mx-auto space-y-6">
      <div className="relative inline-flex items-center justify-center">
        <div className="h-14 w-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
          <MessageSquare className="h-7 w-7" />
        </div>
        <div className="absolute -top-1 -right-1 h-6 w-6 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
          <ShieldCheck className="h-3.5 w-3.5" />
        </div>
      </div>

      <div className="space-y-2 max-w-lg mx-auto">
        <h3 className="text-lg font-bold text-slate-100 tracking-tight">
          Grounded Evidence Intelligence
        </h3>
        <p className="text-xs text-slate-400 leading-relaxed">
          {caseName ? `Inquire directly into the evidence record for ${caseName}. ` : 'Query the case record with full evidentiary grounding. '}
          Answers are strictly tied to cited document chunks and verified through deterministic citation and token overlap gates.
        </p>
      </div>

      {/* Suggested Inquiries */}
      <div className="pt-2 text-left space-y-3">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-400 uppercase tracking-wider px-1">
          <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
          <span>Suggested Inquiries</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {SAMPLE_QUESTIONS.map((sample, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => onSelectQuestion(sample.question)}
              className="p-3 rounded-xl border border-slate-800 hover:border-indigo-500/40 bg-slate-950/40 hover:bg-slate-900/80 text-left transition-all duration-150 group cursor-pointer flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between gap-1 mb-1">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-indigo-400">
                    {sample.category}
                  </span>
                  <ArrowRight className="h-3 w-3 text-slate-600 group-hover:text-indigo-400 transition-colors shrink-0" />
                </div>
                <p className="text-xs font-medium text-slate-200 group-hover:text-indigo-200 transition-colors line-clamp-2">
                  {sample.question}
                </p>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
