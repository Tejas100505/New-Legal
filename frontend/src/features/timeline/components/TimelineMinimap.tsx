import { useMemo } from 'react';
import type { TimelineEvent } from '@/types';
import { useTimelineStore } from '../store/timelineStore';
import { Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

interface TimelineMinimapProps {
  events: TimelineEvent[];
}

export function TimelineMinimap({ events }: TimelineMinimapProps) {
  const selectedEventId = useTimelineStore((s) => s.selectedEventId);
  const selectEvent = useTimelineStore((s) => s.selectEvent);

  const sorted = useMemo(() => {
    return [...events].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  }, [events]);

  const { minTime, maxTime, range } = useMemo(() => {
    if (sorted.length === 0) return { minTime: 0, maxTime: 0, range: 0 };
    const min = new Date(sorted[0].timestamp).getTime();
    const max = new Date(sorted[sorted.length - 1].timestamp).getTime();
    return { minTime: min, maxTime: max, range: max - min || 1 };
  }, [sorted]);

  const markers = useMemo(() => {
    return sorted.map((evt) => {
      const evtTime = new Date(evt.timestamp).getTime();
      const pct = ((evtTime - minTime) / range) * 100;
      return {
        id: evt.id,
        pct: Math.min(98, Math.max(2, pct)),
        type: evt.type,
        title: evt.title,
        priority: evt.priority,
      };
    });
  }, [sorted, minTime, range]);

  if (events.length === 0) return null;

  return (
    <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/80 rounded-xl p-3 flex flex-col gap-2 select-none">
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider flex items-center gap-1.5">
          <Clock className="h-3.5 w-3.5 text-indigo-400" /> Density Minimap Navigator
        </span>
        <div className="flex gap-4 text-[9px] text-slate-500 font-mono">
          <span>Start: {new Date(minTime).toLocaleDateString()}</span>
          <span>End: {new Date(maxTime).toLocaleDateString()}</span>
        </div>
      </div>

      {/* Slider Runway */}
      <div className="h-8 bg-slate-950/80 rounded-lg border border-slate-850 relative flex items-center overflow-hidden">
        {/* Background Grid Lines */}
        <div className="absolute inset-0 flex justify-between px-4 pointer-events-none">
          <span className="h-full w-px bg-slate-900" />
          <span className="h-full w-px bg-slate-900" />
          <span className="h-full w-px bg-slate-900" />
          <span className="h-full w-px bg-slate-900" />
        </div>

        {/* Event Markers */}
        {markers.map((m) => {
          const isSelected = m.id === selectedEventId;
          const colorClass = 
            m.priority === 'critical' ? 'bg-red-500' 
            : m.priority === 'high' ? 'bg-orange-500' 
            : m.type === 'ai_decision' ? 'bg-amber-400' 
            : m.type === 'ocr_timestamp' ? 'bg-cyan-400' 
            : 'bg-indigo-500';
            
          return (
            <button
              key={m.id}
              onClick={() => selectEvent(m.id)}
              className={cn(
                "absolute top-1/2 -translate-y-1/2 w-1.5 h-3.5 rounded-full transition-all hover:scale-150 z-10 cursor-pointer",
                isSelected ? "ring-2 ring-indigo-400 h-5 w-2 shadow-lg shadow-indigo-500" : "opacity-60 hover:opacity-100",
                colorClass
              )}
              style={{ left: `${m.pct}%` }}
              title={m.title}
            />
          );
        })}
      </div>
    </div>
  );
}
