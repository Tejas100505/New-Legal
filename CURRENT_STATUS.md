# CURRENT_STATUS.md — Agentic AI for E-Discovery & Legal Review

*Companion to MASTER_CONTEXT.md. This file tracks exact current position,
what's done vs. not, and the precise next action. Read MASTER_CONTEXT.md
first for full background — this file assumes that context.*

*Last updated: after completing and independently verifying nine major
workstreams: (1) Critical Cross-Tenant Data Leak Fix, (2) Quota-Exhaustion
Honest Handling (QUOTA_PAUSED), (3) File Storage Migration to Supabase
Storage, (4) Self-Registration + UX Improvements, (5) Supabase Keep-Alive
Documentation (activation pending), (6) Batch 1 Session-Debris Cleanup
(CLOSED / APPROVED), (7) Batch 2 — Honest Analytics Metrics & UI
Remediation (Tasks 1–6 genuinely EXECUTED, VERIFIED, and CLOSED),
(8) Rate Limiting + Password-Strength Hardening (Tasks 1–3 genuinely
EXECUTED, VERIFIED, and CLOSED). Updated with evidence-backed test
baseline and backlog tracking.*

---

## 1. Project Current State

**What the product currently does:** processes case document collections
(currently the 424-document real Enron + synthetic dataset; 426 documents
accounted for across case storage migration; 437 total in database) through an 18-stage pipeline,
extracts and canonicalizes entities, builds a real weighted and centrality-sized
Knowledge Graph of people/organizations, produces grounded summaries,
privilege/risk findings, and a prioritized AI Review queue — all human-confirmed,
nothing auto-finalized. See MASTER_CONTEXT.md for full product framing.

**Overall implementation status:**
- Core pipeline, human review UI, domain NER, Triage Orchestrator, and Tier 2
  evaluation remain fully built and verified (see MASTER_CONTEXT.md).
- Knowledge Graph Steps 1–3 are complete and independently verified:
  1. **Entity alias resolution** — ✅ VERIFIED (Section 2).
  2. **Real edge weighting** — ✅ VERIFIED / RECONFIRMED (Section 2 & 8).
  3. **Centrality-based node sizing** — ✅ VERIFIED WITH DOCUMENTED LIMITATIONS
     (Section 3).
- Nine follow-up workstreams completed and verified:
  1. **Cross-Tenant Data Leak** — ✅ FIXED / CLOSED (independently verified
     with real HTTP evidence).
  2. **Quota-Exhaustion Honest Handling** — ✅ CLOSED (independently verified
     with real triggered-failure tests and live HTTP evidence).
  3. **Supabase File Storage Migration** — ✅ CLOSED (independently verified
     with real migration output, bucket API evidence, and access-control
     re-testing).
  4. **Self-Registration + UX Improvements** — ✅ CLOSED (independently verified
     at time of completion; admin escalation vulnerability fixed).
  5. **Supabase Keep-Alive Documentation** — ✅ CLOSED (documentation delivered;
     manual activation by project owner is PENDING).
  6. **Batch 1 Session-Debris Cleanup** — ✅ CLOSED / APPROVED (post-cleanup
     debris eradicated; historical test baseline).
  7. **Batch 2 Honest Analytics Metrics & UI Remediation** — ✅ VERIFIED COMPLETE / CLOSED
     (Tasks 1–6 fully executed and verified: Task 1 KMeans wheel & exception fix;
     Task 2 data-derived graph edge test expectation; Task 3 dead `/agents/analytics`
     endpoint & caller removal; Task 4 live `total_storage_bytes` query; Task 5 frontend
     fallback removal & null handling in `analyticsStore.ts`/`DashboardPage.tsx`; Task 6
     honest relabeling of offline evaluation benchmarks in `AnalyticsPage.tsx` with
     digit-for-digit historical verification).
  8. **Rate Limiting + Password-Strength Hardening** — ✅ VERIFIED COMPLETE / CLOSED
     (Tasks 1–3 fully executed and verified: Task 1 auth rate limiting on `/auth/login`
     and `/auth/register` at 5/min per IP via shared singleton limiter, 2/2 tests passed
     with HTTP 429 and cross-IP non-interference evidence; Task 2 AI & pipeline endpoint
     rate limits across 12 routes using shared limiter singleton, 13/13 tests passed
     including 20-request batch-safety and 60/61 boundary proofs; Task 3 5-rule strong
     password policy on `RegisterRequest` via Pydantic validator with non-retroactive
     login compatibility, 8/8 tests passed).
  9. **LLMClient Extraction & Gemini Test Harness** — ✅ VERIFIED COMPLETE / CLOSED
     (LLMClient.generate_text() interface, retry/failover handling, key-rotation state
     handling, quota-error detection, opt-in live Gemini test protection, and default
     regression protection against accidental live API calls).
  10. **Case-Level Summary + Grounded RAG Q&A — Batch 1: Persistence Scaffolding** — ✅ VERIFIED COMPLETE / CLOSED
      (`case_summaries` PostgreSQL table, SQLAlchemy model, Alembic migration with strictly lowercase enum constraint,
      `CaseSummaryRepository` with atomic updates and DESC-ordered queries, Pydantic schemas, 14/14 tests passed).
  11. **Case-Level Summary + Grounded RAG Q&A — Batch 2: Case Summary Generation** — ✅ VERIFIED COMPLETE / CLOSED
      (Case-level intelligence synthesis from structured pre-computed metadata without raw document re-reading; Tier 1
      corpus overview + Tier 2 notable findings; deterministic timeline aggregation; narrow top-N entity centrality
      reusing CentralityService and EdgeWeightingService formulas directly without full-graph overhead; 5 structured
      sections with "Notable Provisions & Findings" replacing literal "Clause"; 1 LLM call verified against real 423-doc
      case under hard ceiling of 5; state machine with 6 verified states; concurrency guard returning 409; SlowAPI 2/min
      rate limiting; case-scoped document security authorization; 14/14 tests passed).
- **Official Test & Build Baseline:** Full backend test suite **145 passed, 2 failed,
  3 skipped** (in 142–150s). The 2 failures are the documented baseline LLM non-deterministic variations
  (`tests/test_intelligence_layer.py::test_classification` asserting `'Contract' == 'Contracts'` and
  `tests/test_intelligence_layer.py::test_clustering` asserting `'Financial Fraud' in [...]`); 3 skipped tests
  (`test_report_exports_format_encoding` due to missing `reportlab`, `test_ocr_pdf_processing`
  due to missing test PDF, and `test_generate_text_live` because live Gemini execution is
  intentionally opt-in and `RUN_LIVE_GEMINI_TESTS` was not set). Frontend build clean (**0 errors**).
- **Environment Fragility Note:** An interpreter divergence was investigated between system Python (`python`,
  `C:\Python313\python.exe`) and the local virtualenv (`backend\.venv`). An orphan empty `docx/` namespace package
  in `.venv\Lib\site-packages` (dated 08-09-2026) caused `test_reports_api.py` to fail in virtualenv runs because
  Python's PEP 420 namespace handling allowed `import docx` to succeed, setting `DOCX_AVAILABLE = True`, where
  `docx.Document()` subsequently failed with `AttributeError`. Under standard system Python, `import docx` raises
  `ModuleNotFoundError`, correctly setting `DOCX_AVAILABLE = False` and passing cleanly. Batch 2 did NOT introduce
  this failure. Regressions must be evaluated by failure composition, not raw failure count.
- **Next Task:** Case-Level Summary + Grounded RAG Q&A — Batch 3: Grounded RAG Q&A (NEXT / NOT STARTED).

---

## 2. Completed + Verified

### Carried forward (verified in prior sessions, unchanged)
- Real embeddings, grounded summarization, hybrid privilege detection
  (F1 1.0000 on 24-doc synthetic benchmark), Timeline/Risk agents,
  Clustering with dynamic TF-IDF + LLM labeling, full JWT auth/RBAC,
  document ownership scoping, Human Review UI, domain NER (F1 0.8065
  combined), multilingual research NER (v3: Hindi 80%/Marathi 77% F1),
  Triage Orchestrator (verified via DOC_103A/DOC_103B branching proof),
  Tier 2 evaluation (400 hand-labeled Enron emails + 24 synthetic
  privilege docs), full 424-document real ingestion, Knowledge Graph and
  Timeline pages rendering real data. See MASTER_CONTEXT.md for full
  detail on each.

### Knowledge Graph Step 1 — Entity Alias Resolution — VERIFIED
(Preserved from prior verified state; unchanged.)
- Real DB-derived counts: 10,397 raw mentions, 5,335 unique raw entity
  strings, 5,087 canonical clusters produced, reconciled to 5,083 live
  entity nodes served by `/api/v1/graph` at the time of that audit.
- Cluster distribution: 4,884 singletons, 170 size-2, 26 size-3, 5
  size-4, 2 size-5 clusters.
- 5 real spot-checked merge examples confirmed correct (e.g. Kenneth Lay
  = "Ken Lay" + "Kenneth Lay" across 18 source documents).
- False-merge audit: title-only references, common surnames, and
  first-name/nickname compatibility adversarially tested — zero
  cross-person merges found.
- Artifact handling confirmed: header/protocol strings and bare
  single-token names correctly left as unmerged singletons.
- Regression: `test_entity_resolution.py` 12/12 passed.
- Independently corroborated by a separate Antigravity audit (matching
  core mechanisms: formula correctness, alias clustering, type
  isolation, empty-hash node handling).

### Knowledge Graph Step 2 — Real Edge Weighting — VERIFIED / RECONFIRMED
- Replaces the previous hardcoded uniform 0.8 edge weight with a
  data-derived, explainable formula:
  `S_breadth(D) = ln(1+1.5(D-1)) / ln(1+1.5(D_cap-1))`, `D_cap = 10`,
  plus a small DepthBoost and floor/ceiling clamps.
- Artifact/fragment suppression (`should_suppress_edge` in
  `edge_weighting.py`) implemented as generic logic (protocol/MIME/
  timezone header blocklist + a generic single-token-person rule) — not
  a hardcoded name list.
- Regression: `test_edge_weighting.py` — 9/9 passed.
- **Deeper D_cap/F_cap ceiling audit — CLOSED** (see Section 8 for full detail):
  - Six previously-suspicious ceiling-defining pairs (`ENRON`↔`Steven`,
    `NA`↔`Steven`, `ENRON`↔`Lynn`, `NA`↔`Lynn`, `PST`↔`Shelley Corman`,
    `ENRON`↔`Dutch\Fin Desk`) individually investigated against real raw
    document/header text.
  - `NA`, `PST`, and `Dutch\Fin Desk` confirmed genuine non-entity
    artifacts (Exchange OU routing, timezone/file-extension string, email
    client folder path) correctly handled by suppression logic.
  - `Steven` and `Lynn` confirmed real people affected by deliberate
    bare single-token ambiguity limitation (no false-positive cross-person
    merges). Neither appears among surviving top-D genuine pairs.
  - Surviving top genuine pairs: Shelley Corman↔ENRON (D=11, F=11, W=1.0000),
    Scott Neal↔ECT (D=10, F=11, W=1.0000), Kenneth Lay↔ENRON (D=9, F=10,
    W=0.9812), Mary Kay↔ENRON (D=8, F=8, W=0.9177), Kevin M Presto↔ENRON
    (D=7, F=7, W=0.8680).
  - Percentile check: distribution heavily right-skewed (p90–p98 at D=2,
    p99=3, anchors at D=7–11). `D_cap=10` / `F_cap=10` reconfirmed correct.

### Workstream 1 — Critical Cross-Tenant Data Leak — FIXED
**Status: CLOSED — independently verified with real HTTP evidence.**
- **Problem & Root Cause:** A production-readiness audit discovered and
  live reproduction confirmed that an authenticated user could access another
  user's/case's documents. Specifically, `check_document_access()` in
  `documents.py` only enforced ownership for orphan documents (`case_id=None`);
  case-owned documents bypassed ownership checks. Furthermore, `list_cases()`
  and `hybrid_search()` lacked user/case scoping.
- **Verification of Vulnerability:** Two real accounts ("Alice"/Firm Alpha
  and "Bob"/Firm Beta) and a real confidential document were tested across
  9 real attack vectors. All 9 leaked data prior to the fix.
- **Implementation:** Creator-only access model implemented using
  `case.created_by` and `document.uploaded_by` with administrator override
  (the database schema has no team/organization/tenant concept). Security
  fixes applied across 11 modules: `cases.py`, `documents.py`, `search.py`,
  `chunk_repository.py`, `graph.py`, `timeline.py`, `analytics.py`,
  `reports.py`, `review.py`, `intelligence.py`, and `ocr.py`.
- **WebSocket Hardening:** `websocket.py` was hardened to track authenticated
  `user_id` and support targeted user/case broadcasts.
- **Post-Fix Verification:** Exact original attack scenario re-run after
  the fix. All 9 attack vectors returned 403 Forbidden or empty results.
  `test_cross_tenant_access_isolation` added. 13/13 security audit tests
  passed. Follow-up discrepancies were investigated and fully explained.

### Workstream 2 — Quota-Exhaustion Honest Handling
**Status: CLOSED — independently verified with real triggered-failure tests and live HTTP evidence.**
- **Problem & Root Cause:** Quota exhaustion on LLM providers could
  previously cause a document to silently fall through and be marked
  `REVIEWED`, even though downstream analysis was incomplete.
- **Implementation:**
  - Added `DocumentStatus.QUOTA_PAUSED` enum state.
  - Updated database constraints via Alembic migration (`d7e8f9a0b1c2_add_quota_paused_status.py`).
  - Implemented `QuotaExhaustedException` and `is_quota_error()`.
  - Updated `orchestrator.py` to honestly pause processing on quota errors,
    preserving all real upstream stage results already completed.
  - Preserved `RiskAgent` deterministic keyword pre-screen without modification.
  - Preserved `ClassificationAgent` key-rotation retry logic without modification.
  - Added `POST /api/v1/documents/{id}/retry` endpoint enforcing creator-only
    access control.
  - Built smart-resume logic to avoid re-running valid completed stages.
  - Updated frontend with Quota Paused badges, warning alert banner, and
    interactive Resume button.
  - Updated analytics queries to exclude `quota_paused` documents from the
    reviewed document count.
- **Verification:** 8 real pytest tests covering quota behavior passed.
  A Windows-specific pytest asyncio workaround was properly scoped and
  removed from deployment roots. Live HTTP verification confirmed paused
  state and successful resume.

### Workstream 3 — File Storage Migrated to Supabase Storage
**Status: CLOSED — independently verified with real migration output, real bucket API evidence, and access-control re-testing.**
- **Problem:** Uploaded documents were previously stored on ephemeral local
  disk (`backend/uploads/`), creating data loss risks on container restarts.
- **Implementation:**
  - Designed `storage_service.py` with `StorageBackend` abstract base class,
    `SupabaseStorageBackend`, and `LocalStorageBackend`.
  - Document downloads continue strictly through authenticated
    `GET /api/v1/documents/{id}/download`, enforcing creator-only ownership.
  - No direct or public Supabase Storage URLs are exposed to clients.
  - The `"legal-documents"` bucket was independently verified to be **PRIVATE**.
  - Built migration script `scripts/migrate_storage_to_supabase.py`.
  - Storage failures return honest 502/400 HTTP errors.
- **Migration Execution & Verification:**
  - Migrated 426 real corpus documents (400 Enron + 24 synthetic + 2
    legitimately split across cases). Fresh SHA-256 checksums were computed
    on local and remote ends: 0 corruption, 0 failed uploads.
  - 6 missing local files were traced to old test fixtures, not real corpus data.
  - Migration idempotency verified: second execution resulted in 0 newly
    migrated, 426 already migrated.
  - New document uploads independently confirmed to land directly in
    Supabase Storage.
  - Cross-tenant access control re-tested against Supabase-backed downloads.
  - Storage usage: ~0.84 MB of 1 GB free-tier limit.
- *Dataset distinction note:* The 426 figure refers specifically to the
  migration storage corpus (400 Enron + 24 synthetic + 2 legitimately split
  across cases), while 424 refers to the primary active ingested dataset.

### Workstream 4 — Self-Registration + UX Improvements
**Status: CLOSED — independently verified at time of completion.**
- **Privilege Escalation Vulnerability Fixed:** During audit, a second real
  security vulnerability was discovered: `RegisterRequest` accepted a
  client-supplied `role`, allowing unauthenticated users to register as
  `{"role": "admin"}`. Server-side enforcement was implemented to strictly
  default self-registration to `LAWYER`. Real negative test verified that
  admin escalation attempts are blocked.
- **Features Implemented & Verified:**
  - Sign-up flow added to `LoginPage.tsx`.
  - Live account creation verified through UI: new account correctly had
    0 cases and 0 documents, and could not access other users' data.
  - Dashboard hardcoded fallback values removed.
  - "Flagged for Review" and "High & Critical Risk" separated into distinct
    metrics.
  - Technical UI jargon translated into plain legal terminology.
  - Real-time upload-processing progress feedback added, using ownership-scoped
    status polling.
- **Discrepancy Investigation:** Historical `flagged_documents` metric change
  (from 23 to 4–5) was investigated and found to be associated with user-scoping
  changes and underlying data evolution; exact timing/mechanism could not be
  fully reconstructed because no database status audit trail exists (this
  uncertainty is deliberately preserved).
- **Known Residual Issue:** Password minimum length of 6 remains a known
  weakness and was not addressed in this workstream.
- **Historical Verification:** Recorded a regression-suite pass at the time
  of completion, independently verified with real HTTP tests, live screenshots,
  and the regression suite available at that time.

### Workstream 5 — Supabase Keep-Alive — Documentation
**Status: DOCUMENTATION CLOSED; ACTIVATION PENDING.**
- **Investigation:** Supabase free-tier project pausing is triggered by
  inactivity on the PostgreSQL database itself. The existing
  `GET /api/v1/health` endpoint executes an active `SELECT 1` query, confirmed
  through live testing and server logs.
- **Implementation:** No application code changes were required. Because no
  git repository exists in the workspace, GitHub Actions was not utilized.
  Created [`docs/SUPABASE_KEEPALIVE.md`](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/docs/SUPABASE_KEEPALIVE.md)
  documenting three zero-cost options: cron-job.org, UptimeRobot, and
  Supabase pg_cron extension.
- **Activation Status:** **PENDING.** Manual project-owner setup has not
  been confirmed. The keep-alive mitigation is NOT yet active.

### Workstream 6 — Batch 1 — Session-Debris Cleanup
**Status: CLOSED / APPROVED.**
- **Scope:** Pure cleanup only — no application logic or database changes.
- **Deleted Artifacts:**
  - `scratch/` directory deleted: 203 obsolete files.
  - 7 root-level test/debug artifacts removed.
  - 11 backend-root test artifacts deleted, including orphaned SQLite DBs.
  - 12 `backend/scripts` temporary test artifacts deleted.
  - `__pycache__` directories cleaned up.
  - `apply_init_sql.py` inspected, confirmed to be genuinely empty
    (0 bytes / 1 comment line), and safely deleted.
  - `.github/workflows/ci.yml` was inspected and deliberately **KEPT**
    (harmless future CI infrastructure, though no git repository currently
    exists).
- **Post-Cleanup Verification:**
  - Pytest suite: **91 passed, 1 skipped, 5 failed**.
  - All 5 test failures were individually investigated and confirmed to be
    **pre-existing and completely unrelated to cleanup**:
    1. Embedding-norm assertion mismatch against actual API behavior
       (pre-existing test-design issue).
    2. Missing optional `reportlab` dependency (environment/dependency issue).
    3. `test_graph_edge_reconciliation.py` hardcoded expected edge count of
       `6955` (stale baseline due to subsequent legitimate document uploads).
    4. Known LLM non-determinism in `test_classification.py`.
    5. Known LLM non-determinism in `test_clustering.py`.
  - Frontend production build: `npm run build` passed with **0 errors**.
  - Backend startup verified clean.
  - Follow-up evidence closed all four audit gaps.

### Workstream 7 — Batch 2 — Honest Analytics Metrics & UI Remediation — VERIFIED COMPLETE / CLOSED
**Status: VERIFIED COMPLETE / CLOSED — all 6 implementation and verification tasks executed, independently confirmed with backend tests, live database queries, and headless browser evidence.**

- **Scope Evolution & Transparency Note (Standing Rule 4 in Action):**
  Batch 2's actual implementation grew beyond its original nominal scope (initial analytics queries) because rigorous, evidence-first investigation during development surfaced several deep, previously uncataloged issues:
  1. Broken KMeans clustering in the Python 3.13 environment caused by wheel architecture mismatch.
  2. A stale hardcoded edge assertion and test-harness database leak in `test_graph_edge_reconciliation.py`.
  3. A completely dead, fabricated backend endpoint (`/api/v1/agents/analytics`) returning 11 hardcoded metrics and sparklines.
  4. Uncertainty over whether document storage size was real or mock.
  5. Front-end fallback fabrication in `analyticsStore.ts` and `DashboardPage.tsx`.
  6. Front-end presentation of offline synthetic benchmark aggregates as "live" case metrics in `AnalyticsPage.tsx`.
  Rather than ignoring or glossing over these issues, each was methodically resolved and verified across 6 focused tasks.

- **Task 1 — KMeans/scikit-learn Environment & Exception-Handling Fix:**
  - Root cause: A wheel architecture mismatch (CPython 3.11 wheel installed into a CPython 3.13 `.venv`) caused `from sklearn.cluster import KMeans` to fail silently.
  - Fix: Clean reinstallation of `scikit-learn` matching Python 3.13; narrowed broad exception handling in `app/agents/clustering.py` from `except Exception:` to `except ImportError:` with explicit error logging and an informative `RuntimeError` raise (no silent fallback existed downstream).
  - Regression verified: `tests/test_intelligence_layer.py::test_clustering` passed; isolated intermittent failure in `test_risk_analysis` to unrelated LLM non-determinism across 5 repeated runs.

- **Task 2 — Graph Edge Count Reconciliation (`test_graph_edge_reconciliation.py`):**
  - Problem: `test_graph_edge_reconciliation.py` failed with `AssertionError: Expected exactly 6,955 doc-mention edges, got 6967` due to a hardcoded count that became stale as real documents were ingested.
  - Fix: Replaced hardcoded assertion with a dynamic, data-derived expectation computing `total_mentions` across the documents visible in that test's session.
  - Root-Cause Discovery: Diagnosed that `test_security_audit.py` unconditionally rebinds `app.db.session.AsyncSessionLocal` to SQLite with no teardown, silently redirecting subsequent tests in the same process away from PostgreSQL. (Logged as Issue 1 in Known Issues).

- **Task 3 — Removal of Dead Fabricated `/api/v1/agents/analytics` Endpoint:**
  - Problem: `/api/v1/agents/analytics` in `backend/app/api/v1/agents.py` returned 11 fully fabricated/mock values (`98.7`, `94.2`, `2.4`, `3241`, `42.7`, `84521`, hardcoded sparklines containing `1.9`).
  - Fix: Confirmed zero production consumers (the frontend `fetchAgentAnalytics()` was completely unused dead code). Deleted the endpoint, route declaration, and unused frontend service method entirely. Zero regressions.

- **Task 4 — Real Storage Metric Verification & Live Backend Query:**
  - Investigation: Confirmed `Document.file_size` is 100% populated (437/437 documents, genuine range 220 bytes to 22,233 bytes, sum 891,556 bytes across all documents; traced to genuine upload-time `file.read()` measurement in `documents.py`).
  - Implementation: Added `total_storage_bytes` to `GET /api/v1/analytics` (`backend/app/api/v1/analytics.py`), dynamically computed via `select(func.sum(Document.file_size))` scoped to creator/admin and non-excluded statuses (`status.notin_(excluded_entity_statuses)`).
  - Verification: Verified live return of exactly **889,159 bytes** across 430 non-excluded documents for admin scope (cross-checked three independent ways).

- **Task 5 — Frontend Fallback Removal & Honest Null/Pending States:**
  - `frontend/src/stores/analyticsStore.ts`: Removed all fabricated fallback numbers (`ocrAccuracy: 99.0`, `storageUsage: 42.7`, `apiUsage: 84521`, `retrievalQuality: 89.6`, `similarCases: 18`, `agentRuntime: 47.3`). Added `totalStorageBytes` to interface, mapped from `data.total_storage_bytes`.
  - `frontend/src/features/dashboard/pages/DashboardPage.tsx`: Removed fallback strings (`'99.0'`, `'0.84'`). Wired storage card (`m3`) to real formatted storage (e.g. `868.3 KB`). Unmeasured metrics honestly render `"N/A"` / `"Pending measurement"`.
  - Discrepancy Investigation: Traced the origin of `99.0` and `89.6` to `EvaluationRepository`'s `evaluation_metrics` table average (`avg_ocr_accuracy: 0.9903`, `avg_retrieval_precision: 0.8960` across 32 static benchmark rows), explaining why they matched past hardcoded values.
  - Logged a stray `0.99` fallback at line 95 of `DashboardPage.tsx` to Known Issues (Issue 2).

- **Task 6 — Relabeling Blended Synthetic-Benchmark Averages in `AnalyticsPage.tsx`:**
  - Problem: `AnalyticsPage.tsx` was independently calling `api.get('/analytics')` and rendering blended `evaluation_metrics` averages into chart titles as live case metrics, including an actively misleading label `"98.2% Live Benchmark"` for a static 24-doc synthetic benchmark.
  - Implementation:
    - Added a dedicated section header: `OFFLINE EVALUATION BENCHMARKS` with `Synthetic Benchmark Suite (N=32 records)` badge.
    - Relabeled Card 1 to `Retrieval Precision vs Recall`, added `Synthetic Benchmark` badge, subtitle `Blended Evaluation Average: 89.6% Precision / 86.4% Recall (offline, N=32 benchmark records)`, and surfaced dynamic backend caption `explanation.retrieval_precision_recall`.
    - Relabeled Card 2: completely eliminated misleading `"Live Benchmark"`, added `Synthetic Benchmark` badge, subtitle `Benchmark Test Set Accuracy: 98.2% (offline, N=32 benchmark records)`, and clarified 24 synthetic test documents.
    - Relabeled Card 3: `Hallucination Rate (Offline Evaluation Suite)`, surfaced `explanation.hallucination_rate`, and fixed a unit-formatting bug (`0.1698` was rendered unscaled as `Rate: 0.1698%`; corrected to `17.0%`).
    - Verified static per-split bar chart data digit-for-digit against `MASTER_CONTEXT.md` Section 12 and `data/full_evaluation_results.json`: all 16 data points confirmed to be exact historical evaluation findings, not fabricated.

- **Frontend & Backend Verification:**
  - Backend full pytest suite: **95 passed, 2 skipped, 1 failed** (flaky LLM assertion in `test_clustering.py`).
  - Frontend production build: `npm run build` completed with **0 errors**.
  - Visual verification: Headless browser screenshots captured and verified across `DashboardPage` and `AnalyticsPage`.

### Workstream 8 — Rate Limiting + Password-Strength Hardening — VERIFIED COMPLETE / CLOSED
**Status: VERIFIED COMPLETE / CLOSED — all 3 tasks executed and independently confirmed with 23 new backend tests (117 total passing), real HTTP 429 rate limit enforcement, and strict Pydantic password complexity validation.**

- **Task 1 — Authentication Rate Limiting (`/auth/login` and `/auth/register`):**
  - Problem & Risk: Authentication endpoints lacked request throttling, exposing the application to brute-force credential stuffing and automated registration spam.
  - Implementation:
    - Attached SlowAPI `limiter` from `app.core.rate_limit` (`Limiter(key_func=get_remote_address)`) to `/api/v1/auth/login` and `/api/v1/auth/register` in `backend/app/api/v1/auth.py`.
    - Both endpoints decorated with `@limiter.limit("5/minute")`.
    - Keyed strictly per client IP address.
  - Verification & Evidence:
    - 2/2 tests passing in `tests/test_rate_limit.py`.
    - Verified that 5 consecutive requests from client IP 1 succeed/fail authentication normally (HTTP 401 for bad login / 201 for register), and the 6th request is rejected with HTTP 429 `{"detail": "Rate limit exceeded: 5 per 1 minute"}`.
    - Verified cross-IP non-interference: requests from client IP 2 are unaffected by client IP 1's throttled state.
    - Regression verified: `test_registration_security.py` and `test_security_audit.py` (13/13) unaffected.

- **Task 2 — AI & Pipeline Endpoint Rate Limiting:**
  - Problem & Risk: Costly LLM orchestration, extraction, embedding, search, and file processing endpoints lacked rate limits, leaving the system vulnerable to accidental exhaustion of external LLM API quotas or denial-of-service.
  - Implementation:
    - Enforced rate limiting across 12 AI and pipeline endpoints using the exact same shared `limiter` singleton from `app.core.rate_limit` (confirmed zero duplicate `Limiter` instances in the codebase):
      - `/documents/upload` (60/min)
      - `/documents/upload-multiple` (10/min)
      - `/documents/{id}/retry` (10/min)
      - `/search` & `/search/semantic` (20/min)
      - `/embed` (10/min)
      - `/review` (5/min)
      - `/clusters` (10/min)
      - `/classify` (15/min)
      - `/timeline` (15/min)
      - `/entities` (20/min)
      - `/relationships` (20/min)
      - `/ocr` (20/min)
  - Verification & Evidence:
    - 13/13 new tests passing in `tests/test_rate_limit_ai_endpoints.py` with real HTTP 429 response assertions per endpoint.
    - Document upload batch-safety confirmed: 20 sequential uploads under the 60/min ceiling complete without 429 throttling.
    - Boundary proof confirmed: 60 sequential uploads allowed, exactly the 61st request rejected with HTTP 429.
    - Quota-exhaustion suite (8/8 in `test_quota_exhaustion.py`) reconfirmed passing: retry throttling did not interfere with `QUOTA_PAUSED` smart-resume logic.
  - Known Limitation Logged (not fixed): Frontend `DocumentsPage.tsx` currently uploads multiple selected files via a sequential loop of individual `POST /documents/upload` requests rather than using `POST /documents/upload-multiple`. While safe for typical batches (<60 files/min), batches >60 would hit the upload limit. (Logged to Known Issues).

- **Task 3 — Strong Password Policy Hardening:**
  - Problem & Risk: Registration previously permitted passwords as short as 6 characters with zero character class requirements, posing a credential compromise risk.
  - Implementation:
    - Implemented a 5-rule password complexity policy on `RegisterRequest.password` in `backend/app/schemas/user.py` using a Pydantic v2 `@field_validator("password")`:
      1. Minimum length: 8 characters.
      2. At least one uppercase letter (`isupper()`).
      3. At least one lowercase letter (`islower()`).
      4. At least one digit (`isdigit()`).
      5. At least one special character (non-alphanumeric, `not c.isalnum()`).
    - Specific, clear validation error messages returned for each distinct rule failure.
    - `LoginRequest.password` was deliberately retained with `min_length=1`: the strong password policy is strictly enforced on registration and is **non-retroactive** to pre-existing legacy accounts.
    - Confirmed absent: no password-reset or password-change endpoints currently exist in the API (identified as future integration points for this same validator).
  - Verification & Evidence:
    - 8/8 tests passing in `tests/test_password_policy.py`.
    - Verified all 5 individual rule rejections return HTTP 422 Unprocessable Entity with exact rule-specific error messages.
    - Compliant registration verified (HTTP 201).
    - Legacy weak-password login verified (HTTP 200).
    - Rate limit interaction verified: 422 validation rejections do not trigger premature 429 blocks until threshold.
  - Known Finding Logged (not fixed): Frontend `LoginPage.tsx` still performs client-side validation against `6+ characters` only; users submitting 6–7 character passwords pass frontend checks but receive backend 422 validation errors. (Logged to Known Issues).

- **Baseline Evolution Across Workstream 8:**
  - Pre-workstream baseline: **95 passed, 2 skipped, 1 failed** (`test_clustering.py` flaky LLM label).
  - After Task 1: **97 passed, 2 skipped, 1 failed**.
  - After Task 2: **110 passed, 2 skipped, 1 failed**.
  - After Task 3: **117 passed, 2 skipped, 2 failed** (a second flaky LLM test was observed: `test_classification` asserting `'Contract' == 'Contracts'`, alongside `test_clustering`; both confirmed non-deterministic LLM output label variations, NOT code regressions).
  - Frontend production build: **0 errors** maintained throughout all three tasks.

### Workstream 9 — LLMClient Extraction & Gemini Test Harness — VERIFIED COMPLETE / CLOSED
**Status: VERIFIED COMPLETE / CLOSED — LLMClient extraction, retry/failover handling, key-rotation state handling, quota-error detection, and opt-in test harness implemented and verified against production code and pytest suite.**

- **1. Live Gemini Test Guarded & Opt-In:**
  - File: `backend/tests/test_gemini_client.py`
  - The live Gemini API test is guarded with:
    ```python
    @pytest.mark.skipif(
        not os.getenv("RUN_LIVE_GEMINI_TESTS"),
        reason="Live Gemini API test consumes limited daily quota; opt-in with RUN_LIVE_GEMINI_TESTS=1",
    )
    ```
  - Therefore:
    - Normal regression runs do NOT call the live Gemini API.
    - The live test can be explicitly enabled only with: `RUN_LIVE_GEMINI_TESTS=1`.
    - This prevents accidental consumption of limited daily API quota (500/day primary, 20/day fallback).

- **2. Default Full Regression Result:**
  - Command: `python -m pytest -q --tb=short`
  - Verified result: **119 passed, 2 failed, 3 skipped** (Time: 117.29s).
  - The 2 failures are known/pre-existing baseline failures (unrelated to LLMClient test-harness work):
    - `tests/test_intelligence_layer.py::test_classification`
    - `tests/test_intelligence_layer.py::test_clustering`
  - The 3 skipped tests are:
    1. `tests/test_evaluation_analytics_integration.py::test_report_exports_format_encoding` (Reason: `reportlab` library missing in the environment).
    2. `tests/test_ocr_agent.py::test_ocr_pdf_processing` (Reason: required test PDF file is missing).
    3. `tests/test_gemini_client.py::test_generate_text_live` (Reason: live Gemini test is intentionally opt-in and `RUN_LIVE_GEMINI_TESTS` was not set).
  - Note: The default test suite is explicitly NOT described as fully green due to the two pre-existing baseline failures.

- **3. Targeted Default Gemini Test Result:**
  - Command: `pytest tests/test_gemini_client.py -v -rs`
  - Verified result: **1 passed, 1 skipped**.
  - Specifically:
    - `test_llm_client_failover_and_validation`: PASSED
    - `test_generate_text_live`: SKIPPED because live execution is opt-in.
  - Important: `test_llm_client_failover_and_validation` performs **ZERO live API calls**. It verifies:
    - Input validation before network dispatch
    - `AgentException` handling for empty prompts
    - Quota-error pattern matching through `is_quota_error()`
    - Key rotation state behavior
    - `reset_primary_exhausted()`
    - `mark_primary_exhausted()`

- **4. Explicit Opt-In Live Gemini Verification:**
  - The live test was intentionally executed ONCE with `RUN_LIVE_GEMINI_TESTS=1`.
  - Command equivalent:
    `$env:RUN_LIVE_GEMINI_TESTS="1"; python -m pytest tests/test_gemini_client.py -v -s; Remove-Item Env:\RUN_LIVE_GEMINI_TESTS`
  - Verified result: **2 passed in 3.12s**.
  - Specifically:
    - `test_generate_text_live`: PASSED
    - `test_llm_client_failover_and_validation`: PASSED
  - The live Gemini API call succeeded.
  - Record: **Explicit opt-in live Gemini verification: PASSED (single live API invocation).**
  - No API key, token, or credential is included or exposed.

- **5. Retry / Failover Implementation Confirmed Against Production Code:**
  - The actual production agents were inspected:
    - `backend/app/agents/summarization.py`: retry loop uses 3 attempts; rate-limit handling waits 15 seconds between attempts (`await asyncio.sleep(15.0)`).
    - `backend/app/agents/classification.py`: retry loop uses 3 attempts; rate-limit handling waits 15 seconds between attempts (`await asyncio.sleep(15.0)`).
  - Record verified behavior:
    - 3 retry attempts
    - 15-second wait on rate-limit retry
    - Behavior confirmed directly from actual production implementation (not implied as experimentally stress-tested).

- **6. Workstream Status & Scope:**
  - Mark: **CLOSED / VERIFIED**.
  - The verified scope includes:
    - `LLMClient.generate_text()` interface
    - Retry/failover handling
    - Key-rotation state handling
    - Quota-error detection
    - Opt-in live Gemini test protection
    - Default regression protection against accidental live API calls
  - IMPORTANT: "LLMClient extraction is closed" means this specific workstream is closed. It does NOT mean the overall CaseGraph/New-Legal project is complete.

### Case-Level Summary + Grounded RAG Q&A — Batch 1: Persistence Scaffolding — CLOSED
**Status: CLOSED / VERIFIED** (Persistence scaffolding, database model, migration, repository, and tests verified)
- **Model & Database Table:**
  - Designed and created the `case_summaries` table (`CaseSummary` model in `backend/app/models/case_summary.py`).
  - Columns: `id` (UUID PK), `case_id` (UUID FK -> cases.id, ON DELETE CASCADE, NOT NULL), `status` (Enum: `generating`, `complete`, `failed`, `quota_paused`), `source_data_hash` (VARCHAR(64)), `summary_json` (JSONB, nullable), `model_version` (VARCHAR(64)), `generated_by` (UUID FK -> users.id, nullable), `generated_at` (TIMESTAMPTZ, nullable), `source_doc_count` (INTEGER), standard `created_at` and `updated_at`.
- **Alembic Migration & Enum Hardening:**
  - Generated migration `3508daeefd89_add_case_summaries_table.py`.
  - Self-skeptical review identified and corrected an autogenerated dual-case status CHECK constraint (`('generating', 'complete', 'failed', 'quota_paused', 'GENERATING', 'COMPLETE', 'FAILED', 'QUOTA_PAUSED')`). Hardened to strictly lowercase variants only (`('generating', 'complete', 'failed', 'quota_paused')`) matching the established `DocumentStatus` pattern.
- **Repository & Registration:**
  - Implemented `CaseSummaryRepository` (`backend/app/repositories/case_summary_repository.py`) with `create()`, `get_latest_by_case()`, `update_status()`, and `save_summary()`.
  - Registered `CaseSummary` in `backend/app/models/__init__.py` and `backend/migrations/env.py`.
- **Verification:**
  - 14/14 CRUD tests in `tests/test_case_summary_crud.py` passed, including explicit named tests for DESC `created_at` ordering and status transitions.

### Case-Level Summary + Grounded RAG Q&A — Batch 2: Case Summary Generation — CLOSED
**Status: CLOSED / VERIFIED** (Case-level intelligence synthesis, 5-section executive summary, state machine, concurrency guard, narrow entity centrality, rate limiting, and case security authorization verified on real 423-document case)
- **Architecture & Synthesis Strategy:**
  - Synthesizes case-wide intelligence strictly from pre-computed, stored document metadata (`doc_metadata`) without re-reading raw document text or re-running document-level pipelines.
  - **Tier 1 Corpus Overview:** Structured minimal overview across all 423 documents in the case (filename, primary category, document summary excerpt, key entities).
  - **Tier 2 Notable Findings Expansion:** Deep structured expansion for high-value subsets: privileged documents, high/critical risk files, and flagged evidentiary items.
  - **Deterministic Timeline Aggregation:** Chronological event timeline extraction with core operational activity window (`core_activity_start` to `core_activity_end`) distinguished from external or historical citation dates.
  - **Narrow Top-N Entity Centrality:** Reuses verified Step 2 (`EdgeWeightingService`) and Step 3 (`CentralityService`) mathematical formulas directly against case-scoped entity metadata, completely bypassing full-graph assembly overhead.
- **5 Conceptual Structured Sections:**
  1. `executive` — Executive summary of case scope, operational timeline, and core narrative.
  2. `legal` — Legal claims, defenses, key legal theories, and regulatory implications.
  3. `notable_provisions_and_findings` — High-risk terms, critical liabilities, and privileged materials (replaces the earlier literal "Clause" concept to reflect actual evidentiary findings).
  4. `evidence` — Key communications, factual admissions, documentary trail, and evidentiary gaps.
  5. `key_people_and_relationships` — Central actors ranked by weighted degree centrality with verified incident communication/interaction edges.
- **LLM Call Budget Ceiling:**
  - Single Gemini invocation (`gemini-3.5-flash-lite`). Target $\le 3$ calls, hard ceiling $\le 5$ calls; verified **exactly 1 LLM call** executed on the real 423-document case.
- **API Surface & Endpoints:**
  - `POST /api/v1/cases/{case_id}/summary/generate`: Initiates summary synthesis. Enforces SlowAPI `2/minute` rate limit and returns HTTP 200 (success), 409 (conflict if already generating), 403 (unauthorized access), 429 (rate limit exceeded), or 503 (quota paused).
  - `GET /api/v1/cases/{case_id}/summary`: Fetches latest summary. Returns HTTP 200 (complete summary), 404 (no summary exists), or 403 (unauthorized access). Includes `stale: true` flag if source data hash differs from current case document state (does NOT auto-regenerate; manual MVP trigger).
- **State Machine Verification (6 Verified States):**
  - Row 1: No summary $\rightarrow$ GET returns 404 with explicit detail message.
  - Row 2: In-flight generation $\rightarrow$ GET serves previous COMPLETE summary with `generating: true`.
  - Row 3: Generation success $\rightarrow$ atomic update to `COMPLETE` with `summary_json`, `model_version`, `generated_at`.
  - Row 4: Non-quota generation failure $\rightarrow$ status `FAILED`, GET serves previous COMPLETE summary with `failed_last_generation: true`.
  - Row 5: Quota exhaustion $\rightarrow$ status `QUOTA_PAUSED`, HTTP 503, preserves previous COMPLETE summary.
  - Row 6: Stale state $\rightarrow$ live data hash mismatch returns `stale: true` without triggering automatic regeneration.
- **Concurrency & Security Guards:**
  - Near-simultaneous `POST /generate` requests return HTTP 409 Conflict; exactly one LLM generation sequence runs.
  - Explicit case-scoped authorization: `get_case_scoped_document_ids(db, case_id, current_user)` strictly enforced on both endpoints. Unauthorized stranger and cross-case requests deterministically return HTTP 403 Forbidden; admin override succeeds.
- **Review Issues Investigated & Resolved:**
  1. *Privilege Count Reconciliation:* Reconciled discrepancy between initial 12/6/18 report and live query: exactly **19 unique privileged documents** (`is_privileged == True`) in the active case (11 attorney-client, 6 work-product, 2 dual/other).
  2. *Synthetic & Historical Dates:* `earliest_referenced_date` (1930-05-20, historical statutory citation) and `latest_referenced_date` (2024-10-12, synthetic benchmark authoring dates) are preserved honestly; summary directive anchors case narrative to core operational window (1999–2002) and logs synthetic dates as a known limitation.
  3. *Real Centrality Integration:* Corrected initial raw mention-counting implementation to directly reuse `CentralityService` (weighted degree) and `EdgeWeightingService` (calibrated weights). Top entities accurately reflect real centrality (e.g. Fletcher J Sturm, weighted degree 56.7642, importance 1.0, top communication edges).
  4. *Deterministic Rate Limit Proof:* Pinned exact expected HTTP outcomes across rapid attempts (Attempt 1: 403, Attempt 2: 403, Attempt 3: 429).
  5. *Zero Live Quota Consumption for Quota Testing:* Verified quota-exhaustion behavior using an injected `QuotaExhaustedException` mock; zero live production API quota was consumed.
  6. *Narrow Method Latency Optimization:* Calling `_build_knowledge_graph()` was measured at ~18.6s cold / 7.1–7.4s warm. The narrow method eliminated full graph assembly and redundant document queries, reducing in-memory entity calculation to **2.7084s – 2.8982s** (~70–85% reduction). Total end-to-end endpoint latency measured at **23.6708s** on the real 423-doc case (LLM ~11.5s, narrow centrality ~2.8s, timeline ~1.2s, DB I/O & transport ~7.7s).
  7. *Internal System Token Mechanism Removed:* An initial draft used an inline `ADMIN` token payload to call `_build_knowledge_graph`. With the narrow method, this mechanism was completely deleted. Authorization is enforced solely at the endpoint boundary.
- **Verification:**
  - 14/14 tests in `tests/test_case_summary_generation.py` passed.
  - Real 423-document case execution verified: status `complete`, 5 non-empty sections, 1 LLM call.

---

## 3. Knowledge Graph Step 3 — Centrality-Based Node Sizing — VERIFIED WITH DOCUMENTED LIMITATIONS

**Status: VERIFIED WITH DOCUMENTED LIMITATIONS** (core mechanism, math,
and calibration independently confirmed; non-blocking limitations documented).

### What was built
- New `CentralityService` (`backend/app/services/centrality_service.py`)
  computes real **weighted-degree (node strength) centrality** over the
  live, Step-1-resolved, Step-2-weighted, suppressed **entity-entity**
  edges only — document-mention edges are explicitly excluded.
- Replaces the old hardcoded uniform `0.75` entity node importance.
  **Document node importance remains unchanged at `0.9`.**
- **Normalization:** single global logarithmic formula, no type-specific
  branching:
  ```
  importance(v) = 0.05 + 0.95 * ln(1 + min(strength(v), C)) / ln(1 + C)
  ```
  Zero-degree (isolated) entities receive exactly `0.05` via this same
  formula, with no special-casing required.
- **Cap `C = 9.0`**, derived reproducibly as
  `C = ceil(p99 of the connected, artifact-unflagged strength distribution) = ceil(8.8218) = 9.0`.
- **Weighted degree retained as sole metric:** cheap, deterministic,
  directly built on Step 2's verified real weights; betweenness centrality
  deferred.
- **No type-specific normalization:** single global scale ensures cross-type
  comparability.
- Computed **per-request**, consistent with `EdgeWeightingService` (<10ms).

### Two remediation rounds (both resolved)
1. **Round 1** (initial single-token-organization contamination):
   501 single-token, non-email entities mistyped as `organization` were
   contaminating calibration. Resolved with generic `is_single_token_organization()`
   flagging rule (mirroring Step 2's `is_single_token_person()`), excluding
   flagged nodes from `C` derivation, and adding frontend visual warnings.
2. **Round 2** (reporting-layer transcription error): direct inspection
   confirmed no code defect ever existed in strength calculations — a
   milestone table in the Round 1 report contained a manual transcription
   error. Verified by re-running `compare_centrality_caps.py` independently;
   correct values reproduced.

### Real calibration data (final, verified)
- **4,264 entity nodes** analyzed (entity-entity graph).
- **322 email-pattern strings** mistyped as `organization`, flagged.
- **493 single-token, non-email fragments** mistyped as `organization`,
  flagged structurally.
- **2,677 connected entities** remaining after excluding flagged categories.
- Connected, unflagged strength distribution: p90 = 3.0680, p95 = 6.2258,
  p98 = 7.3174, **p99 = 8.8218** → **C = 9.0**.

### Real milestone values (final, verified against live `/api/v1/graph`)
| Entity | Type | Weighted Degree (strength) | Importance |
|---|---|---|---|
| ENRON | organization | 107.4154 | 1.0000 |
| ECT | organization | 68.0520 | 1.0000 |
| Shelley Corman | person | 14.1495 | 1.0000 |
| Scott Neal | person | 12.5504 | 1.0000 |
| Kenneth Lay | person | 7.0377 | 0.9099 |
| Median connected entity | — | ~0.5–0.65 | ~0.22–0.26 |
| Zero-degree / isolated entity | — | 0.0000 | 0.0500 (floor) |

---

## 4. Centrality Artifact Handling (Step 3)

- **322 email-pattern organization strings** — flagged via regex detection
  of email-like labels typed `organization`.
- **493 single-token organization fragments** — flagged via generic
  structural rule (single token, no `@`, typed `organization`).
- Both categories are **flagged only, never silently reclassified** (`likely_misclassified`).
- Both categories are **excluded from `C` calibration sample**.
- Flagged nodes still receive real, computed importance values via the
  global formula.
- **Frontend visually marks flagged nodes** (dashed border + badge in
  `CustomNode.tsx`). `NodeDetailPanel.tsx` displays an explicit warning.

### Residual, documented (non-blocking) limitations
- **8 legacy Lotus Notes/Exchange routing strings** with non-standard
  `@` usage (e.g. `'NA/Enron@Enron'`, `'scorman@enron'`) contain `@` but
  aren't valid emails. Low strength (≤ 0.75), no impact on `C` or top
  rankings. Documented edge case.
- **Steven / Lynn ambiguous-merge limitation** — real people, bare-token
  nodes, does not affect the centrality ceiling or Step 3 calibration.

---

## 5. Frontend Status

- `CustomNode.tsx` dynamically scales entity node dimensions, padding,
  typography, and icon sizing based on centrality `importance` (`[0.05, 1.0]`).
- Document nodes retain fixed sizing (`0.9`).
- Flagged nodes receive dashed borders, warning badges, and detail warnings.
- Missing `importance` fallback set to `0.05` (mathematical floor).
- Live authenticated browser screenshots verified canvas rendering.
- `LoginPage.tsx` updated with self-registration form; defaults safely to LAWYER.
- Dashboard updated: hardcoded fallbacks removed; "Flagged for Review" and
  "High & Critical Risk" separated.
- Technical terminology rewritten into clear legal language.
- Real-time upload processing feedback with ownership-scoped polling.
- `npm run build` passed with **0 errors**.

---

## 6. Testing / Verification Status

### Knowledge Graph Regression (27/27 passed)
- `test_centrality.py` — 6/6 passed.
- `test_edge_weighting.py` — 9/9 passed.
- `test_entity_resolution.py` — 12/12 passed.

### Security & Access Control
- Cross-tenant access isolation audit: 13/13 tests passed.
- Admin privilege escalation blocked (negative test passed).

### Rate Limiting & Password Hardening (23/23 passed)
- `test_rate_limit.py` — 2/2 passed (auth login/register 5/min rate limits, HTTP 429, cross-IP non-interference).
- `test_rate_limit_ai_endpoints.py` — 13/13 passed (per-endpoint AI/pipeline rate limits, upload batch-safety 20-req and 60/61 boundary proofs).
- `test_password_policy.py` — 8/8 passed (5 password rejection rules, compliant registration, non-retroactive legacy login, rate-limit interaction).

### Quota-Exhaustion Handling
- 8/8 pytest tests passed for quota paused behavior, smart-resume, and retry.

### LLMClient & Gemini Test Harness (2/2 verified)
- `test_gemini_client.py` (Default targeted run, zero live API calls): **1 passed, 1 skipped**.
  - `test_llm_client_failover_and_validation`: PASSED (verifies input validation before network dispatch, AgentException handling for empty prompts, quota-error pattern matching through `is_quota_error()`, key rotation state behavior, `reset_primary_exhausted()`, and `mark_primary_exhausted()`).
  - `test_generate_text_live`: SKIPPED (live Gemini execution is intentionally opt-in; guarded with `@pytest.mark.skipif(not os.getenv("RUN_LIVE_GEMINI_TESTS"), ...)`).
  - Performs **ZERO live API calls**.
- `test_gemini_client.py` (Explicit opt-in live Gemini test via `RUN_LIVE_GEMINI_TESTS=1`): **2 passed in 3.12s**.
  - `test_generate_text_live`: PASSED.
  - `test_llm_client_failover_and_validation`: PASSED.
  - Succeeded with single live Gemini API invocation. No secrets or credentials exposed.

### Official Full Test Suite Baseline
- Pytest full run: `python -m pytest -q --tb=short` $\rightarrow$ **119 passed, 2 failed, 3 skipped** (Time: 117.29s).
  - The 2 failures are known/pre-existing baseline failures in `test_intelligence_layer.py` (confirmed LLM output variations rather than code regressions; unrelated to LLMClient test-harness work):
    1. `tests/test_intelligence_layer.py::test_classification`
    2. `tests/test_intelligence_layer.py::test_clustering`
  - The 3 skipped tests are:
    1. `tests/test_evaluation_analytics_integration.py::test_report_exports_format_encoding` (Reason: `reportlab` library missing in environment).
    2. `tests/test_ocr_agent.py::test_ocr_pdf_processing` (Reason: required test PDF file is missing).
    3. `tests/test_gemini_client.py::test_generate_text_live` (Reason: live Gemini test is intentionally opt-in and `RUN_LIVE_GEMINI_TESTS` was not set).
  - Note: The default test suite is explicitly NOT described as fully green due to the two known baseline failures.
  - Explicit opt-in live Gemini verification: **2 passed in 3.12s** (single live API invocation; `test_generate_text_live` and `test_llm_client_failover_and_validation` both PASSED).
  - Crucially, all security, quota, storage, graph reconciliation, rate limiting, password policy, and LLMClient failover/validation tests pass cleanly. Default regression runs execute zero live API calls.
- Frontend production build: `npm run build` passed with **0 errors** (built in 5.71s).
- Backend startup verified clean.

---

## 7. Implemented But Not Verified

- **Dashboard "AI Agents" panel per-agent stats re-fix** — needs independent
  verification with real evidence to ensure distinct, non-mock stats are
  served across agents.
- **Supabase Keep-Alive Activation** — documentation delivered, but manual
  activation by the project owner is **PENDING** and unconfirmed.

---

## 8. Step 2 Ceiling Audit — CLOSED

- Traced ceiling-defining pairs to real raw email text.
- `NA`, `PST`, `Dutch\Fin Desk` confirmed genuine non-entity artifacts
  handled by suppression.
- `Steven` and `Lynn` confirmed real people with ambiguous single-token
  contexts; no impact on ceiling.
- `ENRON` canonical ID consistency confirmed.
- `D_cap = 10` / `F_cap = 10` reconfirmed correct; max-based calibration
  justified over percentile-based (p99=3 vs genuine ties at D=7–11).

---

## 9. Planned / Not Started (Priority Order)

1. **Case-Level Summary + Grounded RAG Q&A — Batch 3: Grounded RAG Q&A (NEXT / NOT STARTED)**
   - **Planned Architecture:** Question $\rightarrow$ case authentication/authorization $\rightarrow$ retrieve case-scoped chunks $\rightarrow$ if zero relevant chunks, return an honest "not found / insufficient evidence" response without calling LLM $\rightarrow$ grounded prompt $\rightarrow$ `LLMClient` $\rightarrow$ deterministic cited-chunk existence gate $\rightarrow$ token-overlap grounding gate $\rightarrow$ answer + citations OR suppression/warning.
   - **Planned MVP Scope:** Stateless single-turn Q&A, case-scoped top-k retrieval, evidence citations, strict grounding refusal if facts not in case, adversarial "not in case" verification, endpoint security, quota-aware behavior.
   - **Implementation Status:** NOT STARTED (0 lines implemented, 0 endpoints created).
2. **Hardcoded case-name fix** ("California Energy Market Practices Inquiry"
   in 5 frontend locations).
3. **Test-account/test-case cleanup** (~28 test accounts, 2 test cases;
   dry-run cascade/orphan safety check required first).
4. **JWT logout / token blocklist mechanism** (invalidate tokens before
   natural 60-min expiry).
5. **Document status audit trail** (`status_history` table for transition
   tracking).
6. **Report Rewrite** (reframe around case-investigation, pipeline+orchestrator,
   real graph, diagram reconciliation; unblocked, but preceded by security/hardening).
7. **Existing lower-priority issues** (graph latency ~9.68s, OCR mock
   fallback strings, Dashboard AI Agents panel verification, cross-page
   entity linking, legacy Lotus Notes strings).

---

## 10. Currently In Progress

- **Nothing is actively mid-task.**
- Case-Level Summary + Grounded RAG Q&A — Batch 1 (Persistence Scaffolding) is **CLOSED / VERIFIED**.
- Case-Level Summary + Grounded RAG Q&A — Batch 2 (Case Summary Generation) is **CLOSED / VERIFIED**.
- Workstream 8 (Rate Limiting + Password-Strength Hardening) is **VERIFIED COMPLETE / CLOSED** (Tasks 1–3 executed, verified, and closed).
- Workstream 9 (LLMClient Extraction & Gemini Test Harness) is **VERIFIED COMPLETE / CLOSED** (LLMClient extraction, failover/retry handling, key-rotation state handling, quota-error detection, and opt-in test harness verified).
- Next task: **Case-Level Summary + Grounded RAG Q&A — Batch 3: Grounded RAG Q&A (NEXT / NOT STARTED)**.

---

## 11. Known Issues / Limitations / Open Findings

1. **Batch 2 — Hardcoded Analytics Values & Mislabeled Benchmarks:** **RESOLVED / CLOSED**
   (Section 2, Workstream 7). `total_entities_detected` dynamically computed from DB
   (10,409 raw mentions across 430 reviewed/flagged documents); `total_storage_bytes`
   dynamically computed from DB (`Document.file_size`, 889,159 bytes); `avg_review_time_seconds`
   and `avg_confidence_score` honestly returned as `null`/`None`. Frontend renders `N/A`
   with neutral dashed sparkline. Dead `/api/v1/agents/analytics` endpoint deleted.
   `AnalyticsPage.tsx` offline synthetic benchmarks honestly relabeled.
2. **Rate Limiting:** **RESOLVED / CLOSED in Workstream 8 (Tasks 1 & 2)**. Shared SlowAPI
   singleton (`limiter`) attached to FastAPI app and enforced across `/auth/login` (5/min),
   `/auth/register` (5/min), `/documents/upload` (60/min), `/documents/upload-multiple` (10/min),
   `/documents/{id}/retry` (10/min), `/search` & `/search/semantic` (20/min), `/embed` (10/min),
   `/review` (5/min), `/clusters` (10/min), `/classify` (15/min), `/timeline` (15/min),
   `/entities` (20/min), `/relationships` (20/min), and `/ocr` (20/min). Verified with 15 passing
   tests with HTTP 429 and cross-IP non-interference evidence.
3. **Password Policy:** **RESOLVED / CLOSED in Workstream 8 (Task 3)**. Enforces 5-rule strong
   password policy on registration in `backend/app/schemas/user.py` (minimum 8 characters, at
   least one uppercase letter, one lowercase letter, one digit, and one special character) via
   Pydantic v2 `@field_validator`. Non-retroactive to legacy logins. Verified with 8 passing tests.
4. **JWT Logout:** Logout does not invalidate the token; JWT remains valid until natural
   expiry (~60 minutes).
5. **Hardcoded Case Name:** `"California Energy Market Practices Inquiry"` appears in 5
   frontend locations as fallback/display text.
6. **Document Status Audit Trail:** No `status_history` table exists, preventing full
   historical reconstruction of document state transitions.
7. **Test-Account / Test-Case Cleanup:** ~28 test/verification accounts and 2 test cases
   remain in the database. Deletion has NOT been performed; requires a dry-run cascade check.
8. **Legacy Upload Files:** ~332 files (~1.5 MB) remain in `backend/uploads/` after the
   Supabase migration.
9. **Stale Graph Edge Count in Tests:** **RESOLVED in Batch 2 / Task 2**. Replaced the
   hardcoded `6955` edge assertion in `test_graph_edge_reconciliation.py` with a live
   data-derived expectation.
10. **Batch 2 Backlog Item 1 — `test_security_audit.py` Global Session Monkeypatch:**
    - **File:** `backend/tests/test_security_audit.py`, lines 15–21.
    - **What it does:** At module import time, `test_security_audit.py` unconditionally
      rebinds `app.db.session.AsyncSessionLocal` to a local SQLite engine
      (`sqlite+aiosqlite:///./test_security.db`) with zero teardown or restoration.
    - **Why it's a problem:** Any subsequent test in the same pytest session silently loses
      access to PostgreSQL and queries SQLite instead (the root cause of the 6,967 vs 4
      edge count discrepancy).
    - **Recommended fix:** Convert to an autouse pytest fixture with `try/finally` teardown
      restoration. (Candidate for test-harness-hardening workstream; logged, not fixed).
11. **Batch 2 Backlog Item 2 — `DashboardPage.tsx` Line 95 Stray `0.99` Fallback:**
    - **File:** `frontend/src/features/dashboard/pages/DashboardPage.tsx`, line 95.
    - **What it does:** When mapping documents fetched via `api.get('/documents?page_size=1000')`,
      assigns `ocrAccuracy: meta.confidence_score || 0.99`.
    - **Why it's a problem:** If a document lacks `confidence_score` (or is null), this fallback
      injects `0.99` (99%) into internal table previews, even though the primary dashboard
      card was cleaned in Task 5.
    - **Recommended fix:** Replace with `meta.confidence_score ?? null` and render `"N/A"`
      in downstream table progress bars. (Logged, not fixed).
12. **Existing Lower-Priority Issues:**
    - `/api/v1/graph` endpoint latency (~7.3s–9.68s baseline from document/entity assembly loop).
    - OCR mock fallback strings in `ocr.py`.
    - Dashboard AI Agents panel verification needed.
    - Cross-page entity linking not implemented.
    - 8 legacy Lotus Notes/Exchange routing strings unflagged.
    - CASE_REFERENCE NER type deliberately regex-only.
    - VerificationAgent uses token overlap rather than full NLI.
    - `.env` embedding provider naming alias (`sentence-transformers` -> Gemini).
13. **Discrepancy Note — Graph Node Count Scope:**
    - Live `/api/v1/graph` endpoint returns **4,727 total nodes** (437 document nodes +
      4,290 canonical entity nodes) with 9,884 edges.
    - Historical Step 1 audit recorded **5,087 clusters / 5,083 canonical nodes** from an
      earlier offline run over an earlier document subset and unpruned singletons.
    - Stale UI mock constant `1,506` was never a real measurement and has now been completely
      eradicated from frontend code.
14. **Workstream 8 Finding 1 — Frontend One-File-Per-Request Upload Loop:**
    - **File:** `frontend/src/features/documents/pages/DocumentsPage.tsx`
    - **What it does:** When uploading multiple files, the frontend uploads each file individually
      in a sequential `for` loop hitting `POST /api/v1/documents/upload` once per file, rather than
      calling the batch endpoint `POST /api/v1/documents/upload-multiple`.
    - **Why it's a limitation:** While realistic batch uploads remain well within the 60 requests/min
      ceiling, very large batch uploads (>60 files in <60 seconds) would trigger HTTP 429 rate limiting.
    - **Recommended fix:** Refactor frontend upload handler to use `POST /api/v1/documents/upload-multiple`
      (which accepts multipart `files: list[UploadFile]` and has a 10 requests/min limit). (Logged, not fixed).
15. **Workstream 8 Finding 2 — Frontend LoginPage.tsx Password Validation Copy Mismatch:**
    - **File:** `frontend/src/features/auth/pages/LoginPage.tsx`
    - **What it does:** Client-side validation in `LoginPage.tsx` checks only `password.length >= 6` with
      hint text "Must be at least 6 characters".
    - **Why it's a problem:** Backend registration now strictly enforces 8+ characters, uppercase, lowercase,
      digit, and special character. A user registering with 6 or 7 characters (or missing character classes)
      passes client validation but fails on the server with HTTP 422.
    - **Recommended fix:** Update client-side validation schema and UI hint text in `LoginPage.tsx` to match
      the backend 5-rule password policy. (Logged, not fixed).
16. **Case-Level Summary Finding 1 — Synthetic Benchmark Document Dates in Timeline Aggregates:**
    - **Context:** The 24 synthetic regulatory benchmark documents ingested into the Enron corpus carry authoring dates from 2023–2024, causing the aggregated `latest_referenced_date` to reflect the benchmark creation window rather than the historical 1999–2002 Enron dispute.
    - **Handling:** Rather than silently fabricating or overwriting raw document metadata, the summary prompt directives specifically anchor executive narrative to the core operational activity window (`core_activity_start` to `core_activity_end`), distinguishing external or synthetic benchmark dates from core operational conduct. Logged honestly as a known limitation for downstream presentation.
17. **Permanent Environment Fragility Note — `.venv` vs System Python Interpreter Divergence (Namespace Package Artifact):**
    - **File:** `backend/.venv/Lib/site-packages/docx`
    - **What it does:** An orphan, empty directory named `docx/` from an old installation attempt (dated 08-09-2026) exists inside the local `.venv`. Under Python 3's PEP 420 (Implicit Namespace Packages), `import docx` succeeds without error, causing `DOCX_AVAILABLE = True` in `app/agents/report.py`. When `test_reports_api.py::test_case_scoping_helper_and_report_export` is run under `.venv`, it expects HTTP 200 for docx export, but `ReportAgent._to_docx` crashes on `docx.Document()` with `AttributeError: module 'docx' has no attribute 'Document'`, returning HTTP 400 and failing the test.
    - **Contrast with System Python:** Under the project's standard system Python (`C:\Python313\python.exe`), `python-docx` is not installed; `import docx` raises `ModuleNotFoundError`, correctly setting `DOCX_AVAILABLE = False`. The test executes the `else:` branch (`assert res_docx.status_code == 400`), passing 100% cleanly.
    - **Critical Rule:** This failure was NOT caused by Batch 2 code. All future regression executions must explicitly record the exact interpreter used, environment, and exact failing test composition (not merely a raw failure count) to avoid confusing environmental package artifacts with code regressions. Do NOT attempt ad-hoc dependency fixes without explicit investigation and approval.

---

## 12. Datasets / Real Data Status

- **Primary Ingested Dataset:** 424 real documents (400 Enron + 24 synthetic),
  21,327 chunks stored, Case ID `8d8389d4-2534-452d-85b4-65efe5b8e1c3`.
- **Storage Migration Corpus:** 426 real documents accounted for in Supabase
  Storage (400 Enron + 24 synthetic + 2 legitimately split across cases).
  All 426 verified with matching SHA-256 hashes.
- **Raw Entity Mentions in DB:** Exactly **10,409** raw extracted entity mentions
  across 430 non-excluded (`REVIEWED` / `FLAGGED`) documents in PostgreSQL
  `doc_metadata["entities"]`.
- **Knowledge Graph Live Data (current query verification):**
  - **4,727 total nodes** (437 document nodes, 4,290 canonical entity nodes).
  - Entity types: 1,780 person, 1,415 organization, 681 date, 223 location,
    180 money, 7 case_number, 4 court.
  - **9,884 live edges**.
  - C = 9.0 (centrality normalization cap).

---

## 13. Architecture / Decisions

- **Creator-Only Access Control:** Enforced via `case.created_by` and
  `document.uploaded_by` with admin override. Chosen because the database
  schema has no team/organization/tenant concept. Reused across all
  document, case, search, graph, and analytics endpoints.
- **Storage Abstraction:** Supabase Storage accessed via `StorageBackend`
  abstraction (`storage_service.py`). Documents are downloaded strictly
  through authenticated backend endpoints; no direct public bucket URLs.
- **Quota Handling:** `DocumentStatus.QUOTA_PAUSED` provides honest
  error handling. Smart-resume avoids re-running valid completed stages.
- **Batch Separation:** Batch 1 cleanup was strictly separated from logic/
  database changes.
- **CI Configuration:** `.github/workflows/ci.yml` retained as harmless
  future infrastructure.
- **apply_init_sql.py:** Confirmed empty and removed during cleanup.
- **Graph Centrality:** Weighted-degree centrality (`CentralityService`)
  computed over entity-entity edges (<10ms per-request), with fixed cap
  `C = 9.0` and global logarithmic normalization. Betweenness deferred.
- **Test Baseline Maintenance & Edge Reconciliation:** The stale hardcoded 6955
  edge assertion in `test_graph_edge_reconciliation.py` was resolved in Batch 2 /
  Task 2 by replacing it with a live, data-derived expectation. The root-cause defect
  in `test_security_audit.py` (global SQLite monkeypatch without teardown) was diagnosed
  and logged to Known Issues.
- **Real Storage Usage Metric:** `total_storage_bytes` was added to `/api/v1/analytics`,
  computed dynamically from `Document.file_size` (889,159 bytes across 430 non-excluded
  documents). `Document.file_size` is 100% populated and measured at upload time.
- **Dead Endpoint Deletion:** The dead `/api/v1/agents/analytics` endpoint (11 fabricated
  fields) and its unused frontend caller `fetchAgentAnalytics()` were permanently deleted.
- **Offline Benchmark Framing:** `AnalyticsPage.tsx` now explicitly frames evaluation
  metrics under an "Offline Evaluation Benchmarks" section with dynamic `N=` records
  and backend explanations, eliminating misleading "Live Benchmark" labels.
- **Analytics Definition Honesty:** Raw entity mentions (`total_entities_detected`)
  are strictly separated from canonical graph nodes. Unmeasured metrics
  (`avg_review_time_seconds`, `avg_confidence_score`) strictly return `None`/`null`
  rather than substituting benchmark latency or fake composite formulas.
- **LLMClient Extraction & Gemini Test Harness:** Centralized `LLMClient.generate_text()`
  interface in `backend/app/agents/gemini_client.py` handles input validation before network
  dispatch, quota error detection (`is_quota_error()`), and automatic failover from
  `GOOGLE_API_KEY` to `GOOGLE_API_KEY_2`. The live Gemini test in `backend/tests/test_gemini_client.py`
  is guarded by `@pytest.mark.skipif(not os.getenv("RUN_LIVE_GEMINI_TESTS"), ...)` to prevent
  accidental quota consumption during routine regression runs. The default targeted test
  `test_llm_client_failover_and_validation` performs zero live network calls. Production agent
  retry loops in `summarization.py` and `classification.py` confirm 3 retry attempts with a
  15-second wait on rate-limit retries.
- **Case Summary Persistence Scaffolding (Batch 1):** `case_summaries` table with explicit UUID foreign key to `cases.id` (ON DELETE CASCADE, NOT NULL), strict lowercase status enum constraint (`generating`, `complete`, `failed`, `quota_paused`), `source_data_hash` for stale detection, and latest-ordered repository query ordering by `created_at.desc()`.
- **Case-Level Summary Generation Architecture (Batch 2):** Synthesizes executive legal summary strictly from pre-computed structured document metadata (`doc_metadata`), eliminating raw document text re-reading and redundant document-level agent execution. Employs Tier 1 minimal overview across all 423 case documents, Tier 2 expansion for privileged/high-risk/flagged subsets, deterministic timeline extraction with core operational activity window, and narrow top-N entity centrality reusing verified `CentralityService` and `EdgeWeightingService` formulas directly without full-graph assembly. Single LLM call execution under a hard ceiling of 5 (target $\le 3$). State machine supports 6 verified states with concurrency protection (HTTP 409) and case-scoped security authorization (`get_case_scoped_document_ids`).

---

## 14. Next Exact Task

**CASE-LEVEL SUMMARY + GROUNDED RAG Q&A — BATCH 3: GROUNDED RAG Q&A**

Status: **NEXT / NOT STARTED**

Scope:
- Implement grounded, case-scoped question answering over case chunks.
- Architecture:
  1. Question input $\rightarrow$ user authorization & case scoping.
  2. Retrieve case-scoped chunks (`top_k`).
  3. Zero-chunk shortcut: if no chunks found, return an honest "not found / insufficient evidence" response without calling the LLM.
  4. Grounded prompt assembly with citation guidelines.
  5. Call `LLMClient.generate_text()`.
  6. Deterministic cited-chunk existence validation gate.
  7. Token-overlap grounding verification gate.
  8. Return answer with citations or suppression/grounding warning.
- Verification requirements:
  - Stateless single-turn Q&A.
  - Zero out-of-case hallucinated content.
  - Adversarial "not in case" rejection test using real evidence.
  - Endpoint-specific access authorization tests.
  - Quota-exhaustion handling.
- Implementation: 0 lines implemented, 0 endpoints created.

---

## 15. Verification Rules / Standing Hard Constraints

(Preserved from MASTER_CONTEXT.md Section 15 — apply to ALL future work)

1. No mocks, no fabricated/synthetic data presented as real, no silent
   fallbacks. Always verify with real output before accepting "done."
2. Ground-truth purity — never let an AI system generate its own
   evaluation labels.
3. Verification scripts go in `scratch/`, run via real file execution,
   never inline `python -c` through PowerShell.
4. Self-skeptical review required at the end of every task — report
   what could still be fake or wrong, flag other issues found even if
   out of scope. (This session's two Step 3 remediation rounds, and the
   Step 2 ceiling re-audit, are working examples of this rule in
   practice — a first-round contamination issue and a reporting
   transcription error were both caught and corrected via this
   standard, not accepted at face value.)
5. Always back up before destructive operations, with shown evidence.
6. Prefer honest pending/null states over fabricated placeholder data.
7. Every "completed"/"verified" claim needs independent, shown
   evidence — real logs, real query results, real screenshots.
8. Keep the written report honestly aligned with actual system state —
   the report rewrite (Section 14) may now proceed, since all three
   Knowledge Graph steps are genuinely done and verified, not merely
   claimed.
9. Zero cost / free-tier only — no paid APIs, no paid infrastructure.

---

## CURRENT SESSION / HANDOFF STATUS

### Workstream 8 — Rate Limiting + Password-Strength Hardening — CLOSED
**Status: VERIFIED COMPLETE / CLOSED** (All 3 implementation and verification tasks finished)

#### Summary of Workstream 8 Work Delivered
- **Task 1 (Auth Rate Limiting):** Attached shared SlowAPI limiter (`limiter`) to `/auth/login` and `/auth/register` in `backend/app/api/v1/auth.py` at 5 requests/min per IP. Verified 2/2 tests in `test_rate_limit.py` passing with HTTP 429 and cross-IP non-interference evidence.
- **Task 2 (AI & Pipeline Rate Limiting):** Applied `@limiter.limit()` across 12 AI and pipeline endpoints using the shared singleton limiter: `/documents/upload` (60/min), `/documents/upload-multiple` (10/min), `/documents/{id}/retry` (10/min), `/search` & `/search/semantic` (20/min), `/embed` (10/min), `/review` (5/min), `/clusters` (10/min), `/classify` (15/min), `/timeline` (15/min), `/entities` (20/min), `/relationships` (20/min), and `/ocr` (20/min). Verified 13/13 tests in `test_rate_limit_ai_endpoints.py` passing, including 20-request batch-safety and 60/61 boundary proofs. Quota tests (8/8) reconfirmed passing.
- **Task 3 (Password Policy Hardening):** Implemented 5-rule strong password policy on `RegisterRequest.password` in `backend/app/schemas/user.py` (minimum 8 chars, uppercase, lowercase, digit, special char) via Pydantic v2 `@field_validator`. Deliberately left `LoginRequest` unconstrained (non-retroactive for legacy users). Verified 8/8 tests in `test_password_policy.py` passing.

### Workstream 9 — LLMClient Extraction & Gemini Test Harness — CLOSED
**Status: VERIFIED COMPLETE / CLOSED** (LLMClient extraction, failover/retry handling, key rotation, quota-error detection, and opt-in test harness verified against production code and tests)

#### Summary of Workstream 9 Work Delivered
- **Live Gemini Test Guarded & Opt-In:** Live Gemini API test in `backend/tests/test_gemini_client.py` guarded with `@pytest.mark.skipif(not os.getenv("RUN_LIVE_GEMINI_TESTS"), reason="Live Gemini API test consumes limited daily quota; opt-in with RUN_LIVE_GEMINI_TESTS=1")`. Routine regression test runs perform zero live Gemini API calls and do not consume limited daily quota (500/day primary, 20/day fallback).
- **Targeted Default Test:** `pytest tests/test_gemini_client.py -v -rs` verified: 1 passed, 1 skipped (`test_llm_client_failover_and_validation` PASSED with ZERO live API calls, verifying input validation, empty prompt handling, `is_quota_error()`, and key rotation state; `test_generate_text_live` SKIPPED).
- **Explicit Live Gemini Verification:** Executed intentionally ONCE with `RUN_LIVE_GEMINI_TESTS=1`. Verified: 2 passed in 3.12s (`test_generate_text_live` PASSED, `test_llm_client_failover_and_validation` PASSED). Explicit opt-in live Gemini verification: PASSED (single live API invocation).
- **Production Agent Code Verification:** Confirmed retry loops in production agents `backend/app/agents/summarization.py` and `backend/app/agents/classification.py`: 3 retry attempts, 15-second wait on rate-limit retry (`await asyncio.sleep(15.0)`).

#### Official Verification Baseline (Prior to Case Summary Feature)
- **Backend Test Suite:** `python -m pytest -q --tb=short` $\rightarrow$ **119 passed, 2 failed, 3 skipped** (Time: 117.29s).

### Case-Level Summary + Grounded RAG Q&A — Batch 1: Persistence Scaffolding — CLOSED
**Status: VERIFIED COMPLETE / CLOSED**
- Implemented `case_summaries` table, model, Alembic migration `3508daeefd89_add_case_summaries_table.py` (with hardened lowercase status constraint), and `CaseSummaryRepository`.
- 14/14 tests passing in `tests/test_case_summary_crud.py`.

### Case-Level Summary + Grounded RAG Q&A — Batch 2: Case Summary Generation — CLOSED
**Status: VERIFIED COMPLETE / CLOSED**
- Implemented case-wide executive summary synthesis in `backend/app/services/case_intelligence_service.py` (`generate_case_summary()`).
- Structured pre-computed input strategy: Tier 1 minimal overview across all 423 documents; Tier 2 deep expansion for privileged, high/critical risk, and flagged evidentiary items; deterministic timeline aggregation distinguishing core operational activity from historical statutory citations.
- Narrow top-N entity centrality: directly queries case documents, reuses `CentralityService` (weighted degree) and `EdgeWeightingService` (calibrated weights, suppression rules) mathematical formulas directly, completely bypassing full-graph assembly and discarding. Reduced in-memory entity calculation latency from ~18.6s to **2.7084s – 2.8982s** (~70–85% reduction).
- Single LLM call architecture verified on the real 423-document case (`8d8389d4-2534-452d-85b4-65efe5b8e1c3`) under hard ceiling of 5 calls. Total end-to-end endpoint latency measured at **23.6708s** (LLM ~11.5s, narrow centrality ~2.8s, timeline ~1.2s, DB I/O & transport ~7.7s).
- 5 conceptual sections: `executive`, `legal`, `notable_provisions_and_findings` (replacing literal "Clause" concept), `evidence`, `key_people_and_relationships`.
- Verified 6-row state machine, 409 concurrency conflict guard, SlowAPI 2/minute rate limiting, and case-scoped document security authorization (`get_case_scoped_document_ids`).
- Quota-exhaustion behavior verified via mocked `QuotaExhaustedException` injection with **zero live production API quota consumed**.
- Internal system token mechanism completely removed; authorization enforced strictly at the route boundary.
- 14/14 tests passing in `tests/test_case_summary_generation.py`.

#### Final Official Verification Baseline (Post-Batch 2 Closure)
- **Backend Test Suite:** `python -m pytest tests/ -q --tb=short` $\rightarrow$ **145 passed, 2 failed, 3 skipped** (Time: 142–150s).
- **Three-Run Regression Investigation & Side-by-Side Proof:**
  - An earlier virtualenv run in task-1809 showed a changed failure composition: `test_clustering` and `test_reports_api`.
  - Thorough root-cause analysis proved `test_reports_api` failed solely due to an environmental artifact: an empty, orphan `docx/` directory in `backend\.venv\Lib\site-packages` (dated 08-09-2026). Under Python 3's PEP 420 namespace mechanism, `import docx` succeeded, falsely setting `DOCX_AVAILABLE = True`, which subsequently crashed on `docx.Document()` with `AttributeError`.
  - Under the project's standard system Python (`C:\Python313\python.exe`), `python-docx` is not installed; `import docx` raises `ModuleNotFoundError`, correctly setting `DOCX_AVAILABLE = False`, and `test_reports_api` passes 100% cleanly (23.99s).
  - Batch 2 did NOT introduce this failure. `test_classification` passing in that run was consistent with its known non-deterministic LLM behavior (`'Contracts'` vs `'Contract'`).
  - Three consecutive full regression runs under standard system Python confirmed the exact baseline failure composition is 100% stable:
    - **Run 1:** 145 passed, 2 failed (`test_classification`, `test_clustering`), 3 skipped (147.87s)
    - **Run 2:** 145 passed, 2 failed (`test_classification`, `test_clustering`), 3 skipped (150.38s)
    - **Run 3:** 145 passed, 2 failed (`test_classification`, `test_clustering`), 3 skipped (142.59s)
- **3 Skipped Tests:**
  1. `test_evaluation_analytics_integration.py::test_report_exports_format_encoding` (missing `reportlab`).
  2. `test_ocr_agent.py::test_ocr_pdf_processing` (missing test PDF).
  3. `test_gemini_client.py::test_generate_text_live` (opt-in test; `RUN_LIVE_GEMINI_TESTS` not set).
- **Frontend Production Build:** `npm run build` $\rightarrow$ **0 errors** (maintained clean).

---

## NEXT SESSION — START HERE

**Current Working System State:**
- The application is running on FastAPI (backend, port 8000) and Vite/React (frontend, port 5173) connected to PostgreSQL with pgvector and Supabase Storage.
- Multi-tenant data isolation, quota paused handling, and Knowledge Graph Steps 1–3 are fully intact.
- Case-Level Summary + Grounded RAG Q&A — Batch 1 (Persistence Scaffolding) is **100% CLOSED / VERIFIED** (14/14 tests).
- Case-Level Summary + Grounded RAG Q&A — Batch 2 (Case Summary Generation) is **100% CLOSED / VERIFIED** (14/14 tests; real 423-doc case generation verified, 23.7s end-to-end latency, 1 LLM call).
- Official baseline stands at **145 passed, 2 failed, 3 skipped** with verified stable failure composition.

**Important Files for Context:**
- `backend/app/models/case_summary.py` — `CaseSummary` database model.
- `backend/app/repositories/case_summary_repository.py` — Atomic updates and DESC-ordered queries for summaries.
- `backend/app/services/case_intelligence_service.py` — Tiered input aggregation, deterministic timeline, narrow entity centrality, and summary synthesis.
- `backend/app/api/v1/case_summaries.py` — Summary generation and retrieval endpoints.
- `backend/tests/test_case_summary_crud.py` — Batch 1 persistence tests (14 tests).
- `backend/tests/test_case_summary_generation.py` — Batch 2 summary generation, state machine, security, rate limit, and real case tests (14 tests).
- `CURRENT_STATUS.md` & `MASTER_CONTEXT.md` — Project sources of truth.

**Exact Next Action:**
- Proceed to **Case-Level Summary + Grounded RAG Q&A — Batch 3: Grounded RAG Q&A** (Status: **NEXT / NOT STARTED**).
- Planned architecture:
  1. User authentication & case-scoped authorization check.
  2. Retrieve case-scoped document chunks (`top_k`).
  3. Zero-chunk shortcut: return honest "not found / insufficient evidence" response without calling LLM if zero relevant chunks found.
  4. Build grounded prompt containing chunk evidence and citation directives.
  5. Call `LLMClient.generate_text()`.
  6. Deterministic cited-chunk existence validation gate.
  7. Token-overlap grounding verification gate.
  8. Return answer with chunk citations OR suppression/warning.
- **Strict Constraint:** 0 lines of Batch 3 implemented so far; implementation will begin upon scoping and instruction.
