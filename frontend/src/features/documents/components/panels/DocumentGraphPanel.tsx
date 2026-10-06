import { useState, useEffect } from 'react';
import { Share2, Users, Building, Calendar, MapPin, Scale, Hash, DollarSign, FileText, Loader2, ArrowRight } from 'lucide-react';
import { Badge } from '@/components/atoms/Badge';
import api from '@/lib/api';

interface GraphNode {
  id: string;
  label: string;
  type: string;
  importance?: number;
  description?: string;
  metadata?: Record<string, string>;
}

interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  type: string;
  weight: number;
}

interface DocumentGraphPanelProps {
  doc?: any;
}

const typeIcons: Record<string, React.ElementType> = {
  people: Users,
  organizations: Building,
  dates: Calendar,
  locations: MapPin,
  courts: Scale,
  case_numbers: Hash,
  money: DollarSign,
  document: FileText,
};

const typeColors: Record<string, { bg: string; text: string; border: string }> = {
  people: { bg: 'bg-indigo-500/10', text: 'text-indigo-400', border: 'border-indigo-500/20' },
  organizations: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/20' },
  locations: { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/20' },
  dates: { bg: 'bg-cyan-500/10', text: 'text-cyan-400', border: 'border-cyan-500/20' },
  courts: { bg: 'bg-purple-500/10', text: 'text-purple-400', border: 'border-purple-500/20' },
  case_numbers: { bg: 'bg-slate-500/10', text: 'text-slate-400', border: 'border-slate-500/20' },
  money: { bg: 'bg-green-500/10', text: 'text-green-400', border: 'border-green-500/20' },
  document: { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/20' },
};

export function DocumentGraphPanel({ doc }: DocumentGraphPanelProps) {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [selectedEntity, setSelectedEntity] = useState<GraphNode | null>(null);

  useEffect(() => {
    let isMounted = true;
    async function loadDocumentGraph() {
      if (!doc?.id) return;
      setIsLoading(true);
      try {
        const res = await api.get('/graph', {
          params: { documentId: doc.id, minWeight: 0.05 },
        });
        if (isMounted) {
          setNodes(res.data?.nodes || []);
          setEdges(res.data?.edges || []);
        }
      } catch (err) {
        console.error('Failed to load document graph:', err);
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }
    loadDocumentGraph();
    return () => {
      isMounted = false;
    };
  }, [doc?.id]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center text-slate-500">
        <Loader2 className="h-6 w-6 animate-spin text-indigo-400 mb-2" />
        <p className="text-xs font-medium">Extracting document graph neighborhood...</p>
      </div>
    );
  }

  // Filter out the document node itself for the entity list
  const entityNodes = nodes.filter((n) => n.type !== 'document');

  if (entityNodes.length === 0 && edges.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center text-slate-500 rounded-xl bg-slate-900/30 border border-slate-800">
        <Share2 className="h-8 w-8 text-slate-600 mb-2" />
        <h4 className="text-xs font-semibold text-slate-400">No Relationships Indexed</h4>
        <p className="text-[11px] text-slate-500 mt-1 max-w-xs">
          No relational links or co-occurring entities were isolated for this document in the knowledge graph.
        </p>
      </div>
    );
  }

  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

  return (
    <div className="flex flex-col gap-4 text-left">
      {/* Top Telemetry Strip */}
      <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Share2 className="h-4 w-4 text-indigo-400" />
            <span className="text-xs font-bold text-slate-200">Document Graph Neighborhood</span>
          </div>
          <Badge variant="purple" size="xs">
            {entityNodes.length} Entities · {edges.length} Edges
          </Badge>
        </div>
        <p className="text-[11px] text-slate-400 leading-relaxed">
          Knowledge graph links directly connected to <span className="font-semibold text-slate-300">{doc?.original_filename || 'this document'}</span>.
        </p>
      </div>

      {/* Interactive Entity Neighborhood Cards */}
      <div className="space-y-2">
        <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider px-1">
          Connected Entities ({entityNodes.length})
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {entityNodes.map((entity) => {
            const Icon = typeIcons[entity.type] || Users;
            const colors = typeColors[entity.type] || { bg: 'bg-slate-800', text: 'text-slate-300', border: 'border-slate-700' };
            const isSelected = selectedEntity?.id === entity.id;

            return (
              <div
                key={entity.id}
                onClick={() => setSelectedEntity(isSelected ? null : entity)}
                className={`p-2.5 rounded-xl border transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-slate-800/90 border-indigo-500 shadow-md shadow-indigo-500/10'
                    : 'bg-slate-900/40 border-slate-800/80 hover:border-slate-700 hover:bg-slate-900/70'
                }`}
              >
                <div className="flex items-start gap-2">
                  <div className={`p-1.5 rounded-lg ${colors.bg} ${colors.text} shrink-0`}>
                    <Icon className="h-3.5 w-3.5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="text-xs font-semibold text-slate-200 truncate">{entity.label}</div>
                    <div className="text-[10px] text-slate-400 capitalize">{entity.type}</div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Relational Edge Links */}
      <div className="space-y-2 pt-2">
        <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider px-1">
          Extracted Relationships ({edges.length})
        </div>
        <div className="space-y-1.5 max-h-[300px] overflow-y-auto pr-1">
          {edges.map((edge) => {
            const src = nodeMap.get(edge.source);
            const tgt = nodeMap.get(edge.target);

            return (
              <div
                key={edge.id}
                className="p-2.5 rounded-xl bg-slate-900/40 border border-slate-800/70 text-xs flex items-center justify-between gap-2"
              >
                <div className="flex items-center gap-1.5 min-w-0 flex-1">
                  <span className="font-medium text-slate-300 truncate max-w-[120px]">
                    {src?.label || edge.source}
                  </span>
                  <div className="flex items-center gap-1 text-[10px] text-indigo-400 font-mono bg-indigo-500/10 px-1.5 py-0.5 rounded border border-indigo-500/20 shrink-0">
                    <ArrowRight className="h-2.5 w-2.5" />
                    <span>{edge.label || edge.type}</span>
                  </div>
                  <span className="font-medium text-slate-300 truncate max-w-[120px]">
                    {tgt?.label || edge.target}
                  </span>
                </div>
                <div className="text-[10px] font-mono text-slate-500 shrink-0">
                  w={edge.weight.toFixed(2)}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
