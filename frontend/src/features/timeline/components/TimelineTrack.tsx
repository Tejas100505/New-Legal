import { useMemo } from 'react';
import type { TimelineEvent } from '@/types';
import { TimelineEventCard } from './TimelineEventCard';
import { useTimelineStore } from '../store/timelineStore';
import { Calendar } from 'lucide-react';

interface TimelineTrackProps {
  events: TimelineEvent[];
}

export function TimelineTrack({ events }: TimelineTrackProps) {
  const selectedEventId = useTimelineStore((s) => s.selectedEventId);
  const selectEvent = useTimelineStore((s) => s.selectEvent);

  // Group events by Month & Year for timeline milestones
  const groupedEvents = useMemo(() => {
    const groups: Record<string, TimelineEvent[]> = {};
    
    events.forEach((evt) => {
      const date = new Date(evt.timestamp);
      const monthYear = date.toLocaleString('default', { month: 'long', year: 'numeric' });
      
      if (!groups[monthYear]) {
        groups[monthYear] = [];
      }
      groups[monthYear].push(evt);
    });

    return Object.entries(groups);
  }, [events]);

  return (
    <div className="flex-1 flex flex-col gap-6">
      {groupedEvents.map(([monthYear, groupEvents]) => (
        <div key={monthYear} className="flex flex-col gap-4 relative">
          {/* Milestone Sticky Header */}
          <div className="sticky top-0 z-10 flex items-center gap-2 bg-slate-950/80 backdrop-blur-md py-2 border-b border-slate-900">
            <Calendar className="h-4 w-4 text-indigo-400" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
              {monthYear}
            </h3>
            <span className="text-[10px] text-slate-500 font-mono">
              ({groupEvents.length} {groupEvents.length === 1 ? 'event' : 'events'})
            </span>
          </div>

          {/* Cards List */}
          <div className="relative pl-1">
            {groupEvents.map((evt, idx) => (
              <TimelineEventCard
                key={evt.id}
                event={evt}
                isSelected={selectedEventId === evt.id}
                onSelect={() => selectEvent(evt.id)}
                index={idx}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
