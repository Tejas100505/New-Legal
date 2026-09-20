import { create } from 'zustand';
import type { GraphFilters, GraphLayoutMode, ShortestPathResult } from '@/types';
import type { Node, Edge } from '@xyflow/react';
import api from '@/lib/api';

interface GraphState {
  nodes: Node[];
  edges: Edge[];
  rawNodes: any[];
  rawEdges: any[];
  source: 'live' | 'mock_fallback';
  selectedNodeId: string | null;
  filters: GraphFilters;
  layoutMode: GraphLayoutMode;
  isClustered: boolean;
  shortestPath: ShortestPathResult | null;
  highlightedNeighbors: string[];
  
  // Actions
  fetchGraph: () => Promise<void>;
  setNodes: (nodes: Node[]) => void;
  setEdges: (edges: Edge[]) => void;
  selectNode: (nodeId: string | null) => void;
  setFilters: (filters: Partial<GraphFilters>) => void;
  setLayoutMode: (mode: GraphLayoutMode) => void;
  toggleClustering: () => void;
  findShortestPath: (sourceId: string, targetId: string) => void;
  clearShortestPath: () => void;
  highlightNeighbors: (nodeId: string) => void;
  clearHighlights: () => void;
  expandNode: (nodeId: string) => void;
}

function normalizeNodeType(rawType: any): string {
  const s = String(rawType || '').toLowerCase().trim();
  if (s.startsWith('org') || s === 'organizations') return 'organization';
  if (s.startsWith('peop') || s === 'person' || s === 'people') return 'person';
  if (s.startsWith('case')) return 'case';
  if (s.startsWith('doc')) return 'document';
  if (s.startsWith('loc')) return 'location';
  if (s.startsWith('event') || s.startsWith('date')) return 'event';
  if (s.startsWith('contract')) return 'contract';
  if (s.startsWith('email')) return 'email';
  if (s.includes('evidence') || s.startsWith('money')) return 'evidence';
  if (s.includes('legal') || s.startsWith('court')) return 'legal_issue';
  return 'evidence';
}

export const useGraphStore = create<GraphState>((set, get) => ({
  nodes: [],
  edges: [],
  rawNodes: [],
  rawEdges: [],
  source: 'mock_fallback',
  selectedNodeId: null,
  filters: {
    nodeTypes: ['document', 'person', 'organization', 'evidence', 'email', 'contract', 'legal_issue', 'event', 'location', 'case'],
    edgeTypes: ['mentions', 'ownership', 'similarity', 'communication', 'citation', 'references', 'evidence_link', 'relationship'],
    minWeight: 0.1,
    caseId: null,
    searchQuery: '',
    dateRange: null,
  },
  layoutMode: 'force',
  isClustered: false,
  shortestPath: null,
  highlightedNeighbors: [],

  fetchGraph: async () => {
    try {
      const response = await api.get('/graph');
      const rawNodesList = response.data.nodes || [];
      const rawLinksList = response.data.links || response.data.edges || [];

      // 1. Normalize nodes to ensure valid IDs, labels, and lowercase singular types
      const normalizedNodes = rawNodesList.map((n: any) => ({
        ...n,
        id: String(n.id || n.name),
        label: n.label || n.name || n.id || 'Entity',
        type: normalizeNodeType(n.type),
      }));

      // 2. Normalize and deduplicate edges into clean format
      const seenEdges = new Set<string>();
      const normalizedEdges: any[] = [];
      for (let i = 0; i < rawLinksList.length; i++) {
        const l = rawLinksList[i];
        const src = String(l.source);
        const tgt = String(l.target);
        if (!src || !tgt) continue;

        const key = `${src}__${tgt}`;
        if (seenEdges.has(key)) continue;
        seenEdges.add(key);

        const rawRel = String(l.relation || l.label || l.type || 'mentions').toLowerCase();
        const rel = rawRel.startsWith('mention') ? 'mentions' : rawRel;
        normalizedEdges.push({
          id: l.id || `edge_${i}_${src.replace(/[^a-zA-Z0-9]/g, '_')}_${tgt.replace(/[^a-zA-Z0-9]/g, '_')}`,
          source: src,
          target: tgt,
          label: l.label || l.relation || 'mentions',
          type: rel,
          weight: typeof l.weight === 'number' ? l.weight : 0.85,
          metadata: l.metadata || {},
        });
      }

      set({
        rawNodes: normalizedNodes,
        rawEdges: normalizedEdges,
        source: response.data.source || 'live'
      });
    } catch (err) {
      console.error('Failed to fetch graph data from backend, falling back to mock data:', err);
      set({
        rawNodes: [],
        rawEdges: [],
        source: 'mock_fallback'
      });
    }
  },

  setNodes: (nodes) => set({ nodes }),
  setEdges: (edges) => set({ edges }),
  
  selectNode: (nodeId) => {
    set({ selectedNodeId: nodeId });
    if (nodeId) {
      get().highlightNeighbors(nodeId);
    } else {
      get().clearHighlights();
    }
  },

  setFilters: (newFilters) => set((state) => ({ filters: { ...state.filters, ...newFilters } })),
  setLayoutMode: (layoutMode) => set({ layoutMode }),
  toggleClustering: () => set((state) => ({ isClustered: !state.isClustered })),
  
  findShortestPath: (sourceId, targetId) => {
    if (!sourceId || !targetId || sourceId === targetId) {
      set({ shortestPath: null });
      return;
    }

    // Weighted Dijkstra pathfinding over relationship graph
    // Distance formula: distance = 1 / Math.max(0.01, edge.weight)
    // Minimizing distance favors paths with the strongest relationship connectivity
    const adjList = new Map<string, Array<{ target: string; edgeId: string; weight: number; distance: number }>>();

    get().rawEdges.forEach((edge: any) => {
      const src = String(edge.source);
      const tgt = String(edge.target);
      const weight = typeof edge.weight === 'number' ? edge.weight : 0.85;
      const distance = 1.0 / Math.max(0.01, weight);

      if (!adjList.has(src)) adjList.set(src, []);
      if (!adjList.has(tgt)) adjList.set(tgt, []);

      adjList.get(src)!.push({ target: tgt, edgeId: edge.id, weight, distance });
      adjList.get(tgt)!.push({ target: src, edgeId: edge.id, weight, distance }); // Undirected pathfinding
    });

    // Min-heap for efficient Dijkstra traversal
    class MinHeap {
      private data: Array<{ nodeId: string; dist: number }> = [];

      push(item: { nodeId: string; dist: number }) {
        this.data.push(item);
        let idx = this.data.length - 1;
        while (idx > 0) {
          const parentIdx = (idx - 1) >> 1;
          if (this.data[idx].dist >= this.data[parentIdx].dist) break;
          const tmp = this.data[idx];
          this.data[idx] = this.data[parentIdx];
          this.data[parentIdx] = tmp;
          idx = parentIdx;
        }
      }

      pop(): { nodeId: string; dist: number } | undefined {
        if (this.data.length === 0) return undefined;
        const top = this.data[0];
        const bottom = this.data.pop()!;
        if (this.data.length > 0) {
          this.data[0] = bottom;
          let idx = 0;
          const len = this.data.length;
          while (true) {
            const leftIdx = (idx << 1) + 1;
            const rightIdx = leftIdx + 1;
            let swapIdx = -1;

            if (leftIdx < len && this.data[leftIdx].dist < this.data[idx].dist) {
              swapIdx = leftIdx;
            }
            if (
              rightIdx < len &&
              this.data[rightIdx].dist < (swapIdx === -1 ? this.data[idx].dist : this.data[leftIdx].dist)
            ) {
              swapIdx = rightIdx;
            }

            if (swapIdx === -1) break;
            const tmp = this.data[idx];
            this.data[idx] = this.data[swapIdx];
            this.data[swapIdx] = tmp;
            idx = swapIdx;
          }
        }
        return top;
      }

      get size(): number {
        return this.data.length;
      }
    }

    const distances = new Map<string, number>();
    const parentMap = new Map<string, { node: string; edgeId: string; weight: number } | null>();
    const heap = new MinHeap();

    distances.set(sourceId, 0);
    parentMap.set(sourceId, null);
    heap.push({ nodeId: sourceId, dist: 0 });

    let found = false;
    while (heap.size > 0) {
      const current = heap.pop()!;
      if (current.dist > (distances.get(current.nodeId) ?? Infinity)) {
        continue;
      }
      if (current.nodeId === targetId) {
        found = true;
        break;
      }

      const neighbors = adjList.get(current.nodeId) || [];
      for (const edge of neighbors) {
        const altDist = current.dist + edge.distance;
        const knownDist = distances.get(edge.target) ?? Infinity;
        if (altDist < knownDist) {
          distances.set(edge.target, altDist);
          parentMap.set(edge.target, { node: current.nodeId, edgeId: edge.edgeId, weight: edge.weight });
          heap.push({ nodeId: edge.target, dist: altDist });
        }
      }
    }

    if (found) {
      const pathNodes: string[] = [];
      const pathEdges: string[] = [];
      let totalWeight = 0;
      let curr = targetId;

      while (curr !== sourceId) {
        const step = parentMap.get(curr);
        if (step) {
          pathNodes.unshift(curr);
          pathEdges.unshift(step.edgeId);
          totalWeight += step.weight;
          curr = step.node;
        } else {
          break;
        }
      }
      pathNodes.unshift(sourceId);

      set({
        shortestPath: {
          path: pathNodes,
          edges: pathEdges,
          totalWeight: parseFloat(totalWeight.toFixed(4)),
        }
      });
    } else {
      set({ shortestPath: null });
    }
  },

  clearShortestPath: () => set({ shortestPath: null }),

  highlightNeighbors: (nodeId) => {
    const connectedNodeIds = new Set<string>([nodeId]);
    get().rawEdges.forEach((edge: any) => {
      if (edge.source === nodeId) connectedNodeIds.add(edge.target);
      if (edge.target === nodeId) connectedNodeIds.add(edge.source);
    });
    set({ highlightedNeighbors: Array.from(connectedNodeIds) });
  },

  clearHighlights: () => set({ highlightedNeighbors: [] }),

  expandNode: (nodeId) => {
    const currentNodes = get().nodes;
    const currentEdges = get().edges;
    
    // Find all edges connected to nodeId in rawEdges
    const connectedEdges = (get().rawEdges as any[]).filter(
      (edge: any) => edge.source === nodeId || edge.target === nodeId
    );

    const nodesToAdd: Node[] = [];
    const edgesToAdd: Edge[] = [];

    connectedEdges.forEach((edge: any) => {
      const otherNodeId = edge.source === nodeId ? edge.target : edge.source;
      
      // If edge not already in canvas, add it
      if (!currentEdges.some((e) => e.id === edge.id)) {
        edgesToAdd.push({
          id: edge.id,
          source: edge.source,
          target: edge.target,
          label: edge.label,
          type: 'straight',
          animated: true,
          style: { stroke: '#6366f1', strokeWidth: 2 },
        });
      }

      // If node not already in canvas, add it
      if (!currentNodes.some((n) => n.id === otherNodeId)) {
        const mockNode = (get().rawNodes as any[]).find((n: any) => n.id === otherNodeId);
        if (mockNode) {
          const isDoc = mockNode.type === 'document';
          nodesToAdd.push({
            id: mockNode.id,
            type: 'customNode',
            position: {
              x: (currentNodes.find((n) => n.id === nodeId)?.position.x || 0) + (Math.random() - 0.5) * 350,
              y: (currentNodes.find((n) => n.id === nodeId)?.position.y || 0) + (Math.random() - 0.5) * 350,
            },
            data: { 
              label: mockNode.label || mockNode.name || mockNode.id, 
              type: mockNode.type || 'document',
              importance: typeof mockNode.importance === 'number' ? mockNode.importance : (isDoc ? 0.9 : 0.05),
              likelyMisclassified: mockNode.metadata?.likely_misclassified === 'true' || mockNode.metadata?.likely_misclassified === true,
              isHighlighted: true,
              isDimmed: false,
              isPathNode: false,
              metadata: mockNode.metadata || {},
              description: mockNode.description
            },
          });
        }
      }
    });

    if (nodesToAdd.length > 0 || edgesToAdd.length > 0) {
      set({
        nodes: [...currentNodes, ...nodesToAdd],
        edges: [...currentEdges, ...edgesToAdd],
      });
    }
  },
}));


