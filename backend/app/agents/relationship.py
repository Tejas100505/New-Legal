from typing import Any, Dict, List
from pydantic import BaseModel
import networkx as nx

from app.agents.base import BaseAgent, AgentException
from loguru import logger


class RelationshipInput(BaseModel):
    document_id: str
    entities: Dict[str, List[str]] # Output from EntityExtractionAgent


class RelationshipOutput(BaseModel):
    document_id: str
    graph_data: Dict[str, Any] # Node-link format
    confidence_score: float


class RelationshipAgent(BaseAgent[RelationshipInput, RelationshipOutput]):
    """
    Builds Relationship graphs using NetworkX.
    Nodes: Documents, People, Organizations, Evidence, Cases
    Edges: mentions, ownership, communication, similarity
    """
    
    def __init__(self):
        super().__init__(
            name="RelationshipAgent",
            prompt_version="1.0.0",
            input_model=RelationshipInput,
            output_model=RelationshipOutput,
        )

    def _build_graph(self, document_id: str, entities: Dict[str, List[str]]) -> nx.Graph:
        G = nx.Graph()
        
        # Add central document node
        G.add_node(document_id, type="Document", label=document_id)
        
        # Map entity lists to types
        mapping = {
            "people": "People",
            "organizations": "Organizations",
            "case_numbers": "Cases",
        }
        
        for key, ntype in mapping.items():
            for entity in entities.get(key, []):
                node_id = f"{ntype}_{entity}"
                G.add_node(node_id, type=ntype, label=entity)
                # Relationship: Document mentions Entity
                G.add_edge(document_id, node_id, relation="mentions")
                
        # Mock additional edges based on co-occurrence in a real scenario
        # e.g., if a Person and Organization are both in the doc, maybe 'ownership' or 'communication'
        people = entities.get("people", [])
        orgs = entities.get("organizations", [])
        
        if people and orgs:
            for p in people:
                for o in orgs:
                    p_id = f"People_{p}"
                    o_id = f"Organizations_{o}"
                    G.add_edge(p_id, o_id, relation="communication")
                    
        return G

    async def _execute(self, validated_input: RelationshipInput) -> dict:
        logger.info(f"[{self.name}] Building relationship graph for {validated_input.document_id}")
        
        try:
            G = self._build_graph(validated_input.document_id, validated_input.entities)
            
            # Serialize for JSON output
            data = nx.node_link_data(G, edges="links")
            
            return {
                "document_id": validated_input.document_id,
                "graph_data": data,
                "confidence_score": 0.85
            }
        except Exception as e:
            logger.error(f"Relationship generation failed: {e}")
            raise AgentException(f"Relationship generation failed: {e}")
