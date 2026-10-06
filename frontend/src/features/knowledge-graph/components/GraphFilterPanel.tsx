import { useMemo, useState } from 'react';
import { useGraphStore, PRIMARY_NODE_TYPES, SECONDARY_NODE_TYPES, ALL_NODE_TYPES } from '../store/graphStore';
import { GRAPH_NODE_COLORS, GRAPH_EDGE_COLORS } from '@/lib/constants';
import type { GraphNodeType, GraphEdgeType } from '@/types';
import { SlidersHorizontal, Eye, Link, X, ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

const EDGE_TYPES: GraphEdgeType[] = [
  'mentions', 'ownership', 'similarity', 'communication',
  'citation', 'references', 'evidence_link', 'relationship'
];

interface GraphFilterPanelProps {
  onClose?: () => void;
  isOverlay?: boolean;
}

function formatNodeTypeLabel(type: string): string {
  if (type === 'legal_issue') return 'Legal Issue';
  return type.charAt(0).toUpperCase() + type.slice(1);
}

export function GraphFilterPanel({ onClose, isOverlay = false }: GraphFilterPanelProps = {}) {
  const [isMoreOpen, setIsMoreOpen] = useState(false);
  const filters = useGraphStore((s) => s.filters);
  const setFilters = useGraphStore((s) => s.setFilters);
  const resetFilters = useGraphStore((s) => s.resetFilters);
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

  const secondaryActiveCount = useMemo(() => {
    return SECONDARY_NODE_TYPES.filter((t) => filters.nodeTypes.includes(t)).length;
  }, [filters.nodeTypes]);

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
    setFilters({ nodeTypes: [...ALL_NODE_TYPES] });
    setIsMoreOpen(true);
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
    <div className={cn(
      "w-64 backdrop-blur-xl border border-slate-200 dark:border-slate-800/80 rounded-xl p-4 flex flex-col gap-5 overflow-y-auto transition-all",
      isOverlay 
        ? "bg-white/95 dark:bg-slate-900/95 max-h-[calc(100vh-6rem)] shadow-2xl z-30" 
        : "bg-white/70 dark:bg-slate-900/50 max-h-[calc(100vh-14rem)]"
    )}>
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-2">
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="h-4 w-4 text-indigo-500 dark:text-indigo-400" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-800 dark:text-slate-300">Graph Filters</h3>
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 transition-colors cursor-pointer"
            title="Close filters"
            aria-label="Close filters"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Node Types */}
      <div className="flex flex-col gap-2">
        <div className="flex justify-between items-center">
          <span className="text-xs font-medium text-slate-600 dark:text-slate-400 flex items-center gap-1.5">
            <Eye className="h-3.5 w-3.5" /> Node Types
          </span>
          <div className="flex gap-1.5 text-[10px]">
            <button 
              type="button"
              id="filter-nodes-all-btn"
              onClick={handleSelectAllNodes} 
              className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 font-medium cursor-pointer"
              title="Select all primary and secondary node types"
            >
              All
            </button>
            <span className="text-slate-300 dark:text-slate-700">|</span>
            <button 
              type="button"
              id="filter-nodes-none-btn"
              onClick={handleClearNodes} 
              className="text-slate-500 hover:text-slate-700 dark:hover:text-slate-400 font-medium cursor-pointer"
              title="Deselect all node types"
            >
              None
            </button>
          </div>
        </div>

        {/* Primary Node Types: Document, Person, Organization, Legal Issue */}
        <div className="flex flex-col gap-1.5" id="primary-node-types-list">
          {PRIMARY_NODE_TYPES.map((type) => {
            const color = GRAPH_NODE_COLORS[type] || '#fff';
            const checked = filters.nodeTypes.includes(type);
            const count = nodeCounts[type] || 0;
            return (
              <label 
                key={type} 
                id={`filter-node-${type}`}
                className="flex items-center justify-between text-xs text-slate-700 dark:text-slate-300 cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800/30 p-1 rounded transition-colors"
              >
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleNodeType(type)}
                    className="rounded border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-850 text-indigo-600 dark:text-indigo-500 focus:ring-indigo-500/30 h-3.5 w-3.5 cursor-pointer"
                  />
                  <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: color }} />
                  <span>{formatNodeTypeLabel(type)}</span>
                </div>
                {rawNodes.length > 0 && (
                  <span className="text-[10px] font-mono text-slate-400 dark:text-slate-500">
                    {count.toLocaleString()}
                  </span>
                )}
              </label>
            );
          })}
        </div>

        {/* Divider before More node types */}
        <div className="border-t border-slate-200 dark:border-slate-800/80 my-0.5" />

        {/* Expandable Secondary Node Types */}
        <div className="flex flex-col gap-1.5">
          <button
            type="button"
            id="more-node-types-toggle"
            onClick={() => setIsMoreOpen((prev) => !prev)}
            className="flex items-center justify-between text-xs text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 font-medium py-1 px-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800/40 transition-colors cursor-pointer group"
            aria-expanded={isMoreOpen}
            title={isMoreOpen ? "Collapse secondary node types" : "Expand more node types"}
          >
            <div className="flex items-center gap-1.5">
              {isMoreOpen ? (
                <ChevronDown className="h-3.5 w-3.5 text-slate-500 dark:text-slate-400 group-hover:text-slate-800 dark:group-hover:text-slate-200 transition-transform" />
              ) : (
                <ChevronRight className="h-3.5 w-3.5 text-slate-500 dark:text-slate-400 group-hover:text-slate-800 dark:group-hover:text-slate-200 transition-transform" />
              )}
              <span>More node types</span>
            </div>
            {secondaryActiveCount > 0 && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-indigo-50 dark:bg-indigo-500/20 text-indigo-600 dark:text-indigo-300 font-semibold">
                {secondaryActiveCount} active
              </span>
            )}
          </button>

          {isMoreOpen && (
            <div 
              id="more-node-types-list"
              className="flex flex-col gap-1.5 pl-2 border-l-2 border-slate-200 dark:border-slate-800/80 animate-in slide-in-from-top-1 duration-150"
            >
              {SECONDARY_NODE_TYPES.map((type) => {
                const color = GRAPH_NODE_COLORS[type] || '#fff';
                const checked = filters.nodeTypes.includes(type);
                const count = nodeCounts[type] || 0;
                return (
                  <label 
                    key={type} 
                    id={`filter-node-${type}`}
                    className="flex items-center justify-between text-xs text-slate-700 dark:text-slate-300 cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800/30 p-1 rounded transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleNodeType(type)}
                        className="rounded border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-850 text-indigo-600 dark:text-indigo-500 focus:ring-indigo-500/30 h-3.5 w-3.5 cursor-pointer"
                      />
                      <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: color }} />
                      <span>{formatNodeTypeLabel(type)}</span>
                    </div>
                    {rawNodes.length > 0 && (
                      <span className="text-[10px] font-mono text-slate-400 dark:text-slate-500">
                        {count.toLocaleString()}
                      </span>
                    )}
                  </label>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Edge Types */}
      <div className="flex flex-col gap-2">
        <div className="flex justify-between items-center">
          <span className="text-xs font-medium text-slate-600 dark:text-slate-400 flex items-center gap-1.5">
            <Link className="h-3.5 w-3.5" /> Relationships
          </span>
          <div className="flex gap-1.5 text-[10px]">
            <button 
              type="button"
              id="filter-edges-all-btn"
              onClick={handleSelectAllEdges} 
              className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 font-medium cursor-pointer"
            >
              All
            </button>
            <span className="text-slate-300 dark:text-slate-700">|</span>
            <button 
              type="button"
              id="filter-edges-none-btn"
              onClick={handleClearEdges} 
              className="text-slate-500 hover:text-slate-700 dark:hover:text-slate-400 font-medium cursor-pointer"
            >
              None
            </button>
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          {EDGE_TYPES.map((type) => {
            const color = GRAPH_EDGE_COLORS[type] || '#fff';
            const checked = filters.edgeTypes.includes(type);
            const count = edgeCounts[type] || 0;
            return (
              <label 
                key={type} 
                id={`filter-edge-${type}`}
                className="flex items-center justify-between text-xs text-slate-700 dark:text-slate-300 cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800/30 p-1 rounded transition-colors"
              >
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleEdgeType(type)}
                    className="rounded border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-850 text-indigo-600 dark:text-indigo-500 focus:ring-indigo-500/30 h-3.5 w-3.5 cursor-pointer"
                  />
                  <span className="w-3 h-0.5 shrink-0" style={{ backgroundColor: color }} />
                  <span className="capitalize">{type.replace('_', ' ')}</span>
                </div>
                {rawEdges.length > 0 && (
                  <span className="text-[10px] font-mono text-slate-400 dark:text-slate-500">
                    {count.toLocaleString()}
                  </span>
                )}
              </label>
            );
          })}
        </div>
      </div>

      {/* Connection Weight Threshold */}
      <div className="flex flex-col gap-2 border-t border-slate-200 dark:border-slate-800 pt-3">
        <div className="flex justify-between text-xs text-slate-600 dark:text-slate-400">
          <span>Min Strength</span>
          <span className="font-mono text-indigo-600 dark:text-indigo-400 font-semibold">{filters.minWeight.toFixed(2)}</span>
        </div>
        <input
          type="range"
          min="0.0"
          max="1.0"
          step="0.05"
          value={filters.minWeight}
          onChange={(e) => setFilters({ minWeight: parseFloat(e.target.value) })}
          className="w-full h-1 bg-slate-200 dark:bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
        />
      </div>

      {/* Reset Button */}
      <button
        type="button"
        id="filter-reset-all-btn"
        onClick={() => resetFilters()}
        className="w-full py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800/80 dark:hover:bg-slate-750 text-slate-700 dark:text-slate-300 text-xs font-semibold border border-slate-300 dark:border-slate-700/60 transition-all hover:text-slate-900 dark:hover:text-slate-100 cursor-pointer"
      >
        Reset All Filters
      </button>
    </div>
  );
}
