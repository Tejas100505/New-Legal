import { useCallback } from 'react';
import type { GraphNode, GraphEdge, ShortestPathResult, GraphNodeType } from '@/types';
import type { Node, Edge } from '@xyflow/react';

// Semantic query terms expansion map to simulate natural language search
const SEMANTIC_EXPANSIONS: Record<string, string[]> = {
  'people': ['person', 'employee', 'scientist', 'ceo', 'scientist', 'miller', 'whitfield', 'chen', 'vance', 'ross'],
  'person': ['people', 'employee', 'scientist', 'ceo', 'scientist', 'miller', 'whitfield', 'chen', 'vance', 'ross'],
  'company': ['organization', 'corp', 'industries', 'meridian', 'atlas', 'greenfield', 'partners', 'sec'],
  'organization': ['company', 'corp', 'industries', 'meridian', 'atlas', 'greenfield', 'partners', 'sec'],
  'illegal': ['theft', 'allegation', 'infringement', 'secret', 'breach', 'filiing', 'unauthorized', 'preservation'],
  'theft': ['illegal', 'allegation', 'infringement', 'secret', 'breach', 'unauthorized'],
  'contract': ['nda', 'agreement', 'signed', 'bound', 'compliance', 'consequential'],
  'location': ['san jose', 'austin', 'tx', 'california', 'ca', 'london', 'switzerland'],
  'evidence': ['repo', 'ledger', 'wire', 'transfer', 'recording', 'log', 'security', 'forensic', 'copy', 'disk'],
  'file': ['pdf', 'docx', 'xlsx', 'eml', 'document', 'report', 'blueprint', 'minutes', 'will', 'subpoena'],
};

export function useGraphOperations() {
  // BFS pathfinder
  const findShortestPath = useCallback((
    _rawNodes: { id: string }[],
    rawEdges: GraphEdge[],
    sourceId: string,
    targetId: string
  ): ShortestPathResult | null => {
    if (!sourceId || !targetId) return null;

    const adjList: Record<string, Array<{ target: string; edgeId: string; weight: number }>> = {};

    rawEdges.forEach((edge) => {
      if (!adjList[edge.source]) adjList[edge.source] = [];
      if (!adjList[edge.target]) adjList[edge.target] = [];
      adjList[edge.source].push({ target: edge.target, edgeId: edge.id, weight: edge.weight });
      adjList[edge.target].push({ target: edge.source, edgeId: edge.id, weight: edge.weight }); // Undirected
    });

    const queue: string[] = [sourceId];
    const visited = new Set<string>([sourceId]);
    const parentMap: Record<string, { node: string; edgeId: string; weight: number } | null> = { [sourceId]: null };

    let found = false;
    while (queue.length > 0) {
      const curr = queue.shift()!;
      if (curr === targetId) {
        found = true;
        break;
      }

      const neighbors = adjList[curr] || [];
      for (const edge of neighbors) {
        if (!visited.has(edge.target)) {
          visited.add(edge.target);
          parentMap[edge.target] = { node: curr, edgeId: edge.edgeId, weight: edge.weight };
          queue.push(edge.target);
        }
      }
    }

    if (found) {
      const pathNodes: string[] = [];
      const pathEdges: string[] = [];
      let totalWeight = 0;
      let curr = targetId;

      while (curr !== sourceId) {
        const step = parentMap[curr];
        if (step) {
          pathNodes.unshift(curr);
          pathEdges.unshift(step.edgeId);
          totalWeight += step.weight;
          curr = step.node;
        }
      }
      pathNodes.unshift(sourceId);

      return {
        path: pathNodes,
        edges: pathEdges,
        totalWeight: parseFloat(totalWeight.toFixed(2)),
      };
    }
    return null;
  }, []);

  // Fuzzy Semantic Search Matcher
  const computeSemanticScores = useCallback((
    nodes: GraphNode[],
    query: string
  ): Set<string> => {
    const matchedNodeIds = new Set<string>();
    if (!query) {
      nodes.forEach((n) => matchedNodeIds.add(n.id));
      return matchedNodeIds;
    }

    const queryWords = query.toLowerCase().split(/\s+/).filter(Boolean);
    const expandedTerms = new Set<string>(queryWords);

    // Expand search keywords semantically
    queryWords.forEach((word) => {
      if (SEMANTIC_EXPANSIONS[word]) {
        SEMANTIC_EXPANSIONS[word].forEach((term) => expandedTerms.add(term));
      }
    });

    nodes.forEach((n) => {
      let score = 0;
      const label = n.label.toLowerCase();
      const desc = (n.description || '').toLowerCase();
      const type = n.type.toLowerCase();

      // Check expanded keywords
      expandedTerms.forEach((term) => {
        if (label.includes(term)) {
          score += 10;
        }
        if (desc.includes(term)) {
          score += 4;
        }
        if (type.includes(term)) {
          score += 6;
        }
        // Match metadata
        if (n.metadata) {
          Object.values(n.metadata).forEach((val) => {
            if (String(val).toLowerCase().includes(term)) {
              score += 3;
            }
          });
        }
      });

      if (score > 0) {
        matchedNodeIds.add(n.id);
      }
    });

    return matchedNodeIds;
  }, []);

  // Node Clustering positions generator
  const getClusteredLayout = useCallback((
    filteredNodes: Node[],
    filteredEdges: Edge[],
    isClustered: boolean
  ): { clusteredNodes: Node[]; clusteredEdges: Edge[] } => {
    if (!isClustered) {
      return { clusteredNodes: filteredNodes, clusteredEdges: filteredEdges };
    }

    // Group nodes by type
    const groups: Record<GraphNodeType, Node[]> = {} as any;
    filteredNodes.forEach((node) => {
      const type = node.data?.type as GraphNodeType;
      if (!groups[type]) groups[type] = [];
      groups[type].push(node);
    });

    const clusteredNodes: Node[] = [];
    let groupIndex = 0;

    // Layout variables for clusters
    const activeTypes = Object.keys(groups) as GraphNodeType[];
    const cols = Math.ceil(Math.sqrt(activeTypes.length));
    const clusterSpacing = 650;

    activeTypes.forEach((type) => {
      const nodesInType = groups[type];
      if (nodesInType.length === 0) return;

      const clusterX = (groupIndex % cols) * clusterSpacing;
      const clusterY = Math.floor(groupIndex / cols) * clusterSpacing;
      const clusterId = `cluster_${type}`;

      // 1. Create a styled parent group container node
      const parentNode: Node = {
        id: clusterId,
        type: 'group',
        position: { x: clusterX, y: clusterY },
        style: {
          width: 380,
          height: 380,
          backgroundColor: 'rgba(15, 23, 42, 0.15)',
          border: '1.5px dashed rgba(99, 102, 241, 0.25)',
          borderRadius: '16px',
        },
        data: {
          label: `${type.replace('_', ' ').toUpperCase()} CLUSTER`,
          type: 'group',
        },
      };
      clusteredNodes.push(parentNode);

      // 2. Position child nodes circularly inside the parent
      nodesInType.forEach((node, nodeIdx) => {
        const radius = 100;
        const angle = (nodeIdx / nodesInType.length) * 2 * Math.PI;
        // Coordinates relative to parent node
        const childX = 190 + radius * Math.cos(angle) - 75; // center is at 190, 190
        const childY = 190 + radius * Math.sin(angle) - 25;

        clusteredNodes.push({
          ...node,
          parentId: clusterId,
          extent: 'parent',
          position: { x: childX, y: childY },
        });
      });

      groupIndex++;
    });

    return { clusteredNodes, clusteredEdges: filteredEdges };
  }, []);

  return {
    findShortestPath,
    computeSemanticScores,
    getClusteredLayout,
  };
}
