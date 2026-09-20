import { useMemo } from 'react';
import { useGraphStore } from '../store/graphStore';
import { GRAPH_NODE_COLORS, GRAPH_EDGE_COLORS } from '@/lib/constants';
import type { GraphNodeType, GraphEdgeType } from '@/types';
import { SlidersHorizontal, Eye, Link } from 'lucide-react';

const NODE_TYPES: GraphNodeType[] = [
  'document', 'person', 'organization', 'evidence',
  'email', 'contract', 'legal_issue', 'event', 'location', 'case'
];

const EDGE_TYPES: GraphEdgeType[] = [
  'mentions', 'ownership', 'similarity', 'communication',
  'citation', 'references', 'evidence_link', 'relationship'
];

export function GraphFilterPanel() {
  const filters = useGraphStore((s) => s.filters);
  const setFilters = useGraphStore((s) => s.setFilters);
  const rawNodes = useGraphStore((s) => s.rawNodes);
  const rawEdges = useGraphStore((s) => s.rawEdges);

  const nodeCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    rawNodes.forEach((n: any) => {
      const t = n.type || 'evidence';
      counts[t] = (counts[t] || 0) + 1;
    });
    return counts;
  }, [rawNodes]);

  const edgeCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    rawEdges.forEach((e: any) => {
      const t = (e.type || e.relation || 'relationship').toLowerCase();
      counts[t] = (counts[t] || 0) + 1;
    });
    return counts;
  }, [rawEdges]);

  const toggleNodeType = (type: GraphNodeType) => {
    const nodeTypes = filters.nodeTypes.includes(type)
      ? filters.nodeTypes.filter((t) => t !== type)
      : [...filters.nodeTypes, type];
    setFilters({ nodeTypes });
  };

  const toggleEdgeType = (type: GraphEdgeType) => {
    const edgeTypes = filters.edgeTypes.includes(type)
      ? filters.edgeTypes.filter((t) => t !== type)
      : [...filters.edgeTypes, type];
    setFilters({ edgeTypes });
  };

  const handleSelectAllNodes = () => {
    setFilters({ nodeTypes: [...NODE_TYPES] });
  };

  const handleSelectAllEdges = () => {
    setFilters({ edgeTypes: [...EDGE_TYPES] });
  };

  const handleClearNodes = () => {
    setFilters({ nodeTypes: [] });
  };

  const handleClearEdges = () => {
    setFilters({ edgeTypes: [] });
  };

  return (
    <div className="w-64 bg-slate-900/50 backdrop-blur-xl border border-slate-800/80 rounded-xl p-4 flex flex-col gap-5 overflow-y-auto max-h-[calc(100vh-14rem)]">
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <SlidersHorizontal className="h-4 w-4 text-indigo-400" />
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">Graph Filters</h3>
      </div>

      {/* Node Types */}
      <div className="flex flex-col gap-2">
        <div className="flex justify-between items-center">
          <span className="text-xs font-medium text-slate-400 flex items-center gap-1.5">
            <Eye className="h-3.5 w-3.5" /> Node Types
          </span>
          <div className="flex gap-1.5 text-[10px]">
            <button onClick={handleSelectAllNodes} className="text-indigo-400 hover:text-indigo-300">All</button>
            <span className="text-slate-700">|</span>
            <button onClick={handleClearNodes} className="text-slate-500 hover:text-slate-400">None</button>
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          {NODE_TYPES.map((type) => {
            const color = GRAPH_NODE_COLORS[type] || '#fff';
            const checked = filters.nodeTypes.includes(type);
            return (
              <label 
                key={type} 
                className="flex items-center justify-between text-xs text-slate-300 cursor-pointer hover:bg-slate-800/30 p-1 rounded transition-colors"
              >
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleNodeType(type)}
                    className="rounded border-slate-700 bg-slate-850 text-indigo-500 focus:ring-indigo-500/30 h-3.5 w-3.5"
                  />
                  <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: color }} />
                  <span className="capitalize">{type.replace('_', ' ')}</span>
                </div>
                {rawNodes.length > 0 && (
                  <span className="text-[10px] font-mono text-slate-500">
                    {nodeCounts[type] || 0}
                  </span>
                )}
              </label>
            );
          })}
        </div>
      </div>

      {/* Edge Types */}
      <div className="flex flex-col gap-2">
        <div className="flex justify-between items-center">
          <span className="text-xs font-medium text-slate-400 flex items-center gap-1.5">
            <Link className="h-3.5 w-3.5" /> Relationships
          </span>
          <div className="flex gap-1.5 text-[10px]">
            <button onClick={handleSelectAllEdges} className="text-indigo-400 hover:text-indigo-300">All</button>
            <span className="text-slate-700">|</span>
            <button onClick={handleClearEdges} className="text-slate-500 hover:text-slate-400">None</button>
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          {EDGE_TYPES.map((type) => {
            const color = GRAPH_EDGE_COLORS[type] || '#fff';
            const checked = filters.edgeTypes.includes(type);
            return (
              <label 
                key={type} 
                className="flex items-center justify-between text-xs text-slate-300 cursor-pointer hover:bg-slate-800/30 p-1 rounded transition-colors"
              >
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleEdgeType(type)}
                    className="rounded border-slate-700 bg-slate-850 text-indigo-500 focus:ring-indigo-500/30 h-3.5 w-3.5"
                  />
                  <span className="w-3 h-0.5 shrink-0" style={{ backgroundColor: color }} />
                  <span className="capitalize">{type.replace('_', ' ')}</span>
                </div>
                {rawEdges.length > 0 && (
                  <span className="text-[10px] font-mono text-slate-500">
                    {edgeCounts[type] || 0}
                  </span>
                )}
              </label>
            );
          })}
        </div>
      </div>

      {/* Connection Weight Threshold */}
      <div className="flex flex-col gap-2 border-t border-slate-800 pt-3">
        <div className="flex justify-between text-xs text-slate-400">
          <span>Min Strength</span>
          <span className="font-mono text-indigo-400 font-semibold">{filters.minWeight.toFixed(2)}</span>
        </div>
        <input
          type="range"
          min="0.0"
          max="1.0"
          step="0.05"
          value={filters.minWeight}
          onChange={(e) => setFilters({ minWeight: parseFloat(e.target.value) })}
          className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
        />
      </div>
    </div>
  );
}
