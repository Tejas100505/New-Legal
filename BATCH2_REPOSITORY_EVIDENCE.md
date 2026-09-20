# Batch 2 Repository Evidence Report

**Target Workspace:** `c:\Users\under\OneDrive\Desktop\New-Legal1 (2)\New-Legal1 (2)\New-Legal1 (1)\New-Legal1\New-Legal`  
**Generated On:** September 16, 2026  
**Auditor Mode:** Read-Only Verification & Evidence Gathering (Zero Code Modifications)

---

## 1. Environment

- **Operating System:** Windows 10/11 (AMD64)
- **Active Python Executable:** `c:\Users\under\OneDrive\Desktop\New-Legal1 (2)\New-Legal1 (2)\New-Legal1 (1)\New-Legal1\New-Legal\backend\.venv\Scripts\python.exe`
- **Python Version:** Python 3.13.2 (system interpreter at `C:\Python313\python.exe`)
- **Node.js / Package Manager:** Node runtime with npm, Vite v8.1.4, TypeScript 5.x
- **Database Engine:** PostgreSQL 16 with pgvector extension (Supabase cloud / local connection via asyncpg)
- **Database Connection String [REPO EVIDENCE]:** Loaded via `app.config.Settings.async_database_url` in [backend/app/db/session.py](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/backend/app/db/session.py#L24).

---

## 2. Repository Structure

Exact verified absolute file paths [REPO EVIDENCE]:
- **Project Root:** `c:\Users\under\OneDrive\Desktop\New-Legal1 (2)\New-Legal1 (2)\New-Legal1 (1)\New-Legal1\New-Legal`
- **Backend Directory:** `c:\Users\under\OneDrive\Desktop\New-Legal1 (2)\New-Legal1 (2)\New-Legal1 (1)\New-Legal1\New-Legal\backend`
- **Frontend Directory:** `c:\Users\under\OneDrive\Desktop\New-Legal1 (2)\New-Legal1 (2)\New-Legal1 (1)\New-Legal1\New-Legal\frontend`
- **Backend Dependencies:** [backend/requirements.txt](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/backend/requirements.txt) (64 lines)
- **Frontend Dependencies:** [frontend/package.json](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/frontend/package.json)
- **Backend Test Directory:** `c:\Users\under\OneDrive\Desktop\New-Legal1 (2)\New-Legal1 (2)\New-Legal1 (1)\New-Legal1\New-Legal\backend\tests` (33 test modules)
- **Root Test Directory:** `c:\Users\under\OneDrive\Desktop\New-Legal1 (2)\New-Legal1 (2)\New-Legal1 (1)\New-Legal1\New-Legal\tests` (contains `e2e`, `integration`, `unit`)

---

## 3. Fabricated Analytics Sweep

A strict ripgrep search was conducted across the entire repository for the 9 audited numeric values: `98.7`, `94.2`, `2.4`, `3241`, `42.7`, `84521`, `1.9`, `99.0`, `0.84`.

| Value | Exact File & Line | Context & Code | Classification | Application Usage |
|---|---|---|---|---|
| **98.7** | [backend/app/api/v1/agents.py:L453](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/backend/app/api/v1/agents.py#L453) | `ocrAccuracy=_metric("OCR Accuracy", 98.7, "%", 0.2, ...)` | **Hardcoded fabricated API value** | Returned by `/api/v1/agents/analytics` |
| **98.7** | [frontend/src/lib/mockData.ts:L34,L223](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/frontend/src/lib/mockData.ts#L34) | `value: '98.7%'` | Mock dataset constant | Mock fallback / demo data |
| **94.2** | [backend/app/api/v1/agents.py:L454](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/backend/app/api/v1/agents.py#L454) | `aiConfidence=_metric("AI Confidence", 94.2, "%", ...)` | **Hardcoded fabricated API value** | Returned by `/api/v1/agents/analytics` |
| **94.2** | [backend/app/api/v1/timeline.py:L148](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/backend/app/api/v1/timeline.py#L148) | `"metadata": {"confidence": "94.2%"}` | Fallback mock timeline entry | Served on empty timeline |
| **2.4** | [backend/app/api/v1/agents.py:L457](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/backend/app/api/v1/agents.py#L457) | `processingTime=_metric("Processing Time", 2.4, "s", ...)` | **Hardcoded fabricated API value** | Returned by `/api/v1/agents/analytics` |
| **3241** | [backend/app/api/v1/agents.py:L458](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/backend/app/api/v1/agents.py#L458) | `evidenceCount=_metric("Evidence Count", 3241, "items", ...)` | **Hardcoded fabricated API value** | Returned by `/api/v1/agents/analytics` |
| **42.7** | [backend/app/api/v1/agents.py:L462](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/backend/app/api/v1/agents.py#L462) | `storageUsage=_metric("Storage Usage", 42.7, "GB", ...)` | **Hardcoded fabricated API value** | Returned by `/api/v1/agents/analytics` |
| **42.7** | [frontend/src/stores/analyticsStore.ts:L153](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/frontend/src/stores/analyticsStore.ts#L153) | `updated.storageUsage.value = 42.7;` | **Hardcoded store fallback value** | Injected on store refresh |
| **84521** | [backend/app/api/v1/agents.py:L463](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/backend/app/api/v1/agents.py#L463) | `apiUsage=_metric("API Usage", 84521, "calls", ...)` | **Hardcoded fabricated API value** | Returned by `/api/v1/agents/analytics` |
| **84521** | [frontend/src/stores/analyticsStore.ts:L154](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/frontend/src/stores/analyticsStore.ts#L154) | `updated.apiUsage.value = 84521;` | **Hardcoded store fallback value** | Injected on store refresh |
| **1.9** | [backend/app/api/v1/agents.py:L461](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/backend/app/api/v1/agents.py#L461) | `hallucinationRate=[2.8, 2.4, 2.1, 1.9, 1.7, 1.5, 1.3]` | **Hardcoded sparkline array** | Returned by `/api/v1/agents/analytics` |
| **99.0** | [frontend/src/stores/analyticsStore.ts:L108](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/frontend/src/stores/analyticsStore.ts#L108) | `updated.ocrAccuracy.value = 99.0;` | **Hardcoded store fallback value** | Injected on store refresh |
| **99.0** | [frontend/src/features/dashboard/pages/DashboardPage.tsx:L157](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/frontend/src/features/dashboard/pages/DashboardPage.tsx#L157) | `analytics.ocrAccuracy.value > 0 ? ... : (documents.length > 0 ? '99.0' : '0.0')` | **Hardcoded UI fallback string** | Rendered on dashboard card |
| **0.84** | [frontend/src/features/dashboard/pages/DashboardPage.tsx:L158](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/frontend/src/features/dashboard/pages/DashboardPage.tsx#L158) | `analytics.storageUsage.value > 0 ? ... : (documents.length > 0 ? '0.84' : '0.0')` | **Hardcoded UI fallback string** | Rendered on dashboard card |

---

## 4. Agents Analytics Endpoint

[REPO EVIDENCE]
- **Exact File:** [backend/app/api/v1/agents.py:L432-L465](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/backend/app/api/v1/agents.py#L432-L465)
- **Route:** `@router.get("/analytics", response_model=AgentAnalyticsResponse)` (full path `/api/v1/agents/analytics`)
- **Fields Returned:**
  1. `ocrAccuracy`: 98.7 (hardcoded float + hardcoded sparkline `[96.1, 96.8, 97.2, 97.5, 97.9, 98.3, 98.7]`)
  2. `aiConfidence`: 94.2 (hardcoded float + hardcoded sparkline `[90.5, 91.2, 92.0, 92.8, 93.4, 93.9, 94.2]`)
  3. `processingTime`: 2.4 (hardcoded float + hardcoded sparkline `[3.8, 3.5, 3.1, 2.9, 2.7, 2.5, 2.4]`)
  4. `evidenceCount`: 3241 (hardcoded int + hardcoded sparkline `[2680, 2820, 2950, 3020, 3100, 3180, 3241]`)
  5. `storageUsage`: 42.7 (hardcoded float + hardcoded sparkline `[28, 31, 34, 36, 38, 40, 42.7]`)
  6. `apiUsage`: 84521 (hardcoded int + hardcoded sparkline `[45000, 52000, 58000, 64000, 71000, 78000, 84521]`)
  7. `accuracyTrend`: `[97.2, 97.8, 98.1, 98.3, 98.5, 98.6, 98.7]` (hardcoded array)
  8. `confidenceTrend`: `[91.5, 92.1, 92.8, 93.4, 93.8, 94.0, 94.2]` (hardcoded array)
  9. `hallucinationRate`: `[2.8, 2.4, 2.1, 1.9, 1.7, 1.5, 1.3]` (hardcoded array)
  10. `avgLatency`: `[3.2, 2.9, 2.7, 2.6, 2.5, 2.4, 2.4]` (hardcoded array)
  11. `activeAgentsCount`: `len(agents)` (dynamic count of in-memory registered agents = 8)
  12. `successRate`: 99.2 (hardcoded float)
- **Callers Search:**
  - `frontend/src/features/agents/api.ts:L35-L38`: Function `fetchAgentAnalytics()` calls `api.get(API_ENDPOINTS.AGENTS.ANALYTICS)`.
  - **Repo-wide callers of `fetchAgentAnalytics`:** **ZERO callers**. No component or store currently triggers this function.
  - **Backend callers:** **ZERO callers**.
  - **Scripts / Documentation callers:** **ZERO callers**.

---

## 5. Analytics Implementation & Admin Entity Count

[REPO EVIDENCE & DATABASE EVIDENCE]
Inspected [backend/app/api/v1/analytics.py](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/backend/app/api/v1/analytics.py):

1. **Entity / Mention Count Calculation:**
   - Evaluated dynamically via `select(Document.doc_metadata)` with status filter.
   - For each metadata row, inspects `doc_metadata["entities"]`:
     - If dict-of-categories (production shape), sums `len(items)` for each category list.
     - If flat list (legacy/compatibility), sums `len(doc_entities)`.
2. **Chunk Count Calculation:**
   - Evaluated via `select(func.count(DocumentChunk.id))` joined to Document and Case.
3. **Storage Usage Calculation:**
   - **NOT CALCULATED in `analytics.py`**. The endpoint does not query `Document.file_size` or storage bytes.
4. **Status Filtering Mechanism:**
   - Negative exclude-list: `status.notin_([UPLOADED, VALIDATING, OCR_PROCESSING, CHUNKING, EMBEDDING, ANALYZING, QUOTA_PAUSED, ERROR])`.
   - Admitted statuses: `[DocumentStatus.REVIEWED, DocumentStatus.FLAGGED]`.
5. **Logic Duplication:**
   - `analytics.py` calculates its own metrics.
   - `agents.py` returns hardcoded metrics completely independent of `analytics.py`.
   - `analyticsStore.ts` contains its own hardcoded fallback assignments (`storageUsage = 42.7`, `apiUsage = 84521`, `ocrAccuracy = 99.0`, `retrievalQuality = 89.6`).
   - No shared analytics service helper exists in `backend/app/services/`.
6. **Live Admin Entity Count Query Result [DATABASE EVIDENCE]:**
   - Query executed directly on PostgreSQL database:
     - Non-excluded documents: **430** (425 `REVIEWED` + 5 `FLAGGED`)
     - Total raw extracted entities detected: **10,409**
     - Breakdown by category:
       - `people`: 4,899
       - `organizations`: 3,636
       - `dates`: 1,199
       - `locations`: 442
       - `money`: 221
       - `case_numbers`: 7
       - `courts`: 5
       - **Total: 10,409**

---

## 6. Null / Availability Semantics

[REPO EVIDENCE]
Inspected [backend/app/api/v1/analytics.py:L158-L168](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/backend/app/api/v1/analytics.py#L158-L168) and [frontend/src/features/analytics/components/AnalyticsGrid.tsx](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/frontend/src/features/analytics/components/AnalyticsGrid.tsx):

- **`avg_review_time_seconds`:**
  - Backend returns `None` (`null` in JSON).
  - Frontend renders `"N/A"` with a `"Pending measurement"` badge and a neutral horizontal dashed line (`border-t border-dashed border-slate-800/80`). Sparkline never pushes 0.
- **`avg_confidence_score`:**
  - Backend returns `None` (`null` in JSON).
  - Frontend renders `"N/A"` with a `"Pending measurement"` badge and a dashed line. Sparkline never pushes 0.
- **`OCR Accuracy`:**
  - Backend `analytics.py` does NOT return an `ocr_accuracy` value inside `enriched_metrics` (only an explanation string in the response metadata).
  - `frontend/src/stores/analyticsStore.ts:L108` explicitly injects `updated.ocrAccuracy.value = 99.0;`.
  - `frontend/src/features/dashboard/pages/DashboardPage.tsx:L157` formats it with a fallback: `(documents.length > 0 ? '99.0' : '0.0')%`.
  - Unavailable OCR accuracy is represented as **a fabricated value (99.0%)** in the dashboard.
- **`Storage Usage`:**
  - Backend `analytics.py` does NOT compute storage usage.
  - `frontend/src/stores/analyticsStore.ts:L153` injects `updated.storageUsage.value = 42.7;`.
  - `frontend/src/features/dashboard/pages/DashboardPage.tsx:L158` formats it with a fallback: `(documents.length > 0 ? '0.84' : '0.0') MB`.
  - Unavailable storage usage is represented as **a fabricated/fallback value (42.7 GB in store, 0.84 MB in dashboard card)**.

---

## 7. Document Count Reconciliation

[DATABASE EVIDENCE]
Executed direct query against the PostgreSQL `documents`, `cases`, and `users` tables via [scratch/audit_corpus_scope.py](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/scratch/audit_corpus_scope.py):

```sql
SELECT status, count(*) FROM documents GROUP BY status;
```
- `REVIEWED`: 425
- `FLAGGED`: 5
- `UPLOADED`: 4
- `QUOTA_PAUSED`: 1
- `ANALYZING`: 1
- `ERROR`: 1
- **Total Documents in Database:** **437**

```sql
SELECT c.id, c.title, count(d.id) 
FROM documents d 
LEFT JOIN cases c ON d.case_id = c.id 
GROUP BY c.id, c.title;
```
- Case `8d8389d4-2534-452d-85b4-65efe5b8e1c3` ("California Energy Market Practices Inquiry"): **423**
- Case `None` (Orphan documents): **11**
- Case `bd8c3f56-9f3d-49f0-8804-d1bf7bca7a71` ("Project Vulcan - Firm Beta Confidential IP Matter"): **1**
- Case `83969a81-07ab-40f6-8e6a-3bdb3a1377de` ("Memory Profiling Case"): **1**
- Case `685b2574-bda0-43aa-b1ec-b75ff3faee3e` ("OCR Failure Verification Matter"): **1**
- **Total:** **437**

```sql
SELECT u.id, u.email, count(d.id) 
FROM documents d 
LEFT JOIN users u ON d.uploaded_by = u.id 
GROUP BY u.id, u.email;
```
- `user@example.com` (Jane Doe - Primary User): **424**
- `None` (Unassigned / system seed): **5**
- `alice_lawyer@firm-alpha.com` (Test account): **5**
- `bob_lawyer@firm-beta.com` (Test account): **1**
- `lawyer_a_1a6443@firm.com` (Test account): **1**
- `lawyer_a_c958a8@firm.com` (Test account): **1**
- **Total:** **437**

### Reconciled Count Accounting
1. **424 Documents:** The primary active Enron + synthetic dataset uploaded by `user@example.com` under Case `8d8389d4-...`.
2. **426 Documents:** The count of files migrated to Supabase Storage in Workstream 3 (424 original documents + 2 testing/profiling documents that existed as local files during storage migration).
3. **430 Documents:** Completed pipeline documents with status `[REVIEWED, FLAGGED]` (425 reviewed + 5 flagged). These 430 documents are queried by `/api/v1/analytics`, yielding the 10,409 raw mentions.
4. **437 Documents:** All records in the `documents` table (430 completed + 4 uploaded + 1 quota_paused + 1 analyzing + 1 error). In `/api/v1/graph`, all documents having `doc_metadata IS NOT NULL` generate **437 document nodes** (`doc_xxxxxxxx`).
5. **Test Account Contamination:**
   - 8 documents in the database belong to test accounts (`alice_lawyer`, `bob_lawyer`, `lawyer_a_*`).
   - 6 of those 8 documents have status `REVIEWED` or `FLAGGED`.
   - Under an un-scoped admin query, these 6 documents **are included** in global analytics and graph generation.

---

## 8. Graph Reconciliation

[REPO EVIDENCE & DATABASE EVIDENCE]
Executed live graph generation simulation against PostgreSQL using [scratch/audit_graph_nodes.py](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/scratch/audit_graph_nodes.py) mirror of [backend/app/api/v1/graph.py](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/backend/app/api/v1/graph.py):

- **Clusters produced by `EntityResolutionService`:** **5,096**
- **Candidate clusters visited across documents:** **5,093** (3 unvisited)
- **Nodes pruned by `should_suppress_node`:** **803**
  - `single_token_person_fragment`: 779
  - `header_or_protocol_artifact`: 23
  - `both_header_and_single_token_person`: 1
- **Final live canonical entity nodes:** **4,290**
  - `person`: 1,780
  - `organization`: 1,415
  - `date`: 681
  - `location`: 223
  - `money`: 180
  - `case_number`: 7
  - `court`: 4
- **Document nodes:** **437**
- **Total graph nodes:** **4,727** (4,290 canonical entity nodes + 437 document nodes)
- **Total live edges (minWeight = 0.1):** **9,884**
  - Document-to-entity containment edges: **6,967**
  - Inter-entity relationship edges: **2,917**

### Exact Arithmetic
$$\text{Visited Candidate Clusters } (5,093) - \text{Suppressed Nodes } (803) = \text{Live Canonical Entity Nodes } (4,290)$$
$$\text{Live Entity Nodes } (4,290) + \text{Document Nodes } (437) = \text{Total Graph Nodes } (4,727)$$

### Resolution of Historical 5,087 / 5,083 vs Current 4,290
- In the initial implementation (Knowledge Graph Step 1), before the single-token person suppression rule was introduced in `edge_weighting.py`, only 4 header/protocol delimiters were suppressed ($5,087 - 4 = 5,083$).
- Later, the generic `is_single_token_person(name, category)` rule was implemented to prune unresolvable single-token names (779 nodes like `'Sue'`, `'John'`).
- Concurrently, 9 additional clusters were created from subsequent document uploads ($5,087 \to 5,096$).
- Subtracting the 803 pruned nodes from the 5,093 candidate clusters yields exactly **4,290 live canonical entity nodes**.

---

## 9. Graph Edge Test Failure Investigation

[TEST EVIDENCE & REPO EVIDENCE]
Inspected [backend/tests/test_graph_edge_reconciliation.py](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/backend/tests/test_graph_edge_reconciliation.py) and executed via pytest:

- **Command:** `.\.venv\Scripts\python.exe -m pytest tests/test_graph_edge_reconciliation.py -vv -s`
- **Result:**
  ```text
  FAILED tests/test_graph_edge_reconciliation.py::test_graph_endpoint_no_doc_nodes_in_inter_entity_pairs_and_exact_mention_reconciliation
  AssertionError: Expected exactly 6,955 doc-mention edges, got 6967
  assert 6967 == 6955
  ```
- **World A vs World B Determination:**
  - **WORLD B APPLIES.**
  - The test sets up:
    ```python
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res_zero = await client.get("/api/v1/graph?minWeight=0.0", headers=headers)
    ```
  - The test does **not** mock the database, does **not** use an isolated SQLite test database, and does **not** reset database state. It executes `GET /api/v1/graph` against the **live PostgreSQL database**.
  - When the test was originally written, the live database contained documents yielding exactly 6,955 document-to-entity containment edges.
  - As subsequent test documents were ingested into PostgreSQL (bringing total documents to 437), the live document-mention edge count increased from 6,955 to 6,967 (+12 edges).
  - The hardcoded assertion `assert len(doc_edges_zero) == 6955` failed because of database data growth against an un-isolated live database.

---

## 10. KMeans / Clustering Failure Investigation

[TEST EVIDENCE & REPO EVIDENCE]
Inspected [backend/app/agents/clustering.py](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/backend/app/agents/clustering.py) and [backend/tests/test_intelligence_layer.py](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/backend/tests/test_intelligence_layer.py):

- **Command:** `.\.venv\Scripts\python.exe -m pytest tests/test_intelligence_layer.py::test_clustering`
- **Traceback:**
  ```text
  tests\test_intelligence_layer.py:18: in test_clustering
      clusters = await cluster_agent.cluster_documents(docs)
  app\agents\clustering.py:184: in cluster_documents
      kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
  E   TypeError: 'NoneType' object is not callable
  ```
- **Code in `app/agents/clustering.py:L14-L19`:**
  ```python
  try:
      from sklearn.cluster import KMeans
      from sklearn.feature_extraction.text import TfidfVectorizer
  except (ImportError, Exception):
      KMeans = None
      TfidfVectorizer = None
  ```
- **Root Cause Verified via Direct Python Execution:**
  - Running `.\.venv\Scripts\python.exe -c "from sklearn.cluster import KMeans"` produces:
    ```text
    ImportError: No module named 'sklearn.__check_build._check_build'
    Contents of ...\.venv\Lib\site-packages\sklearn\__check_build:
    _check_build.cp311-win_amd64.pyd
    ```
  - **The scikit-learn package in `.venv` was installed as a CPython 3.11 wheel (`cp311`), but the active virtual environment is running Python 3.13.2 (`cp313`)**.
  - Python 3.13 cannot load `cp311` compiled C-extension `.pyd` files, causing `import sklearn` to raise `ImportError`.
  - The `try/except` block in `clustering.py` caught this exception and set `KMeans = None`.
  - At line 184, calling `KMeans(...)` fails with `'NoneType' object is not callable`.

---

## 11. SlowAPI Status

[REPO EVIDENCE]
- **Present in `requirements.txt`:** **YES** ([backend/requirements.txt:L24](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/backend/requirements.txt#L24) contains `slowapi>=0.1.9`).
- **Installed in Virtual Environment:** **YES** (`pip show slowapi` reports version `0.1.10`).
- **Middleware / Instantiation:**
  - [backend/app/main.py:L173-L177](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/backend/app/main.py#L173-L177):
    ```python
    if SLOWAPI_AVAILABLE:
        limiter = Limiter(key_func=get_remote_address)
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        logger.info("Rate limiting enabled")
    ```
- **Route Decorators:** **ZERO**. A repo-wide search for `@limiter.limit` returns **0 occurrences**. None of the `/api/v1/auth/login`, `/api/v1/auth/register`, or AI endpoints have rate-limiting decorators applied.
- **Test Coverage:** **ZERO**. No tests exist in `backend/tests` verifying rate-limiting enforcement.

---

## 12. Git & Backup State

[REPO EVIDENCE]
- **Git Repository Initialized:** **NO**.
  - Running `git status` produces:
    ```text
    fatal: not a git repository (or any of the parent directories): .git
    ```
- **Recent Backups / Workspace Snapshots:**
  - The active workspace is located at:
    `c:\Users\under\OneDrive\Desktop\New-Legal1 (2)\New-Legal1 (2)\New-Legal1 (1)\New-Legal1\New-Legal`
  - The path reflects nested OneDrive desktop backup folders created on the host filesystem.
  - Internal backup subfolder: `data\enron_evaluation\labeling\_backup_before_merge` contains prior label evaluation backups.

---

## 13. Full Backend Test Results

[TEST EVIDENCE]

### Full Backend Suite Run
```powershell
.\.venv\Scripts\python.exe -m pytest -q --tb=short
```
- **Total Tests Run:** 98
- **Passed:** 94
- **Failed:** 2
- **Skipped:** 2:
  1. `tests/test_evaluation_analytics_integration.py::test_report_exports_format_encoding` (reason: `reportlab not installed`)
  2. `tests/test_intelligence_layer.py::test_timeline_generation` (optional embedding model test)
- **Warnings:** 9
- **Execution Time:** 101.87s

### Specifically Relevant Sub-Suites Run
```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_security_audit.py tests/test_quota_exhaustion.py tests/test_entity_resolution.py tests/test_edge_weighting.py tests/test_centrality.py -q
```
- **Security Audit (`test_security_audit.py`):** 13 passed (100%)
- **Quota Exhaustion (`test_quota_exhaustion.py`):** 8 passed (100%)
- **Entity Resolution (`test_entity_resolution.py`):** 12 passed (100%)
- **Edge Weighting (`test_edge_weighting.py`):** 9 passed (100%)
- **Centrality Service (`test_centrality.py`):** 6 passed (100%)
- **Combined Sub-Suite Total:** **48 passed, 0 failed in 42.21s**.

---

## 14. Frontend Build & Implementation

[REPO EVIDENCE & TEST EVIDENCE]
- **Build Command:** `npm run build` in `c:\Users\under\OneDrive\Desktop\New-Legal1 (2)\New-Legal1 (2)\New-Legal1 (1)\New-Legal1\New-Legal\frontend`
- **Output:**
  ```text
  > frontend@0.0.0 build
  > tsc -b && vite build

  vite v8.1.4 building client environment for production...
  transforming...✓ 3273 modules transformed.
  rendering chunks...
  computing gzip size...
  ✓ built in 4.92s
  ```
- **Exit Code:** 0 (Clean build, 0 TypeScript errors, 0 bundling errors).
- **Dashboard Implementation Relevant to Analytics:**
  - [frontend/src/features/dashboard/pages/DashboardPage.tsx:L157-L158](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/frontend/src/features/dashboard/pages/DashboardPage.tsx#L157-L158):
    - Fallback values `'99.0%'` (OCR) and `'0.84 MB'` (Storage) are still rendered when metric value `<= 0`.
  - [frontend/src/features/dashboard/pages/DashboardPage.tsx:L303](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/frontend/src/features/dashboard/pages/DashboardPage.tsx#L303):
    - Replaced the hardcoded badge `'1,506 Entities'` with dynamic `${analytics.evidenceCount.value.toLocaleString()} Entities`.

---

## 15. CURRENT_STATUS.md Cross-Check

| Claim in CURRENT_STATUS | Actual Evidence | Match? | Notes |
|---|---|---|---|
| "Batch 2 — Honest Analytics Metrics & UI Remediation — VERIFIED COMPLETE" | `DashboardPage.tsx` lines 157-158 retain `'99.0%'` and `'0.84 MB'` fallbacks; `agents.py` retains hardcoded `/analytics` endpoint. | **NO (Contradicted)** | Backend `analytics.py` is honest, but dashboard and agents router still have hardcoded/fallback analytics. |
| "Zero occurrences of 1506, 1,506, 0.824, or 1.9 remain in application source code" | `1.9` exists at line 461 in `backend/app/api/v1/agents.py`. | **NO (Contradicted)** | `1506`, `1,506`, and `0.824` are completely eliminated, but `1.9` remains in `agents.py`. |
| "total_entities_detected yields exactly 10,409 raw mentions across 430 non-excluded documents" | Direct DB query in PostgreSQL verified 430 non-excluded documents and 10,409 raw mentions. | **YES (Verified)** | Exact match verified against live PostgreSQL. |
| "avg_review_time_seconds and avg_confidence_score honestly returned as None/null" | Verified in `analytics.py` lines 164 & 166. | **YES (Verified)** | Exact match. |
| "Knowledge graph returns 4,727 total nodes (437 document nodes, 4,290 canonical entity nodes) and 9,884 edges" | Live graph simulation queries verified 437 doc nodes, 4,290 canonical entity nodes, and 9,884 edges. | **YES (Verified)** | Exact match. |
| "slowapi is missing from requirements.txt" | [backend/requirements.txt:L24](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/backend/requirements.txt#L24) contains `slowapi>=0.1.9`. | **NO (Contradicted)** | `slowapi` is already present in `requirements.txt` and installed. |
| "Workspace is not under Git" | `git status` returns `fatal: not a git repository`. | **YES (Verified)** | Exact match. |
| "Batch 1 test run: 91 passed, 1 skipped, 5 failed" | Full backend test suite currently reports 94 passed, 2 skipped, 2 failed. | **NO (Outdated)** | Test suite results evolved to 94 passed, 2 failed. |
| "Cross-tenant access control verified with 13 passed tests" | `test_security_audit.py` executes 13 tests, all 13 passed. | **YES (Verified)** | Exact match. |
| "Quota-exhaustion verified with 8 passed tests" | `test_quota_exhaustion.py` executes 8 tests, all 8 passed. | **YES (Verified)** | Exact match. |

---

## 16. Opus Findings Cross-Check

1. **Fabricated analytics values exist:**  
   **CONFIRMED.** Found hardcoded `98.7`, `94.2`, `2.4`, `3241`, `42.7`, `84521`, `1.9` in [backend/app/api/v1/agents.py:L453-L464](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/backend/app/api/v1/agents.py#L453-L464) and `42.7`, `84521`, `99.0`, `89.6` in [frontend/src/stores/analyticsStore.ts:L108-L154](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/frontend/src/stores/analyticsStore.ts#L108-L154).
2. **Dashboard has fabricated/stale values:**  
   **CONFIRMED.** [DashboardPage.tsx:L157-L158](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/frontend/src/features/dashboard/pages/DashboardPage.tsx#L157-L158) contains static fallback values `'99.0%'` and `'0.84 MB'`.
3. **Agents analytics endpoint needs honesty/deprecation:**  
   **CONFIRMED.** `/api/v1/agents/analytics` returns static mock numbers. Frontend export `fetchAgentAnalytics` in `agents/api.ts` is unused.
4. **Null semantics need correction:**  
   **PARTIALLY CONFIRMED.** `AnalyticsGrid.tsx` correctly handles nulls with `"N/A"` and dashed baselines, but `DashboardPage.tsx` and `analyticsStore.ts` overwrite or fall back to fake non-null numbers.
5. **Analytics should be centralized:**  
   **CONFIRMED.** There is no centralized `analytics_service.py`; logic is split across `analytics.py`, `agents.py`, and `analyticsStore.ts`.
6. **Positive status filtering should be considered:**  
   **CONFIRMED.** `analytics.py` uses a negative exclude list (`status.notin_(...)`). While it currently resolves to `[REVIEWED, FLAGGED]`, an explicit positive filter `status.in_([REVIEWED, FLAGGED])` is more robust against future enum additions.
7. **Graph discrepancy needs reconciliation:**  
   **RESOLVED.** 4,290 canonical entity nodes = 5,093 visited candidates - 803 pruned nodes (779 single-token person fragments + 24 headers). Historical 5,083 was prior to single-token person pruning.
8. **Graph-edge test needs root-cause diagnosis:**  
   **RESOLVED.** World B confirmed: `test_graph_edge_reconciliation.py` hits the live PostgreSQL DB directly via `ASGITransport(app=app)`. Hardcoded baseline 6,955 failed because live containment edges grew to 6,967 with subsequent document additions.
9. **KMeans None is a dependency/import issue:**  
   **CONFIRMED.** scikit-learn binary wheel in `.venv` was compiled for CPython 3.11 (`_check_build.cp311-win_amd64.pyd`) and fails to import under Python 3.13.2, setting `KMeans = None`.
10. **Test accounts should not be deleted/heuristically filtered:**  
    **CONFIRMED.** Test accounts own 8 documents in PostgreSQL, 6 of which have `REVIEWED`/`FLAGGED` status and legitimately contribute to live database metrics.
11. **Document count discrepancy needs accounting:**  
    **RESOLVED.** 424 = Jane Doe original corpus; 426 = storage migration corpus; 430 = completed reviewed/flagged corpus; 437 = total documents in database.
12. **Storage metric should be genuinely measured or null:**  
    **CONFIRMED.** Storage is unmeasured in `analytics.py` and populated with hardcoded values (42.7 GB / 0.84 MB).
13. **SlowAPI already exists:**  
    **CONFIRMED.** `slowapi>=0.1.9` is in `requirements.txt` line 24, installed in `.venv`, and initialized in `main.py`, but has 0 endpoint limit decorators.
14. **Git was not initialized:**  
    **CONFIRMED.** `git status` reports `fatal: not a git repository`.

---

## 17. Verified Open Issues

1. **Fabricated Values in Dashboard & Store:**
   - `frontend/src/features/dashboard/pages/DashboardPage.tsx` lines 157–158: fallback strings `'99.0%'` and `'0.84 MB'`.
   - `frontend/src/stores/analyticsStore.ts` lines 108, 144, 151–154: hardcoded assignments `ocrAccuracy = 99.0`, `retrievalQuality = 89.6`, `similarCases = 18`, `agentRuntime = 47.3`, `storageUsage = 42.7`, `apiUsage = 84521`.
2. **Fabricated Backend Route `/api/v1/agents/analytics`:**
   - `backend/app/api/v1/agents.py` lines 432–465: returns hardcoded mock analytics including `1.9` in `hallucinationRate`.
3. **Failing Pytest Tests (2 Failures):**
   - `tests/test_graph_edge_reconciliation.py`: stale hardcoded assertion `assert len(doc_edges_zero) == 6955` (actual live count is 6,967).
   - `tests/test_intelligence_layer.py`: `TypeError: 'NoneType' object is not callable` at `KMeans(...)` due to CPython 3.11 wheel incompatible with Python 3.13.2.
4. **Rate Limiting Inactive on Routes:**
   - SlowAPI is initialized on `app.state.limiter`, but zero `@limiter.limit` decorators are applied to `/auth/login`, `/auth/register`, or AI routes.
5. **No Version Control:**
   - Workspace root has no Git repository initialized.

---

## 18. Evidence-Based Recommended Next Investigation

1. **Dashboard & Store Null Remediation:**
   - Change `DashboardPage.tsx` to handle `null` for `ocrAccuracy` and `storageUsage` without falling back to `'99.0'` or `'0.84'`.
   - Remove fake number assignments in `analyticsStore.ts:refreshAnalytics` so unmeasured metrics remain `null`.
2. **Deprecate or Remove `/api/v1/agents/analytics`:**
   - Remove or honestly stub `/api/v1/agents/analytics` in `backend/app/api/v1/agents.py` and delete the unused `fetchAgentAnalytics` helper.
3. **Environment Fix for scikit-learn:**
   - Reinstall a Python 3.13-compatible wheel of `scikit-learn` in `.venv` so `from sklearn.cluster import KMeans` succeeds.
4. **Isolate Test Database for Graph Tests:**
   - Provide a fixture-backed database session for `test_graph_edge_reconciliation.py` instead of running assertions against the evolving live PostgreSQL database.
5. **Wire SlowAPI Route Decorators:**
   - Apply `@limiter.limit("5/minute")` to auth endpoints and write integration tests verifying HTTP 429 responses.
