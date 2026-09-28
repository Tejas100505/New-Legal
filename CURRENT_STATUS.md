# CURRENT_STATUS.md — Agentic AI for E-Discovery & Legal Review

*Companion to MASTER_CONTEXT.md. This file tracks exact current position,
what's done vs. not, and the precise next action. Read MASTER_CONTEXT.md
first for full background — this file assumes that context.*

*Last updated: after completing and independently verifying fourteen major
workstreams: (1) Critical Cross-Tenant Data Leak Fix, (2) Quota-Exhaustion
Honest Handling (QUOTA_PAUSED), (3) File Storage Migration to Supabase
Storage, (4) Self-Registration + UX Improvements, (5) Supabase Keep-Alive
Documentation (activation pending), (6) Batch 1 Session-Debris Cleanup
(CLOSED / APPROVED), (7) Batch 2 — Honest Analytics Metrics & UI
Remediation (Tasks 1–6 genuinely EXECUTED, VERIFIED, and CLOSED),
(8) Rate Limiting + Password-Strength Hardening (Tasks 1–3 genuinely
EXECUTED, VERIFIED, and CLOSED), (9) LLMClient Extraction & Test Harness
(CLOSED / VERIFIED), (10) Case-Level Summary Batch 1: Persistence Scaffolding
(CLOSED / VERIFIED), (11) Case-Level Summary Batch 2: Summary Generation
(CLOSED / VERIFIED), (12) Grounded RAG Q&A Batch 3 (CLOSED / VERIFIED),
(13) Batch 4: Frontend / UX Remediation & Legal Workflow Integration
(Sub-batches 4a–4g genuinely EXECUTED, VERIFIED, and CLOSED), and
(14) Real Case-Scoped & Document-Scoped Pipeline Execution Status Endpoint
(backed by status_history and Document status, hardcoded case_001 eliminated,
verified with 7 new tests, 197 passed backend baseline).*

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
- Ten follow-up workstreams completed and verified:
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
  12. **Case-Level Summary + Grounded RAG Q&A — Batch 3: Grounded RAG Q&A** — ✅ VERIFIED COMPLETE / CLOSED
      (Stateless single-turn grounded Q&A endpoint POST /api/v1/cases/{case_id}/ask; BM25-union-cosine candidate generation
      with min_chunk_chars=50, address-list filter, and theta=None pre-LLM scalar floor; single Gemini generation call;
      deterministic Gate A citation existence verification; deterministic Gate B lexical grounding verification with
      token overlap tau=0.55 and normalized numeric/date containment; SlowAPI 10/minute rate limiting; creator-only + admin
      override authorization preventing case existence leakage; 20/20 stubbed tests passed with 0 live API calls; Gate B 8/8
      smoke test passed; 165 passed full regression with 0 regressions; real 423-doc Enron live verification passed across
      3 positive, 2 absent, and 2 near-domain stress tests with 7/8 live LLM calls compliant; live stress tests demonstrated
      LLM honesty + Gate A holding with 0 citations; Gate B suppression verified offline via unit and smoke tests).
  13. **Batch 4: Frontend / UX Remediation & Legal Workflow Integration** — ✅ VERIFIED COMPLETE / CLOSED
      (Sub-batches 4a–4g fully executed and verified:
      - 4a: Navigation shell restructuring (case-scoped sidebar, attorney workflow hierarchy, 6 legacy compatibility redirects).
      - 4b: Case workspace tabs layout & shell (Overview, Evidence, Review, Findings, Relationships, Timeline, Report, Ask).
      - 4c: Case Intelligence Summary UI (5 structured sections, generation trigger, live hash staleness detection).
      - 4d: Grounded Case Q&A UI (interactive query box, cited chunk cards `[C1]`, Gate A/B status badges, suppression warning banner, `insufficient_evidence` empty state).
      - 4e: Findings tab (verified 29 findings: 19 privilege, 7 risk, 3 escalation; substantive flag extraction; evidence traceability deep links to `/documents/{id}`).
      - 4f: Dashboard rewrite (executive review command center, urgent review queue, active matters, attention banner, live audit log fallback; pipeline visualizers and technical grids relocated to Settings) + Settings expansion (`/settings/analytics` honest 11-metric grid with provenance notes, `/settings/agents` 18-agent architectural reference, `/settings/system` live health telemetry).
      - 4g: Cleanup & polish (dead mock & duplicate file removal: `mockData.ts`, `mockAnalytics.ts`, `Dashboard.tsx`, `CaseList.tsx`, `Header.tsx`, `AppLayout.tsx`, `Sidebar.tsx`; multi-file upload batching refactored to `POST /documents/upload-multiple` verified via network inspection; production build `0 errors`; oxlint `0 new warnings/errors`; backend tests matching 165/2/3 baseline)).
- **Official Test & Build Baseline:** Full backend test suite **165 passed, 2 failed,
  3 skipped** across 170 tests (in ~190s). The 2 failures are the documented baseline LLM non-deterministic variations
  (`tests/test_intelligence_layer.py::test_clustering` asserting cluster naming and
  `tests/test_review_pipeline.py::test_risk_analysis` asserting `'CRITICAL' == 'HIGH'` risk threshold; both verified
  passing in isolated reruns; `test_classification` verified consistently passing 3/3 times); 3 skipped tests
  (`test_report_exports_format_encoding` due to missing `reportlab`, `test_ocr_pdf_processing`
  due to missing test PDF, and `test_generate_text_live` because live Gemini execution is
  intentionally opt-in and `RUN_LIVE_GEMINI_TESTS` was not set). Frontend production build clean (**0 errors**).
- **Environment Hygiene Resolution:** The interpreter divergence between system Python and the local `.venv`
  caused by an orphan, empty `docx/` namespace package directory in `backend/.venv/Lib/site-packages` was resolved
  in Batch 4g by removing the empty directory. `import docx` now consistently raises `ImportError` across both environments
  when `python-docx` is not installed, setting `DOCX_AVAILABLE = False` and allowing `tests/test_reports_api.py` to pass 100% cleanly.
  Zero tracked backend source files were modified to achieve this fix.
- **Next Task:** Bug-fix follow-up (Section 9 Item 2) or Report Rewrite (Section 9 Item 5; Section 14). (Test-Account/Test-Case Cleanup is CLOSED / VERIFIED).

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

### Case-Level Summary + Grounded RAG Q&A — Batch 3: Grounded RAG Q&A — CLOSED
**Status: CLOSED / VERIFIED** (Stateless single-turn case-scoped grounded Q&A endpoint, BM25-union-cosine candidate generation, theta=None pre-LLM relevance floor justification, deterministic Gate A citation existence, deterministic Gate B lexical grounding, rate limiting, and case authorization verified on real 423-document case)
- **Pipeline Architecture & Grounding Strategy:**
  - `POST /api/v1/cases/{case_id}/ask`: Single-turn, stateless, case-scoped grounded Q&A.
  - Case-scoped retrieval: `retrieve_case_chunks_qa` queries only documents belonging to `case_id`.
  - Candidate generation: In-memory BM25 top-20 union pgvector cosine top-20, deduplicated, then reranked via hybrid scoring formula (0.4 cosine + 0.3 BM25 + 0.3 deterministic term overlap + 0.25 domain boost).
  - Pre-filtering: `min_chunk_chars=50` (eliminating low-signal noise without losing any calibration chunk) and address-list structural header fragment filtering.
  - Passthrough: Top-5 candidate chunks are labeled `[C1]`..`[Ck]` and inserted into the prompt with zero secondary filtering.
  - Single Gemini Generation Call: Explicit system instructions treating excerpt text as untrusted data with mandatory bracketed citation syntax (`[C1]`). Zero answer text generated without citations.
- **Pre-LLM Relevance Floor Investigation: Closed with theta = None:**
  - Full diagnostic trail documented and hashed at `backend/scratch/floor_decision_final.md` (SHA-256: `ca391365ca41e789c7187ff2ac3f4f247fd440e901fcf5a98ec47b3a6262bf85`).
  - Structural rationale: Per-pool BM25 max-normalization (`bm25/max(bm25)`) guarantees every candidate pool contains a chunk scoring 1.0 on BM25 component regardless of true relevance, and baseline cosine similarity sits at 0.50-0.57. Together these produce out-of-case top-1 hybrid scores of 0.54-0.67 unconditionally, overlapping legitimate in-case scores (0.44-0.78).
  - Decision: `theta = None` was selected because no defensible pre-LLM scalar relevance floor was established on this corpus/retrieval configuration. Selecting `theta = None` does not prove retrieval quality nor does it imply Gate B alone prevents false citations. Rather, quality control is provided across the full pipeline: case-scoped retrieval, grounded prompting, LLM insufficiency behavior, Gate A (citation existence), Gate B (lexical grounding), and mandatory human review.
- **Deterministic Post-Generation Verification Gates:**
  - **Gate A (Citation Existence):**
    - Parses all `[C1]`..`[Ck]` labels in raw LLM response.
    - If 0 citations found $\rightarrow$ fails Gate A, immediately resolves to `status="insufficient_evidence"`, `answer=None` (naturally handles honest model refusals).
    - If any citation label is unknown (e.g. `[C99]`) $\rightarrow$ fails Gate A, resolves to `status="suppressed"`, `answer=None`.
  - **Gate B (Lexical Grounding & Containment):**
    - Only runs if Gate A passes with $\ge 1$ valid citation.
    - Sentence segmentation: splits answer into individual sentences.
    - Content-token overlap: verifies per-sentence content token overlap against cited chunk texts $\ge \tau = 0.55$. Direct copy of 44 stopwords from `VerificationAgent`.
    - Numeric, date, ratio, and currency containment: exact normalized containment against cited chunk texts.
    - Ordinal suffix normalization: e.g. `15th` $\rightarrow$ `15`, catching ungrounded dates deterministically.
    - Any failing sentence triggers suppression of the entire answer (`status="suppressed"`, `answer=None`).
- **Security & Authorization Model (Batch 2 Exact Match):**
  - Creator-only + admin-override via `get_case_scoped_document_ids`.
  - Authorization check runs before existence check: an unauthorized non-admin user querying a nonexistent case receives HTTP 403 Forbidden ("Access denied to this case"), never leaking case existence via 404.
  - HTTP 404 is reserved for admin (or authorized) requests hitting nonexistent cases.
- **Rate Limiting & Safety:**
  - Attached to SlowAPI shared singleton limiter (`app.core.rate_limit.limiter`) with `@limiter.limit("10/minute")`.
  - Input validation: Pydantic `field_validator` rejects empty/whitespace strings with HTTP 422; max question length 1000 characters.
  - Quota exhaustion: `QuotaExhaustedException` caught and mapped to HTTP 503 Service Unavailable, 0 answer text leaked.
- **Verification & Test Results:**
  - **Unit & Integration Suite (`tests/test_case_qa.py`):** **20/20 PASSED** in 30.11s with **0 live Gemini API calls** (autouse `stub_embedding_agent` and `AsyncMock` for `LLMClient.generate_text`). Tests cover auth 401/403/404/200, cross-case isolation, candidate scoping, empty candidate handling, Gate A zero citations, Gate A unknown citation, Gate B low overlap, Gate B ungrounded number, Gate B grounded success, prompt injection defense, quota 503, general error 500, rate limit 10/min, input validation 422.
  - **Full Test Suite Regression:** **165 passed, 2 failed, 3 skipped** (identical 2 known baseline failures, +20 new tests, 0 regressions).
  - **Gate B Smoke Test (`backend/scratch/smoke_test_gateb.py`):** 8/8 hand-written test sentences matched expectation (SHA-256: `22833f5f1ce3e2062ef88ccfe21e40fb82b8cfe907bfa351e56ce94f884969c9`).
  - **Real-Data Initial Verification Script (`backend/scratch/verify_real_data_qa.py`):**
    - Target: Real 423-document Enron case `8d8389d4-2534-452d-85b4-65efe5b8e1c3`.
    - Positive questions (3/3): CALIB-IN-08 (`grounded`, cited 40 CFR 60.11 / 80%), CALIB-IN-03 (`grounded`, cited $9M marked-to-market profits), CALIB-IN-10 (`grounded`, cited WAPA hourly balanced schedule as of Oct 28th).
    - Adversarial questions (2/2): CALIB-OUT-06 NEAR-DOMAIN ABSENT (`insufficient_evidence`, 0 citations, answer=None), CALIB-OUT-08 CROSS-CASE (`insufficient_evidence`, 0 citations, answer=None).
    - Security checks (2/2): Stranger querying Enron case $\rightarrow$ 403 Forbidden; cross-case query $\rightarrow$ 403 Forbidden.
    - Initial Live LLM calls: 5 calls (SHA-256: `36457a2d19d2cd412602a43356fda60249a0f264496b432b6913fe7b2172cc4c`).
  - **Adversarial Stress Test (`backend/scratch/stress_test_theta_none.py`):**
    - Target: Real 423-document Enron case `8d8389d4-2534-452d-85b4-65efe5b8e1c3`.
    - Questions tested: CALIB-OUT-04 (Duke Energy / FERC EL01-88 fine) and CALIB-OUT-07 (Reliant Energy California emergency credit lines).
    - In both cases, retrieval surfaced topically-close chunks (mentioning "July 13 and 14", "July 2001", "Duke", "California ISO", "April 13, 2001"), but the LLM honestly declined to cite anything (*"Insufficient evidence in the case record to answer this question."*), resolving cleanly at Gate A to `insufficient_evidence`.
    - **Live Adversarial Verification vs Gate B Distinction:** Live adversarial verification demonstrated LLM-honesty + Gate A on two real near-domain-absent questions (CALIB-OUT-04 Duke Energy and CALIB-OUT-07 Reliant Energy). In both cases the LLM declined to cite evidence, so Gate A resolved the response as insufficient evidence and Gate B was not exercised live. Gate B's false-positive citation suppression mechanism was separately verified through the stubbed unit test (`test_qa_gate_b_unsupported_number_suppressed`) and the Gate B smoke test. Thus the live tests do not constitute a live demonstration of Gate B suppressing a successfully generated false citation.
    - Stress test live calls: 2 calls. Cumulative live verification calls across Batch 3: $5 + 2 = 7$ calls.
    - **Budget Compliance: 7/8 live LLM calls compliant ($\le 8$ ceiling strictly observed).**
    - Transcript saved to `backend/scratch/adversarial_stress_test_transcript.txt` (SHA-256: `c280c1bb2f1dc2e398e7214520622246e3bca400a509564a512f5456024c43dc`).
- **Known Limitations:**
  - *No Pre-LLM Scalar Relevance Cutoff (theta = None):* `theta = None` means there is no pre-LLM scalar relevance floor filtering chunks before prompt assembly. Quality control is provided across the full pipeline (case-scoped retrieval, grounded prompting, LLM insufficiency behavior, Gate A, Gate B, and human review).
  - *Lexical Grounding vs. Semantic Entailment:* Gate B implements deterministic lexical grounding (token overlap $\ge 0.55$) and numeric/date containment, not full semantic entailment or Natural Language Inference (NLI). It has known limitations around heavy paraphrasing and cannot detect semantic negation (e.g. adding "did not" to an otherwise faithful chunk sentence); documented limitation preserved and tested in smoke test case 8.
  - *Gate B Live Adversarial Boundary:* The live adversarial tests did not exercise a successful false citation through Gate B because the LLM honestly declined to cite evidence; Gate B's defense against false-positive citations is verified deterministically by stubbed unit tests and smoke tests, not by a live example.
  - *Corpus Ingestion Fragmentation:* Header and email address-list fragments in raw corpus chunks remain a known corpus/retrieval limitation, scoring deceptively high on lexical overlap without filtering; mitigated via regex heuristic `is_address_list_fragment` and `min_chunk_chars=50`.
  - *Shared BM25 Tokenization Fix:* Word-boundary regex tokenization (`\b\w+\b`) was fixed in `RetrievalAgent._execute` as a positive side-effect, ensuring consistent tokenization between candidate generation and hybrid reranking.
  - *Multi-Hop Synthesis:* Multi-hop questions requiring synthesis across $>5$ chunks or cross-document reasoning without common keywords are deferred to future offline batch reasoning pipelines.

---

### Batch 4 — Frontend / UX Remediation & Legal Workflow Integration — CLOSED
**Status: VERIFIED / CLOSED**
**Batch 4a–4g: VERIFIED / CLOSED** (All seven sub-batches implemented, tested, and independently verified against repository evidence)

#### Summary of Batch 4 Work Delivered:
- **Architectural Shift:** Reorganized the frontend from an internal AI/pipeline developer perspective into an attorney-first Case Workspace hierarchy (`/cases/{id}/*`), grounding all analysis in legal matter context.
- **Sub-batch 4a — Navigation Shell & Routing Infrastructure (CLOSED / VERIFIED):**
  - Case-scoped sidebar navigation (`Sidebar.tsx`) presenting active matter context, matter switching, and attorney workflow links.
  - Six legacy compatibility redirects in `App.tsx`: `/investigation` → `/cases`, `/knowledge-graph` → `/cases`, `/timeline` → `/cases`, `/ai-review` → `/cases`, `/analytics` → `/settings/analytics`, `/agents` → `/settings/agents`.
- **Sub-batch 4b — Case Workspace Shell & Context (CLOSED / VERIFIED):**
  - `CaseWorkspaceLayout.tsx` and `CaseWorkspaceContext.tsx` providing case-level state, real-time metrics, matter switching, and tab routing across 8 investigation tabs.
- **Sub-batch 4c — Case Intelligence Summaries UI (CLOSED / VERIFIED):**
  - `OverviewTab.tsx` integrating 5 structured legal sections from Batch 2 (`executive`, `legal`, `notable_provisions_and_findings`, `evidence`, `key_people_and_relationships`).
  - Manual generation trigger (`POST /generate`), loading states, live hash staleness detection.
- **Sub-batch 4d — Grounded Case Q&A UI (CLOSED / VERIFIED):**
  - `AskTab.tsx` integrating grounded RAG endpoint (`POST /ask`) from Batch 3.
  - Interactive query box with suggested prompts; cited chunk cards `[C1]`..`[Ck]`; Gate A/B status badges; suppression warning banner; `insufficient_evidence` empty state.
- **Sub-batch 4e — Findings Tab & Evidence Traceability (CLOSED / VERIFIED):**
  - `FindingsTab.tsx` surfacing 29 verified findings (19 privilege, 7 risk, 3 escalation).
  - Evidence traceability deep links to `/documents/{id}`.
- **Sub-batch 4f — Executive Dashboard Overhaul & Settings Expansion (CLOSED / VERIFIED):**
  - `DashboardPage.tsx` redesigned as executive review command center: Urgent Review Queue, Active Matters grid, Attention Needed banner, live audit log fallback.
  - Technical pipeline visualizers relocated to Settings sub-views:
    - `/settings/analytics`: Honest 11-metric grid with offline-benchmark provenance notes.
    - `/settings/agents`: 18-agent architectural reference and execution order.
    - `/settings/system`: Live PostgreSQL and Redis infrastructure telemetry.
- **Sub-batch 4g — Cleanup, Polish & Upload Batching (CLOSED / VERIFIED):**
  - **Dead Code Pruning:** Confirmed 0 imports and deleted 7 dead files (1,305 lines removed): `mockData.ts`, `mockAnalytics.ts`, `Dashboard.tsx` (scaffold duplicate), `CaseList.tsx` (scaffold duplicate), `Header.tsx` (dead layout copy), `AppLayout.tsx`, `Sidebar.tsx` (dead layout scaffolds).
  - **Retained Files:** `pages/NotFound.tsx` (active 404 route in `App.tsx`), `components/organisms/Header.tsx` (canonical active header in `DashboardLayout.tsx`).
  - **Upload Batching Refactor (Known Issue 14 Resolved):** Refactored `DocumentsPage.tsx` multi-file upload to dispatch to `POST /api/v1/documents/upload-multiple` instead of sequential per-file `POST /documents/upload`. Preserved single-file fallback and progress tracking.
  - **Runtime Network Verification:** Automated Puppeteer interception verified 1 HTTP request to `/documents/upload-multiple` and 0 to `/documents/upload` when uploading 2 files.
  - **Production Build:** `npm run build` (`tsc -b && vite build`) → **0 errors** (4.29s).
  - **Lint:** `npm run lint` (`oxlint`) → **0 new errors, 0 new warnings** (maintained baseline).
  - **Backend Test Suite:** **165 passed, 2 failed, 3 skipped** (170 tests). Exact match to post-Batch 3 baseline (0 regressions). The 2 failures are documented LLM non-deterministic variations (`test_clustering` cluster naming, `test_risk_analysis` risk threshold `CRITICAL` vs `HIGH`; both verified passing in isolated reruns; `test_classification` verified consistently passing 3/3 times).
  - **No Backend Source Modifications:** Zero tracked backend source files were modified for Batch 4g. The only environment-level cleanup was removing an orphan empty `docx/` namespace package directory from `.venv/Lib/site-packages/` (untracked).
  - **Targeted Non-Regression Spot-Checks:** Dashboard renders cleanly, all 8 workspace tabs functional, all 6 compatibility redirects functional, 0 console errors.
  - **Git State:** All file deletions unstaged (`git reset HEAD`) to preserve uniform unstaged working tree convention.

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

- **Architecture:** Case-first legal investigation workspace (`/cases/{id}/*`) with case-scoped sidebar navigation (`Sidebar.tsx`) and 6 compatibility redirects (`/investigation` → `/cases`, `/knowledge-graph` → `/cases`, `/timeline` → `/cases`, `/ai-review` → `/cases`, `/analytics` → `/settings/analytics`, `/agents` → `/settings/agents`).
- **Case Workspace (`CaseWorkspaceLayout.tsx`, `CaseWorkspaceContext.tsx`):** Unifies 8 investigation tabs under live matter state:
  - `OverviewTab.tsx`: 5 structured legal sections (Batch 2), manual generation trigger, live hash staleness detection.
  - `EvidenceTab.tsx`: Case-scoped document repository and batch upload handler (`POST /api/v1/documents/upload-multiple`).
  - `ReviewTab.tsx`: Priority-ranked human-in-the-loop review queue for privileged/risk documents.
  - `FindingsTab.tsx`: 29 verified matter findings (19 privilege, 7 risk, 3 escalation) with deep links to document viewer (`/documents/{id}`).
  - `RelationshipsTab.tsx`: Cytoscape Knowledge Graph with centrality-scaled node sizing (`CustomNode.tsx`, `[0.05, 1.0]`) and edge-weight filtering.
  - `TimelineTab.tsx`: Chronological matter timeline with source document provenance.
  - `ReportTab.tsx`: Multi-format report exports (JSON, Markdown, CSV, PDF, DOCX) and audit log preview.
  - `AskTab.tsx`: Grounded Case Q&A interface (Batch 3) with query box, cited chunk cards `[C1]`, Gate A/B status badges, suppression warning banner, and `insufficient_evidence` empty state.
- **Executive Dashboard (`DashboardPage.tsx`):** Redesigned as an executive review command center: Urgent Review Queue (top 5 prioritized unconfirmed items), Active Matters grid with direct workspace entry points, Attention Needed banner, and live audit log fallback.
- **Settings Sub-Views (`/settings/*`):** Technical internals relocated to dedicated administrative tabs:
  - `/settings/analytics`: Honest 11-metric analytics grid with explicit offline-benchmark provenance notes.
  - `/settings/agents`: 18-agent architectural reference and execution order.
  - `/settings/system`: Live PostgreSQL and Redis infrastructure telemetry.
- **Upload Batching (Known Issue 14 Resolved):** Refactored `DocumentsPage.tsx` to dispatch multi-file uploads via `POST /api/v1/documents/upload-multiple` (10/min limit) instead of sequential per-file `POST /documents/upload` loops; verified via runtime network interception.
- **Password Policy Alignment (Known Issue 15 Resolved):** `LoginPage.tsx` client-side validation schema and hint text match the backend 5-rule strong password policy.
- **Dead Code Cleanup:** Removed 7 unreferenced files (1,305 lines pruned): `mockData.ts`, `mockAnalytics.ts`, `Dashboard.tsx`, `CaseList.tsx`, `Header.tsx`, `AppLayout.tsx`, `Sidebar.tsx`. Retained active files `pages/NotFound.tsx` and `components/organisms/Header.tsx`.
- **Production Build:** `npm run build` (`tsc -b && vite build`) passed with **0 errors**.
- **Lint:** `npm run lint` (`oxlint`) passed with **0 new warnings, 0 new errors**.

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

- **Dashboard "AI Agents" panel per-agent stats re-fix** — **CLOSED / VERIFIED (2026-09-27)**:
  - **Ground Truth Finding:** Real per-agent execution data (latency/duration, confidence score, and execution timestamps) exists in PostgreSQL `audit_logs` (`resource_type == 'agent'`), dynamically logged during document processing runs by `record_agent_execution` in `backend/app/services/orchestrator.py`.
  - **Captured Live Output Evidence:** Authenticated query against `GET /api/v1/agents` confirmed all 18 canonical agents return distinct, non-mock values across the board (OCR: 4199ms / 100.0%; Ingestion: 164ms / 100.0%; Classification: 1808ms / 99.0%; Chunking: 2ms / 100.0%; Embedding: 3159ms / 100.0%; Retrieval: 4754ms / 95.0%; Entity Extraction: 235ms / 95.0%; Relationship: 2ms / 94.0%; Timeline: 1905ms / 90.0%; Summarization: 3091ms / 81.2%; Privilege: 8ms / 98.0%; Risk: 1300ms / 90.0%; PII: 3ms / 98.0%; Review: 1ms / 95.0%; Verification: 1ms / 90.0%; Clustering: 2016ms / 90.0%; Report: 1ms / 95.0%; Triage: 1ms / 82.0%).
  - **Standing Rule 6 Compliance:** Per-agent token consumption is uninstrumented in `AuditLog` (recorded as 0 in DB) and is honestly rendered as "—" / "N/A (uninstrumented)" across the UI, eliminating all fake/simulated numbers.
  - **Frontend Wiring:** `SettingsAgentsPage.tsx` (the canonical route post-Batch-4f) wired to `GET /api/v1/agents` via React Query; displays live latency, confidence, status badges, and execution timestamps for each agent; notice banner honestly documents telemetry provenance.
  - **De-simulation:** Removed residual `Math.random()` simulation in `AgentDetailModal.tsx`.
  - **Targeted Regression Suite:** `backend/tests/test_agents_api.py` added with 2 tests verifying 18 agents, distinct metrics (OCR 4199ms vs Chunking 12ms), honest idle state for unrun agents, and single-agent status endpoints; 2/2 passed. Frontend build clean (`tsc -b && vite build`, 0 errors).
  - **Disguised-Mock Confidence Defect Correction & Remediation (2026-09-27):**
    - **Defect Discovery:** Source-level tracing following the initial verification revealed that while `duration_ms` was genuinely real and dynamically timed, 10 of 15 agent-execution logging sites in `orchestrator.py` had silently written hardcoded per-agent-type constants (e.g. 100.0, 95.0, 94.0, 92.0, 90.0, 80.0) as `confidence` rather than genuine per-execution values. Additionally, `triage` logged `priority_score` under the label `confidence`.
    - **Remediation Standard:** The verification standard for confidence is **"genuine per-execution source, honestly traced from real agent output to API"**, NOT mere numerical variance across runs. Numerical variation is not a test for authenticity (consistent inputs may produce identical outputs, whereas fabricated random formulas would vary while remaining completely fake). No new scoring methodology or formula was invented for any agent.
    - **Classification & Fixes Applied:**
      - **Category A (Real per-execution confidence exists in model):**
        - `timeline`: Wires `tl_result.confidence_score * 100` (`TimelineOutput.confidence_score` computed per-execution from date specificity, verbs, context in `timeline.py:240`).
        - `risk`: Wires `risk_result.confidence_score * 100` (`RiskOutput.confidence_score` computed per-execution from risk assessment & keyword density in `risk.py:285, 318`).
      - **Category B (Deterministic operations or static defaults with no defensible per-execution confidence concept):**
        - Pass `None` in `AuditLog.details["confidence"]`, returned as `null` by `GET /api/v1/agents` and rendered as honest `"N/A"` across `SettingsAgentsPage.tsx`, `AgentCard.tsx`, and `AgentDetailModal.tsx` (reusing the exact uninstrumented token pattern).
        - Applied to: `ocr (text-only)` (raw text bypasses OCR engine), `chunking` (deterministic text splitting), `embedding` (deterministic vector generation), `entity_extraction` (regex/rules/NER default static constant 0.95), `relationship_extraction`/`relationship`/`knowledge_graph` (networkx graph construction default static constant 0.85), `legal_review`/`review` (rule-based aggregation default static constant 0.87).
      - **Semantic Mismatch Separation (Triage):**
        - `triage_result.priority_score` (0–100 review priority index) was decoupled from confidence. Orchestrator now records `priority_score` in its own field (`AuditLog.details["priority_score"]`), passing `confidence=None`. `AgentStatusResponse` surfaces `priority_score` separately.
      - **Untouched Sites (4 already-real sites preserved):**
        - `ocr (file present)` (`ocr_result.confidence_score * 100`), `classification` (`class_result.confidence_score * 100`), `summarization` (`sum_result.confidence_score * 100`), and `privilege` (`priv_result.confidence_score * 100`) preserved as verified genuine.
    - **Targeted Test Expansion:** `backend/tests/test_agents_api.py` expanded with `test_confidence_provenance_category_a_and_b` verifying Category A dynamic wiring with varying values, Category B honest `None`/`null` passthrough, and untouched agent verification. Isolated fixture isolation hardened to ensure zero cross-suite database pollution. Frontend production build verified clean (0 errors).
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

- **Batch 4: Frontend / UX Remediation & Legal Workflow Integration — VERIFIED COMPLETE / CLOSED**
  (Sub-batches 4a–4g fully implemented, tested, and verified; see Section 2 and Section 5).
1. **Test-account/test-case cleanup** — **CLOSED / VERIFIED (2026-09-27)**.
   Scope executed as approved: 29 test accounts, 492 test cases (491 automated + 1 "Project Vulcan"),
   333 documents, 114 chunks, and 214 summaries removed; `user@example.com` promoted to ADMIN.
   One incident occurred (scope violation: document `8539d172` and its 18 chunks in excluded Case `83969a81`
   were deleted due to a missing case-exclusion filter in Step 3). Document row was fully restored from backup
   via `backend/scratch/restore_incident_document.py` (`uploaded_by` re-attributed to `user@example.com`,
   `status=flagged`), with 18 original chunks confirmed permanently unrecoverable and left at 0 per Rule 6.
   Following a self-reported restoration report containing fabricated values (caught under Standing Rule 7),
   an independent, output-anchored re-verification (`backend/scratch/independent_reverify.py`) executed 4 raw
   SQL queries and verified all 4 live database values MATCH expected ground truth (primary case `8d8389d4`,
   admin user `f20699fb`, restored document fields/status/checksum, and case `685b2574` chunk count = 0).
   Task is formally CLOSED / VERIFIED.
2. **Fix cleanup/bulk-deletion script exclusion-filter bug** — **CLOSED / VERIFIED (2026-09-27)**.
   Codebase inspection confirmed that no reusable bulk-deletion logic exists in the production application codebase (`backend/app/repositories/`, `backend/app/services/`, `backend/app/api/v1/` all only implement single-resource deletion by primary key ID). The bug pattern exclusively existed in the one-off scratch cleanup script. Fix delivered across three components:
   (a) Corrected historical cleanup script `backend/scratch/execute_test_cleanup.py` Step 3 query to explicitly apply `.where(~Document.case_id.in_(EXCLUDED_CASE_IDS | {PRIMARY_CASE_ID}))`, updating document targets from 8 to 7 (332 total).
   (b) Created reusable safety helper module `backend/scratch/cleanup_safety.py` providing `assert_no_protected_case_overlap()`, `apply_case_exclusion_guard()`, and `build_safe_document_user_deletion_query()` with standard protected case definitions (`PRIMARY_CASE_ID`, `PROTECTED_CASE_IDS`, `ALL_PROTECTED_CASE_IDS`).
   (c) Added mandatory convention documentation in `backend/scratch/README.md` and verified with 5 unit tests in `backend/tests/test_cleanup_safety.py` (5/5 passed). (See Section 11 Item 19 for full incident detail.)
3. **JWT logout / token blocklist mechanism** — **CLOSED / VERIFIED (2026-09-27)**.
   Architectural review selected Option A: per-user `token_version` column on `users` with direct scalar DB lookup in `get_current_user` (`SELECT token_version, is_active FROM users WHERE id = :sub`), strict HTTP 401 on missing/inactive/mismatched tokens (no test-environment bypass).
   - Migration `backend/alembic/versions/e8f9a0b1c2d3_add_token_version_to_users.py` added `token_version INTEGER NOT NULL DEFAULT 0` to `users` table in PostgreSQL.
   - `backend/app/models/user.py`: Added `token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)`.
   - `backend/app/auth/dependencies.py`: Updated `TokenPayload` with `token_version: int = 0`, embedded version into `create_access_token` and `decode_token`, and hardened `get_current_user` to validate `token_version` against the live DB row.
   - `backend/app/api/v1/auth.py`: Updated `POST /api/v1/auth/login` to embed live `token_version` and hardened `POST /api/v1/auth/logout` to atomically increment `token_version + 1` with `@limiter.limit("10/minute")`.
   - Verified with 7 comprehensive unit tests in `backend/tests/test_jwt_logout.py` (7/7 passed) and verified full test suite regression (178 passed, 1 pre-existing flaky LLM test failed, 3 skipped; 0 unexplained regressions).
4. **Document status audit trail** — **CLOSED / VERIFIED (2026-09-27)**.
   Added a complete status transition audit trail via new `status_history` table:
   - Migration `backend/alembic/versions/b2c3d4e5f6a7_add_status_history_table.py` created `status_history` (`id` UUID PK, `document_id` UUID FK -> `documents.id` ON DELETE CASCADE, `old_status` VARCHAR(50) nullable, `new_status` VARCHAR(50) NOT NULL, `changed_at` TIMESTAMPTZ default now(), `changed_by` UUID FK -> `users.id` nullable, `reason` TEXT nullable, `created_at`, `updated_at`).
   - Created ORM model `backend/app/models/status_history.py` and linked `status_history` relationship on `Document` (`backend/app/models/document.py`).
   - Created schema `StatusHistoryResponse` in `backend/app/schemas/document.py`.
   - Created atomic helper `record_status_transition()` in `backend/app/services/status_history_service.py` ensuring document status mutations and history records commit together atomically.
   - Refactored all direct status-assignment sites across `backend/app/services/orchestrator.py` (8 pipeline stages), `backend/app/api/v1/documents.py` (PATCH, override, retry), `backend/app/api/v1/review.py` (review pipeline), `backend/app/services/document_service.py` (initial upload), and `backend/app/repositories/document_repository.py` to route through the unified helper.
   - Added read endpoint `GET /api/v1/documents/{document_id}/status-history` with creator-only + admin-override authorization.
   - Verified with 5 unit/integration tests in `backend/tests/test_status_history.py` (5/5 passed) and full regression suite verification (182 passed, 2 documented flaky LLM tests, 3 skipped).
   - **Documented Limitation:** Forward-only recording from deployment forward; past transitions prior to migration are unrecorded (not backfilled or estimated per Standing Rules).
5. **Report Rewrite** (reframe around case-investigation, pipeline+orchestrator,
   real graph, diagram reconciliation; unblocked, but preceded by security/hardening).
6. **Existing lower-priority issues** (graph latency ~9.68s — CLOSED/VERIFIED 2026-09-28, OCR mock fallback strings — CLOSED/VERIFIED 2026-09-28, Dashboard AI Agents panel verification — CLOSED/VERIFIED 2026-09-27, cross-page entity linking, legacy Lotus Notes strings).

---

## 10. Currently In Progress

- **Batch 4 (Frontend / UX Remediation & Legal Workflow Integration) is VERIFIED COMPLETE / CLOSED (Sub-batches 4a–4g).**
- Case-Level Summary + Grounded RAG Q&A — Batch 1 (Persistence Scaffolding) is **CLOSED / VERIFIED**.
- Case-Level Summary + Grounded RAG Q&A — Batch 2 (Case Summary Generation) is **CLOSED / VERIFIED**.
- Case-Level Summary + Grounded RAG Q&A — Batch 3 (Grounded RAG Q&A) is **CLOSED / VERIFIED**.
- Workstream 8 (Rate Limiting + Password-Strength Hardening) is **VERIFIED COMPLETE / CLOSED**.
- Workstream 9 (LLMClient Extraction & Gemini Test Harness) is **VERIFIED COMPLETE / CLOSED**.
- **Test-Account / Test-Case Cleanup** is **CLOSED / VERIFIED** (Section 9 Item 1; Section 11 Items 7, 19; Section 14). Scope executed as approved, incident document restored, and independent re-verification (`backend/scratch/independent_reverify.py`) confirmed all 4 live facts match expected ground truth. Follow-up exclusion-filter fix (Section 9 Item 2) and document re-ingestion decision remain open.
- **Currently Active Task:** Awaiting owner priority selection between Section 9 Item 2 (Fix exclusion-filter bug) and Section 9 Item 5 (Report Rewrite).

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
4. **JWT Logout:** **RESOLVED / CLOSED (2026-09-27)**. Logout immediately and completely invalidates all issued JWTs for the user prior to their natural 60-minute expiry via atomic per-user `token_version` increment in the `users` table and live DB scalar verification in `get_current_user`. Strict HTTP 401 enforced across all environments with zero test bypasses. Verified with 7 comprehensive unit tests in `backend/tests/test_jwt_logout.py` and full regression suite verification.
5. **Hardcoded Case Name:** `"California Energy Market Practices Inquiry"` appears in 5
   frontend locations as fallback/display text.
6. **Document Status Audit Trail:** **RESOLVED / CLOSED (2026-09-27)**. Historical transition gap resolved by introducing the `status_history` table (migration `b2c3d4e5f6a7`), the atomic `record_status_transition` helper across all pipeline and API endpoints, and the read endpoint `GET /api/v1/documents/{document_id}/status-history`. Explicit limitation: starts recording from deployment forward; no backfill of pre-deployment status history (data does not exist and was not fabricated per Standing Rules). Verified with 5 unit tests in `backend/tests/test_status_history.py` (5/5 passed) and full regression suite verification.
7. **Test-Account / Test-Case Cleanup:** **CLOSED / VERIFIED WITH DOCUMENTED INCIDENT & LIMITATION (2026-09-27).**
   Dry-run completed (`backend/scratch/dry_run_test_cleanup.py`), 4 ambiguities owner-approved, destructive cleanup executed (`backend/scratch/execute_test_cleanup.py`). Successfully removed 29 test accounts (including admin accounts, with prior promotion of `user@example.com` to ADMIN), 492 test cases (491 automated test-fixture + 1 "Project Vulcan"), 333 documents, 114 document chunks, and 214 case summaries. Two cases explicitly excluded per owner approval: `685b2574` (OCR Failure Verification Matter) and `83969a81` (Memory Profiling Case). One scope violation occurred: document `8539d172` from excluded case `83969a81` was incorrectly deleted by the Step 3 query due to a missing case-exclusion filter (see Item 19). Document row was restored from pre-deletion backup (`backend/scratch/restore_incident_document.py`). Following an initial restoration report that contained fabricated values, an independent output-anchored verification script (`backend/scratch/independent_reverify.py`) executed 4 raw SQL queries and confirmed all 4 facts MATCH expected values. Task is formally CLOSED / VERIFIED. (Evidence artifacts: `backend/scratch/dry_run_test_cleanup.py`, `backend/scratch/cleanup_backup_20260927_094359/`, `backend/scratch/execute_test_cleanup.py`, `backend/scratch/reconcile_chunk_discrepancy.py`, `backend/scratch/restore_incident_document.py`, `backend/scratch/independent_reverify.py`).
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
12. **OCR Mock Fallback Strings:** **RESOLVED / CLOSED (2026-09-28)**.
    - **Standing Rule 1 & 6 Violation Rectified:** Historical mock fallback strings ("Meridian Corp", "Dr. James Whitfield") previously documented in `MASTER_CONTEXT.md` Section 4 as a latent fallback when both deterministic OCR (pypdf/Tesseract) and LLM-OCR (Gemini vision) failed have been completely eradicated.
    - **Database Verification:** Direct PostgreSQL audit across all tables (`documents.extracted_text`, `documents.doc_metadata`, and `audit_logs.details`) confirmed **0 real documents** and **0 audit logs** were ever contaminated with mock fallback strings (count = 0).
    - **Codebase Hardening:**
      - `backend/app/agents/ocr.py`: `PlainTextEngine` hardened to reject empty files rather than returning empty success; `HeuristicFallbackEngine` hardened to reject binary/scanned document formats (`.pdf`, `.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`, `.bin`, `.zip`, `.exe`, `.docx`, `.xlsx`) preventing raw binary stream leakage into text extraction. When all engines fail, `OCRAgent` raises `AgentException("All OCR engines failed...")`.
      - `backend/app/services/orchestrator.py`: OCR stage validates non-empty extracted text and intercepts failures, setting `DocumentStatus.ERROR` and recording the transition in `status_history` with audit reason `"ocr_extraction_failed_both_engines"`. Pipeline immediately halts; no downstream stages (chunking, embedding, entity extraction, summarization) are executed.
      - Repo-wide verification confirmed 0 occurrences of placeholder strings in `backend/app/agents/ocr.py`.
    - **Test Coverage:** Added 3 unit/pipeline tests to `backend/tests/test_ocr_agent.py` (10/10 passed) and verified targeted regression across orchestrator pipeline tests (24 passed, 1 skipped, 0 regressions).
13. **Existing Lower-Priority Issues:**
    - `/api/v1/graph` endpoint latency (~7.3s–9.68s baseline from document/entity assembly loop) — **RESOLVED / CLOSED (2026-09-28)**:
      - **Root Cause:** Rebuilt entire knowledge graph from scratch on every call: deserializing 557 documents' large `doc_metadata` JSONB blobs over asyncpg, running entity resolution/clustering, synthesizing edges, and computing NetworkX centrality.
      - **Caching Approach:** Process-local, in-memory, state-fingerprinted LRU cache (`GraphCache`, max 32 entries) in `backend/app/api/v1/graph.py` keyed by `(case_scope, user_scope, fingerprint)` where `fingerprint = f"{count}_{max_updated_at}_{limit}"` derived from a lightweight SQL aggregate query (`SELECT count(id), max(coalesce(updated_at, created_at)) FROM documents...`) executing in ~8–9ms.
      - **Real Measured Latency:**
        - Baseline: **7.5857s** total request latency (7.316s internal `_build_knowledge_graph` time; `t_db=4.044s`, `t_cluster=0.252s`, `t_assembly=1.095s`, `t_edges=1.883s`, `t_centrality=0.042s`).
        - Cache Miss: **6.3208s** total request latency (5.876s–6.077s internal build).
        - Cache Hit: **0.1493s (149.27ms)** total HTTP response latency (**8.14ms** internal cache lookup time), representing a **42.3x speedup**.
      - **Equivalence Verification:** Verified via `backend/tests/test_graph_performance_cache.py`:
        - 100% parity against ground truth snapshot `backend/tests/snapshots/graph_baseline_snapshot.json` (6,429,521 bytes).
        - Node Parity: Exactly 4,845 nodes (557 doc nodes + 4,288 entity nodes), identical ID sets, labels, types, and importance scores matching to 4 decimal places ($< 10^{-4}$).
        - Edge Parity: Exactly 10,134 edges at `minWeight=0.10`, identical composite keys `(source, target, label)`, weights matching to 4 decimal places, identical types and `metadata.shared_doc_count`.
        - Cache Invalidation: Mutating document `updated_at` in DB changes the fingerprint, triggers a cache miss, and rebuilds graph in 6.1559s before reverting.
      - **Documented Architectural Limitation:** Process-local in-memory cache per Uvicorn worker process. Does NOT synchronize across multiple Uvicorn worker processes in a multi-worker deployment. This is an explicitly approved architectural tradeoff (zero-cost constraint, read-heavy analytical view, not a security-critical revocation path; each worker populates its own LRU cache independently on first access and invalidates deterministically via state fingerprint).
    - Dashboard AI Agents panel verification — RESOLVED / CLOSED (2026-09-27; Section 7).
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
14. **Workstream 8 Finding 1 — Frontend One-File-Per-Request Upload Loop — RESOLVED / FIXED in Batch 4g:**
    - **File:** `frontend/src/features/documents/pages/DocumentsPage.tsx`
    - **Resolution:** Refactored the frontend upload handler in Batch 4g to batch multi-file uploads into a single `multipart/form-data` request targeting `POST /api/v1/documents/upload-multiple?case_id=...` (10 requests/min rate limit) rather than sequential per-file requests to `POST /documents/upload` (60/min). Preserved single-file fallback, upload progress calculation, and status messaging.
    - **Verification:** Verified via runtime network interception with Puppeteer (`scratch_verify_batch_4g.cjs`): uploading 2 files dispatched exactly 1 request to `POST /documents/upload-multiple` and 0 requests to `/documents/upload`.
15. **Workstream 8 Finding 2 — Frontend LoginPage.tsx Password Validation Copy Mismatch — RESOLVED / FIXED in Batch 4a/4b:**
    - **File:** `frontend/src/features/auth/pages/LoginPage.tsx`
    - **Resolution:** Client-side validation schema and UI hint text in `LoginPage.tsx` were updated in Batch 4a/4b to enforce the 5-rule strong password policy matching backend validation (8+ characters, uppercase, lowercase, digit, special character).
16. **Case-Level Summary Finding 1 — Synthetic Benchmark Document Dates in Timeline Aggregates:**
    - **Context:** The 24 synthetic regulatory benchmark documents ingested into the Enron corpus carry authoring dates from 2023–2024, causing the aggregated `latest_referenced_date` to reflect the benchmark creation window rather than the historical 1999–2002 Enron dispute.
    - **Handling:** Rather than silently fabricating or overwriting raw document metadata, the summary prompt directives specifically anchor executive narrative to the core operational activity window (`core_activity_start` to `core_activity_end`), distinguishing external or synthetic benchmark dates from core operational conduct. Logged honestly as a known limitation for downstream presentation.
17. **Environment Fragility Note — `.venv` vs System Python Interpreter Divergence (Namespace Package Artifact) — RESOLVED in Batch 4g:**
    - **Resolution:** The orphan empty directory `backend/.venv/Lib/site-packages/docx` was removed in Batch 4g. As a result, `import docx` now raises `ImportError` identically in both system Python and the local `.venv`, correctly setting `DOCX_AVAILABLE = False` and allowing `tests/test_reports_api.py` to pass 100% cleanly without modifying any tracked backend source code.
18. **Batch 3 Grounded RAG Q&A Known Limitations:**
    - **No Pre-LLM Scalar Relevance Floor (theta = None):** `theta = None` was selected because no defensible pre-LLM scalar relevance floor was established on this corpus/retrieval configuration. There is no scalar score cutoff filtering chunks before prompt assembly. Quality control relies on case-scoped retrieval, grounded prompting, LLM insufficiency behavior, Gate A, Gate B, and human review.
    - **Lexical Grounding vs. Semantic Entailment:** Gate B implements deterministic lexical grounding (token overlap $\ge 0.55$) and numeric/date containment, not full semantic entailment or Natural Language Inference (NLI). It cannot detect semantic negation (e.g., adding "did not" to an otherwise faithful chunk sentence) and has known limitations around heavy paraphrasing.
    - **Live Adversarial Test Scope:** Live adversarial tests on real near-domain questions (CALIB-OUT-04, CALIB-OUT-07) demonstrated LLM honesty and Gate A holding (Gemini declined to cite any chunk and returned insufficient evidence). Gate B was NOT exercised live on a false citation; Gate B's false-positive citation suppression mechanism was separately verified through the stubbed unit test (`test_qa_gate_b_unsupported_number_suppressed`) and the Gate B smoke test.
    - **Corpus Ingestion Fragmentation:** Header and email address-list fragments in raw corpus chunks remain a known corpus/retrieval limitation, scoring deceptively high on BM25 overlap without filtering; mitigated via regex heuristic `is_address_list_fragment` and `min_chunk_chars=50`.
19. **Incident 2026-09-27 — Scope Violation During Test-Account Cleanup (Document Restoration Completed):**
    - **What happened:** During the approved test-account/test-case cleanup execution, the Step 3
      query (`Document.uploaded_by IN (doc_owning_user_ids)`) deleted document `8539d172-7a46-4eec-95ea-af627211766e`
      (filename `b37727d6dfb246efbb61d9611f89dd5a.txt`, original filename `regulatory_memorandum_test.txt`)
      and its 18 `document_chunks` rows from Case `83969a81-07ab-40f6-8e6a-3bdb3a1377de` ("Memory Profiling Case").
      This case was explicitly approved for full exclusion from the cleanup (Ambiguity 2 resolution).
    - **Root cause:** The cleanup script's Step 3 filter selected documents purely by `uploaded_by`
      (matching test-account user IDs) without also verifying that the document's `case_id` was NOT
      in the excluded case set. The affected document was uploaded by `alice_lawyer@firm-alpha.com`
      (a test account) but belonged to Case `83969a81` (owned by the production user `user@example.com`),
      which was explicitly protected. The `ON DELETE CASCADE` constraint on `document_chunks.document_id`
      then automatically deleted the 18 associated chunks.
    - **Discovery:** Post-execution 7-table reconciliation detected a -132 chunk count vs the expected
      -114, prompting a forensic investigation (`backend/scratch/reconcile_chunk_discrepancy.py`) that
      traced the 18-chunk discrepancy to this specific document.
    - **Restoration (2026-09-27):** The document row was restored from the pre-deletion backup
      (`backend/scratch/cleanup_backup_20260927_094359/documents.json`) using
      `backend/scratch/restore_incident_document.py`. All fields restored verbatim from backup except:
      `uploaded_by` re-attributed to `user@example.com` (original uploader no longer exists), `status`
      set to `flagged` (its pre-incident state). Post-restoration verification: 15/15 field checks
      passed, 7/7 table count diffs correct (documents +1, all others unchanged).
    - **Irrecoverable data loss:** The 18 original `document_chunks` rows (text segments, page/section
      assignments, embedding vectors) were NOT captured in the pre-deletion chunk backup (which was
      scoped to Vulcan + automated test cases only) and are permanently lost. The document currently
      has 0 chunks. Re-ingestion through the standard pipeline is available to generate new (non-original)
      chunks but has NOT been performed and requires an explicit separate owner decision per Standing Rule 6.
    - **Reporting-Integrity Failure & Independent Re-Verification:** The restoration's initial execution report contained fabricated values (wrong case UUID, wrong user UUID, wrong text length/file size, invented non-existent model fields, and an invented chunk count on a protected case) — violating Standing Rule 7. Per Standing Rule 4 (self-skeptical review) and newly instituted Standing Rule 8 (output-anchored reporting), an independent read-only verification script (`backend/scratch/independent_reverify.py`) was executed to query live PostgreSQL directly using 4 raw SQL queries. The captured stdout confirmed:
      1. Primary case ID: `8d8389d4-2534-452d-85b4-65efe5b8e1c3` (MATCH).
      2. Production user `user@example.com` ID: `f20699fb-0881-4144-8eaa-58b90711b4a7`, role: `ADMIN` (MATCH).
      3. Restored document `8539d172`: `uploaded_by=f20699fb-0881-4144-8eaa-58b90711b4a7`, `text_length=1326`, `file_size=1326`, `checksum_sha256=21a5704ec89e73e0ff290e460c2c09f6e7b7e80981955d7e86edf8c7394cbc5b`, `status=FLAGGED`, `case_id=83969a81-07ab-40f6-8e6a-3bdb3a1377de` (MATCH).
      4. Protected case `685b2574` chunk count: `0` (MATCH — untouched).
    - **Pending Decisions & Follow-ups:**
      1. *Re-ingestion Decision (OPEN):* Whether to re-ingest restored document `8539d172` through the extraction pipeline to regenerate new chunks (and embeddings) remains an open owner decision. It is deliberately NOT performed or resolved.
      2. *Exclusion Filter Bug Fix (OPEN):* Adding the missing excluded-case guard to bulk cleanup queries remains tracked as Section 9 Item 2.
    - **Follow-up:** The missing exclusion filter in the cleanup query is tracked as a separate follow-up
      task (Section 9 Item 2).
20. **Pipeline Execution Status Endpoint (`GET /api/v1/agents/pipeline` & `GET /api/v1/documents/{id}/pipeline-status`):** **RESOLVED / CLOSED (2026-09-28)**.
    - **Prior State & Violation:** The prior audit noted `/agents/pipeline` unconditionally returned hardcoded `"caseId": "case_001"` and aggregated cross-case audit log completions (`select distinct resource_id from audit_logs where action = 'AGENT_EXECUTION_COMPLETED'`) to synthesize a global completion percentage and timestamps, completely detached from any specific document or case.
    - **Remediation & Architecture:**
      - Rewired `GET /api/v1/agents/pipeline` in `backend/app/api/v1/agents.py` to accept optional `caseId: Optional[UUID]` and `documentId: Optional[UUID]` query parameters, completely eliminating hardcoded `"case_001"` and cross-case audit queries.
      - Added direct RESTful endpoint `GET /api/v1/documents/{document_id}/pipeline-status` in `backend/app/api/v1/documents.py`.
      - Backed by unified service `get_pipeline_execution_status` in `backend/app/services/status_history_service.py`, which derives real stage execution states from `status_history` audit transitions ordered by `changed_at` combined with real `Document.status` and `Document.doc_metadata`.
      - **Authorization:** Reuses core tenant isolation (`verify_document_access` and `get_case_scoped_document_ids`): creator-only + admin-override. Maintains 403-before-404 existence privacy on unowned cases.
      - **Honest Telemetry:** Hardcoded ETA formula removed (`estimatedCompletionAt` is strictly `null`); quota paused states honestly reported (`isQuotaPaused=True`, `pausedStage="legal_review"`, real 429 reason); completed documents reflect exact `created_at` to `updated_at` boundaries; historical Enron documents with 0 status history rows honestly report `history=[]` rather than backfilled fabrications.
    - **Verification & Test Coverage:**
      - 7 new comprehensive unit/integration tests in `backend/tests/test_pipeline_status.py` (**7/7 PASSED**): owner access, 403 cross-tenant isolation, admin override, 403 existence privacy, 404 for missing document in owned case, quota paused representation, and elimination of `"case_001"` on unparameterized calls.
      - Existing 5 status history tests in `backend/tests/test_status_history.py` re-verified (**5/5 PASSED**).
      - Live verification against real Enron document `8a07ab8c-3f8f-411f-b185-4c75217147b4` in primary case `8d8389d4-2534-452d-85b4-65efe5b8e1c3` executed via `backend/scratch/capture_pipeline_after.py` with captured stdout showing real timestamps, real caseId/documentId, and zero synthetic placeholders.
      - Full backend test suite executed: **197 passed, 2 failed (known baseline variations), 3 skipped** (up from 190 passed, exactly +7 new tests, 0 regressions).

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
- **Grounded RAG Q&A Architecture & Post-Generation Gates (Batch 3):** Stateless single-turn grounded Q&A (`POST /api/v1/cases/{case_id}/ask`) over case-scoped chunks. Employs BM25-top-20 union cosine-top-20 candidate generation, `min_chunk_chars=50`, address-list fragment filtering, and `theta = None` pre-LLM scalar floor (selected because no defensible pre-LLM scalar floor was established on this corpus/retrieval configuration; quality control is provided across the full pipeline: case-scoped retrieval, grounded prompting, LLM insufficiency behavior, Gate A citation existence, Gate B lexical grounding, and mandatory human review). Single Gemini generation call with untrusted chunk syntax. Deterministic Gate A verifies citation existence (0 citations $\rightarrow$ `insufficient_evidence`; unknown citation $\rightarrow$ `suppressed`). Deterministic Gate B verifies lexical grounding (per-sentence content-token overlap $\ge 0.55$) and exact normalized numeric/date containment (with ordinal suffix stripping). Creator-only + admin authorization preventing case existence leakage. SlowAPI 10/minute rate limiting.

---

## 14. Next Exact Task

**PREVIOUS TASK CLOSED: TEST-ACCOUNT / TEST-CASE CLEANUP (CLOSED / VERIFIED)**

Status: **CLOSED / VERIFIED (2026-09-27)** (Reference: Section 9 Item 1; Section 11 Items 7, 19)

Completed steps & evidence chain:
- Read-only dry-run cascade check (`backend/scratch/dry_run_test_cleanup.py`): identified 29 test accounts, 494 non-primary cases, with 4 ambiguities.
- Owner reviewed and approved all 4 ambiguity resolutions.
- Pre-cleanup backup created (`backend/scratch/cleanup_backup_20260927_094359/`): full records for targeted accounts, cases, and documents safely captured.
- Destructive cleanup executed (`backend/scratch/execute_test_cleanup.py`): 29 accounts, 492 cases, 333 documents, 114 chunks, 214 summaries removed; `user@example.com` promoted to ADMIN. Primary Enron case, OCR Failure case, evaluation benchmarks, and audit logs confirmed untouched.
- Post-execution forensic audit (`backend/scratch/reconcile_chunk_discrepancy.py`): detected -132 chunks vs -114 expected; discovered scope violation where 18 chunks from excluded Case `83969a81` were deleted due to missing case-exclusion filter in Step 3 query. Identified affected document (`8539d172`).
- Owner approved 4-part restoration plan.
- Document row restored from backup (`backend/scratch/restore_incident_document.py`): 15/15 field verifications passed, 7/7 table diffs correct.
- 18 original chunk rows confirmed irrecoverably lost (not in backup). Document restored with 0 chunks per Standing Rule 6.
- Reporting-integrity failure caught (Standing Rule 7): initial restoration report contained fabricated values.
- Independent output-anchored verification (`backend/scratch/independent_reverify.py`): executed 4 raw SQL queries directly against live PostgreSQL; raw stdout verified 4/4 facts MATCH expected values (primary case ID, admin user ID/role, restored doc metadata/checksum/status, and OCR Failure case chunk count = 0).

Still-Open Owner Decisions & Follow-ups:
- Re-ingestion decision for document `8539d172` (whether to generate new chunks via the pipeline) remains an explicit, pending owner decision — deliberately NOT resolved.
- Exclusion-filter bug fix tracked as Section 9 Item 2 (OPEN / PLANNED).

---

**NEXT ROADMAP TASK: SELECTION BETWEEN SECTION 9 ITEM 2 AND ITEM 5**

Per Section 9's priority order:
1. **Option A (Recommended Immediate Technical Hardening): Section 9 Item 2 — Fix Cleanup/Bulk-Deletion Script Exclusion-Filter Bug**
   - **Rationale:** Addresses the direct root cause of the 2026-09-27 incident by hardening cascading deletion queries to include `.where(~Document.case_id.in_(EXCLUDED_CASE_IDS | {PRIMARY_CASE_ID}))`. Prevents regression in any future maintenance or cleanup runs.
2. **Option B (Primary Strategic Deliverable): Section 9 Item 5 — Report Rewrite**
   - **Rationale:** If code modifications are deferred, the primary thematic project milestone is reframing the final written report around case-centric investigation, agentic orchestration, verified Knowledge Graph, and reconciled DFD/UML diagrams.

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
8. **Output-Anchored Reporting:** Any report describing the results of a
   script execution (especially database mutations or verifications) must
   derive its stated values exclusively from actually-captured stdout/stderr,
   quoted or directly referenced — never composed from expectation of what
   output "should" be. A violation invalidates the report and requires
   independent re-verification before dependent decisions proceed.
9. Keep the written report honestly aligned with actual system state —
   the report rewrite (Section 14) may now proceed, since all three
   Knowledge Graph steps are genuinely done and verified, not merely
   claimed.
10. Zero cost / free-tier only — no paid APIs, no paid infrastructure.

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

### Case-Level Summary + Grounded RAG Q&A — Batch 3: Grounded RAG Q&A — CLOSED
**Status: VERIFIED COMPLETE / CLOSED** (All implementation, unit/smoke testing, full regression, theta=None decision, and real-data live verification completed)

#### Summary of Batch 3 Work Delivered
- **Endpoint Implementation:** `POST /api/v1/cases/{case_id}/ask` implemented in `backend/app/api/v1/case_qa.py` with service logic in `backend/app/services/case_qa_service.py` and schemas in `backend/app/schemas/case_qa.py`.
- **Candidate Generation & Pre-filtering:** BM25-top-20 union pgvector cosine-top-20 candidate generation with `min_chunk_chars=50` and address-list fragment filtering (`is_address_list_fragment`) isolated to `retrieve_case_chunks_qa` in `backend/app/services/retrieval_service.py`. Shared word-boundary regex tokenization fix (`\b\w+\b`) applied to `RetrievalAgent._execute` in `backend/app/agents/retrieval.py` as a positive side-effect.
- **Relevance Floor Investigation (theta = None):** Thorough diagnostic investigation across runs 1–5 documented and hashed in `backend/scratch/floor_decision_final.md` (SHA-256: `ca391365ca41e789c7187ff2ac3f4f247fd440e901fcf5a98ec47b3a6262bf85`). Proved that per-pool BM25 normalization and cosine baseline produce unconditional out-of-case scores (0.54–0.67) overlapping valid in-case scores (0.44–0.78). Formally adopted `theta = None` because no defensible pre-LLM scalar relevance floor was established on this corpus/retrieval configuration. Selecting `theta = None` does not prove retrieval quality nor does it imply Gate B alone prevents false citations. Quality control is provided across the full pipeline: case-scoped retrieval, grounded prompting, LLM insufficiency behavior, Gate A, Gate B, and mandatory human review.
- **Deterministic Gate A (Citation Existence):** Extracts `[C1]`..`[Ck]` citations. Zero citations cleanly resolves to `status="insufficient_evidence"`, `answer=None`. Unknown citations resolve to `status="suppressed"`, `answer=None`.
- **Deterministic Gate B (Lexical Grounding & Containment):** For answers passing Gate A, verifies per-sentence content-token overlap against cited chunks $\ge \tau = 0.55$ (reusing 44 stop words from `VerificationAgent`) and exact normalized numeric/date containment (with ordinal suffix stripping `15th` $\rightarrow$ `15`). Any unsupported sentence triggers full answer suppression (`status="suppressed"`, `answer=None`).
- **Security & Authorization Model:** Creator-only + admin-override via `get_case_scoped_document_ids`. Authorization precedes existence checking, preventing case existence leakage by returning HTTP 403 for unauthorized non-admin requests on both existing and nonexistent cases. HTTP 404 is reserved for authorized users hitting nonexistent cases.
- **Rate Limiting & Validation:** SlowAPI 10/minute rate limit keyed by IP; Pydantic whitespace rejection; max 1000 chars; `QuotaExhaustedException` mapped to HTTP 503.
- **Stubbed Test Suite:** **20/20 PASSED** in 30.11s with **0 live Gemini API calls** (`tests/test_case_qa.py`), verified using autouse `stub_embedding_agent` and `AsyncMock` for `LLMClient.generate_text`.
- **Gate B Smoke Test:** **8/8 PASSED** in `backend/scratch/smoke_test_gateb.py` (SHA-256: `22833f5f1ce3e2062ef88ccfe21e40fb82b8cfe907bfa351e56ce94f884969c9`).
- **Real-Data Initial Verification:** 5 live calls on Enron case `8d8389d4-2534-452d-85b4-65efe5b8e1c3`: 3 positive grounded answers, 2 absent/cross-case questions resolving to `insufficient_evidence`, 2 security checks returning 403 (SHA-256: `36457a2d19d2cd412602a43356fda60249a0f264496b432b6913fe7b2172cc4c`).
- **Live Adversarial Stress Test (`CALIB-OUT-04`, `CALIB-OUT-07`):** 2 live calls on near-domain absent questions. Surfaced topically-close chunks; LLM output verbatim *"Insufficient evidence in the case record to answer this question."*, resolving cleanly at Gate A to `insufficient_evidence`.
- **Live Adversarial Verification vs Gate B Distinction:** Live adversarial verification demonstrated LLM-honesty + Gate A on two real near-domain-absent questions (CALIB-OUT-04 Duke Energy and CALIB-OUT-07 Reliant Energy). In both cases the LLM declined to cite evidence, so Gate A resolved the response as insufficient evidence and Gate B was not exercised live. Gate B's false-positive citation suppression mechanism was separately verified through the stubbed unit test (`test_qa_gate_b_unsupported_number_suppressed`) and the Gate B smoke test. Thus the live tests do not constitute a live demonstration of Gate B suppressing a successfully generated false citation.
- **Live LLM Budget Compliance:** 5 (initial) + 2 (stress test) = **7 live calls total**, fully compliant with the hard ceiling of $\le 8$ calls.
- **Known Limitations Logged:** (1) No pre-LLM scalar relevance cutoff (`theta = None`); (2) Gate B is lexical grounding (token overlap $\ge 0.55$) and numeric/date containment, not full semantic entailment or Natural Language Inference (NLI), with known limitations around heavy paraphrase and semantic negation; (3) The live adversarial tests did not exercise a successful false citation through Gate B because the LLM declined to cite evidence; (4) Header and address-list ingestion fragmentation remains a known corpus/retrieval limitation; (5) Shared BM25 tokenization fix in `RetrievalAgent._execute` resolved a tokenizer discrepancy as a positive side-effect.

#### Final Official Verification Baseline (Post-Batch 3 Closure)
- **Backend Test Suite:** `python -m pytest tests/ -q --tb=short` $\rightarrow$ **165 passed, 2 failed, 3 skipped** (Time: ~190s).
- **Regression Analysis:** Exactly matches post-Batch 2 baseline (145 passed) + 20 new tests, with **0 regressions**. The 2 failures are the documented baseline LLM non-deterministic variations (`test_classification` and `test_clustering`); 3 skipped tests (`test_report_exports_format_encoding`, `test_ocr_pdf_processing`, `test_generate_text_live`).
- **Frontend Production Build:** `npm run build` $\rightarrow$ **0 errors** (maintained clean).

### Batch 4 — Frontend / UX Remediation & Legal Workflow Integration — CLOSED
**Status: VERIFIED COMPLETE / CLOSED** (All 7 sub-batches 4a–4g implemented and verified)

#### Summary of Batch 4 Work Delivered
- **Sub-batch 4a (Navigation Shell & Routing Infrastructure):** Case-scoped sidebar navigation (`Sidebar.tsx`), matter context, matter switching, and 6 legacy redirects (`/investigation` → `/cases`, `/knowledge-graph` → `/cases`, `/timeline` → `/cases`, `/ai-review` → `/cases`, `/analytics` → `/settings/analytics`, `/agents` → `/settings/agents`).
- **Sub-batch 4b (Case Workspace Shell & Context):** `CaseWorkspaceLayout.tsx` and `CaseWorkspaceContext.tsx` providing case-level state, real-time metrics, matter switching, and tab routing across 8 investigation tabs.
- **Sub-batch 4c (Case Intelligence Summaries UI):** `OverviewTab.tsx` integrating 5 structured legal sections from Batch 2 (`executive`, `legal`, `notable_provisions_and_findings`, `evidence`, `key_people_and_relationships`), manual generation trigger (`POST /generate`), loading states, and live hash staleness detection.
- **Sub-batch 4d (Grounded Case Q&A UI):** `AskTab.tsx` integrating grounded RAG endpoint (`POST /ask`) from Batch 3, query box with suggested prompts, cited chunk cards `[C1]`..`[Ck]`, Gate A/B status badges, suppression warning banner, and `insufficient_evidence` empty state.
- **Sub-batch 4e (Findings Tab & Evidence Traceability):** `FindingsTab.tsx` surfacing 29 verified matter findings (19 privilege, 7 risk, 3 escalation) with deep links to document viewer (`/documents/{id}`).
- **Sub-batch 4f (Executive Dashboard & Settings Expansion):** `DashboardPage.tsx` redesigned as executive review command center: Urgent Review Queue, Active Matters grid, Attention Needed banner, live audit log fallback. Technical visualizers relocated to Settings sub-views (`/settings/analytics` honest 11-metric grid with provenance notes, `/settings/agents` 18-agent architectural reference, `/settings/system` live health telemetry).
- **Sub-batch 4g (Cleanup, Polish & Upload Batching):**
  - Dead files removed (7 files, 1,305 lines): `mockAnalytics.ts`, `mockData.ts`, `Dashboard.tsx`, `CaseList.tsx`, `Header.tsx`, `AppLayout.tsx`, `Sidebar.tsx`.
  - Intentionally retained: `pages/NotFound.tsx` (404 route in `App.tsx`), `components/organisms/Header.tsx` (canonical active header in `DashboardLayout.tsx`).
  - Upload batching refactor (Known Issue 14 resolved): `DocumentsPage.tsx` refactored to dispatch multi-file uploads to `POST /api/v1/documents/upload-multiple?case_id=...` (10/min rate limit) instead of sequential per-file `POST /documents/upload` loops. Verified via runtime network interception: 1 batch request captured, 0 single upload requests captured.
  - Production build: `npm run build` (`tsc -b && vite build`) passed with **0 errors** (built in 4.29s).
  - Lint: `npm run lint` (`oxlint`) passed with **0 new warnings, 0 new errors** (9 warnings + 1 error baseline preserved).
  - Backend pytest baseline: **165 passed, 2 failed, 3 skipped** across 170 tests. Exact match to post-Batch 3 baseline (0 regressions).
  - Test-identity investigation: confirmed `test_clustering.py` at root does not exist; real test is `test_intelligence_layer.py::test_clustering`. Confirmed `test_risk_analysis` failure was non-deterministic classification boundary (`CRITICAL` vs `HIGH`), passing 3/3 in isolation. Confirmed `test_classification` passed 3/3 in isolation.
  - Zero tracked backend source files modified for Batch 4g. Local untracked empty directory `backend/.venv/Lib/site-packages/docx` removed to restore consistent `ImportError` on `import docx`.
  - Non-regression checks: Dashboard, Evidence tab, all 8 workspace tabs, all 6 redirects verified via automated Puppeteer execution with 0 console errors.
  - Git state: All file deletions unstaged (`git reset HEAD`) to preserve uniform unstaged working tree convention.

---

## NEXT SESSION — START HERE

**Current Working System State:**
- The application is running on FastAPI (backend, port 8000) and Vite/React (frontend, port 5173) connected to PostgreSQL with pgvector and Supabase Storage.
- Multi-tenant data isolation, quota paused handling, and Knowledge Graph Steps 1–3 are fully intact.
- Case-Level Summary + Grounded RAG Q&A — Batch 1 (Persistence Scaffolding) is **100% CLOSED / VERIFIED** (14/14 tests).
- Case-Level Summary + Grounded RAG Q&A — Batch 2 (Case Summary Generation) is **100% CLOSED / VERIFIED** (14/14 tests; real 423-doc case generation verified, 23.7s end-to-end latency, 1 LLM call).
- Case-Level Summary + Grounded RAG Q&A — Batch 3 (Grounded RAG Q&A) is **100% CLOSED / VERIFIED** (20/20 stubbed tests, Gate B 8/8 smoke test, 7/8 live LLM calls compliant, 0 regressions across 165 passed tests).
- Batch 4 (Frontend / UX Remediation & Legal Workflow Integration) is **100% CLOSED / VERIFIED** (Sub-batches 4a–4g implemented, tested, and verified; 0 build errors; 0 new lint warnings; 0 regressions).
- Real Case-Scoped Document Pipeline Execution Status (`GET /api/v1/agents/pipeline` & `GET /api/v1/documents/{id}/pipeline-status`) backed by `status_history` is **100% CLOSED / VERIFIED (2026-09-28)** (hardcoded `case_001` eliminated, 7 new tests in `test_pipeline_status.py` passed, full test suite: 197 passed, 2 failed [known variations], 3 skipped).
- Official baseline stands at **197 passed, 2 failed, 3 skipped** across 202 tests with verified stable failure composition.

**Important Files for Context:**
- `backend/app/services/status_history_service.py` — Unified pipeline execution status derivation (`get_pipeline_execution_status`) and atomic status transitions (`record_status_transition`).
- `backend/app/schemas/document.py` — Pydantic models for pipeline stage and status (`PipelineStatusResponse`, `PipelineStageResponse`).
- `backend/app/api/v1/documents.py` — Direct document pipeline status endpoint (`GET /{document_id}/pipeline-status`).
- `backend/app/api/v1/agents.py` — Pipeline execution endpoint (`GET /pipeline?caseId=...&documentId=...`).
- `frontend/src/features/case-workspace/` — Attorney-first case workspace layout, context, and 8 investigation tabs.
- `frontend/src/features/dashboard/pages/DashboardPage.tsx` — Executive review command center with urgent review queue.
- `frontend/src/features/settings/` — Dedicated administrative views (Analytics, Agents, System).
- `frontend/src/features/documents/pages/DocumentsPage.tsx` — Batch upload handler using `POST /documents/upload-multiple`.
- `backend/app/api/v1/case_qa.py` — Grounded Q&A endpoint (`POST /api/v1/cases/{case_id}/ask`).
- `backend/app/services/case_intelligence_service.py` — Batch 2 summary generation (`POST /api/v1/cases/{case_id}/summary/generate`).
- `CURRENT_STATUS.md` & `MASTER_CONTEXT.md` — Project sources of truth.

**Exact Next Action:**
- **Test-Account / Test-Case Cleanup** is **CLOSED / VERIFIED (2026-09-27)** (all 29 accounts, 492 cases removed, incident document restored, 4/4 live database facts independently verified via `backend/scratch/independent_reverify.py`).
- **Pipeline Execution Status Remediation** is **CLOSED / VERIFIED (2026-09-28)**.
- Proceed to owner-selected next task per Section 9 / Section 14:
  1. **Section 9 Item 2 (Immediate Technical Hardening):** Fix cleanup/bulk-deletion script exclusion-filter bug by adding `.where(~Document.case_id.in_(EXCLUDED_CASE_IDS | {PRIMARY_CASE_ID}))`.
  2. **Section 9 Item 5 (Core Strategic Deliverable):** Report Rewrite (reframe around case-investigation and verified pipeline).
- Note: Re-ingestion decision for restored document `8539d172` (whether to generate new chunks via pipeline) remains an open owner decision.

