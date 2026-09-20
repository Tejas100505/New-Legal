# MASTER_CONTEXT.md — Agentic AI for E-Discovery & Legal Review

*This document preserves the complete, accurate state of this project as
established across an extended working conversation. Only information
explicitly established in that conversation is included. IMPLEMENTED/
VERIFIED work is distinguished from PLANNED/INTENDED work throughout.*

---

## 1. Project Identity

- **Name:** Agentic AI for E-Discovery & Legal Review (repo: `New-Legal`)
- **Context:** Final Year Engineering Capstone, B.E. Information Technology,
  Vidyalankar Institute of Technology, University of Mumbai, AY 2025-26.
- **Team:** Tejas Shingte, Deven Hadkar, Vipul Raghatwan. Guide: Dr. Neha Kudu.
- **Development method:** "Vibe-coded" using Claude via Antigravity IDE,
  with this conversation acting as the planning/review/verification layer.

## 2. Original Report vs. Actual Implemented System (MISMATCH — important)

The **original synopsis report** (uploaded at the start of this project)
describes a narrower system:
- **5 named agents:** Retrieval Agent, Clustering Agent, Summarization
  Agent, Privilege Agent, optional Review Agent.
- **"Review Map" graph** defined explicitly as a **document-to-document**
  graph (nodes = documents, edges = semantic similarity/shared cluster).
- **Tech stack claimed:** Python, FastAPI, LangChain, Sentence
  Transformers, LLM ("GPT or Llama"), Supabase/Postgres+pgvector,
  scikit-learn, NetworkX/D3/React Flow, React.
- **Evaluation claimed:** ROUGE, BLEU, semantic similarity.
- The report's own DFD/UML diagrams (Chapter 9) described a *different*
  agent set than the prose (Ingestion Agent, Processing/OCR Agent,
  Knowledge Agent, Agentic Relevance & Review Agent, Reporting Agent) —
  this internal inconsistency was flagged in the original review and has
  **never been reconciled**.

The **actual built system** (see Sections 4-13) has ~18 pipeline stages/
agents, real Gemini LLM integration (not GPT/Llama), a real fine-tuned
domain NER model, a genuinely agentic Triage Orchestrator, real evaluation
with baseline comparisons, and — per the most recent direction change
(Section 14) — is being reframed from "document review + privilege
detection" toward "case investigation" (connecting people, timeline, and
risk across the whole document collection).

**The report has NOT yet been rewritten to match the current system.**
This is planned but not done (see CURRENT_STATUS.md).

## 3. Target Users & Product Workflow

**Target customer (established early, still valid):** small-firm/
litigation-support teams doing early case assessment — not large
enterprise e-discovery vendors (a market already served by mature tools).

**Current product workflow (implemented):**
1. Lawyer creates a case, uploads a large batch of documents (PDFs,
   emails, text files).
2. Every document runs through the full pipeline (Section 5) —
   ingestion, OCR, classification, chunking, embedding, entity extraction,
   relationship mapping, timeline extraction, clustering, summarization,
   privilege detection, risk scoring, PII detection, review aggregation.
3. The Triage Orchestrator (Section 7) computes a review priority and
   escalation flag per document, based on the combined signals from all
   upstream stages.
4. Lawyer works from a prioritized AI Review queue: sees the real
   document text, real grounded summaries, real privilege reasoning with
   evidence, and either confirms or overrides each AI finding — nothing
   is auto-finalized without human sign-off.
5. Lawyer can also explore via Semantic Search, Knowledge Graph, Timeline,
   Investigation dashboard, and export Reports (audit-ready, multiple
   formats).

**Revised core idea (Section 14, in progress, not yet reflected in the
written report):** not a chatbot, not a plain summarizer — a system that
builds a *connected, investigable picture* of the whole case: who the key
people are, how they're connected (weighted relationship graph), what
happened when (timeline), what's risky, what's privileged, and what
evidence backs every finding.

## 4. Full Pipeline / Agent Inventory (VERIFIED, as of last full audit)

| # | Agent | File | Type | Status |
|---|---|---|---|---|
| 1 | OCRAgent | `ocr.py` | Deterministic + LLM fallback | Real & tested. **Known issue:** mock fallback strings ("Meridian Corp", "Dr. James Whitfield") still present at lines ~166-171 and ~210-223, used only if both pypdf/Tesseract and Gemini vision fail. Flagged, not yet removed. |
| 2 | DocumentIngestionAgent | `ingestion.py` | Deterministic | Real & tested |
| 3 | ClassificationAgent | `classification.py` | LLM (Gemini) + keyword fallback | Real & tested. Has fallback-LLM retry pattern (added later) plus a fixed response-parsing bug (list-of-dicts content handling) |
| 4 | ChunkingAgent | `chunking.py` | Deterministic | Real & tested |
| 5 | EmbeddingAgent | `embedding.py` | Neural API (Gemini) | Real & tested. `gemini-embedding-001`, 1024-dim, `output_dimensionality=1024`. Jina/OpenAI providers raise explicit `NotImplementedError` rather than silently faking. |
| 6 | RetrievalAgent | `retrieval.py` | Deterministic hybrid | Real & tested. BM25 + pgvector cosine, plus `CAISO_OPERATIONAL_PATTERNS` relevance boost (+0.25) added after evaluation found structured/tabular scheduling docs scored poorly |
| 7 | EntityExtractionAgent | `entity_extraction.py` | Hybrid (fine-tuned spaCy + regex) | Real & tested. See Section 8 for full detail. `NERMock` fully removed. |
| 8 | RelationshipAgent | `relationship.py` | Deterministic (NetworkX) | Real & tested, but currently uses **uniform edge weight (0.8)** and **static node importance (0.75)** — real weighting/centrality is a planned next step, not yet built |
| 9 | TimelineAgent | `timeline.py` | Deterministic + selective LLM | Real & tested. Multi-format date extraction, context-sensitive confidence scoring (replacing old hardcoded 0.88), selective Gemini narrative synthesis for complex documents only |
| 10 | SummarizationAgent | `summarization.py` | LLM (Gemini) | Real & tested. 4 perspectives (Executive, Legal, Evidence, Clause), grounded citations `[Chunk N, § Section, p. X]` or `"page/section unavailable"` (never fabricated), real neural cosine similarity via `GeminiEmbeddingProvider` (replacing fake Jaccard `SemanticSimilarityChecker`), `TokenOverlapChecker` kept but explicitly labeled "lexical" not "semantic" |
| 11 | PrivilegeAgent | `privilege.py` | Hybrid (regex + Gemini) | Real & tested. See Section 9 for full detail |
| 12 | RiskAgent | `risk.py` | Deterministic pre-screen + Gemini | Real & tested. Replaced hardcoded confidence formula `0.85 + 0.05*len(found)`; pre-screen keyword list tightened from bare words (dispute, price, liability, penalty) to legal-context collocations to avoid false triggers on casual language (verified against real test sentences) |
| 13 | PIIAgent | `pii.py` | Deterministic (regex) | Real & tested |
| 14 | ReviewAgent | `review.py` | Deterministic aggregator | Real & tested |
| 15 | VerificationAgent | `verification.py` | Deterministic (token overlap) | Real but basic — not full NLI entailment, flagged as a known simplification |
| 16 | ClusteringAgent | `clustering.py` | Deterministic (KMeans) + LLM labeling | Real & tested. Runs on real embeddings (fixed from fake `[len(text)%10]*1024`). Dynamic TF-IDF + Gemini centroid-exemplar labeling replaced hardcoded `_auto_label()` keyword map. Header-stripping added before TF-IDF so labels reflect topics not custodian names. Verified with zero label overlap across two different datasets (Enron vs. synthetic). |
| 17 | ReportAgent | `report.py` | Deterministic | Real & tested. PDF/DOCX/CSV/JSON/Markdown export |
| 18 | TriageOrchestratorAgent | `triage.py` | **Genuinely agentic** | Real & tested. See Section 7 |

## 5. Backend Architecture (VERIFIED)

- **Language/runtime:** Python 3.13.2 (compatible 3.11+)
- **Framework:** FastAPI (≥0.115) on Uvicorn, async
- **Database:** PostgreSQL 15+ with pgvector (v0.8.2 confirmed active),
  hosted on **Supabase** (AWS Mumbai, `ap-south-1`), async connection
  pooler via `asyncpg`
- **ORM/migrations:** SQLAlchemy 2.0 (async), Alembic
- **Auth:** Local stateless JWT (`python-jose` + `passlib`/direct bcrypt),
  HS256, RBAC (client/lawyer/admin roles)
- **Redis:** declared in requirements, confirmed NOT required — unused in
  the actual pipeline (Celery/task queue never wired in); safe to skip
  entirely when running locally

## 6. AI/LLM Configuration (VERIFIED, evolved significantly — see history)

- **Primary LLM:** `gemini-3.5-flash-lite` — confirmed via live testing:
  **15 RPM**, **500 requests/day** (empirically confirmed via a real
  captured 429 quota error during full-dataset ingestion; an earlier
  claim of 1,500 RPD was superseded by this later, more directly-tested
  number — **500/day is the confirmed real figure**)
- **Fallback LLM:** `gemini-3.8-flash` — confirmed via live 429 error:
  **20 requests/day** hard cap (much stricter than the primary)
- **Both models are pinned to exact version strings**, not the `-latest`
  alias, deliberately — for audit/reproducibility reasons specific to a
  legal application (a privilege determination must be traceable to a
  specific, stable model version)
- **Dual API key rotation:** `GOOGLE_API_KEY` and `GOOGLE_API_KEY_2`,
  automatic failover on daily quota exhaustion (added after hitting the
  500/day cap mid-ingestion on the real 424-document dataset)
- **Embedding model:** `gemini-embedding-001`, 1024-dim, via API (not
  local) — chosen specifically because local `sentence-transformers`/
  `bge-m3` required ~4-5GB disk (unavailable on the dev machine at the
  time)
- **Important config-file caveat:** `.env` still says
  `EMBEDDING_PROVIDER=sentence-transformers` / `EMBEDDING_MODEL=BAAI/bge-m3`
  — this is intentionally aliased in `embedding.py` to route to the real
  Gemini API instead, to avoid downloading heavy local models. Someone
  reading `.env` alone would be misled; this is a known documentation gap.

## 7. Triage Orchestrator — The Genuinely Agentic Component (VERIFIED)

File: `backend/app/agents/triage.py`. Built specifically to make
"Agentic AI" an earned claim (per the original review's Part 4 critique
that the original 5-agent design was a deterministic pipeline, not
agentic).

**Documented thresholds:**
- `PRIVILEGE_BORDERLINE_MIN = 0.45`, `PRIVILEGE_BORDERLINE_MAX = 0.75`
- `SUMMARY_GROUNDING_THRESHOLD = 0.65`

**Decision paths (non-linear, verified with real branching):**
- `BORDERLINE_PRIVILEGE_ESCALATION` — priority 88-96, `IMMEDIATE_HUMAN_REVIEW`,
  framed around FRE 502 subject-matter waiver risk
- `CRITICAL_RISK_EXPOSURE` — priority 82-100, regulatory-authority boost (+6.0)
- `CONFIRMED_PRIVILEGE_LOG` — priority 75-85
- `HIGH_RELEVANCE_COMMERCIAL` — priority 60-80
- `ROUTINE_BENIGN` — priority 5-45

**Adaptive second-pass LLM re-analysis:** when regex privilege signal is
borderline and the document is relevant, the orchestrator autonomously
triggers a second, deeper LLM privilege pass rather than following a
fixed rule.

**Strongest proof of genuine agentic behavior (verified test evidence):**
two documents (`DOC_103A`, `DOC_103B`) started from an *identical* initial
regex privilege signal (0.62). `DOC_103A` triggered the adaptive
second-pass LLM re-analysis, which resolved the ambiguity (confirmed
non-privileged, 0.99 confidence) and settled at priority 73.2. `DOC_103B`
did not get resolved and escalated to priority 95.4 (rank #1, ahead of
documents with higher raw relevance). This is direct evidence of a real
decision under uncertainty with a visible branch, not a fixed formula.

Integrated into `orchestrator.py` as Stage 8.5. Sets `doc.meta["triage"]`,
`doc.meta["review_priority"]`, and `DocumentStatus.FLAGGED` on escalation.
`AIReviewPage.tsx` sorts the queue by `triage.priority_score` descending
and renders escalation badges + a reasoning card.

## 8. Named Entity Recognition — TWO SEPARATE TRACKS

### 8a. Domain-matched e-discovery NER (INTEGRATED into the real product)

- **Entity schema:** `ATTORNEY`, `CUSTODIAN`, `PRIVILEGE_MARKER`,
  `CASE_REFERENCE` (custom) + generic `PERSON`/`ORG`/`DATE`/`MONEY`/`GPE`
  (base spaCy, preserved via pseudo-rehearsal)
- **Training data:** weak-supervision bootstrap (regex privilege patterns
  + base spaCy PERSON + email sender headers + case-reference regex) over
  144 documents (24 synthetic + 120 stratified real Enron), producing 334
  candidate spans. **100% human-reviewed and corrected** by the user
  (ground-truth purity maintained — no AI-generated labels used as truth).
- **Final label distribution (334 confirmed):** NONE 199 (59.6%),
  CUSTODIAN 77 (23.1%), PRIVILEGE_MARKER 27 (8.1%), ATTORNEY 24 (7.2%),
  CASE_REFERENCE 7 (2.1%)
- **Split:** document-level (116 unique docs) — Train 82 docs/241 spans,
  Val 17 docs/47 spans, Test 17 docs/46 spans
- **Model:** fine-tuned `en_core_web_sm` spaCy NER, 20 epochs, best
  checkpoint epoch 14. Saved to `backend/models/legal_ner_ediscovery_v1`
- **Held-out TEST results (real, verified):**
  - ATTORNEY: P 1.0000 / R 0.4000 / F1 0.5714 (support 5)
  - CUSTODIAN: P 0.4444 / R 0.5714 / F1 0.5000 (support 7)
  - PRIVILEGE_MARKER: P 0.5000 / R 0.6667 / F1 0.5714 (support 3)
  - CASE_REFERENCE: P 0 / R 0 / F1 **0.0000** (support 1) — **critical
    weakness**, only 7 total positive examples across the whole dataset,
    insufficient to train a neural head. **Decision: CASE_REFERENCE
    stays on deterministic regex only in production; neural predictions
    for this type are explicitly discarded.**
  - Base entities preserved: DATE F1 1.000, ORG F1 0.869, PERSON F1
    0.800, GPE F1 0.250 (support 4, small sample), MONEY F1 0 (support 0
    — no test examples existed)
  - **Overall combined: P 0.8043 / R 0.8087 / F1 0.8065**
- **Integration status:** fully wired into `entity_extraction.py`,
  `NERMock` completely removed, verified with real extraction output on
  4 real documents (correctly distinguishing CUSTODIAN from generic
  PERSON; correctly tagging CASE_REFERENCE via `[REGEX]` vs. everything
  else via `[MODEL]`).

### 8b. Multilingual research NER (STANDALONE, NOT integrated into product)

- **Purpose:** separate research contribution for the report, not part of
  the working e-discovery product (domain mismatch — court-judgment
  entities like JUDGE/PETITIONER/COURT don't occur in corporate case
  correspondence).
- **Schema (14 types):** CASE_NUMBER, COURT, DATE, GPE, JUDGE, LAWYER,
  ORG, OTHER_PERSON, PETITIONER, PRECEDENT, PROVISION, RESPONDENT,
  STATUTE, WITNESS
- **Base data:** OpenNyAI/Legal-NLP-EkStep Indian legal judgment corpus,
  English + machine-translated Hindi/Marathi (distant supervision, entity
  spans translated in isolation and located via substring search)
- **Model:** XLM-RoBERTa-base fine-tuned via spaCy, trained on free Google
  Colab GPU (T4)
- **v3 (reported as the final benchmark):** Hindi 80% F1, Marathi 77% F1
  on held-out 72 Hindi / 70 Marathi sentences
- **v4 (attempted improvement, documented as a negative result):**
  re-cleaned training data (fixed 4 annotation issues: JUDGE trailing
  tokens, GPE postposition suffixes, PRECEDENT punctuation, CASE_NUMBER
  digit-presence), retrained via sequential warm-start fine-tuning
  (confirmed genuine warm-start via step-0 loss comparison: Phase 2
  step-0 loss 93.80/96.88 vs. Phase 1's 695.38/349.14 — proves component
  sourcing worked, not a from-scratch retrain). **Final v4 result:**
  Hindi Strict F1 44.69% (Suffix-Normalized 61.45%), Marathi Strict F1
  45.26% (Suffix-Normalized 48.18%) — **both remain well below v3 even
  after normalization**. Root cause diagnosed: `clean_annotations.py`
  stripped postpositions from training data only (held-out set correctly
  left untouched per methodology), creating a train/eval distribution
  shift specific to agglutinative Hindi/Marathi morphology.
  **Per explicit agreement, iteration on v4 stopped here.** v3 (80%/77%)
  is the reported final benchmark; v4 is documented honestly as an
  inconclusive follow-up with a real diagnostic explanation — this is
  intended to be written up as a legitimate methodological finding, not
  hidden.
- Model saved to Google Drive:
  `/content/drive/MyDrive/multilingual_legal_ner_v4/final_v4_model_best`

## 9. Privilege Detection — Full Detail (VERIFIED)

Hybrid two-pass system in `privilege.py`:
- **Pass 1 (regex):** `PRIVILEGE_PATTERNS` / `STRONG_PRIVILEGE_PATTERNS`
  for explicit high-confidence markers (e.g. "ATTORNEY-CLIENT
  PRIVILEGED"). **Recall-priority safeguard:** explicit regex matches
  cannot be silently overridden to non-privileged by the LLM.
- **Pass 2 (Gemini LLM):** triggered for ambiguous cases — `AMBIGUOUS_LEGAL_TERMS`
  regex list (expanded during evaluation to include "partner", "law
  firm", "llp", "p.c.", "legal group", "legal department" after a real
  false negative was found in evaluation).
- **Two real bugs found and fixed via the Tier 2 evaluation process:**
  1. A press-release document with a boilerplate "Attorney-Client
     Privileged / Work Product" footer disclaimer was auto-accepted as
     privileged via the Pass 1 regex short-circuit, without ever reaching
     the LLM. **Fix:** matches found specifically within disclaimer/
     footer text now route to Pass 2 (LLM) for confirmation instead of
     auto-accepting.
  2. A document from "Miriam Goldstein, Antitrust Practice Group Leader"
     was missed because the ambiguous-terms list didn't include "partner"
     or "law firm" — it never reached the LLM at all. **Fix:** expanded
     the term list (see above).

## 10. Knowledge Graph — Current State (PARTIALLY BUILT, actively evolving)

- **Backend:** `RelationshipAgent` (`relationship.py`) builds a NetworkX
  graph from document/entity co-occurrence. Real `/api/v1/graph` endpoint
  exists and returns real data.
- **Frontend:** `@xyflow/react` + `elkjs`, interactive canvas with entity
  filters (Document, Person, Organization, Evidence, Email, Contract,
  Legal Issue, Event, Location), search, zoom/pan, node inspector,
  shortest-path finder.
- **KNOWN LIMITATIONS (confirmed in the most recent full audit):**
  1. **Edge weights are hardcoded to a uniform 0.8** — no real
     co-occurrence or communication-frequency weighting yet.
  2. **Node importance is hardcoded to a uniform 0.75** — no real
     centrality calculation (degree/betweenness via NetworkX) driving
     node size yet.
  3. **No cross-document entity alias resolution** — entity nodes are
     deduplicated via naive case-insensitive string hashing
     (`f"ent_{hash(item) & 0xffffff}"`), meaning "Kenneth Lay", "Ken Lay",
     "K. Lay", and "Chairman Lay" would currently appear as **separate,
     fragmented nodes** instead of one canonical person.
- **Entities storage:** no standalone `entities` relational table —
  entities are stored as JSON inside `documents.doc_metadata["entities"]`;
  the `/api/v1/entities` endpoint dynamically parses this across all
  documents at request time.

## 11. Frontend (React 19 + TypeScript + Vite, TailwindCSS 4, Zustand,
TanStack Query, Recharts, `@xyflow/react`/`elkjs`)

**15 pages total.** As of the most recent full audit, all pages were
brought to "fully dynamic" or acceptable status EXCEPT the specific
known gaps below. See CURRENT_STATUS.md for exact per-page state at the
time context was preserved — this file records the overall pattern and
history, not a live snapshot.

**Pattern of bugs found and fixed across the frontend audit (history):**
- A recurring URL-prefix bug: frontend called `/intelligence/graph`,
  `/intelligence/timeline`, `/intelligence/entities` but the real backend
  routes are `/graph`, `/timeline`, `/entities` (no `/intelligence`
  prefix) — caused Knowledge Graph and Timeline pages to silently render
  empty despite real backend data existing. Found and fixed across
  multiple files.
- Multiple pages had hardcoded/mock stub values sitting inside otherwise-
  real pages (Dashboard preview cards, Cases page document counts,
  Investigation page category counts and "AI findings", Reports page
  file-size/page-count display).
- The Analytics page was **100% mock** — called the real `/analytics`
  endpoint but discarded the response and rendered from
  `mockAnalytics.ts` instead. Fully rewired to real data; the one
  benchmark metric never actually measured (hallucination rate) is
  honestly left as a null/pending state rather than fabricated.
- **A subtler, later-caught version of the same problem:** after an
  initial "fix" to the Dashboard's AI Agents panel (originally showing
  all agents permanently "Idle"), the replacement was found to still be
  **fake in a disguised way** — every agent showed identical hardcoded
  per-category stats (e.g. all showing exactly 1.9s processing time and
  6.0k tokens, rather than real per-agent execution data). This was
  flagged explicitly as "the same mock problem, better disguised" and
  sent back for a genuine fix using real logged execution data. **Status
  of this specific re-fix was not yet confirmed complete when this
  context was preserved — see CURRENT_STATUS.md.**

## 12. Dataset & Evaluation (Tier 2 — VERIFIED, real numbers)

### Real dataset: Enron Email subset
- 400 real emails from the CMU Enron Email Corpus
  (`enron_mail_20150507.tar.gz`), stratified across 20 custodians (20
  emails each), deduplicated by SHA-256, filtered to 150-4000 char body
  length, split 70/15/15 (280 train / 60 val / 60 test)
- **Case scenario used for labeling:** "In re: Enron California Energy
  Market Practices Inquiry" — a FERC/CPUC/CAISO investigation into
  California energy market practices, 2000-2001 (chosen to genuinely
  match the real content of the Enron corpus)
- **Labeled entirely by hand by the user** (solo), using a documented
  decision guide with two explicitly flagged traps: (1) "privileged"
  boilerplate email-footer disclaimers do not indicate real privilege —
  this pattern accounted for ~90% of keyword-triggered privilege flags
  and had to be manually screened out; (2) "price"/"scheduling" keywords
  over-triggered relevance suggestions and needed extra scrutiny.
- **Final real ground-truth labels:** 21/400 relevant (5.25%), 1/400
  privileged (0.25% — `enron_train_092_hain-m`, a Cal PX/FERC compliance
  filing protest cc'ing GC Mark Haedicke).
- A **rule-based (non-LLM) pre-flagging script** was used to speed up
  human labeling — deliberately built as a separate, simple, transparent
  keyword heuristic (not using Gemini or the system under evaluation) to
  avoid circular evaluation. Ground-truth columns were kept 100% blank
  until human-filled; verified via automated checks at multiple points.

### Synthetic privilege benchmark (built because real data had only 1
positive privilege example — statistically unusable alone)
- 24 fully original documents, **never derived from real Enron content**
  (confirmed independent) — 12 genuine privilege examples across varied
  categories (regulatory compliance, litigation strategy, contract
  indemnity, settlement, internal investigation, IP/patent, employment,
  FERC defense, antitrust, environmental, M&A, tax memo) and 12 hard
  negatives specifically designed to look privileged but not be (lawyer
  cc'd for business only, boilerplate disclaimer footers, routine legal-
  dept administrative intake, forwarding a lawyer's contact info
  socially, GC doing routine scheduling, lawyer forwarding public news,
  lawyer acting as a pure business negotiator, etc.)
- File: `data/synthetic_privilege_benchmark.csv`, `source="synthetic"`
  tagged on every record

### Real evaluation results (stored in `data/full_evaluation_results.json`
and in the `evaluation_metrics` DB table, 31 records)

**Relevance retrieval (combined 400-doc Enron test, AFTER fixes —
CAISO operational-header relevance boost + recalibrated threshold 0.48):**
| Metric | Value |
|---|---|
| Precision | 0.7647 |
| Recall | 0.6190 |
| F1 | 0.6842 |
| Accuracy | 0.9700 |

Split breakdown: Train P0.9000/R0.6000/F1 0.7200; Val P1.0000/R0.3333/
F1 0.5000; Test P0.5000/R1.0000/F1 0.6667.

BM25 keyword-only baseline: P0.2600/R0.6190/F1 0.3662/Acc 0.8875.

Before-fix result (semantic pipeline before the CAISO boost was added):
P0.3056/R0.5238/F1 0.3860 — the fix that closed most of this gap was
identifying that automated CAISO scheduling logs (`<CODESITE>` format,
tabular content) scored poorly on pure semantic similarity and adding a
targeted relevance boost for known operational header patterns.

**Privilege detection (24-doc synthetic hard-negative benchmark, AFTER
both bug fixes described in Section 9):**
| Metric | Value |
|---|---|
| Precision | 1.0000 |
| Recall | 1.0000 |
| F1 | 1.0000 |
| Accuracy | 1.0000 |

Before fixes: P0.9167/R0.9167/F1 0.9167. Regex-only baseline:
P0.6000/R0.2500/F1 0.3529/Acc 0.5417.

**IMPORTANT CAVEAT (must be preserved):** the `evaluation_metrics` table's
API-aggregated "average" values (e.g. `avg_retrieval_precision: 0.896`)
are NOT the same as the headline combined-test-set numbers above — the
API average blends per-split breakdowns, the BM25 baseline, and the
privilege benchmark's perfect scores together into one number. **When
writing the report or discussing results, use the specific combined
Enron-400 test numbers (0.7647/0.6190/0.6842) and the specific
privilege-benchmark numbers (1.0000/1.0000/1.0000), not the blended API
average**, to avoid misrepresenting or overstating the result.

## 13. Model Configuration History (important — do not re-litigate)

- Original assumption `gemini-3.6-flash` was never real; actual default
  was the `gemini-flash-latest` alias, which silently resolves to
  whatever Google considers current (was `gemini-3.8-flash` at the time).
- Confirmed via live captured 429 errors (not estimated from docs):
  `gemini-3.8-flash` free tier = **20 requests/day**;
  `gemini-3.5-flash-lite` free tier = **15 RPM / 500 requests/day**
  (the 500/day figure was confirmed later, during full-dataset
  ingestion, and supersedes an earlier 1,500/day estimate).
- **Final configuration:** `gemini-3.5-flash-lite` as primary,
  `gemini-3.8-flash` as fallback, both pinned to exact version strings
  (not `-latest`) for legal-domain reproducibility/auditability.
- Dual API key rotation (`GOOGLE_API_KEY_2`) added after hitting the
  500/day cap mid-ingestion on the real 424-document run, specifically to
  avoid degrading to a heuristic/non-LLM fallback for the remaining
  documents (a deliberate choice to preserve consistent real-LLM quality
  across the whole demo dataset rather than silently mixing quality
  levels).

## 14. Recent Direction Change — Topic Reframing (IN PROGRESS)

**Old framing (in the original report, and echoed by earlier build
milestones):** a "5-agent" document review and privilege-detection tool.

**New agreed framing (established late in this conversation, NOT yet
written into the report):** an end-to-end **case investigation system**.
Instead of reviewing documents in isolation, it aggregates the whole
evidentiary corpus into one connected, investigable picture: who spoke to
whom, what was the timeline, where are the risk clusters. Explicitly
**not** primarily a chatbot, **not** simply a document summarizer.

**New one-line description agreed on:** *"An Agentic AI-based E-Discovery
and Legal Review system that processes large collections of case
documents and automatically extracts, connects, summarizes, and analyzes
the information to help lawyers understand and investigate a case
faster."*

**Agreed replacement for "5 agents":** describe the system structurally —
a 14-18 stage processing pipeline (deterministic stages + LLM-reasoning
stages) plus the Triage Orchestrator as the one genuinely agentic
component that makes decisions under uncertainty. This is both more
accurate and more defensible at viva than either the old "5 agents" claim
or an inflated "18 agents" headline number.

**What's ALREADY built and verified that supports this new framing:**
Investigation dashboard, interactive Knowledge Graph canvas (with known
limitations, see Section 10), domain NER extracting ATTORNEY/CUSTODIAN
roles specifically to populate people-centric graph nodes, Timeline
aggregation, Triage Orchestration.

**What is NOT yet built (identified gaps, in agreed priority order):**
1. **Entity alias/coreference resolution** (must come first — see
   Section 10, item 3) — a prompt for this was written and given to the
   user; the user has stated they executed it, but **results have not
   yet been reviewed in this conversation**. A follow-up independent
   verification prompt was also given but its results have likewise not
   yet been reviewed. **This is the current in-progress task — see
   CURRENT_STATUS.md.**
2. Real co-occurrence-based edge weighting (replacing the hardcoded 0.8)
   — NOT YET STARTED, depends on #1 being confirmed first
3. Centrality-based node sizing via NetworkX (replacing the hardcoded
   0.75 importance) — NOT YET STARTED, depends on #1 and #2
4. OCR mock-string cleanup (Section 4, item 1) — low priority, cheap,
   not yet done
5. Cross-page entity linking (clickable entity badges navigating to the
   graph) — lowest priority, not yet done

**After the above:** report rewrite (problem statement, drop "5 agents"
framing, redefine the Review Map/graph section around the real people-
relationship graph, reconcile the still-unresolved DFD/UML diagram
mismatch from the original report, update the demo script to lead with
the case-investigation story).

## 15. Standing Rules (apply to ALL future work on this project)

1. **No mocks, no fabricated/synthetic data presented as real, no silent
   fallbacks.** Always verify with real output before accepting a claim
   of "done."
2. **Ground-truth purity:** never let an AI system generate its own
   evaluation labels (this makes evaluation circular and meaningless).
   Human labeling is required for ground truth. AI predictions must live
   in clearly separate, explicitly-labeled columns/files, never mixed
   into ground-truth fields.
3. **Verification scripts go in `scratch/`, executed via real file
   execution (`python script.py`), NEVER inline `python -c "..."` through
   PowerShell** — this caused a real ~27-minute silent deadlock due to a
   PowerShell/Python quote-escaping incompatibility. Documented in
   `.agents/rules/powershell_python_execution.md`.
4. **Self-skeptical review required at the end of every task** —
   explicitly report "what could still be fake or wrong," flag any other
   mocks/shortcuts found even if out of the current task's scope, never
   silently fix or silently leave them unmentioned.
5. **Always back up before destructive operations** (DB deletes, file
   overwrites) with real, shown evidence of the backup before proceeding.
6. **Prefer honest pending/null states over fabricated placeholder data**
   when real data doesn't exist yet (e.g. `hallucination_rate` is
   deliberately left `null` because it was never actually measured,
   rather than inventing a plausible number).
7. **Every "completed"/"verified" claim needs independent, shown
   evidence** — real logs, real query results, real screenshots. Past
   claims of "fixed" have been found to still be subtly fake on
   independent re-check (e.g. the disguised per-agent-stats bucket
   problem in Section 11) — continued skepticism toward self-reported
   completion is warranted, especially before anything goes into the
   report or a demo.
8. **Keep the written report honestly aligned with the actual system
   state** — never let the report claim more than what's actually built
   and verified; update report text whenever the system's real
   capabilities diverge from what was previously written.
9. **Zero cost / free-tier only** — no paid APIs, no paid infrastructure,
   throughout the entire project.
