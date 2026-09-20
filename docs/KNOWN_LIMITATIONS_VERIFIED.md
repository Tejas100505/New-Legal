# Verified System Limitations: Knowledge Graph Latency & Verification Grounding

> **Notice & Purpose**: This document is internal engineering and evaluation documentation to inform the eventual report rewrite. It provides an empirical, evidence-based audit of two documented system limitations in the **Agentic AI for E-Discovery & Legal Review** platform:
> 1. The `/api/v1/graph` endpoint latency and runtime bottleneck breakdown.
> 2. The `VerificationAgent` token-overlap grounding check mechanism and failure modes.
>
> **Design Decision**: This file is maintained as a dedicated limitations document in `docs/` alongside `architecture.md` and `EVALUATION_METHODOLOGY_NOTES.md` to keep runtime systems and architectural constraints clearly separated from evaluation benchmark methodology.

---

## 1. Knowledge Graph Latency Audit (`/api/v1/graph`)

### A. Background & Prior Assumption
Previous project documentation cited an endpoint latency of approximately **~9.68 seconds** across 424 documents. In `backend/app/api/v1/graph.py` (lines 342–343), developer comments attributed this latency primarily to:
> *"full document metadata traversal and entity resolution loop (lines 206-330)"*

Following Task #3, which removed 5,100 spurious duplicate document-containment edges from the inter-entity pool and reconciled edge counts, the endpoint was re-benchmarked against the live PostgreSQL database (427 documents).

### B. Measured Wall-Clock Latencies
Direct multi-request benchmarks were executed against the live endpoint across two evaluation runs (a 5-run benchmark including cold/pool warm-up, and a 3-run warm benchmark session):

| Run / Benchmark Session | Default `minWeight=0.1` | Unfiltered `minWeight=0.0` | Nodes | Edges (`minWeight=0.1`) | Edges (`minWeight=0.0`) | JSON Payload Size |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **5-Run Benchmark (Initial Cold/Warm)** | **10.287s** (range 7.618s–13.239s) | **7.157s** (range 6.007s–8.695s) | 4,699 | 9,858 | 34,902 | 4.41 MB / 15.67 MB |
| **3-Run Warm Session (Run 1)** | 6.489s | 5.833s | 4,699 | 9,858 | 34,902 | 4.41 MB / 15.67 MB |
| **3-Run Warm Session (Run 2)** | 6.240s | 5.754s | 4,699 | 9,858 | 34,902 | 4.41 MB / 15.67 MB |
| **3-Run Warm Session (Run 3)** | 5.914s | 5.711s | 4,699 | 9,858 | 34,902 | 4.41 MB / 15.67 MB |
| **Warm Session Mean** | **6.214s** | **5.766s** | 4,699 | 9,858 | 34,902 | 4.41 MB / 15.67 MB |

* **Comparison to Prior Baseline (~9.68s)**:
  - At default `minWeight=0.1`, multi-run mean latency averages **10.29s** over cold/warm cycles and **6.21s** when the database connection pool is warm.
  - At `minWeight=0.0`, assembly latency averages **7.16s** (and **5.77s** warm) returning 34,902 reconciled edges.
  - Removing 5,100 duplicate edges decreased the raw edge payload at `minWeight=0.0`, but did not meaningfully alter overall endpoint latency because edge generation is not the primary bottleneck.

### C. Profiling Scope Clarification
The initial phase-by-phase profiling breakdown reported in earlier documentation was executed specifically against **`minWeight=0.1`** (where Phase 8 pruned edges from 27,961 inter-entity and 6,941 mention edges down to 9,858 edges with `weight >= 0.1`). To avoid any juxtaposition ambiguity, both settings (`minWeight=0.1` and `minWeight=0.0`) have now been profiled separately with real `time.perf_counter()` timing brackets covering every internal stage of the request lifecycle.

### D. Granular Phase-by-Phase Profiling Breakdown (Measured Numbers Only)
Direct `time.perf_counter()` brackets were applied to all server-side assembly stages, plus Pydantic response validation and JSON serialization:

| Pipeline Stage | Description | `minWeight=0.1` (Default) | `minWeight=0.0` (Unfiltered) |
| :--- | :--- | :---: | :---: |
| **Phase 1: Database Query** | `SELECT id, original_filename, file_size, doc_metadata FROM documents` (427 rows) | 2.835s | 3.151s |
| **Phase 2: Mention Aggregation** | Extracting entity lists from `doc_metadata['entities']` | 0.009s | 0.010s |
| **Phase 3: Entity Resolution** | `EntityResolutionService.cluster_entities()` (DBSCAN + string distance) | 0.242s | 0.306s |
| **Phase 4: Document Traversal** | Remapping document nodes, canonical lookups, and link extraction | 1.013s | 1.003s |
| **Phase 5: Mentions Edge Synthesis** | Synthesizing 6,941 document-to-entity containment edges | 0.050s | 0.046s |
| **Phase 6: Inter-Entity Edge Synthesis** | Calibrating weights across 69,382 candidate entity pairs | 1.254s | 1.223s |
| **Phase 7: Centrality Calculation** | `CentralityService.apply_centrality_to_nodes()` | 0.038s | 0.040s |
| **Phase 8: Edge Threshold Filtering** | Pruning edges below `min_weight` threshold | 0.009s (to 9,858 edges) | 0.009s (to 34,902 edges) |
| **Subtotal: In-Memory Assembly (Phases 1–8)** | In-memory graph construction | **5.450s** | **5.788s** |
| **Phase 9a: Pydantic Validation** | `GraphResponse(nodes=..., edges=...)` validation & instantiation | **0.053s** | **0.144s** |
| **Phase 9b: JSON Serialization** | `resp_model.model_dump_json().encode('utf-8')` | **0.035s** (4.41 MB payload) | **0.102s** (15.67 MB payload) |
| **Total Measured In-Process Pipeline** | Phases 1 through 9b | **5.537s** | **6.033s** |

### E. Request Lifecycle Reconciliation
Comparing the directly measured in-process execution pipeline against client-observed HTTP roundtrip wall-clock times:

| Lifecycle Metric | `minWeight=0.1` (Default) | `minWeight=0.0` (Unfiltered) |
| :--- | :---: | :---: |
| **In-Memory Graph Assembly (Phases 1–8)** | 5.450s | 5.788s |
| **Pydantic Response Validation (Phase 9a)** | 0.053s | 0.144s |
| **JSON Response Body Serialization (Phase 9b)** | 0.035s | 0.102s |
| **Total Server In-Process Execution** | **5.537s** | **6.033s** |
| **Client-Observed HTTP Roundtrip (Warm Session Mean)** | **6.214s** | **5.766s** |
| **Client-Observed HTTP Roundtrip (5-Run Multi-Benchmark Mean)** | **10.287s** | **7.157s** |
| **Unaccounted Overhead vs. Warm Session Mean** | **+0.677s** | **-0.267s** (within DB run variance) |
| **Unaccounted Overhead vs. 5-Run Benchmark Mean** | **+4.750s** | **+1.124s** |

#### Reconciliation Findings:
1. **Pydantic Validation and JSON Serialization are negligible bottlenecks**:
   - For `minWeight=0.1` (4.41 MB JSON): Validation takes **0.053s** (53ms) and serialization takes **0.035s** (35ms) — combined under **0.09s**.
   - For `minWeight=0.0` (15.67 MB JSON): Validation takes **0.144s** (144ms) and serialization takes **0.102s** (102ms) — combined under **0.25s**.
   - Neither validation nor serialization explains the larger multi-second variance.
2. **True Source of the Unaccounted Latency Gap**:
   - In warm conditions, the server in-process pipeline (5.54s at `minWeight=0.1`, 6.03s at `minWeight=0.0`) accounts for almost the entire warm HTTP roundtrip (6.21s and 5.77s), leaving a modest unaccounted overhead of **+0.68s** at `minWeight=0.1` (which is ASGI middleware execution: `RequestIDMiddleware`, `CORSMiddleware`, JWT decode, and HTTP response socket chunk streaming).
   - The larger multi-second gap observed in broader benchmarks (reaching 10.29s mean at `minWeight=0.1`) is driven by **PostgreSQL connection pool acquisition latency and cold cache page fetching during Phase 1** (where database query time alone varies from 2.8s up to 6.3s across runs), not transport serialization. Any remaining discrepancy between in-process assembly and external HTTP roundtrip is explicitly: *unaccounted overhead, likely ASGI/HTTP transport, connection pool acquisition, and TCP socket chunking, not further profiled in this task*.

### F. Recommendations (No Implementation Required in This Task)
1. **Database Projection Optimization**: In a future optimization task, replace `SELECT doc_metadata` with PostgreSQL JSON operators (`doc_metadata->'entities'`, `doc_metadata->'graph_data'`) to extract only the graph-relevant keys rather than streaming full review summaries and pipeline logs for 427 documents.
2. **Server-Side Graph Materialization / Caching**: Precompute and cache the global canonical graph representation in Redis or a dedicated materialized table on document ingestion, rather than reconstructing 34,902 relationships on-the-fly for every HTTP request.
3. **Status**: Non-blocking for local prototype and evaluation demo purposes.

---

## 2. VerificationAgent Grounding Limitation Audit

### A. Architectural Mechanism
`VerificationAgent` ([backend/app/agents/verification.py](file:///c:/Users/under/OneDrive/Desktop/New-Legal1%20%282%29/New-Legal1%20%282%29/New-Legal1%20%281%29/New-Legal1/New-Legal/backend/app/agents/verification.py)) implements grounding verification via a token-overlap heuristic:
1. **Token Extraction**: Strips punctuation and extracts alphanumeric tokens via `\b\w+\b`.
2. **Stopword Stripping**: Removes a hardcoded set of 42 common words:
   ```python
   stopwords = {
       "the", "a", "an", "is", "are", "was", "were", "in", "on", "at",
       "to", "for", "of", "and", "or", "but", "not", "with", "this",
       "that", "it", "be", "as", "by", "from", "has", "had", "have",
       "will", "can", "may", "its", "no", "do", "if", "so", "all",
       "executive", "overview", "legal", "analysis", "evidence", "summary",
       "clause"
   }
   ```
3. **Hallucination Metric**:
   $$\text{hallucination\_ratio} = \frac{|\text{content\_summary} \setminus \text{content\_source}|}{|\text{content\_summary}|}$$
   - If ratio $> 0.50 \rightarrow$ `CRITICAL` issue logged.
   - If ratio $> 0.20 \rightarrow$ `MEDIUM` issue logged.
   - If ratio $\le 0.20 \rightarrow$ `is_valid = True`, no issue logged.
4. **Consistency Heuristic**: Checks only three hardcoded string pairs:
   `("not guilty", "guilty")`, `("innocent", "convicted")`, `("approved", "rejected")`.

### B. Inherent Failure Modes of Token Overlap (vs. Full NLI Entailment)
Because token overlap treats text as an unordered bag of tokens:
1. **Insensitivity to Polarity & Negation**: Words like `"not"` and `"no"` are explicitly defined as stopwords. Reversing an assertion from positive to negative does not introduce unsupported content tokens.
2. **Insensitivity to Word Order & Predicate Binding**: A statement asserting *"Alice sued Bob"* and *"Bob sued Alice"* share identical token sets.
3. **Blindness to Semantic Inversion**: Replacing a single verb (e.g. *"admitted"* with *"denied"*) introduces only 1 unsupported token out of a 15–20 word sentence ($\approx 5\%$), remaining far below the $20\%$ issue threshold.

### C. Concrete System Verification with Real Output

The live `VerificationAgent` was tested with concrete legal scenarios:

#### Test Case 1: Missed Grounding Contradiction (The Limitation)
* **Source Text**:
  > *"In the Q3 regulatory compliance review, Enron energy traders explicitly admitted that California power schedules were intentionally manipulated to induce artificial transmission congestion."*
* **Contradictory Summary A (Reversed Meaning: "denied" vs "admitted")**:
  > *"In the Q3 regulatory compliance review, Enron energy traders explicitly denied that California power schedules were intentionally manipulated to induce artificial transmission congestion."*
  * **Real Agent Output**:
    - `is_valid`: **`True`** (Incorrectly validated)
    - `hallucination_score`: **`0.0556`** (5.56% — well below the 20% detection threshold)
    - `issues detected`: **`0`**
* **Contradictory Summary B (Syntactic Negation: "were not involved in")**:
  > *"In the Q3 regulatory compliance review, Enron energy traders were not involved in manipulating California power schedules to induce artificial transmission congestion."*
  * **Real Agent Output**:
    - `is_valid`: **`True`** (Incorrectly validated)
    - `hallucination_score`: **`0.1250`** (12.5% — well below the 20% detection threshold)
    - `issues detected`: **`0`**

*Evaluation Result*: The summary asserts the exact opposite of the source document, completely exonerating individuals who admitted guilt, yet passes verification as 100% valid because almost all tokens match the source text.

---

#### Test Case 2: Correctly Caught Grounding Failure (What Token Overlap Does Catch)
To maintain an honest, balanced assessment, the agent was tested on a genuine factual hallucination introducing external entities:
* **Source Text**:
  > *"Enron Wholesale Services reported quarterly revenues of $400 million from domestic natural gas contracts."*
* **Hallucinated Summary**:
  > *"Enron Wholesale Services acquired Swiss biotech pharmaceutical startup Cytovance for $2 billion in Zurich offshore accounts."*
  * **Real Agent Output**:
    - `is_valid`: **`False`** (Correctly invalidated)
    - `hallucination_score`: **`0.7857`** (78.6%)
    - `issues detected`: **`1`**
    - `Issue Details`:
      - **Severity**: `CRITICAL`
      - **Type**: `hallucination`
      - **Description**: *"High hallucination detected: 79% of summary terms not found in source."*
      - **Evidence**: *"Unsupported terms: startup, biotech, cytovance, billion, accounts"*

*Evaluation Result*: Token overlap successfully catches ungrounded facts, foreign entities, and external fabrications that introduce unseen vocabulary.

### D. Recommendations (No Implementation Required in This Task)
1. **Role of Token Overlap**: Token overlap is an effective, zero-cost, low-latency filter for catching completely ungrounded hallucinations and out-of-context entity injections.
2. **Requirement for True Grounding**: In high-stakes legal e-discovery where affirmative vs. negative statements determine culpability, token overlap is fundamentally insufficient to guarantee semantic alignment.
3. **Future Architecture**: Implementing a true Natural Language Inference (NLI) cross-encoder (such as `DeBERTa-v3-large-mnli`) or a calibrated Gemini LLM verification prompt is the appropriate architectural remediation, deferred in the present iteration under zero-cost / local-compute constraints.
