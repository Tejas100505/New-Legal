"""
Verification script for ClusteringAgent on real Enron dataset and synthetic dataset:
1. Run clustering on the real Enron 400-document dataset (using cached 1024-dim Gemini embeddings).
2. Show actual clusters formed with generated labels and sample documents per cluster.
3. Compare against a completely different dataset (the synthetic privilege benchmark)
   to prove that labels dynamically change according to content, rather than falling back to fixed names.
4. Report API cost profile.
"""

import os
import sys
import csv
import json
import time
import asyncio

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, "..", ".env"))

from app.agents.clustering import ClusteringAgent, ClusteringInput

BASE_DIR = os.path.abspath(os.path.join(backend_dir, ".."))
ENRON_FINAL_CSV = os.path.join(BASE_DIR, "data", "enron_evaluation", "labeling", "labeling_template_all_FINAL.csv")
EMBEDDINGS_CACHE_FILE = os.path.join(BASE_DIR, "data", "enron_evaluation", ".cache", "enron_gemini_embeddings_1024.json")
SYNTH_BENCHMARK_CSV = os.path.join(BASE_DIR, "data", "synthetic_privilege_benchmark.csv")

async def run_verification():
    print("=" * 80)
    print("RUNNING LIVE CLUSTERING VERIFICATION ON REAL ENRON 400-DOC DATASET")
    print("=" * 80)

    # 1. Load Enron dataset and cached embeddings
    with open(ENRON_FINAL_CSV, "r", encoding="utf-8") as f:
        enron_rows = list(csv.DictReader(f))
    with open(EMBEDDINGS_CACHE_FILE, "r", encoding="utf-8") as f:
        cache = json.load(f)

    doc_embeddings = cache["doc_embeddings"]
    assert len(enron_rows) == len(doc_embeddings) == 400, "Dataset / embedding length mismatch"

    enron_docs = []
    for i, r in enumerate(enron_rows):
        p = os.path.join(BASE_DIR, r["filename"])
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8", errors="replace") as fp:
                txt = fp.read()
        else:
            txt = f"Subject: {r.get('subject', '')}\n\n{r.get('text_preview', '')}"
        
        enron_docs.append({
            "id": r["document_id"],
            "subject": r.get("subject", ""),
            "text": txt[:3000],
            "embedding": doc_embeddings[i]
        })

    agent = ClusteringAgent()

    # Run clustering with k=4 clusters on Enron dataset
    start_time = time.time()
    enron_out = await agent.run(ClusteringInput(
        documents=enron_docs,
        n_clusters=4,
        use_llm_labeling=True
    ))
    enron_runtime = time.time() - start_time

    print(f"\nEnron Clustering Completed in {enron_runtime:.2f}s | Confidence: {enron_out.confidence_score}")
    print(f"Generated {len(enron_out.clusters)} clusters:\n")

    id_to_doc = {d["id"]: d for d in enron_docs}

    for c in enron_out.clusters:
        print("=" * 70)
        print(f"CLUSTER {c.cluster_id}: \"{c.label}\" ({len(c.document_ids)} documents)")
        print(f"Top Distinguishing TF-IDF Terms: {', '.join(c.top_terms)}")
        print("Sample Documents:")
        for did in c.document_ids[:3]:
            doc_item = id_to_doc.get(did, {})
            snippet = doc_item.get("text", "").replace("\n", " ")[:140]
            print(f"  - [{did}] Subj: {doc_item.get('subject', '')[:50]}")
            print(f"    Text: {snippet}...")
        print("=" * 70)

    # 2. Test dynamic adaptation on a completely DIFFERENT dataset (Synthetic Benchmark)
    print("\n" + "=" * 80)
    print("TESTING DYNAMIC ADAPTATION ON SECOND DATASET (SYNTHETIC PRIVILEGE BENCHMARK)")
    print("=" * 80)

    with open(SYNTH_BENCHMARK_CSV, "r", encoding="utf-8") as f:
        synth_rows = list(csv.DictReader(f))

    # Generate quick embeddings for the 24 synthetic docs using Gemini
    from app.agents.embedding import GeminiEmbeddingProvider
    provider = GeminiEmbeddingProvider()
    synth_texts = [r["text"] for r in synth_rows]
    synth_embeddings = provider.embed_batch(synth_texts)

    synth_docs = [
        {"id": r["benchmark_id"], "subject": r["subject"], "text": r["text"], "embedding": synth_embeddings[i]}
        for i, r in enumerate(synth_rows)
    ]

    synth_out = await agent.run(ClusteringInput(
        documents=synth_docs,
        n_clusters=3,
        use_llm_labeling=True
    ))

    print(f"\nSynthetic Benchmark Clusters (k=3):")
    for c in synth_out.clusters:
        print(f"  * Cluster {c.cluster_id}: \"{c.label}\" (Terms: {', '.join(c.top_terms[:4])}) - {len(c.document_ids)} docs")

    # Verify that synthetic labels are entirely different from Enron labels
    enron_labels = [c.label.lower() for c in enron_out.clusters]
    synth_labels = [c.label.lower() for c in synth_out.clusters]
    print(f"\nEnron Labels:     {enron_labels}")
    print(f"Synthetic Labels: {synth_labels}")
    overlap = set(enron_labels).intersection(set(synth_labels))
    print(f"Label Overlap: {overlap} (Should be empty, demonstrating true content-derived naming)")
    assert len(overlap) == 0, f"Found unexpected label overlap: {overlap}"

    print("\n" + "=" * 80)
    print("ALL CLUSTERING VERIFICATIONS COMPLETED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_verification())
