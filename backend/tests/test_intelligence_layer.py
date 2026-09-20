import pytest
from app.agents.classification import ClassificationAgent, ClassificationInput
from app.agents.entity_extraction import EntityExtractionAgent, EntityExtractionInput
from app.agents.relationship import RelationshipAgent, RelationshipInput
from app.agents.timeline import TimelineAgent, TimelineInput
from app.agents.clustering import ClusteringAgent, ClusteringInput

@pytest.fixture
def classification_agent():
    return ClassificationAgent()

@pytest.fixture
def entity_agent():
    return EntityExtractionAgent()

@pytest.fixture
def relationship_agent():
    return RelationshipAgent()

@pytest.fixture
def timeline_agent():
    return TimelineAgent()

@pytest.fixture
def clustering_agent():
    return ClusteringAgent()


@pytest.mark.asyncio
async def test_classification(classification_agent):
    input_data = ClassificationInput(document_id="doc1", text="This is a contract agreement.")
    result = await classification_agent.run(input_data)
    
    assert result.category == "Contracts"
    assert result.confidence_score > 0.9


@pytest.mark.asyncio
async def test_entity_extraction(entity_agent):
    text = "John Doe works at Acme Corp and earned $1,000.00 on 2023-01-15 for Case No. 123-ABC in the Supreme Court."
    input_data = EntityExtractionInput(document_id="doc1", text=text)
    result = await entity_agent.run(input_data)
    
    ents = result.entities
    assert "John Doe" in ents.people
    assert "Acme Corp" in ents.organizations
    assert "$1,000.00" in ents.money
    assert "2023-01-15" in ents.dates
    assert "Case No. 123-ABC" in ents.case_numbers
    assert "Supreme Court" in ents.courts


@pytest.mark.asyncio
async def test_legal_ner_integration(entity_agent):
    text = (
        "Subject: Privileged & Confidential: Legal Assessment in Apex v. RailCorp regarding Case No. 2025-CV-1234\n"
        "From: elena.vance@apollolegal.com\n"
        "To: marcus.reed@apollo.com\n\n"
        "Pursuant to your request yesterday regarding our cross-border power swap execution facilities, "
        "I have reviewed the CFTC Part 43 obligations.\n\n"
        "Elena Vance\n"
        "Senior Regulatory Counsel\n"
        "Apollo Legal Advisors LLP"
    )
    input_data = EntityExtractionInput(document_id="doc_legal_1", text=text)
    result = await entity_agent.run(input_data)
    
    ents = result.entities
    # Custom fine-tuned types
    assert any("Privileged & Confidential" in m for m in ents.privilege_markers)
    assert any("Elena Vance" in a for a in ents.attorneys)
    # Regex case reference types
    assert any("Apex v. RailCorp" in c for c in ents.case_references)
    assert any("Case No. 2025-CV-1234" in c for c in ents.case_references)
    # Unified entity_list with provenance
    assert len(result.entity_list) > 0
    sources = {item.source for item in result.entity_list}
    assert "fine_tuned_model" in sources
    assert "regex" in sources


@pytest.mark.asyncio
async def test_relationship_graph(relationship_agent):
    entities = {
        "people": ["John Doe", "Jane Smith"],
        "organizations": ["Acme Corp"],
        "case_numbers": ["Case No. 1"]
    }
    input_data = RelationshipInput(document_id="doc1", entities=entities)
    result = await relationship_agent.run(input_data)
    
    graph_data = result.graph_data
    assert "nodes" in graph_data
    assert "links" in graph_data
    
    node_ids = [n["id"] for n in graph_data["nodes"]]
    assert "doc1" in node_ids
    assert "People_John Doe" in node_ids
    assert "Organizations_Acme Corp" in node_ids
    assert "Cases_Case No. 1" in node_ids
    
    # Check edges
    links = graph_data["links"]
    assert len(links) >= 4 # Mentions edges + communication edges


@pytest.mark.asyncio
async def test_timeline(timeline_agent):
    text = "The event started on 2023-05-10. Then on 2022-01-01, something else happened. Finally, 2023-12-31 marked the end."
    input_data = TimelineInput(document_id="doc1", text=text)
    result = await timeline_agent.run(input_data)
    
    timeline = result.timeline
    assert len(timeline) == 3
    # Check chronological sort
    assert timeline[0].date == "2022-01-01"
    assert timeline[1].date == "2023-05-10"
    assert timeline[2].date == "2023-12-31"


@pytest.mark.asyncio
async def test_clustering(clustering_agent):
    documents = [
        {"id": "doc1", "text": "fraud and bank issues", "embedding": [0.1, 0.2]},
        {"id": "doc2", "text": "bank fraud case", "embedding": [0.11, 0.19]},
        {"id": "doc3", "text": "contract breach dispute", "embedding": [0.9, 0.8]},
        {"id": "doc4", "text": "breach of contract", "embedding": [0.85, 0.82]}
    ]
    input_data = ClusteringInput(documents=documents, n_clusters=2)
    result = await clustering_agent.run(input_data)
    
    clusters = result.clusters
    assert len(clusters) == 2
    
    labels = [c.label for c in clusters]
    assert "Financial Fraud" in labels
    assert "Contract Dispute" in labels
