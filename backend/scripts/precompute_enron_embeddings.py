"""
Embedding pre-generator for Enron 400 emails with robust retry and batching.
Caches embeddings to data/enron_evaluation/.cache/enron_gemini_embeddings_1024.json.
"""

import os
import sys
import csv
import json
import time

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, "..", ".env"))

from app.agents.embedding import _get_gemini_client

BASE_DIR = os.path.abspath(os.path.join(backend_dir, ".."))
ENRON_FINAL_CSV = os.path.join(BASE_DIR, "data", "enron_evaluation", "labeling", "labeling_template_all_FINAL.csv")
CACHE_DIR = os.path.join(BASE_DIR, "data", "enron_evaluation", ".cache")
os.makedirs(CACHE_DIR, exist_ok=True)
CACHE_FILE = os.path.join(CACHE_DIR, "enron_gemini_embeddings_1024.json")

CASE_SCENARIO_QUERY = (
    "California energy market practices, pricing, regulatory communications, and trading strategy"
)

def main():
    print("=" * 80)
    print("PRE-GENERATING & CACHING GEMINI EMBEDDINGS (400 DOCS + QUERY)")
    print("=" * 80)

    client = _get_gemini_client()

    with open(ENRON_FINAL_CSV, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"Loaded {len(rows)} Enron documents from {ENRON_FINAL_CSV}")

    # 1. Load existing cache if partial
    existing_cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                existing_cache = json.load(f)
            print(f"Found existing cache with {len(existing_cache.get('doc_embeddings', []))} embeddings.")
        except Exception:
            existing_cache = {}

    query_vec = existing_cache.get("query_embedding")
    if not query_vec:
        print("Generating query embedding...")
        res = client.models.embed_content(
            model="gemini-embedding-001",
            contents=[CASE_SCENARIO_QUERY],
            config={"output_dimensionality": 1024}
        )
        query_vec = res.embeddings[0].values
        time.sleep(1.0)

    doc_vectors = existing_cache.get("doc_embeddings", [])

    # Prepare texts truncated to 3500 chars to avoid token quota burst
    doc_texts = []
    for r in rows:
        p = os.path.join(BASE_DIR, r["filename"])
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8", errors="replace") as fp:
                txt = fp.read()
        else:
            txt = f"Subject: {r.get('subject', '')}\n\n{r.get('text_preview', '')}"
        doc_texts.append(txt[:3500])

    start_idx = len(doc_vectors)
    BATCH_SIZE = 10  # 10 texts per request = safe under token per minute quota

    print(f"Starting from index {start_idx} / {len(doc_texts)} (Batch size: {BATCH_SIZE})...")

    for i in range(start_idx, len(doc_texts), BATCH_SIZE):
        batch = doc_texts[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (len(doc_texts) + BATCH_SIZE - 1) // BATCH_SIZE

        retries = 5
        success = False
        while retries > 0 and not success:
            try:
                res = client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=batch,
                    config={"output_dimensionality": 1024}
                )
                for emb in res.embeddings:
                    doc_vectors.append(emb.values)
                success = True
                print(f"[{batch_num:02d}/{total_batches}] Embedded docs {i} to {i+len(batch)-1} (Total: {len(doc_vectors)})")
            except Exception as e:
                retries -= 1
                wait_sec = 5.0 * (6 - retries)
                print(f"[RETRY {retries}] Error on batch {batch_num}: {e}. Waiting {wait_sec:.1f}s...")
                time.sleep(wait_sec)

        if not success:
            raise RuntimeError(f"Failed to embed batch {batch_num} after retries.")

        # Periodically flush cache
        if len(doc_vectors) % 50 == 0 or len(doc_vectors) == len(doc_texts):
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump({"query_embedding": query_vec, "doc_embeddings": doc_vectors}, f)
            print(f"  [CACHE SAVED] {len(doc_vectors)} embeddings saved to {CACHE_FILE}")

        # Pacing between batches to respect 15 RPM / token burst limits
        time.sleep(4.2)

    print("\nALL 400 EMBEDDINGS SUCCESSFULLY GENERATED AND CACHED!")

if __name__ == "__main__":
    main()
