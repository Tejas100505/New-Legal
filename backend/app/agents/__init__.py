"""
AI Agents package.

Each agent is a specialized LangGraph node responsible for one stage
of the e-discovery pipeline. Agent implementations are added in Part 2.

Agent architecture:
    - Each agent module exposes a callable (async function or class)
      conforming to the LangGraph node interface.
    - Agents communicate via a shared TypedDict state that flows
      through the orchestration graph.
    - The orchestrator (services/orchestrator.py) wires agents into
      a LangGraph StateGraph.

Planned agents (Part 2):
    1. DocumentIngestionAgent — validates, OCRs, and stores documents
    2. RetrievalAgent — semantic search over embeddings
    3. ClusteringAgent — groups similar documents
    4. SummarizationAgent — generates cited summaries
    5. PrivilegeAgent — flags privileged content
    6. ReviewAgent — consolidates all agent outputs
"""
