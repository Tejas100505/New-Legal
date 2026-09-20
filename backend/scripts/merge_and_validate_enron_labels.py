"""
Merge and Validate Enron Human Labeling CSV Files

Requirements:
1. Merge into labeling_template_all_FINAL.csv, preserving:
   document_id, split, original content columns, suggestion columns,
   and the human-filled is_relevant/is_privileged/notes columns.
2. Validate:
   - Exactly 400 unique document_ids, no duplicates
   - No missing is_relevant or is_privileged values
   - TRUE/FALSE values normalized and consistent (strip, uppercase)
   - is_privileged = TRUE never occurs where is_relevant = FALSE (flag specific document_id, don't silently fix)
   - Split counts still exactly 60 val / 60 test / 280 train
   - No accidental edits to original email content/subject columns (compare against backup)
3. Identify and list exact document_id(s) marked is_privileged = TRUE
4. Compare final human labels against suggested_relevant column:
   - Report agreement rate
   - List specific document_ids where human overrode suggestion (both directions)
"""

import os
import csv
import sys
import glob

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LABELING_DIR = os.path.join(BASE_DIR, "data", "enron_evaluation", "labeling")
BACKUP_DIR = os.path.join(LABELING_DIR, "_backup_before_merge")
FINAL_OUT_PATH = os.path.join(LABELING_DIR, "labeling_template_all_FINAL.csv")

FILES_TO_PROCESS = [
    ("val", "labeling_template_val.csv", 60),
    ("test", "labeling_template_test.csv", 60),
    ("train", "labeling_template_train.csv", 280),
]

CONTENT_COLUMNS = ["filename", "custodian", "date", "sender", "recipient", "subject", "text_preview"]

def normalize_bool_val(raw_val: str, field_name: str, doc_id: str):
    if raw_val is None:
        raise ValueError(f"Missing value for {field_name} in doc {doc_id}")
    cleaned = str(raw_val).strip()
    if not cleaned:
        raise ValueError(f"Empty/blank value for {field_name} in doc {doc_id}")
    upper = cleaned.upper()
    if upper in ("TRUE", "1", "T", "YES"):
        return "TRUE"
    elif upper in ("FALSE", "0", "F", "NO"):
        return "FALSE"
    else:
        raise ValueError(f"Unrecognized boolean value '{raw_val}' for {field_name} in doc {doc_id}")

def get_latest_backup_file(pattern: str) -> str:
    matches = glob.glob(os.path.join(BACKUP_DIR, pattern))
    if not matches:
        raise FileNotFoundError(f"No backup file found matching {pattern} in {BACKUP_DIR}")
    matches.sort(reverse=True)
    return matches[0]

def main():
    print("=" * 80)
    print("ENRON HUMAN LABELS MERGE & VALIDATION")
    print("=" * 80)

    # 1. Load backup files to verify content integrity
    backup_records = {}
    for split_key, fname, expected_count in FILES_TO_PROCESS:
        base_prefix = fname.replace(".csv", "")
        backup_file = get_latest_backup_file(f"{base_prefix}_*.csv")
        print(f"Loading reference backup for {split_key}: {backup_file}")
        with open(backup_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                backup_records[row["document_id"]] = row

    print(f"Total backup records loaded: {len(backup_records)}")

    # 2. Process and validate labeled files
    all_rows = []
    doc_ids_seen = set()
    split_counts = {"train": 0, "val": 0, "test": 0}
    content_discrepancies = []
    logical_rule_violations = []
    missing_value_violations = []
    privileged_docs = []

    # Agreement tracking
    total_docs = 0
    agreement_matches = 0
    human_true_sugg_false = []  # Human added relevance (override suggestion FALSE -> TRUE)
    human_false_sugg_true = []  # Human rejected relevance (override suggestion TRUE -> FALSE)

    fieldnames = None

    for split_key, fname, expected_count in FILES_TO_PROCESS:
        fpath = os.path.join(LABELING_DIR, fname)
        if not os.path.exists(fpath):
            raise FileNotFoundError(f"Labeled file not found: {fpath}")

        print(f"\nProcessing {fname} (expected {expected_count} rows)...")
        with open(fpath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if fieldnames is None:
                fieldnames = list(reader.fieldnames)
            
            rows = list(reader)
            print(f"  Read {len(rows)} rows from {fname}")

            if len(rows) != expected_count:
                print(f"  [WARNING/ERROR] Expected {expected_count} rows but got {len(rows)} in {fname}!")

            for row in rows:
                doc_id = row.get("document_id", "").strip()
                split = row.get("split", "").strip()

                # Duplicate check
                if doc_id in doc_ids_seen:
                    raise ValueError(f"DUPLICATE document_id detected: {doc_id}")
                doc_ids_seen.add(doc_id)

                if split in split_counts:
                    split_counts[split] += 1
                else:
                    split_counts[split] = 1

                # Missing values check & normalization
                raw_rel = row.get("is_relevant")
                raw_priv = row.get("is_privileged")

                try:
                    norm_rel = normalize_bool_val(raw_rel, "is_relevant", doc_id)
                except ValueError as e:
                    missing_value_violations.append(str(e))
                    norm_rel = str(raw_rel).strip()

                try:
                    norm_priv = normalize_bool_val(raw_priv, "is_privileged", doc_id)
                except ValueError as e:
                    missing_value_violations.append(str(e))
                    norm_priv = str(raw_priv).strip()

                # Normalize in place for final export
                row["is_relevant"] = norm_rel
                row["is_privileged"] = norm_priv

                # Rule check: is_privileged == TRUE never occurs where is_relevant == FALSE
                if norm_priv == "TRUE" and norm_rel == "FALSE":
                    logical_rule_violations.append({
                        "document_id": doc_id,
                        "split": split,
                        "subject": row.get("subject", ""),
                        "notes": row.get("notes", "")
                    })

                if norm_priv == "TRUE":
                    privileged_docs.append({
                        "document_id": doc_id,
                        "split": split,
                        "is_relevant": norm_rel,
                        "subject": row.get("subject", ""),
                        "sender": row.get("sender", ""),
                        "recipient": row.get("recipient", ""),
                        "notes": row.get("notes", "")
                    })

                # Content tampering check against backup
                if doc_id in backup_records:
                    bak_row = backup_records[doc_id]
                    for ccol in CONTENT_COLUMNS:
                        val_curr = row.get(ccol, "")
                        val_bak = bak_row.get(ccol, "")
                        if val_curr != val_bak:
                            content_discrepancies.append({
                                "document_id": doc_id,
                                "column": ccol,
                                "backup_val": val_bak[:50],
                                "current_val": val_curr[:50]
                            })

                # Agreement comparison against suggested_relevant
                raw_sugg = row.get("suggested_relevant")
                norm_sugg = normalize_bool_val(raw_sugg, "suggested_relevant", doc_id) if raw_sugg else "FALSE"
                
                total_docs += 1
                if norm_rel == norm_sugg:
                    agreement_matches += 1
                else:
                    if norm_sugg == "TRUE" and norm_rel == "FALSE":
                        human_false_sugg_true.append({
                            "document_id": doc_id,
                            "split": split,
                            "subject": row.get("subject", ""),
                            "suggested_terms": row.get("suggested_relevance_terms", ""),
                            "notes": row.get("notes", "")
                        })
                    elif norm_sugg == "FALSE" and norm_rel == "TRUE":
                        human_true_sugg_false.append({
                            "document_id": doc_id,
                            "split": split,
                            "subject": row.get("subject", ""),
                            "suggested_terms": row.get("suggested_relevance_terms", ""),
                            "notes": row.get("notes", "")
                        })

                all_rows.append(row)

    # 3. Write merged FINAL CSV
    print(f"\nWriting merged {len(all_rows)} rows to {FINAL_OUT_PATH}...")
    with open(FINAL_OUT_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"Successfully wrote {FINAL_OUT_PATH} ({os.path.getsize(FINAL_OUT_PATH)} bytes)")

    # 4. Report Validation Results
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print(f"Total Unique Document IDs: {len(doc_ids_seen)} (Expected 400)")
    print(f"Duplicates: {400 - len(doc_ids_seen) if len(all_rows) != len(doc_ids_seen) else 0}")
    print(f"Split counts: Train={split_counts.get('train', 0)} (exp 280), Val={split_counts.get('val', 0)} (exp 60), Test={split_counts.get('test', 0)} (exp 60)")
    print(f"Missing Value Violations: {len(missing_value_violations)}")
    if missing_value_violations:
        for m in missing_value_violations:
            print(f"  - {m}")

    print(f"Content Column Discrepancies vs Backup: {len(content_discrepancies)}")
    if content_discrepancies:
        for cd in content_discrepancies:
            print(f"  - {cd['document_id']} col '{cd['column']}': '{cd['backup_val']}' vs '{cd['current_val']}'")

    print(f"Logical Rule Violations (is_privileged=TRUE with is_relevant=FALSE): {len(logical_rule_violations)}")
    if logical_rule_violations:
        print("  [CRITICAL FLAG] Violations detected! Specific document_id(s):")
        for v in logical_rule_violations:
            print(f"    - {v['document_id']} (split: {v['split']}) Subject: {v['subject']}")

    # 5. Privileged Documents Report
    print("\n" + "=" * 80)
    print(f"DOCUMENTS MARKED is_privileged = TRUE (Total: {len(privileged_docs)})")
    print("=" * 80)
    for p in privileged_docs:
        print(f"  * Document ID: {p['document_id']}")
        print(f"    Split: {p['split']}")
        print(f"    Relevant: {p['is_relevant']}")
        print(f"    Sender: {p['sender']}")
        print(f"    Recipient: {p['recipient']}")
        print(f"    Subject: {p['subject']}")
        print(f"    Notes: {p['notes']}")
        print("  " + "-" * 60)

    # 6. Agreement Analysis Report
    agreement_rate = (agreement_matches / total_docs) * 100.0 if total_docs > 0 else 0.0
    print("\n" + "=" * 80)
    print("HUMAN LABELS VS SUGGESTION AGREEMENT ANALYSIS")
    print("=" * 80)
    print(f"Total documents evaluated: {total_docs}")
    print(f"Agreements: {agreement_matches} ({agreement_rate:.2f}%)")
    print(f"Disagreements: {total_docs - agreement_matches} ({100.0 - agreement_rate:.2f}%)")
    print(f"\nBreakdown of Overrides:")
    print(f"  1. Suggested TRUE -> Human Overrode to FALSE (False Positives from Suggestion): {len(human_false_sugg_true)}")
    print(f"  2. Suggested FALSE -> Human Overrode to TRUE (False Negatives from Suggestion): {len(human_true_sugg_false)}")

    print(f"\n--- Overrides: Suggested TRUE -> Human FALSE ({len(human_false_sugg_true)} items) ---")
    for o in human_false_sugg_true:
        print(f"  * {o['document_id']} [{o['split']}] (Triggered terms: {o['suggested_terms']}) - Subj: {o['subject'][:60]}")

    print(f"\n--- Overrides: Suggested FALSE -> Human TRUE ({len(human_true_sugg_false)} items) ---")
    for o in human_true_sugg_false:
        print(f"  * {o['document_id']} [{o['split']}] - Subj: {o['subject'][:60]}")

    print("\n" + "=" * 80)
    print("OVERALL CLASS DISTRIBUTION (HUMAN LABELS)")
    print("=" * 80)
    rel_count = sum(1 for r in all_rows if r["is_relevant"] == "TRUE")
    priv_count = sum(1 for r in all_rows if r["is_privileged"] == "TRUE")
    print(f"Relevant (is_relevant=TRUE): {rel_count}/{total_docs} ({rel_count/total_docs*100:.1f}%)")
    print(f"Non-Relevant (is_relevant=FALSE): {total_docs - rel_count}/{total_docs} ({(total_docs-rel_count)/total_docs*100:.1f}%)")
    print(f"Privileged (is_privileged=TRUE): {priv_count}/{total_docs} ({priv_count/total_docs*100:.1f}%)")

if __name__ == "__main__":
    main()
