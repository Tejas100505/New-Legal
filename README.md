# Agentic AI for E-Discovery & Legal Review

> Enterprise-grade platform automating legal document review through a pipeline of
> specialized AI agents — OCR, RAG, multi-agent orchestration, semantic retrieval,
> clustering, summarization, privilege detection, and explainable legal reasoning.

**University of Mumbai — B.E. Information Technology 2025-26**

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         React + Vite + TS                           │
│               Dashboard · Upload · Review · Graphs                  │
├──────────────────────────────────────────────────────────────────────┤
│                           FastAPI (async)                           │
│  ┌──────────┐  ┌───────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Routers  │→ │ Services  │→ │ Repositories │→ │   Models     │  │
│  └──────────┘  └───────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │           Agent Orchestration (LangGraph + LangChain)        │  │
│  │  Ingest · Retrieve · Cluster · Summarize · Privilege · QA   │  │
│  └──────────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────────┤
│  PostgreSQL + pgvector    │    Redis + Celery    │    File Storage  │
└──────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker & Docker Compose v2
- Node.js 20+ (for frontend dev)
- Python 3.11+ (for backend dev)

### Development (Docker)

```bash
# Clone and configure
cp .env.example .env
# Edit .env with your API keys

# Start all services
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/v1/health

### Development (Local)

```bash
# Backend
cd backend
python -m venv .venv
.venv/Scripts/activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Project Structure

```
/frontend        — React + Vite + TypeScript + Tailwind CSS v4
/backend
  /app
    /api         — Versioned FastAPI routers
    /agents      — One module per agent (LangGraph nodes)
    /services    — Business logic, orchestration
    /repositories— DB access layer (Repository Pattern)
    /models      — SQLAlchemy ORM models
    /schemas     — Pydantic request/response models
    /ocr         — OCR provider adapters
    /rag         — Chunking, embeddings, retrieval
    /auth        — JWT authentication
    /middleware   — Request ID, logging middleware
    /db          — Database session, base model
    /utils       — Logging, helpers
  /alembic       — Database migrations
/database        — Init scripts, schema
/tests           — Unit, integration, e2e
/docs            — Architecture documentation
/docker          — Dockerfiles, nginx config
/.github/workflows — CI/CD pipelines
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite 8, TypeScript, Tailwind CSS v4 |
| Backend | FastAPI, Python 3.11+, async/await |
| Agents | LangGraph, LangChain |
| Database | PostgreSQL 16 + pgvector |
| Cache/Queue | Redis 7, Celery |
| OCR | PaddleOCR, PyMuPDF, Tesseract (fallback) |
| Embeddings | Sentence-Transformers (BGE-M3), OpenAI (optional) |
| LLMs | OpenAI, Anthropic Claude, Google Gemini (configurable) |
| Visualization | React Flow, D3.js, Recharts |
| DevOps | Docker, Docker Compose, GitHub Actions |

## License

Academic project — University of Mumbai, 2025-26.
