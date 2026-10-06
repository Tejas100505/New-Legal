import { useState, useMemo, useRef, useEffect } from 'react';
import { useGraphStore } from '../store/graphStore';
import { Search, GitCommit, Download, Sparkles, RotateCcw, Maximize2, Minimize2, SlidersHorizontal, Sun, Moon } from 'lucide-react';
import { useThemeStore } from '@/stores/themeStore';
import { GRAPH_LAYOUTS, GRAPH_NODE_COLORS } from '@/lib/constants';
import type { GraphLayoutMode } from '@/types';
import { cn } from '@/lib/utils';
import { toPng, toSvg } from 'html-to-image';
import jsPDF from 'jspdf';

interface GraphToolbarProps {
  onOpenPathFinder: () => void;
  onApplyLayout: () => void;
  isMaximized?: boolean;
  onToggleMaximize?: () => void;
  showFilters?: boolean;
  onToggleFilters?: () => void;
}

export function GraphToolbar({ 
  onOpenPathFinder, 
  onApplyLayout,
  isMaximized = false,
  onToggleMaximize,
  showFilters = false,
  onToggleFilters,
}: GraphToolbarProps) {
  const filters = useGraphStore((s) => s.filters);
  const setFilters = useGraphStore((s) => s.setFilters);
  const layoutMode = useGraphStore((s) => s.layoutMode);
  const setLayoutMode = useGraphStore((s) => s.setLayoutMode);
  const isClustered = useGraphStore((s) => s.isClustered);
  const toggleClustering = useGraphStore((s) => s.toggleClustering);

  const rawNodes = useGraphStore((s) => s.rawNodes);
  const selectNode = useGraphStore((s) => s.selectNode);
  const resetFilters = useGraphStore((s) => s.resetFilters);

  const { resolvedTheme, toggleTheme } = useThemeStore();

  const [exportDropdown, setExportDropdown] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const searchContainerRef = useRef<HTMLDivElement>(null);

  // Close search suggestions on outside click
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  // Compute search matches across ALL rawNodes (all 4,676+ entities/docs)
  const searchSuggestions = useMemo(() => {
    const q = (filters.searchQuery || '').trim().toLowerCase();
    if (!q || q.length < 1) return [];
    const matches: any[] = [];
    for (let i = 0; i < rawNodes.length; i++) {
      const n = rawNodes[i];
      const label = (n.label || n.name || '').toLowerCase();
      if (label.includes(q)) {
        matches.push(n);
        if (matches.length >= 8) break;
      }
    }
    return matches;
  }, [filters.searchQuery, rawNodes]);

  const handleSelectSuggestion = (nodeId: string) => {
    selectNode(nodeId);
    setShowSuggestions(false);
    setTimeout(onApplyLayout, 50);
  };

  const handleReset = () => {
    resetFilters();
    setShowSuggestions(false);
    setTimeout(onApplyLayout, 50);
  };

  const triggerExport = async (format: 'png' | 'svg' | 'pdf') => {
    setExportDropdown(false);
    const element = document.querySelector('.react-flow') as HTMLElement;
    if (!element) return;

    try {
      if (format === 'png') {
        const dataUrl = await toPng(element, { backgroundColor: '#0b0f19' });
        const link = document.createElement('a');
        link.download = 'knowledge-graph.png';
        link.href = dataUrl;
        link.click();
      } else if (format === 'svg') {
        const dataUrl = await toSvg(element, { backgroundColor: '#0b0f19' });
        const link = document.createElement('a');
        link.download = 'knowledge-graph.svg';
        link.href = dataUrl;
        link.click();
      } else if (format === 'pdf') {
        const dataUrl = await toPng(element, { backgroundColor: '#0b0f19', width: 800, height: 600 });
        const pdf = new jsPDF('l', 'px', [800, 600]);
        pdf.addImage(dataUrl, 'PNG', 0, 0, 800, 600);
        pdf.save('knowledge-graph.pdf');
      }
    } catch (err) {
      console.error('Failed to export graph', err);
    }
  };

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-slate-900/50 backdrop-blur-xl border border-slate-800/80 rounded-xl relative z-20">
      {/* Search Input with Autocomplete Dropdown across full corpus */}
      <div ref={searchContainerRef} className="relative flex-1 max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
        <input
          type="text"
          value={filters.searchQuery}
          onFocus={() => setShowSuggestions(true)}
          onChange={(e) => {
            setFilters({ searchQuery: e.target.value });
            setShowSuggestions(true);
          }}
          placeholder="Search entities across complete case graph..."
          className="w-full pl-10 pr-4 py-2 rounded-lg bg-slate-800/60 border border-slate-700/50 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 transition-all"
        />

        {showSuggestions && searchSuggestions.length > 0 && (
          <div className="absolute left-0 right-0 mt-1.5 rounded-xl bg-slate-900/95 backdrop-blur-xl border border-slate-750 shadow-2xl overflow-hidden z-50">
            <div className="px-3 py-1.5 border-b border-slate-800 text-[10px] uppercase tracking-wider text-slate-400 font-semibold flex justify-between">
              <span>Matching Entities ({searchSuggestions.length})</span>
              <span className="text-slate-500">Click to bring into view</span>
            </div>
            <div className="max-h-60 overflow-y-auto divide-y divide-slate-800/60">
              {searchSuggestions.map((item) => {
                const color = GRAPH_NODE_COLORS[item.type] || '#6366f1';
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => handleSelectSuggestion(item.id)}
                    className="w-full text-left px-3 py-2 flex items-center justify-between gap-2 hover:bg-indigo-500/10 transition-colors group cursor-pointer"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: color }} />
                      <span className="text-xs text-slate-200 font-medium truncate group-hover:text-indigo-200">
                        {item.label}
                      </span>
                    </div>
                    <span
                      className="px-2 py-0.5 rounded text-[10px] font-semibold border capitalize shrink-0"
                      style={{ borderColor: `${color}40`, color }}
                    >
                      {item.type?.replace('_', ' ')}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Operations Controls */}
      <div className="flex items-center gap-2 flex-wrap">
        {/* Reset View */}
        <button
          onClick={handleReset}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs font-semibold border border-slate-700/50 transition-colors"
          title="Reset graph filters and view"
        >
          <RotateCcw className="h-3.5 w-3.5 text-slate-400" /> Reset View
        </button>
        {/* Layout Mode */}
        <div className="flex items-center gap-1.5 bg-slate-850 rounded-lg p-0.5 border border-slate-800">
          {GRAPH_LAYOUTS.map((lay) => (
            <button
              key={lay.mode}
              onClick={() => {
                setLayoutMode(lay.mode as GraphLayoutMode);
                setTimeout(onApplyLayout, 50); // Re-run layout algorithm
              }}
              className={`px-2.5 py-1.5 rounded-md text-[10px] font-medium transition-colors ${
                layoutMode === lay.mode
                  ? 'bg-indigo-500/20 text-indigo-300'
                  : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              {lay.label}
            </button>
          ))}
        </div>

        {/* Path Finder */}
        <button
          onClick={onOpenPathFinder}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs font-semibold border border-slate-700/50 transition-colors"
        >
          <GitCommit className="h-3.5 w-3.5 text-indigo-400" /> Path Finder
        </button>

        {/* Node Clustering */}
        <button
          onClick={toggleClustering}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
            isClustered
              ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30'
              : 'bg-slate-800 hover:bg-slate-750 text-slate-300 border-slate-700/50'
          }`}
        >
          <Sparkles className="h-3.5 w-3.5" /> Clustered Nodes
        </button>

        {/* Export Graph Dropdown */}
        <div className="relative">
          <button
            onClick={() => setExportDropdown(!exportDropdown)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs font-semibold border border-slate-700/50 transition-colors"
          >
            <Download className="h-3.5 w-3.5 text-indigo-400" /> Export Graph
          </button>
          {exportDropdown && (
            <div className="absolute right-0 mt-1.5 w-36 rounded-lg bg-slate-900 border border-slate-800 shadow-2xl py-1 z-10">
              <button 
                onClick={() => triggerExport('png')} 
                className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-800 text-slate-300 hover:text-slate-100"
              >
                Export as PNG
              </button>
              <button 
                onClick={() => triggerExport('svg')} 
                className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-800 text-slate-300 hover:text-slate-100"
              >
                Export as SVG
              </button>
              <button 
                onClick={() => triggerExport('pdf')} 
                className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-800 text-slate-300 hover:text-slate-100"
              >
                Export as PDF
              </button>
            </div>
          )}
        </div>

        {/* Toggle Filters Panel (visible when maximized) */}
        {isMaximized && onToggleFilters && (
          <button
            type="button"
            id="graph-filters-toggle"
            onClick={onToggleFilters}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-indigo-500/50",
              showFilters
                ? "bg-indigo-500/20 text-indigo-300 border-indigo-500/40"
                : "bg-slate-800 hover:bg-slate-750 text-slate-300 border-slate-700/50"
            )}
            title={showFilters ? "Hide graph filters" : "Show graph filters"}
            aria-label={showFilters ? "Hide graph filters" : "Show graph filters"}
          >
            <SlidersHorizontal className="h-3.5 w-3.5 text-indigo-400" />
            <span>Filters</span>
          </button>
        )}

        {/* Theme toggle (visible in maximized mode where global header is hidden) */}
        {isMaximized && (
          <button
            type="button"
            id="graph-theme-toggle"
            onClick={toggleTheme}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-colors cursor-pointer border border-slate-700/50"
            title={`Switch to ${resolvedTheme === 'dark' ? 'light' : 'dark'} mode`}
            aria-label={`Switch to ${resolvedTheme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {resolvedTheme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
        )}

        {/* Maximize / Fullscreen Toggle Button */}
        {onToggleMaximize && (
          <button
            type="button"
            id="graph-maximize-toggle"
            onClick={onToggleMaximize}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-indigo-500/50",
              isMaximized
                ? "bg-indigo-600 hover:bg-indigo-500 text-white border-indigo-500 shadow-md shadow-indigo-600/30"
                : "bg-slate-800 hover:bg-slate-750 text-slate-300 hover:text-white border-slate-700/50"
            )}
            title={isMaximized ? "Exit fullscreen" : "Maximize graph"}
            aria-label={isMaximized ? "Exit graph fullscreen" : "Maximize graph"}
          >
            {isMaximized ? (
              <>
                <Minimize2 className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Minimize</span>
              </>
            ) : (
              <>
                <Maximize2 className="h-3.5 w-3.5 text-indigo-400" />
                <span className="hidden sm:inline">Maximize</span>
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}
