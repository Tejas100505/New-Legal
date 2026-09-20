"""
Generate Clean CSV Labeling Templates for Human Reviewers
Reads data/enron_evaluation/manifest.json and generates Google Sheets-ready CSV files.
"""

import os
import csv
import json

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(BASE_DIR, "data", "enron_evaluation")
LABELING_DIR = os.path.join(DATA_DIR, "labeling")
MANIFEST_PATH = os.path.join(DATA_DIR, "manifest.json")

os.makedirs(LABELING_DIR, exist_ok=True)

CSV_COLUMNS = [
    "document_id",
    "split",
    "filename",
    "custodian",
    "date",
    "sender",
    "recipient",
    "subject",
    "text_preview",
    "is_relevant",      # HUMAN GROUND TRUTH: Leave blank for human entry (TRUE / FALSE)
    "is_privileged",    # HUMAN GROUND TRUTH: Leave blank for human entry (TRUE / FALSE)
    "notes",            # HUMAN GROUND TRUTH: Leave blank for human entry (freeform notes)
    "reviewer",         # HUMAN REVIEWER: e.g. "Reviewer 1", "Reviewer 2", "Reviewer 3"
    "reviewed_at",      # REVIEW TIMESTAMP
]

def clean_csv_field(val) -> str:
    if val is None:
        return ""
    # Normalize internal newlines to single spaces for clean spreadsheet row display
    return str(val).replace("\r", " ").replace("\n", " ").strip()

def main():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    splits = {
        "train": [],
        "val": [],
        "test": [],
        "all": manifest,
    }

    for item in manifest:
        splits[item["split"]].append(item)

    print("=" * 80)
    print("GENERATING HUMAN LABELING CSV TEMPLATES")
    print("=" * 80)

    for split_name, items in splits.items():
        fname = f"labeling_template_{split_name}.csv"
        fpath = os.path.join(LABELING_DIR, fname)

        with open(fpath, "w", newline="", encoding="utf-8-sig") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=CSV_COLUMNS, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()

            for item in items:
                row = {
                    "document_id": item["document_id"],
                    "split": item["split"],
                    "filename": item["filename"],
                    "custodian": item["custodian"],
                    "date": clean_csv_field(item["date"]),
                    "sender": clean_csv_field(item["sender"]),
                    "recipient": clean_csv_field(item["recipient"]),
                    "subject": clean_csv_field(item["subject"]),
                    "text_preview": clean_csv_field(item["text_preview"]),
                    "is_relevant": "",       # STRICTLY BLANK FOR HUMAN GROUND TRUTH
                    "is_privileged": "",     # STRICTLY BLANK FOR HUMAN GROUND TRUTH
                    "notes": "",             # STRICTLY BLANK FOR HUMAN GROUND TRUTH
                    "reviewer": "",          # BLANK
                    "reviewed_at": "",       # BLANK
                }
                writer.writerow(row)

        print(f"Generated {fname}: {len(items)} rows at {fpath}")

    print("=" * 80)
    print("CSV GENERATION COMPLETE: ALL GROUND TRUTH FIELDS REMAIN 100% EMPTY")
    print("=" * 80)

if __name__ == "__main__":
    main()
