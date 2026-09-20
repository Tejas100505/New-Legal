import { useState } from 'react';
import { useGraphStore } from '../store/graphStore';
import { Search, GitCommit, Download, Sparkles } from 'lucide-react';
import { GRAPH_LAYOUTS } from '@/lib/constants';
import type { GraphLayoutMode } from '@/types';
import { toPng, toSvg } from 'html-to-image';
import jsPDF from 'jspdf';

interface GraphToolbarProps {
  onOpenPathFinder: () => void;
  onApplyLayout: () => void;
}

export function GraphToolbar({ onOpenPathFinder, onApplyLayout }: GraphToolbarProps) {
  const filters = useGraphStore((s) => s.filters);
  const setFilters = useGraphStore((s) => s.setFilters);
  const layoutMode = useGraphStore((s) => s.layoutMode);
  const setLayoutMode = useGraphStore((s) => s.setLayoutMode);
  const isClustered = useGraphStore((s) => s.isClustered);
  const toggleClustering = useGraphStore((s) => s.toggleClustering);

  const [exportDropdown, setExportDropdown] = useState(false);

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
    <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-slate-900/50 backdrop-blur-xl border border-slate-800/80 rounded-xl">
      {/* Search Input */}
      <div className="relative flex-1 max-w-xs">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
        <input
          type="text"
          value={filters.searchQuery}
          onChange={(e) => setFilters({ searchQuery: e.target.value })}
          placeholder="Semantic graph search..."
          className="w-full pl-10 pr-4 py-2 rounded-lg bg-slate-800/60 border border-slate-700/50 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 transition-all"
        />
      </div>

      {/* Operations Controls */}
      <div className="flex items-center gap-2 flex-wrap">
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
      </div>
    </div>
  );
}
