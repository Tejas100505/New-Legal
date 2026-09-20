import { useState } from 'react';
import { PageShell } from '@/components/templates/PageShell';
import { useTimelineStore } from '../store/timelineStore';
import { TimelineFilterBar } from '../components/TimelineFilterBar';
import { TimelineTrack } from '../components/TimelineTrack';
import { TimelineMinimap } from '../components/TimelineMinimap';
import { TimelineEventDetail } from '../components/TimelineEventDetail';
import { Badge } from '@/components/atoms/Badge';
import { CalendarClock, Search } from 'lucide-react';

import { useEffect } from 'react';

export function TimelinePage() {
  const events = useTimelineStore((s) => s.events);
  const filters = useTimelineStore((s) => s.filters);
  const fetchTimeline = useTimelineStore((s) => s.fetchTimeline);
  const source = useTimelineStore((s) => s.source);

  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    fetchTimeline(filters.caseId);
  }, [fetchTimeline, filters.caseId]);

  // 7 Filter Dimensions matching
  const filteredEvents = events.filter((e) => {
    // 1. Keyword search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      const matchesText = 
        e.title.toLowerCase().includes(query) || 
        e.description.toLowerCase().includes(query) ||
        (e.entityNames && e.entityNames.some((ent) => ent.toLowerCase().includes(query)));
      if (!matchesText) return false;
    }

    // 2. Case filter
    if (filters.caseId && e.caseId !== filters.caseId) return false;

    // 3. Priority filter
    if (filters.priority && e.priority !== filters.priority) return false;

    // 4. Lead Counsel (Lawyer) filter
    if (filters.lawyerName && e.lawyerName !== filters.lawyerName) return false;

    // 5. Related Entity filter
    if (filters.entityName && (!e.entityNames || !e.entityNames.includes(filters.entityName))) return false;

    // 6. Evidence Document (Document) filter
    if (filters.documentId && e.documentId !== filters.documentId) return false;

    // 7. Evidence ID filter
    if (filters.evidenceId && e.evidenceId !== filters.evidenceId) return false;

    // 8. Date Range filter
    if (filters.dateRange?.start) {
      const start = new Date(filters.dateRange.start).getTime();
      const evtTime = new Date(e.timestamp).getTime();
      if (evtTime < start) return false;
    }
    if (filters.dateRange?.end) {
      const end = new Date(filters.dateRange.end).getTime();
      const evtTime = new Date(e.timestamp).getTime();
      if (evtTime > end) return false;
    }

    // Type category filter (multiple choice)
    if (filters.categories && filters.categories.length > 0 && e.type && !filters.categories.includes(e.type)) {
      return false;
    }

    return true;
  });

  // Sort events chronologically
  const sortedEvents = [...filteredEvents].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  return (
    <PageShell
      title="Interactive Chronological Audit Timeline"
      description="Chronological event audit trail. Track emails, payments, contract signings, OCR discoveries, and AI legal decisions across matters."
      fullWidth
    >
      <div className="flex flex-col gap-4 h-[calc(100vh-12rem)]">
        {/* Filter Engine */}
        <div className="flex flex-col gap-3">
          {/* Quick Search and Top Controls */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-slate-900/50 backdrop-blur-xl border border-slate-800/80 rounded-xl">
            <div className="relative flex-1 max-w-xs">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search audit trail..."
                className="w-full pl-10 pr-4 py-2 rounded-lg bg-slate-800/60 border border-slate-700/50 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 transition-all"
              />
            </div>
            
            <div className="flex items-center gap-2">
              <Badge variant={source === 'live' ? 'success' : 'warning'} size="sm">
                {source === 'live' ? '● Live DB Data' : '▲ Demo Fallback'}
              </Badge>
              <Badge variant="info" size="sm">
                {sortedEvents.length} Events Logged
              </Badge>
            </div>
          </div>

          <TimelineFilterBar />
        </div>

        {/* Timeline Minimap Density Ruler */}
        <TimelineMinimap events={sortedEvents} />

        <div className="flex-1 flex gap-4 min-h-0">
          {/* Chronological Scrollable Track */}
          <div className="flex-1 rounded-xl border border-slate-800/80 bg-slate-950 p-6 overflow-y-auto min-h-0">
            {sortedEvents.length > 0 ? (
              <div className="max-w-2xl mx-auto py-4 relative">
                {/* Visual timeline central bar */}
                <div className="absolute left-[20px] top-4 bottom-4 w-0.5 bg-slate-800/80" />

                <TimelineTrack events={sortedEvents} />
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center text-center gap-2 h-full py-20 text-slate-500">
                <CalendarClock className="h-10 w-10 text-slate-700" />
                <p className="text-sm font-semibold">No Timeline Events Found</p>
                <p className="text-xs text-slate-600 max-w-[240px]">
                  No events match the active search parameters or filters. Modify filters or reset the filter engine.
                </p>
              </div>
            )}
          </div>

          {/* Right Panel Event detail view */}
          <TimelineEventDetail />
        </div>
      </div>
    </PageShell>
  );
}
