# Architecture — Agentic AI E-Discovery & Legal Review

## System Architecture

```mermaid
graph TB
    subgraph Frontend["Frontend (React + Vite + TS)"]
        UI[UI Components]
        Pages[Pages & Routing]
        API_Client[Axios API Client]
    end

    subgraph Backend["Backend (FastAPI)"]
        subgraph API["API Layer"]
            Routers[Versioned Routers<br>/api/v1/]
            Auth[JWT Auth Middleware]
            RateLimit[Rate Limiting]
        end

        subgraph Services["Service Layer"]
            DocService[Document Service]
            CaseService[Case Service]
            Orchestrator[Agent Orchestrator]
        end

        subgraph Agents["AI Agent Layer (LangGraph)"]
            Ingestion[Ingestion Agent]
            Retrieval[Retrieval Agent]
            Clustering[Clustering Agent]
            Summarization[Summarization Agent]
            Privilege[Privilege Agent]
            Review[Review Agent]
        end

        subgraph Data["Data Access Layer"]
            Repos[Repositories]
            Models[ORM Models]
        end
    end

    subgraph Infrastructure["Infrastructure"]
        PG[(PostgreSQL 16<br>+ pgvector)]
        Redis[(Redis 7)]
        FileStore[File Storage]
    end

    UI --> API_Client
    API_Client --> Routers
    Routers --> Auth
    Routers --> Services
    Services --> Repos
    Services --> Orchestrator
    Orchestrator --> Agents
    Repos --> Models
    Models --> PG
    Services --> Redis
    Services --> FileStore
```

## Processing Pipeline

```mermaid
graph LR
    A[Upload] --> B[Validate]
    B --> C[OCR]
    C --> D[Metadata]
    D --> E[Classify]
    E --> F[Chunk]
    F --> G[Embed]
    G --> H[Vector DB]
    H --> I[Retrieve]
    I --> J[Extract<br>Entities]
    J --> K[Timeline]
    K --> L[Summarize]
    L --> M[Privilege<br>Detection]
    M --> N[Risk<br>Analysis]
    N --> O[QA]
    O --> P[Report]
    P --> Q[Dashboard]
```

## Layered Architecture

| Layer | Responsibility | Example |
|-------|---------------|---------|
| **Router** | HTTP concerns, validation, response formatting | `api/v1/documents.py` |
| **Service** | Business logic, orchestration | `services/document_service.py` |
| **Repository** | Database access, queries | `repositories/document_repository.py` |
| **Model** | Data structure, ORM mapping | `models/document.py` |
| **Schema** | Request/response serialization | `schemas/document.py` |

## Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Async ORM | SQLAlchemy 2.0 async | Native asyncpg support, Alembic migrations |
| Auth | python-jose JWT | Provider-agnostic, works with Firebase/Supabase/local |
| Embeddings | pgvector | Integrated with PostgreSQL, IVFFlat indexing |
| Agent framework | LangGraph | State machine for complex agent workflows |
| Frontend state | React hooks + Axios | Simple, no global state needed yet |
| Styling | Tailwind CSS v4 | CSS-native config, Vite plugin, no JS runtime |
