import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { 
  FileText, User, Building, Search, Mail, ShieldAlert,
  Calendar, MapPin, Briefcase, FileCode, Scale
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { GRAPH_NODE_COLORS } from '@/lib/constants';
import type { GraphNodeType } from '@/types';

const typeIcons: Record<GraphNodeType, React.ElementType> = {
  document: FileText,
  person: User,
  organization: Building,
  evidence: Search,
  email: Mail,
  contract: Scale,
  legal_issue: ShieldAlert,
  event: Calendar,
  location: MapPin,
  case: Briefcase,
};

interface CustomNodeProps {
  data: {
    label: string;
    type: GraphNodeType;
    importance?: number;
    likelyMisclassified?: boolean;
    isHighlighted?: boolean;
    isDimmed?: boolean;
    isPathNode?: boolean;
  };
  selected?: boolean;
}

export const CustomNode = memo(({ data, selected }: CustomNodeProps) => {
  const nodeType = (data?.type || 'document') as GraphNodeType;
  const Icon = typeIcons[nodeType] || FileCode;
  const color = GRAPH_NODE_COLORS[nodeType] || '#64748b';
  const isDoc = nodeType === 'document';
  const importance = typeof data?.importance === 'number' ? data.importance : (isDoc ? 0.9 : 0.05);
  const isLikelyMisclassified = Boolean(data?.likelyMisclassified);

  // Scaled dimensions for entity nodes based on importance [0.05, 1.0]
  // Documents maintain default fixed sizing
  const scaleRatio = Math.max(0.0, Math.min(1.0, (importance - 0.05) / 0.95));
  const minWidth = isDoc ? 150 : Math.round(135 + scaleRatio * 65); // 135px to 200px
  const paddingY = isDoc ? 'py-3' : scaleRatio > 0.6 ? 'py-3.5' : scaleRatio < 0.2 ? 'py-2' : 'py-2.5';
  const labelSize = isDoc ? 'text-xs' : scaleRatio > 0.7 ? 'text-[13px]' : scaleRatio < 0.2 ? 'text-[11px]' : 'text-xs';
  const iconSize = isDoc ? 'h-4 w-4' : scaleRatio > 0.7 ? 'h-4 w-4' : 'h-3.5 w-3.5';

  return (
    <div
      className={cn(
        "px-4 rounded-xl bg-slate-900 border text-slate-200 transition-all duration-300 shadow-lg flex flex-col items-center gap-1.5",
        paddingY,
        selected ? "ring-2 ring-indigo-500 scale-105" : "border-slate-800",
        data?.isHighlighted && "border-indigo-400 shadow-indigo-500/10 shadow-md scale-105",
        data?.isDimmed && "opacity-30 blur-[0.5px]",
        data?.isPathNode && "border-emerald-500 ring-1 ring-emerald-500 shadow-emerald-500/20",
        isLikelyMisclassified && "border-dashed border-amber-500/60 bg-slate-900/90"
      )}
      style={{
        borderLeft: `4px solid ${color}`,
        minWidth: `${minWidth}px`,
      }}
    >
      <Handle type="target" position={Position.Left} className="w-2 h-2 !bg-slate-700" />
      
      <div className="flex items-center gap-2 w-full justify-start">
        <div 
          className="p-1.5 rounded-lg shrink-0" 
          style={{ backgroundColor: `${color}15`, color }}
        >
          <Icon className={iconSize} />
        </div>
        <div className="flex-1 min-w-0">
          <p className={cn("font-semibold text-slate-100 truncate text-left", labelSize)}>{data?.label || 'Entity'}</p>
          <div className="flex items-center gap-1.5">
            <p className="text-[9px] text-slate-500 capitalize text-left">{(nodeType || '').replace('_', ' ')}</p>
            {isLikelyMisclassified && (
              <span className="text-[8px] px-1 py-0.2 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 font-medium">
                flagged
              </span>
            )}
          </div>
        </div>
      </div>

      <Handle type="source" position={Position.Right} className="w-2 h-2 !bg-slate-700" />
    </div>
  );
});

CustomNode.displayName = 'CustomNode';
