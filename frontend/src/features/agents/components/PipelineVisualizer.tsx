/**
 * PipelineVisualizer — horizontal pipeline flow visualization
 * showing the 10 processing stages with animated progress.
 */

import { motion } from 'framer-motion';
import {
  FolderPlus, Upload, Eye, Database, Search, Scale,
  Share2, CalendarClock, Link2, FileBarChart, ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAgentStore } from '@/stores/agentStore';
import type { AgentStatus, PipelineStageName } from '@/types';

const stageIcons: Record<PipelineStageName, React.ElementType> = {
  case_creation: FolderPlus,
  document_upload: Upload,
  ocr: Eye,
  indexing: Database,
  retrieval: Search,
  legal_review: Scale,
  graph_generation: Share2,
  timeline_generation: CalendarClock,
  evidence_linking: Link2,
  final_report: FileBarChart,
};

const statusStyles: Record<AgentStatus, { bg: string; ring: string; text: string }> = {
  idle: { bg: 'bg-slate-800', ring: 'ring-slate-700', text: 'text-slate-500' },
  queued: { bg: 'bg-amber-500/10', ring: 'ring-amber-500/30', text: 'text-amber-400' },
  running: { bg: 'bg-indigo-500/10', ring: 'ring-indigo-500/40', text: 'text-indigo-400' },
  completed: { bg: 'bg-emerald-500/10', ring: 'ring-emerald-500/30', text: 'text-emerald-400' },
  failed: { bg: 'bg-red-500/10', ring: 'ring-red-500/30', text: 'text-red-400' },
  retrying: { bg: 'bg-orange-500/10', ring: 'ring-orange-500/30', text: 'text-orange-400' },
};

export function PipelineVisualizer() {
  const pipelineStages = useAgentStore((s) => s.pipelineStages);
  const overallProgress = useAgentStore((s) => s.overallProgress);

  return (
    <div
      className="rounded-xl p-5 bg-slate-900/50 backdrop-blur-xl border border-slate-800/50"
      role="region"
      aria-label="Processing Pipeline"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-indigo-500" />
          <h3 className="text-sm font-semibold text-slate-200">Processing Pipeline</h3>
        </div>
        <span className="text-xs font-mono text-slate-400">{overallProgress}% complete</span>
      </div>

      {/* ── Overall Progress Bar ───────────────────────────────────── */}
      <div className="h-1 w-full rounded-full bg-slate-800/60 mb-5 overflow-hidden">
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500"
          initial={{ width: 0 }}
          animate={{ width: `${overallProgress}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        />
      </div>

      {/* ── Stage Flow ─────────────────────────────────────────────── */}
      <div
        className="flex items-center gap-1 overflow-x-auto pb-2 -mx-1 px-1"
        role="list"
        aria-label="Pipeline stages"
      >
        {pipelineStages.map((stage, i) => {
          const Icon = (stage.id && stageIcons[stage.id as PipelineStageName]) || Scale;
          const styles = statusStyles[stage.status];
          const isActive = stage.status === 'running';
          const isCompleted = stage.status === 'completed';

          return (
            <div key={stage.id} className="flex items-center shrink-0" role="listitem">
              {/* Stage Node */}
              <motion.div
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: i * 0.06 }}
                className={cn(
                  'flex flex-col items-center gap-1.5 px-2 py-2 rounded-xl',
                  'transition-all duration-300 min-w-[70px]',
                  isActive && 'ring-1',
                  styles.ring,
                )}
                aria-label={`${stage.label}: ${stage.status}`}
                tabIndex={0}
              >
                <div className={cn(
                  'h-8 w-8 rounded-lg flex items-center justify-center transition-all',
                  styles.bg,
                  isActive && 'agent-running',
                )}>
                  <Icon className={cn('h-4 w-4', styles.text)} />
                </div>
                <span className={cn('text-[9px] font-medium text-center leading-tight', styles.text)}>
                  {stage.label}
                </span>
                {stage.agentIds.length > 0 && (
                  <span className="text-[8px] text-slate-600">
                    {stage.agentIds.length} agent{stage.agentIds.length > 1 ? 's' : ''}
                  </span>
                )}
              </motion.div>

              {/* Connector Arrow */}
              {i < pipelineStages.length - 1 && (
                <div className="flex items-center px-0.5 shrink-0">
                  <div className={cn(
                    'h-px w-4 transition-colors duration-300',
                    isCompleted ? 'bg-emerald-500/50' :
                    isActive ? 'bg-indigo-500/50' :
                    'bg-slate-800'
                  )} />
                  <ChevronRight className={cn(
                    'h-3 w-3 -ml-1 transition-colors',
                    isCompleted ? 'text-emerald-500/50' :
                    isActive ? 'text-indigo-500/50' :
                    'text-slate-800'
                  )} />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
