"""
Run Isolated AI Prediction Pilot on Enron Validation Sample
Strictly paced (4.5s delay) to respect 15 RPM free-tier limit.
Outputs to an isolated CSV with explicit AI_PREDICTION_* columns.
Does NOT modify or touch human ground-truth labeling templates.
"""

import os
import sys
import csv
import time
import json
import asyncio

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, "..", ".env"))

from app.agents.classification import ClassificationAgent, ClassificationInput
from app.agents.privilege import PrivilegeAgent, PrivilegeInput

BASE_DIR = os.path.abspath(os.path.join(backend_dir, ".."))
DATA_DIR = os.path.join(BASE_DIR, "data", "enron_evaluation")
MANIFEST_PATH = os.path.join(DATA_DIR, "manifest.json")
OUTPUT_CSV = os.path.join(DATA_DIR, "ai_predictions_val_sample.csv")

SAMPLE_SIZE = 15
PACING_DELAY_SECONDS = 4.5

async def main():
    print("=" * 80)
    print("STARTING PACED AI PREDICTION PILOT ON ENRON VALIDATION SET")
    print(f"Sample Size: {SAMPLE_SIZE} emails | Pacing Delay: {PACING_DELAY_SECONDS}s per item")
    print("=" * 80)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Filter validation set items
    val_items = [m for m in manifest if m["split"] == "val"][:SAMPLE_SIZE]
    print(f"Selected {len(val_items)} validation emails for AI prediction pilot.\n")

    classification_agent = ClassificationAgent()
    privilege_agent = PrivilegeAgent()

    results = []
    batch_start_time = time.time()

    for idx, item in enumerate(val_items, 1):
        file_path = os.path.join(BASE_DIR, item["filename"])
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            file_text = f.read()

        item_start = time.time()
        print(f"[{idx}/{SAMPLE_SIZE}] Processing: {item['document_id']} ({item['subject'][:40]})...", end=" ", flush=True)

        # 1. Run ClassificationAgent
        c_input = ClassificationInput(filename=os.path.basename(file_path), text=file_text)
        c_out = await classification_agent.run(c_input)

        # 2. Run PrivilegeAgent
        p_input = PrivilegeInput(document_id=item["document_id"], text=file_text)
        p_out = await privilege_agent.run(p_input)

        elapsed = time.time() - item_start
        print(f"Done in {elapsed:.2f}s | Type: {c_out.document_type} | Priv: {p_out.is_privileged} (conf: {p_out.confidence_score:.2f})", flush=True)

        results.append({
            "document_id": item["document_id"],
            "filename": item["filename"],
            "custodian": item["custodian"],
            "subject": item["subject"],
            "AI_PREDICTION_document_type": c_out.document_type,
            "AI_PREDICTION_is_privileged": p_out.is_privileged,
            "AI_PREDICTION_privilege_confidence": round(p_out.confidence_score, 4),
            "AI_PREDICTION_privilege_method": p_out.detection_method,
            "AI_PREDICTION_privilege_reasoning": p_out.reasoning.replace("\n", " ")[:200],
            "AI_PREDICTION_latency_seconds": round(elapsed, 2),
        })

        if idx < SAMPLE_SIZE:
            print(f"     Pacing delay ({PACING_DELAY_SECONDS}s to respect 15 RPM)...", flush=True)
            await asyncio.sleep(PACING_DELAY_SECONDS)

    total_batch_time = time.time() - batch_start_time

    # Write isolated AI predictions CSV
    fieldnames = [
        "document_id",
        "filename",
        "custodian",
        "subject",
        "AI_PREDICTION_document_type",
        "AI_PREDICTION_is_privileged",
        "AI_PREDICTION_privilege_confidence",
        "AI_PREDICTION_privilege_method",
        "AI_PREDICTION_privilege_reasoning",
        "AI_PREDICTION_latency_seconds",
    ]

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print("\n" + "=" * 80)
    print("AI PREDICTION PILOT COMPLETED SUCCESSFULLY")
    print(f"Total Emails Processed: {len(results)}")
    print(f"Total Batch Time: {total_batch_time:.2f} seconds (Average: {total_batch_time/len(results):.2f}s/email including pacing)")
    print(f"Predictions saved to isolated file: {OUTPUT_CSV}")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
