import { Link } from 'react-router-dom';
import { FileText, ExternalLink, Hash, BookOpen } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { CitationItem } from '../hooks/useCaseAsk';

interface CitationCardProps {
  item: CitationItem;
  label?: string;
  highlighted?: boolean;
  className?: string;
}

export function CitationCard({ item, label, highlighted = false, className }: CitationCardProps) {
  const cardId = label ? `citation-card-${label.replace(/[[\]]/g, '')}` : `citation-card-${item.chunk_id}`;

  return (
    <div
      id={cardId}
      tabIndex={-1}
      className={cn(
        'group relative p-3.5 rounded-xl border transition-all duration-300',
        highlighted
          ? 'bg-indigo-950/30 border-indigo-500/60 ring-2 ring-indigo-500/40 shadow-lg shadow-indigo-500/10'
          : 'bg-slate-900/60 border-slate-800/80 hover:border-slate-700/80 hover:bg-slate-900/80',
        className
      )}
    >
      {/* Header with Label, Filename link, and Metadata */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          {label && (
            <span className="font-mono text-xs font-bold text-indigo-400 bg-indigo-500/15 border border-indigo-500/30 px-2 py-0.5 rounded shrink-0">
              {label}
            </span>
          )}

          <Link
            to={`/documents/${item.document_id}`}
            title={`View source document: ${item.filename}`}
            className="flex items-center gap-1.5 text-xs font-semibold text-slate-200 hover:text-indigo-300 transition-colors truncate max-w-[280px] sm:max-w-[360px]"
          >
            <FileText className="h-3.5 w-3.5 text-slate-400 shrink-0 group-hover:text-indigo-400 transition-colors" />
            <span className="truncate">{item.filename}</span>
            <ExternalLink className="h-3 w-3 opacity-0 group-hover:opacity-100 text-indigo-400 transition-opacity shrink-0" />
          </Link>
        </div>

        {/* Section and Page Tags */}
        <div className="flex items-center gap-1.5 text-[10px] text-slate-400">
          {item.section && item.section !== 'unavailable' && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-800/70 border border-slate-700/50 font-mono">
              <Hash className="h-2.5 w-2.5 text-slate-500" />
              <span className="truncate max-w-[120px]">{item.section}</span>
            </span>
          )}
          {item.page !== undefined && item.page !== null && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-800/70 border border-slate-700/50 font-mono">
              <BookOpen className="h-2.5 w-2.5 text-slate-500" />
              <span>Page {item.page}</span>
            </span>
          )}
        </div>
      </div>

      {/* Verified Excerpt Block */}
      <blockquote className="text-xs text-slate-300 font-serif leading-relaxed italic border-l-2 border-indigo-500/40 pl-3 py-1 bg-slate-950/40 rounded-r mt-2">
        "{item.excerpt}"
      </blockquote>
    </div>
  );
}
