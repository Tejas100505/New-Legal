# Evaluation Methodology Notes & Evidence-Based Caveats

> **Notice & Purpose**: This document is internal working documentation to inform the eventual report rewrite. It provides an empirical audit of the evaluation methodology, chronological relationship between pipeline fixes and evaluation benchmarks, and statistical limitations of the reported performance metrics. It does NOT alter any system code, evaluation scripts, or stored database metrics.

---

## Evidence Source Note

* **Source of Chronological Evidence**: Chronological findings in this document are derived from IDE conversation transcripts, tool execution logs with ISO timestamps, and direct code/data inspection.
* **Absence of Git Repository**: No `.git` version control repository exists within this project workspace (the directory structure reflects an unzipped/copied working tree). Standard `git log` and `git blame` histories were unavailable.
* **Scope & Inherent Limitations**: The chronological evidence relies on recorded IDE session logs from June through September 2026—specifically session `485ea7fc-b92c-4570-8af3-eeb1785701fd` on 2026-09-06, which captured the initial evaluation runs, failure analyses, user requests, code modifications, and immediate re-evaluations verbatim. Any unrecorded activity or offline manual edits outside these recorded sessions, if any occurred, could not be independently reviewed.

---

## Executive Summary

A methodological audit was conducted on two headline evaluation results in the **Agentic AI for E-Discovery & Legal Review** project:
1. **Privilege Detection Hybrid F1 = 1.0000** (Precision 1.0000, Recall 1.0000) on the 24-document synthetic benchmark.
2. **Relevance Retrieval Hybrid F1 = 0.6842** (Precision 0.7647, Recall 0.6190, Combined) and **Test Recall = 1.0000** on the 400-document Enron evaluation dataset.

### Core Findings
1. **Direct Tuning on the Evaluation Sets Confirmed**: Empirical audit of the development trajectory confirms that both the privilege routing/term fixes and the California ISO (`CAISO_OPERATIONAL_PATTERNS`) retrieval boost were developed in direct response to specific failures identified during evaluation on the exact same benchmarks they are now scored against.
2. **Small-Sample Fragility in Retrieval Splits**: Across the 400-document Enron evaluation dataset, exactly **21 documents (5.25%)** are truly relevant under human ground-truth labels. The `test` split contains only **3 positive documents**, and the `val` split contains only **3 positive documents**. Consequently, the reported headline metric of "Test Recall = 1.0000" reflects retrieving exactly 3 out of 3 documents, where a single missed document swings recall by 33.33 percentage points.
3. **Absence of Independent Held-Out Benchmark**: No independent, unexposed, human-labeled evaluation dataset exists within the repository. Generating synthetic held-out data using an LLM was rejected to preserve Ground-Truth Purity (Rule 6).

---

## 1. Chronological Audit: Pipeline Fixes vs. Evaluation Benchmarks (Step 1)

An empirical audit of the project trajectory was conducted to determine whether fixes were added for general reasons or tuned specifically against benchmark failures.

### A. Privilege Detection: Disclaimer Routing & Term List Expansion

* **Component**: `backend/app/agents/privilege.py` (`AMBIGUOUS_LEGAL_TERMS`, `DISCLAIMER_PATTERNS`, `_is_match_in_disclaimer_or_footer`).
* **Target Benchmark**: `data/synthetic_privilege_benchmark.csv` (24 documents: 12 true privilege cases, 12 hard negatives).

#### Empirical Chronology
1. **Initial Evaluation Run**: On 2026-09-06, the full evaluation script (`backend/scripts/run_full_evaluation.py`) was executed on the 24-document synthetic privilege benchmark.
2. **Identified Failure Modes**:
   - **False Positive on `synth_priv_0020`**: A public corporate press release ("Zenith Financial Corp") contained a standard boilerplate confidentiality disclaimer footer ("CONFIDENTIALITY NOTICE: Attorney-Client Privileged / Work Product..."). The first-pass regex (`STRONG_PRIVILEGE_PATTERNS`) matched `"attorney-client privileged"` and short-circuited in Path 1 as an automatic True Positive without invoking Gemini LLM review.
   - **False Negative on `synth_priv_009`**: An internal antitrust legal assessment from outside counsel ("Miriam Goldstein, Antitrust Practice Group Leader, Goldstein & Partners LLP") lacked the explicit words `"attorney"` or `"lawyer"`. Because `"partner"` and `"law firm"` were absent from `AMBIGUOUS_LEGAL_TERMS`, the document registered zero legal signals and was classified non-privileged in Path 3 without reaching the LLM.
3. **Targeted Implementation**: On 2026-09-06, targeted code changes were introduced:
   - Added `_is_match_in_disclaimer_or_footer()` and `DISCLAIMER_PATTERNS` to detect boilerplate blocks and route disclaimer matches to Path 2/LLM reasoning instead of short-circuiting.
   - Expanded `AMBIGUOUS_LEGAL_TERMS` to include `\b(partner|associate|law\s+firm|llp|p\.c\.|legal\s+group|legal\s+department)\b`.
   - Created `backend/scripts/test_privilege_fixes.py` specifically hardcoded to test these two benchmark documents (`target_ids = ["synth_priv_0020", "synth_priv_009"]`).
4. **Re-Evaluation on the Same 24 Documents**: The full evaluation was immediately re-run on the exact same 24-document benchmark, resulting in:
   - `TP = 12, FP = 0, TN = 12, FN = 0`
   - `Precision = 1.0000, Recall = 1.0000, F1 = 1.0000`

#### Chronological Finding
The privilege F1 = 1.0000 metric was achieved by **direct iterative remediation against the failure cases of that exact 24-document benchmark**. While the architectural mechanism (routing ambiguous footers and law firm roles to LLM contextual review) is technically sound, the resulting 1.0000 F1 score reflects successful tuning against known failure cases rather than proven generalization across unseen legal documents.

---

### B. Retrieval Relevance: California ISO Operational Boost

* **Component**: `backend/app/agents/retrieval.py` (`CAISO_OPERATIONAL_PATTERNS`, `final_score += 0.25`).
* **Target Benchmark**: `data/enron_evaluation/labeling/labeling_template_all_FINAL.csv` (400 human-labeled Enron emails).

#### Empirical Chronology
1. **Initial Evaluation Run**: On 2026-09-06, retrieval was evaluated against the scenario query:
   > *"California energy market practices, pricing, regulatory communications, and trading strategy"*
2. **Identified Failure Mode**:
   - The initial run yielded 10 false negatives. As documented in the initial evaluation analysis:
     > *"6 of the 10 false negatives in Enron are automated hourly scheduling logs (e.g., `enron_train_001_guzman-m`, `enron_train_023_guzman-m`). Human reviewers deemed them relevant because they represent real California ISO hour-ahead market schedules. However, because these emails consist of tabular numbers and code abbreviations rather than natural language, standard text embeddings and BM25 assigned them low semantic similarity scores (~0.23)."*
3. **Targeted Implementation**: On 2026-09-06, `CAISO_OPERATIONAL_PATTERNS` was introduced directly into `retrieval.py`:
   ```python
   CAISO_OPERATIONAL_PATTERNS = [
       re.compile(r"\bhourahead\s+hour\b", re.IGNORECASE),
       re.compile(r"\bcaiso\s+notif", re.IGNORECASE),
       re.compile(r"\bcaiso\s+notice", re.IGNORECASE),
       re.compile(r"\bstart\s+date:.*hourahead", re.IGNORECASE),
       re.compile(r"\bcongestion\s+management\s+reform\b", re.IGNORECASE),
       re.compile(r"\bcmr\s+stakeholder\b", re.IGNORECASE),
       re.compile(r"\bprotest\s+to\s+(?:cal\s*)?px\b", re.IGNORECASE),
   ]
   ```
   If any pattern matches, a hardcoded bonus of `+0.25` is added to `final_score`.
4. **Pattern Specificity**: Every single pattern in `CAISO_OPERATIONAL_PATTERNS` corresponds to exact phrases in specific documents in the 400-document set:
   - `\bhourahead\s+hour\b` and `\bstart\s+date:.*hourahead` $\rightarrow$ `enron_train_001`, `023`, `032`, `130`, `203`, and `enron_test_039`.
   - `\bcaiso\s+notif` $\rightarrow$ `enron_val_021`.
   - `\bcaiso\s+notice` and `\bcongestion\s+management\s+reform\b` $\rightarrow$ `enron_train_089`.
   - `\bcmr\s+stakeholder\b` $\rightarrow$ `enron_train_186`.
   - `\bprotest\s+to\s+(?:cal\s*)?px\b` $\rightarrow$ `enron_train_092`.
5. **Re-Evaluation on the Same 400 Documents**: Re-running the evaluation on the same 400 documents lifted these scheduling logs above the decision threshold (0.48), yielding headline metrics:
   - Combined: `Precision = 0.7647, Recall = 0.6190, F1 = 0.6842`
   - Test Split: `Precision = 0.5000, Recall = 1.0000, F1 = 0.6667`

#### Chronological Finding
The CAISO operational boost was **formulated directly from the text of false negatives identified in the 400-document Enron dataset and re-scored on that same dataset**. The boost functions as a domain-specific rule-based prior, but its measured contribution cannot be cited as unassisted semantic retrieval generalization.

---

## 2. Statistical Analysis & Small-Sample Fragility (Step 2)

### A. Ground-Truth Distribution Across Splits

Querying the authoritative human-reviewed labels in `data/enron_evaluation/labeling/labeling_template_all_FINAL.csv` yields the following exact counts:

| Split | Total Documents | Truly Relevant ($N_{pos}$) | Irrelevant ($N_{neg}$) | Prevalence (%) |
| :--- | :---: | :---: | :---: | :---: |
| **Train** | 280 | 15 | 265 | 5.36% |
| **Validation** | 60 | 3 | 57 | 5.00% |
| **Test** | 60 | 3 | 57 | 5.00% |
| **Total (Combined)** | **400** | **21** | **379** | **5.25%** |

### B. Positive Document Identifiers

* **Train Split ($N=15$)**: `enron_train_001_guzman-m`, `enron_train_023_guzman-m`, `enron_train_032_guzman-m`, `enron_train_055_hain-m`, `enron_train_066_badeer-r`, `enron_train_085_hain-m`, `enron_train_089_badeer-r`, `enron_train_092_hain-m`, `enron_train_102_scholtes-d`, `enron_train_130_guzman-m`, `enron_train_186_badeer-r`, `enron_train_190_guzman-m`, `enron_train_192_whalley-g`, `enron_train_203_guzman-m`, `enron_train_273_badeer-r`.
* **Validation Split ($N=3$)**: `enron_val_014_hain-m`, `enron_val_021_badeer-r`, `enron_val_055_badeer-r`.
* **Test Split ($N=3$)**: `enron_test_007_hain-m`, `enron_test_011_whalley-g`, `enron_test_039_guzman-m`.

### C. Prevalence of CAISO Operational Matches
Across the 21 ground-truth positive documents:
- **10 of 21 (47.6%)** match `CAISO_OPERATIONAL_PATTERNS` and receive the `+0.25` bonus:
  - Train: 8 of 15 (53.3%)
  - Validation: 1 of 3 (33.3%) — `enron_val_021_badeer-r`
  - Test: 1 of 3 (33.3%) — `enron_test_039_guzman-m`

### D. Fragility Analysis for Split-Level Metrics

The headline result **"Test Recall = 1.0000"** is based on exactly **3 positive documents**:
1. `enron_test_007_hain-m` (natural language text on conference restructuring)
2. `enron_test_011_whalley-g` (natural language news report on utility rate increase)
3. `enron_test_039_guzman-m` (tabular hour-ahead log rescued by `CAISO_OPERATIONAL_PATTERNS`)

#### Mathematical Sensitivity
* **3 of 3 retrieved** $\rightarrow$ Recall = **1.0000 (100.0%)** (Current reported result)
* **2 of 3 retrieved** $\rightarrow$ Recall = **0.6667 (66.7%)** (Drop of 33.33 percentage points from 1 error)
* **1 of 3 retrieved** $\rightarrow$ Recall = **0.3333 (33.3%)** (Drop of 66.67 percentage points from 2 errors)

Furthermore, in the test split:
* $\text{TP} = 3$
* $\text{FP} = 3$ (`enron_test_008_badeer-r`, `enron_test_028_hain-m`, `enron_test_052_presto-k`)
* $\text{Precision} = \frac{3}{3 + 3} = 0.5000$ (50.0%)
* $\text{F1} = 2 \times \frac{0.5000 \times 1.0000}{0.5000 + 1.0000} = 0.6667$

In the validation split:
* $\text{TP} = 1$ (`enron_val_021_badeer-r`)
* $\text{FN} = 2$ (`enron_val_014_hain-m`, `enron_val_055_badeer-r`)
* $\text{Recall} = \frac{1}{3} = 0.3333$ (33.3%)
* $\text{Precision} = 1.0000$ (1 TP, 0 FP)
* $\text{F1} = 0.5000$

#### Statistical Conclusion
Split-level metrics where $N_{pos} = 3$ exhibit extreme discrete volatility. A single false negative in the test set causes a 33.3% swing in recall. Reporting "100% recall" without disclosing that it is derived from 3 documents creates a false impression of ceiling performance.

---

## 3. Investigation of Held-Out Evaluation Feasibility (Step 3)

### A. Repository & Corpus Audit
An exhaustive search of all repository directories (`data/`, `uploads/`, `backend/uploads/`, database tables) confirmed:
1. **Document Storage**: All 427 documents in the active database consist exclusively of:
   - 400 Enron emails from the evaluation subset (`data/enron_evaluation/raw_emails`).
   - 24 synthetic privilege benchmark documents (`data/synthetic_cases/`).
   - 3 legacy or test upload artifacts without independent ground-truth annotations.
2. **Label Availability**: No independent, unexposed, human-verified legal ground truth exists in the codebase outside `labeling_template_all_FINAL.csv` and `synthetic_privilege_benchmark.csv`.

### B. Adherence to Ground-Truth Purity (Rule 6)
* **Constraint**: Standing Rule #6 mandates: *"Never let an AI system generate its own evaluation labels; human labeling is required for ground truth."*
* **Decision**: Generating a new synthetic dataset or using Gemini to auto-label unseen emails from the broader CMU Enron archive would violate Rule 6 and fabricate a pseudo-validation.
* **Finding**: **No genuinely held-out, human-labeled dataset is available within the scope of this repository.** Stating this absence plainly and transparently is methodologically honest and preserves scientific integrity.

---

## 4. Recommendations for Eventual Report Rewrite (Step 4)

When drafting the final report in subsequent tasks, the following presentation standards must be maintained:

### 1. Frame Fixes as Domain-Specific Engineering Enhancements
* **Do**: Describe the privilege disclaimer filter and term list expansion as necessary architectural refinements that correctly handle standard legal correspondence patterns (e.g. distinguishing substantive advice from boilerplate footers and recognizing law firm titles).
* **Do**: Describe `CAISO_OPERATIONAL_PATTERNS` as an evidence-based hybrid retrieval prior designed to capture structured/tabular scheduling logs that inherently fail semantic embedding similarity.

### 2. State Metrics as "Tuning-Set / Benchmark-Calibrated"
* **Do Not**: Present F1 = 1.0000 (privilege) or F1 = 0.6842 / Test Recall = 1.0000 (retrieval) as evidence of unconstrained generalization to unseen documents.
* **Do**: Explicitly note that these figures were measured on the benchmark sets following iterative remediation of observed failure modes.

### 3. Disclose Sample Sizes & Low Prevalence Transparently
* **Do**: Accompany every split-level metric with sample sizes:
  > *"In the test split ($N=60$), exactly 3 documents are relevant under ground truth (5.0% prevalence). The retrieval pipeline retrieved all 3 ($R = 1.0000, P = 0.5000, F1 = 0.6667$), with 1 of the 3 retrieved via the CAISO operational pattern boost."*
* **Do**: State the discrete sensitivity: *"Given $N_{pos}=3$, each document represents 33.3% of the split's recall."*

### 4. Maintain Full Baseline Comparisons
* **Do**: Report the hybrid retrieval performance alongside the keyword-only BM25 baseline ($F1 = 0.3662, P = 0.2600, R = 0.6190$) to honestly demonstrate relative lift over uncalibrated search without overclaiming absolute perfection.
