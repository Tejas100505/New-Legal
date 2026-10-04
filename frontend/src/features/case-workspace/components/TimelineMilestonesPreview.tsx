import { Link } from 'react-router-dom';
import { History, Calendar, FileText, ArrowUpRight, ChevronRight, ExternalLink } from 'lucide-react';
import { Badge } from '@/components/atoms/Badge';

interface TimelineMilestonesPreviewProps {
  caseId: string;
  keyDates?: Array<{
    date: string;
    title: string;
    source_document?: string;
  }>;
  timelineSpan?: {
    total_events?: number;
    core_activity_start?: string;
    core_activity_end?: string;
  };
}

export function TimelineMilestonesPreview({
  caseId,
  keyDates = [],
  timelineSpan,
}: TimelineMilestonesPreviewProps) {
  const displayedDates = (keyDates || []).slice(0, 4);

  return (
    <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-5 backdrop-blur-sm space-y-4 shadow-sm" id="timeline-milestones-section">
      {/* ── Section Header ────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/60 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <History className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-slate-100">Evidentiary Timeline Milestones</h3>
              {timelineSpan?.total_events !== undefined && (
                <Badge variant="outline" size="xs">
                  {timelineSpan.total_events} Chronological Events
                </Badge>
              )}
            </div>
            <p className="text-[11px] text-slate-400">
              {timelineSpan?.core_activity_start
                ? `Core activity period: ${timelineSpan.core_activity_start} to ${timelineSpan.core_activity_end}`
                : 'Key historical dates identified across case communications'}
            </p>
          </div>
        </div>

        <Link
          to={`/cases/${caseId}/timeline`}
          className="text-xs text-indigo-400 hover:text-indigo-300 font-medium inline-flex items-center gap-1 transition-colors self-start sm:self-auto"
          id="timeline-milestones-open-full"
        >
          <span>Open Full Interactive Timeline</span>
          <ArrowUpRight className="h-3 w-3" />
        </Link>
      </div>

      {/* ── Content Grid or Empty State ────────────────────────────── */}
      {displayedDates.length === 0 ? (
        <div className="p-6 rounded-xl bg-slate-950/40 border border-slate-800 text-center space-y-3" id="timeline-milestones-empty">
          <Calendar className="h-6 w-6 text-slate-500 mx-auto" />
          <div className="space-y-1">
            <p className="text-xs font-semibold text-slate-300">No milestone dates synthesized</p>
            <p className="text-[11px] text-slate-500 max-w-md mx-auto">
              Chronological milestones are extracted during Case Intelligence Summary generation, or you can browse the raw timeline events directly.
            </p>
          </div>
          <Link
            to={`/cases/${caseId}/timeline`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors border border-slate-700/60"
          >
            <span>Open Timeline Track</span>
            <ChevronRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {displayedDates.map((item, idx) => (
              <div
                key={idx}
                className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700/90 transition-all flex flex-col justify-between gap-2 shadow-sm"
              >
                <div className="space-y-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-xs font-semibold text-emerald-400">
                      {item.date}
                    </span>
                    {item.source_document && (
                      <Link
                        to={`/cases/${caseId}/evidence`}
                        state={{ caseId, returnTab: 'overview' }}
                        className="inline-flex items-center gap-1 text-[11px] text-slate-400 hover:text-indigo-300 truncate max-w-[200px] transition-colors"
                        title={item.source_document}
                      >
                        <FileText className="h-3 w-3 shrink-0" />
                        <span className="truncate">{item.source_document}</span>
                        <ExternalLink className="h-2.5 w-2.5 shrink-0" />
                      </Link>
                    )}
                  </div>
                  <p className="text-xs text-slate-300 line-clamp-2 leading-relaxed">
                    {item.title}
                  </p>
                </div>
              </div>
            ))}
          </div>

          <div className="flex justify-between items-center text-xs text-slate-400 pt-1">
            <span className="text-[11px] text-slate-500">
              {timelineSpan?.total_events ? `${timelineSpan.total_events} events indexed across corpus` : 'Chronological span'}
            </span>
            <Link
              to={`/cases/${caseId}/timeline`}
              className="text-xs text-indigo-400 hover:text-indigo-300 font-medium inline-flex items-center gap-1"
            >
              <span>View full timeline track →</span>
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
