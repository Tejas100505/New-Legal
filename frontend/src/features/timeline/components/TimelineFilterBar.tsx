import { useTimelineStore } from '../store/timelineStore';
import { Filter, RotateCcw, Calendar, ShieldAlert, FileText, User, Link2 } from 'lucide-react';
import type { TimelinePriority } from '@/types';

interface TimelineFilterBarProps {
  hideCaseSelector?: boolean;
}

export function TimelineFilterBar({ hideCaseSelector = false }: TimelineFilterBarProps = {}) {
  const filters = useTimelineStore((s) => s.filters);
  const setFilters = useTimelineStore((s) => s.setFilters);
  const resetFilters = useTimelineStore((s) => s.resetFilters);
  const events = useTimelineStore((s) => s.events) as any[];

  // Extract filter dimensions from events
  const uniqueCases = Array.from(new Set(events.map((e) => e.caseId).filter(Boolean))).map((id) => {
    return { id, name: events.find((e) => e.caseId === id)?.caseName || id };
  });

  const uniqueLawyers = Array.from(
    new Set(events.map((e) => e.lawyerName).filter(Boolean))
  ) as string[];

  const uniqueEntities = Array.from(
    new Set(events.flatMap((e) => e.entityNames || []).filter(Boolean))
  ) as string[];

  const uniqueDocuments = Array.from(
    new Set(events.map((e) => e.documentName).filter(Boolean))
  ).map((name) => {
    return { name, id: events.find((e) => e.documentName === name)?.documentId || name };
  });

  const uniqueEvidences = Array.from(
    new Set(events.map((e) => e.evidenceId).filter(Boolean))
  ) as string[];

  return (
    <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/80 rounded-xl p-4 flex flex-col gap-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-indigo-400" />
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">Timeline Filter Engine</span>
        </div>
        <button 
          onClick={resetFilters}
          className="flex items-center gap-1 text-[10px] text-slate-500 hover:text-slate-300 transition-colors"
        >
          <RotateCcw className="h-3 w-3" /> Reset Filters
        </button>
      </div>

      <div className={`grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 ${hideCaseSelector ? 'lg:grid-cols-6' : 'lg:grid-cols-7'} gap-3`}>
        {/* 1. Case Filter */}
        {!hideCaseSelector && (
          <div className="flex flex-col gap-1" id="timeline-case-selector">
            <label className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">Matter</label>
            <select
              value={filters.caseId || ''}
              onChange={(e) => setFilters({ caseId: e.target.value || null })}
              className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-2 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
            >
              <option key="all-cases" value="">All Cases</option>
              {uniqueCases.map((c, idx) => (
                <option key={`case-${c.id ?? idx}-${idx}`} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
        )}

        {/* 2. Priority Filter */}
        <div className="flex flex-col gap-1">
          <label className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider flex items-center gap-1">
            <ShieldAlert className="h-3 w-3 text-rose-400" /> Priority
          </label>
          <select
            value={filters.priority || ''}
            onChange={(e) => setFilters({ priority: (e.target.value as TimelinePriority) || null })}
            className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-2 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
          >
            <option key="all-priorities" value="">All Priorities</option>
            <option key="priority-critical" value="critical">Critical</option>
            <option key="priority-high" value="high">High</option>
            <option key="priority-medium" value="medium">Medium</option>
            <option key="priority-low" value="low">Low</option>
          </select>
        </div>

        {/* 3. Lawyer Filter */}
        <div className="flex flex-col gap-1">
          <label className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider flex items-center gap-1">
            <User className="h-3 w-3 text-indigo-400" /> Lead Counsel
          </label>
          <select
            value={filters.lawyerName || ''}
            onChange={(e) => setFilters({ lawyerName: e.target.value || null })}
            className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-2 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
          >
            <option key="all-counsel" value="">All Counsel</option>
            {uniqueLawyers.map((l, idx) => (
              <option key={`lawyer-${l}-${idx}`} value={l}>{l}</option>
            ))}
          </select>
        </div>

        {/* 4. Related Entity Filter */}
        <div className="flex flex-col gap-1">
          <label className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">Related Entity</label>
          <select
            value={filters.entityName || ''}
            onChange={(e) => setFilters({ entityName: e.target.value || null })}
            className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-2 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
          >
            <option key="all-entities" value="">All Entities</option>
            {uniqueEntities.map((ent, idx) => (
              <option key={`ent-${ent}-${idx}`} value={ent}>{ent}</option>
            ))}
          </select>
        </div>

        {/* 5. Document Filter */}
        <div className="flex flex-col gap-1">
          <label className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider flex items-center gap-1">
            <FileText className="h-3 w-3 text-cyan-400" /> Evidence Doc
          </label>
          <select
            value={filters.documentId || ''}
            onChange={(e) => setFilters({ documentId: e.target.value || null })}
            className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-2 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
          >
            <option key="all-docs" value="">All Documents</option>
            {uniqueDocuments.map((doc, idx) => (
              <option key={`doc-${doc.id ?? idx}-${idx}`} value={doc.id}>{doc.name}</option>
            ))}
          </select>
        </div>

        {/* 6. Evidence Filter */}
        <div className="flex flex-col gap-1">
          <label className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider flex items-center gap-1">
            <Link2 className="h-3 w-3 text-orange-400" /> Evidence ID
          </label>
          <select
            value={filters.evidenceId || ''}
            onChange={(e) => setFilters({ evidenceId: e.target.value || null })}
            className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-2 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
          >
            <option key="all-evidence" value="">All Evidence</option>
            {uniqueEvidences.map((ev, idx) => (
              <option key={`ev-${ev}-${idx}`} value={ev}>{ev}</option>
            ))}
          </select>
        </div>

        {/* 7. Date Range Filter */}
        <div className="flex flex-col gap-1">
          <label className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider flex items-center gap-1">
            <Calendar className="h-3 w-3 text-emerald-400" /> Date Start/End
          </label>
          <div className="flex items-center gap-1">
            <input
              type="date"
              value={filters.dateRange?.start || ''}
              onChange={(e) => setFilters({ dateRange: { start: e.target.value, end: filters.dateRange?.end || '' } })}
              className="w-1/2 bg-slate-800/50 border border-slate-700/50 rounded-lg p-1.5 text-[10px] text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
            />
            <input
              type="date"
              value={filters.dateRange?.end || ''}
              onChange={(e) => setFilters({ dateRange: { start: filters.dateRange?.start || '', end: e.target.value } })}
              className="w-1/2 bg-slate-800/50 border border-slate-700/50 rounded-lg p-1.5 text-[10px] text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
