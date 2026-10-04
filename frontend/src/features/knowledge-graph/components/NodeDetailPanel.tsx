import { useGraphStore } from '../store/graphStore';
import { GRAPH_NODE_COLORS } from '@/lib/constants';
import { X, Info, FileText, HelpCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export function NodeDetailPanel() {
  const selectedNodeId = useGraphStore((s) => s.selectedNodeId);
  const selectNode = useGraphStore((s) => s.selectNode);
  const expandNode = useGraphStore((s) => s.expandNode);
  const rawNodes = useGraphStore((s) => s.rawNodes);
  const rawEdges = useGraphStore((s) => s.rawEdges);
  const navigate = useNavigate();

  if (!selectedNodeId) {
    return (
      <div className="w-80 bg-slate-900/50 backdrop-blur-xl border border-slate-800/80 rounded-xl p-6 flex flex-col items-center justify-center text-center gap-2 h-full max-h-[calc(100vh-14rem)]">
        <HelpCircle className="h-8 w-8 text-slate-700" />
        <p className="text-sm font-medium text-slate-400">No entity selected</p>
        <p className="text-xs text-slate-600 max-w-[200px]">Click any node on the graph to inspect metadata, citations, and relationships.</p>
      </div>
    );
  }

  const node = rawNodes.find((n: any) => n.id === selectedNodeId);
  if (!node) return null;

  const color = GRAPH_NODE_COLORS[node.type] || '#64748b';

  // Find relationships
  const connections = rawEdges.filter(
    (edge: any) => edge.source === selectedNodeId || edge.target === selectedNodeId
  ).map((edge: any) => {
    const isSource = edge.source === selectedNodeId;
    const targetId = isSource ? edge.target : edge.source;
    const targetNode = rawNodes.find((n: any) => n.id === targetId);
    return {
      edgeId: edge.id,
      label: edge.label || edge.relation || 'relates_to',
      type: edge.type || 'relationship',
      weight: edge.weight ?? 0.85,
      targetName: targetNode?.label || targetNode?.name || targetId,
      targetType: targetNode?.type || 'entity',
    };
  });

  return (
    <div className="w-80 bg-slate-900/50 backdrop-blur-xl border border-slate-800/80 rounded-xl p-4 flex flex-col gap-4 overflow-y-auto max-h-[calc(100vh-14rem)]">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center gap-2">
          <Info className="h-4 w-4 text-indigo-400" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">Entity Details</h3>
        </div>
        <button 
          onClick={() => selectNode(null)}
          className="p-1 rounded hover:bg-slate-800 text-slate-500 hover:text-slate-300 transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Header Info */}
      <div className="flex flex-col gap-2">
        <div className="flex items-start justify-between gap-2">
          <h4 className="text-base font-bold text-slate-100">{node.label}</h4>
          <span 
            className="px-2 py-0.5 rounded-full text-[10px] font-semibold border capitalize shrink-0" 
            style={{ borderColor: `${color}40`, color }}
          >
            {node.type.replace('_', ' ')}
          </span>
        </div>
        {node.metadata?.likely_misclassified === 'true' && (
          <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-left">
            <p className="text-[11px] text-amber-300 font-medium">Type may be inaccurate — resembles an email address or single-word fragment</p>
            <p className="text-[10px] text-amber-400/80 mt-0.5">This node is classified as an organization, but its label matches an email pattern or bare single-token fragment.</p>
          </div>
        )}
        {node.description && (
          <p className="text-xs text-slate-400 leading-relaxed bg-slate-950/40 p-2.5 rounded-lg border border-slate-850">
            {node.description}
          </p>
        )}
      </div>

      {/* Expansion button */}
      <button 
        onClick={() => expandNode(node.id)}
        className="w-full py-1.5 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 text-xs font-medium border border-indigo-500/20 transition-all active:scale-95"
      >
        Expand Connections
      </button>

      {/* Properties Metadata */}
      <div className="flex flex-col gap-2">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Properties</span>
        <div className="flex flex-col gap-1.5">
          {Object.entries(node.metadata).map(([key, val]) => (
            <div key={key} className="flex justify-between items-center text-xs p-1.5 rounded bg-slate-950/20">
              <span className="text-slate-500 capitalize">{key.replace(/([A-Z])/g, ' $1')}</span>
              <span className="font-medium text-slate-300 max-w-[150px] truncate" title={String(val)}>{String(val)}</span>
            </div>
          ))}
          {node.caseId && (
            <div className="flex justify-between items-center text-xs p-1.5 rounded bg-slate-950/20">
              <span className="text-slate-500">Case Scope</span>
              <span className="font-medium text-indigo-400">{node.caseId}</span>
            </div>
          )}
        </div>
      </div>

      {/* Linked Evidences or Documents */}
      {node.type === 'document' && (
        <div className="flex flex-col gap-2 border-t border-slate-800 pt-3">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Actions</span>
          <button
            onClick={() => {
              const docId = node.metadata?.document_id || node.id.replace('doc_', '');
              navigate(`/documents/${docId}`, {
                state: {
                  caseId: node.caseId || node.metadata?.case_id,
                  returnTab: 'relationships',
                },
              });
            }}
            className="flex items-center justify-center gap-1.5 w-full py-1.5 rounded-lg bg-indigo-600/30 hover:bg-indigo-600/50 border border-indigo-500/40 text-indigo-200 text-xs font-medium transition-all cursor-pointer"
          >
            <FileText className="h-3.5 w-3.5" /> Open in Document Intelligence
          </button>
        </div>
      )}

      {/* Relationships */}
      <div className="flex flex-col gap-2 border-t border-slate-800 pt-3">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Relationships ({connections.length})</span>
        <div className="flex flex-col gap-2 max-h-48 overflow-y-auto pr-1">
          {connections.map((conn) => (
            <div 
              key={conn.edgeId} 
              className="p-2 rounded-lg bg-slate-950/30 border border-slate-850 hover:border-slate-700 transition-colors flex flex-col gap-1 text-left"
            >
              <div className="flex justify-between items-center">
                <span className="text-xs text-slate-300 font-semibold truncate max-w-[130px]" title={conn.targetName}>
                  {conn.targetName}
                </span>
                <span className="text-[9px] text-slate-500 capitalize">{conn.targetType}</span>
              </div>
              <div className="flex justify-between items-center text-[10px] text-slate-500">
                <span className="text-indigo-400 font-medium italic">{conn.label}</span>
                <span>Strength: {(conn.weight * 100).toFixed(0)}%</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
