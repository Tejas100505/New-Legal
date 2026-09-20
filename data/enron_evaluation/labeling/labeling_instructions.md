# Human Labeling Protocol: Enron Evaluation Dataset

## 1. Overview & Objective
This labeling project establishes an **independent, human-verified ground-truth dataset** for evaluating the e-discovery pipeline's accuracy, precision, recall, and F1-score across:
- **Document Relevance** (Classification / Scope)
- **Legal Privilege** (Attorney-Client Privilege / Work Product Doctrine)

> [!IMPORTANT]
> **Zero Pre-Filled Labels**: All ground-truth columns (`is_relevant`, `is_privileged`, `notes`) must be entered exclusively by human reviewers. AI predictions are never merged into these columns to prevent circular evaluation.

---

## 2. Google Sheets Setup & Validation Guide

The CSV files in `data/enron_evaluation/labeling/` are formatted with UTF-8 BOM (`utf-8-sig`) and single-line previews for clean display in Google Sheets or Microsoft Excel.

### Quick Setup in Google Sheets:
1. Open [Google Sheets](https://sheets.new).
2. Go to **File > Import > Upload** and select `labeling_template_val.csv` (or `train.csv` / `test.csv`).
3. Select **Import location**: *Replace spreadsheet*, **Separator type**: *Comma*.
4. **Data Validation for Columns `is_relevant` (Column J) and `is_privileged` (Column K)**:
   - Select Column J (from row 2 down to the last row).
   - Go to **Data > Data validation > Add rule**.
   - Under **Criteria**, choose **Dropdown** (or **Checkbox**).
   - Enter values:
     - `TRUE` (Background color: Soft Green)
     - `FALSE` (Background color: Soft Red)
   - Repeat for Column K (`is_privileged`).
5. **Reviewer Assignment**:
   - Column M (`reviewer`): Enter your reviewer handle (e.g. `Reviewer 1`, `Reviewer 2`, `Reviewer 3`).
   - Column N (`reviewed_at`): Enter review date (e.g. `2026-09-06`).

---

## 3. Ground Truth Definitions

### A. Case Relevance Standard (`is_relevant`)
The hypothetical investigation scenario is:
> **"SEC & FERC Investigation into Enron Commercial Operations, Pipeline Capacity Allocations, Regulatory Inquiries, and Executive Correspondence (1999–2002)."**

- **Mark `TRUE` if the document discusses**:
  - Commercial contracts, energy trading deals, pipeline transport agreements, or customer commitments.
  - California energy crisis, regulatory filings, FERC/SEC subpoenas, or compliance inquiries.
  - Senior executive communications (Ken Lay, Jeff Skilling, Mark Frevert, etc.) regarding company policy, transactions, or accounting disputes.
  - Internal audits, operational discrepancies, or litigation risks.
- **Mark `FALSE` if the document is purely**:
  - Personal correspondence, lunch arrangements, sports pools, or personal greetings.
  - Automated spam, generic newsletters, industry PR digests, or computer system maintenance notices.

### B. Legal Privilege Standard (`is_privileged`)
Under Federal Rule of Evidence 502 and federal common law:

- **Mark `TRUE` only if**:
  - The communication is between a client/employee and legal counsel (in-house or outside attorneys such as Vinson & Elkins, Bracewell & Patterson).
  - The communication was kept confidential.
  - The **primary purpose** is seeking, rendering, or discussing substantive legal advice, or it constitutes Attorney Work-Product prepared in anticipation of litigation.
- **Mark `FALSE` if**:
  - An attorney is merely carbon-copied (CC'd) on a business email with no legal advice sought or provided.
  - The attorney is acting in a purely business, commercial, or administrative capacity (e.g., signing a routine non-disclosure agreement as a corporate officer).
  - Standard non-disclosure / commercial confidentiality agreements (confidential != legally privileged).

---

## 4. Team Workflow for 3-Person Team

| Reviewer | Phase 1: Validation Set (60 rows) | Phase 2: Test Set (60 rows) | Phase 3: Train Set (280 rows) |
|---|---|---|---|
| **Reviewer 1 (Lead)** | Rows 1–30 | Rows 1–30 | Rows 1–95 |
| **Reviewer 2** | Rows 31–60 | Rows 31–60 | Rows 96–190 |
| **Reviewer 3** | Dual-review 20 overlap rows for Inter-Annotator Agreement | Dual-review 20 overlap rows | Rows 191–280 |

### Dual Review & Fleiss' Kappa:
To ensure scientific rigor, Reviewer 3 should independently label an overlap subset of 20 emails from each split. This allows the system to compute Cohen's / Fleiss' Kappa ($\kappa$) inter-annotator agreement before freezing the ground truth.
