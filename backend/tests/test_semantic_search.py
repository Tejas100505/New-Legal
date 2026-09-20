import pytest
import uuid
from app.agents.chunking import ChunkingAgent, ChunkingInput
from app.agents.embedding import EmbeddingAgent, EmbeddingInput, ChunkData
from app.agents.retrieval import RetrievalAgent, RetrievalInput, ChunkData as RetChunkData

@pytest.fixture
def chunking_agent():
    return ChunkingAgent()

@pytest.fixture
def embedding_agent():
    return EmbeddingAgent()

@pytest.fixture
def retrieval_agent():
    return RetrievalAgent()

@pytest.mark.asyncio
async def test_chunking_semantic_boundaries(chunking_agent):
    text = "# Section 1\n\nThis is paragraph one.\n\nThis is paragraph two."
    input_data = ChunkingInput(
        document_id="doc-123",
        text=text,
        metadata={"filename": "test.txt"}
    )
    result = await chunking_agent.run(input_data)
    
    assert len(result.chunks) == 3
    assert result.chunks[0].text == "# Section 1"
    assert result.chunks[1].text == "This is paragraph one."
    assert result.chunks[1].section == "Section 1"
    assert result.chunks[2].text == "This is paragraph two."

from app.agents.base import AgentException

@pytest.mark.asyncio
async def test_embedding_configurable_providers(embedding_agent):
    chunk = ChunkData(
        chunk_id="chunk-1",
        document_id="doc-123",
        page=1,
        section="test",
        text="Sample legal text for embedding verification",
        metadata={}
    )
    # Test Gemini provider directly
    res_gemini = await embedding_agent.run(EmbeddingInput(chunks=[chunk], provider="gemini"))
    assert res_gemini.provider_used == "gemini-embedding-001"
    assert len(res_gemini.embedded_chunks[0].embedding) == 1024
    assert all(isinstance(x, float) for x in res_gemini.embedded_chunks[0].embedding)

    # Test legacy alias sentence_transformers routes to gemini-embedding-001
    res_st = await embedding_agent.run(EmbeddingInput(chunks=[chunk], provider="sentence_transformers"))
    assert res_st.provider_used == "gemini-embedding-001"
    assert len(res_st.embedded_chunks[0].embedding) == 1024

    # Test unimplemented provider raises AgentException explicitly (no fake fallbacks)
    with pytest.raises(AgentException) as exc_info:
        await embedding_agent.run(EmbeddingInput(chunks=[chunk], provider="Jina"))
    assert "not implemented" in str(exc_info.value).lower()

@pytest.mark.asyncio
async def test_hybrid_retrieval_and_citations(retrieval_agent):
    # Setup candidate chunks mimicking DB vector search results
    candidates = [
        RetChunkData(
            chunk_id="c1", document_id="d1", page=1, section="Background",
            text="The quick brown fox jumps over the lazy dog.",
            metadata={"filename": "doc1.pdf"}, vector_score=0.9
        ),
        RetChunkData(
            chunk_id="c2", document_id="d2", page=5, section="Analysis",
            text="A completely irrelevant document about apples and oranges.",
            metadata={"filename": "doc2.pdf"}, vector_score=0.8
        )
    ]
    
    input_data = RetrievalInput(
        query="brown fox",
        candidate_chunks=candidates,
        top_k=5
    )
    
    result = await retrieval_agent.run(input_data)
    
    assert len(result.results) == 2
    # Ensure c1 is ranked higher because of BM25 exact match and CE overlap
    assert result.results[0].chunk_id == "c1"
    
    # Check citation format: [doc1.pdf, p. 1, § Background]
    assert "doc1.pdf" in result.results[0].citation
    assert "p. 1" in result.results[0].citation
    assert "Background" in result.results[0].citation

@pytest.mark.asyncio
async def test_metadata_filtering(retrieval_agent):
    candidates = [
        RetChunkData(
            chunk_id="c1", document_id="d1", page=1, section="test",
            text="fox", metadata={"author": "Alice"}, vector_score=0.9
        ),
        RetChunkData(
            chunk_id="c2", document_id="d2", page=1, section="test",
            text="fox", metadata={"author": "Bob"}, vector_score=0.9
        )
    ]
    
    input_data = RetrievalInput(
        query="fox",
        candidate_chunks=candidates,
        metadata_filters={"author": "Bob"},
        top_k=5
    )
    
    result = await retrieval_agent.run(input_data)
    
    assert len(result.results) == 1
    assert result.results[0].chunk_id == "c2"
