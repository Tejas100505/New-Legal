import { motion } from 'framer-motion';
import { 
  Mail, Scale, Users, DollarSign, Activity, Search, 
  AlertTriangle, Clock, Brain, FileText, Upload, Shield, ChevronRight
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDate } from '@/lib/utils';
import { Badge } from '@/components/atoms/Badge';
import type { TimelineEvent, TimelineEventCategory } from '@/types';

const categoryIcons: Record<TimelineEventCategory, React.ElementType> = {
  email: Mail,
  contract: Scale,
  hearing: Users,
  payment: DollarSign,
  legal_event: Activity,
  evidence: Search,
  incident: AlertTriangle,
  ocr_timestamp: Clock,
  ai_decision: Brain,
  document: FileText,
  case: Activity,
  review: Shield,
  ai_finding: AlertTriangle,
  upload: Upload,
  status_change: ChevronRight,
};

const categoryColors: Record<TimelineEventCategory, string> = {
  email: 'border-cyan-500/20 text-cyan-400 bg-cyan-500/10',
  contract: 'border-pink-500/20 text-pink-400 bg-pink-500/10',
  hearing: 'border-purple-500/20 text-purple-400 bg-purple-500/10',
  payment: 'border-emerald-500/20 text-emerald-400 bg-emerald-500/10',
  legal_event: 'border-indigo-500/20 text-indigo-400 bg-indigo-500/10',
  evidence: 'border-orange-500/20 text-orange-400 bg-orange-500/10',
  incident: 'border-red-500/20 text-red-400 bg-red-500/10',
  ocr_timestamp: 'border-slate-500/20 text-slate-400 bg-slate-500/10',
  ai_decision: 'border-amber-500/20 text-amber-400 bg-amber-500/10',
  document: 'border-blue-500/20 text-blue-400 bg-blue-500/10',
  case: 'border-teal-500/20 text-teal-400 bg-teal-500/10',
  review: 'border-indigo-500/20 text-indigo-400 bg-indigo-500/10',
  ai_finding: 'border-rose-500/20 text-rose-400 bg-rose-500/10',
  upload: 'border-sky-500/20 text-sky-400 bg-sky-500/10',
  status_change: 'border-yellow-500/20 text-yellow-400 bg-yellow-500/10',
};

interface TimelineEventCardProps {
  event: TimelineEvent;
  isSelected: boolean;
  onSelect: () => void;
  index: number;
}

export function TimelineEventCard({ event, isSelected, onSelect, index }: TimelineEventCardProps) {
  const Icon = categoryIcons[event.type] || Clock;
  const colorClass = categoryColors[event.type] || 'border-slate-800 text-slate-400 bg-slate-900/30';

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.03, duration: 0.25 }}
      onClick={onSelect}
      className={cn(
        "relative pl-8 md:pl-10 pb-6 cursor-pointer group",
        isSelected && "scale-[1.01]"
      )}
    >
      {/* Connector line overlay */}
      <span className="absolute left-[15px] top-8 bottom-0 w-px bg-slate-800 group-last:bg-transparent" />

      {/* Circle Icon Indicator */}
      <span className={cn(
        "absolute left-1.5 top-1 flex h-8 w-8 items-center justify-center rounded-full border transition-all duration-300",
        isSelected ? "ring-2 ring-indigo-500 ring-offset-2 ring-offset-slate-950 scale-110" : "hover:scale-105",
        colorClass
      )}>
        <Icon className="h-4 w-4" />
      </span>

      {/* Content Box */}
      <div className={cn(
        "rounded-xl p-4 bg-slate-900/40 border transition-all duration-300",
        isSelected 
          ? "border-indigo-500/50 bg-indigo-950/5 shadow-lg shadow-indigo-500/5" 
          : "border-slate-800/80 hover:border-slate-700/80"
      )}>
        <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
          <span className="text-[10px] text-indigo-400 font-semibold uppercase tracking-wider">
            {event.caseName}
          </span>
          <span className="text-[10px] text-slate-500 flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {formatDate(event.timestamp)}
          </span>
        </div>

        <h3 className="text-sm font-semibold text-slate-200 mb-1 flex items-center gap-2">
          {event.title}
          {event.priority && (
            <Badge 
              variant={
                event.priority === 'critical' ? 'danger' 
                : event.priority === 'high' ? 'warning' 
                : 'default'
              } 
              size="xs"
            >
              {event.priority}
            </Badge>
          )}
        </h3>

        <p className="text-xs text-slate-400 leading-relaxed mb-3 line-clamp-2">
          {event.description}
        </p>

        {/* Footer badges / chips */}
        <div className="flex flex-wrap gap-1.5 items-center pt-2.5 border-t border-slate-850 text-[10px] text-slate-500">
          <Badge variant="outline" size="xs" className="capitalize">
            {event.type.replace('_', ' ')}
          </Badge>

          {event.lawyerName && (
            <span className="text-slate-500">
              Counsel: <strong className="text-slate-400">{event.lawyerName}</strong>
            </span>
          )}

          {event.amount && (
            <Badge variant="success" size="xs">
              ${event.amount.toLocaleString()}
            </Badge>
          )}

          {event.entityNames && event.entityNames.length > 0 && (
            <div className="flex items-center gap-1 ml-auto">
              {event.entityNames.slice(0, 2).map((ent) => (
                <span key={ent} className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                  {ent}
                </span>
              ))}
              {event.entityNames.length > 2 && (
                <span className="text-slate-600">+{event.entityNames.length - 2}</span>
              )}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
