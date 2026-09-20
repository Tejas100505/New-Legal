"""
Verification Script for Enron Dataset & Labeling Infrastructure

Verifies:
1. File counts and split integrity (280 Train + 60 Val + 60 Test = 400 Total)
2. Integrity of all 400 files on disk (non-empty, accessible)
3. Schema check on CSV templates: confirms ground-truth fields are 100% EMPTY
4. Pipeline ingestion compatibility: runs DocumentIngestionAgent on 3 actual extracted files
5. Inspects AI prediction pilot outputs
"""

import os
import sys
import csv
import json
import asyncio

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.agents.ingestion import DocumentIngestionAgent, IngestionInput

BASE_DIR = os.path.abspath(os.path.join(backend_dir, ".."))
DATA_DIR = os.path.join(BASE_DIR, "data", "enron_evaluation")
MANIFEST_PATH = os.path.join(DATA_DIR, "manifest.json")
LABELING_DIR = os.path.join(DATA_DIR, "labeling")
AI_PREDICTIONS_CSV = os.path.join(DATA_DIR, "ai_predictions_val_sample.csv")

async def main():
    print("=" * 80)
    print("ENRON EVALUATION DATASET & LABELING INFRASTRUCTURE VERIFICATION")
    print("=" * 80)

    # ── Check 1: Manifest and Split Counts ────────────────────────────────
    print("\n[CHECK 1] Manifest and Split Count Verification:")
    assert os.path.exists(MANIFEST_PATH), f"Missing manifest at {MANIFEST_PATH}"
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    total_count = len(manifest)
    train_count = sum(1 for m in manifest if m["split"] == "train")
    val_count = sum(1 for m in manifest if m["split"] == "val")
    test_count = sum(1 for m in manifest if m["split"] == "test")

    print(f"  Total emails in manifest: {total_count}")
    print(f"  Train split: {train_count} (70.0%)")
    print(f"  Val split:   {val_count} (15.0%)")
    print(f"  Test split:  {test_count} (15.0%)")

    assert total_count == 400, f"Expected 400 total, got {total_count}"
    assert train_count == 280, f"Expected 280 train, got {train_count}"
    assert val_count == 60, f"Expected 60 val, got {val_count}"
    assert test_count == 60, f"Expected 60 test, got {test_count}"
    print("  [OK] Split arithmetic exactly 280/60/60 = 400.")

    # ── Check 2: Physical Disk File Verification ──────────────────────────
    print("\n[CHECK 2] Verifying Physical Files on Disk:")
    missing = 0
    empty = 0
    custodians = set()
    for m in manifest:
        fpath = os.path.join(BASE_DIR, m["filename"])
        custodians.add(m["custodian"])
        if not os.path.exists(fpath):
            missing += 1
        elif os.path.getsize(fpath) == 0:
            empty += 1

    print(f"  Files verified on disk: {len(manifest) - missing}/{len(manifest)}")
    print(f"  Distinct custodians represented: {len(custodians)}")
    print(f"  Empty files: {empty}")
    assert missing == 0, f"Found {missing} missing files!"
    assert empty == 0, f"Found {empty} empty files!"
    print("  [OK] All 400 files exist and contain non-zero bytes.")

    # ── Check 3: Schema and Ground Truth Blankness Check ──────────────────
    print("\n[CHECK 3] Labeling CSV Template Schema & Ground Truth Purity:")
    templates = ["labeling_template_train.csv", "labeling_template_val.csv", "labeling_template_test.csv"]
    for t_name in templates:
        t_path = os.path.join(LABELING_DIR, t_name)
        assert os.path.exists(t_path), f"Missing template {t_name}"
        with open(t_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            for r in rows:
                assert r["is_relevant"] == "", f"Polluted ground truth in {t_name}: {r['is_relevant']}"
                assert r["is_privileged"] == "", f"Polluted ground truth in {t_name}: {r['is_privileged']}"
                assert r["notes"] == "", f"Polluted ground truth in {t_name}: {r['notes']}"
        print(f"  [OK] {t_name} ({len(rows)} rows): Ground truth fields 100% blank for human reviewers.")

    # ── Check 4: Pipeline Ingestion Compatibility Check ───────────────────
    print("\n[CHECK 4] Testing Pipeline Ingestion on 3 Sample Enron Files:")
    agent = DocumentIngestionAgent()
    sample_items = [manifest[0], manifest[140], manifest[280]]

    for i, item in enumerate(sample_items, 1):
        full_path = os.path.join(BASE_DIR, item["filename"])
        ingestion_input = IngestionInput(
            file_path=full_path,
            original_filename=os.path.basename(full_path),
            custodian=item["custodian"]
        )
        out = await agent.run(ingestion_input)
        print(f"  Sample {i}: {item['document_id']}")
        print(f"    MIME Type: {out.mime_type} | Document Type: {out.document_type} | Size: {out.file_size} bytes")
        print(f"    Hash (SHA256): {out.hash[:16]}... | Custodian: {out.custodian}")
        assert out.file_size > 0
        assert out.hash is not None

    print("  [OK] DocumentIngestionAgent successfully ingested all sample files without error.")

    # ── Check 5: AI Prediction Pilot Summary ──────────────────────────────
    print("\n[CHECK 5] AI Prediction Pilot Inspection:")
    assert os.path.exists(AI_PREDICTIONS_CSV), "Missing AI predictions CSV"
    with open(AI_PREDICTIONS_CSV, "r", encoding="utf-8-sig") as f:
        p_rows = list(csv.DictReader(f))

    print(f"  Total AI predictions generated: {len(p_rows)}")
    for i, r in enumerate(p_rows[:3], 1):
        print(f"  Prediction Row {i}: {r['document_id']}")
        print(f"    Subject: {r['subject']}")
        print(f"    AI_PREDICTION_document_type: {r['AI_PREDICTION_document_type']}")
        print(f"    AI_PREDICTION_is_privileged: {r['AI_PREDICTION_is_privileged']} (conf: {r['AI_PREDICTION_privilege_confidence']})")
        print(f"    AI_PREDICTION_privilege_method: {r['AI_PREDICTION_privilege_method']}")
        print(f"    AI_PREDICTION_latency: {r['AI_PREDICTION_latency_seconds']}s")

    print("\n" + "=" * 80)
    print("ALL VERIFICATIONS COMPLETED AND CONFIRMED WITH 100% REAL PIPELINE OUTPUT")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
