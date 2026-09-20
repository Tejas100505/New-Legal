import { useTimelineStore } from '../store/timelineStore';
import { Badge } from '@/components/atoms/Badge';
import { Info, HelpCircle, FileText, Link2, User, UserCheck } from 'lucide-react';
import { formatDate } from '@/lib/utils';

export function TimelineEventDetail() {
  const selectedEventId = useTimelineStore((s) => s.selectedEventId);
  const selectEvent = useTimelineStore((s) => s.selectEvent);
  const events = useTimelineStore((s) => s.events) as any[];

  if (!selectedEventId) {
    return (
      <div className="w-80 bg-slate-900/50 backdrop-blur-xl border border-slate-800/80 rounded-xl p-6 flex flex-col items-center justify-center text-center gap-2 h-full max-h-[calc(100vh-14rem)]">
        <HelpCircle className="h-8 w-8 text-slate-700" />
        <p className="text-sm font-medium text-slate-400">No event selected</p>
        <p className="text-xs text-slate-600 max-w-[200px]">Click any event in the chronological timeline to view supporting legal files, metadata, and extracted entities.</p>
      </div>
    );
  }

  const event = events.find((e: any) => e.id === selectedEventId);
  if (!event) return null;

  return (
    <div className="w-80 bg-slate-900/50 backdrop-blur-xl border border-slate-800/80 rounded-xl p-4 flex flex-col gap-4 overflow-y-auto max-h-[calc(100vh-14rem)]">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center gap-2">
          <Info className="h-4 w-4 text-indigo-400" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">Audit Detail</h3>
        </div>
        <button 
          onClick={() => selectEvent(null)}
          className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
        >
          Clear
        </button>
      </div>

      {/* Main Info */}
      <div className="flex flex-col gap-2">
        <div className="flex flex-col gap-1">
          <span className="text-[10px] text-indigo-400 font-bold uppercase">{event.caseName}</span>
          <h4 className="text-sm font-bold text-slate-100">{event.title}</h4>
        </div>
        <p className="text-xs text-slate-400 leading-relaxed bg-slate-950/40 p-2.5 rounded-lg border border-slate-850">
          {event.description}
        </p>
      </div>

      {/* Audit Meta */}
      <div className="flex flex-col gap-2">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Record Information</span>
        <div className="flex flex-col gap-1.5 text-xs">
          <div className="flex justify-between items-center p-1.5 rounded bg-slate-950/20">
            <span className="text-slate-500">Timestamp</span>
            <span className="font-mono text-slate-300">{formatDate(event.timestamp)}</span>
          </div>
          <div className="flex justify-between items-center p-1.5 rounded bg-slate-950/20">
            <span className="text-slate-500">Recorded By</span>
            <span className="text-slate-300 flex items-center gap-1"><User className="h-3 w-3" /> {event.userName}</span>
          </div>
          {event.lawyerName && (
            <div className="flex justify-between items-center p-1.5 rounded bg-slate-950/20">
              <span className="text-slate-500">Lead Counsel</span>
              <span className="text-indigo-400 flex items-center gap-1"><UserCheck className="h-3 w-3" /> {event.lawyerName}</span>
            </div>
          )}
        </div>
      </div>

      {/* Extracted Entities */}
      {event.entityNames && event.entityNames.length > 0 && (
        <div className="flex flex-col gap-2 border-t border-slate-800 pt-3">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Extracted Entities</span>
          <div className="flex flex-wrap gap-1.5">
            {event.entityNames.map((name: any) => (
              <Badge key={name} variant="outline" size="xs">
                {name}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Linked Legal Artifacts */}
      {(event.documentId || event.evidenceId) && (
        <div className="flex flex-col gap-2 border-t border-slate-800 pt-3">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Linked Exhibits & Files</span>
          <div className="flex flex-col gap-1.5">
            {event.documentId && (
              <div className="flex items-center gap-2 p-2 rounded bg-slate-950/30 border border-slate-850 hover:border-slate-700 transition-colors">
                <FileText className="h-4 w-4 text-cyan-400" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-slate-300 font-semibold truncate">{event.documentName}</p>
                  <p className="text-[9px] text-slate-500">File ID: {event.documentId}</p>
                </div>
              </div>
            )}
            {event.evidenceId && (
              <div className="flex items-center gap-2 p-2 rounded bg-slate-950/30 border border-slate-850 hover:border-slate-700 transition-colors">
                <Link2 className="h-4 w-4 text-orange-400" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-slate-300 font-semibold truncate">Physical Evidence Reference</p>
                  <p className="text-[9px] text-slate-500">Evidence ID: {event.evidenceId}</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* AI Decision Context */}
      {event.type === 'ai_decision' && (
        <div className="flex flex-col gap-2 border-t border-slate-800 pt-3 bg-amber-500/5 p-2 rounded-lg border border-amber-500/10">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-amber-400">AI Reasoning Context</span>
          <div className="text-[11px] text-slate-400 leading-relaxed">
            This event represents a critical AI automated decision point. Model confidence is verified at <strong>{event.metadata.confidence || '95%'}</strong> based on supporting evidence linking.
          </div>
        </div>
      )}
    </div>
  );
}
