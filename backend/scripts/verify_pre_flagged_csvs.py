"""
Verify Pre-Flagged CSVs and Display 5 Real Example Rows
"""

import os
import csv
import json

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(BASE_DIR, "data", "enron_evaluation")
LABELING_DIR = os.path.join(DATA_DIR, "labeling")

def main():
    csv_files = [
        "labeling_template_train.csv",
        "labeling_template_val.csv",
        "labeling_template_test.csv",
        "labeling_template_all.csv",
    ]

    print("=" * 80)
    print("VERIFYING PRE-FLAGGED CSV TEMPLATES & GROUND TRUTH BLANKNESS")
    print("=" * 80)

    # ── Check 1: Strict Ground-Truth Purity across all files ───────────────
    for fname in csv_files:
        fpath = os.path.join(LABELING_DIR, fname)
        with open(fpath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            for i, r in enumerate(rows, 1):
                assert r["is_relevant"] == "", f"Ground truth is_relevant not empty at {fname}:{i} -> '{r['is_relevant']}'"
                assert r["is_privileged"] == "", f"Ground truth is_privileged not empty at {fname}:{i} -> '{r['is_privileged']}'"
                assert r["notes"] == "", f"Ground truth notes not empty at {fname}:{i} -> '{r['notes']}'"
                assert r["reviewer"] == "", f"Reviewer not empty at {fname}:{i}"
                assert r["reviewed_at"] == "", f"Reviewed_at not empty at {fname}:{i}"
        print(f"  [OK] {fname}: All {len(rows)} rows have 100% BLANK ground truth fields.")

    # ── Check 2: Display 5 Diverse Example Rows ───────────────────────────
    all_path = os.path.join(LABELING_DIR, "labeling_template_all.csv")
    with open(all_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)

    # Select 5 illustrative rows:
    # 1. High-confidence relevant + needs privilege review
    # 2. High-confidence relevant + no privilege review
    # 3. Low-confidence relevant (1 term) + no privilege
    # 4. Low-confidence relevant + needs privilege
    # 5. Non-relevant (0 terms) + no privilege review
    examples = []
    for r in all_rows:
        if r["suggested_relevant"] == "TRUE" and r["suggestion_confidence"] == "high" and r["needs_privilege_review"] == "TRUE":
            examples.append(("High-Conf Relevant & Needs Privilege Review", r))
            break

    for r in all_rows:
        if r["suggested_relevant"] == "TRUE" and r["suggestion_confidence"] == "high" and r["needs_privilege_review"] == "FALSE":
            examples.append(("High-Conf Relevant & No Privilege Review", r))
            break

    for r in all_rows:
        if r["suggested_relevant"] == "TRUE" and r["suggestion_confidence"] == "low" and r["needs_privilege_review"] == "FALSE":
            examples.append(("Low-Conf Relevant (Single Keyword) & No Privilege", r))
            break

    for r in all_rows:
        if r["suggested_relevant"] == "FALSE" and r["needs_privilege_review"] == "TRUE":
            examples.append(("Non-Relevant but Contains Legal/Privilege Mention", r))
            break

    for r in all_rows:
        if r["suggested_relevant"] == "FALSE" and r["needs_privilege_review"] == "FALSE":
            examples.append(("Completely Non-Relevant & Routine (Fast-Triage)", r))
            break

    print("\n" + "=" * 80)
    print("5 REAL EXAMPLE ROWS WITH SUGGESTIONS FILLED IN")
    print("=" * 80)

    for i, (label, r) in enumerate(examples, 1):
        print(f"\n--- EXAMPLE {i}: {label} ---")
        print(f"  Document ID:             {r['document_id']} ({r['split'].upper()})")
        print(f"  Custodian:               {r['custodian']}")
        print(f"  Subject:                 {r['subject']}")
        print(f"  Text Preview:            {r['text_preview'][:160]}...")
        print(f"  [GROUND TRUTH] is_relevant:   '{r['is_relevant']}' (EMPTY FOR HUMAN REVIEW)")
        print(f"  [GROUND TRUTH] is_privileged: '{r['is_privileged']}' (EMPTY FOR HUMAN REVIEW)")
        print(f"  [GROUND TRUTH] notes:         '{r['notes']}' (EMPTY FOR HUMAN REVIEW)")
        print(f"  >> suggested_relevant:        {r['suggested_relevant']}")
        print(f"  >> suggestion_confidence:     {r['suggestion_confidence']}")
        print(f"  >> suggested_relevance_terms: [{r['suggested_relevance_terms']}]")
        print(f"  >> needs_privilege_review:    {r['needs_privilege_review']}")
        print(f"  >> suggested_privilege_terms: [{r['suggested_privilege_terms']}]")

    print("\n" + "=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
