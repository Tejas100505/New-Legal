import { useEffect, useMemo, useCallback, useState } from 'react';
import {
  ReactFlow, Background, Controls, MiniMap,
  useNodesState, useEdgesState, useReactFlow,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useGraphStore } from '../store/graphStore';
import { CustomNode } from './nodes/CustomNode';
import { GRAPH_NODE_COLORS } from '@/lib/constants';
import { useGraphOperations } from '../hooks/useGraphOperations';
import { BookOpen, X } from 'lucide-react';

interface GraphCanvasProps {
  layoutTrigger: number;
  caseId?: string;
}

const nodeTypes = {
  customNode: CustomNode,
};

export function GraphCanvas({ layoutTrigger, caseId }: GraphCanvasProps) {
  const { fitView } = useReactFlow();
  const [nodes, setNodes, onNodesChange] = useNodesState<any>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<any>([]);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [activeCitation, setActiveCitation] = useState<any | null>(null);

  const storeNodes = useGraphStore((s) => s.nodes);
  const storeEdges = useGraphStore((s) => s.edges);
  const setStoreNodes = useGraphStore((s) => s.setNodes);
  const setStoreEdges = useGraphStore((s) => s.setEdges);
  const selectedNodeId = useGraphStore((s) => s.selectedNodeId);
  const selectNode = useGraphStore((s) => s.selectNode);
  const highlightedNeighbors = useGraphStore((s) => s.highlightedNeighbors);
  const shortestPath = useGraphStore((s) => s.shortestPath);
  const filters = useGraphStore((s) => s.filters);
  const layoutMode = useGraphStore((s) => s.layoutMode);
  const isClustered = useGraphStore((s) => s.isClustered);
  const fetchGraph = useGraphStore((s) => s.fetchGraph);
  const rawNodes = useGraphStore((s) => s.rawNodes);
  const rawEdges = useGraphStore((s) => s.rawEdges);
  const source = useGraphStore((s) => s.source);

  const { computeSemanticScores, getClusteredLayout } = useGraphOperations();

  // Load graph data from backend on mount
  useEffect(() => {
    fetchGraph(caseId);
  }, [fetchGraph, caseId]);

  // Sync React Flow nodes and edges back to store
  useEffect(() => {
    setStoreNodes(nodes);
  }, [nodes, setStoreNodes]);

  useEffect(() => {
    setStoreEdges(edges);
  }, [edges, setStoreEdges]);

  // Re-sync local ReactFlow state when store nodes or edges expand
  useEffect(() => {
    if (storeNodes.length > nodes.length) {
      setNodes(storeNodes);
    }
  }, [storeNodes, nodes.length, setNodes]);

  useEffect(() => {
    if (storeEdges.length > edges.length) {
      setEdges(storeEdges);
    }
  }, [storeEdges, edges.length, setEdges]);


  // Compute hovered node neighbors
  const hoveredNeighbors = useMemo(() => {
    if (!hoveredNodeId) return new Set<string>();
    const neighbors = new Set<string>([hoveredNodeId]);
    rawEdges.forEach((edge) => {
      if (edge.source === hoveredNodeId) neighbors.add(edge.target);
      if (edge.target === hoveredNodeId) neighbors.add(edge.source);
    });
    return neighbors;
  }, [hoveredNodeId, rawEdges]);

  // Compute entity and document counts from rawNodes
  const entityCount = useMemo(() => rawNodes.filter((n: any) => !String(n.id).startsWith('doc_') && n.type !== 'document').length, [rawNodes]);
  const docCount = useMemo(() => rawNodes.filter((n: any) => String(n.id).startsWith('doc_') || n.type === 'document').length, [rawNodes]);

  // Compute and apply layouts
  const applyLayout = useCallback((rawNodesInput: any[], rawEdgesInput: any[]) => {
    if (!rawNodesInput || rawNodesInput.length === 0) {
      setNodes([]);
      setEdges([]);
      return;
    }

    // 1. Calculate node connectivity degrees across all edges
    const nodeDegree: Record<string, number> = {};
    for (let i = 0; i < rawEdgesInput.length; i++) {
      const e = rawEdgesInput[i];
      nodeDegree[e.source] = (nodeDegree[e.source] || 0) + 1;
      nodeDegree[e.target] = (nodeDegree[e.target] || 0) + 1;
    }

    // 2. Run semantic search fuzzy matcher
    const matchedIds = computeSemanticScores(rawNodesInput, filters.searchQuery);

    // 3. Filter nodes by user-selected entity types and query match
    let filteredNodes = rawNodesInput.filter((n) => {
      const nType = (n.type || '').toLowerCase();
      if (!filters.nodeTypes.some((t) => t.toLowerCase() === nType || nType.startsWith(t))) return false;
      return matchedIds.has(n.id);
    });

    // 4. Sort nodes by connectivity degree so the most central, critical entities appear first
    filteredNodes.sort((a, b) => (nodeDegree[b.id] || 0) - (nodeDegree[a.id] || 0));

    // 5. Cap active viewport nodes to ensure fast 60fps rendering without choking SVG DOM
    const MAX_ACTIVE_NODES = filters.searchQuery ? 80 : 60;
    let visibleNodes = filteredNodes.slice(0, MAX_ACTIVE_NODES);

    // Ensure selected node or shortest path nodes are always included in visibleNodes
    const priorityNodeIds = new Set<string>();
    if (selectedNodeId) priorityNodeIds.add(selectedNodeId);
    if (shortestPath?.path) shortestPath.path.forEach((id) => priorityNodeIds.add(id));

    priorityNodeIds.forEach((pId) => {
      if (!visibleNodes.some((n) => n.id === pId)) {
        const found = rawNodesInput.find((n) => n.id === pId);
        if (found) visibleNodes.unshift(found);
      }
    });

    const activeNodeIds = new Set(visibleNodes.map((n) => n.id));

    // 6. Filter edges connecting active nodes
    let filteredEdges = rawEdgesInput.filter((e) => {
      const eType = (e.type || e.relation || 'mentions').toLowerCase();
      if (!filters.edgeTypes.some((t) => t.toLowerCase() === eType || eType.startsWith(t.toLowerCase()))) return false;
      const weight = typeof e.weight === 'number' ? e.weight : 0.85;
      if (weight < filters.minWeight) return false;
      return activeNodeIds.has(e.source) && activeNodeIds.has(e.target);
    });

    // Cap edges to top 150 for clarity and SVG performance
    if (filteredEdges.length > 150) {
      filteredEdges = filteredEdges.slice(0, 150);
    }

    // 7. Compute layout coordinates
    const layoutNodes = visibleNodes.map((n, idx) => {
      let x = 0;
      let y = 0;

      if (layoutMode === 'grid') {
        const cols = Math.ceil(Math.sqrt(visibleNodes.length));
        x = (idx % cols) * 260;
        y = Math.floor(idx / cols) * 150;
      } else if (layoutMode === 'radial') {
        const radius = 220 + (idx % 3) * 130;
        const angle = (idx / (visibleNodes.length || 1)) * 2 * Math.PI;
        x = radius * Math.cos(angle) + 400;
        y = radius * Math.sin(angle) + 300;
      } else if (layoutMode === 'hierarchical' || layoutMode === 'dagre') {
        const ranks: Record<string, number> = {
          case: 0,
          document: 1,
          contract: 1,
          email: 1,
          legal_issue: 2,
          evidence: 2,
          person: 3,
          organization: 3,
          event: 4,
          location: 4,
        };
        const rank = ranks[n.type] ?? 2;
        const siblings = visibleNodes.filter((node) => (ranks[node.type] ?? 2) === rank);
        const siblingIdx = siblings.findIndex((node) => node.id === n.id);
        
        x = rank * 280;
        y = siblingIdx * 110 - (siblings.length * 55) + 300;
      } else {
        // Force-directed positioning distributed across concentric rings
        const count = visibleNodes.length || 1;
        const angle = (idx / count) * 2 * Math.PI;
        const radius = Math.min(750, 140 + Math.sqrt(idx) * 60);
        x = 500 + radius * Math.cos(angle);
        y = 400 + radius * Math.sin(angle);
      }

      // Check highlighted/dimmed states
      const isPathNode = shortestPath?.path.includes(n.id);
      const activeActiveNodeId = hoveredNodeId || selectedNodeId;
      const activeNeighbors = hoveredNodeId ? hoveredNeighbors : new Set(highlightedNeighbors);

      const isHighlighted = activeActiveNodeId ? activeNeighbors.has(n.id) : false;
      const isDimmed = activeActiveNodeId ? !activeNeighbors.has(n.id) && !isPathNode : false;

      return {
        id: n.id,
        type: 'customNode',
        position: { x, y },
        data: {
          label: n.label || n.name || n.id,
          type: n.type || 'document',
          importance: typeof n.importance === 'number' ? n.importance : 0.05,
          likelyMisclassified: n.metadata?.likely_misclassified === 'true' || n.metadata?.likely_misclassified === true,
          isHighlighted,
          isDimmed,
          isPathNode,
        },
      };
    });

    const layoutEdges = filteredEdges.map((e) => {
      const isPathEdge = shortestPath?.edges.includes(e.id);
      const activeActiveNodeId = hoveredNodeId || selectedNodeId;
      
      const isHighlighted = activeActiveNodeId && (e.source === activeActiveNodeId || e.target === activeActiveNodeId);
      const isDimmed = activeActiveNodeId && !isHighlighted && !isPathEdge;

      return {
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label,
        animated: Boolean(isPathEdge || isHighlighted),
        type: 'straight',
        style: {
          stroke: isPathEdge 
            ? '#10b981' 
            : isHighlighted 
            ? '#6366f1' 
            : isDimmed 
            ? '#33415520' 
            : '#47556960',
          strokeWidth: isPathEdge || isHighlighted ? 2.5 : 1,
        },
      };
    });

    // 8. Generate clustered container node groupings if enabled
    const { clusteredNodes, clusteredEdges } = getClusteredLayout(layoutNodes, layoutEdges, isClustered);

    setNodes(clusteredNodes);
    setEdges(clusteredEdges);
    if (clusteredNodes.length > 0) {
      setTimeout(() => {
        fitView({ padding: 0.2, duration: 400 });
      }, 50);
    }
  }, [filters, layoutMode, selectedNodeId, highlightedNeighbors, shortestPath, hoveredNodeId, hoveredNeighbors, isClustered, computeSemanticScores, getClusteredLayout, setNodes, setEdges, fitView]);

  // Re-calculate layouts
  useEffect(() => {
    if (rawNodes && rawNodes.length > 0) {
      applyLayout(rawNodes, rawEdges);
    } else {
      applyLayout([], []);
    }
  }, [applyLayout, layoutTrigger, rawNodes, rawEdges]);

  const onNodeClick = (_: React.MouseEvent, node: any) => {
    selectNode(node.id);
  };

  const onPaneClick = () => {
    selectNode(null);
    setActiveCitation(null);
  };

  const onNodeMouseEnter = (_: React.MouseEvent, node: any) => {
    setHoveredNodeId(node.id);
  };

  const onNodeMouseLeave = () => {
    setHoveredNodeId(null);
  };

  const onEdgeClick = (_: React.MouseEvent, edge: any) => {
    const rawEdge = rawEdges.find((e: any) => e.id === edge.id);
    if (rawEdge) {
      const sourceNode = rawNodes.find((n: any) => n.id === rawEdge.source);
      const targetNode = rawNodes.find((n: any) => n.id === rawEdge.target);
      
      setActiveCitation({
        ...rawEdge,
        sourceName: sourceNode?.label || sourceNode?.name || rawEdge.source,
        targetName: targetNode?.label || targetNode?.name || rawEdge.target,
        excerpt: rawEdge.description || `Verified relationship: ${sourceNode?.label || rawEdge.source} -> ${rawEdge.label || rawEdge.relation} -> ${targetNode?.label || rawEdge.target}.`,
        date: rawEdge.metadata?.date || '2026-09-07',
        weight: rawEdge.weight ?? 0.85,
      });
    }
  };

  return (
    <div className="w-full h-full relative" style={{ minHeight: '500px' }}>
      {/* Status Badges */}
      <div className="absolute top-4 right-4 z-10 flex items-center gap-2">
        {rawNodes.length > 0 && (
          <div className="px-2.5 py-1.5 rounded-lg text-xs font-medium backdrop-blur-md border bg-slate-900/80 border-slate-750/50 text-slate-300">
            Showing <strong className="text-indigo-400">{nodes.length}</strong> active nodes (<strong className="text-slate-200">{entityCount}</strong> entities, <strong className="text-slate-200">{docCount}</strong> docs)
          </div>
        )}
        <div className="px-3 py-1.5 rounded-lg text-xs font-semibold backdrop-blur-md border shadow-lg flex items-center gap-1.5 cursor-default select-none transition-all duration-300 bg-slate-900/80 border-slate-750/50">
          <span className={`h-2 w-2 rounded-full ${source === 'live' ? 'bg-emerald-500 shadow-[0_0_8px_#10b981]' : 'bg-amber-500 shadow-[0_0_8px_#f59e0b]'}`} />
          <span className={source === 'live' ? 'text-emerald-400' : 'text-amber-400'}>
            {source === 'live' ? 'Live DB Data' : 'Demo Fallback'}
          </span>
        </div>
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        onNodeMouseEnter={onNodeMouseEnter}
        onNodeMouseLeave={onNodeMouseLeave}
        onEdgeClick={onEdgeClick}
        fitView
        onlyRenderVisibleElements={true}
        minZoom={0.1}
        maxZoom={2.5}
        attributionPosition="bottom-left"
        proOptions={{ hideAttribution: true }}
        style={{ backgroundColor: '#0a0e1a' }}
      >
        <Background color="#1e293b40" gap={24} size={1} />
        <Controls
          style={{
            borderRadius: '12px',
            overflow: 'hidden',
            border: '1px solid rgba(148, 163, 184, 0.1)',
          }}
        />
        <MiniMap
          style={{
            backgroundColor: '#0f172a',
            borderRadius: '8px',
            border: '1px solid rgba(148, 163, 184, 0.1)',
          }}
          maskColor="rgba(0, 0, 0, 0.6)"
          nodeColor={(n: any) => GRAPH_NODE_COLORS[n.data?.type] || '#6366f1'}
        />
      </ReactFlow>

      {/* Citation Preview Glassmorphic Overlay Panel */}
      {activeCitation && (
        <div className="absolute bottom-6 left-6 right-6 md:left-1/2 md:-translate-x-1/2 md:w-[480px] bg-slate-900/90 backdrop-blur-md border border-slate-700/80 rounded-xl p-4 shadow-2xl z-20 flex flex-col gap-2">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center gap-2 text-indigo-400">
              <BookOpen className="h-4 w-4" />
              <span className="text-xs font-bold uppercase tracking-wider">Citation Evidence Link Preview</span>
            </div>
            <button 
              onClick={() => setActiveCitation(null)}
              className="text-slate-500 hover:text-slate-300 transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="flex flex-col gap-1">
            <p className="text-xs font-semibold text-slate-100">
              Source: <span className="text-slate-400 font-normal">{activeCitation.sourceName}</span>
            </p>
            <p className="text-xs font-semibold text-slate-100">
              Cites Precedent: <span className="text-indigo-400 font-normal">{activeCitation.targetName}</span>
            </p>
            <div className="bg-slate-950/50 p-2.5 rounded-lg border border-slate-850 text-xs italic text-slate-300 leading-normal mt-1">
              "{activeCitation.excerpt}"
            </div>
          </div>
          <div className="flex justify-between items-center text-[10px] text-slate-500 mt-1">
            <span>Citation Strength: <strong>{(activeCitation.weight * 100).toFixed(0)}%</strong></span>
            <span>Date Logged: {activeCitation.date}</span>
          </div>
        </div>
      )}
    </div>
  );
}
