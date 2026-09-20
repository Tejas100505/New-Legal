import { useState, useMemo, useRef, useEffect } from 'react';
import { useGraphStore } from '../store/graphStore';
import { X, GitCommit, ArrowRight, Zap, CheckCircle2, Search } from 'lucide-react';
import { Badge } from '@/components/atoms/Badge';

interface PathFinderModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface EntityComboboxProps {
  label: string;
  selectedId: string;
  onSelect: (nodeId: string) => void;
  disabledId?: string;
  rawNodes: any[];
  placeholder?: string;
}

function EntityCombobox({
  label,
  selectedId,
  onSelect,
  disabledId,
  rawNodes,
  placeholder = 'Type to search entity...'
}: EntityComboboxProps) {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const selectedNode = useMemo(
    () => rawNodes.find((n: any) => n.id === selectedId),
    [rawNodes, selectedId]
  );

  // Filter across all rawNodes
  const filteredNodes = useMemo(() => {
    if (!query.trim()) {
      return rawNodes.filter((n: any) => n.id !== disabledId).slice(0, 40);
    }
    const q = query.toLowerCase();
    return rawNodes
      .filter((n: any) => {
        if (n.id === disabledId) return false;
        const name = (n.label || n.name || '').toLowerCase();
        const type = (n.type || '').toLowerCase();
        return name.includes(q) || type.includes(q);
      })
      .slice(0, 40);
  }, [rawNodes, query, disabledId]);

  // Click away listener to close dropdown
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="flex flex-col gap-1.5 relative" ref={containerRef}>
      <label className="text-xs text-slate-400 font-semibold">{label}</label>
      
      {selectedNode ? (
        <div className="flex items-center justify-between bg-slate-800/90 border border-indigo-500/40 rounded-lg p-2 text-xs text-slate-200">
          <div className="flex items-center gap-2 truncate">
            <span className="font-medium truncate">{selectedNode.label || selectedNode.name}</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-700/60 text-slate-400 capitalize shrink-0">
              {selectedNode.type}
            </span>
          </div>
          <button
            type="button"
            onClick={() => {
              onSelect('');
              setQuery('');
              setIsOpen(true);
            }}
            className="p-0.5 hover:bg-slate-700 rounded text-slate-400 hover:text-slate-200 transition-colors"
            title="Clear selection"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ) : (
        <div className="relative">
          <div className="flex items-center gap-2 bg-slate-800/80 border border-slate-700/50 rounded-lg p-2 text-xs text-slate-200 focus-within:ring-2 focus-within:ring-indigo-500/30 focus-within:border-indigo-500/50">
            <Search className="h-3.5 w-3.5 text-slate-400 shrink-0" />
            <input
              type="text"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setIsOpen(true);
              }}
              onFocus={() => setIsOpen(true)}
              placeholder={placeholder}
              className="bg-transparent border-none outline-none text-xs text-slate-200 placeholder:text-slate-500 w-full"
            />
            {query && (
              <button
                type="button"
                onClick={() => setQuery('')}
                className="text-slate-500 hover:text-slate-300"
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </div>

          {isOpen && (
            <div className="absolute top-full left-0 right-0 mt-1 max-h-48 overflow-y-auto rounded-lg bg-slate-800 border border-slate-700 shadow-xl z-50 py-1 divide-y divide-slate-700/50">
              {filteredNodes.length === 0 ? (
                <div className="px-3 py-2 text-xs text-slate-500 text-center">
                  No matching entities found
                </div>
              ) : (
                filteredNodes.map((n: any) => (
                  <button
                    key={n.id}
                    type="button"
                    onClick={() => {
                      onSelect(n.id);
                      setIsOpen(false);
                      setQuery('');
                    }}
                    className="w-full px-3 py-1.5 flex items-center justify-between text-left hover:bg-indigo-500/20 transition-colors text-xs text-slate-300"
                  >
                    <span className="truncate mr-2">{n.label || n.name}</span>
                    <span className="text-[10px] px-1 py-0.5 rounded bg-slate-900 text-slate-400 capitalize shrink-0">
                      {n.type}
                    </span>
                  </button>
                ))
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function PathFinderModal({ isOpen, onClose }: PathFinderModalProps) {
  const [source, setSource] = useState('');
  const [target, setTarget] = useState('');
  const findShortestPath = useGraphStore((s) => s.findShortestPath);
  const shortestPath = useGraphStore((s) => s.shortestPath);
  const clearShortestPath = useGraphStore((s) => s.clearShortestPath);
  const rawNodes = useGraphStore((s) => s.rawNodes);

  if (!isOpen) return null;

  const handleCalculate = () => {
    if (source && target) {
      findShortestPath(source, target);
    }
  };

  const handleClose = () => {
    clearShortestPath();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div 
        className="w-full max-w-lg rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-2xl flex flex-col gap-5 text-slate-100"
        role="dialog"
        aria-modal="true"
        aria-label="Shortest Path Finder"
      >
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <GitCommit className="h-5 w-5 text-indigo-400" />
            <h2 className="text-lg font-bold">Shortest Path Discovery</h2>
          </div>
          <button 
            onClick={handleClose} 
            className="p-1 rounded-lg hover:bg-slate-800 text-slate-500 hover:text-slate-300 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Inputs */}
        <div className="grid grid-cols-2 gap-4">
          <EntityCombobox
            label="Source Entity"
            selectedId={source}
            onSelect={setSource}
            disabledId={target}
            rawNodes={rawNodes}
            placeholder="Search source entity..."
          />

          <EntityCombobox
            label="Target Entity"
            selectedId={target}
            onSelect={setTarget}
            disabledId={source}
            rawNodes={rawNodes}
            placeholder="Search target entity..."
          />
        </div>

        <button
          onClick={handleCalculate}
          disabled={!source || !target}
          className="w-full py-2.5 rounded-lg bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium text-sm flex items-center justify-center gap-2 transition-all active:scale-[0.98]"
        >
          <Zap className="h-4 w-4" /> Discover Connections
        </button>

        {/* Shortest Path Results */}
        {shortestPath ? (
          <div className="flex flex-col gap-3 bg-slate-950/40 p-4 rounded-xl border border-slate-850">
            <div className="flex justify-between items-center text-xs text-slate-400">
              <span className="flex items-center gap-1"><CheckCircle2 className="h-4 w-4 text-emerald-400" /> Path Found!</span>
              <span>Degree of Separation: <strong className="text-slate-200">{shortestPath.path.length - 1}</strong></span>
            </div>
            
            <div className="flex flex-wrap items-center gap-2 py-2">
              {shortestPath.path.map((nodeId, idx) => {
                const node = rawNodes.find((n: any) => n.id === nodeId);
                return (
                  <div key={nodeId} className="flex items-center gap-2">
                    <Badge variant={node?.type === 'document' ? 'info' : node?.type === 'person' ? 'purple' : 'default'} size="sm">
                      {node?.label || node?.name || nodeId}
                    </Badge>
                    {idx < shortestPath.path.length - 1 && (
                      <ArrowRight className="h-3 w-3 text-slate-600" />
                    )}
                  </div>
                );
              })}
            </div>

            <div className="flex justify-between items-center text-[10px] text-slate-500 border-t border-slate-800/60 pt-2 mt-1">
              <span className="italic">Path highlighted on Knowledge Graph</span>
              <span>Total Relationship Weight: <strong className="text-slate-300 font-medium">{shortestPath.totalWeight}</strong></span>
            </div>
          </div>
        ) : (
          source && target && (
            <div className="text-center text-xs text-slate-500 py-4 bg-slate-950/20 rounded-xl border border-dashed border-slate-800">
              No connection found between these two entities.
            </div>
          )
        )}
      </div>
    </div>
  );
}

